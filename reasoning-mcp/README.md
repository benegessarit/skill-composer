# Reasoning MCP

MCP server for structured multi-turn reasoning. Forces Claude to generate personas, role-play each in separate turns, stress-test assumptions, then synthesize.

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

## Tools

### Ensemble Reasoning (multi-turn)

These tools enforce a deliberate workflow: generate personas → role-play each → stress-test → synthesize.

#### ensemble

Generate or register an ensemble of personas for reasoning about a question. Two-call pattern: first call returns a generation prompt, second call registers the agents.

**Parameters:**
- `question` (required): The question/problem to reason about
- `agents` (optional): JSON of generated agents (omit first call to get generation prompt)
- `min_agents` (default 3): Minimum personas required
- `include_chaos` (default true): Require a chaos/perturbation agent
- `include_orchestrator` (default true): Require an orchestrator agent

**Returns:** Without agents: generation prompt. With agents: session_id and registered agent list.

#### invoke

Role-play as a specific persona for ONE turn. Two-call pattern.

**Parameters:**
- `session_id` (required): From ensemble()
- `agent` (required): Persona name to invoke
- `response` (optional): JSON of agent's response (omit to get role-play prompt)
- `context` (optional): Additional context for this turn

**Returns:** Without response: role-play prompt with prior discussion context. With response: registration confirmation and suggested next step.

Orchestrator agents get a special prompt that tracks who has spoken, what questions remain unanswered, and which agents should go next.

#### perturb

Chaos engineering for reasoning. Stress-test specific assumptions.

**Parameters:**
- `session_id` (required): From ensemble()
- `target` (required): The assumption/claim to perturb
- `mode` (default "negate"): One of `negate`, `remove`, `extreme`, `opposite`
- `result` (optional): JSON of perturbation result (omit to get prompt)

**Result JSON requires:** `perturbation`, `impact` (survives/breaks/weakens), `explanation`

#### synthesize

Forced synthesis of all perspectives. Blocked until min_agents have been invoked.

**Parameters:**
- `session_id` (required): From ensemble()
- `synthesis` (optional): JSON of synthesis (omit to get prompt)

**Synthesis JSON requires:** `conclusion`, `confidence`, `key_tensions`, `assumptions`

**Returns:** With synthesis: final session summary including dissent tracking.

#### get_session_state

Inspect current session: agents, invocations, perturbations, progress.

### Metacognitive Tools (standalone)

These tools work independently — no session required.

#### depth_probe

Metacognitive audit before executing. Forces examination of: Is the framing right? What reasoning is needed? Where will analysis be shallow?

**Parameters:**
- `question` (required): The question/problem to probe
- `result` (optional): JSON reflection (omit to get self-interrogation prompt)

**Result JSON requires:** `reframing`, `thinking_required`, `shallow_spots`, `missing_dimensions`, `process_critique`

#### plan_probe

Inventory what you actually know vs. will fake for each phase of a plan. Catches structural compliance masquerading as depth.

**Parameters:**
- `plan` (required): The execution plan or optimized prompt
- `result` (optional): JSON inventory (omit to get audit prompt)

**Result JSON requires:** `phases[]` (each with `phase`, `know`, `take`, `gaps`, `has_substance`), `phone_in_phase`, `expert_flag`

Anti-hedge enforcement: `take` field rejects hedging phrases ("it depends", "on one hand", etc.) — state a position or say "no position."

#### plan_prompt

Create a weighted execution plan from an optimized prompt. Allocate 100 weight points across phases with enforced trade-offs.

**Parameters:**
- `optimized_prompt` (required): The prompt to plan execution for
- `result` (optional): JSON plan (omit to get template)

**Validation rules:**
- Weights must sum to 100
- No two phases get the same weight
- Max weight must be ≥3x min weight
- `produces` must be specific (not "results" or "analysis")

Auto-assigns depth: weight ≥30 → deep, 15-29 → medium, <15 → shallow.

#### pause

Mid-execution restart test. Forces re-evaluation between phases: knowing what you now know, would you change the remaining plan?

**Parameters:**
- `phase_completed` (required): Name of phase just finished
- `result` (optional): JSON reflection (omit to get prompt)

**Result JSON requires:** `restart` (what you'd change), `next_phase_still_valid` (boolean)

#### surface

Mid-execution blind spot check. Lists what your momentum is hiding.

**Parameters:**
- `question` (required): Current phase or constraint being worked on
- `result` (optional): JSON surfacing (omit to get prompt)

**Result JSON requires:** `blind_spots[]` (each with `what`, `type`: assumption/omission/scope), `tension`, `decision` (continue/redirect/stop)

Validates: ≥2 blind spots, no duplicates (>70% word overlap rejected), tension must reference a blind spot.

#### audit_probe

Asymmetric audit from a different cognitive frame. One-call tool — no pre-prompt.

**Parameters:**
- `execution_frame` (required): Frame used during execution (e.g., "analysis")
- `audit_frame` (required): DIFFERENT frame for auditing (e.g., "pre-mortem")
- `result` (required): JSON audit

**Result JSON requires:** `execution_summary`, `gaps`, `vulnerability`, `revision`

Same-frame review is rejected ("echo chamber").

## Example: Ensemble Workflow

```python
# 1. Get persona generation prompt
r = ensemble(question="Should we use microservices or monolith?")
# Returns prompt for generating personas

# 2. Register generated personas
r = ensemble(
    question="Should we use microservices or monolith?",
    agents=[
        {"name": "Pragmatist", "role": "Staff engineer", "purpose": "Real-world trade-offs",
         "perspective": "Ship fast, scale later"},
        {"name": "Architect", "role": "Platform lead", "purpose": "Long-term maintainability",
         "perspective": "Get the boundaries right first"},
        {"name": "Chaos", "role": "Adversary", "purpose": "Break assumptions",
         "perspective": "What fails at 10x scale?", "is_chaos": True},
        {"name": "Facilitator", "role": "Discussion guide", "purpose": "Track coverage",
         "perspective": "Who hasn't been heard?", "is_orchestrator": True},
    ]
)
session_id = r["session_id"]

# 3. Invoke each persona (separate turns enforced)
r = invoke(session_id=session_id, agent="Pragmatist")
# Returns role-play prompt → Claude responds as Pragmatist
r = invoke(session_id=session_id, agent="Pragmatist",
           response={"response": "Monolith. Split when you feel the pain.", "raises": ["What's the team size?"]})

# 4. Stress-test an assumption
r = perturb(session_id=session_id, target="Team is small enough for monolith", mode="extreme")
# Returns perturbation prompt

# 5. Synthesize (blocked until min_agents heard)
r = synthesize(session_id=session_id)
# Returns synthesis prompt with all perspectives + perturbation results
```

## Example: Metacognitive Tools

```python
# Depth probe before starting work
r = depth_probe(question="How should we handle auth?")
# Returns self-interrogation prompt → respond with reframing, shallow spots, etc.

# Plan with weighted budget
r = plan_prompt(optimized_prompt="<your prompt with phases>")
# Returns planning template → allocate 100 points across phases

# Mid-execution check
r = pause(phase_completed="ANALYSIS")
# Returns restart test → what would you change?

# Asymmetric audit after completion
r = audit_probe(
    execution_frame="analysis",
    audit_frame="pre-mortem",
    result={"execution_summary": "...", "gaps": "...", "vulnerability": "...", "revision": "..."}
)
```

## Dependencies

- Python ≥3.10
- `mcp>=1.0.0`

## Session Management

Sessions are stored in memory with a cap of 100. When the limit is reached, synthesized (completed) sessions are evicted first, falling back to oldest session if all are active.

## License

MIT
