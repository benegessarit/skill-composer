"""Tests for the Generative Agent Ensemble MCP server."""
import json
import pytest
from reasoning_mcp.server import (
    audit_probe,
    ensemble,
    invoke,
    perturb,
    plan_prompt,
    surface,
    synthesize,
    get_session_state,
    sessions,
)


@pytest.fixture(autouse=True)
def clear_sessions():
    sessions.clear()
    yield
    sessions.clear()


def _sample_agents():
    """Sample agents JSON for testing."""
    return json.dumps({
        "agents": [
            {"name": "Performance Engineer", "role": "Speed advocate", "purpose": "Optimize latency", "perspective": "Speed is everything", "is_chaos": False},
            {"name": "Data Integrity Hawk", "role": "Durability advocate", "purpose": "Ensure data safety", "perspective": "Data loss is unacceptable", "is_chaos": False},
            {"name": "Chaos Gremlin", "role": "Failure analyst", "purpose": "Find failure modes", "perspective": "Everything will break", "is_chaos": True},
            {"name": "Discussion Director", "role": "Meta-observer", "purpose": "Assess progress", "perspective": "Push for depth", "is_orchestrator": True},
        ]
    })


def _sample_invoke_response(text: str, suggests: str | None = None):
    """Sample invoke response JSON."""
    return json.dumps({
        "response": text,
        "raises": ["What about edge cases?"],
        "suggests_next": suggests,
    })


def _sample_perturb_result(impact: str):
    """Sample perturb result JSON."""
    return json.dumps({
        "perturbation": "Assumed the opposite",
        "impact": impact,
        "explanation": "Because reasons",
    })


def _sample_synthesis():
    """Sample synthesis JSON."""
    return json.dumps({
        "conclusion": "Use Redis for caching with Postgres as source of truth",
        "confidence": 0.8,
        "dissent": "Data Integrity Hawk wants AOF if any persistence",
        "key_tensions": ["Speed vs durability tradeoff"],
        "assumptions": ["Data is reconstructible", "Team knows Redis"],
    })


# --- ensemble tests ---

@pytest.mark.asyncio
async def test_ensemble_returns_prompt_without_agents():
    """First call to ensemble returns generation prompt."""
    result = json.loads(await ensemble(question="Should we use Redis?"))
    assert result["action"] == "generate_personas"
    assert "prompt" in result
    assert "Redis" in result["prompt"]
    assert "next_step" in result


@pytest.mark.asyncio
async def test_ensemble_creates_session_with_agents():
    """Second call with agents creates session."""
    result = json.loads(await ensemble(
        question="Should we use Redis?",
        agents=_sample_agents(),
    ))
    assert "session_id" in result
    assert len(result["agents"]) == 4
    assert result["chaos_agent"] == "Chaos Gremlin"
    assert result["orchestrator_agent"] == "Discussion Director"


@pytest.mark.asyncio
async def test_ensemble_rejects_too_few_agents():
    """Ensemble rejects fewer agents than min_agents."""
    agents = json.dumps([
        {"name": "A", "role": "R", "purpose": "P", "perspective": "V"},
    ])
    result = json.loads(await ensemble(
        question="Test?",
        agents=agents,
        min_agents=3,
    ))
    assert "error" in result
    assert "at least 3" in result["error"]


