---
name: ui-inspiration
description: >-
  Where to look — and what to look for — before building any UI, so design
  choices are grounded in real shipping products instead of generic layout
  generated from memory. Use at the START of any UI/frontend task: building or
  designing a dashboard, admin panel, data table, internal tool, config viewer,
  log/audit/sizing tool, settings page, console, analytics view, or single-file
  HTML app. Triggers on "build a UI", "design a dashboard", "make an admin
  panel", "what should this look like", "style this tool", "UI inspiration",
  "lay out this page", or any data-dense SaaS / internal-tool screen. Points at
  live products (Linear, Stripe, Grafana, Datadog, Retool) and component
  libraries (shadcn/ui) with the right search terms per UI category, then adapt.
---

# UI Inspiration

A reference of **where to look — and what to look for — before building a UI.**
The goal is to ground design choices in real, shipping products instead of
generating generic layout from memory. **Pull a concrete pattern, then adapt it.**

## How to use this skill

When a UI task starts, do this in order:

1. **Classify the UI** (see "Pick the right category"). The category determines
   which sources are useful and which search terms surface the right examples.
2. **Pull 1–3 concrete reference patterns** from the sources for that category —
   a real layout, a real component arrangement, a real interaction. **Name what
   you're borrowing and why.**
3. **Adapt, don't copy.** Answer: what pattern works, why it works, and whether
   it fits this context. Avoid pixel-copying aspirational concept shots that
   don't survive contact with real data.
4. **Default to buildable.** Favor dense, functional layouts from live products
   over award-bait. If the deliverable is a single-file HTML tool, lean on
   component libraries and live-product references, not motion-heavy concept art.

## Pick the right category

Most of the work here is **internal tools / admin dashboards / data-dense SaaS
application UI** — log parsers, sizing calculators, audit tools, config viewers,
dashboards. That is **NOT** consumer mobile and **NOT** marketing landing pages,
so steer away from those sources and search terms.

**Search terms that surface the right results** on the galleries below:
`dashboard`, `admin panel`, `data table`, `analytics`, `SaaS app`,
`developer tools`, `settings UI`, `console`, `internal tool`.

| If building… | Best sources | Notes |
|---|---|---|
| **Dashboard / admin / data-dense tool** | Live products (Linear, Stripe, Grafana, Datadog, Retool), shadcn/ui dashboard blocks | The core case. Study live products directly. |
| **Component / build-ready layout** | shadcn/ui, Tailwind UI, UI Database | Pairs patterns with actual code. Best for single-file HTML tools. |
| **Real app screens / full flow** | Mobbin, Page Flows, Pttrns | Best libraries, but mostly paywalled now (see flags). |
| **Web / SaaS marketing site** | Godly, Land-book, Landingfolio | Free curated galleries. |
| **Broad visual direction only** | Dribbble, Behance, Awwwards, Muzli | Free to browse. Filter the unbuildable concept shots hard. |

## The sources

### Live products — study directly (best free source for dense UI)

The gold standard for the data-heavy work. Free to open and inspect. When in
doubt, reach for these first.

- **Linear** — https://linear.app — masterclass in speed, clarity, dense-but-calm layout, keyboard-driven interaction.
- **Stripe Dashboard** — https://dashboard.stripe.com / https://stripe.com — making complex tasks feel approachable; excellent tables, forms, empty states.
- **Vercel** — https://vercel.com/dashboard — clean developer-tool aesthetic, good project/list patterns.
- **Grafana** — https://play.grafana.org — live public playground for metrics/observability dashboards.
- **Datadog** — https://www.datadoghq.com — dense telemetry UI, panel and filter patterns.
- **Retool** — https://retool.com/templates — internal-tool layouts and templates, directly on-point.

### Component / build-ready (most directly usable for HTML tools)

- **shadcn/ui** — https://ui.shadcn.com — free, open source. The **Blocks** and **Dashboard** sections are essentially copy-paste admin layouts.
- **Tailwind UI** — https://tailwindcss.com/plus — previews free to study; components are paid.
- **UI Database** — https://uidatabase.com — patterns paired with copy-paste AI prompts (ChatGPT / Cursor / v0).

### Real app screenshots & full flows

- **Mobbin** — https://mobbin.com — largest library of real iOS/Android/web screens, organized by app, flow, and element. Limited free browsing, then subscription-gated.
- **Page Flows** — https://pageflows.com — complete recorded user journeys (onboarding → checkout → upgrade). Mostly paid.
- **Pttrns** — https://pttrns.com — curated mobile pattern library. Mostly paid.

### Web / SaaS site galleries (free)

- **Godly** — https://godly.website — curated, lean SaaS/web.
- **Land-book** — https://land-book.com — large free gallery.
- **Landingfolio** — https://www.landingfolio.com — landing-page focused, annotated.

### Broad visual inspiration (free to browse — filter hard)

Good for color, type, and visual direction. Weak for buildable dense UI — these
skew toward aspirational concept work, so don't copy literally.

- **Dribbble** — https://dribbble.com — widest range; best filtered by `dashboard` / `saas` / `admin`.
- **Behance** — https://www.behance.net — agency-portfolio heavy.
- **Awwwards** — https://www.awwwards.com — award-winning, often over-designed web experiences.
- **Muzli** — https://muz.li — browser-extension inspiration stream; background tool, not deep analysis.

### Free-to-browse cheat sheet

For "free AND matches dense-tool work," the honest shortlist:

- **Study directly:** Linear, Stripe, Grafana, Retool, Datadog, Vercel.
- **Pull layouts from:** shadcn/ui dashboard blocks.
- **Skim a gallery:** Godly, Land-book.

The dedicated app-screenshot libraries (Mobbin, Page Flows, Pttrns) are
better-organized but paywall quickly — note this if recommending them to the user.

## Patterns that translate to single-file HTML tools

When the deliverable is a self-contained HTML tool (the common delivery
pattern), the reusable ideas above are mostly **structural, not decorative**:

- **Dense tables done calmly** — Linear/Stripe row spacing, zebra-free quiet borders, right-aligned numerics, monospaced IDs.
- **Filter + result split** — a left/top filter rail driving a live result region (Datadog, Grafana panels).
- **Command palette / keyboard-first** — Linear's Cmd-K pattern for power users.
- **Empty + loading + error states** — Stripe's handling of these is worth copying; tools usually skip them and feel unfinished.
- **Restrained palette + one accent** — let data carry the color; reserve accent for actions/status.
- **Inline status pills** — compact colored chips for pass/fail/warn, ideal for audit and sizing output.

When you reach for one of these, **say which product it's borrowed from** so the
user can go look at the source.

## Hand off to brand assets

Once the visual language is set here (palette, accent, density, aesthetic), generate the actual
brand imagery — app icon, logo/mark, nav/severity/vendor icon set, page banners — with the
**`graphics-builder`** skill (Gemini image pipeline). Feed it what you established here: the accent
hex and a one-line style descriptor become its STYLE-LINE (the cohesion anchor), so the generated
assets match the screen. This skill sets the layout; `graphics-builder` fills it with on-brand art
(and hand-authored SVG for crisp vector marks).
