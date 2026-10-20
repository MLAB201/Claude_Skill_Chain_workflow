# Claude Skill Chain Workflow

A small, opinionated set of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills
and hooks I use day to day: a disciplined build loop for shipping changes into existing
codebases without breaking them, a terse response mode for when I don't need the prose, and a
couple of hooks that cut token waste and auto-backup files before edits.

## What's in here

```
INSTALL.md              installer instructions written FOR Claude Code to execute
skills/
  rigorous-build/      the main one — disciplined build-and-validate loop ("fable methodology")
  caveman/              ultra-compressed response style
  rb-explore/           rigorous-build's companion for EXPLORING unknown systems
  ui-inspiration/       rigorous-build's companion for grounding UI work in real products
  rb-graphics-builder/  rigorous-build's companion for building a UI/product from a vague idea
  compactor/            handoff + /compact — the fix for a session running out of tokens
  counsel-of-5/         five-persona panel for hard decisions/tradeoffs
  rb-interview/         rigorous-build's companion for the self-assessment gate — grades answers, not just asks
hooks/
  trim-bash-output.js  PreToolUse hook: rewrites noisy git commands to save tokens
  archive-backup.ps1   PreToolUse hook: backs up a file before Claude edits it
  settings.snippet.json  reference JSON (for humans doing it by hand)
  README.md            full hook explainer / manual setup instructions
video-transcript-app/  web app: pull transcripts from YouTube & TikTok videos
```

## Install — the easy way

Clone or download this repo, open Claude Code with this folder as the working directory, and
just say:

> install these skills

Claude Code will read [`INSTALL.md`](INSTALL.md) and do the rest itself: copy both skill
folders into `~/.claude/skills/`, copy the cross-platform token-optimizer hook into
`~/.claude/hooks/`, copy the Windows-only auto-backup hook if you're on Windows, and merge the
hook wiring into your `~/.claude/settings.json` — backing it up first and appending to your
existing hooks rather than overwriting them. It'll tell you when it's done and to restart Claude
Code. No manual JSON editing required.

## Install — by hand

If you'd rather do it yourself (or want to see exactly what changes):

```
# skills — global, available in every project
cp -r skills/rigorous-build      ~/.claude/skills/
cp -r skills/caveman             ~/.claude/skills/
cp -r skills/rb-explore          ~/.claude/skills/
cp -r skills/ui-inspiration      ~/.claude/skills/
cp -r skills/rb-graphics-builder ~/.claude/skills/
cp -r skills/compactor           ~/.claude/skills/
cp -r skills/counsel-of-5        ~/.claude/skills/
cp -r skills/rb-interview        ~/.claude/skills/
```

Restart Claude Code (or start a new session). Claude will now invoke `/rigorous-build` or
`/caveman` when you type the slash command, or automatically when your prompt matches what
each skill's description says it's for (see each `SKILL.md` for the exact trigger phrases).

Skills work with zero hooks installed — the hooks only add token savings and automatic
backups on top. For the hooks, see [`hooks/README.md`](hooks/README.md) for the manual steps,
including merging the JSON into `settings.json` by hand.

## `video-transcript-app/` — YouTube & TikTok transcripts

A small web app (Python/FastAPI backend, plain HTML/JS frontend): paste a YouTube or TikTok
link and get the video's transcript to search, copy, or download as `.txt`/`.srt`/`.vtt`/`.json`.
It uses the platform's captions when they exist (via `youtube-transcript-api` and `yt-dlp`), and
can optionally fall back to local Whisper speech-to-text for videos with none. It can also be
installed on an Android phone as a home-screen app that appears in the YouTube and TikTok
**Share** menus, and run as a local MCP server so Claude (desktop app, Claude Code) or any MCP
client can fetch transcripts itself. Setup, phone install, MCP, API, and configuration are in
[`video-transcript-app/README.md`](video-transcript-app/README.md).

## `/rigorous-build` — the main one

The disciplined build-and-validate loop for shipping a feature into a large or existing
codebase without breaking it. I call it the "fable methodology" because it's built to
reproduce how my strongest model behaves by default — ground every claim in the real code, run
an adversarial pre-mortem before writing a line, refuse to guess when a judgment can't be
proven, and validate through layered gates before ever calling something done.

The loop, cheapest steps first:

```
GROUND  →  BACKUP  →  BUILD  →  VALIDATE  →  CLEAN UP  →  DOCUMENT
(real code) (archive) (match+reuse) (4 gates)  (no litter)   (memory)
```

Full details, the self-interrogation checklist, the validation gates, and the junior-model
contract table (for running the same discipline on cheaper models) are in
[`skills/rigorous-build/SKILL.md`](skills/rigorous-build/SKILL.md). It also has a
self-improvement loop — [`PERSONA-MINER.md`](skills/rigorous-build/PERSONA-MINER.md) is a
prompt you paste into a conversation to mine it for new senior-engineer behavior worth folding
back into the skill.

