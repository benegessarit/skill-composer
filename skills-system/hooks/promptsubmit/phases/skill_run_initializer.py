"""Phase: SkillRun initialization for CLI skill invocations.

Creates SkillRun when user invokes a skill via /skill-name that has
uses_skill_run: true in frontmatter. This handles the CLI case;
PreToolUse handles when Claude invokes skills programmatically.

Guarantees:
1. Breadcrumb creation for contract validation (stop hook)
2. Path injection via additionalContext
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# File-based logging for debugging
LOG_FILE = Path.home() / ".claude" / "tmp" / "skill-run-initializer.log"

# Skill file locations to search (in order)
SKILL_PATHS = [
    Path.home() / ".claude" / "skills",
    Path.home() / "claude-code" / "skills",
]


def _log(message: str) -> None:
    """Append timestamped message to log file."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] [promptsubmit] {message}\n")
    except OSError:
        pass


def _read_skill_file(skill: str) -> tuple[dict, str]:
    """Read skill's SKILL.md file, return (frontmatter, content)."""
    for base in SKILL_PATHS:
        skill_file = base / skill / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text()
            match = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
            if match:
                try:
                    frontmatter = yaml.safe_load(match.group(1)) or {}
                    body = match.group(2)
                    return frontmatter, body
                except yaml.YAMLError:
                    return {}, content
            return {}, content
    return {}, ""


def _extract_phases_from_content(content: str) -> list[str]:
    """Extract phase names from ## Phase N: Name headers.

    Runtime extraction - no build step needed. Skills just write
    ## Phase 1: Name headers and enforcement happens automatically.
    """
    matches = re.findall(r"^## Phase \d+:\s*(.+)$", content, re.MULTILINE)
    phases = []
    for match in matches:
        if "(optional)" in match.lower():
            continue
        normalized = match.strip().lower()
        normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
        normalized = re.sub(r"\s+", "-", normalized)
        phases.append(normalized)
    return phases


def _write_skill_todos_marker(cwd: str, skill: str, required_todos: list) -> None:
    """Write skill_todos.json marker for TodoWrite validation.

    This enables the PreToolUse hook (skill_todo_validator.py) to enforce
    that Claude creates the required todos at the START of the skill.
    """
    import json

    # Try cwd/.planning/ first, then ~/projects/{project}/.planning/
    cwd_path = Path(cwd)
    planning_dir = cwd_path / ".planning"

    if not planning_dir.exists():
        # Try to find project from cwd
        projects_dir = Path.home() / "projects"
        try:
            relative = cwd_path.relative_to(projects_dir)
            project = relative.parts[0] if relative.parts else None
            if project:
                planning_dir = projects_dir / project / ".planning"
        except ValueError:
            # cwd not under ~/projects/, try relative to home
            try:
                relative = cwd_path.relative_to(Path.home())
                # Use first directory component as project
                project = relative.parts[0] if relative.parts else cwd_path.name
                planning_dir = Path.home() / "projects" / project / ".planning"
            except ValueError:
                planning_dir = cwd_path / ".planning"

    planning_dir.mkdir(parents=True, exist_ok=True)

    # Write marker
    marker = planning_dir / "skill_todos.json"
    validated = planning_dir / "skill_validated"

    # Clear any previous validation marker
    if validated.exists():
        validated.unlink()

    marker.write_text(
        json.dumps(
            {
                "skill": skill,
                "required_todos": required_todos,
            }
        )
    )
    _log(f"  wrote skill_todos.json to {planning_dir}")


def _extract_skill_from_prompt(prompt: str) -> tuple[str | None, str]:
    """Extract skill name and mode from /skill-name or /skill-name - command.

    Handles:
    - /skill-name        → full mode (default)
    - /skill-name -      → quick mode
    - /skill-name args   → full mode
    - /skill-name - args → quick mode

    Returns:
        (skill_name, mode) where mode is "quick" or "full"
    """
    prompt = prompt.strip()
    if not prompt.startswith("/"):
        return None, "full"

    # Extract the command (first word after /) and check for - after space
    match = re.match(r"^/([a-zA-Z][-a-zA-Z0-9]*)(?:\s+(-))?", prompt)
    if not match:
        return None, "full"

    skill = match.group(1)
    mode = "quick" if match.group(2) else "full"
    return skill, mode


def check(ctx: dict) -> dict | None:
    """Create SkillRun for CLI skill invocations requiring structured output.

    Modes:
    - /skill   → full mode: follow **full:** instructions (default)
    - /skill - → quick mode: follow **quick:** instructions

    Both modes get TodoWrite enforcement and SkillRun if configured.
    Mode just tells Claude which conditional instructions to follow.

    Args:
        ctx: Context dict with prompt, cwd, session_id fields

    Returns:
        dict with "context" key for mode injection, None if not a skill
    """
    prompt = ctx.get("prompt", "")

    skill, mode = _extract_skill_from_prompt(prompt)
    if not skill:
        return None

    _log(f"CLI skill invoked: {skill} (mode={mode})")

    # Read skill file and extract phases from content (runtime extraction)
    frontmatter, content = _read_skill_file(skill)
    uses_skill_run = frontmatter.get("uses_skill_run")

    # Runtime phase extraction - no build step needed
    # Frontmatter required_todos takes precedence if explicitly set
    required_todos = frontmatter.get("required_todos") or _extract_phases_from_content(content)
    _log(f"  uses_skill_run: {uses_skill_run}, required_todos: {required_todos}")

    # Write skill_todos marker if skill has required_todos (for PreToolUse validation)
    cwd = ctx.get("cwd", "")
    if required_todos and cwd:
        _write_skill_todos_marker(cwd, skill, required_todos)

    # Build mode context
    mode_context = (
        f"## Mode: {mode}\n\n"
        f"Follow **{mode}:** instructions where specified.\n"
        f"{'Skip phases marked `(full only)`.' if mode == 'quick' else 'Execute all phases including those marked `(full only)`.'}"
    )

    if not uses_skill_run:
        _log("  skipping SkillRun creation (uses_skill_run not set)")
        return {"context": mode_context}

    # Create SkillRun
    try:
        from formaltask.utils.skill_output import SkillRun

        # Use skill name as title; pass session_id from hook context
        # to avoid cross-instance contamination via shared current-session.json
        run = SkillRun.create(skill, skill, session_id=ctx.get("session_id"))

        _log(f"  created SkillRun at {run.dir}")

        # Return paths via context
        return {
            "context": (
                f"{mode_context}\n\n"
                f"### SkillRun Initialized\n\n"
                f"Run directory created automatically. Use these paths:\n"
                f"- **Run dir**: `{run.dir}`\n"
                f"- **Synthesis**: `{run.synthesis}` (REQUIRED)\n"
                f"- **Context**: `{run.context}`\n"
                f"- **Handoffs**: `{run.handoffs}/`\n"
                f"- **Outputs**: `{run.outputs}/`\n"
                f"- **Log**: `{run.log}`\n\n"
                f"Write synthesis.md before completing the skill."
            )
        }
    except Exception as e:
        _log(f"  ERROR: {e}")
        return {"context": mode_context}
