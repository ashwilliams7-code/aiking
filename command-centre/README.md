# AI King Command Centre — live public-safe ops layer

Live route: `https://aiking.info/command-centre/`

This is a public-safe, approval-first customer acquisition radar for AI King.

## What it does

- Displays the current saved lead pipeline from `data/leads.json`.
- Automatic lead-radar scraping is paused; no daily scans run while the workflow is disabled/no `schedule` trigger exists.
- Manual refresh is still possible via GitHub Actions `workflow_dispatch` if Ash explicitly asks for it.
- Scores local dental / aesthetics prospects for AI King fit.
- Generates Telegram-ready summary text for Ash to approve/review.

## Safety boundaries

- No automatic outbound messages.
- No login-only scraping, CAPTCHA bypass, hidden APIs, or private data collection.
- No secrets in the repo.
- Published lead data is public-safe metadata only.

## Manual scraper run

Open the GitHub Actions workflow:

`https://github.com/ashwilliams7-code/aiking/actions/workflows/aiking-command-centre-scrape.yml`

Then click **Run workflow**.

## Local verification

```bash
python3 -m py_compile command-centre/scripts/scrape_public_leads.py
python3 command-centre/scripts/scrape_public_leads.py --limit 6
python3 -m http.server 8788
# open http://127.0.0.1:8788/command-centre/
```