@pytest.mark.asyncio
async def test_ensemble_rejects_missing_chaos_agent():
    """Ensemble rejects when include_chaos=True but no chaos agent."""
    agents = json.dumps([
        {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": False},
        {"name": "B", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": False},
        {"name": "C", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": False, "is_orchestrator": True},
    ])
    result = json.loads(await ensemble(
        question="Test?",
        agents=agents,
        include_chaos=True,
    ))
    assert "error" in result
    assert "chaos" in result["error"].lower()


@pytest.mark.asyncio
async def test_ensemble_allows_no_chaos_when_disabled():
    """Ensemble accepts no chaos agent when include_chaos=False."""
    agents = json.dumps([
        {"name": "A", "role": "R", "purpose": "P", "perspective": "V"},
        {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
        {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
    ])
    result = json.loads(await ensemble(
        question="Test?",
        agents=agents,
        include_chaos=False,
        include_orchestrator=False,
    ))
    assert "session_id" in result
    assert result["chaos_agent"] is None


@pytest.mark.asyncio
async def test_ensemble_accepts_native_dict():
    """Ensemble accepts agents as native dict (not just JSON string).

    MCP clients may pass already-parsed JSON objects instead of strings.
    """
    agents_dict = {
        "agents": [
            {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": True},
            {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
            {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
            {"name": "D", "role": "R", "purpose": "P", "perspective": "V", "is_orchestrator": True},
        ]
    }
    result = json.loads(await ensemble(
        question="Test?",
        agents=agents_dict,  # Native dict, not json.dumps()
    ))
    assert "session_id" in result
    assert len(result["agents"]) == 4


@pytest.mark.asyncio
async def test_ensemble_accepts_native_list():
    """Ensemble accepts agents as native list (not just JSON string)."""
    agents_list = [
        {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": True},
        {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
        {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
        {"name": "D", "role": "R", "purpose": "P", "perspective": "V", "is_orchestrator": True},
    ]
    result = json.loads(await ensemble(
        question="Test?",
        agents=agents_list,  # Native list, not json.dumps()
    ))
    assert "session_id" in result
    assert len(result["agents"]) == 4


# --- invoke tests ---

@pytest.mark.asyncio
async def test_invoke_returns_prompt_without_response():
    """First call to invoke returns role-play prompt."""
    # Setup session
    session_result = json.loads(await ensemble(
        question="Should we use Redis?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    result = json.loads(await invoke(
        session_id=session_id,
        agent="Performance Engineer",
    ))
    assert result["action"] == "role_play"
    assert "prompt" in result
    assert "Performance Engineer" in result["prompt"]


@pytest.mark.asyncio
async def test_invoke_registers_response():
    """Second call with response registers invocation."""
    # Setup session
    session_result = json.loads(await ensemble(
        question="Should we use Redis?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    # Get prompt (first call)
    await invoke(session_id=session_id, agent="Performance Engineer")

    # Register response (second call)
    result = json.loads(await invoke(
        session_id=session_id,
        agent="Performance Engineer",
        response=_sample_invoke_response("Redis is fast, 0.1ms reads."),
    ))
    assert result["registered"] is True
    assert result["invocation_number"] == 1
    assert result["unique_agents_invoked"] == 1


@pytest.mark.asyncio
async def test_invoke_accepts_native_dict():
    """Invoke accepts response as native dict (not just JSON string)."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    # Pass response as native dict, not JSON string
    result = json.loads(await invoke(
        session_id=session_id,
        agent="Performance Engineer",
        response={"response": "Fast", "raises": [], "suggests_next": None},
    ))
    assert result["registered"] is True


@pytest.mark.asyncio
async def test_invoke_rejects_unknown_agent():
    """Invoke rejects agents not in ensemble."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    result = json.loads(await invoke(
        session_id=session_id,
        agent="Unknown Agent",
    ))
    assert "error" in result
    assert "not in ensemble" in result["error"]


@pytest.mark.asyncio
async def test_invoke_tracks_unique_agents():
    """Invoke tracks unique agents invoked."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    # Invoke same agent twice
    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("First response"))
    result = json.loads(await invoke(
        session_id=session_id,
        agent="Performance Engineer",
        response=_sample_invoke_response("Second response"),
    ))

    assert result["invocation_number"] == 2
    assert result["unique_agents_invoked"] == 1  # Still 1


@pytest.mark.asyncio
async def test_invoke_session_not_found():
    """Invoke returns error for unknown session."""
    result = json.loads(await invoke(
        session_id="nonexistent",
        agent="Test",
    ))
    assert "error" in result
    assert "not found" in result["error"]


# --- perturb tests ---

@pytest.mark.asyncio
async def test_perturb_returns_prompt_without_result():
    """First call to perturb returns perturbation prompt."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    result = json.loads(await perturb(
        session_id=session_id,
        target="Redis is fast",
        mode="negate",
    ))
    assert result["action"] == "perturb"
    assert "prompt" in result
    assert "negate" in result["prompt"]


@pytest.mark.asyncio
async def test_perturb_registers_result():
    """Second call with result registers perturbation."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    result = json.loads(await perturb(
        session_id=session_id,
        target="Redis is fast",
        mode="negate",
        result=_sample_perturb_result("survives"),
    ))
    assert result["registered"] is True
    assert result["impact"] == "survives"


@pytest.mark.asyncio
async def test_perturb_validates_impact():
    """Perturb validates impact field."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    bad_result = json.dumps({
        "perturbation": "test",
        "impact": "invalid",
        "explanation": "test",
    })
    result = json.loads(await perturb(
        session_id=session_id,
        target="test",
        result=bad_result,
    ))
    assert "error" in result
    assert "survives" in result["error"]


# --- synthesize tests ---

@pytest.mark.asyncio
async def test_synthesize_blocked_until_min_agents():
    """Synthesize is blocked until min_agents invoked."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
        min_agents=3,
    ))
    session_id = session_result["session_id"]

    # Only invoke 2 agents
    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("Fast"))
    await invoke(session_id=session_id, agent="Data Integrity Hawk",
                 response=_sample_invoke_response("Safe"))

    result = json.loads(await synthesize(session_id=session_id))
    assert "error" in result
    assert "at least 3" in result["error"]
    assert result["count"] == 2


@pytest.mark.asyncio
async def test_synthesize_returns_prompt_when_ready():
    """Synthesize returns prompt when min_agents met."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
        min_agents=3,
    ))
    session_id = session_result["session_id"]

    # Invoke all 3 agents
    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("Fast"))
    await invoke(session_id=session_id, agent="Data Integrity Hawk",
                 response=_sample_invoke_response("Safe"))
    await invoke(session_id=session_id, agent="Chaos Gremlin",
                 response=_sample_invoke_response("What if it breaks?"))

    result = json.loads(await synthesize(session_id=session_id))
    assert result["action"] == "synthesize"
    assert "prompt" in result
    assert len(result["agents_heard"]) == 3


@pytest.mark.asyncio
async def test_synthesize_completes_session():
    """Synthesize with synthesis JSON completes session."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
        min_agents=3,
    ))
    session_id = session_result["session_id"]

    # Invoke all agents
    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("Fast"))
    await invoke(session_id=session_id, agent="Data Integrity Hawk",
                 response=_sample_invoke_response("Safe"))
    await invoke(session_id=session_id, agent="Chaos Gremlin",
                 response=_sample_invoke_response("Breaks"))

    result = json.loads(await synthesize(
        session_id=session_id,
        synthesis=_sample_synthesis(),
    ))
    assert result["workflow_complete"] is True
    assert result["conclusion"] == "Use Redis for caching with Postgres as source of truth"
    assert result["confidence"] == 0.8


@pytest.mark.asyncio
async def test_synthesize_blocks_after_completion():
    """Synthesize blocks after session is complete."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
        min_agents=3,
    ))
    session_id = session_result["session_id"]

    # Complete session
    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("Fast"))
    await invoke(session_id=session_id, agent="Data Integrity Hawk",
                 response=_sample_invoke_response("Safe"))
    await invoke(session_id=session_id, agent="Chaos Gremlin",
                 response=_sample_invoke_response("Breaks"))
    await synthesize(session_id=session_id, synthesis=_sample_synthesis())

    # Try again
    result = json.loads(await synthesize(session_id=session_id))
    assert "error" in result
    assert "already synthesized" in result["error"]


# --- get_session_state tests ---

@pytest.mark.asyncio
async def test_get_session_state():
    """get_session_state returns session info."""
    session_result = json.loads(await ensemble(
        question="Test?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("Fast"))

    state = json.loads(await get_session_state(session_id))
    assert state["session_id"] == session_id
    assert state["question"] == "Test?"
    assert len(state["agents"]) == 4
    assert len(state["invocations"]) == 1
    assert state["unique_agents_invoked"] == 1
    assert state["synthesized"] is False


@pytest.mark.asyncio
async def test_get_session_state_not_found():
    """get_session_state returns error for unknown session."""
    result = json.loads(await get_session_state("nonexistent"))
    assert "error" in result
    assert "not found" in result["error"]


# --- orchestrator tests ---

@pytest.mark.asyncio
async def test_ensemble_rejects_missing_orchestrator():
    """Ensemble rejects when include_orchestrator=True but no orchestrator agent."""
    agents = json.dumps([
        {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": True},
        {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
        {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
    ])
    result = json.loads(await ensemble(
        question="Test?",
        agents=agents,
        include_orchestrator=True,
    ))
    assert "error" in result
    assert "orchestrator" in result["error"].lower()


@pytest.mark.asyncio
async def test_ensemble_allows_no_orchestrator_when_disabled():
    """Ensemble accepts no orchestrator when include_orchestrator=False."""
    agents = json.dumps([
        {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": True},
        {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
        {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
    ])
    result = json.loads(await ensemble(
        question="Test?",
        agents=agents,
        include_orchestrator=False,
    ))
    assert "session_id" in result
    assert result["orchestrator_agent"] is None


@pytest.mark.asyncio
async def test_orchestrator_gets_special_prompt():
    """Orchestrator invocation returns orchestrate action with special prompt."""
    session_result = json.loads(await ensemble(
        question="Should we use Redis?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    # First invoke a regular agent
    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("Fast", "Data Integrity Hawk"))

    # Now invoke the orchestrator
    result = json.loads(await invoke(
        session_id=session_id,
        agent="Discussion Director",
    ))
    assert result["action"] == "orchestrate"
    assert "ORCHESTRATOR" in result["prompt"]
    assert "PROGRESS CHECK" in result["prompt"]
    assert "COVERAGE AUDIT" in result["prompt"]
    assert "TENSION DETECTOR" in result["prompt"]


@pytest.mark.asyncio
async def test_orchestrator_prompt_includes_context():
    """Orchestrator prompt includes agents spoken and unanswered questions."""
    session_result = json.loads(await ensemble(
        question="Should we use Redis?",
        agents=_sample_agents(),
    ))
    session_id = session_result["session_id"]

    # Invoke agents with questions
    await invoke(session_id=session_id, agent="Performance Engineer",
                 response=_sample_invoke_response("Redis is fast"))
    await invoke(session_id=session_id, agent="Data Integrity Hawk",
                 response=_sample_invoke_response("What about durability?"))

    # Orchestrator prompt should include context
    result = json.loads(await invoke(
        session_id=session_id,
        agent="Discussion Director",
    ))
    assert "Performance Engineer" in result["prompt"]
    assert "Data Integrity Hawk" in result["prompt"]


# --- plan_prompt tests ---

_SAMPLE_PROMPT_XML = """<role>Backend advisor</role>
<purpose>Your job is to recommend an auth approach.</purpose>

FLOW: [OPTIONS] -> [ANALYSIS] -> [RECOMMENDATION]

<phase name="Options">
  <instruction>List 4 auth approaches.</instruction>
</phase>

<phase name="Analysis">
  <instruction>Compare top 3.</instruction>
</phase>

<phase name="Recommendation">
  <instruction>Pick one.</instruction>
</phase>

CONSTRAINTS:
- No waffling"""


_SAMPLE_PROMPT_FLOW_ONLY = """Analyze the problem.

FLOW: [GATHER] -> [EVALUATE] -> [DECIDE]

Do the work."""


def _sample_plan(num_phases=3, weights=None, depths=None):
    """Create a valid plan result.

    depths parameter is accepted for backward compat but ignored by the server
    (depth is auto-calculated from weight).
    """
    if weights is None:
        weights = [50, 35, 15] if num_phases == 3 else [50, 30, 12, 8][:num_phases]

    phases = []
    for i in range(num_phases):
        phase = {
            "phase": i + 1,
            "name": f"Phase {i + 1}",
            "weight": weights[i],
            "produces": f"Detailed {i + 1}-column comparison table with specific headers",
            "depends_on": list(range(1, i + 1)) if i > 0 else [],
            "skip_if": None if i == 0 else f"Phase {i} already covers this",
        }
        # Include depth if explicitly passed (server overwrites it anyway)
        if depths is not None:
            phase["depth"] = depths[i]
        phases.append(phase)
    return json.dumps({"phases": phases})


@pytest.mark.asyncio
async def test_plan_prompt_returns_template_xml_phases():
    """plan_prompt extracts XML phases and returns planning template."""
    result = json.loads(await plan_prompt(optimized_prompt=_SAMPLE_PROMPT_XML))
    assert result["action"] == "plan_prompt"
    assert result["phase_count"] == 3
    assert "Options" in result["phases_detected"]
    assert "Analysis" in result["phases_detected"]
    assert "Recommendation" in result["phases_detected"]
    assert "PLANNER" in result["prompt"]
    assert "BUDGET" in result["prompt"]


@pytest.mark.asyncio
async def test_plan_prompt_returns_template_flow_phases():
    """plan_prompt extracts FLOW line phases."""
    result = json.loads(await plan_prompt(optimized_prompt=_SAMPLE_PROMPT_FLOW_ONLY))
    assert result["phase_count"] == 3
    assert "GATHER" in result["phases_detected"]
    assert "EVALUATE" in result["phases_detected"]
    assert "DECIDE" in result["phases_detected"]


@pytest.mark.asyncio
async def test_plan_prompt_handles_no_phases():
    """plan_prompt works when no phases can be extracted."""
    result = json.loads(await plan_prompt(optimized_prompt="Just a plain question with no structure."))
    assert result["phase_count"] == 0
    assert result["phases_detected"] == []
    assert "Count the phases" in result["prompt"]


@pytest.mark.asyncio
async def test_plan_prompt_validates_valid_plan():
    """plan_prompt accepts a valid plan with correct budget allocation."""
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=_sample_plan(3),
    ))
    assert result["planned"] is True
    assert result["phase_count"] == 3


@pytest.mark.asyncio
async def test_plan_prompt_rejects_phase_count_mismatch():
    """plan_prompt rejects when plan phase count doesn't match prompt."""
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,  # 3 phases
        result=_sample_plan(2, weights=[75, 25], depths=["deep", "medium"]),
    ))
    assert "error" in result
    assert "mismatch" in result["error"]


@pytest.mark.asyncio
async def test_plan_prompt_rejects_duplicate_weights():
    """plan_prompt rejects plans where two phases have the same weight."""
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=_sample_plan(3, weights=[40, 40, 20], depths=["deep", "deep", "medium"]),
    ))
    assert "error" in result
    assert "same weight" in result["error"]


@pytest.mark.asyncio
async def test_plan_prompt_rejects_insufficient_spread():
    """plan_prompt rejects when max/min weight spread < 3x."""
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=_sample_plan(3, weights=[40, 35, 25], depths=["deep", "deep", "medium"]),
    ))
    assert "error" in result
    assert "3x" in result["error"]


@pytest.mark.asyncio
async def test_plan_prompt_rejects_wrong_weight_sum():
    """plan_prompt rejects weights that don't sum to 100."""
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=_sample_plan(3, weights=[50, 30, 10], depths=["deep", "deep", "shallow"]),
    ))
    assert "error" in result
    assert "sum to 100" in result["error"]


