from __future__ import annotations

from abc import ABC, abstractmethod
from app.review.domain.entities import Review


class ReviewRepositoryPort(ABC):
    @abstractmethod
    async def save(self, review: Review) -> Review: ...

    @abstractmethod
    async def update(self, review: Review) -> None: ...

    @abstractmethod
    async def find_by_id(self, review_id: int) -> Review | None: ...

    @abstractmethod
    async def find_by_branch(self, branch: str) -> Review | None: ...

    @abstractmethod
    async def find_approved(self) -> list[Review]: ...

    @abstractmethod
    async def find_all(self) -> list[Review]: ...
