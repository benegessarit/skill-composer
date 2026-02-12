# ZOOM

Change abstraction level—in for tractability, out for context.

## Injection Point
phase-0 — Restructure prompt to operate at right altitude

## When to use
The task needs **altitude correction** — the question is either too abstract to act on (paralysis, no next step) or too concrete to see the system (lost in weeds, missing forest).

Do NOT use when the question is already at the right altitude — concrete enough to act on, abstract enough to see context.

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
