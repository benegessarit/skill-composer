"""Reasoning MCP server.

Enforces multi-turn ensemble reasoning: Claude generates personas,
role-plays each in separate turns, then synthesizes.
"""
import json
import re
import uuid
from typing import Literal

from mcp.server.fastmcp import FastMCP

from reasoning_mcp.models import Agent, Invocation, Perturbation, Session
from reasoning_mcp.prompts import (
    CHAOS_INSTRUCTION,
    DEPTH_PROBE_PROMPT,
    ENSEMBLE_PROMPT,
    INVOKE_PROMPT,
    ORCHESTRATOR_INSTRUCTION,
    ORCHESTRATOR_INVOKE_PROMPT,
    PERTURB_PROMPT,
    PERTURBATIONS_CONTEXT,
    PAUSE_PROMPT,
    PLAN_PROBE_PROMPT,
    PLAN_PROMPT_TEMPLATE,
    PRIOR_CONTEXT_TEMPLATE,
    SURFACE_PROMPT,
    SYNTHESIZE_PROMPT,
)

mcp = FastMCP("reasoning_mcp")
sessions: dict[str, Session] = {}
MAX_SESSIONS = 100


def _json(obj: dict) -> str:
    return json.dumps(obj, indent=2)


def _normalize_json(value: str | dict | list) -> dict | list:
    """Normalize JSON input - handles both strings and already-parsed objects.

    MCP clients may pass JSON as strings OR as already-parsed dicts/lists.
    This function handles both cases uniformly.
    """
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def _extract_phases(prompt_text: str) -> list[str]:
    """Extract phase names from an optimized prompt.

    Tries XML-style <phase name="...">, then FLOW line [PHASE] -> [PHASE].
    Returns empty list if no phases found.
    """
    xml_phases = re.findall(r'<phase\s+name="([^"]+)"', prompt_text)
    if xml_phases:
        return xml_phases

    flow_match = re.search(r'FLOW:\s*(.+)', prompt_text)
    if flow_match:
        flow_phases = re.findall(r'\[([^\]]+)\]', flow_match.group(1))
        if flow_phases:
            return flow_phases

    return []


def _parse_agents(agents_input: str | dict | list) -> list[Agent]:
    """Parse agents from JSON string or already-parsed object."""
    data = _normalize_json(agents_input)

    if isinstance(data, dict) and "agents" in data:
        agents_list = data["agents"]
    elif isinstance(data, list):
        agents_list = data
    else:
        raise ValueError("Expected JSON array of agents or object with 'agents' key")

    agents = []
    for i, a in enumerate(agents_list):
        if not isinstance(a, dict):
            raise ValueError(f"Agent {i} must be an object")
        for field in ("name", "role", "purpose", "perspective"):
            if field not in a:
                raise ValueError(f"Agent {i} missing required field '{field}'")
        agents.append(Agent(
            name=a["name"],
            role=a["role"],
            purpose=a["purpose"],
            perspective=a["perspective"],
            is_chaos=a.get("is_chaos", False),
            is_orchestrator=a.get("is_orchestrator", False),
        ))
    return agents


def _collect_unanswered_questions(session: Session) -> list[str]:
    """Collect questions raised but not addressed in subsequent invocations."""
    all_raised: list[str] = []

    for idx, inv in enumerate(session.invocations):
        for q in inv.raises:
            keywords = [w for w in q.lower().split() if len(w) > 3]
            if not keywords:
                continue
            # Only check responses AFTER this invocation
            later_responses = " ".join(
                later.response.lower()
                for later in session.invocations[idx + 1:]
            )
            # Require at least half the keywords matched (word-boundary)
            matched = sum(
                1 for kw in keywords
                if re.search(r'\b' + re.escape(kw) + r'\b', later_responses)
            )
            if matched < len(keywords) / 2:
                all_raised.append(f"{inv.agent} asked: {q}")

    return all_raised


def _format_invocations(invocations: list[Invocation]) -> str:
    """Format invocations for context."""
    if not invocations:
        return "(No prior discussion)"
    lines = []
    for inv in invocations:
        lines.append(f"**{inv.agent}**: {inv.response}")
        if inv.raises:
            lines.append(f"  Raised: {', '.join(inv.raises)}")
    return "\n\n".join(lines)


