from playwright.sync_api import sync_playwright

def active(page):
    return page.evaluate("""() => {
      const a = document.activeElement;
      if (!a) return 'null';
      return a.tagName + (a.className ? '.'+String(a.className).split(' ').join('.') : '') + (a.name ? '[name='+a.name+']' : '') + (a.textContent ? ' txt='+a.textContent.trim().slice(0,30) : '');
    }""")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='chrome')
    page = browser.new_page()
    page.goto('http://127.0.0.1:8765/contact.html')
    page.wait_for_load_state('networkidle')

    # --- Test 1: modal flow, focus after send ---
    page.click('header [data-open-briefing]')
    page.wait_for_timeout(300)
    print('after open, active:', active(page))
    m = page.locator('.modal [data-bb]')
    page.fill('.modal input[name=name]', 'Test Person')
    page.fill('.modal input[name=role]', 'CEO')
    page.fill('.modal input[name=organisation]', 'TestCo')
    page.fill('.modal input[name=email]', 'test@example.com')
    page.click('.modal [data-bb-next]')
    page.wait_for_timeout(700)
    print('step2 active:', active(page))
    # choose timeframe chip via keyboard-ish (check radio)
    page.check('.modal input[name=timeframe][value="Next 30 days"]')
    page.fill('.modal textarea[name=outcome]', 'Automate reporting.')
    page.click('.modal [data-bb-next]')
    page.wait_for_timeout(800)
    print('step3 active:', active(page))
    # keyboard: focus the send button and press Enter (keyboard user)
    page.focus('.modal [data-bb-next]')
    page.keyboard.press('Enter')
    page.wait_for_timeout(1600)  # 850ms motion delay + slack
    done_visible = page.is_visible('.modal [data-bb-done]')
    print('done visible:', done_visible)
    print('AFTER SEND active element:', active(page))
    # Tab once - where does focus go?
    page.keyboard.press('Tab')
    print('after Tab #1:', active(page))
    page.keyboard.press('Tab')
    print('after Tab #2:', active(page))
    # is focus inside the modal?
    inside = page.evaluate("() => !!document.activeElement.closest('.modal')")
    print('focus inside modal after tabs:', inside)

    # --- Test 2: close and reopen modal in done state ---
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    print('after Escape close, active:', active(page))
    page.click('header [data-open-briefing]')
    page.wait_for_timeout(400)
    print('reopened (done state), active:', active(page))
    inside2 = page.evaluate("() => !!document.activeElement.closest('.modal')")
    print('focus inside modal on reopen:', inside2)
    page.keyboard.press('Tab')
    print('reopen Tab #1:', active(page))
    inside3 = page.evaluate("() => !!document.activeElement.closest('.modal')")
    print('focus inside modal after reopen Tab:', inside3)

    # --- Test 3: radio group accessible name ---
    page.goto('http://127.0.0.1:8765/contact.html')
    page.wait_for_load_state('networkidle')
    snap = page.locator('[data-briefing-inline] .bb-choice').first.evaluate("""el => {
      const r = el.querySelector('input[type=radio]');
      return { hasFieldset: !!r.closest('fieldset.bb-choice, [role=radiogroup]'),
               choiceRole: el.getAttribute('role'),
               labelledby: el.getAttribute('aria-labelledby') };
    }""")
    print('radio group semantics:', snap)

    # aria snapshot of the chips area (inline mount) after moving to step 2
    page.fill('[data-briefing-inline] input[name=name]', 'A')
    page.fill('[data-briefing-inline] input[name=role]', 'B')
    page.fill('[data-briefing-inline] input[name=organisation]', 'C')
    page.fill('[data-briefing-inline] input[name=email]', 'a@b.co')
    page.click('[data-briefing-inline] [data-bb-next]')
    page.wait_for_timeout(700)
    print(page.locator('[data-briefing-inline] fieldset[data-step="2"]').aria_snapshot())

    browser.close()
