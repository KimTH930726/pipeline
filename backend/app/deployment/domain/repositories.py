from __future__ import annotations

from abc import ABC, abstractmethod
from app.deployment.domain.entities import Deployment


class DeploymentRepositoryPort(ABC):
    @abstractmethod
    async def save(self, deployment: Deployment) -> Deployment: ...

    @abstractmethod
    async def update(self, deployment: Deployment) -> None: ...

    @abstractmethod
    async def find_by_id(self, deployment_id: int) -> Deployment | None: ...

    @abstractmethod
    async def find_recent(self, branch: str | None = None, limit: int = 20) -> list[Deployment]: ...

    @abstractmethod
    async def find_last_successful(self, branch: str) -> Deployment | None: ...
