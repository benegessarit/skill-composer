"""Skill todo validator - validates TodoWrite against skill's required_todos.

Enforces that planning skills create todos matching their required_todos
before proceeding. Uses marker files in project's .planning/ directory.

Separate from worker validation (todowrite_validator.py) - only fires when:
1. Not in a worker context (no .task/ dir)
2. skill_todos.json marker exists
3. skill_validated marker does NOT exist
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_worker(ctx: dict) -> bool:
    """Check if we're in a worker context (.task/ dir exists)."""
    cwd = ctx.get("cwd")
    if not cwd:
        return False
    task_dir = Path(cwd) / ".task"
    return (task_dir / "id").is_file()


def _find_planning_dir(ctx: dict) -> Path | None:
    """Find .planning/ dir from cwd or projects directory."""
    cwd = ctx.get("cwd")
    if not cwd:
        return None

    # Check cwd/.planning/
    planning_dir = Path(cwd) / ".planning"
    if planning_dir.exists():
        return planning_dir

    # Check if cwd is under ~/projects/{project}/
    cwd_path = Path(cwd)
    projects_dir = Path.home() / "projects"
    try:
        relative = cwd_path.relative_to(projects_dir)
        project = relative.parts[0] if relative.parts else None
        if project:
            planning_dir = projects_dir / project / ".planning"
            if planning_dir.exists():
                return planning_dir
    except ValueError:
        pass  # cwd not under ~/projects/

    return None


def _step_present(todos: list[dict], step: str) -> bool:
    """Check if any todo contains all words from the step name.

    Fuzzy match: "Codebase context" matches "Gather codebase context using MCP"
    """
    words = step.lower().split()
    return any(all(w in t.get("content", "").lower() for w in words) for t in todos)


def check(ctx: dict) -> dict | None:
    """Validate TodoWrite against skill's required_todos.

    Returns:
        None to allow, or {"decision": "block", "reason": str} to block.
    """
    if ctx.get("tool_name") != "TodoWrite":
        return None

    # Skip workers (handled by todowrite_validator.py)
    if _is_worker(ctx):
        return None

    # Find .planning/ directory
    planning_dir = _find_planning_dir(ctx)
    if not planning_dir:
        return None

    # Check for skill_todos.json marker
    marker = planning_dir / "skill_todos.json"
    if not marker.exists():
        return None

    # Already validated?
    validated = planning_dir / "skill_validated"
    if validated.exists():
        return None

    # Load required todos
    try:
        data = json.loads(marker.read_text())
        skill = data.get("skill", "unknown")
        required = data.get("required_todos", [])
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to read skill_todos.json: %s", e)
        return None

    if not required:
        return None

    # Validate todos
    todos = ctx.get("tool_input", {}).get("todos", [])
    missing = [step for step in required if not _step_present(todos, step)]

    if missing:
        return {
            "decision": "block",
            "reason": f"Skill '{skill}' requires these TodoWrite steps: {missing}. Add them before proceeding.",
        }

    # Validation passed - create marker
    try:
        validated.touch()
        logger.debug("Skill todo validation passed for %s", skill)
    except OSError as e:
        logger.debug("Failed to create skill_validated marker: %s", e)

    return None