Trigger it by typing `/rigorous-build`, or just ask Claude to "build/add this feature",
"continue the work", or "carry on the same level of quality" — the skill's description is
written so Claude picks it up on its own in those cases.

## `/caveman`

Ultra-compressed, telegraphic response style. Strips filler words, pleasantries, and hedging —
keeps full technical accuracy (file paths, line numbers, exact commands, code blocks
untouched). Useful when you want fast, dense answers instead of prose.

Trigger with `/caveman`, or say "caveman mode" / "use caveman". See
[`skills/caveman/SKILL.md`](skills/caveman/SKILL.md) for the exact rules and a before/after
example.

## The rigorous-build chain

`/rigorous-build` is the constitution — evidence, integrity, honest uncertainty, layered
validation gates. The rest of the chain applies that same discipline to different
work-shapes, each staying narrow so no single skill file bloats into unreadability:

- **`/rb-explore`** — when the job isn't shipping a change but figuring out how something
  undocumented behaves (a black box, an unfamiliar API, "reverse engineer this"), rigorous-build
  hands off to this instead. Same evidence/integrity rules, applied to building a world model
  by experiment: predict before you act, replicate under varied conditions (not just repeats),
  hold out a slice of your observation budget to validate the assembled rule, and report
  UNDETERMINED honestly rather than an elegant rule that's wrong.
- **`/ui-inspiration`** — when the change has a UI, rigorous-build says to ground the layout in
  a real shipping product (Linear, Stripe, Grafana, shadcn/ui) before inventing one from memory.
  It's a reference doc, not a generator — it tells you where to look and what to borrow, then you
  adapt it.
- **`/rb-graphics-builder`** — the fourth link in the chain, for building a UI or product from a
  vague idea instead of generic "AI slop." Asks what's actually being built (reads reference
  screenshots if you have them), pulls real inspiration via `ui-inspiration` plus a live web
  search, and — critically — **always asks what color scheme you want** instead of defaulting to
  the generic AI look (purple/violet gradients, dark-mode-by-default, glassmorphism-for-its-own-
  sake). Once the visual language is locked, it hands the actual build off to `rigorous-build`.
  *Note: this one's authored for this repo, not copied from a live personal config the way the
  others are — there's no dependency on an image-generation MCP or API key, it's pure
  requirements-gathering + web search.*

Not included: `graphics-builder` (the original, image-generating version). It needs a Gemini
image-generation MCP registered plus an API key, and spends API credits per image — real setup
friction for a first install. `rb-graphics-builder` above covers the actual problem (avoiding
generic AI-looking output) without that dependency.

