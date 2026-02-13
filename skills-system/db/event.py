"""Life event tracking — phase-level breadcrumbs for skills."""

import json
import logging
from dataclasses import asdict

from .connection import open_db
from .models import LifeEvent

logger = logging.getLogger(__name__)


def emit_event(
    skill: str,
    phase: str,
    event_type: str = "phase_enter",
    session_id: str = "",
    payload: dict | None = None,
) -> str | None:
    """Emit a life event. Returns event ID. Fails open on DB errors."""
    event = LifeEvent(
        skill=skill,
        phase=phase,
        event_type=event_type,
        session_id=session_id,
        payload=json.dumps(payload) if payload else "",
    )
    data = asdict(event)

    try:
        with open_db() as db:
            db.execute(
                "INSERT INTO life_event (id, timestamp, skill, phase, event_type, session_id, payload) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (data["id"], data["timestamp"], data["skill"], data["phase"],
                 data["event_type"], data["session_id"], data["payload"]),
            )
            db.commit()
        return data["id"]
    except Exception as e:
        logger.warning("Failed to emit life event: %s", e)
        return None
