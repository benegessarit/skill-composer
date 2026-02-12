"""Integration tests for the Generative Agent Ensemble MCP."""
import json
import pytest
from reasoning_mcp.server import (
    ensemble,
    invoke,
    perturb,
    synthesize,
    sessions,
)


@pytest.fixture(autouse=True)
def clear_sessions():
    sessions.clear()
    yield
    sessions.clear()


@pytest.mark.asyncio
async def test_full_ensemble_workflow():
    """Integration test: complete workflow from question to synthesis."""
    question = "Should we use Redis or Postgres for caching?"

    # 1. Get generation prompt
    r1 = json.loads(await ensemble(question=question))
    assert r1["action"] == "generate_personas"
    assert "Redis" in r1["prompt"] or "Postgres" in r1["prompt"]

    # 2. Register generated agents
    agents = json.dumps({
        "agents": [
            {
                "name": "Performance Engineer",
                "role": "Latency optimizer",
                "purpose": "Minimize response times",
                "perspective": "Speed is the top priority",
                "is_chaos": False,
            },
            {
                "name": "Data Integrity Hawk",
                "role": "Durability advocate",
                "purpose": "Ensure no data loss",
                "perspective": "Data safety trumps speed",
                "is_chaos": False,
            },
            {
                "name": "Ops Veteran",
                "role": "Operations engineer",
                "purpose": "Consider maintenance burden",
                "perspective": "Simple systems last longer",
                "is_chaos": False,
            },
            {
                "name": "Chaos Gremlin",
                "role": "Failure analyst",
                "purpose": "Find failure modes",
                "perspective": "Everything breaks at 3am",
                "is_chaos": True,
            },
            {
                "name": "Discussion Director",
                "role": "Meta-observer",
                "purpose": "Assess progress and push for depth",
                "perspective": "Comfortable consensus is usually wrong",
                "is_orchestrator": True,
            },
        ],
        "suggested_order": ["Performance Engineer", "Data Integrity Hawk", "Ops Veteran", "Chaos Gremlin", "Discussion Director"],
    })
    r2 = json.loads(await ensemble(question=question, agents=agents))
    assert "session_id" in r2
    session_id = r2["session_id"]
    assert r2["chaos_agent"] == "Chaos Gremlin"
    assert r2["orchestrator_agent"] == "Discussion Director"
    assert len(r2["agents"]) == 5

    # 3. Invoke Performance Engineer
    r3_prompt = json.loads(await invoke(session_id=session_id, agent="Performance Engineer"))
    assert r3_prompt["action"] == "role_play"
    assert "Performance Engineer" in r3_prompt["prompt"]

    r3 = json.loads(await invoke(
        session_id=session_id,
        agent="Performance Engineer",
        response=json.dumps({
            "response": "Redis wins hands down for caching. Sub-millisecond reads, 0.1ms typical. Postgres can't compete — 1-5ms for simple queries. For hot-path caching, Redis is the clear choice. Just watch memory limits.",
            "raises": ["What's our memory budget?", "How big is the working set?"],
            "suggests_next": "Data Integrity Hawk",
        }),
    ))
    assert r3["registered"] is True
    assert r3["suggests_next"] == "Data Integrity Hawk"

    # 4. Invoke Data Integrity Hawk
    r4_prompt = json.loads(await invoke(session_id=session_id, agent="Data Integrity Hawk"))
    assert "Performance Engineer" in r4_prompt["prompt"]  # Prior context included

    r4 = json.loads(await invoke(
        session_id=session_id,
        agent="Data Integrity Hawk",
        response=json.dumps({
            "response": "Hold on. Redis persistence is an afterthought. RDB snapshots lose data between saves. AOF has rewrite risks. If this cached data matters, Postgres. If it's truly ephemeral and reconstructible, Redis is OK.",
            "raises": ["Is the cached data reconstructible from source?"],
            "suggests_next": "Ops Veteran",
        }),
    ))
    assert r4["registered"] is True

    # 5. Invoke Ops Veteran
    r5 = json.loads(await invoke(
        session_id=session_id,
        agent="Ops Veteran",
        response=json.dumps({
            "response": "Both have ops overhead. Redis needs memory tuning, eviction policies, replica failover. Postgres you already run — less operational complexity. But Redis cluster is simpler than Postgres replication for caching.",
            "raises": ["Do we already run Redis in production?"],
            "suggests_next": "Chaos Gremlin",
        }),
    ))
    assert r5["registered"] is True

    # 6. Invoke Chaos Gremlin
    r6 = json.loads(await invoke(
        session_id=session_id,
        agent="Chaos Gremlin",
        response=json.dumps({
            "response": "Let me break both. Redis node dies at 3am — what happens? App crashes or degrades gracefully? Postgres connection pool exhausted — what's the fallback? Network partition between app and cache — cascading failure or isolated blast radius?",
            "raises": ["What's the fallback when cache is unavailable?", "How do we detect cache failures?"],
            "suggests_next": "synthesize",
        }),
    ))
    assert r6["registered"] is True
    assert r6["can_synthesize"] is True

    # 7. Apply a perturbation
    r7_prompt = json.loads(await perturb(
        session_id=session_id,
        target="Redis is faster than Postgres",
        mode="negate",
    ))
    assert r7_prompt["action"] == "perturb"

    r7 = json.loads(await perturb(
        session_id=session_id,
        target="Redis is faster than Postgres",
        mode="negate",
        result=json.dumps({
            "perturbation": "Assumed Postgres with good indexing matches Redis latency",
            "impact": "weakens",
            "explanation": "If latency difference is negligible, Redis complexity isn't worth it. But for hot-path reads, Redis still wins on P99.",
        }),
    ))
    assert r7["registered"] is True
    assert r7["impact"] == "weakens"

    # 8. Synthesize
    r8_prompt = json.loads(await synthesize(session_id=session_id))
    assert r8_prompt["action"] == "synthesize"
    assert r8_prompt["perturbations_applied"] == 1

    r8 = json.loads(await synthesize(
        session_id=session_id,
        synthesis=json.dumps({
            "conclusion": "Use Redis for caching with Postgres as source of truth. Cache is read-through and reconstructible from DB. Fallback: bypass cache on Redis failure, serve from Postgres (degraded but functional).",
            "confidence": 0.8,
            "dissent": "Data Integrity Hawk wants AOF enabled if any data persistence is needed. Ops Veteran notes we don't currently run Redis.",
            "key_tensions": [
                "Speed (Redis) vs durability (Postgres)",
                "Operational simplicity (Postgres) vs caching performance (Redis)",
            ],
            "assumptions": [
                "Cached data is reconstructible from Postgres",
                "Team has Redis operational experience or is willing to learn",
                "Memory budget is sufficient for working set",
            ],
        }),
    ))
    assert r8["workflow_complete"] is True
    assert r8["confidence"] == 0.8
    assert len(r8["agents_heard"]) == 4
    assert r8["perturbations_applied"] == 1


