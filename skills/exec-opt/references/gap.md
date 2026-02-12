# GAP

Find mismatches between things that should match. The verification primitive.

## Injection Point
phase-0 — Add gap-detection phases to the optimized prompt

## When to use
The task needs **verification** — comparing what IS against what SHOULD BE. Two things that should match: claim vs evidence, spec vs implementation, expectation vs reality.

Do NOT use when the task is generative, not comparative.

## Phases to Add

<phase name="Gap-Detect">
  <instruction>Identify the two things being compared. What SHOULD match? (Claim vs evidence, spec vs implementation, expectation vs reality, version A vs version B). List each pair explicitly.</instruction>
  <output>
    **Comparing:** [Thing A] vs [Thing B]
    **Should match on:** [dimensions where alignment is expected]
  </output>
</phase>

<phase name="Gap-Report">
  <instruction>For each dimension, check alignment. Report gaps with specifics—not "they differ" but "A says X, B says Y."</instruction>
  <output>
    | Dimension | A | B | Gap? |
    |-----------|---|---|------|
    [For each dimension]

    **Gaps found:** [list with specifics]
    **Verdict:** [ALIGNED / GAPS FOUND]
  </output>
</phase>

## Constraints
- Both sides of comparison must be explicit before checking
- Gaps require specifics, not just "mismatch detected"
- If no gaps found, say so—don't manufacture concerns
