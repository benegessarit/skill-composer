# SURFACE

Make the implicit explicit. Find what you don't know you don't know.

## Injection Point
phase-0 — Add surfacing phases BEFORE main analysis

## When to use
The task needs **assumption surfacing** — hidden assumptions are likely load-bearing. The question takes things for granted that might be wrong, or pre-filters options before asking.

Do NOT use when the assumptions are explicit and the framing is solid. Surfacing adds noise to well-framed questions.

## Phases to Add

<phase name="Surface-Implicit">
  <instruction>Before answering the actual question, surface what's UNSTATED. What is the question assuming is true? What context is taken for granted? What options were pre-filtered before asking? List 5+ implicit assumptions or pre-decisions.</instruction>
  <output>
    **Assumptions baked in:**
    - [Assumption 1] — assumed true, but is it?
    - [Assumption 2] — assumed true, but is it?
    - [...]

    **Pre-filtered options:**
    - [Option they didn't consider because...]

    **Missing context that would change the answer:**
    - [Context 1]
    - [Context 2]
  </output>
</phase>

<phase name="Surface-Challenge">
  <instruction>Pick the 2-3 most load-bearing assumptions. What happens if they're wrong? Does the question even make sense if assumption X is false?</instruction>
  <output>
    **If [Assumption 1] is wrong:** [consequence—question changes to...]
    **If [Assumption 2] is wrong:** [consequence—question changes to...]

    **Revised question (if needed):** [The better question to ask, given what surfaced]
  </output>
</phase>

## Constraints
- Minimum 5 implicit items surfaced before proceeding
- At least one must be a "pre-filtered option" (something dismissed before asking)
- If surfacing changes the question, answer the NEW question, not the original