@pytest.mark.asyncio
async def test_workflow_with_multiple_invocations_per_agent():
    """Test that agents can be invoked multiple times."""
    r1 = json.loads(await ensemble(
        question="Test question?",
        agents=json.dumps([
            {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": True},
            {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
            {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
        ]),
        include_orchestrator=False,
    ))
    session_id = r1["session_id"]

    # Invoke A twice, B once, C once
    for agent, count in [("A", 2), ("B", 1), ("C", 1)]:
        for _ in range(count):
            await invoke(
                session_id=session_id,
                agent=agent,
                response=json.dumps({"response": f"{agent} speaking", "raises": [], "suggests_next": None}),
            )

    # Should be able to synthesize (3 unique agents)
    result = json.loads(await synthesize(session_id=session_id))
    assert result["action"] == "synthesize"
    assert len(result["agents_heard"]) == 3


@pytest.mark.asyncio
async def test_invoke_blocked_after_synthesize():
    """Test that invoke is blocked after synthesis."""
    r1 = json.loads(await ensemble(
        question="Test?",
        agents=json.dumps([
            {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": True},
            {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
            {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
        ]),
        include_orchestrator=False,
    ))
    session_id = r1["session_id"]

    # Complete workflow
    for agent in ["A", "B", "C"]:
        await invoke(session_id=session_id, agent=agent,
                     response=json.dumps({"response": "test", "raises": [], "suggests_next": None}))

    await synthesize(
        session_id=session_id,
        synthesis=json.dumps({
            "conclusion": "Done",
            "confidence": 1.0,
            "dissent": None,
            "key_tensions": [],
            "assumptions": [],
        }),
    )

    # Try to invoke again
    result = json.loads(await invoke(session_id=session_id, agent="A"))
    assert "error" in result
    assert "already synthesized" in result["error"]


@pytest.mark.asyncio
async def test_perturb_blocked_after_synthesize():
    """Test that perturb is blocked after synthesis."""
    r1 = json.loads(await ensemble(
        question="Test?",
        agents=json.dumps([
            {"name": "A", "role": "R", "purpose": "P", "perspective": "V", "is_chaos": True},
            {"name": "B", "role": "R", "purpose": "P", "perspective": "V"},
            {"name": "C", "role": "R", "purpose": "P", "perspective": "V"},
        ]),
        include_orchestrator=False,
    ))
    session_id = r1["session_id"]

    # Complete workflow
    for agent in ["A", "B", "C"]:
        await invoke(session_id=session_id, agent=agent,
                     response=json.dumps({"response": "test", "raises": [], "suggests_next": None}))

    await synthesize(
        session_id=session_id,
        synthesis=json.dumps({
            "conclusion": "Done",
            "confidence": 1.0,
            "dissent": None,
            "key_tensions": [],
            "assumptions": [],
        }),
    )

    # Try to perturb
    result = json.loads(await perturb(session_id=session_id, target="test"))
    assert "error" in result
    assert "already synthesized" in result["error"]
