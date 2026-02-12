"""Auto-log LifeEvent when Claude reads a skill step or SKILL.md file.

Fires on PostToolUse for Read tool. Detects:
- */skills/*/steps/*.md  (step reads — existing)
- */skills/*/SKILL.md    (skill invocation — NEW)

Span-based tracking: monolithic skills = single-step span (transaction),
step-based skills = multi-step span (saga). Parent pointer = composition signal.

DB-only: no module-level state, no stack file. Each subprocess invocation
queries life.db directly for span state.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from db.connection import open_db
from db.event import emit_event

STEP_PATTERN = re.compile(r"/skills/([^/]+)/steps/([^/]+)\.md$")
SKILL_PATTERN = re.compile(r"/skills/([^/]+)/SKILL\.md$")


def _get_or_create_span(
    skill: str, step: str | None = None, session_id: str | None = None
) -> str | None:
    """DB-only span management. Returns span_id or None on error.

    3-branch algorithm: active -> append, suspended -> resume, else -> create.
    All queries scoped by session_id to prevent cross-session interference.
    """
    try:
        with open_db() as db:
            db.execute("BEGIN EXCLUSIVE")

            # Build session filter — nullable for backcompat with old spans
            if session_id:
                session_filter = " AND session_id = ?"
                session_params = (session_id,)
            else:
                session_filter = ""
                session_params = ()

            # Branch 1: Active span for this skill in this session — append step
            row = db.execute(
                "SELECT span_id, steps FROM skill_span "
                "WHERE skill = ? AND status = 'active'" + session_filter + " "
                "ORDER BY started_at DESC LIMIT 1",
                (skill,) + session_params,
            ).fetchone()
            if row:
                span_id = row["span_id"]
                if step:
                    steps = json.loads(row["steps"])
                    steps.append(step)
                    db.execute(
                        "UPDATE skill_span SET last_step = ?, steps = ? WHERE span_id = ?",
                        (step, json.dumps(steps), span_id),
                    )
                db.commit()
                return span_id

            # Branch 2: Suspended span for this skill in this session — resume
            row = db.execute(
                "SELECT span_id, steps FROM skill_span "
                "WHERE skill = ? AND status = 'suspended'"
                + session_filter + " "
                "ORDER BY started_at DESC LIMIT 1",
                (skill,) + session_params,
            ).fetchone()
            if row:
                span_id = row["span_id"]
                steps = json.loads(row["steps"])
                if step:
                    steps.append(step)
                db.execute(
                    "UPDATE skill_span SET status = 'active', suspended_at = NULL, "
                    "last_step = ?, steps = ? WHERE span_id = ?",
                    (step or steps[-1], json.dumps(steps), span_id),
                )
                db.commit()
                return span_id

            # Branch 3: Create new span
            span_id = str(uuid.uuid4())[:12]
            # Parent = most recent non-completed span for a different skill in this session
            parent_row = db.execute(
                "SELECT span_id FROM skill_span "
                "WHERE skill != ? AND status IN ('active', 'suspended')"
                + session_filter + " "
                "ORDER BY started_at DESC LIMIT 1",
                (skill,) + session_params,
            ).fetchone()
            parent_span_id = parent_row["span_id"] if parent_row else None
            first_step = step or "SKILL"
            db.execute(
                "INSERT INTO skill_span (span_id, skill, parent_span_id, status, "
                "first_step, last_step, steps, session_id) "
                "VALUES (?, ?, ?, 'active', ?, ?, ?, ?)",
                (span_id, skill, parent_span_id, first_step, first_step,
                 json.dumps([first_step]), session_id),
            )
            db.commit()
            return span_id

    except Exception as e:
        logger.debug("step_logger: span failed: %s", e)
        return None  # NOT "unknown" — fail-open


def _suspend_current_span(skill: str, session_id: str | None = None) -> None:
    """Suspend all active spans for a skill in this session."""
    try:
        with open_db() as db:
            if session_id:
                db.execute(
                    "UPDATE skill_span SET status = 'suspended', "
                    "suspended_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
                    "WHERE skill = ? AND status = 'active' AND session_id = ?",
                    (skill, session_id),
                )
            else:
                db.execute(
                    "UPDATE skill_span SET status = 'suspended', "
                    "suspended_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
                    "WHERE skill = ? AND status = 'active'",
                    (skill,),
                )
            db.commit()
    except Exception as e:
        logger.debug("step_logger: suspend failed: %s", e)


def log_step_enter(ctx: dict) -> dict | None:
    """Log step_enter event when a step or SKILL.md file is read.

    Returns dict with additionalContext for Claude if warranted.
    """
    if ctx.get("tool_name") != "Read":
        return None

    file_path = ctx.get("tool_input", {}).get("file_path", "")

    # Try step pattern first, then skill pattern
    step_match = STEP_PATTERN.search(file_path)
    skill_match = SKILL_PATTERN.search(file_path) if not step_match else None

    if not step_match and not skill_match:
        return None

    if step_match:
        skill, step = step_match.group(1), step_match.group(2)
    else:
        skill, step = skill_match.group(1), None

    # Skip internal directories
    if skill.startswith("_"):
        return None

    session_id = ctx.get("session_id")

    try:
        # Detect skill switch — find active span for a different skill in THIS session
        with open_db() as db:
            if session_id:
                prev_row = db.execute(
                    "SELECT skill, span_id FROM skill_span "
                    "WHERE status = 'active' AND skill != ? AND session_id = ? "
                    "ORDER BY started_at DESC LIMIT 1",
                    (skill, session_id),
                ).fetchone()
            else:
                prev_row = db.execute(
                    "SELECT skill, span_id FROM skill_span "
                    "WHERE status = 'active' AND skill != ? "
                    "ORDER BY started_at DESC LIMIT 1",
                    (skill,),
                ).fetchone()
            # Materialize before closing — Row objects survive fetchone()
            prev_skill = prev_row["skill"] if prev_row else None

        if prev_skill:
            emit_event(prev_skill, "session_end", event_type="session_end")
            _suspend_current_span(prev_skill, session_id=session_id)

        # Get or create span (handles resume, append, create)
        span_id = _get_or_create_span(skill, step, session_id=session_id)

        # Emit session_start if switching skills
        if prev_skill:
            emit_event(skill, "session_start", event_type="session_start")

        # Log the event
        phase = step or "SKILL"
        emit_event(skill, phase, event_type="step_enter")

        # Context injection
        parts = []

        with open_db() as db:
            row = db.execute(
                "SELECT COUNT(*) as cnt FROM life_event "
                "WHERE skill = ? AND phase = ? AND event_type = 'step_enter'",
                (skill, phase),
            ).fetchone()
            count = row["cnt"] if row else 0

            if count > 10:
                parts.append(f"[{skill}:{phase} — visit #{count}. Adapt pacing.]")

            # Ancestry context from span parent
            if span_id:
                parent_row = db.execute(
                    "SELECT s2.skill FROM skill_span s1 "
                    "JOIN skill_span s2 ON s1.parent_span_id = s2.span_id "
                    "WHERE s1.span_id = ?",
                    (span_id,),
                ).fetchone()
                if parent_row:
                    parts.append(
                        f"[Entered from {parent_row['skill']} — be brief, context already loaded.]"
                    )

        if parts:
            return {"additionalContext": " ".join(parts)}

    except Exception as e:
        logger.debug("step_logger: failed (non-blocking): %s", e)

    return None