**On other UI/UX-quality skills:** a few of the strongest ones for this — `dataviz` (rigorous
color/form rules for charts and dashboards), `run` (launch the app and actually look at it —
what rigorous-build's "visual read-back" gate needs), `artifact-design` — are **built into
Claude Code itself**, not custom files living in `~/.claude/skills/`. Nothing to install; they're
already there once Claude Code is. Worth knowing they exist and pair naturally with
rigorous-build's validation gates, but there's no file to copy for them.

## `/rb-interview` and `/counsel-of-5` — pressure-testing before you commit

Two different ways to stop a bad plan before it costs you a build cycle:

- **`/rb-interview`** is the skill rigorous-build's self-assessment gate offers when its §0
  self-interrogation leaves a real gap — it interrogates a single decision, plan, or request. It
  asks the 2–5 questions that would actually change the outcome, then **grades the answers**
  instead of accepting whatever comes back — if an answer is vague ("make it nicer"), it says
  exactly why that's not enough and what specific answer would be. It's also usable standalone
  whenever you suspect your own ask is underspecified, not just when rigorous-build offers it.
- **`/counsel-of-5`** convenes five distinct expert personas (picked for the question — pragmatist,
  architect, security/risk, operator, skeptic by default) to independently take a position, argue
  the sharpest disagreements, then synthesize one decisive verdict. This is the one to reach for
  when there's a genuine tradeoff and you want more than one lens on it before committing.

Trigger either with its slash command, or the phrases in each `SKILL.md`. See
[`skills/rb-interview/SKILL.md`](skills/rb-interview/SKILL.md) and
[`skills/counsel-of-5/SKILL.md`](skills/counsel-of-5/SKILL.md).

## `/compactor` — the fix for running out of tokens

If a session runs long, the usual failure mode is losing state to a lossy auto-compaction, or
just re-deriving everything from scratch in a new session because nothing durable got written
down. `/compactor` writes a dense HANDOFF file to disk — current task, what's validated vs not,
exact resume point, gotchas — then hands over a ready-to-run `/compact` command so the next
context starts from that file instead of from nothing. It's not something rigorous-build calls
directly, but it's the most direct fix for a session burning tokens re-explaining itself.

Trigger with `/compactor`, or say "handoff and compact" / "prep for compaction", or just use it
whenever a session is getting long and you want to preserve state before compacting. See
[`skills/compactor/SKILL.md`](skills/compactor/SKILL.md).

## The ideal workflow — how these actually chain together

None of these are meant to be used in isolation — the value is in the order you reach for them.
Here's the intended flow, cheapest/earliest steps first:

```
                    ┌─ vague/underspecified ask? ──→ /rb-interview (pressure-test it first)
                    │
   START ───────────┤
                    │
                    └─ pick the work-shape:
                         │
                         ├─ shipping a change into code you can already read
                         │    → /rigorous-build directly
                         │
                         ├─ figuring out how an undocumented system behaves
                         │    → /rb-explore
                         │
                         └─ building a UI/product from a vague idea
                              → /rb-graphics-builder (pulls in /ui-inspiration)
                                   → hands off to /rigorous-build for the actual build

                    mid-build, a genuine tradeoff appears?
                         → /counsel-of-5 (synthesize a verdict, then keep building)

                    session running long?
                         → /compactor BEFORE context fills, not after

   THROUGHOUT: /caveman is an orthogonal style toggle, on or off at any point.
   THROUGHOUT: the two hooks run silently on every tool call regardless of which
               skill is active — token trimming on Bash, auto-backup on every edit.
```

**Worked example** — "help me build a settings dashboard for my app, I'm not sure exactly what
it needs yet":

1. The ask is underspecified → **`/rb-interview`** first. It won't accept "make it good" — it asks
   what settings actually need to live there, who the user is, and (this matters a lot for the
   next step) what color scheme/brand you're going for, grading each answer until they're
   specific enough to build from.
2. It's a UI being built from a vague idea, not a known code change → **`/rb-graphics-builder`**.
   It asks for reference screenshots if you have an existing app, pulls real dashboard patterns
   via `ui-inspiration` (Linear, Stripe, Grafana, Retool), searches the web for 2–3 current
   examples, and locks the palette from step 1 instead of defaulting to a purple gradient.
3. Visual language locked → hands off to **`/rigorous-build`**, which does the actual
   implementation: grounds in the real existing code, backs up before editing, builds matching
   existing patterns, and runs the four validation gates (syntax → smoke → behavior probe →
   visual read-back) before calling it done.
4. Midway, you're torn between a tabbed layout and a single scrolling page → **`/counsel-of-5`**
   convenes five lenses (pragmatist, architect, UX, operator, skeptic) and gives you one
   decisive call instead of you guessing.
5. Session's been going two hours and context is filling up → **`/compactor`** writes a handoff
   and hands you the `/compact` command before anything gets lost.

The whole time, the hooks are working underneath this without you thinking about them: every
`git status`/`diff`/`log` call comes back trimmed, and every file rigorous-build edits gets
backed up first automatically.

## Hooks — token optimizer & auto-backup

Claude Code hooks are scripts the harness runs automatically around tool calls — mine are wired
into my global `~/.claude/settings.json` as `PreToolUse` hooks. Two are included:

- **`trim-bash-output.js`** rewrites a handful of exact, bare git commands (`git status`,
  `git diff`, `git log`, etc.) to strip ANSI color and disable the pager before they run, so
  their output doesn't burn tokens in the transcript — and keeps a ledger of the actual bytes
  saved. It only touches an *exact* bare command; anything with extra flags, pipes, or
  chaining passes through untouched.
- **`archive-backup.ps1`** copies a file to a timestamped archive right before Claude edits it
  with `Edit`/`Write`/`NotebookEdit` — this is what makes the "backup before edit" step in
  `/rigorous-build` actually happen instead of just being a suggestion.

Both fire on `PreToolUse` rather than `PostToolUse` — the hook API only lets you rewrite tool
input *before* a call runs, so that's the only point where you can actually shrink what gets
captured. Full setup steps (where to put the scripts, what to merge into `settings.json`, how
to verify it's working) are in [`hooks/README.md`](hooks/README.md).

## Sharing this with GitHub Desktop

If this repo already exists on GitHub as a private repo and you just want to push these local
changes: open GitHub Desktop, it should show the new/changed files under this repo, write a
commit summary, click **Commit to main**, then **Push origin**. If the repo isn't on GitHub yet,
use **File → Add Local Repository** in GitHub Desktop, select this folder, then **Publish
repository** (uncheck "Keep this code private" if you want your friend to see it without being
added as a collaborator). Either way, once it's pushed you can just send your friend the repo
URL.
