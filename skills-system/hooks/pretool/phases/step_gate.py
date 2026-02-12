"""Step dependency gate - blocks reading step files until dependencies are satisfied.

PreToolUse hook for Read tool. When Claude tries to read a skill step file,
checks that all consumed artifacts have been produced by previously-visited steps.

Uses:
- Step file frontmatter (consumes/produces) to build dependency graph
- skill_span.steps from life.db to check which steps have been visited
"""

import json
import logging
import re
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

STEP_PATTERN = re.compile(r"/skills/([^/]+)/steps/([^/]+)\.md$")

# Module-level cache: skill_name -> {artifact: step_name}
_produces_map: dict[str, dict[str, str]] = {}
# Module-level cache: skill_name -> {step_name: [consumed_artifacts]}
_consumes_map: dict[str, dict[str, list[str]]] = {}
# Module-level cache: skill_name -> set of optional step names
_optional_steps: dict[str, set[str]] = {}

_SKILLS_DIR = Path.home() / ".claude" / "skills"

# Root inputs always satisfied — not produced by any step
ROOT_INPUTS = {"user-request"}

_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from db.connection import open_db


def _build_contracts(skill: str) -> None:
    """Parse all step files and build produces/consumes maps for a skill."""
    if skill in _produces_map:
        return

    produces: dict[str, str] = {}
    consumes: dict[str, list[str]] = {}
    optional: set[str] = set()

    steps_dir = _SKILLS_DIR / skill / "steps"
    if not steps_dir.is_dir():
        _produces_map[skill] = produces
        _consumes_map[skill] = consumes
        _optional_steps[skill] = optional
        return

    for step_file in steps_dir.glob("*.md"):
        step_name = step_file.stem
        try:
            content = step_file.read_text()
        except OSError:
            continue

        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            continue

        try:
            fm = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            continue

        for artifact in fm.get("produces", []):
            produces[artifact] = step_name
        consumes[step_name] = fm.get("consumes", [])
        if fm.get("optional"):
            optional.add(step_name)

    _produces_map[skill] = produces
    _consumes_map[skill] = consumes
    _optional_steps[skill] = optional


def _get_span_steps(skill: str, session_id: str | None = None) -> list[str] | None:
    """Get steps visited in the current active span for this skill.

    Returns None if no active span exists (editing, browsing — not invoking).
    The caller treats None as "allow" — gate only enforces during active sessions.
    """
    try:
        with open_db() as db:
            if session_id:
                row = db.execute(
                    "SELECT steps FROM skill_span "
                    "WHERE skill = ? AND status = 'active' AND session_id = ? "
                    "ORDER BY started_at DESC LIMIT 1",
                    (skill, session_id),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT steps FROM skill_span "
                    "WHERE skill = ? AND status = 'active' "
                    "ORDER BY started_at DESC LIMIT 1",
                    (skill,),
                ).fetchone()

            if not row:
                return None  # No active span — not invoking this skill
            return json.loads(row["steps"]) if row["steps"] else []
    except Exception as e:
        logger.debug("step_gate: failed to get visited steps: %s", e)
        return None


def check(ctx: dict) -> dict | None:
    """Block step reads whose dependencies haven't been visited yet.

    Returns:
        None to allow, or {"decision": "block", "reason": str} to block.
    """
    if ctx.get("tool_name") != "Read":
        return None

    file_path = ctx.get("tool_input", {}).get("file_path", "")
    match = STEP_PATTERN.search(file_path)
    if not match:
        return None

    skill, step = match.group(1), match.group(2)

    # Skip internal directories
    if skill.startswith("_"):
        return None

    # Build dependency graph
    _build_contracts(skill)

    # Get this step's consumes
    step_consumes = _consumes_map.get(skill, {}).get(step, [])
    if not step_consumes:
        return None  # No frontmatter or no consumes — allow

    # All root inputs? Always allow
    if all(c in ROOT_INPUTS for c in step_consumes):
        return None

    # Check which steps have been visited (scoped to this session)
    session_id = ctx.get("session_id")
    visited = _get_span_steps(skill, session_id=session_id)
    if visited is None:
        return None  # DB error — fail open
    produces_map = _produces_map.get(skill, {})

    # Find unsatisfied dependencies
    missing = []
    for artifact in step_consumes:
        if artifact in ROOT_INPUTS:
            continue
        producer = produces_map.get(artifact)
        if producer and producer not in visited:
            if producer in _optional_steps.get(skill, set()):
                continue  # optional step skipped — allow through
            missing.append(f"'{artifact}' (produced by '{producer}')")

    if missing:
        return {
            "decision": "block",
            "reason": f"Step '{step}' requires {', '.join(missing)}. Complete those steps first.",
        }

    return None
