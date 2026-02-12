# COMPOSE

Synthesize — build a new thing from the pieces you've analyzed.

## Injection Point
phase-last — Add synthesis after all analytical phases complete

## When to use
The task needs **construction** — analysis has produced pieces (comparisons, critiques, inversions, stress tests) that need to become something new. Claude's default is to hand back decomposed pieces without reassembling them.

Do NOT use when the deliverable IS the analysis. If the user wants a comparison table, the table is the output — don't synthesize it into a recommendation they didn't ask for.

## Phases to Add

<phase name="Compose">
  <instruction>Review all prior phase outputs. What new thing emerges from combining them? Don't summarize — synthesize. The output should contain ideas that weren't in any single prior phase.</instruction>
  <output>
    **Synthesis:** [The new thing — framework, recommendation, design, or insight that emerges from combining prior phases]
    **What's new here:** [What this adds beyond restating prior phases]
  </output>
</phase>

## Constraints
- Synthesis must contain at least one idea not present in any prior phase
- "Summary of above" is not composition — it must COMBINE, not RESTATE
- If nothing new emerges, say so — forced synthesis is worse than honest analysis
