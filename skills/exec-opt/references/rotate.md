# ROTATE

View from a different angle—stakeholder, time, or frame.

## Injection Point
phase-0 — Add perspective-shift before synthesis

## When to use
The task needs **perspective shift** — multiple valid viewpoints exist and the answer depends on whose angle you take. Stakeholder differences, time horizons, or conceptual reframes would reveal blind spots.

Do NOT use when the task has a single clear framing and perspective doesn't change the answer.

## Phases to Add

<phase name="Rotate">
  <instruction>Identify current viewing angle (whose perspective? what timeframe? what frame?). Then rotate: pick 2-3 other angles that would see this differently. Could be stakeholders, time shifts, or conceptual reframes.</instruction>
  <output>
    **Current angle:** [Perspective/time/frame you're in]
    **Rotations:**
    - [Angle 2]: sees this as [how]
    - [Angle 3]: sees this as [how]
    - [Angle 4]: sees this as [how]
  </output>
</phase>

<phase name="Synthesize-Views">
  <instruction>What do the rotated views reveal that the original angle missed? What's true across all angles? What's only true from one?</instruction>
  <output>
    **Blind spots in original:** [What you couldn't see]
    **Invariant (true from all angles):** [What holds regardless]
    **Perspective-dependent:** [What changes based on angle]
  </output>
</phase>

## Constraints
- Name the current angle before rotating—can't rotate without knowing starting position
- Minimum 2 rotations, maximum 4
- At least one rotation should be uncomfortable or non-obvious