@pytest.mark.asyncio
async def test_plan_prompt_auto_calculates_depth():
    """plan_prompt derives depth from weight — model doesn't need to specify it."""
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=_sample_plan(3, weights=[50, 35, 15]),
    ))
    assert result["planned"] is True
    phases = result["phases"]
    assert phases[0]["depth"] == "deep"     # 50 >= 30
    assert phases[1]["depth"] == "deep"     # 35 >= 30
    assert phases[2]["depth"] == "medium"   # 15 >= 15


@pytest.mark.asyncio
async def test_plan_prompt_rejects_generic_produces():
    """plan_prompt rejects generic produces values like 'results'."""
    plan = json.loads(_sample_plan(3))
    plan["phases"][0]["produces"] = "results"
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=json.dumps(plan),
    ))
    assert "error" in result
    assert "produces" in result["error"]


@pytest.mark.asyncio
async def test_plan_prompt_rejects_missing_field():
    """plan_prompt rejects phases missing required fields."""
    plan = json.loads(_sample_plan(3))
    del plan["phases"][1]["skip_if"]
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=json.dumps(plan),
    ))
    assert "error" in result
    assert "skip_if" in result["error"]


@pytest.mark.asyncio
async def test_plan_prompt_rejects_empty_phases():
    """plan_prompt rejects empty phases array."""
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=json.dumps({"phases": []}),
    ))
    assert "error" in result
    assert "empty" in result["error"]


