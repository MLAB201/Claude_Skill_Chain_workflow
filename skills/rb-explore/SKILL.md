---
name: rb-explore
description: Companion to rigorous-build for EXPLORING unknown systems — black boxes, undocumented devices, hidden rules, unfamiliar APIs/protocols, "figure out how this behaves" tasks. Use when the job is building a world model by experiment rather than shipping a change; when probing a system whose transition rules are not documented; when the user says "reverse engineer", "figure out the rule", "map its behavior", "probe it", or an agent must interact with something novel under a budget. Enforces: hypothesis ledger (predict before act), varied-context replication, held-out validation of the assembled model, cause-keyed predictive rules, coincidence fencing, and honest UNDETERMINED over elegant-but-wrong.
---

# RB-Explore — world-model discipline for unknown systems

Companion to `rigorous-build` (the constitution: evidence rule, integrity, honest
reporting all apply here). This manual governs the EXPLORE work-shape: a budget of
observations against a system whose rules you don't know. Provenance: every rule below
was mined from a controlled failure in RB-Lab experiment 4 (THE LOCK, 2026-07-05) —
see Web\RB-Lab\_grader\exp4\RESULTS.md.

Through-line: **an elegant rule that is wrong is the worst outcome** — strictly worse
than "rule not determined." A model fitted to all your observations has explained
nothing until it predicts observations it was not fitted to.

## The five laws

### 1. Hypothesis ledger — predict before you act
Unstructured poking is allowed only as a labeled opening phase. After it, every
observation you spend is logged BEFORE acting as: hypothesis under test → predicted
outcome → (then) observed outcome → verdict SUPPORTS / REFUTES / UNINFORMATIVE.
A prediction written after seeing the result is not a prediction.
*Why: the ledger is what separated the only honest report from two wrong ones.*

### 2. Varied-context replication — same conditions prove less than they feel
A finding is ESTABLISHED only when replicated under VARIED context: a different route
to the same visible state, a different point in the sequence, a different session/time.
Identical-condition repeats (e.g. always right after a reset) earn ESTABLISHED-NARROW
at best — every hidden variable was frozen, so agreement is expected even if hidden
state exists. Deliberately arrange the experiment that could EXPOSE hidden state:
reach the same visible state two different ways and apply the same action. If the
budget cannot arrange it, the whole-state premise is UNTESTED — say so; never write
"hidden state ruled out" from same-context repeats.
*Why: bare arm 1 ruled out hidden state from replications that all shared hidden
context — and built its entire model on that false floor. Scored 0.*

### 3. Hold-out gate — reserve budget to test the assembled model
Reserve a fixed slice of the observation budget (default ≥20%) as HOLD-OUT. Before
spending it: write down the assembled best rule AND its concrete predictions for the
held-out trials. Then run them and report predicted-vs-observed, verbatim. A rule that
merely retrodicts the observations it was fitted to is UNVALIDATED — perfect self-fit
is expected of overfitting and proves nothing. No self-consistency check can catch
overfit; only out-of-sample prediction can.
*Why: bare arm 2 produced a complete rule retrodicting all 15 of its own observations
(mechanically verified) that was wrong in every structural claim. It spent 15/15
observations fitting, 0 testing.*

### 4. Cause-keyed rules — predictive form or it isn't a rule
State every rule as an executable predictor: (visible state, action, context) → next
state. Classifying observations by their OUTCOMES ("when 2 lamps flip, X happens") is
description, not mechanism — it cannot predict and it smuggles the effect into the
trigger. If you catch yourself keying a rule to what happened rather than to what was
done and under what conditions, you have a taxonomy, not a model.
*Why: arm 1's outcome-classified "laws" fit everything and predicted nothing.*

### 5. Coincidence fencing — audit what your evidence shares
Before promoting any invariant, list the context its supporting observations SHARE
(sequence position, path, mode, timing). If they share unexamined context, tag it
SUPPORTED-COINCIDENT and, if budget allows, spend the discriminating observation.
Replication count alone never promotes a claim whose observations are correlated.
*Why: arm 3's only cross-state invariant (4/4 observations) was a lucky streak — every
observation had coincidentally sampled the same hidden mode.*

## Report contract (checkable obligations — brief-ready)

1. PREMISE CHECK — assumptions about the system (determinism, visible state = whole
   state, fixed action effects), each TESTED (with trial numbers) / UNTESTED. The
   whole-state premise requires a varied-context test (law 2) to be marked TESTED.
2. HYPOTHESIS LEDGER — per law 1, every observation, opening exploration labeled.
3. FINDINGS — three-state: ESTABLISHED (varied-context replication) /
   ESTABLISHED-NARROW or SUPPORTED-COINCIDENT (same-context only; shared context
   named) / SUPPORTED (single observation) / UNDETERMINED.
4. HOLD-OUT RESULTS — the assembled rule as written BEFORE the reserved trials, its
   predictions, the observed outcomes, and the honest hit rate. If the hold-out was
   not run (budget exhausted), the rule is reported as UNVALIDATED, in those words.
5. CALIBRATION — final claims worded to exactly what the evidence supports; RULED OUT
   list with trial numbers; UNDETERMINED list. Banned: "ruled out" from same-context
   repeats; presenting a fitted rule as validated; the word "probably" in a claim.
6. CUT LIST — what was not investigated and the budget reasoning.

## Definition of done
- [ ] Ledger complete — no unlabeled observation spends
- [ ] Whole-state premise given a varied-context test, or marked UNTESTED
- [ ] Every ESTABLISHED claim survived varied-context replication
- [ ] Hold-out reserved, predictions pre-written, hit rate reported (or UNVALIDATED)
- [ ] Rules in predictive cause-keyed form
- [ ] Shared-context audit done on every promoted invariant
- [ ] UNDETERMINED stated plainly where the budget could not decide

## Self-improvement
Mined like the parent skill: run PERSONA-MINER against exploration sessions; merge
rules here (not into rigorous-build) when the work-shape is exploration. Keep under
~150 lines; sharpen over append.
