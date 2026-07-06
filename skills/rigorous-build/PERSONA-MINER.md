# Persona Miner — paste this into any conversation to harvest fable behavior

Usage: paste the block below into a conversation where senior-model (fable) work happened —
a build, a review, a de-risk, agent reports. It extracts transferable behaviors and offers to
merge them into the rigorous-build skill. Mine BEFORE compacting — compaction usually destroys
the Agent tool-call parameters that prove which model did the work.

---

```
You are auditing THIS conversation for transferable senior-engineer behavior.

Context: I maintain a skill file — ~/.claude/skills/rigorous-build/SKILL.md —
that encodes the "fable methodology": the disciplined build/review behavior of my strongest
model (fable), so that other models running the skill reproduce its results. Fable's work may
appear here as my own turns or as subagent reports quoted in the conversation. Your job: mine
this conversation for behaviors worth encoding.

Step 1 — Read the skill file first (Read tool). You are looking for what is NOT already in it.
If you cannot read it, say so and mark your output UNDEDUPED instead of guessing.

Step 2 — Re-scan this conversation for senior-grade moments. FABLE-ONLY RULE: only moments
produced by fable-attributed work qualify — attribute (Step 2b) BEFORE you qualify; the skill
learns from fable exclusively. Qualifying signals:
- A premise from the task/plan was tested against the real code/data and corrected or rejected
- A failure mode was caught BEFORE shipping — especially a plausible-but-WRONG output a user
  would have trusted and acted on
- Scope was cut, refused, or deferred to protect correctness or trust, with the reasoning stated
- A verdict/answer was worded to claim exactly what the evidence supports, no more
- Uncertainty was made a first-class result (indeterminate/unknown) instead of a guess
- Tests/fixtures were chosen to EXPOSE specific wrong answers (incl. a positive control),
  not to confirm success
- New code was shaped to feed an existing pipeline instead of forking a parallel path
- Untrusted input got explicit caps/bounds/abort rules; degradation was loud (a notes/manifest
  of what was skipped) instead of silent
- The model built its own testability (exposed internals, mock counterpart) because the real
  environment was unavailable
- Anything else where the model generated structure (plans, tables, decision rules) that a
  weaker model would have skipped — and that structure changed the outcome

Step 2b — Attribute provenance for each candidate moment. Determine WHICH model produced it
using ONLY visible evidence, in this priority:
  (a) the launching Agent tool call's explicit `model:` parameter (join the agent's report
      back to its launch by description/label);
  (b) `/model` command output lines in the conversation ("Set model to ...") — these mark the
      main loop's model from that point onward;
  (c) the agent type's definition file — read `.claude/agents/<type>.md` frontmatter `model:`;
  (d) the project's documented model hierarchy (e.g. a CLAUDE.md role→model table).
NEVER infer the model from output style or quality — "looks senior, must be fable" is circular
and poisons the dataset. If the chain is broken (e.g. post-compaction), tag UNKNOWN.
GATE: only FABLE-attributed moments proceed to Step 3. OTHER-MODEL and UNKNOWN are excluded —
unprovable is treated as not-fable. Report exclusions in one line (count + reason), no more.

Step 3 — For each qualifying moment (MAX 5, ranked by impact), emit exactly:
- Name: 3-6 words
- Provenance: FABLE (required — non-fable never reaches this step), with the specific
  evidence (e.g. "Agent call passed model:fable" / "session set to Fable 5 at /model")
- Moment: 1-2 sentences on what actually happened HERE (cite the artifact/file/decision)
- Rule: the generalized imperative, ≤2 sentences, written for a build/review loop
- Skill section: where it belongs (Stance / Self-interrogation / Ground / Backup / Build /
  Integrity / Validate / Junior-model table / Document)
- Junior-model form: the same rule as a CHECKABLE OBLIGATION — an artifact or gate a
  compliant model must produce (e.g. "report must contain a premise-check table w/ file:line")

Step 4 — Honesty gates:
- Already covered by the skill → drop it, or emit "SHARPEN: <existing bullet> → <sharper wording>"
- Nothing qualifies → output exactly: NOTHING NEW — skill already covers what this session
  demonstrated. Do not pad.
- Project-specific facts (paths, function names, app behavior) are NOT rules — generalize
  or discard them (they belong in that project's memory, not the skill).
- Fable-only is absolute: OTHER-MODEL and UNKNOWN moments are NEVER merged into the skill.
  If a non-fable agent showed senior behavior under an obligation-style brief, you may note
  it in ONE line as VALIDATION (evidence the junior-model table is working) — telemetry
  only, never a rule.

Step 5 — Stop after the extraction and show me the candidates. If I reply "merge": back up
SKILL.md to _archive/SKILL_backup_<yyyymmdd>_<topic>.md first, apply the additions (prefer
sharpening an existing bullet over appending a new one; keep the file under ~260 lines — a
bloated skill stops being read), and show me the diff.
```
