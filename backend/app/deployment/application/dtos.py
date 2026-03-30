from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class DeployRequestDTO(BaseModel):
    branch: str


class DeployStatusDTO(BaseModel):
    id: int
    branch: str
    commit_sha: str | None
    status: str
    rolled_back: bool = False
    commit_messages: str | None = None
    started_at: datetime | None
    finished_at: datetime | None


class DeployDetailDTO(DeployStatusDTO):
    build_log: str | None = None
    error_log: str | None = None


class DeployPageDTO(BaseModel):
    items: list[DeployStatusDTO]
    total: int
    page: int
    size: int
