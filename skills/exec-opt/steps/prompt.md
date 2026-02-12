---
consumes: [depth-probe]
produces: [optimized-prompt]
---
## Step 2: Optimized Prompt

The executor has ZERO context. Everything they need is in the prompt or it doesn't exist.

### Format

```
STANCE: [WHO — stance, not job title. Names how this person SEES.]
ATTITUDE: [Belief controversial to dissenters + concrete consequence.]

Your job is [depth probe `reframing` VERBATIM].

FLOW: [PHASE1] → [PHASE2] → ...

**[Phase Name]**
[Imperative instruction. 1-3 sentences. Specific counts.]
Output: [Exact format — columns, rows, structure]

CONSTRAINTS:
- [Hard rules with values]
- [Each depth probe shallow_spot]
- [Lens constraints if active]
```

### WHO/ATTITUDE — 3 rules

1. **WHO names the stance**, not the job. Not "security engineer" — the cognitive bias they bring.
2. **ATTITUDE states a belief controversial to dissenters** with a concrete consequence. Has an enemy.
3. **Derive from depth_probe's `thinking_required` field.** Extract the cognitive mode needed.

### Depth probe transfer (MECHANICAL)

| Probe field | Goes to | Rule |
|------------|---------|------|
| `reframing` | "Your job is" | VERBATIM. If "framing is correct", restate as deliverable. |
| `thinking_required` | STANCE/ATTITUDE | Extract cognitive mode → stance + controversial belief. |
| `shallow_spots` | CONSTRAINTS | EACH → `[Phase X] must address [spot]. Hand-waving = violation.` |
| `missing_dimensions` | CONSTRAINT or phase | Hard rule → constraint. Needs explanation → phase instruction. |
| `process_critique` | CONSTRAINT or phase | Method fix → constraint. Structural fix → phase instruction. |

**Every finding gets a home.** Count: N findings, N placements. Mismatch = dropped something.

### Lens inflection

When a lens was selected in Step 1b, it inflects the ENTIRE prompt.
→ Read and apply: `references/lens-inflection.md`

### Structural check

- [ ] WHO names stance not job?
- [ ] Reframing used verbatim?
- [ ] All shallow_spots mapped to constraints?

A failure: fix before proceeding.
