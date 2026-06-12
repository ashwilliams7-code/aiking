# AIKING Dynamic WordPress Website Migration Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task after Ash approves the architecture and plugin choices.

**Goal:** Move AIKING from the current static GitHub Pages landing site into a premium, mobile-first, dynamic WordPress platform with real CMS editing, lead capture, client/prospect logins, plugin-powered automations, and conversion infrastructure.

**Current baseline:** `/Users/Sky/projects/aiking` is a static `index.html` site deployed to GitHub Pages at `https://aiking.info`, with a public-safe `command-centre/` route backed by JSON and GitHub Actions. The current site is visually strong but operationally too static for a serious agency-style WordPress presence.

**Architecture:** Keep `aiking.info` live on the static site until the WordPress build is fully staged, QA’d, secured, and ready. Build WordPress in staging first, recreate the current AIKING look as a dynamic theme/template system, then cut DNS over only after mobile, auth, plugin, SEO, analytics, and security checks pass.

**Recommended Stack:** Managed WordPress hosting + WordPress + Bricks Builder or a custom block theme + ACF Pro + CPTs + Fluent Forms/CRM/Booking or HubSpot/GoHighLevel integrations + SureMembers/MemberPress for login portals + RankMath SEO + performance/security/backups.

---

## Executive Direction

AIKING should become a real dynamic business platform, not just a prettier landing page.

The new site should feel like:

- a premium AI automation agency / private executive AI systems studio
- a mobile-first sales machine
- a content engine for AI agents, automation, executive leverage, and case studies
- a lead capture + qualification funnel
- a private portal for prospects/clients to log in and see audits, proposals, resources, or project status
- a backend Ash/Sky can update without touching raw HTML every time

The key is to avoid “bloated WordPress brochure site” energy. We want WordPress power with AIKING sharpness: fast, premium, cinematic, secure, and operational.

---

## Recommended Strategic Choice

### Use WordPress for the main public site

Use WordPress for:

- homepage
- service pages
- landing pages
- blog/resources
- case studies
- FAQ/schema pages
- lead forms
- quizzes/calculators
- client/prospect login portal
- booking/application funnel
- SEO/content publishing

### Keep heavier internal ops separate

Do **not** expose sensitive operational dashboards through the public WordPress site unless they are properly gated.

The existing `command-centre/` can either:

1. stay public-safe as a marketing/demo route, or
2. move behind a login as an internal/prospect portal feature, or
3. be rebuilt as a private WordPress dashboard page that reads sanitized data from an API.

Default recommendation: keep the current public command centre public-safe for now, but make the serious pipeline/private data login-only.

---

## Recommended Plugin / Feature Stack

### Builder / Theme Layer

Pick one:

1. **Bricks Builder** — recommended default for AIKING
   - Fast, developer-friendly, dynamic data support.
   - Better than Elementor for performance-heavy premium builds.
   - Good for reusable templates, CMS loops, dynamic landing pages.

2. **Custom block theme**
   - Cleanest long-term engineering choice.
   - More dev time.
   - Better if we want a fully custom, version-controlled AIKING theme.

3. **Elementor Pro**
   - Familiar agency ecosystem.
   - More plugin/theme bloat risk.
   - Only use if Ash specifically wants the common King Kong-style agency stack.

**Recommendation:** Bricks Builder + a custom child theme for AIKING.

### Dynamic CMS

- **ACF Pro** — custom fields for services, case studies, funnels, guarantee blocks, testimonials, AI agent types.
- **CPT UI** or custom code — custom post types:
  - AI Agents
  - Services
  - Case Studies
  - Resources
  - FAQs
  - Client Wins / Proof
  - Industries
  - Landing Pages

### Lead Capture / Forms

- **Fluent Forms Pro** or **Gravity Forms**
  - Private AI Revenue Leakage Audit form
  - qualification questionnaire
  - lead source tracking
  - file uploads if needed
  - conditional logic
  - webhook to CRM / Telegram / email

### CRM / Automation

Pick one:

1. **HubSpot** — polished CRM, easier client-facing credibility.
2. **GoHighLevel** — more agency funnel/SMS/automation power.
3. **FluentCRM** — WordPress-native, cheaper, more self-contained.

**Recommendation:** HubSpot if credibility + clean ops matter most; GoHighLevel if SMS/funnel automation becomes central.

### Booking