def _format_perturbations(perturbations: list[Perturbation]) -> str:
    """Format perturbations for context."""
    if not perturbations:
        return ""
    lines = []
    for p in perturbations:
        lines.append(f"- **{p.target}** ({p.mode}): {p.impact} — {p.explanation}")
    return PERTURBATIONS_CONTEXT.format(perturbations="\n".join(lines))


@mcp.tool()
async def ensemble(
    question: str,
    agents: str | dict | list | None = None,
    min_agents: int = 3,
    include_chaos: bool = True,
    include_orchestrator: bool = True,
) -> str:
    """Generate or register an ensemble of personas for reasoning about a question.

    Call without agents to get the generation prompt.
    Call with agents JSON to register the ensemble and get session ID.

    Args:
        question: The question/problem to reason about
        agents: JSON string of generated agents (call without this first to get prompt)
        min_agents: Minimum personas required (default 3)
        include_chaos: Whether to require a chaos/perturbation agent (default True)
        include_orchestrator: Whether to require an orchestrator agent (default True)

    Returns:
        Without agents: Prompt for generating personas
        With agents: Session info including session_id and registered agents
    """
    if agents is None:
        # Return prompt for generating personas
        chaos_instruction = CHAOS_INSTRUCTION if include_chaos else ""
        orchestrator_instruction = ORCHESTRATOR_INSTRUCTION if include_orchestrator else ""
        prompt = ENSEMBLE_PROMPT.format(
            question=question,
            min_agents=min_agents,
            chaos_instruction=chaos_instruction,
            orchestrator_instruction=orchestrator_instruction,
        )
        return _json({
            "action": "generate_personas",
            "prompt": prompt,
            "next_step": "Call ensemble again with the 'agents' parameter containing your generated JSON",
        })

    # Parse and validate agents
    parsed_agents = _parse_agents(agents)

    if len(parsed_agents) < min_agents:
        return _json({
            "error": f"Need at least {min_agents} agents, got {len(parsed_agents)}",
            "action": "Add more personas with distinct perspectives",
        })

    if include_chaos and not any(a.is_chaos for a in parsed_agents):
        return _json({
            "error": "Missing chaos/perturbation agent (is_chaos: true)",
            "action": "Add one agent with is_chaos: true to stress-test assumptions",
        })

    if include_orchestrator and not any(a.is_orchestrator for a in parsed_agents):
        return _json({
            "error": "Missing orchestrator agent (is_orchestrator: true)",
            "action": "Add one agent with is_orchestrator: true to assess discussion progress and push for depth",
        })

    # Evict oldest synthesized session if at capacity (prefer completed over active)
    if len(sessions) >= MAX_SESSIONS:
        victim = next((sid for sid, s in sessions.items() if s.synthesized), None)
        if victim is None:
            victim = next(iter(sessions))  # fallback: oldest regardless
        sessions.pop(victim)

    # Create session
    session_id = str(uuid.uuid4())[:8]
    session = Session(
        id=session_id,
        question=question,
        agents=parsed_agents,
        min_agents=min_agents,
    )
    sessions[session_id] = session

    chaos_agent = next((a.name for a in parsed_agents if a.is_chaos), None)
    orchestrator_agent = next((a.name for a in parsed_agents if a.is_orchestrator), None)

    return _json({
        "session_id": session_id,
        "agents": [a.to_dict() for a in parsed_agents],
        "suggested_order": [a.name for a in parsed_agents],
        "chaos_agent": chaos_agent,
        "orchestrator_agent": orchestrator_agent,
        "next_step": f"Call invoke with session_id='{session_id}' and agent='<name>' to role-play each persona",
    })


