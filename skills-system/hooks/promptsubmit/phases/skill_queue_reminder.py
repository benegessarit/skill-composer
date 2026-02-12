"""Phase: Inject pending-queue reminder during skill sessions.

Queries ~/life/life.db for an active or suspended skill_span matching the
current session. Checks suspended too so the reminder survives skill nesting
(e.g., /mode-verify invoked during /learning-companion).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

QUEUE_SKILLS = {
    "learning-companion": {
        "path": "~/life/learning/pending-queue.md",
        "arrows": "Node/Edge/Evidence",
    },
    "therapy-journal": {
        "path": "~/life/therapy-journal/pending-queue.md",
        "arrows": "State/Bridge",
    },
    "goal-compass": {
        "path": "~/life/goals/pending-queue.md",
        "arrows": "Evidence/State/Sheet",
    },
}


def check(ctx: dict) -> dict | None:
    """Inject queue reminder if a skill session (active or suspended) has a pending-queue."""
    session_id = ctx.get("session_id")
    if not session_id:
        return None

    try:
        from db.connection import open_db

        with open_db() as db:
            row = db.execute(
                "SELECT skill FROM skill_span "
                "WHERE status IN ('active', 'suspended') AND session_id = ? "
                "ORDER BY started_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()

        if not row:
            return None

        skill = row["skill"]
        info = QUEUE_SKILLS.get(skill)
        if not info:
            return None

        reminder = (
            f"[Queue active: {info['path']}. "
            f"After confirmed moments, silently append: "
            f"timestamp + context + -> items ({info['arrows']}). Don't announce.]"
        )
        return {"context": reminder}

    except Exception as e:
        logger.debug("skill_queue_reminder: %s", e)
        return None