- **Calendly embed** for fastest launch, or
- **FluentBooking** for WordPress-native booking.

### Login / Portal

Pick based on depth:

1. **SureMembers** — simpler protected content / member dashboards.
2. **MemberPress** — heavier, paid memberships, gated resources, invoices/payments if needed.
3. **WP Customer Area / Client Portal plugin** — client-document style portal.
4. **Custom portal plugin** — best if we need AIKING-specific dashboards later.

**Recommendation:** Start with SureMembers for a lightweight prospect/client portal. Upgrade to custom portal only after the first real workflow is proven.

Portal sections:

- `/login/`
- `/portal/`
- `/portal/audit/`
- `/portal/proposal/`
- `/portal/project-status/`
- `/portal/resources/`

### SEO / Schema / Redirects

- **RankMath SEO**
- **Redirection**
- **Schema blocks** for FAQs, services, local/executive consulting, articles
- preserve `https://aiking.info/` canonical
- map old routes before launch

### Performance

Depends on host:

- **WP Rocket** or **LiteSpeed Cache**
- **Perfmatters**
- **ShortPixel / Imagify**
- CDN via Cloudflare
- aggressively limit scripts on mobile

### Security / Reliability

- host-level backups + **UpdraftPlus** optional secondary backups
- **Wordfence** or **Solid Security**
- **WP 2FA**
- **Limit Login Attempts** if not covered by security plugin
- **WP Mail SMTP**
- **Simple History** for audit trail
- staging environment required

---

## Information Architecture

### Primary Pages

1. `/` — premium dynamic homepage
2. `/ai-agents/` — AI agent systems overview
3. `/services/` — service hub
4. `/services/ai-agent-deployment/`
5. `/services/operations-automation/`
6. `/services/revenue-follow-up-systems/`
7. `/case-studies/`
8. `/resources/`
9. `/about/`
10. `/contact/` or `/apply/`
11. `/login/`
12. `/portal/`

### Homepage Sections

1. Mobile-first cinematic hero
2. Clear positioning: “Deploy AI Agents across your business”
3. Problem section: slow follow-up, manual ops, missed leverage
4. Agent deployment map
5. Proof / demo / command-centre teaser
6. Services
7. Case studies / proof blocks
8. Founder trust section
9. Audit/application CTA
10. FAQ
11. Sticky mobile CTA

### Dynamic Content Types

#### AI Agent CPT

Fields:

- agent name
- business function
- problem solved
- workflow diagram
- inputs
- outputs
- guardrails
- human approval points
- integrations
- CTA

#### Service CPT

Fields:

- headline
- outcome
- symptoms
- deliverables
- implementation timeline
- tools/integrations
- FAQ
- CTA

#### Case Study CPT

Fields:

- client/industry
- starting problem
- build delivered
- result/proof
- anonymization level
- testimonial
- before/after workflow

#### Resource CPT

Fields:

- article/video/guide type
- topic
- gated or public
- lead magnet attachment
- CTA

---

## Mobile Experience Requirements

The mobile site should not just resize desktop.

Required mobile behavior:

- instant premium first screen with clear CTA
- sticky bottom CTA after hero
- fast menu with service/agent/resource links
- thumb-friendly forms
- no long static text walls
- scroll-triggered sections that feel alive but do not block action
- interactive audit/quiz module
- dynamic proof cards
- lightweight animations only; no laggy canvas everywhere
- every important CTA visible within 1–2 scrolls

Mobile-specific modules:

1. “Find your AI bottleneck” quiz
2. “Choose your agent layer” cards
3. “Revenue leak calculator”
4. “Private audit application” form
5. “Book strategy call” CTA
6. Client/prospect login button

---

## Migration Phases

### Phase 0 — Decisions Ash Needs To Make

Before implementation, confirm:

1. Hosting: Kinsta / Cloudways / SiteGround / existing hosting?
2. Builder: Bricks, custom block theme, or Elementor-style agency stack?
3. CRM: HubSpot, GoHighLevel, FluentCRM, or none at first?
4. Portal depth: simple protected resources or full client dashboard?
5. Booking: Calendly, FluentBooking, GoHighLevel calendar, or manual email first?
6. Payments: Stripe/client invoices now or later?
7. Do we keep `command-centre/` public, private, or rebuild it?

Default recommendation:

