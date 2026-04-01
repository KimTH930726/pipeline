from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AuditEntry:
    event_type: str
    branch: str
    commit_sha: str | None = None
    acted_by: str | None = None
    ai_report: dict | None = None
    metadata: dict | None = None
    prev_hash: str | None = None
    entry_hash: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None
