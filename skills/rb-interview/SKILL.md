---
name: rb-interview
description: Companion to rigorous-build for the self-assessment gate — when §0's self-interrogation leaves a real gap, rigorous-build offers this instead of guessing or barging into questions uninvited. Interrogates a decision, plan, or request, then grades the answers instead of accepting whatever comes back: when an answer is short, vague, or sloppy, say so explicitly, name the specific reason it's insufficient, and ask again for exactly what's missing. Also usable standalone — Use when the user types /rb-interview, says "grill me on this", "pressure-test this", "interview me on this", "make sure I've thought this through", or before committing to a nontrivial decision/plan where a thin answer now becomes an expensive wrong turn later.
---

# RB-Interview — don't accept a sloppy answer

Companion to `rigorous-build` for the requirement-gathering work-shape — the skill its
self-assessment gate offers when §0 leaves a real gap ("I've got a few questions that would
sharpen this — want me to ask them, or should we skip the interview and get building?"). Also
stands alone for pressure-testing any decision or plan before committing to it.

Two jobs, in order: ask the questions that expose gaps in a decision/plan/request, then
actually **grade** the answers instead of taking whatever comes back at face value. A short or
vague answer is a gap, not a resolved one — name it, say exactly why it's insufficient, and ask
again for the specific thing still missing.

## Through-line

Most requirement-gathering fails silently: ask a question, get a two-word answer, proceed as if
it settled things. This skill refuses that move. An answer only counts as resolved if it's
specific enough that someone else could act on it without guessing — otherwise call it out by
name and push back once before moving on. Don't stall forever either — this is a pressure test,
not an interrogation loop with no exit.

## Process

1. **Find the load-bearing unknowns.** Before asking anything, list the 2–5 things about this
   decision/plan/request that would change what gets built if the answer were different. Don't
   ask questions whose answer wouldn't actually change the outcome — that's stalling, not rigor.

2. **Ask pointed, specific questions — one pass.** All the genuinely load-bearing questions at
   once, not a drip-feed. Confirm every part of a multi-part ask gets addressed before moving on.

3. **Grade every answer before proceeding — this is the actual point of the skill.** For each
   answer, check: is it specific enough that two different people implementing from it would
   build the same thing?
   - If yes: say so in one line ("clear — proceeding") and move on. Don't grill what's already
     clear; that's not rigor, it's noise.
   - If no: name exactly which answer is insufficient and why (*"'make it nice' doesn't tell me
     what changes — nice compared to what, measured how?"*). State exactly what would make it
     sufficient (*"I need: which of these 3 metrics matters most, and what current number
     counts as 'bad'"*). Ask again, once, for that specific gap — don't just repeat the
     original question verbatim.
   - If the second answer is still too thin to act on: say so plainly and make the most
     defensible assumption explicit (*"proceeding with X since you didn't specify — flag if
     wrong"*) rather than silently guessing or stalling indefinitely.

4. **Offer the summary — don't force it.** Once every answer is graded, ask once, in one line:
   *"Want me to read back the settled picture before I ship, or good to go as-is?"*
   - **Ship as-is:** proceed straight to handoff. No summary printed, nothing re-explained.
   - **Read it back:** write the assembled picture as one cohesive statement of what will get
     built — not a re-print of the Q&A transcript. Writing it yourself is itself a check: it
     surfaces contradictions between answers that each graded fine individually but don't cohere
     once stated as a whole, which you'll explain to yourself more precisely than the user's
     answers did. Then ask once: *"Match what you meant, or is something off?"*
     - **Agree:** proceed to handoff.
     - **Disagree:** reopen ONLY the specific disputed point(s) — grade the new answer per step
       3, then re-offer this same choice. Never re-ask or re-summarize a point that's already
       settled; the loop closes on the delta, not a restart.

## What "sloppy" looks like — call these out by name

- A vague qualifier with no referent: "make it better / nicer / cleaner / more professional"
  with nothing named to compare against.
- Answering a different, easier question than the one actually asked.
- A one-word answer to a question with real branches ("yes" to "which of these three...").
- Deferring a decision that blocks the next step ("whatever you think") on something only the
  user can actually judge — their budget, their brand, their users, their risk tolerance.

## Output shape

```
## Interview: <one-line subject>

1. <question> — <question> — ...  (numbered, load-bearing only)

### Answers graded
- ✓ <question>: specific enough — proceeding as stated
- ✗ <question>: too thin — <exactly what's missing> — <what I need instead>

### Settled vs. still assumed
<what's now locked in, and any assumption being made explicit because a gap didn't close>

### Confirmation
Want me to read back the settled picture before I ship, or good to go as-is?
<if read back requested: one cohesive paragraph, then "Match what you meant, or is something off?">
```

## Handoff back to rigorous-build

Once every load-bearing unknown is either resolved or explicitly assumed, and the confirmation
step is resolved (shipped as-is, or the summary was agreed to), hand the settled answers back to
`rigorous-build` (or whichever skill triggered this) — this skill's job ends at a clear, graded
set of answers, not at building anything itself.

## Definition of done

- [ ] Every load-bearing unknown was asked about, not guessed
- [ ] Every answer was graded, not just accepted
- [ ] Any insufficient answer was named specifically, with what would fix it
- [ ] Remaining assumptions (if any) are stated explicitly, not silent
- [ ] Summary offered once, never forced; any disagreement reopened only the disputed point(s), not the whole interview
