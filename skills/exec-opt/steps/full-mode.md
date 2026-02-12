---
consumes: [optimized-prompt]
produces: [execution, audit]
---
## Step 3: Plan + Execute + Audit

### 3a. Plan (plan_prompt)

Call `mcp__reasoning-mcp__plan_prompt(optimized_prompt="<your full optimized prompt text>")`.

If unavailable via direct call, use `mcp__gateway__call_mcp_tool(mcp_name="reasoning-mcp", tool_name="plan_prompt", arguments={...})`.

Follow the returned prompt. Allocate 100 weight points:
- No two phases get the same weight
- Highest weight ≥ 3x lowest weight
- weight ≥ 30 → "deep", 15-29 → "medium", < 15 → "shallow"
- `produces` = exact output format, not "results" or "analysis"
- `skip_if` forces you to argue against each phase's necessity

#### Lens test fields (when lenses active)

Add `[lens]_test` field to relevant phases:

| Lens | Test field |
|------|------------|
| #ive | `"ive_test": "What makes this output feel assembled rather than inevitable?"` |
| #popper | `"popper_test": "What evidence would invalidate this recommendation?"` |
| #socrates | `"socrates_test": "What does this contradict from Phase 1?"` |
| #lamport | `"lamport_test": "What states are unspecified?"` |

Validate: call `plan_prompt` again with `result=<your plan JSON>`. Fix flagged errors, don't redesign.

**The plan is now the execution contract.**

### 3b. Execute

Execute from the **plan**, not the original prompt.

For each phase in plan order:
1. Read `produces` — that's your deliverable
2. Respect depth: **deep** (≥30) = full analysis, evidence. **medium** (15-29) = solid, no hand-waving. **shallow** (<15) = 2-3 sentences.
3. Check `depends_on` — prerequisite outputs must exist
4. Check `skip_if` — if met, skip with one-line note
5. Produce the exact output format from `produces`

#### Per-phase pause (weight ≥ 15)

After completing any phase with weight ≥ 15, call `pause(phase_completed="PhaseName")`.

Reflect:
- What did this phase reveal that wasn't in the plan?
- Does the next phase still make sense given what I learned?
- Should remaining phases change?

If `next_phase_still_valid: false` — rewrite the next phase's instruction or skip with a note.

### 3c. Audit (audit_probe)

Pick two DIFFERENT cognitive frames:
- `execution_frame`: the primary mode you used (analysis, comparison, recommendation, decomposition)
- `audit_frame`: a DIFFERENT mode (synthesis, pre-mortem, inversion, integration)

Same-frame review is an echo chamber.

Call `mcp__reasoning-mcp__audit_probe(execution_frame="...", audit_frame="...", result=<JSON>)`.

Required JSON:
```json
{
  "execution_summary": "2-3 sentence summary of what you produced",
  "gaps": "What did the analysis miss, skip, or assume?",
  "vulnerability": "Weakest claim — what breaks first?",
  "revision": "Specific fix — 'add X to phase Y', not 'could be better'"
}
```

Apply revisions: gaps fixable in 1-2 sentences → fix inline. Vulnerability changes conclusion → say so. Revision → apply or state why not.

One pass. Fix what matters, flag what you can't, move on.

#### Subagent delegation (>6K tokens of output)

When execution output is large, delegate audit to a subagent. Write output to `/tmp/exec-opt-audit-input.md`, spawn with `subagent_type: "general-purpose"`, include: depth_probe reframing, pause insights, key constraints, frame pair. Read result and apply.
