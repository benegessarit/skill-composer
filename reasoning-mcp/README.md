# Reasoning MCP

MCP server for structured reasoning with enforced workflow stages.

## Installation

```bash
pip install reasoning-mcp
# or for development:
pip install -e .
```

## Usage

Add to Claude Code:

```bash
claude mcp add reasoning-mcp -- python -m reasoning_mcp
```

## Workflow

The MCP enforces a 4-stage reasoning workflow:

1. **begin_session** → Returns meta_analysis prompt
2. **submit_meta_analysis** → Returns scaffold selection prompt
3. **declare_scaffold** → Returns style prompt for first phase
4. **think** (per phase) → Returns prompt for next phase or completion

## Tools

### begin_session

Start a new reasoning session.

**Parameters:**
- `session_id` (optional): Session identifier (auto-generated if not provided)

**Returns:** Meta-analysis prompt with XML structure for `<surface_ask>`, `<real_need>`, `<unstated_context>`, `<failure_modes>`, `<optimal_response>`.

### submit_meta_analysis

Submit your meta-analysis to proceed to scaffold selection.

**Parameters:**
- `meta_analysis` (required): Your completed meta-analysis
- `session_id` (required): Session identifier

**Returns:** Scaffold selection prompt with USE WHEN / AVOID WHEN guidance.

### declare_scaffold

Declare your chosen scaffold type and phase flow.

**Parameters:**
- `scaffold_type` (required): "divergent" | "sequential" | "adversarial" | "checkpoint"
- `flow` (required): List of phase names (e.g., ["OPTIONS", "EVALUATE", "PICK"])
- `session_id` (required): Session identifier

**Returns:** Declaration prompt and style-specific prompt for first phase.

### think

Execute a thinking phase.

**Parameters:**
- `phase_name` (required): Name of current phase (must match declared flow)
- `content` (required): The thought content
- `session_id` (required): Session identifier
- `tactic` (optional): Tactic name for guidance lookup
- `relation` (optional): "builds" | "revises" | "forks" | "attacks" | "synthesizes" | "concludes"
- `targets` (optional): List of thought IDs this relates to

**Returns:** Phase completion status, tactic guidance if provided, and prompt for next phase.

### get_tactic_info

Get detailed information about a specific tactic.

**Parameters:**
- `tactic` (required): Tactic name

**Returns:** Style, default stance, guidance, expected outputs, and style prompt.

### get_session_state

Get current state of a reasoning session.

**Parameters:**
- `session_id` (required): Session identifier

**Returns:** Stage, scaffold type, flow, current phase index, thought count.

## Scaffold Types

| Type | Use When | Style |
|------|----------|-------|
| **divergent** | Need options, alternatives, possibilities | Generate freely, no filtering |
| **sequential** | Need to build reasoning chain | Thought → Thought → Revision |
| **adversarial** | High stakes, need stress-testing | Future failure → Cause → Prevention |
| **checkpoint** | Ready to decide | Verify → Conclusion → Flips-if |

## Tactics (19 available)

Call `get_tactic_info` to get details for any tactic:

**Divergent:** WILD_OPTIONS, HYPOTHESES, ALTERNATIVES, INVERSION, PRIOR_ART
**Sequential:** EVIDENCE_AUDIT, COMPLEXITY_INVENTORY, STEEL_MAN_OPPOSITE, GAP_ANALYSIS, CONTRADICTION, META_AUDIT
**Adversarial:** PREMORTEM, FAILURE_MODES
**Branching:** BRANCH_EXPLORE
**Checkpoint:** ANTIREZ_TEST, VERDICT, PICK, NEXT_ACTION
**Special:** META_ANALYSIS

## Example

```python
# 1. Start session
r = begin_session()
# Returns meta_analysis prompt

# 2. Submit analysis
r = submit_meta_analysis(
    meta_analysis="Surface: auth. Real need: simple, secure.",
    session_id=r["session_id"]
)
# Returns scaffold selection prompt

# 3. Declare scaffold
r = declare_scaffold(
    scaffold_type="divergent",
    flow=["OPTIONS", "EVALUATE", "PICK"],
    session_id=r["session_id"]
)
# Returns style prompt for OPTIONS phase

# 4. Execute phases
r = think(
    phase_name="OPTIONS",
    content="JWT, cookies, OAuth, magic links",
    tactic="WILD_OPTIONS",
    session_id=r["session_id"]
)
# Returns prompt for EVALUATE phase

r = think(
    phase_name="EVALUATE",
    content="OAuth too complex. JWT and cookies viable.",
    tactic="ANTIREZ_TEST",
    relation="attacks",
    targets=[1],
    session_id=r["session_id"]
)
# Returns prompt for PICK phase

r = think(
    phase_name="PICK",
    content="JWT for API, httpOnly cookie for web.",
    tactic="VERDICT",
    relation="concludes",
    targets=[1, 2],
    session_id=r["session_id"]
)
# Returns workflow_complete: True
```
