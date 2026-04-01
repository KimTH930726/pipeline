from __future__ import annotations

from dataclasses import dataclass
from app.shared.domain.events import DomainEvent


@dataclass
class RollbackExecuted(DomainEvent):
    branch: str = ""
    target_sha: str = ""
    new_commit_sha: str | None = None
    deployment_id: int | None = None
    acted_by: str | None = None