@mcp.tool()
async def invoke(
    session_id: str,
    agent: str,
    response: str | dict | None = None,
    context: str | None = None,
) -> str:
    """Role-play as a specific persona for ONE turn.

    Call without response to get the role-play prompt.
    Call with response JSON to register the invocation.

    Args:
        session_id: Session ID from ensemble()
        agent: Name of the persona to invoke
        response: JSON string of the agent's response (call without this first to get prompt)
        context: Optional additional context for this turn

    Returns:
        Without response: Prompt for role-playing this persona
        With response: Confirmation and suggestion for next step
    """
    if session_id not in sessions:
        return _json({"error": f"Session '{session_id}' not found"})

    session = sessions[session_id]

    if session.synthesized:
        return _json({"error": "Session already synthesized. Start a new session for new questions."})

    agent_obj = next((a for a in session.agents if a.name == agent), None)
    if agent_obj is None:
        available = [a.name for a in session.agents]
        return _json({
            "error": f"Agent '{agent}' not in ensemble",
            "available_agents": available,
        })

    if response is None:
        # Return prompt for role-playing
        prior_context = _format_invocations(session.invocations) if session.invocations else "(No prior discussion)"

        # Use special prompt for orchestrator
        if agent_obj.is_orchestrator:
            agents_spoken = list(set(i.agent for i in session.invocations))
            available_agents = [a.name for a in session.agents if not a.is_orchestrator]
            unanswered = _collect_unanswered_questions(session)

            prompt = ORCHESTRATOR_INVOKE_PROMPT.format(
                question=session.question,
                prior_context=prior_context,
                available_agents=", ".join(available_agents),
                agents_spoken=", ".join(agents_spoken) if agents_spoken else "(none yet)",
                unanswered_questions="\n".join(f"- {q}" for q in unanswered) if unanswered else "(none tracked)",
            )
        else:
            formatted_prior = ""
            if session.invocations:
                formatted_prior = PRIOR_CONTEXT_TEMPLATE.format(invocations=prior_context)

            prompt = INVOKE_PROMPT.format(
                agent_name=agent_obj.name,
                agent_role=agent_obj.role,
                agent_purpose=agent_obj.purpose,
                agent_perspective=agent_obj.perspective,
                question=session.question,
                prior_context=formatted_prior,
                additional_context=context or "",
            )

        return _json({
            "action": "role_play" if not agent_obj.is_orchestrator else "orchestrate",
            "agent": agent_obj.to_dict(),
            "prompt": prompt,
            "invocations_so_far": len(session.invocations),
            "next_step": f"Role-play as {agent}, then call invoke again with 'response' parameter containing JSON",
        })

    # Parse and register response
    try:
        data = _normalize_json(response)
    except ValueError as e:
        return _json({"error": f"Invalid response JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Response must be a JSON object, not an array"})

    if "response" not in data:
        return _json({"error": "Response JSON must include 'response' field"})

    invocation = Invocation(
        agent=agent,
        response=data["response"],
        raises=data.get("raises", []),
        suggests_next=data.get("suggests_next"),
    )
    session.invocations.append(invocation)

    unique_agents = set(i.agent for i in session.invocations)
    can_synthesize = len(unique_agents) >= session.min_agents

    result: dict = {
        "registered": True,
        "agent": agent,
        "invocation_number": len(session.invocations),
        "unique_agents_invoked": len(unique_agents),
        "min_agents_required": session.min_agents,
        "can_synthesize": can_synthesize,
    }

    if invocation.raises:
        result["raises"] = invocation.raises

    if invocation.suggests_next:
        if invocation.suggests_next.lower() == "synthesize":
            if can_synthesize:
                result["next_step"] = f"Call synthesize(session_id='{session_id}')"
            else:
                result["next_step"] = f"Need {session.min_agents - len(unique_agents)} more unique agents before synthesize"
        else:
            result["suggests_next"] = invocation.suggests_next
            result["next_step"] = f"Call invoke with agent='{invocation.suggests_next}'"
    else:
        remaining = [a.name for a in session.agents if a.name not in unique_agents]
        if remaining:
            result["remaining_agents"] = remaining
            result["next_step"] = f"Continue with: {remaining[0]} or another agent"
        elif can_synthesize:
            result["next_step"] = f"All agents heard. Call synthesize(session_id='{session_id}')"

    return _json(result)


