from __future__ import annotations

from abc import ABC, abstractmethod
from app.audit.domain.entities import AuditEntry


class AuditRepositoryPort(ABC):
    @abstractmethod
    async def get_last_hash(self) -> str | None: ...

    @abstractmethod
    async def save(self, entry: AuditEntry) -> AuditEntry: ...

    @abstractmethod
    async def find_by_id(self, entry_id: int) -> AuditEntry | None: ...

    @abstractmethod
    async def find_timeline(
        self,
        branch: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditEntry], int]: ...
