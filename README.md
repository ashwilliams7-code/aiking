# AIKING — aiking.info

Landing site for **AIKING** (the *King of AI* persona). Single-page, static, no build step.

- **Live:** https://aiking.info
- **Stack:** plain HTML/CSS/JS (one `index.html`), hosted on GitHub Pages.
- **Booking:** Cal.com popup — set your real `username/event` slug in the `data-cal-link` attributes in `index.html` (see the comment block near the bottom of the file).

## Edit & deploy

It's a single file — edit `index.html`, commit, push. GitHub Pages redeploys automatically on push to `main`.

## Custom domain

`CNAME` pins the site to `aiking.info`. DNS must point at GitHub Pages (apex A/AAAA records + a `www` CNAME).
