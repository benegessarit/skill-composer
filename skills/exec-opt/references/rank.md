# RANK

Force-rank by impact — prioritize, don't just list.

## Injection Point
phase-last — Add ranking after analysis produces multiple findings

## When to use
The task needs **prioritization** — analysis has surfaced multiple items (risks, options, recommendations, findings) and the user needs to know which ones actually matter. Claude's default is to present N items with equal weight. RANK forces: which 2-3 of these are decisive?

Do NOT use when the user explicitly wants a complete list or when all items genuinely carry equal weight.

## Phases to Add

<phase name="Rank">
  <instruction>Take all items from prior phases. Force-rank by actual impact — not by how easy they are to articulate. Top 3 get full justification. The rest get one line. If you can't rank them, state the ranking criterion that's missing.</instruction>
  <output>
    **Ranking criterion:** [What "matters most" means for this task]
    **#1:** [Item] — [Why this is decisive, not just important]
    **#2:** [Item] — [Why this ranks here]
    **#3:** [Item] — [Why this ranks here]
    **The rest:** [One-line each, or "these don't matter compared to the top 3"]
  </output>
</phase>

## Constraints
- Must commit to a ranking — "all are important" is a cop-out
- Top item must be justified as #1, not just listed first
- If ranking is genuinely impossible, state the missing information that would enable it
