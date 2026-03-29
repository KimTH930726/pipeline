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
    started_at: datetime | None
    finished_at: datetime | None
