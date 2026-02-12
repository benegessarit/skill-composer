# LAMPORT

What states haven't you specified?

## Probe
"What states haven't you specified?"

## Phases to Add

<phase name="Dependency-Trace">
  <instruction>Read the plan/proposal as a state machine. For each component: what does it read? What does it write? What must be true BEFORE it runs? What becomes true AFTER? List 5+ unspecified state dependencies.</instruction>
  <output>
    **Missing preconditions:**
    - [Component X] assumes [state Y] but plan doesn't establish Y
    - [...]

    **Missing postconditions:**
    - After [X] runs, [Y] is now in state [Z]—who handles that?
    - [...]

    **Unspecified orderings:**
    - Plan doesn't say whether [A] or [B] happens first—matters because [...]
  </output>
</phase>

<phase name="Blast-Radius">
  <instruction>Pick the 3 most dangerous unspecified states. For each: what happens if this state is wrong? What components fail? How far does the failure propagate?</instruction>
  <output>
    **Unspecified state 1:** [What's missing]
    → **If wrong:** [What fails]
    → **Propagates to:** [What else breaks downstream]

    **Unspecified state 2:** [...]
    **Unspecified state 3:** [...]
  </output>
</phase>

## Constraints
- Minimum 5 unspecified states/orderings before proceeding
- "The plan doesn't mention X" is not enough—state what BREAKS if X is wrong
- Think in state transitions: preconditions, postconditions, invariants
- If everything is specified, say so—don't manufacture gaps
