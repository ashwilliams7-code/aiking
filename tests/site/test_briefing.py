#!/usr/bin/env python3
"""End-to-end checks for the aiking briefing builder + modal + pages."""
from playwright.sync_api import sync_playwright
import json, sys

BASE = "http://127.0.0.1:8899"
import os
SHOTS = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "shots")
import os; os.makedirs(SHOTS, exist_ok=True)


def _stub_endpoint(ctx):
    """The static test server has no POST support; emulate the lead-capture
    Worker so form submissions exercise the endpoint-success path."""
    ctx.route("**/v1/lead-requests", lambda r: r.fulfill(
        status=202, content_type="application/json",
        body='{"request_id":"test","status":"accepted","duplicate":false}'))

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (" — " + str(detail) if detail and not cond else ""))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")

    # ---------- desktop: contact page inline form ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 960})
    _stub_endpoint(ctx)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(f"{BASE}/contact.html")
    page.wait_for_load_state("networkidle")

    check("inline builder mounted", page.locator("[data-briefing-inline] form.bb").count() == 1)
    check("step 1 active", page.locator("[data-briefing-inline] .bb-step.active[data-step='1']").count() == 1)
    ref = page.locator("[data-briefing-inline] .bb-ref").inner_text()
    check("ref code shown", ref.startswith("BRF-"), ref)

    # invalid submit on step 1 -> errors, still step 1
    page.locator("[data-briefing-inline] .bb-next").click()
    page.wait_for_timeout(300)
    check("required errors shown", page.locator("[data-briefing-inline] .bb-field.invalid").count() == 4)
    check("still on step 1", "01" in page.locator("[data-briefing-inline] [data-bb-num]").inner_text())

    # bad email kept invalid
    fi = page.locator("[data-briefing-inline]")
    fi.locator("input[name=name]").fill("Jordan Blake")
    fi.locator("input[name=role]").fill("Chief Executive")
    fi.locator("input[name=organisation]").fill("Blake Group")
    fi.locator("input[name=email]").fill("not-an-email")
    fi.locator(".bb-next").click()
    page.wait_for_timeout(300)
    check("bad email blocked", fi.locator(".bb-field.invalid").count() == 1)
    fi.locator("input[name=email]").fill("jordan@blakegroup.com.au")
    page.screenshot(path=f"{SHOTS}/desktop-step1.png")
    fi.locator(".bb-next").click()
    page.wait_for_timeout(700)
    check("advanced to step 2", fi.locator(".bb-step.active[data-step='2']").count() == 1)
    check("progress shows 02", "02" in fi.locator("[data-bb-num]").inner_text())
    check("back button visible", fi.locator(".bb-back").is_visible())

    # step 2: radio chip required
    fi.locator(".bb-next").click()
    page.wait_for_timeout(300)
    check("timeframe required", fi.locator(".bb-choice.invalid").count() == 1)
    fi.locator(".bb-chip:has-text('Next 30 days') input").scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    fi.locator(".bb-chip:has-text('Next 30 days') input").click(force=True)
    fi.locator(".bb-chip:has-text('Pilots underway') input").click(force=True)
    check("timeframe chip checked", fi.locator("input[name=timeframe]:checked").count() == 1)
    check("maturity chip checked", fi.locator("input[name=maturity]:checked").count() == 1)
    fi.locator("textarea[name=outcome]").fill("Lead follow-up is leaking revenue. We want an agentic pipeline that qualifies enquiries overnight and drafts replies for sign-off.")
    cnt = fi.locator("[data-bb-count]").inner_text()
    check("char counter live", cnt != "0", cnt)
    page.screenshot(path=f"{SHOTS}/desktop-step2.png")
    fi.locator(".bb-next").click()
    page.wait_for_timeout(700)
    check("advanced to step 3", fi.locator(".bb-step.active[data-step='3']").count() == 1)
    doc = fi.locator("[data-bb-doc]").inner_text()
    for needle in ["Jordan Blake", "Blake Group", "jordan@blakegroup.com.au", "Next 30 days", "Pilots underway", "Lead follow-up"]:
        check(f"review contains {needle[:20]}", needle in doc)
    check("send label", "Send briefing request" in fi.locator(".bb-next").inner_text())
    page.screenshot(path=f"{SHOTS}/desktop-step3-review.png")

    # edit jump from review
    fi.locator("[data-bb-edit='1']").first.click()
    page.wait_for_timeout(600)
    check("edit jumps to step 1", fi.locator(".bb-step.active[data-step='1']").count() == 1)
    check("values kept", fi.locator("input[name=name]").input_value() == "Jordan Blake")
    fi.locator(".bb-next").click(); page.wait_for_timeout(500)
    fi.locator(".bb-next").click(); page.wait_for_timeout(500)

    # draft persistence before send
    draft = page.evaluate("localStorage.getItem('aiking-briefing-draft')")
    check("draft persisted", draft and "Jordan Blake" in draft)

    # send -> success panel + mailto link correctness (block mailto nav)
    page.evaluate("window.location.assign = () => {}")
    fi.locator(".bb-next").click()
    page.wait_for_timeout(1600)
    check("success panel shown", fi.locator("[data-bb-done]").is_visible())
    href = fi.locator("[data-bb-mailto]").get_attribute("href")
    check("mailto to ash", href.startswith("mailto:ash@aiking.info"))
    from urllib.parse import unquote
    body = unquote(href)
    for needle in ["Jordan Blake", "Blake Group", "Next 30 days", "Pilots underway", "Lead follow-up", ref]:
        check(f"mailto body has {needle[:16]}", needle in body)
    check("draft cleared after send", page.evaluate("localStorage.getItem('aiking-briefing-draft')") is None)
    page.screenshot(path=f"{SHOTS}/desktop-success.png")

    # ---------- draft restore on reload ----------
    page2 = ctx.new_page()
    page2.goto(f"{BASE}/contact.html")
    page2.wait_for_load_state("networkidle")
    page2.locator("[data-briefing-inline] input[name=name]").fill("Restore Test")
    page2.wait_for_timeout(600)  # debounce
    page2.reload(); page2.wait_for_load_state("networkidle")
    check("draft restored on reload", page2.locator("[data-briefing-inline] input[name=name]").input_value() == "Restore Test")
    page2.evaluate("localStorage.removeItem('aiking-briefing-draft')")
    page2.close()

    check("no console errors (contact)", not errors, errors[:3])
    page.close()

    # ---------- desktop: index modal ----------
    page = ctx.new_page()
    errs2 = []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.goto(f"{BASE}/")
    page.wait_for_load_state("networkidle")
    check("no static modal in html", page.locator("#modal-briefing-form").count() == 0)
    page.locator("header [data-open-briefing]").click()
    page.wait_for_timeout(600)
    check("modal opened", page.locator("[data-briefing-modal]:not([hidden])").count() == 1)
    check("modal has builder", page.locator("[data-briefing-modal] form.bb").count() == 1)
    check("modal step1 visible height ok", page.locator("[data-briefing-modal] .bb-step.active input[name=name]").is_visible())
    page.screenshot(path=f"{SHOTS}/desktop-modal.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check("escape closes modal", page.locator("[data-briefing-modal][hidden]").count() == 1)
    check("king stage present", page.locator(".king-stage").count() == 1)
    check("no console errors (index)", not errs2, errs2[:3])
    page.close()
    ctx.close()

    # ---------- mobile: sheet modal + form ----------
    mctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                               user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    _stub_endpoint(mctx)
    mp = mctx.new_page()
    merrs = []
    mp.on("pageerror", lambda e: merrs.append(str(e)))
    mp.goto(f"{BASE}/")
    mp.wait_for_load_state("networkidle")
    mp.locator("header [data-open-briefing]").click()
    mp.wait_for_timeout(700)
    check("mobile modal open", mp.locator("[data-briefing-modal]:not([hidden])").count() == 1)
    box = mp.locator("[data-briefing-modal] .modal-panel").bounding_box()
    check("mobile sheet full width", box and abs(box["width"] - 390) < 2, box)
    check("mobile sheet bottom anchored", box and abs((box["y"] + box["height"]) - 844) < 3, box)
    mp.screenshot(path=f"{SHOTS}/mobile-sheet.png")
    # fill flow quickly on mobile
    fm = mp.locator("[data-briefing-modal]")
    fm.locator("input[name=name]").fill("Mob Test")
    fm.locator("input[name=role]").fill("Director")
    fm.locator("input[name=organisation]").fill("MobCo")
    fm.locator("input[name=email]").fill("mob@test.co")
    fm.locator(".bb-next").click(); mp.wait_for_timeout(700)
    check("mobile step 2", fm.locator(".bb-step.active[data-step='2']").count() == 1)
    mp.screenshot(path=f"{SHOTS}/mobile-step2.png")
    # horizontal overflow check
    overflow = mp.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check("no horizontal overflow", overflow <= 1, overflow)
    check("no console errors (mobile)", not merrs, merrs[:3])
    mp.close(); mctx.close()

    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n{len(results)-len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
