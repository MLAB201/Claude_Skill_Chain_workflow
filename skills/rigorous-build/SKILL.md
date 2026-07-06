---
name: rigorous-build
description: The disciplined build-and-validate loop for shipping features into a large or existing codebase without breaking it — the "Fable methodology". Use when implementing or continuing a feature, especially in big single-file apps or the UBPA auditor (app/index.html, backend/app.py), and whenever the user says "continue the work", "build/add this feature", "make it premium", "carry on the same level of quality", "emulate the fable methodology", or wants careful, validated, backed-up changes rather than a quick patch. Enforces: ground in real code/data, refuse to be confidently wrong (adversarial pre-mortem + honest INDETERMINATE over a plausible-but-false answer), backup before edit, match existing patterns and reuse the existing pipeline, validate through layered gates (syntax → smoke → behavior probe → visual) with adversarial fixtures drawn from real data, test in isolation, de-scope to the honest slice, clean up, and log to memory.
---

# Rigorous Build

Ship a change into an existing codebase so it works the first time, tells the truth, and
leaves the repo clean. One loop, cheapest steps first:

```
GROUND  →  BACKUP  →  BUILD  →  VALIDATE  →  CLEAN UP  →  DOCUMENT
(real code) (archive) (match+reuse) (4 gates)  (no litter)   (memory)
```

Through-line: **refuse to be confidently wrong.** An honest "indeterminate" beats a
plausible answer that's false; a smaller correct slice beats an impressive broken one; a
reverted change beats a half-wired one left in the tree.

