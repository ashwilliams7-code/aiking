# AIKING Mini Audit Test — Allure Beauty Boutique GC

Date: 2026-06-13
Business used for test: Allure Beauty Boutique GC / Hannah
Public site checked: `http://allurebeauty.boutique/`
Booking link checked: Timely booking URL
Instagram checked: `https://www.instagram.com/allurebeautyboutiquegc/`

> Internal test draft only. Do not send externally without Ash approving the tone and facts.

## One-line audit angle

Allure already has a strong beauty offer and a real booking flow, but it is still leaking potential clients at the trust, decision, and follow-up layers — especially visitors who are interested but not ready to pick a service immediately.

## What is working

- The offer is clear: lashes, brows, skin treatments, massage, and teeth whitening in Coomera.
- The site has strong boutique positioning: owner-led, calm, feminine, premium, not franchise-like.
- Booking is not hidden. There are repeated Timely booking CTAs across the page.
- The site uses real result imagery and links to Instagram/Threads.
- Pricing/menu direction is visible enough that visitors are not completely lost.

## Visible revenue leaks

### 1. Trust leak: HTTPS is currently broken

**Evidence:** `https://allurebeauty.boutique/` failed certificate verification. The certificate presented was for `*.github.io`, not `allurebeauty.boutique`.

**Why it matters:**
A normal customer may see a browser security warning or avoid the site entirely. For a beauty business, trust is everything — especially before someone books and shares personal/contact details.

**Fix:**
Resolve the custom-domain SSL certificate so the canonical `https://allurebeauty.boutique/` loads cleanly.

### 2. Decision leak: unsure visitors still have to self-select

The site says “not sure what to book?” but the next step is still essentially: choose a treatment in Timely or message on Instagram.

**Why it matters:**
New clients often do not know whether they need classic lashes, hybrid lashes, brow sculpt, dermaplaning, skin needling, whitening, or a facial. If the choice feels too hard, they delay.

**AIKING angle:**
Add a simple AI-assisted “Glow Match” flow:

1. What are you trying to improve? lashes / brows / skin / smile / reset
2. What is the occasion or timeline?
3. Natural or dramatic result?
4. Any concerns?
5. Recommend 1–2 services and send them to the exact booking path.

### 3. Follow-up leak: Instagram DMs may become manual admin

The site encourages visitors to message on Instagram for help choosing.

**Why it matters:**
That is good for trust, but it creates hidden admin load. If Hannah is busy with appointments, DMs can sit, get forgotten, or require repeated explanation.

**AIKING angle:**
A staff-approved DM/enquiry assistant could draft replies, ask qualifying questions, suggest the right treatment, and push the client toward Timely booking without Hannah needing to type every response manually.

### 4. Rebooking leak: beauty services are recurring, but the site is mostly first-booking focused

Lashes, brows, skin, massage, and whitening all have natural rebooking windows.

**Why it matters:**
The real money is not just first appointment conversion — it is retention and repeat visits.

**AIKING angle:**
Create a lightweight retention agent:

- Lash infill reminder around 2–3 weeks
- Brow maintenance reminder around 4–6 weeks
- Skin plan reminder monthly
- Event/holiday reactivation campaigns
- “Haven’t seen you in a while” win-back sequence

All messaging would be approval-first and brand-safe.

## AIKING Mini Audit Score

| Area | Score | Notes |
| --- | ---: | --- |
| Offer clarity | 8/10 | Clear services and positioning. |
| Booking access | 8/10 | Timely is visible and working. |
| Trust foundation | 4/10 | HTTPS issue is the urgent blocker. |
| Decision support | 6/10 | Good copy, but no guided recommendation flow. |
| Follow-up capture | 5/10 | Visitors can book or DM, but undecided leads may disappear. |
| AIKING fit | 8/10 | Strong fit for a small AI concierge + rebooking assistant. |

## Recommended first AIKING deployment

**Allure Glow Concierge**

A small, controlled AI assistant for the website/Instagram workflow that helps visitors choose the right treatment, captures intent, and pushes them into Timely booking or a staff-approved reply.

### First version

- 3–5 question treatment matcher
- Suggested treatment + booking CTA
- Lead capture for undecided visitors
- Staff-approved reply drafts for Instagram or web enquiries
- Weekly summary: enquiries, common questions, missed-booking opportunities, top treatments requested

### Why this is better than a generic chatbot

This is not “chat with our bot.”

It is a revenue-leakage layer:

> Help interested visitors decide faster, reduce repeated admin questions, and turn more Instagram/site attention into booked appointments.

## Client-friendly mini audit draft

Hey Hannah — I ran Allure through a quick AIKING-style mini audit as a test.

The good news: the brand and offer are already strong. The site clearly positions Allure as a calm, premium, owner-led beauty space, and the Timely booking path is visible.

The main leaks I’d look at are:

1. **Trust:** the HTTPS version of the domain appears to have a certificate issue, which can hurt confidence or block visitors.
2. **Decision-making:** new clients who are unsure what to book still need to self-select or DM you.
3. **Admin load:** Instagram/help-me-choose enquiries can become repeated manual messages.
4. **Retention:** lashes, brows, skin, and whitening all have natural rebooking windows that could be followed up more systematically.

The best AIKING-style fix would not be a generic chatbot. It would be a small **Glow Concierge** that asks a few questions, recommends the right service, sends people into Timely, and drafts follow-up replies for you to approve.

In plain English: Allure probably does not need “AI” for the sake of AI. It needs a cleaner layer between attention, decision, booking, and rebooking.
