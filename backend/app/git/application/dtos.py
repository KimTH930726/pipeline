from __future__ import annotations

from pydantic import BaseModel, field_validator


class BranchInfoDTO(BaseModel):
    name: str
    is_active: bool = False
    last_commit_sha: str | None = None
    last_commit_message: str | None = None


class FileChangeDTO(BaseModel):
    path: str
    status: str


class DiffResponseDTO(BaseModel):
    branch: str
    file_path: str
    diff_text: str


class CreateBranchRequestDTO(BaseModel):
    new_branch: str
    base_branch: str

    @field_validator("new_branch")
    @classmethod
    def validate_branch_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Branch name cannot be empty")
        if ".." in v or v.startswith("/") or v.endswith("/") or v.endswith(".lock"):
            raise ValueError(f"Invalid branch name: {v}")
        return v
