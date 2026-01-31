# FLIP

Invert, negate, or reverse to reveal what straight-ahead thinking misses.

## Injection Point
phase-0 — Add inversion before any recommendation phase

## Trigger Keywords
"what if", "opposite", "wrong", "bad idea", "shouldn't", "devil's advocate", "steelman", "premortem", "what could go wrong", "risks", "downsides", "argue against"

## Phases to Add

<phase name="Flip">
  <instruction>Invert the core question. "Should I X?" → "What makes X catastrophically wrong?" "How to Y?" → "How to guarantee Y fails?" "Is A good?" → "Argue A is terrible."</instruction>
  <output>
    **Flipped question:** [The inversion]
    **What the flip reveals:** [3-5 insights straight-ahead thinking missed]
  </output>
</phase>

<phase name="Integrate">
  <instruction>Return to original question. What changes given the flip? What do you now see that you didn't before?</instruction>
  <output>
    **Pre-flip answer:** [What you would have said]
    **Post-flip answer:** [Adjusted answer]
    **Delta:** [What changed and why]
  </output>
</phase>

## Constraints
- Flip must be genuine inversion, not softened ("some risks" ≠ flip)
- Minimum 3 flip insights—if fewer, flip wasn't aggressive enough
- Flip comes BEFORE recommendation, not after