@mcp.tool()
async def perturb(
    session_id: str,
    target: str,
    mode: Literal["negate", "remove", "extreme", "opposite"] = "negate",
    result: str | dict | None = None,
) -> str:
    """Apply chaos engineering to test reasoning robustness.

    Call without result to get the perturbation prompt.
    Call with result JSON to register the perturbation.

    Args:
        session_id: Session ID from ensemble()
        target: The assumption/claim to perturb
        mode: Perturbation mode (negate, remove, extreme, opposite)
        result: JSON string of perturbation result (call without this first to get prompt)

    Returns:
        Without result: Prompt for applying the perturbation
        With result: Confirmation of registered perturbation
    """
    if session_id not in sessions:
        return _json({"error": f"Session '{session_id}' not found"})

    session = sessions[session_id]

    if session.synthesized:
        return _json({"error": "Session already synthesized"})

    if result is None:
        # Return prompt for perturbation
        context = _format_invocations(session.invocations)
        prompt = PERTURB_PROMPT.format(
            target=target,
            mode=mode,
            context=context,
        )

        return _json({
            "action": "perturb",
            "target": target,
            "mode": mode,
            "prompt": prompt,
            "next_step": "Apply perturbation, then call perturb again with 'result' parameter containing JSON",
        })

    # Parse and register perturbation
    try:
        data = _normalize_json(result)
    except ValueError as e:
        return _json({"error": f"Invalid result JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Result must be a JSON object, not an array"})

    for field in ("perturbation", "impact", "explanation"):
        if field not in data:
            return _json({"error": f"Result JSON must include '{field}' field"})

    if data["impact"] not in ("survives", "breaks", "weakens"):
        return _json({"error": "impact must be 'survives', 'breaks', or 'weakens'"})

    perturbation = Perturbation(
        target=target,
        mode=mode,
        impact=data["impact"],
        explanation=data["explanation"],
    )
    session.perturbations.append(perturbation)

    return _json({
        "registered": True,
        "perturbation_number": len(session.perturbations),
        "target": target,
        "impact": data["impact"],
        "next_step": "Continue invoking agents, perturb more assumptions, or synthesize when ready",
    })


@mcp.tool()
async def synthesize(
    session_id: str,
    synthesis: str | dict | None = None,
) -> str:
    """Forced synthesis of all perspectives into a conclusion.

    Call without synthesis to get the synthesis prompt (blocked until min_agents invoked).
    Call with synthesis JSON to complete the session.

    Args:
        session_id: Session ID from ensemble()
        synthesis: JSON string of synthesis result (call without this first to get prompt)

    Returns:
        Without synthesis: Prompt for synthesizing perspectives
        With synthesis: Final session summary
    """
    if session_id not in sessions:
        return _json({"error": f"Session '{session_id}' not found"})

    session = sessions[session_id]

    if session.synthesized:
        return _json({"error": "Session already synthesized"})

    # Enforce min_agents
    unique_agents = set(i.agent for i in session.invocations)
    if len(unique_agents) < session.min_agents:
        return _json({
            "error": f"Must invoke at least {session.min_agents} unique agents before synthesizing",
            "invoked": list(unique_agents),
            "count": len(unique_agents),
            "required": session.min_agents,
            "remaining": [a.name for a in session.agents if a.name not in unique_agents],
        })

    if synthesis is None:
        # Return prompt for synthesis
        invocations_text = _format_invocations(session.invocations)
        perturbations_text = _format_perturbations(session.perturbations)

        prompt = SYNTHESIZE_PROMPT.format(
            question=session.question,
            invocations=invocations_text,
            perturbations=perturbations_text,
        )

        return _json({
            "action": "synthesize",
            "agents_heard": list(unique_agents),
            "perturbations_applied": len(session.perturbations),
            "prompt": prompt,
            "next_step": "Synthesize all perspectives, then call synthesize again with 'synthesis' parameter containing JSON",
        })

    # Parse and complete session
    try:
        data = _normalize_json(synthesis)
    except ValueError as e:
        return _json({"error": f"Invalid synthesis JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Synthesis must be a JSON object, not an array"})

    for field in ("conclusion", "confidence", "key_tensions", "assumptions"):
        if field not in data:
            return _json({"error": f"Synthesis JSON must include '{field}' field"})

    session.synthesized = True

    return _json({
        "workflow_complete": True,
        "session_id": session_id,
        "question": session.question,
        "conclusion": data["conclusion"],
        "confidence": data["confidence"],
        "dissent": data.get("dissent"),
        "key_tensions": data["key_tensions"],
        "assumptions": data["assumptions"],
        "agents_heard": [i.agent for i in session.invocations],
        "total_invocations": len(session.invocations),
        "perturbations_applied": len(session.perturbations),
    })


