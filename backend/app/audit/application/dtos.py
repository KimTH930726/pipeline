from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class AuditEntryDTO(BaseModel):
    id: int
    event_type: str
    branch: str
    commit_sha: str | None
    acted_by: str | None = None
    ai_report: dict | None
    metadata: dict | None
    created_at: datetime


class AuditTimelineDTO(BaseModel):
    entries: list[AuditEntryDTO]
    total: int
