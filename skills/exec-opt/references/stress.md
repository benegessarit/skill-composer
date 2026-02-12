# STRESS

Push to extremes until something breaks. Find boundaries and failure modes.

## Injection Point
phase-0 — Add stress-testing before finalizing

## When to use
The task needs **boundary finding** — the solution must work at extremes, not just the happy path. Variables could be pushed to 10x, zero, or hostile conditions to find where things break.

Do NOT use when the task is conceptual or theoretical. Stress-testing adds nothing to pure reasoning tasks.

## Phases to Add

<phase name="Stress-Apply">
  <instruction>Identify the key variables/assumptions. Push each to extreme: 10x scale, zero resources, hostile actors, time crunch, everything fails at once. What breaks first?</instruction>
  <output>
    **Variables stressed:**
    - [Variable 1] at extreme: [what happens]
    - [Variable 2] at extreme: [what happens]
    - [Variable 3] at extreme: [what happens]

    **First break point:** [What fails first and why]
  </output>
</phase>

<phase name="Stress-Learn">
  <instruction>What does the breaking point reveal? Is this an acceptable boundary or a fatal flaw? What would make it more robust?</instruction>
  <output>
    **The boundary:** [Where it breaks]
    **Acceptable?** [Yes—design for this limit / No—must fix]
    **Robustness option:** [What would push the boundary further, if needed]
  </output>
</phase>

## Constraints
- Stress at least 2 different variables
- Breaking points must be specific, not vague ("might fail")
- Don't catastrophize—find ACTUAL boundaries, not imagined ones