@mcp.tool()
async def get_session_state(session_id: str) -> str:
    """Get current state of a reasoning session.

    Args:
        session_id: Session ID from ensemble()

    Returns:
        Session state including agents, invocations, and progress
    """
    if session_id not in sessions:
        return _json({"error": f"Session '{session_id}' not found"})

    session = sessions[session_id]
    unique_agents = set(i.agent for i in session.invocations)

    return _json({
        "session_id": session_id,
        "question": session.question,
        "agents": [a.to_dict() for a in session.agents],
        "invocations": [
            {"agent": i.agent, "raises": i.raises, "suggests_next": i.suggests_next}
            for i in session.invocations
        ],
        "perturbations": [
            {"target": p.target, "mode": p.mode, "impact": p.impact}
            for p in session.perturbations
        ],
        "unique_agents_invoked": len(unique_agents),
        "min_agents_required": session.min_agents,
        "can_synthesize": len(unique_agents) >= session.min_agents,
        "synthesized": session.synthesized,
    })


@mcp.tool()
async def depth_probe(
    question: str,
    result: str | dict | None = None,
) -> str:
    """Metacognitive audit of reasoning process before executing.

    Forces examination of the thinking itself: Is the framing right? What kind of
    reasoning is needed? Where will analysis be shallow? What's missing?

    Call without result to get the self-interrogation prompt.
    Call with result JSON to capture the reflection.

    Args:
        question: The question/problem to probe
        result: JSON with reframing, thinking_required, shallow_spots, missing_dimensions, process_critique

    Returns:
        Without result: Prompt for meta-reasoning audit
        With result: The captured reflection
    """
    if result is None:
        return _json({
            "action": "depth_probe",
            "prompt": DEPTH_PROBE_PROMPT.format(question=question),
            "next_step": "Audit your reasoning process, then call depth_probe with result JSON",
        })

    try:
        data = _normalize_json(result)
    except ValueError as e:
        return _json({"error": f"Invalid result JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Result must be a JSON object"})

    required = ("reframing", "thinking_required", "shallow_spots", "missing_dimensions", "process_critique")
    for field in required:
        if field not in data:
            return _json({"error": f"Missing required field: '{field}'"})

    return _json({
        "probed": True,
        "reframing": data["reframing"],
        "thinking_required": data["thinking_required"],
        "shallow_spots": data["shallow_spots"],
        "missing_dimensions": data["missing_dimensions"],
        "process_critique": data["process_critique"],
    })


HEDGE_WORDS = {"it depends", "on one hand", "on the other hand", "arguably", "perhaps", "might be"}


