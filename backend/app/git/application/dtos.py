from __future__ import annotations

from pydantic import BaseModel


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
