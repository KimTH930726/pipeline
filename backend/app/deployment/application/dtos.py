from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, field_serializer


class DeployRequestDTO(BaseModel):
    branch: str


class DeployStatusDTO(BaseModel):
    id: int
    branch: str
    commit_sha: str | None
    status: str
    rolled_back: bool = False
    acted_by: str | None = None
    commit_messages: str | None = None
    started_at: datetime | None
    finished_at: datetime | None

    @field_serializer('started_at', 'finished_at')
    def serialize_dt(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class DeployDetailDTO(DeployStatusDTO):
    build_log: str | None = None
    error_log: str | None = None
    changed_files: list[str] = []


class DeployPageDTO(BaseModel):
    items: list[DeployStatusDTO]
    total: int
    page: int
    size: int