@mcp.tool()
async def plan_probe(
    plan: str,
    result: str | dict | None = None,
) -> str:
    """Inventory domain content before execution begins.

    Forces an honest audit of what you actually know, believe, and will fake
    for each phase of a plan. Catches structural compliance masquerading as
    cognitive depth.

    Call without result to get the self-interrogation prompt.
    Call with result JSON to validate the inventory.

    Args:
        plan: The execution plan (phases with weights/depths) or optimized prompt
        result: JSON with phases[], phone_in_phase, expert_flag

    Returns:
        Without result: Prompt for auditing readiness
        With result: Validated inventory or specific error
    """
    if result is None:
        return _json({
            "action": "plan_probe",
            "prompt": PLAN_PROBE_PROMPT.format(plan=plan),
            "next_step": "Audit your readiness for each phase, then call plan_probe with result JSON",
        })

    try:
        data = _normalize_json(result)
    except ValueError as e:
        return _json({"error": f"Invalid result JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Result must be a JSON object"})

    for field in ("phases", "phone_in_phase", "expert_flag"):
        if field not in data:
            return _json({"error": f"Missing required field: '{field}'"})

    phases = data["phases"]
    if not isinstance(phases, list) or len(phases) == 0:
        return _json({"error": "'phases' must be a non-empty array"})

    substance_count = 0
    for i, phase in enumerate(phases):
        if not isinstance(phase, dict):
            return _json({"error": f"phases[{i}] must be an object"})

        for field in ("phase", "know", "take", "gaps", "has_substance"):
            if field not in phase:
                return _json({"error": f"phases[{i}] missing required field: '{field}'"})

        if not isinstance(phase["know"], list):
            return _json({"error": f"phases[{i}] 'know' must be an array"})

        if not isinstance(phase["gaps"], list):
            return _json({"error": f"phases[{i}] 'gaps' must be an array"})

        # Anti-hedge: take must be a position, not a dodge
        take = str(phase["take"]).lower()
        for hedge in HEDGE_WORDS:
            if re.search(r'\b' + re.escape(hedge) + r'\b', take):
                return _json({
                    "error": f"phases[{i}] 'take' contains hedge '{hedge}' — state a position or say 'no position'",
                    "hint": "What would you bet on? One sentence. No balancing.",
                })

        if phase.get("has_substance"):
            substance_count += 1

    return _json({
        "probed": True,
        "phase_count": len(phases),
        "substance_count": substance_count,
        "hollow_count": len(phases) - substance_count,
        "phone_in_phase": data["phone_in_phase"],
        "expert_flag": data["expert_flag"],
        "next_step": "Execute the plan. Phases with has_substance: false — acknowledge gaps honestly.",
    })


@mcp.tool()
async def pause(
    phase_completed: str,
    result: str | dict | None = None,
) -> str:
    """Mid-execution restart test between phases.

    Forces a cognitive pause: knowing what you now know, would you change
    the remaining phases? The MCP round-trip IS the intervention — it
    interrupts momentum and forces re-evaluation.

    Call without result to get the restart test prompt.
    Call with result JSON to validate the reflection.

    Args:
        phase_completed: Name of the phase just finished
        result: JSON with restart, next_phase_still_valid
    """
    if result is None:
        return _json({
            "action": "pause",
            "phase_completed": phase_completed,
            "prompt": PAUSE_PROMPT,
            "next_step": "Reflect on what you learned, then call pause with result JSON",
        })

    try:
        data = _normalize_json(result)
    except ValueError as e:
        return _json({"error": f"Invalid result JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Result must be a JSON object"})

    for field in ("restart", "next_phase_still_valid"):
        if field not in data:
            return _json({"error": f"Missing required field: '{field}'"})

    restart = str(data["restart"]).strip()
    if not restart:
        return _json({"error": "'restart' must not be empty"})

    valid = data["next_phase_still_valid"]
    if not isinstance(valid, bool):
        return _json({"error": "'next_phase_still_valid' must be a boolean"})

    # If "nothing" — must explain why
    if restart.lower().startswith("nothing") and "—" not in restart and "-" not in restart:
        return _json({
            "error": "'nothing' requires a reason — 'nothing — [why you're sure]'",
            "hint": "Certainty without justification is the thing this tool catches.",
        })

    # If next phase invalid — restart must describe a specific change
    if not valid and len(restart.split()) < 5:
        return _json({
            "error": "next_phase_still_valid is false but restart is too vague — describe the specific change",
        })

    return _json({
        "paused": True,
        "phase_completed": phase_completed,
        "next_phase_still_valid": valid,
        "restart": restart,
    })


