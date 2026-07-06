# aiking.info — Executive Elevation (visual glow-up)

**Date:** 2026-07-06 · **Direction approved by Ash:** Option 1 — elevate the existing
cream + charcoal + lime executive editorial look. Scope: all pages. Copy: free rein,
no invented metrics or claims.

## Goals
Make the site feel premium and designed — depth, motion, texture — while keeping the
conservative executive-advisory positioning intact.

## What changes
1. **Typography** — `text-wrap: balance` on display headings, retuned H1 clamp
   (fixes one-word-per-line wrap at 1440px), Fraunces italic serif accents inside
   key headings with a lime marker underline.
2. **Motion** — IntersectionObserver scroll-reveal system (JS auto-tags cards,
   section heads, process steps; staggered within groups). Hero entrance sequence.
   Intelligence card: pointer tilt + breathing glow + live-ticking status values.
   Button sheen sweep + arrow nudge. Header shrinks on scroll. Modal entrance.
   All gated behind `prefers-reduced-motion: no-preference` and an `html.js` class
   (no-JS users see the static site unchanged).
3. **Depth & texture** — fine SVG grain overlay, lime aurora radials in dark
   sections, gradient hairline card borders, hover lift/glow, ghost serif quote
   mark, process-step connector line.
4. **Navigation** — mobile hamburger with full-screen staggered overlay (replaces
   the 8-link wrapped stack). Sky Intelligence keeps its neon treatment.
5. **Structural fixes** — mobile hero order (headline before dark card), founder
   photo treatment, focus-visible + selection styles, anchor scroll margins.
6. **Copy** — sharpened headings (serif-accent phrasing) on index + 8 subpages.
   Zero new claims; proof stance untouched.

## How
Static architecture unchanged (GitHub Pages + Cloudflare, one `site.css`, one
`site.js`). CSS/JS rewritten in place; all existing class contracts preserved so
the 13 HTML pages inherit the upgrade. Cache-busted via `?v=20260706-exec-elevate`.

## Verification
Local `http.server` + Playwright screenshots (1440px + 390px) pre-push; live
aiking.info verification post-deploy; iterate until GREEN.
