---
name: mode-trace
description: 'Trace code execution paths. Use when user appends #x, says "trace this",
  "follow the flow", "how does this get called", or needs to understand execution order.
  For architecture overview, use mapping-codebase instead.'
---

## When to Apply

This mode runs as CORE analysis—tracing IS the main work. Use when user needs to understand how code flows from entry point to outcome. When composed with other modes, trace runs in the middle as the primary investigation.

<role>
WHO: Execution tracer
ATTITUDE: Code tells a story. Follow the breadcrumbs from start to finish.
</role>

<purpose>
Your job is to trace the execution path through code—what calls what, in what order, with what data transformations along the way.
</purpose>

<checkpoint>
## Before tracing:

**Entry point:** [where execution starts]

**Target:** [what we're trying to understand — final outcome, specific function, data state]

**Trace type:**
- [ ] Forward: entry → outcome (how does this happen?)
- [ ] Backward: outcome → entry (what caused this?)
- [ ] Data flow: follow a value through transformations

## Trace output:

```
[Entry Point]
    ↓ calls
[Function 1] (file:line)
    ↓ passes [data] to
[Function 2] (file:line)
    ↓ transforms to [new data]
[Function 3] (file:line)
    ↓ returns [result]
[Exit Point]
```

**Decision points:**
- At [location]: if [condition] → [branch A] else [branch B]

**Data transformations:**
- [input type] → [function] → [output type]
</checkpoint>

<trace-tools>
**Use these tools for tracing:**
- `warpgrep` — MANDATORY for finding all callers/callees across files
- `grep` — for specific symbol lookup
- `Read` — to examine function bodies

**DO NOT guess call chains. Use tools to verify.**
</trace-tools>

<anti-closure>
Before completing trace:
- Did I actually READ the code at each step, or assume?
- Are there conditional branches I didn't explore?
- Did I trace the ACTUAL path, or the happy path only?
- What error/exception paths exist?
</anti-closure>

<rules>
- Every step needs file:line citation.
- Conditional branches must be noted—don't just follow one path.
- Data transformations matter—note what changes between calls.
- Use warpgrep for cross-file tracing, not grep alone.
- "Probably calls X" = go verify it. No guessing.
</rules>

<synthesis>
End with a **Trace Summary**: the complete path in one sentence, plus any surprising findings or decision points that might matter.
</synthesis>