def _word_overlap(a: str, b: str) -> float:
    """Fraction of shared words between two strings (Jaccard on word sets)."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


@mcp.tool()
async def surface(
    question: str,
    result: str | dict | None = None,
) -> str:
    """Mid-execution blind spot check. Lists what your momentum is hiding.

    Call without result to get the self-interrogation prompt.
    Call with result JSON to validate and register the surfacing.

    Args:
        question: The current phase or constraint being worked on
        result: JSON with blind_spots[], tension, decision

    Returns:
        Without result: Prompt for surfacing blind spots
        With result: Validated surfacing or specific error
    """
    if result is None:
        return _json({
            "action": "surface",
            "context": question,
            "prompt": SURFACE_PROMPT,
            "next_step": "Surface your blind spots, then call surface with result JSON",
        })

    try:
        data = _normalize_json(result)
    except ValueError as e:
        return _json({"error": f"Invalid result JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Result must be a JSON object"})

    for field in ("blind_spots", "tension", "decision"):
        if field not in data:
            return _json({"error": f"Missing required field: '{field}'"})

    spots = data["blind_spots"]
    if not isinstance(spots, list):
        return _json({"error": "'blind_spots' must be an array"})

    if len(spots) < 2:
        return _json({"error": f"Need at least 2 blind spots, got {len(spots)}"})

    # Validate each blind spot
    for i, spot in enumerate(spots):
        if not isinstance(spot, dict):
            return _json({"error": f"blind_spots[{i}] must be an object"})
        if "what" not in spot:
            return _json({"error": f"blind_spots[{i}] missing 'what'"})
        if "type" not in spot:
            return _json({"error": f"blind_spots[{i}] missing 'type'"})
        if spot["type"] not in ("assumption", "omission", "scope"):
            return _json({"error": f"blind_spots[{i}] type must be assumption|omission|scope, got '{spot['type']}'"})

    # Check for duplicate blind spots (>70% word overlap)
    whats = [s["what"] for s in spots]
    for i in range(len(whats)):
        for j in range(i + 1, len(whats)):
            overlap = _word_overlap(whats[i], whats[j])
            if overlap > 0.7:
                return _json({
                    "error": f"blind_spots[{i}] and [{j}] are too similar ({overlap:.0%} word overlap)",
                    "spot_a": whats[i],
                    "spot_b": whats[j],
                    "hint": "Each blind spot must be genuinely different, not a restatement",
                })

    # Tension must reference at least one blind spot
    tension = data["tension"]
    tension_words = set(tension.lower().split())
    connected = any(
        tension_words & set(s["what"].lower().split())
        for s in spots
    )
    if not connected:
        return _json({
            "error": "Tension must reference at least one blind spot — no shared words found",
            "tension": tension,
            "hint": "The tension should name the pull between two specific blind spots",
        })

    # Decision must be valid
    decision = data["decision"]
    if decision not in ("continue", "redirect", "stop"):
        return _json({"error": f"decision must be continue|redirect|stop, got '{decision}'"})

    return _json({
        "surfaced": True,
        "blind_spot_count": len(spots),
        "decision": decision,
    })


@mcp.tool()
async def plan_prompt(
    optimized_prompt: str,
    result: str | dict | None = None,
) -> str:
    """Create a weighted execution plan from an optimized prompt.

    Forces a cognitive role switch from prompt author to execution planner.
    Claude must allocate a 100-point weight budget across phases, forcing
    trade-off decisions that require genuine re-engagement with the prompt.

    Call without result to get the planning template.
    Call with result JSON to validate the plan.

    Args:
        optimized_prompt: The optimized prompt text to plan execution for
        result: JSON with phases array (call without this first to get template)

    Returns:
        Without result: Planning template with detected phases and budget rules
        With result: Validated plan or specific validation error
    """
    phases = _extract_phases(optimized_prompt)
    phase_count = len(phases)

    if result is None:
        if phases:
            phase_section = f"{phase_count} PHASES DETECTED:\n" + "\n".join(
                f"  {i}. {name}" for i, name in enumerate(phases, 1)
            )
        else:
            phase_section = (
                "PHASES: Count the phases in the prompt above. "
                "Include one entry per phase."
            )

        prompt = PLAN_PROMPT_TEMPLATE.format(
            prompt_text=optimized_prompt,
            phase_section=phase_section,
        )

        return _json({
            "action": "plan_prompt",
            "phases_detected": phases,
            "phase_count": phase_count,
            "prompt": prompt,
            "next_step": "Budget and plan each phase, then call plan_prompt with result JSON",
        })

    # --- Validate the plan ---
    try:
        data = _normalize_json(result)
    except ValueError as e:
        return _json({"error": f"Invalid result JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Result must be a JSON object"})

    if "phases" not in data:
        return _json({"error": "Result must include 'phases' array"})

    plan_phases = data["phases"]
    if not isinstance(plan_phases, list):
        return _json({"error": "'phases' must be an array"})

    if len(plan_phases) == 0:
        return _json({"error": "'phases' must not be empty"})

    # Phase count check (only if we detected phases)
    if phase_count > 0 and len(plan_phases) != phase_count:
        return _json({
            "error": f"Phase count mismatch: prompt has {phase_count} phases, plan has {len(plan_phases)}",
            "expected": phase_count,
            "got": len(plan_phases),
        })

    # Validate each phase
    required_fields = ("phase", "name", "weight", "produces", "depends_on", "skip_if")
    generic_produces = {"results", "analysis", "output", "summary", "n/a", "none", "tbd", ""}
    weights: list[float] = []

    for i, phase in enumerate(plan_phases):
        if not isinstance(phase, dict):
            return _json({"error": f"Phase {i + 1} must be an object"})

        for field in required_fields:
            if field not in phase:
                return _json({"error": f"Phase {i + 1} missing required field: '{field}'"})

        # Weight must be a positive number
        w = phase["weight"]
        if not isinstance(w, (int, float)):
            return _json({"error": f"Phase {i + 1} weight must be a number, got {type(w).__name__}"})
        if w <= 0:
            return _json({"error": f"Phase {i + 1} weight must be positive"})
        weights.append(float(w))

        # Auto-calculate depth from weight
        if w >= 30:
            phase["depth"] = "deep"
        elif w >= 15:
            phase["depth"] = "medium"
        else:
            phase["depth"] = "shallow"

        # Produces must be specific
        produces_val = str(phase["produces"]).strip().lower()
        if produces_val in generic_produces:
            return _json({
                "error": f"Phase {i + 1} 'produces' must specify exact format, not '{phase['produces']}'",
            })

    # Weights must sum to 100
    weight_sum = sum(weights)
    if abs(weight_sum - 100) > 1:
        return _json({
            "error": f"Weights must sum to 100, got {weight_sum}",
        })

    # No duplicate weights
    if len(set(weights)) != len(weights):
        return _json({
            "error": "No two phases can have the same weight — allocation requires real trade-offs",
            "weights": weights,
        })

    # Max/min spread >= 3x
    max_w = max(weights)
    min_w = min(weights)
    if min_w > 0 and max_w / min_w < 3:
        return _json({
            "error": f"Highest weight ({max_w}) must be >=3x lowest ({min_w}) — spread is only {max_w / min_w:.1f}x",
            "hint": "Some phases need more depth than others. Commit to the difference.",
        })

    return _json({
        "planned": True,
        "phase_count": len(plan_phases),
        "phases": plan_phases,
        "next_step": "Execute the plan phase by phase. The plan is the contract — weight determines effort.",
    })


@mcp.tool()
async def audit_probe(
    execution_frame: str,
    audit_frame: str,
    result: str | dict,
) -> str:
    """Asymmetric audit of completed reasoning from a different cognitive frame.

    1-call tool — no pre-prompt, no frame contamination. Validates that the
    audit uses a different cognitive lens than the execution, preventing
    echo-chamber self-review.

    Args:
        execution_frame: Frame used during execution (e.g., "analysis", "comparison")
        audit_frame: DIFFERENT frame for auditing (e.g., "synthesis", "pre-mortem")
        result: JSON with execution_summary, gaps, vulnerability, revision
    """
    exec_norm = execution_frame.lower().strip()
    audit_norm = audit_frame.lower().strip()

    if exec_norm == audit_norm:
        return _json({
            "error": "execution_frame and audit_frame must differ — same-frame review is an echo chamber",
            "hint": "If you analyzed, try synthesis. If you compared, try inversion. If you recommended, try pre-mortem.",
        })

    try:
        data = _normalize_json(result)
    except ValueError as e:
        return _json({"error": f"Invalid result JSON: {e}"})

    if not isinstance(data, dict):
        return _json({"error": "Result must be a JSON object"})

    required = ("execution_summary", "gaps", "vulnerability", "revision")
    for field in required:
        if field not in data:
            return _json({"error": f"Missing required field: '{field}'"})

    return _json({
        "audited": True,
        "execution_frame": execution_frame,
        "audit_frame": audit_frame,
        **{k: data[k] for k in required},
    })
