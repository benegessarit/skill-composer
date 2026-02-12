"""Track skill step reads delegated to subagents via Task tool.

Fires on PreToolUse for Task tool. Scans prompt for step file references
(/skills/<skill>/steps/<step>.md) and appends to the active skill_span.

Key safety: ONLY appends to existing active spans. Never creates, never
resumes. If no active span exists, this is a silent no-op.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from db.connection import open_db
from db.event import emit_event

STEP_PATTERN = re.compile(r"/skills/([^/]+)/steps/([^/]+)\.md")


def check(ctx: dict) -> dict | None:
    """Append step references from Task tool prompts to active skill_span."""
    if ctx.get("tool_name") != "Task":
        return None

    prompt = ctx.get("tool_input", {}).get("prompt", "")
    if not prompt:
        return None

    matches = STEP_PATTERN.findall(prompt)
    # Filter internal skills before touching DB
    matches = [(skill, step) for skill, step in matches if not skill.startswith("_")]
    if not matches:
        return None

    session_id = ctx.get("session_id")

    try:
        with open_db() as db:
            for skill, step in matches:
                db.execute("BEGIN EXCLUSIVE")
                if session_id:
                    row = db.execute(
                        "SELECT span_id, steps FROM skill_span "
                        "WHERE skill = ? AND status = 'active' AND session_id = ? "
                        "ORDER BY started_at DESC LIMIT 1",
                        (skill, session_id),
                    ).fetchone()
                else:
                    row = db.execute(
                        "SELECT span_id, steps FROM skill_span "
                        "WHERE skill = ? AND status = 'active' "
                        "ORDER BY started_at DESC LIMIT 1",
                        (skill,),
                    ).fetchone()

                wrote = False
                if row:
                    span_id = row["span_id"]
                    steps = json.loads(row["steps"])
                    if not (steps and steps[-1] == step):
                        steps.append(step)
                        db.execute(
                            "UPDATE skill_span SET last_step = ?, steps = ? WHERE span_id = ?",
                            (step, json.dumps(steps), span_id),
                        )
                        wrote = True
                db.commit()

                if wrote:
                    emit_event(skill, step, event_type="subagent_step_delegate")

    except Exception as e:
        logger.debug("subagent_step_tracker: failed (non-blocking): %s", e)

    return None
