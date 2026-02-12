# BRIDGE

Connect to another domain where this problem is already solved.

## Injection Point
phase-0 — Add analogical search before generating solutions

## When to use
The task needs **cross-domain import** — the problem is unfamiliar in its own domain but its SHAPE has been solved elsewhere. Importing a solution from another field would produce better results than domain-native thinking.

Do NOT use when the problem is well-understood in its own domain. Analogy adds indirection without value.

## Phases to Add

<phase name="Bridge-Search">
  <instruction>What type of problem is this, abstractly? Where else has this shape appeared? Find 2-3 domains where similar problems were solved. Could be other industries, nature, history, other codebases, etc.</instruction>
  <output>
    **Problem shape:** [Abstract description—e.g., "coordination without central authority"]
    **Solved elsewhere:**
    - [Domain 1]: solved via [approach]
    - [Domain 2]: solved via [approach]
    - [Domain 3]: solved via [approach]
  </output>
</phase>

<phase name="Bridge-Import">
  <instruction>Which solution translates best? What would need to adapt? Import the approach and modify for current context.</instruction>
  <output>
    **Best bridge:** [Domain] → [Current problem]
    **Translation:** [How their solution maps to your situation]
    **Adaptation needed:** [What changes for your context]
    **Imported solution:** [The approach, translated]
  </output>
</phase>

## Constraints
- At least 2 bridge domains before picking
- Bridges must be to genuinely different domains, not just similar products
- Translation step is mandatory—don't just say "do what they did"
