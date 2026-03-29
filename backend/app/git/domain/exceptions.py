from __future__ import annotations

from app.shared.domain.exceptions import DomainException, EntityNotFound


class RepositoryNotFound(DomainException):
    def __init__(self, path: str) -> None:
        super().__init__(f"Git repository not found at: {path}", "NOT_FOUND")


class BranchNotFound(EntityNotFound):
    def __init__(self, branch: str) -> None:
        super().__init__("Branch", branch)
