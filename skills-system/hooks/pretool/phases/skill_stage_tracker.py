"""Skill stage tracker - registers planning stage when skill invoked.

Intercepts Skill tool calls for planning skills and calls begin_stage()
BEFORE the skill loads. This guarantees stage registration even when
Claude skips Python code blocks in SKILL.md files.

Also writes skill_todos.json marker for TodoWrite validation.
"""

import json
import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

PLANNING_SKILLS = {
    "planning",
    "critiquing-plans",
    "revising-plans",
    "decomposing-plans",
    "critiquing-specs",
    "revising-specs",
}

SKILL_TO_STAGE = {
    "planning": "plan",
    "critiquing-plans": "critique",
    "revising-plans": "revise-plan",
    "decomposing-plans": "plan-decompose",
    "critiquing-specs": "critique-specs",
    "revising-specs": "revise-specs",
}

# Skill file locations to search (in order)
SKILL_PATHS = [
    Path.home() / ".claude" / "skills",
    Path.home() / "claude-code" / "skills",
]


def _read_skill_frontmatter(skill: str) -> dict:
    """Read YAML frontmatter from skill's SKILL.md file."""
    for base in SKILL_PATHS:
        skill_file = base / skill / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text()
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                try:
                    return yaml.safe_load(match.group(1)) or {}
                except yaml.YAMLError:
                    pass
    return {}


def _write_skill_todos_marker(
    project: str, skill: str, required_todos: list, session_id: str | None = None
) -> None:
    """Write skill_todos.json marker to project's .planning/ directory."""
    from datetime import UTC, datetime

    project_dir = Path.home() / "projects" / project / ".planning"
    project_dir.mkdir(parents=True, exist_ok=True)

    marker = project_dir / "skill_todos.json"
    validated_marker = project_dir / "skill_validated"

    # Remove old validated marker (fresh start for new skill invocation)
    if validated_marker.exists():
        validated_marker.unlink()

    marker_data = {
        "skill": skill,
        "required_todos": required_todos,
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": session_id,
    }
    marker.write_text(json.dumps(marker_data, indent=2))
    logger.info(
        "skill_todos marker WRITE: skill=%s session=%s path=%s",
        skill,
        session_id[:12] if session_id else "none",
        marker,
    )


def check(ctx: dict) -> dict | None:
    """Check Skill tool invocations and register planning stages."""
    if ctx.get("tool_name") != "Skill":
        return None

    tool_input = ctx.get("tool_input", {})
    skill = tool_input.get("skill", "")

    if skill not in PLANNING_SKILLS:
        return None

    args = tool_input.get("args", "").strip()
    if not args:
        return None  # No project to track

    project = args.split()[0]
    stage = SKILL_TO_STAGE[skill]

    try:
        from formaltask.db.path import get_db_path
        from formaltask.epics.planning import begin_stage

        begin_stage(project, stage, get_db_path())
        logger.debug("Registered stage %s for project %s", stage, project)
    except Exception as e:
        logger.debug("Stage registration failed: %s", e)

    # Write skill todos marker for TodoWrite validation
    try:
        frontmatter = _read_skill_frontmatter(skill)
        required_todos = frontmatter.get("required_todos", [])
        if required_todos:
            session_id = ctx.get("session_id")
            _write_skill_todos_marker(project, skill, required_todos, session_id)
    except Exception as e:
        logger.debug("Skill todos marker failed: %s", e)

    return None  # Always allow