- Hosting: Kinsta or Cloudways
- Builder: Bricks
- CRM: HubSpot to start
- Forms: Fluent Forms Pro
- Portal: SureMembers
- Booking: Calendly first, FluentBooking later if needed
- Command centre: keep public-safe demo, build private portal separately

---

### Phase 1 — Staging Setup

**Objective:** Create a safe WordPress environment without touching live `aiking.info`.

Tasks:

1. Buy/connect managed WordPress hosting.
2. Create staging domain, e.g. `staging.aiking.info` or host-provided staging URL.
3. Install WordPress.
4. Lock staging behind password/noindex.
5. Set up SSL.
6. Create admin account with 2FA.
7. Install base theme/builder.
8. Configure backups.
9. Configure Git/theme export strategy.
10. Verify staging loads on desktop and mobile.

Acceptance:

- staging URL loads
- WordPress admin works
- noindex enabled
- SSL active
- backups active
- 2FA active

---

### Phase 2 — Design System Rebuild

**Objective:** Turn the current static AIKING look into reusable WordPress templates.

Tasks:

1. Extract colors, fonts, spacing, cards, buttons, gradients, section styles from current `index.html`.
2. Create global style tokens in Bricks/theme.
3. Build reusable components:
   - hero
   - CTA band
   - proof cards
   - service card
   - agent card
   - founder card
   - FAQ accordion
   - mobile sticky CTA
   - footer
4. Rebuild current homepage as dynamic WordPress page.
5. Replace hardcoded service/proof content with CMS fields where sensible.
6. Test at 390px, 430px, tablet, desktop.

Acceptance:

- staging homepage visually matches or improves current site
- no mobile horizontal overflow
- menu works
- CTA buttons work
- page is editable in WordPress

---

### Phase 3 — CMS/Data Model

**Objective:** Make AIKING content dynamic instead of hardcoded.

Tasks:

1. Create CPTs:
   - Services
   - AI Agents
   - Case Studies
   - Resources
   - FAQs
   - Industries
2. Add ACF field groups for each CPT.
3. Build archive templates.
4. Build single templates.
5. Add 3–5 seed entries for each important CPT.
6. Add dynamic loops on homepage and service pages.
7. Add schema/SEO metadata for each content type.

Acceptance:

- Ash can add/edit services without editing code
- new AI Agent entries automatically appear in loops
- resources/blog can be published normally
- case studies can be anonymized and reused across pages

---

### Phase 4 — Conversion Funnel

**Objective:** Build the lead capture machine.

Tasks:

1. Create AI Revenue Leakage Audit form.
2. Add conditional questions:
   - business type
   - team size
   - revenue range optional
   - biggest revenue leak
   - current tools
   - urgency
   - budget/implementation readiness
3. Configure form notifications.
4. Send form submissions to CRM.
5. Send approval/review summary to Ash/Sky channel if allowed.
6. Add hidden lead source fields.
7. Build thank-you page.
8. Add booking CTA after form completion.
9. Add spam protection.
10. Test submission end-to-end.

Acceptance:

- form submits correctly
- lead appears in CRM
- Ash receives a clean summary
- thank-you page works
- no auto outbound messages without approval

---

### Phase 5 — Login / Portal

**Objective:** Add real logins without overbuilding too early.

Tasks:

1. Install SureMembers/MemberPress or chosen portal plugin.
2. Create roles:
   - Prospect
   - Client
   - Admin
3. Build `/login/` page.
4. Build `/portal/` dashboard.
5. Add protected sections:
   - audit results
   - proposal
   - project status
   - resources
6. Create test prospect user.
7. Create test client user.
8. Add logout/account links.
9. Add password reset flow.
10. Test mobile login flow.
11. Verify unauthorized users cannot access protected pages.

Acceptance:

- users can log in/out
- protected pages are actually protected
- mobile login is clean
- admin can assign content/resources to users/roles

---

### Phase 6 — Command Centre Strategy

**Objective:** Decide what happens to the current `command-centre/` route.

Options:

1. Keep current static public-safe command centre as a credibility/demo asset.
2. Rebuild it inside WordPress as a password-protected dashboard.
3. Split it:
   - public teaser page
   - private logged-in dashboard

Recommended:

- Public page: “AIKING Command Centre” teaser/demo with sanitized data.
- Private portal: real lead/prospect/project data gated behind login.

Tasks:

