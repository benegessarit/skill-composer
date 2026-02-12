# SEQUENCE

Order decisions — what's decided first constrains everything after.

## Injection Point
phase-0 — Add decision ordering before any recommendation phase

## When to use
The task needs **decision sequencing** — there are multiple choices to make and their order matters. Deciding A before B changes the option space for B. Claude's default is to present choices in parallel when they're actually serial.

Do NOT use when decisions are genuinely independent. If ordering doesn't change the answer, SEQUENCE adds noise.

## Phases to Add

<phase name="Dependency Map">
  <instruction>List the decisions this task requires. For each pair, ask: does deciding X first change the options for Y? Draw the dependency order. Find the root decision — the one that constrains the most downstream choices.</instruction>
  <output>
    **Decisions:** [numbered list]
    **Dependencies:** [X must precede Y because...]
    **Root decision:** [The one to resolve first]
    **Forced order:** [Decision sequence]
  </output>
</phase>

<phase name="Sequential Resolution">
  <instruction>Resolve decisions in dependency order. After each, state how it narrows the remaining choices. If a later decision reveals the earlier one was wrong, say so.</instruction>
  <output>
    **Decision 1:** [choice + reasoning]
    **Narrowing effect:** [what this eliminates downstream]
    ...repeat for each decision in order...
  </output>
</phase>

## Constraints
- Minimum 2 decisions identified — if only 1, SEQUENCE doesn't apply
- Each decision must state what it constrains downstream
- "These are independent" is a valid conclusion — don't force false dependencies
