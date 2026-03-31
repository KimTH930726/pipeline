from __future__ import annotations

import asyncio

import logging

from app.sandbox.domain.entities import Sandbox
from app.sandbox.domain.repositories import SandboxRepositoryPort
from app.sandbox.domain.exceptions import SandboxNotFound
from app.sandbox.infrastructure.port_allocator import allocate_port_pair
from app.sandbox.infrastructure.process_manager import SandboxProcessManager
from app.sandbox.infrastructure.sqlalchemy_repository import SQLAlchemySandboxRepository
from app.sandbox.application.dtos import SandboxResponseDTO
from app.shared.infrastructure.database import SessionFactory

logger = logging.getLogger(__name__)


class CreateSandbox:
    def __init__(self, repo: SandboxRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str) -> SandboxResponseDTO:
        used = await self._repo.get_used_ports()
        backend_port, frontend_port = allocate_port_pair(used)

        sandbox = Sandbox(
            branch=branch,
            backend_port=backend_port,
            frontend_port=frontend_port,
        )
        sandbox = await self._repo.save(sandbox)
        asyncio.create_task(self._start(sandbox))
        return self._to_dto(sandbox)

    async def _start(self, sandbox: Sandbox) -> None:
        try:
            sandbox.project_name = f"sandbox-{sandbox.id}"
            ok, error_log = await SandboxProcessManager.start(
                project_name=sandbox.project_name,
                branch=sandbox.branch,
                backend_port=sandbox.backend_port,
                frontend_port=sandbox.frontend_port,
            )
            sandbox.error_log = error_log
            if ok:
                sandbox.mark_running()
            else:
                sandbox.mark_error()
        except Exception as e:
            logger.exception("Sandbox start error for %s", sandbox.id)
            sandbox.error_log = str(e)
            sandbox.mark_error()

        # 비동기 태스크에서 세션이 닫혀있을 수 있으므로 새 세션 사용
        async with SessionFactory() as db:
            repo = SQLAlchemySandboxRepository(db)
            await repo.update(sandbox)

    @staticmethod
    def _to_dto(s: Sandbox) -> SandboxResponseDTO:
        return SandboxResponseDTO(
            id=s.id, branch=s.branch,
            backend_port=s.backend_port, frontend_port=s.frontend_port,
            status=s.status.value, error_log=s.error_log,
        )


class StopSandbox:
    def __init__(self, repo: SandboxRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, sandbox_id: int) -> SandboxResponseDTO:
        sandbox = await self._repo.find_by_id(sandbox_id)
        if not sandbox:
            raise SandboxNotFound(sandbox_id)
        if sandbox.project_name:
            await SandboxProcessManager.stop(sandbox.project_name)
        sandbox.mark_stopped()
        await self._repo.update(sandbox)
        return SandboxResponseDTO(
            id=sandbox.id, branch=sandbox.branch,
            backend_port=sandbox.backend_port, frontend_port=sandbox.frontend_port,
            status=sandbox.status.value,
        )


class DestroySandbox:
    def __init__(self, repo: SandboxRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, sandbox_id: int) -> None:
        sandbox = await self._repo.find_by_id(sandbox_id)
        if not sandbox:
            raise SandboxNotFound(sandbox_id)
        if sandbox.project_name:
            await SandboxProcessManager.destroy(sandbox.project_name)
        await self._repo.delete(sandbox_id)


class ListSandboxes:
    def __init__(self, repo: SandboxRepositoryPort) -> None:
        self._repo = repo

    async def execute(self) -> list[SandboxResponseDTO]:
        sandboxes = await self._repo.find_all()
        return [
            SandboxResponseDTO(
                id=s.id, branch=s.branch,
                backend_port=s.backend_port, frontend_port=s.frontend_port,
                status=s.status.value,
            )
            for s in sandboxes
        ]