1. Audit current public `command-centre/data/*.json` for privacy.
2. Decide public vs private fields.
3. Build a WordPress page template or plugin block for sanitized dashboard data.
4. Protect the private version behind login.
5. Add cache-control rules if dynamic data is used.
6. Test unauthorized access.

Acceptance:

- no private lead/client data is public
- public demo remains impressive
- private dashboard requires login

---

### Phase 7 — Content Expansion

**Objective:** Make the site feel full, credible, and alive.

Initial content set:

1. 6 service pages
2. 8 AI agent pages
3. 3 case study templates, anonymized if needed
4. 10 blog/resource posts
5. 1 lead magnet
6. 1 audit/application funnel
7. 1 about/founder page
8. 1 FAQ hub

Priority articles/resources:

- “What AI Agents Actually Do Inside a Business”
- “Where Most Businesses Leak Follow-Up Revenue”
- “The AI Bottleneck Map: How to Find the First Automation Worth Building”
- “AI Agents vs Chatbots vs Automations”
- “Human Approval Points: How to Deploy AI Without Losing Control”

Acceptance:

- site no longer feels thin/static
- SEO structure exists
- AIKING can publish weekly without code changes

---

### Phase 8 — SEO, Tracking, Analytics

**Objective:** Make the migration safe and measurable.

Tasks:

1. Install RankMath.
2. Set site title/metadata.
3. Configure sitemap.
4. Add schema.
5. Add redirects for any changed routes.
6. Connect Google Search Console.
7. Connect Google Analytics/Plausible/Cloudflare Web Analytics.
8. Configure conversion events:
   - audit form start
   - audit form submit
   - booking click
   - login click
   - resource download
9. Test metadata/social cards.
10. Test sitemap and robots.

Acceptance:

- sitemap works
- noindex removed only at launch
- analytics tracks real events
- old URLs redirect correctly

---

### Phase 9 — Performance / Security QA

**Objective:** WordPress must not become slow or fragile.

Tasks:

1. Run mobile Lighthouse/PageSpeed.
2. Remove unused plugin scripts per page.
3. Optimize images.
4. Enable cache/CDN.
5. Test Core Web Vitals.
6. Configure security headers where host supports them.
7. Confirm admin 2FA.
8. Confirm backups.
9. Confirm plugin/theme auto-update policy.
10. Test login brute-force protection.
11. Test forms for spam.
12. Test mobile Safari/Chrome.

Acceptance:

- mobile performance is acceptable before launch
- login is protected
- backups are verified
- no console errors on key pages
- no horizontal overflow

---

### Phase 10 — Launch / DNS Cutover

**Objective:** Move `aiking.info` to WordPress with minimum risk.

Tasks:

1. Full staging backup.
2. Export current static site backup.
3. Confirm DNS target from host.
4. Lower DNS TTL if needed.
5. Remove staging password/noindex at launch moment.
6. Point `aiking.info` DNS to WordPress host.
7. Verify SSL.
8. Verify homepage.
9. Verify mobile.
10. Verify forms.
11. Verify login.
12. Verify sitemap.
13. Submit sitemap to Search Console.
14. Monitor 404s and form submissions for 48 hours.

Acceptance:

- `https://aiking.info` loads WordPress site
- SSL valid
- audit form works
- login works
- no major mobile bugs
- old content/routes preserved or redirected

---

## Implementation Task List

### Task 1: Confirm Architecture Decisions

**Objective:** Lock stack choices before build.

**Files:**

- Update: `docs/plans/2026-06-11-wordpress-dynamic-site-migration.md`

**Steps:**

1. Ash chooses hosting, builder, CRM, portal, booking, payments, command-centre direction.
2. Update this plan with final choices.
3. Create a build checklist from the finalized stack.

**Verification:**

- no major architecture question remains open

---

### Task 2: Create WordPress Staging

**Objective:** Build safely away from live site.

**Steps:**

1. Create managed WordPress staging instance.
2. Add staging URL.
3. Enable noindex/password protection.
4. Enable SSL.
5. Create admin with 2FA.

**Verification:**

- staging frontend and `/wp-admin/` load
- noindex active
- 2FA active

---

### Task 3: Install Base Stack

**Objective:** Install only necessary plugins first.

**Plugins:**

- Bricks or selected builder
- ACF Pro
- Fluent Forms or Gravity Forms
- RankMath
- WP Mail SMTP
- security plugin
- backup plugin if host backup is insufficient

