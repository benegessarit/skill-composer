# Phase 0.5: Delegate

Classify each phase to keep large outputs OUT of main agent context.

## Decision Tree

For each phase, in order:

1. **Needs conversation context?** (user's situation, preferences, prior discussion) → **RETAIN**
2. **Output < 200 words?** → **RETAIN** (delegation overhead exceeds savings)
3. **Depends on prior phase?**
   - Dependency summarizable in < 100 words → **DELEGATE-SEQUENTIAL**
   - Too rich to summarize → **RETAIN**
4. **Independent of other delegatable phases?**
   - Other independent phases exist → **DELEGATE-PARALLEL**
   - Solo → **DELEGATE-SEQUENTIAL**

**Hard rules:**
- Never delegate the LAST phase (always synthesis)
- Max 4 delegated phases
- Never spend > 50 words classifying a single phase

## Classification Output

```xml
<delegation>
  <phase name="X" disposition="RETAIN" reason="needs user context"/>
  <phase name="Y" disposition="DELEGATE-PARALLEL" reason="self-contained enumeration"/>
  <phase name="Z" disposition="DELEGATE-SEQUENTIAL" depends_on="Y" reason="large output, injectable dependency"/>
</delegation>
```

## Subagent Prompt Template

Use `subagent_type: "general-purpose"` for all delegated phases.

```
You are executing one phase of a structured analysis.

## Your Task
[Phase's <instruction> verbatim]

## Required Output Format
[Phase's <output> verbatim]

[IF dependencies:]
## Context From Prior Phases
### [Phase Name]
[≤100-word summary written by main agent]

[IF <evaluate> exists:]
## Self-Check
Verify: [check]. If fail: [on_fail action].

## Rules
- Produce ONLY the specified format. No preamble.
- Use tools (search, web, files) if needed.
- Output must be self-contained.
```

## Execution & Synthesis

1. Launch DELEGATE-PARALLEL phases simultaneously (single message, multiple Task calls)
2. As each returns: write ≤100-word summary for downstream phases
3. Launch DELEGATE-SEQUENTIAL in dependency order with injected summaries
4. Execute RETAIN phases inline using summaries (not full outputs)
5. Assemble response: paste delegated outputs verbatim + retained outputs

**Write-through rule:** Subagent outputs go to the user response, not through main agent reasoning. Main agent holds ONLY summaries.

**Garbage handling:** Retry once with format reminder. If retry fails, main agent executes the phase.
