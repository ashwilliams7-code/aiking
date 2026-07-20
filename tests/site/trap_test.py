from playwright.sync_api import sync_playwright

def active(page):
    return page.evaluate("""() => {
      const a = document.activeElement;
      if (!a) return 'null';
      return a.tagName + (a.className ? '.'+String(a.className).split(' ').join('.') : '') + (a.name ? '[name='+a.name+']' : '') + ' txt=' + (a.textContent||'').trim().slice(0,25);
    }""")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='chrome')
    page = browser.new_page()
    page.goto('http://127.0.0.1:8765/contact.html')
    page.wait_for_load_state('networkidle')
    page.click('header [data-open-briefing]')
    page.wait_for_timeout(300)
    # step 1 forward cycle from name input
    print('start:', active(page))
    for i in range(8):
        page.keyboard.press('Tab')
        print('Tab', i+1, '->', active(page))
    # backward from modal-close
    page.focus('.modal .modal-close')
    page.keyboard.press('Shift+Tab')
    print('Shift+Tab from close ->', active(page))

    # validation error semantics: submit empty step 1
    page.evaluate("document.querySelectorAll('.modal [data-bb] input').forEach(i=>i.value='')")
    page.click('.modal [data-bb-next]')
    page.wait_for_timeout(200)
    info = page.evaluate("""() => {
      const inp = document.querySelector('.modal input[name=name]');
      const err = inp.closest('.bb-field').querySelector('.bb-err');
      return { focused: document.activeElement===inp,
               ariaInvalid: inp.getAttribute('aria-invalid'),
               describedby: inp.getAttribute('aria-describedby'),
               errText: err.textContent,
               errVisible: getComputedStyle(err).display };
    }""")
    print('error state:', info)
    # accessible name of the invalid input (does wrapping label pick up err text?)
    snap = page.locator('.modal input[name=name]').aria_snapshot()
    print('invalid input aria:', snap)
    browser.close()
