---
name: rb-graphics-builder
description: Companion to rigorous-build for building a UI or visual product from a vague idea instead of generating generic "AI slop." Use when the user wants to design or build a new UI, app, dashboard, landing page, or visual product and hasn't nailed down exact requirements yet. Gathers real requirements (asks clarifying questions, requests reference screenshots), searches for genuine design inspiration, locks a color scheme with the user up front (steering away from default purple gradients and dark-mode-by-default), and builds toward a professional, deliberate result instead of a generic AI-generated look.
---

# RB-Graphics-Builder — build a UI that doesn't look AI-generated

Companion to `rigorous-build` for the DESIGN/BUILD-A-PRODUCT work-shape, the same way
`rb-explore` is the companion for the EXPLORE shape. Pairs with `ui-inspiration` (where to
look for real references) and hands the locked visual language off to `rigorous-build` for
the actual implementation and validation gates.

## Through-line

Generic AI-generated UI has a signature look: purple-to-blue gradients, glassmorphism applied
for its own sake, dark mode by default, emoji standing in for icons, centered hero text with a
vague tagline. The fix isn't "add more polish" — it's grounding every visual decision in
something real *before* generating anything: a reference the user actually likes, a color
scheme they actually chose, a layout appropriate to the category of product.

## 1. Understand the ask before touching pixels

- Restate what's being built in one sentence and confirm it.
- If the user has an existing product or brand, ask for screenshots of it (or of anything
  adjacent they like) and read them — extract concrete facts: existing palette, density, type
  scale, component style. Don't invent a look when a real one is sitting in front of you.
- If there's no screenshot yet, ask a short, pointed set of questions rather than guessing:
  - What's the closest existing product this should feel like? (name one)
  - **Color scheme — ask explicitly, never default.** Don't default to purple/violet gradients
    or dark-mode-first just because that's the common generative-AI look. Get a real answer: a
    brand color, an industry convention, or at minimum an explicit steer ("no purple, no dark
    background unless I ask for it").
  - Who's the audience, and what's the one primary action this screen exists for?
  - Light, dark, or user's choice?

## 2. Go get real references — don't invent from memory

- Invoke `ui-inspiration` for the category-appropriate source list (dashboard vs. marketing
  site vs. consumer app all point at different sources).
- Search the web for 2–3 *current* examples in the same category as what's being built — real
  shipping products, not generic "AI design inspiration" roundups. Name what's being borrowed
  from each and why.
- If reference screenshots were provided in step 1, they outrank generic gallery results —
  treat them as the primary source of truth.

## 3. Build to avoid AI slop, deliberately

Concrete tells to avoid unless the user actually asked for them:
- Purple/violet/blue gradient backgrounds as a default choice
- Dark mode as the only or default theme without being asked
- Glassmorphism/frosted blur applied for decoration rather than function
- Generic hero copy ("Supercharge your workflow", "The future of X")
- Emoji standing in for real icons in a professional product
- Perfectly symmetric, centered, low-information layouts with excess whitespace and no data

Build instead: dense-but-calm layouts modeled on the references from step 2, a restrained
palette anchored to the confirmed color scheme, real content over placeholder lorem ipsum, and
one deliberate accent color used consistently rather than a rainbow of gradients.

## 4. Hand off to rigorous-build for the actual implementation

Once the visual language and references are locked, this skill's job is done. Building the
actual UI, validating it (syntax → smoke → behavior probe → visual read-back gates), and
iterating on real code is `rigorous-build`'s job. Feed it: the confirmed color scheme, the 2–3
reference products/screens and what's borrowed from each, and any constraints gathered in
step 1 — don't build ad hoc here and skip the handoff.

## Definition of done

- [ ] The ask restated and confirmed in one sentence
- [ ] Real references gathered — screenshots read, or 2–3 named live products/searches
- [ ] Color scheme explicitly asked and confirmed with the user, never defaulted
- [ ] AI-slop tells checked against and avoided, or a deliberate reason given for keeping one
- [ ] Handed off to rigorous-build with the locked visual language, not built ad hoc here
