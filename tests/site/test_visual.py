#!/usr/bin/env python3
"""Visual re-checks: hidden-state fix, 3D king render, fresh screenshots."""
from playwright.sync_api import sync_playwright
import os, sys

BASE = "http://127.0.0.1:8899"
SHOTS = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "shots")
os.makedirs(SHOTS, exist_ok=True)

def _stub_endpoint(ctx):
    """The static test server has no POST support; emulate the lead-capture
    Worker so form submissions exercise the endpoint-success path."""
    ctx.route("**/v1/lead-requests", lambda r: r.fulfill(
        status=202, content_type="application/json",
        body='{"request_id":"test","status":"accepted","duplicate":false}'))

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f" — {detail}"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    ctx = browser.new_context(viewport={"width": 1440, "height": 960})
    _stub_endpoint(ctx)
    page = ctx.new_page()
    page.goto(f"{BASE}/contact.html"); page.wait_for_load_state("networkidle")
    fi = page.locator("[data-briefing-inline]")
    check("done block hidden initially", not fi.locator("[data-bb-done]").is_visible())
    check("back hidden on step 1", not fi.locator(".bb-back").is_visible())
    page.locator("#briefing").scroll_into_view_if_needed(); page.wait_for_timeout(900)
    page.screenshot(path=f"{SHOTS}/v2-desktop-step1.png")
    fi.locator("input[name=name]").fill("Jordan Blake")
    fi.locator("input[name=role]").fill("Chief Executive")
    fi.locator("input[name=organisation]").fill("Blake Group")
    fi.locator("input[name=email]").fill("jordan@blakegroup.com.au")
    fi.locator(".bb-next").click(); page.wait_for_timeout(800)
    check("back visible on step 2", fi.locator(".bb-back").is_visible())
    fi.locator(".bb-chip:has-text('Next 30 days') input").click(force=True)
    fi.locator(".bb-chip:has-text('Pilots underway') input").click(force=True)
    fi.locator("textarea[name=outcome]").fill("Lead follow-up is leaking revenue. We want an agentic pipeline that qualifies enquiries overnight and drafts replies for sign-off.")
    page.locator("#briefing").scroll_into_view_if_needed(); page.wait_for_timeout(600)
    page.screenshot(path=f"{SHOTS}/v2-desktop-step2.png")
    fi.locator(".bb-next").click(); page.wait_for_timeout(900)
    page.locator("#briefing").scroll_into_view_if_needed(); page.wait_for_timeout(900)
    page.screenshot(path=f"{SHOTS}/v2-desktop-review.png")
    page.evaluate("window.location.assign = () => {}")
    fi.locator(".bb-next").click(); page.wait_for_timeout(1700)
    check("done visible after send", fi.locator("[data-bb-done]").is_visible())
    check("done ref filled", "BRF-" in fi.locator("[data-bb-doneref]").inner_text())
    page.locator("#briefing").scroll_into_view_if_needed(); page.wait_for_timeout(500)
    page.screenshot(path=f"{SHOTS}/v2-desktop-success.png")
    page.evaluate("localStorage.clear()")
    page.close()

    # 3D king render
    page = ctx.new_page()
    page.goto(f"{BASE}/"); page.wait_for_load_state("networkidle")
    page.locator(".king-stage").scroll_into_view_if_needed()
    try:
        page.wait_for_selector(".king-stage.ready", timeout=25000)
        check("king GLB loaded (stage ready)", True)
    except Exception:
        check("king GLB loaded (stage ready)", False, "model-viewer never fired load")
    page.wait_for_timeout(2500)
    page.locator(".king-stage").screenshot(path=f"{SHOTS}/v2-king-stage.png")
    page.close()

    # mobile screenshots
    mctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    _stub_endpoint(mctx)
    mp = mctx.new_page()
    mp.goto(f"{BASE}/"); mp.wait_for_load_state("networkidle")
    mp.locator("header [data-open-briefing]").click(); mp.wait_for_timeout(800)
    check("mobile done hidden initially", not mp.locator("[data-briefing-modal] [data-bb-done]").is_visible())
    mp.screenshot(path=f"{SHOTS}/v2-mobile-sheet.png")
    mp.close(); mctx.close()
    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n{len(results)-len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