@pytest.mark.asyncio
async def test_plan_prompt_accepts_native_dict():
    """plan_prompt accepts result as native dict."""
    plan = json.loads(_sample_plan(3))
    result = json.loads(await plan_prompt(
        optimized_prompt=_SAMPLE_PROMPT_XML,
        result=plan,
    ))
    assert result["planned"] is True


@pytest.mark.asyncio
async def test_plan_prompt_skips_count_check_when_no_phases_detected():
    """plan_prompt skips phase count validation when no phases were extracted."""
    result = json.loads(await plan_prompt(
        optimized_prompt="Plain text with no structure.",
        result=_sample_plan(2, weights=[75, 25], depths=["deep", "medium"]),
    ))
    # Should not error on count — just validate the plan itself
    # But spread check: 75/25 = 3.0x >= 3x, so passes
    assert result["planned"] is True


# --- audit_probe tests ---

def _sample_audit_result():
    """Sample valid audit probe result."""
    return json.dumps({
        "execution_summary": "Analyzed 3 auth approaches on security, complexity, and cost.",
        "gaps": "Didn't consider rate limiting or token refresh flows.",
        "vulnerability": "Recommendation assumes low traffic — breaks at scale.",
        "revision": "Add rate-limiting analysis as a constraint in the comparison phase.",
    })


