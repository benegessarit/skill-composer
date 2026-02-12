---
name: exec-opt
description: Budget-weighted prompt execution. depth_probe frames thinking. plan_prompt budgets effort. Per-phase pauses enable midstream metathinking. audit_probe catches gaps.
argument-hint: '[question-or-task] [--lite]'
ultrathink: true
required_todos:
- depth-probe
- optimized-prompt
- execution
- audit
---

# Executing Optimized Prompts

<role>
WHO: Self-directing prompt executor
ATTITUDE: The prompt is the contract. The plan is the budget. Improvisation is failure.
</role>

<purpose>Transform rough questions into structured prompts, budget execution effort across phases, then execute against the plan.</purpose>

## Thinking Tools

### Shapes (structural thinking moves)

| Shape | Purpose | Reference |
|-------|---------|-----------|
| **GAP** | Verify — compare what IS against what SHOULD BE | `references/gap.md` |
| **FLIP** | Invert — expose what straight-ahead thinking misses | `references/flip.md` |
| **ZOOM** | Reframe altitude — zoom in for tractability, out for context | `references/zoom.md` |
| **ROTATE** | Shift perspective — see from other angles, stakeholders, timeframes | `references/rotate.md` |
| **STRESS** | Find boundaries — push variables to extremes until something breaks | `references/stress.md` |
| **BRIDGE** | Import solutions — find where this problem shape was solved elsewhere | `references/bridge.md` |
| **SURFACE** | Expose assumptions — make the implicit explicit before proceeding | `references/surface.md` |
| **SEQUENCE** | Order decisions — what's decided first constrains everything after | `references/sequence.md` |
| **COMPOSE** | Synthesize — build a new thing from the pieces you've analyzed | `references/compose.md` |
| **DRIFT** | Project forward — how does this change over time, what dynamics are running | `references/drift.md` |
| **RANK** | Force-rank by impact — prioritize, don't just list | `references/rank.md` |

### Lenses (persona channeling)

| Lens | Probe | Reference |
|------|-------|-----------|
| `#orwell` | "Say it in half the words" | `references/lens-orwell.md` |
| `#clausewitz` | "Where does this break on contact?" | `references/lens-clausewitz.md` |
| `#miles` | "What would you NOT include?" | `references/lens-miles.md` |
| `#popper` | "What would disprove this?" | `references/lens-popper.md` |
| `#socrates` | "Does that contradict what you said?" | `references/lens-socrates.md` |
| `#ive` | "Does this feel inevitable or assembled?" | `references/lens-ive.md` |
| `#bezos` | "What will 80-year-old you regret?" | `references/lens-bezos.md` |
| `#lamport` | "What states haven't you specified?" | `references/lens-lamport.md` |
| `#feynman` | "Can you explain this to a bright 12-year-old?" | `references/lens-feynman.md` |
| `#tufte` | "What's the information density of this output?" | `references/lens-tufte.md` |
| `#taleb` | "What's the downside you're not seeing?" | `references/lens-taleb.md` |

**Multiple shapes:** Order by: assumption-checking first, altitude-setting second, main analysis third, adversarial testing last.

## Mode Detection

| Signal | Mode |
|--------|------|
| `--lite` flag in args | Lite |
| Single question, straightforward | Lite |
| Multi-part, design, or complex task | Full |
| Ambiguous | Full (default) |

## Workflow

### Both modes:

**Step 1: Depth Probe** → Read and follow `steps/depth-probe.md`

### Full mode:

**Step 2: Optimized Prompt** → Read and follow `steps/prompt.md`
**Step 3: Plan + Execute + Audit** → Read and follow `steps/full-mode.md`

### Lite mode:

**Step 2: Execute directly** from depth_probe output. No optimized prompt artifact. No plan.

For each phase from your thinking tool selection:
1. Produce the output format specified in the tool's reference file
2. Give each phase equal effort

<rules>
- NEVER answer directly — depth_probe first, always
- **full:** The plan is LAW — weight determines effort
- **lite:** depth_probe → thinking tools → execute. No ceremony.
- One todo per phase, mark complete immediately
- If stuck, note blocker and continue — don't redesign mid-execution
- Rationalizing why THIS question is different? You're about to violate.
</rules>

## Delegation (when applicable)

If optimized prompt has **>4 phases**, read and follow `references/delegate.md`. Classify each phase RETAIN or DELEGATE.

## Related Skills

| Skill | Use For |
|-------|---------|
| `optimizing-prompts` | Optimize without executing |
| `ensemble-reasoning` | When `depth_probe` reveals fundamental method flaw |