Reference implementation: the UBPA app + its `%LOCALAPPDATA%\Temp\ubpa_smoke\` toolbox.
The full rationale with worked examples is `docs\BUILD_METHODOLOGY.md` in that project.
Companion skills by work-shape: EXPLORING an unknown system (black box, hidden rules,
undocumented device) → invoke `rb-explore`; this file governs the BUILD shape.

## The fable stance (read first)

The mindset the rest of this skill operationalizes:

- **Ground in the code, not the ticket.** The plan's premise is a hypothesis. Go read the
  actual functions and data and let reality correct the plan *before* you build. Cite what
  you found by `file:line`, not from memory.
- **Hunt the confident-wrong answer.** Before writing a line, enumerate every way the
  feature could produce a plausible result that is FALSE and that a user would act on. Those
  cases *are* the design, not an afterthought.
- **Honest slice over impressive-but-wrong.** Ship the part you can prove; refuse (don't
  fake) the part you can't model yet; name the cut out loud.
- **Respect the identity.** The project's constraints (offline / zero-dep / single-file /
  no-server) are the product, not obstacles — bend to them even when a shortcut is easier.
- **Leave it unbroken.** If it can't be made to work and validated this pass, revert it and
  say why. Never leave a half-wired edit in the tree.

## 0. Self-interrogation — the self-prompt (run before building)

Fable's edge is that it generates its own adversarial context before acting. Reproduce that:
answer these IN WRITING (one line each — in the plan, the report, or the journal) before the
first edit. An unanswerable question is your next action, not a detail to skip.

1. **Wrong answer:** what is the most damaging *plausible-but-false* output this change could
   produce, and who would act on it?
2. **Premise:** which facts does the task statement assume about the existing code? Which have
   I verified (file:line) — and which broke on contact?
3. **Consumer:** what existing pipeline/function eats my output, and does it arrive in the
   shape that consumer already digests?
4. **Gate:** how is this proven with no live infrastructure — which fixture, which probe,
   which exact assertion values?
5. **Cut:** what am I refusing or deferring, and does the user-visible surface admit that
   honestly (INDETERMINATE / disabled-with-reason) instead of faking it?
6. **Boundary:** what untrusted input crosses into this code, and what caps/bounds/abort
   rules catch a hostile or malformed version of it?
7. **Identity:** which project constraints (offline / zero-dep / single-file / no-egress)
   does the *easy* implementation violate, and what is the compliant shape?

Generating these answers IS the methodology — the rest of the loop just enforces them.

**Self-assessment gate — offer the interview, don't impose it or skip it.** If answering the
seven questions above leaves a real gap that would change what gets built (vague scope, an
unconfirmed visual/brand direction, a requirement with more than one plausible reading), don't
silently guess and don't launch straight into an interview either. Surface the choice in one
line: *"I've got a few questions that would sharpen this — want me to ask them (`/rb-interview`), or
should we skip the interview and get building?"* If the user wants to skip, proceed on the most
defensible assumption and name it plainly in the report — a rushed build beats a stalled one,
but the offer has to happen before you commit to guessing instead of asking.

## 1. Ground — never fabricate your own inputs

Before designing anything that depends on real data, schema, or machine state, **pull the
real thing first.** Don't invent field names, identifiers, control numbers, config
signatures, or API shapes from memory.
- Read the actual data structure / DB / file before writing code against it.
- Extract real values (categories, enums, signatures) and build against *those*.
- Check what's actually installed/running before advising on it.
- **Verify what the data actually preserves and *means*.** A parser that is tolerant for
  *display* may silently drop the exact tokens your feature depends on (the `established`,
  the `echo-reply`, the object-group) — read it and confirm the field carries the truth
  before you build a verdict on top of it. Tolerant-for-display is a false-answer machine
  for evaluation.
- **Expect the premise to break on contact.** "Just parse the already-ingested X" routinely
  hides an unbuilt prerequisite — the binding, the index, the join, the direction. Find that
  gap before you scope, or you'll ship a confident answer built on data that isn't there.

If a fact isn't in front of you, go get it. A wrong assumption baked into a large file is
expensive to remove.

## 2. Backup before every edit — never delete, always archive

Copy the target to an archive **before touching it**, named for what comes next:
```
Copy-Item "<file>" "<dir>\_archive\<name>_backup_YYYYMMDD[_HHMMSS].<ext>" -Force
```
Superseded artifacts get archived, not deleted. Only delete something you yourself just
created as a throwaway, and say so. Before overwriting anything you didn't create, look at
it first.

## 3. Build — match the surrounding code, reuse the pipeline

New code should be indistinguishable from old. Reuse existing patterns, helpers, classes,
and design tokens instead of inventing parallel ones. Match comment density, naming, and
idiom. **Re-scan the current file right before a scripted edit** — line numbers drift.

- **Feed the existing pipeline; don't fork it.** Make new data arrive in the shape the
  existing consumers already parse (synthesize the canonical form) rather than adding a
  second, parallel path. Mirror a sibling module's structure, vocabulary, and events so the
  new thing reads as one the codebase already had.
- **Bend to the project's identity.** If the ethos is zero-dependency / offline /
  single-file, honor it even when a library would be easier — hand-roll the small thing
  before you add a dep the product's promise forbids.
- **Be defensive at every trust boundary.** Bytes or text from the network, a device, or a
  user get bounds-checks, size/loop caps, and are never silently dropped — carry a diagnostic
  note instead. Write the security posture down (a header comment) *and* implement it.

**Design surface & assets.** When the change has a UI, pull real patterns from `/ui-inspiration`
before laying it out (real shipping-product layouts beat generic from-memory). When the app needs
icons, a logo, banners, or a favicon, generate them with `/graphics-builder` (Gemini → transparent
PNGs / `.ico`), then place + document. Both feed the **visual read-back** gate below.

## 4. Integrity — refuse to be confidently wrong

The senior move on any feature that renders a *judgment* — a verdict, a path, a match, a
reachability claim, a derived count: make it structurally impossible to state a plausible
falsehood.

- **Adversarial pre-mortem.** List the false-PERMIT / false-DENY / false-"delivered" /
  wrong-count traps. For each, ask the only question that matters: *is it detectable from the
  data I actually have?* If yes, handle it. If no, the answer MUST degrade — never guess.
- **Three-state honesty.** DETERMINED / CHANGED / INDETERMINATE (or PERMIT / DENY /
  INDETERMINATE). Uncertainty is a first-class result — shown, non-dismissable, and naming
  the exact condition that stopped it. That transparency is what earns trust in the amber
  instead of resentment.
- **Word confident answers precisely.** "No modeled rule blocks this — verify on device" is
  not "allowed." An advisory must never read as ground truth.
- **De-scope or refuse rather than fake.** Fingerprint and *refuse* inputs you can't model
  (don't best-effort mis-parse ASA netmasks as IOS wildcards into an inverted verdict). Defer
  a sub-feature that would return INDETERMINATE almost always — shipping it is
  abandoned-feature bait. Deliver a per-part verdict: build-this-honestly vs
  don't-build-this-part-yet.
- **Stay consistent with the project's own rulings.** Cite the settled law; don't relitigate
  an integrity rule the team already decided (e.g. "policy claims cap at indeterminate").

## 5. Validate — four gates, cheapest first, stop at first failure

**Never assume an edit landed correctly.** If the project has no gate chain yet, building
the minimal one IS the first task — "no harness" is never a reason to skip validation.

1. **Syntax gate (every edit, instant).** For a big single-file app, extract each inline
   `<script>` and run `new vm.Script()` on it; `py_compile` for Python; `node --check` /
   `tsc --noEmit` elsewhere. (UBPA: `node …\check_scripts.js "<path>\index.html"`.)
2. **Smoke (load + console).** Load the page headless on an **isolated port**, assert key
   functions exist (`typeof` map), assert critical UI rendered/painted, require **0 console
   errors**. (UBPA: `node …\smoke.js http://localhost:8011/index.html`.)
