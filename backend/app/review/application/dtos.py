from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, field_validator


class ReviewRequestDTO(BaseModel):
    branch: str
    comment: str | None = None

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Branch name cannot be empty")
        if v == "main":
            raise ValueError("Cannot review main branch")
        return v


class ReviewResponseDTO(BaseModel):
    id: int
    branch: str
    status: str
    comment: str | None
    created_at: datetime
    reviewed_at: datetime | None
