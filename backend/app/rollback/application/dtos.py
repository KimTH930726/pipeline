from __future__ import annotations

from pydantic import BaseModel


class RollbackRequestDTO(BaseModel):
    branch: str
    target_sha: str | None = None


class RollbackResultDTO(BaseModel):
    status: str
    reverted_to: str
    new_commit: str
    deployment_id: int | None