3. **Behavior probe (the real gate) — with ADVERSARIAL fixtures from real data.** A throwaway
   `probe_<feature>.js` that calls the new code and **asserts the result** — exact counts,
   exact before/after, exact derived values. The fixtures that matter are the ones that would
   EXPOSE a wrong answer: the false-positive and false-negative cases, drawn from the real
   sample lab, that a naive implementation fails (the OSPF route out a shut port that must
   read INDETERMINATE, not "delivered"). Expose the module's internals so the engine is
   unit-testable offline; when there's no live system, **build its counterpart from your own
   code** — e.g. a loopback mock agent from your own response encoder — so the probe drives the
   REAL end-to-end path, not just a unit. Once per project, plant a known failure and confirm the
   harness catches it — a gate that cannot fail is not a gate; and **if a gate ever passes
   something suspect, distrust the harness itself** — a validator with a silent skip (matching a
   block's body instead of its opening tag) is worse than none: repair the tool, re-run, confirm
   it now catches the class.
4. **Visual read-back.** Screenshot new UI and *actually look at the image*. Fix layout,
   re-shoot. Don't trust that it looks right — verify.

**Blind the probe when you are both builder and judge.** If the same context that built the
thing also grades it, contamination is the default: generate fixtures whose expected answers
you cannot know in advance (runtime-random inputs, ground truth written to a quarantined file),
commit the observed result IN WRITING before looking at the truth, then score. And check *why*
a test passed — a correct answer produced by plausible guessing is a method failure dressed as
a validation, because it can't tell you when it's wrong.

## 6. Clean up

Test services run on a throwaway port, never the user's live instance — then kill the test
process. Remove test-only state the run created. Leave the tree as clean as you found it.

## 7. Encode gotchas once

When the platform surprises you, fix it **and** write the gotcha to memory so it's never
re-learned. (Examples that bit these projects: a hot-reload server only exposes functions
present at process *start* → restart + re-probe after backend edits; a display-tolerant
parser that silently drops the tokens an evaluator needs.)

## 8. Right-size the effort

Work inline when that's faster than briefing an agent. Reserve subagents/swarm for genuinely
parallel, independent work. **Strong model (fable) for the judgment-heavy build and the
adversarial review; cheaper models for grunt work.** An integrity-sensitive feature is worth
a dedicated senior *pessimist* pass — someone whose only job is to find the confident-wrong
answer — *before* you build, not after. Don't spawn machinery a single edit doesn't need.
Verification has a cost too: when evidence already in hand answers the question, cite it —
don't re-run an expensive probe as theater when its outcome is already determined.

## 9. Document — memory is the logbook

After each round, append a dated entry to project memory: exact function/file names that
changed, gotchas, backup filenames, and what remains. A future session resumes in one read
instead of re-deriving the codebase. Report honestly: state what was validated and *how*
(numbers, not "should work"); flag caveats out loud; never claim done before the gates pass.
When the user interrupts mid-task, finish the current safe step, then address them.

## Definition of done

- [ ] Self-interrogation (§0) answered in writing, one line each
- [ ] If a real gap remained after §0, the user was offered the /rb-interview (or the choice to skip it) — never silently guessed instead
- [ ] Inputs grounded in real code/data, not assumed; verified the data actually carries what the feature needs
- [ ] Adversarial pre-mortem done — every trap that's undetectable from the data degrades to INDETERMINATE, not a guess
- [ ] Judgments worded so an advisory can't be mistaken for ground truth
- [ ] Scope cut honestly — refused/deferred what can't be modeled, and said so
- [ ] Touched files backed up to `_archive\` first
- [ ] New code matches existing patterns, reuses the existing pipeline, respects the project's identity
- [ ] Syntax gate passes (0 errors)
- [ ] Smoke passes (0 console errors, key UI present/painted)
- [ ] Behavior probe asserts the result with real/mock data, including the false-positive/false-negative fixtures
- [ ] New UI screenshotted and visually checked
- [ ] Test service killed; test-only artifacts removed
- [ ] New gotcha + change summary written to memory
- [ ] Reported honestly with validation evidence — or reverted cleanly if it couldn't be made to work

## Running this skill on a junior/mid model (Opus and below)

A senior model self-generates the structure above by disposition; a junior model executes
contracts. Same loop, harder edges: convert each disposition into a **checkable obligation** —
demand artifacts, not attitude. The report format must refuse to compile without them.

**Contract-bind the strong model too** when the work is unattended or integrity-critical.
Disposition is probabilistic, obligations are structural: measured head-to-head (2026-07-05,
nine controlled runs), bare senior and junior models alike flagged conspicuous problems
voluntarily — but under genuine ambiguity every bare model guessed, and only the
contract-bound arm refused. The table below is insurance for everyone, not remediation
for juniors.

| Fable disposition | Obligation to demand from the junior |
|---|---|
| Attacks the premise | "Premise check" section: each assumption the task makes about existing code, verified w/ file:line, marked HOLDS or BROKEN |
| Cites evidence | Every codebase claim carries file:line; an unanchored claim counts as unverified |
| Enumerates failure modes | Written pre-mortem table: trap → detectable-from-my-data? → handle / INDETERMINATE / refuse |
| Weighs wrong-answer cost | If the feature renders a judgment: three-state output mandatory + precision wording ("not blocked by any modeled rule", never "allowed") |
| De-scopes to the honest slice | Mandatory "Cut list" — what was deferred/refused and why; "nothing cut" itself requires justification |
| Tests adversarially | ≥1 false-positive fixture, ≥1 false-negative fixture, ≥1 positive control — drawn from real sample data, named |
| Reuses the pipeline | Name the existing consumer + show the shape match; a new parallel path needs explicit written justification |
| Designs for the gate | Module exposes internals for offline probing; probe output pasted VERBATIM in the report |
| Degrades loudly | No silent drops — skipped/truncated work carried in a notes/manifest channel |
| Recon-first | Report opens with a recon log: what was READ (files + ranges) before anything was written |
| Reports honestly | Gate outputs verbatim; a "NOT verified" section; the phrase "should work" is banned |

Also give the junior the revert path up front ("if gates fail: restore the backup, report
BLOCKED with exact notes") — a junior left without an exit ships the broken thing.

## Self-improvement loop — this skill maintains itself

This file is living. Whenever a conversation contains senior-model (fable) work — a build, a
review, a de-risk, subagent reports — mine it for behaviors this skill doesn't yet encode:
run `PERSONA-MINER.md` (this folder) against that conversation, or paste its block into it.

Merge rules (the skill follows its own law): backup SKILL.md to `_archive/` first; every
addition needs a concrete evidenced moment; prefer SHARPENING an existing bullet over
appending a new one; max ~5 additions per pass; keep this file under ~260 lines — a bloated
skill stops being read; never delete a load-bearing rule without archiving. A mining pass
that finds nothing new records nothing — absence of insight is a valid result.
