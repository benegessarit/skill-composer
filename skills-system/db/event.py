"""Life event tracking — phase-level breadcrumbs for skills."""

import json
import logging

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
    data = event.to_dict()

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


def get_events_by_date(date_str: str, skill: str | None = None) -> list[dict]:
    """Get events for a date (YYYY-MM-DD). Optionally filter by skill."""
    with open_db() as db:
        if skill:
            rows = db.execute(
                "SELECT id, timestamp, skill, phase, event_type, session_id, payload "
                "FROM life_event WHERE timestamp LIKE ? AND skill = ? ORDER BY timestamp",
                (f"{date_str}%", skill),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, timestamp, skill, phase, event_type, session_id, payload "
                "FROM life_event WHERE timestamp LIKE ? ORDER BY timestamp",
                (f"{date_str}%",),
            ).fetchall()

    events = []
    for row in rows:
        e = dict(row)
        if e["payload"]:
            try:
                e["payload"] = json.loads(e["payload"])
            except json.JSONDecodeError:
                pass
        events.append(e)
    return events


def get_session_events(session_id: str) -> list[dict]:
    """Get all events for a specific Claude session."""
    with open_db() as db:
        rows = db.execute(
            "SELECT id, timestamp, skill, phase, event_type, session_id, payload "
            "FROM life_event WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()

    events = []
    for row in rows:
        e = dict(row)
        if e["payload"]:
            try:
                e["payload"] = json.loads(e["payload"])
            except json.JSONDecodeError:
                pass
        events.append(e)
    return events
