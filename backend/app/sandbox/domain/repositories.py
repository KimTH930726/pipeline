from __future__ import annotations

from abc import ABC, abstractmethod
from app.sandbox.domain.entities import Sandbox


class SandboxRepositoryPort(ABC):
    @abstractmethod
    async def save(self, sandbox: Sandbox) -> Sandbox: ...

    @abstractmethod
    async def update(self, sandbox: Sandbox) -> None: ...

    @abstractmethod
    async def delete(self, sandbox_id: int) -> bool: ...

    @abstractmethod
    async def find_by_id(self, sandbox_id: int) -> Sandbox | None: ...

    @abstractmethod
    async def find_all(self) -> list[Sandbox]: ...

    @abstractmethod
    async def get_used_ports(self) -> set[int]: ...