@pytest.mark.asyncio
async def test_audit_probe_rejects_same_frames():
    """audit_probe rejects when execution and audit frames match."""
    result = json.loads(await audit_probe(
        execution_frame="analysis",
        audit_frame="analysis",
        result=_sample_audit_result(),
    ))
    assert "error" in result
    assert "must differ" in result["error"]


@pytest.mark.asyncio
async def test_audit_probe_rejects_same_frames_case_insensitive():
    """audit_probe frame comparison is case-insensitive."""
    result = json.loads(await audit_probe(
        execution_frame="Analysis",
        audit_frame="analysis",
        result=_sample_audit_result(),
    ))
    assert "error" in result
    assert "must differ" in result["error"]


@pytest.mark.asyncio
async def test_audit_probe_rejects_missing_field():
    """audit_probe rejects when required field is missing."""
    bad_result = json.dumps({
        "execution_summary": "Analyzed stuff.",
        "gaps": "Some gaps.",
    })
    result = json.loads(await audit_probe(
        execution_frame="analysis",
        audit_frame="pre-mortem",
        result=bad_result,
    ))
    assert "error" in result
    assert "vulnerability" in result["error"]


@pytest.mark.asyncio
async def test_audit_probe_validates_valid_result():
    """audit_probe accepts valid asymmetric audit result."""
    result = json.loads(await audit_probe(
        execution_frame="analysis",
        audit_frame="pre-mortem",
        result=_sample_audit_result(),
    ))
    assert result["audited"] is True
    assert result["execution_frame"] == "analysis"
    assert result["audit_frame"] == "pre-mortem"
    assert "gaps" in result
    assert "vulnerability" in result


