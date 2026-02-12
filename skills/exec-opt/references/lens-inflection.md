# Lens Inflection Rules

When a lens fires, it doesn't add a checkbox — it **channels a persona**. The WHO/ATTITUDE shifts. Phases tilt. Constraints sharpen.

## Inflection Table

| Lens | WHO/ATTITUDE becomes | Phase injection | Constraint injection |
|------|---------------------|----------------|---------------------|
| **#ive** | `[domain] designer channeling Ive's inevitability standard` / `If it feels assembled, it is. Redesign until every element earns its place or delete it.` | Add **Inevitability Gate** (adversarial): "For each element in the design, remove it — does the output get worse or just different? If just different, cut it." Output: Table: Element \| Remove it? \| Worse or different? \| KEEP/CUT | `#ive: No element survives by default. Each earns its place or gets cut.` / `#ive: "It feels right" is not evidence. "Removing it breaks X" is evidence.` |
| **#popper** | `[domain] analyst who distrusts unfalsifiable claims` / `A recommendation without a kill condition is an opinion. State what would make you wrong.` | Every checkpoint phase adds: "For each recommendation, state the falsification condition — what evidence would make you retract it. No condition = no recommendation." | `#popper: Every claim states what would disprove it.` / `#popper: "X is best" → "X is best UNLESS [condition]."` |
| **#socrates** | `[domain] examiner who cross-examines own conclusions` / `Agreement between your phases is suspicious. If Phase 3 doesn't challenge Phase 1, you're confirming, not thinking.` | Add **Cross-Examination** (adversarial) after final phase: "Re-read Phase 1 output. Does your conclusion contradict any early claim? List contradictions. For each: which is right? Revise one." | `#socrates: Later phases MUST reference earlier outputs by name.` / `#socrates: If all phases agree, explain why that's not confirmation bias.` |
| **#lamport** | `[domain] specifier who treats unspecified states as bugs` / `You described the happy path. Now describe the other 6 paths you pretended don't exist.` | Add **State Enumeration** before any system/process description: "Enumerate ALL states. For each, list transitions and triggers. Unspecified transitions = bugs." Output: State table. | `#lamport: Every process includes a state table. Narrative = bug.` / `#lamport: "It shouldn't happen" is not a valid state.` |
| **#orwell** | Adds to ANY WHO's ATTITUDE: `...and say it in half the words.` | No phase injection — applies globally to output length | `#orwell: Word budget per phase = 50% of what feels natural. Cut until it hurts, then cut once more.` |
| **#clausewitz** | `[domain] strategist who plans for first contact failure` / `Plans break on contact. Show me where yours breaks.` | Add **Contact Failure** (adversarial): "For each recommendation, name the first thing that goes wrong when attempted in reality." | `#clausewitz: Each recommendation includes its first failure point.` |
| **#miles** | `[domain] editor channeling Miles Davis's silence` / `The notes you don't play matter more. What would you cut?` | Add **Subtraction Pass** after drafting: "Name 1 element to remove from the output. Remove it. If nothing can go, you haven't looked hard enough." | `#miles: After drafting, cut 1 element. Justify what remains by its absence.` |
| **#bezos** | No full inflection — modifies checkpoint phases | Checkpoints add: "For irreversible decisions, state the regret-minimization argument in one sentence." | `#bezos: Irreversible decisions need 2x the evidence of reversible ones.` |
| **#feynman** | `[domain] explainer who treats jargon as evidence of confusion` / `If you need a technical term, you haven't understood the idea yet. Explain the mechanism, not the label.` | Add **Feynman Test** after explanation phases: "Re-explain your key insight without domain-specific terminology. Use concrete analogies. If you can't, you're pattern-matching vocabulary, not understanding." | `#feynman: Every technical term gets a plain-language parenthetical.` / `#feynman: Core insight must be expressible in one sentence a non-expert understands.` |
| **#tufte** | `[domain] information designer channeling Tufte's density standard` / `Every paragraph is a failed table. Every table is a failed diagram. Find the highest-bandwidth format.` | Add **Format Audit** after drafting: "For each section, ask: would a table, matrix, decision tree, timeline, or worked example convey this faster than prose? Convert at least one section." | `#tufte: At least one section must use a non-prose format.` / `#tufte: 3+ paragraphs in a row = missed formatting opportunity.` |
| **#taleb** | `[domain] risk analyst who distrusts smooth predictions` / `Your analysis covers the expected cases. The world is decided by the unexpected ones.` | Add **Black Swan Scan** after risk/recommendation phases: "Name a scenario you haven't considered that would invalidate everything above. Not a known risk made worse — a qualitatively different kind of failure." | `#taleb: Every recommendation states what class of surprise would break it.` / `#taleb: "Low probability" is not reassurance. State consequence magnitude.` |

## Multiple lenses

- Max 2 active lenses per prompt (unless user explicitly stacks more)
- WHO/ATTITUDE: pick the dominant lens for the persona, weave the second into ATTITUDE
- Phase injections: both apply — order by SURFACE → ZOOM → main → FLIP/STRESS → GAP
- Constraints: all active lens constraints included

## Lens selection

Explicit `#lens` tags always activate. When no tag is present, select lenses based on the cognitive needs identified in Step 1c Step 1 — not by matching the question's domain to a lookup table.
