"""SessionEnd phase functions — skill-related subset.

Full version also includes run_doc_analyzer, index_conversation,
vault_capture, and run_skill_queue_flush which depend on FormalTask
infrastructure. This standalone version extracts close_active_skill_session.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def close_active_skill_session(ctx: dict) -> None:
    """Complete any open spans when conversation ends.

    Catches the case where no skill switch triggered step_logger's close logic.
    Scoped by session_id to avoid killing other sessions' spans.
    Completes both active AND suspended spans — suspended spans would otherwise
    be orphaned forever if the session ends while a different skill is active.
    Fails open — if DB is unavailable, does nothing.
    """
    session_id = ctx.get("session_id")
    if not session_id:
        return

    try:
        from db.connection import open_db
        from db.event import emit_event

        with open_db() as db:
            row = db.execute(
                "SELECT skill FROM skill_span "
                "WHERE status IN ('active', 'suspended') AND session_id = ? "
                "ORDER BY started_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()

            if row and row["skill"]:
                emit_event(row["skill"], "session_end", event_type="session_end")

            db.execute(
                "UPDATE skill_span SET status = 'completed', "
                "completed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
                "WHERE status IN ('active', 'suspended') AND session_id = ?",
                (session_id,),
            )
            db.commit()

    except Exception as e:
        logger.debug("skill_session_close: failed (non-blocking): %s", e)


PHASES = [
    close_active_skill_session,
]

__all__ = [
    "close_active_skill_session",
    "PHASES",
]
