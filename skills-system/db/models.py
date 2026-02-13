"""Data models for life.db — skill tracking subset."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _gen_id() -> str:
    return str(uuid.uuid4())[:8]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class LifeEvent:
    """LifeEvent — phase-level breadcrumb tracking for skills."""

    skill: str
    phase: str = ""
    event_type: str = "phase_enter"
    session_id: str = ""
    payload: str = ""
    id: str = field(default_factory=_gen_id)
    timestamp: str = field(default_factory=_now_iso)
