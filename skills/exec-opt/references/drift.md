# DRIFT

Project forward — how does this change over time? What dynamics are running?

## Injection Point
phase-0 — Add temporal projection before recommendations

## When to use
The task needs **temporal reasoning** — the answer depends on dynamics, feedback loops, compounding effects, or decay. Claude's default is snapshot analysis: what's true NOW. DRIFT forces: what's true in 6 months? What feedback loops are running?

Do NOT use for static analysis or one-time decisions with no temporal dimension.

## Phases to Add

<phase name="Drift-Map">
  <instruction>Identify what changes over time. What compounds? What decays? What feedback loops are running (virtuous or vicious)? What phase transitions could occur — tipping points where the system behaves differently?</instruction>
  <output>
    **Compounding:** [What gets stronger/bigger over time]
    **Decaying:** [What erodes, becomes stale, loses value]
    **Feedback loops:** [Self-reinforcing dynamics, positive or negative]
    **Phase transitions:** [Tipping points where behavior changes qualitatively]
  </output>
</phase>

<phase name="Drift-Adjust">
  <instruction>Given the dynamics mapped above, how does this change the recommendation? What's optimal now but wrong in 12 months? What's suboptimal now but compounds into the right answer?</instruction>
  <output>
    **Static answer:** [What you'd recommend ignoring time]
    **Time-adjusted answer:** [What you recommend accounting for drift]
    **Key timing:** [When the answer changes, and what triggers the shift]
  </output>
</phase>

## Constraints
- At least one feedback loop identified — if none exist, DRIFT doesn't apply
- Phase transitions must be specific ("when X reaches Y") not vague ("eventually")
- Don't confuse uncertainty with dynamics — "I don't know what'll happen" isn't drift analysis
