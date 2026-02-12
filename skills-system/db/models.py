"""Pydantic models for life.db — skill tracking subset."""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _gen_id() -> str:
    return str(uuid.uuid4())[:8]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LifeEvent(BaseModel):
    """LifeEvent — phase-level breadcrumb tracking for skills."""

    id: str = Field(default_factory=_gen_id)
    timestamp: str = Field(default_factory=_now_iso)
    skill: str = Field(min_length=1)
    phase: str = ""
    event_type: str = "phase_enter"
    session_id: str = ""
    payload: str = ""

    def to_dict(self) -> dict:
        return self.model_dump()
