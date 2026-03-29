from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Branch:
    name: str
    is_active: bool = False
    last_commit_sha: str | None = None
    last_commit_message: str | None = None


@dataclass(frozen=True)
class FileChange:
    path: str
    status: str  # A, M, D, R


@dataclass(frozen=True)
class Diff:
    branch: str
    file_path: str
    diff_text: str