@pytest.mark.asyncio
async def test_audit_probe_accepts_native_dict():
    """audit_probe accepts result as native dict."""
    result = json.loads(await audit_probe(
        execution_frame="comparison",
        audit_frame="inversion",
        result={
            "execution_summary": "Compared 3 options.",
            "gaps": "Missing edge case for option B.",
            "vulnerability": "Assumed happy path only.",
            "revision": "Add error handling analysis.",
        },
    ))
    assert result["audited"] is True
    assert result["execution_frame"] == "comparison"
    assert result["audit_frame"] == "inversion"


# --- surface tests ---


def _valid_surface_result():
    """Sample valid surface result JSON."""
    return {
        "blind_spots": [
            {"what": "ignoring latency impact on user experience", "type": "omission"},
            {"what": "assuming single-region deployment", "type": "assumption", "evidence": "no region discussion"},
        ],
        "tension": "latency optimization conflicts with single-region constraint",
        "decision": "redirect",
    }


@pytest.mark.asyncio
async def test_surface_returns_prompt_without_result():
    """First call to surface returns the surfacing prompt."""
    result = json.loads(await surface(question="evaluating cache strategy"))
    assert result["action"] == "surface"
    assert "prompt" in result
    assert result["context"] == "evaluating cache strategy"
    assert "blind spots" in result["prompt"].lower()


