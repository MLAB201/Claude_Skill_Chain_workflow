---
name: counsel-of-5
description: Convene a "Counsel of 5" — five distinct expert personas independently analyze a problem, surface disagreements, then synthesize one clear recommendation. Use when the user types /counsel-of-5, says "counsel of 5", "convene the counsel", "get 5 opinions", or asks for multi-perspective deliberation on a hard decision, design, tradeoff, or review.
---

# Counsel of 5

Convene five expert personas to deliberate on the user's question, then deliver one synthesized verdict. The goal is genuine viewpoint diversity — not five voices agreeing, but five lenses that catch what a single pass misses.

## Process

1. **Frame the question.** Restate the problem in one sentence so the panel is anchored. If it's underspecified, state the assumption you're deliberating under (don't stall asking — make the reasonable call).

2. **Pick the panel.** Choose 5 personas whose expertise is *relevant to this specific question*. Each must have a distinct lens that can produce real disagreement. Don't pick five flavors of the same role.
   - Default panel for software/architecture decisions: **Pragmatist** (ship it, minimize complexity), **Architect** (long-term structure, coupling), **Security/Risk** (failure & attack surface), **Operator/SRE** (runtime, observability, on-call cost), **Skeptic/Devil's-Advocate** (attacks the premise itself).
   - Swap in domain experts when the question warrants (e.g. Networking, DBA, Frontend/UX, Cost/FinOps, Performance, Compliance, Data Scientist). Name each persona by role.

3. **Independent takes.** For each persona, give 2–5 tight sentences: their position, the key reason, and the main thing they'd refuse to accept. Persona voices must be allowed to *conflict*. No hedging into consensus prematurely.

4. **Crossfire.** Call out the 1–3 sharpest disagreements between members and what each tradeoff actually hinges on. This is the highest-value section — be specific about *what fact or priority would tip the decision*.

5. **Verdict.** Synthesize into one clear recommendation. State: the call, the 1–2 reasons that won, which dissent you're consciously overriding and why, and any condition that would flip the decision. If the panel genuinely can't converge, say so and name what information would break the tie.

## Output format

```
## Counsel of 5 — <one-line question>

**Panel:** Role A · Role B · Role C · Role D · Role E

### Takes
- **Role A:** …
- **Role B:** …
- **Role C:** …
- **Role D:** …
- **Role E:** …

### Crossfire
- <disagreement 1 — what it hinges on>
- <disagreement 2 — …>

### Verdict
<the call, the winning reasons, the overridden dissent, the flip condition>
```

## Rules

- Five personas, no more, no less. Each must earn its seat with a distinct lens.
- Real tension > false harmony. If all five agree instantly, the panel was chosen badly — repick.
- Keep each take terse. The value is breadth of angle, not length.
- The verdict is mandatory and must be decisive (or explicitly declare a tie + the missing fact).
- Honor any active response-style mode (e.g. caveman) in surrounding prose, but keep the section structure above.
- Stay grounded in the actual codebase/context when the question is about this project — personas cite real files/constraints, not generic platitudes.
