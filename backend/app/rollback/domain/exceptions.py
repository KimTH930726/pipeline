from __future__ import annotations

from app.shared.domain.exceptions import DomainException


class NoStableCommitFound(DomainException):
    def __init__(self, branch: str) -> None:
        super().__init__(f"No stable commit found for branch '{branch}'", "NO_STABLE_COMMIT")