@pytest.mark.asyncio
async def test_surface_validates_valid_result():
    """surface accepts a valid result with diverse blind spots."""
    result = json.loads(await surface(
        question="cache strategy",
        result=_valid_surface_result(),
    ))
    assert result["surfaced"] is True
    assert result["blind_spot_count"] == 2
    assert result["decision"] == "redirect"


@pytest.mark.asyncio
async def test_surface_rejects_too_few_blind_spots():
    """surface rejects fewer than 2 blind spots."""
    result = json.loads(await surface(
        question="test",
        result={
            "blind_spots": [{"what": "one thing", "type": "omission"}],
            "tension": "none",
            "decision": "continue",
        },
    ))
    assert "error" in result
    assert "at least 2" in result["error"]


@pytest.mark.asyncio
async def test_surface_rejects_duplicate_blind_spots():
    """surface rejects blind spots with >70% word overlap."""
    result = json.loads(await surface(
        question="test",
        result={
            "blind_spots": [
                {"what": "ignoring the latency impact on users in production", "type": "omission"},
                {"what": "ignoring the latency impact on users in staging", "type": "omission"},
            ],
            "tension": "latency is a concern in production",
            "decision": "continue",
        },
    ))
    assert "error" in result
    assert "too similar" in result["error"]


@pytest.mark.asyncio
async def test_surface_rejects_invalid_decision():
    """surface rejects invalid decision values."""
    data = _valid_surface_result()
    data["decision"] = "maybe"
    result = json.loads(await surface(question="test", result=data))
    assert "error" in result
    assert "continue|redirect|stop" in result["error"]


@pytest.mark.asyncio
async def test_surface_rejects_invalid_blind_spot_type():
    """surface rejects blind spot with invalid type."""
    result = json.loads(await surface(
        question="test",
        result={
            "blind_spots": [
                {"what": "missing feature X", "type": "bug"},
                {"what": "ignoring constraint Y", "type": "omission"},
            ],
            "tension": "feature X conflicts with constraint Y",
            "decision": "continue",
        },
    ))
    assert "error" in result
    assert "assumption|omission|scope" in result["error"]


@pytest.mark.asyncio
async def test_surface_rejects_disconnected_tension():
    """surface rejects tension that doesn't reference any blind spot."""
    result = json.loads(await surface(
        question="test",
        result={
            "blind_spots": [
                {"what": "ignoring latency impact", "type": "omission"},
                {"what": "assuming single-region deployment", "type": "assumption"},
            ],
            "tension": "completely unrelated sentence about bananas",
            "decision": "continue",
        },
    ))
    assert "error" in result
    assert "no shared words" in result["error"]


@pytest.mark.asyncio
async def test_surface_rejects_missing_field():
    """surface rejects result missing required field."""
    result = json.loads(await surface(
        question="test",
        result={"blind_spots": [], "tension": "something"},
    ))
    assert "error" in result
    assert "decision" in result["error"]


@pytest.mark.asyncio
async def test_surface_accepts_string_result():
    """surface accepts result as JSON string."""
    result = json.loads(await surface(
        question="test",
        result=json.dumps(_valid_surface_result()),
    ))
    assert result["surfaced"] is True


@pytest.mark.asyncio
async def test_surface_rejects_blind_spot_missing_what():
    """surface rejects blind spot without 'what' field."""
    result = json.loads(await surface(
        question="test",
        result={
            "blind_spots": [
                {"type": "omission"},
                {"what": "something else", "type": "assumption"},
            ],
            "tension": "something about omission",
            "decision": "continue",
        },
    ))
    assert "error" in result
    assert "missing 'what'" in result["error"]
