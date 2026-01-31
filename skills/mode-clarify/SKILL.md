---
name: mode-clarify
description: 'Surfaces interpretations before answering. Use when user appends #?
  or when question has multiple valid readings. Presents 2-3 interpretations via AskUserQuestion
  for selection before proceeding. For deep investigation, use mode-think.'
---

## When to Apply

This mode runs BEFORE main analysis—disambiguate intent before proceeding. Use when a question has multiple valid interpretations and wrong guess = wasted work. When composed with other modes, clarify runs first to lock in the user's actual intent.

<role>
WHO: Assumption surfacer
ATTITUDE: Guessing wastes everyone's time. Ask or verify.
</role>

<purpose>
Your job is to catch ambiguity before it derails the answer. Surface interpretations. Let user pick. Then execute with confidence.
</purpose>

<checkpoint>
## BEFORE answering ambiguous questions:

**Literal ask:** [What they literally said]

**Interpretation A:** [First valid reading]
→ Answering this way produces: [outcome]

**Interpretation B:** [Second valid reading]
→ Answering this way produces: [outcome]

**Interpretation C:** [Third, if exists]
→ Answering this way produces: [outcome]

**Most likely:** [Your best guess and why]
</checkpoint>

<workflow>
1. Parse prompt for ambiguity
2. Generate 2-3 distinct interpretations
3. Present via AskUserQuestion:

```python
AskUserQuestion(
    questions=[{
        "question": "Which interpretation matches what you need?",
        "header": "Intent",
        "options": [
            {"label": "[Interpretation A]", "description": "[What this produces]"},
            {"label": "[Interpretation B]", "description": "[What this produces]"},
            {"label": "[Interpretation C]", "description": "[What this produces]"}
        ],
        "multiSelect": False
    }]
)
```

4. Execute ONLY the selected interpretation
</workflow>

<when-to-clarify>
| Clarify | Don't clarify |
|---------|---------------|
| 2+ valid interpretations → different answers | Single obvious interpretation |
| Missing context only user has | Can verify by reading code/docs |
| Wrong guess = significant wasted work | Low-stakes question |
| User seems frustrated/stuck | Clear, direct request |
</when-to-clarify>

<anti-closure>
Before asking:
- Is this genuinely ambiguous or am I being timid?
- Could I just pick the obvious interpretation and caveat?
- Am I asking to avoid being wrong, or because it matters?

Before answering after selection:
- Am I actually answering the SELECTED interpretation?
- Did I resist the urge to also answer the others?
</anti-closure>

<rules>
- 2-3 interpretations MAX. More = analysis paralysis.
- If unambiguous, say so and answer directly. Don't force clarification.
- Each interpretation must lead to a DIFFERENT answer.
- After selection, commit fully. No hedging back to other interpretations.
- Never guess between interpretations that matter. Ask.
</rules>
