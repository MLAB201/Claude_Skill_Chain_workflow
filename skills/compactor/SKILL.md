---
name: compactor
description: Write a detailed session HANDOFF markdown file (or files) capturing everything a fresh context needs — current task state, validated vs unvalidated work, file/line anchors, next steps, gotchas, user rulings — then kick off context compaction by ending the turn with a ready-to-run /compact command pointing at the handoff. Use when the user types /compactor, says "handoff and compact", "write a handoff then compact", "prep for compaction", "compact with a handoff", or when context is nearly full and session state would otherwise be lost.
---

# Compactor — handoff, then compact

Two jobs, in order: (1) persist the session's irreplaceable state into a dense HANDOFF
file on disk, (2) kick off compaction. Compaction summarizes lossily; the handoff is
the lossless record. Anything not written to disk before compacting may be gone.

`/compact` is a built-in CLI command — the model cannot invoke it (not via the Skill
tool, not via Bash). "Kicking it off" means: finish all writes, then make the **very
last line of your final message** a ready-to-run `/compact` command the user submits
with one paste. Never claim you compacted; say the handoff is written and hand over
the command.

## Step 1 — Identify the project(s)

The working directory may be a multi-project workspace (many app folders under one
root). The handoff belongs in the **specific project folder(s) touched this session**,
not the workspace root. If the session genuinely spanned multiple projects, write one
handoff per project — each fresh context reads only its own.

## Step 2 — Match the project's existing handoff convention

Check the project folder before writing (`ls`, don't deep-glob a huge workspace):

- Existing dated handoffs (`SESSION_HANDOFF_YYYY-MM-DD.md`) → write a new one for
  today's date, and open with a supersedes line naming the previous file and
  correcting anything it got wrong ("supersedes SESSION_HANDOFF_2026-07-03, which
  said X; it is now Y"). Never delete or rewrite old handoffs.
- Existing single `HANDOFF.md` → update it in place (backup first if the project has
  a backup convention).
- No handoff yet → create `SESSION_HANDOFF_<YYYY-MM-DD>.md` in the project root.
- If the project has a CLAUDE.md that names an orientation doc, make sure it points
  at (or still correctly points at) the newest handoff. Fix the pointer if stale.

## Step 3 — Write the handoff

**Evidence rule:** every claim must come from this session or be verified against the
files right now. Never write state from memory of what "should" be true — a wrong
handoff is worse than none, because the fresh context will trust it. Convert all
relative dates ("today", "yesterday") to absolute dates.

**Audience rule:** write for a fresh context with ZERO conversation history. It can
read the repo, so don't duplicate what code/git/CLAUDE.md already record — capture
what's *only in this conversation*: decisions and their reasons, what was tried and
failed, what's validated vs merely written, user rulings, exact resume point.

Template (drop sections that don't apply; dense prose, exact paths, `file:line`
anchors, exact commands — no filler):

```markdown
# <Project> — Session Handoff (<YYYY-MM-DD>)

Read this first in a fresh context. <Supersedes line if applicable.>

## What this is (identity — non-negotiable)
One paragraph: what the app is, the constraints every decision bends to
(offline/single-file/no-build/etc.), and what it is NOT.

## Current task — exact resume point
What was mid-flight when the session ended. The precise next action ("implement X
in <file>, pattern at <file:line>"), what is half-done, what must NOT be redone.

## State: validated vs unvalidated
What passed which gates (syntax/probe/visual/tests — name them and their results).
What was written but NOT yet validated. What is known broken.

## The method (how edits are validated here)
The gate chain / validation loop for this project, with exact commands.

## Key anchors
The files, functions, and line ranges that matter for the remaining work.
Grep anchors for anything too big to read end-to-end.

## What shipped this session
Bullet list, terse, with file paths.

## What's left (priority order)
Numbered; first entry = the very next task. Note blockers and open questions
awaiting the owner.

## Gotchas discovered this session
Environment quirks, traps, things that bit us and how they were solved
(exact error → exact fix). These are the most expensive facts to lose.

## Standing constraints / user rulings
Verbatim-ish rules the user laid down, with dates.

## Pointers
CLAUDE.md, BACKLOG/PLAN/JOURNAL, prior handoffs, related docs.
```

Length: as long as the state demands and no longer — typically 40–120 lines. Density
over brevity: cutting a load-bearing fact to save lines defeats the purpose.

## Step 4 — Sweep for unpersisted state

Before handing over the compact command, check for session artifacts that live only
in conversation:

- Durable gotchas or user rulings that belong in auto-memory → save them there too
  (per the memory rules: only what the repo can't record).
- Project journals/backlogs the project's conventions say to update → update them.
- Uncommitted work in a project that commits per cycle → note it in the handoff
  (commit only if the project's own rules say every cycle commits).

## Step 4b — Mine fable behavior BEFORE compaction destroys the evidence

Compaction strips the Agent tool-call parameters (the `model:` fields) that prove which
model did what — so persona mining must happen now, never after.

Cheap pre-check first: does this conversation contain senior-model work? Signals: Agent
launches with `model: "fable"`, a `/model fable` switch in the transcript, or agent types
the project pins to fable (e.g. a CLAUDE.md model hierarchy). If none, skip this step
with one line — do not run the miner on a conversation with nothing to mine.

If yes: Read `~/.claude/skills/rigorous-build/PERSONA-MINER.md` and execute
its embedded prompt against this conversation. **STAGE, NEVER MERGE** (user ruling
2026-07-05: multiple concurrent sessions race on SKILL.md — a compactor pass must not
mutate skill files). Write the qualifying candidates — full miner output format, with
evidence — to `~/.claude/skills/rigorous-build/_candidates/CANDIDATES_<yyyymmdd_hhmm>.md`
(create the folder if needed; note in the file which skill each candidate targets —
rigorous-build, rb-explore, or a future companion). Do NOT edit any SKILL.md. Merging
happens only later, in an interactive session, with explicit user approval per candidate.
Put a one-line result in the final message above the /compact command: "Persona miner:
N candidates staged to _candidates\<file>" or "Persona miner: NOTHING NEW."

## Step 5 — Kick off compaction

Final message: one short line saying which handoff file(s) were written (clickable
paths), then — as the **last line, alone, in a code block** — the command:

```
/compact Read <handoff path> first in the compacted context — it is the authoritative session state. Preserve: <one-line current task + the single most critical gotcha>.
```

The instructions after `/compact` steer the summarizer, so keep them to the two
things summaries lose most: where the authoritative handoff lives, and the exact
resume point. Do not bury the command under further prose — it must be the last
thing on screen so the user can submit it immediately.
