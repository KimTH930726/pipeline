from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RollbackOperation:
    branch: str
    target_sha: str
    new_commit_sha: str | None = None
    deployment_id: int | None = None