**Verification:**

- plugins active
- no PHP fatal errors
- admin remains fast

---

### Task 4: Rebuild Homepage Template

**Objective:** Recreate current homepage dynamically.

**Source:**

- `/Users/Sky/projects/aiking/index.html`

**Steps:**

1. Port visual identity.
2. Rebuild hero.
3. Rebuild service/proof sections.
4. Rebuild founder/contact/FAQ sections.
5. Add sticky mobile CTA.
6. Connect content to CMS fields where appropriate.

**Verification:**

- mobile and desktop screenshots match the intended premium direction
- CTAs work
- no console errors

---

### Task 5: Build Dynamic CPT System

**Objective:** Convert repeated content into editable WordPress content types.

**CPTs:**

- Services
- AI Agents
- Case Studies
- Resources
- FAQs
- Industries

**Verification:**

- new CPT item appears automatically in relevant loops/templates

---

### Task 6: Build Lead Funnel

**Objective:** Replace mailto-only CTA with real application/audit flow.

**Steps:**

1. Build audit form.
2. Create thank-you page.
3. Connect CRM.
4. Connect booking CTA.
5. Test notifications.

**Verification:**

- test lead reaches CRM and notification inbox/channel

---

### Task 7: Build Login Portal

**Objective:** Add real logins and protected content.

**Steps:**

1. Configure member roles.
2. Build login/account pages.
3. Build dashboard.
4. Add protected sample audit/proposal/resource pages.
5. Test unauthorized access.

**Verification:**

- protected pages return login requirement for logged-out users
- test users only see the right content

---

### Task 8: Migrate/Protect Command Centre

**Objective:** Prevent public/private confusion.

**Steps:**

1. Audit current command-centre data.
2. Decide public demo vs private dashboard.
3. Rebuild or link accordingly.
4. Add login protection if private.

**Verification:**

- private data is not publicly accessible

---

### Task 9: SEO + Analytics Setup

**Objective:** Preserve search/social strength and measure conversions.

**Steps:**

1. Set metadata.
2. Create sitemap.
3. Configure schema.
4. Add analytics.
5. Add conversion events.
6. Test social preview.

**Verification:**

- sitemap reachable
- metadata correct
- conversion events fire

---

### Task 10: Launch QA

**Objective:** Do not cut over until WordPress is cleaner than the current static site.

**Checklist:**

- mobile viewport 390px/430px tested
- desktop tested
- forms tested
- login tested
- admin 2FA tested
- backups tested
- page speed tested
- noindex removed only at launch
- redirects ready
- 404 check complete

**Verification:**

- written launch report with screenshots/results

---

### Task 11: DNS Cutover

**Objective:** Move production domain safely.

**Steps:**

1. Backup static site.
2. Backup WordPress staging.
3. Update DNS.
4. Verify SSL.
5. Verify live homepage/forms/login.
6. Submit sitemap.
7. Monitor 48 hours.

**Verification:**

- `https://aiking.info` serves WordPress successfully

---

## First Build Milestone

The fastest useful first milestone is:

1. WordPress staging online
2. Bricks/ACF installed
3. current homepage rebuilt dynamically
4. real AI Revenue Leakage Audit form live on staging
5. basic login portal live on staging
6. mobile QA screenshots captured

Only after that should DNS cutover be considered.

---

## Risks / Guardrails

- Do not move DNS before staging is better than current live site.
- Do not make WordPress admin public without 2FA.
- Do not add every plugin just because agency sites do; every plugin must have a job.
- Do not expose lead/client/ops data publicly.
- Do not break current AIKING positioning: premium, sharp, AI agents, 100x operational leverage.
- Do not make the homepage slower than the current static site without a strong reason.
- Do not rely on mailto forever; the audit form must become real.

---

## Recommended Next Action

Make the stack decision, then create the staging WordPress instance.

My recommended default:

- **Host:** Kinsta or Cloudways
- **Builder:** Bricks
- **CMS:** ACF Pro + CPTs
- **Forms:** Fluent Forms Pro
- **CRM:** HubSpot first
- **Booking:** Calendly first
- **Portal:** SureMembers first
- **Security:** Wordfence/Solid Security + 2FA + host backups
- **Performance:** Cloudflare + host cache + Perfmatters/WP Rocket depending on host

Once approved, implementation should start with staging — not the live domain.
