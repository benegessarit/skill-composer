# ZOOM

Change abstraction level—in for tractability, out for context.

## Injection Point
phase-0 — Restructure prompt to operate at right altitude

## Trigger Keywords
"break down", "step by step", "decompose", "big picture", "zoom out", "context", "specifically", "concretely", "abstractly", "first principles", "simplify", "details", "overview"

## Phases to Add

<phase name="Zoom-Calibrate">
  <instruction>Diagnose the current altitude problem. Is the question too abstract (paralysis, no actionable next step)? Or too concrete (lost in weeds, missing forest)? Pick zoom direction.</instruction>
  <output>
    **Current altitude:** [Too abstract / Too concrete / About right]
    **Zoom direction:** [IN (make tractable) / OUT (gain context) / NONE]
    **Target altitude:** [What level makes this answerable?]
  </output>
</phase>

<phase name="Zoom-Execute">
  <instruction>If zooming IN: break into smallest actionable piece, answer that. If zooming OUT: place in larger system, identify what category of problem this is, then answer. If NONE: proceed normally.</instruction>
  <output>
    **Zoomed frame:** [The reframed question at new altitude]
    **Answer at this altitude:** [The response]
    **Zoom back:** [How this connects to original level]
  </output>
</phase>

## Constraints
- Always state zoom direction explicitly before executing
- Zoomed answer must connect back to original question
- Don't zoom both directions—pick one
