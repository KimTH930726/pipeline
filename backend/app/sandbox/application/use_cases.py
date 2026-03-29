from __future__ import annotations

import asyncio

from app.sandbox.domain.entities import Sandbox
from app.sandbox.domain.repositories import SandboxRepositoryPort
from app.sandbox.domain.exceptions import SandboxNotFound
from app.sandbox.infrastructure.port_allocator import allocate_port
from app.sandbox.infrastructure.process_manager import SandboxProcessManager
from app.sandbox.application.dtos import SandboxResponseDTO


class CreateSandbox:
    def __init__(self, repo: SandboxRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str) -> SandboxResponseDTO:
        used = await self._repo.get_used_ports()
        port = allocate_port(used)

        sandbox = Sandbox(branch=branch, port=port)
        sandbox = await self._repo.save(sandbox)

        asyncio.create_task(self._start(sandbox))
        return self._to_dto(sandbox)

    async def _start(self, sandbox: Sandbox) -> None:
        pid = await SandboxProcessManager.start(sandbox.port)
        if pid:
            sandbox.mark_running(pid)
        else:
            sandbox.mark_error()
        await self._repo.update(sandbox)

    @staticmethod
    def _to_dto(s: Sandbox) -> SandboxResponseDTO:
        return SandboxResponseDTO(id=s.id, branch=s.branch, port=s.port, status=s.status.value)


class DestroySandbox:
    def __init__(self, repo: SandboxRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, sandbox_id: int) -> None:
        sandbox = await self._repo.find_by_id(sandbox_id)
        if not sandbox:
            raise SandboxNotFound(sandbox_id)
        if sandbox.pid:
            SandboxProcessManager.stop(sandbox.pid)
        await self._repo.delete(sandbox_id)


class ListSandboxes:
    def __init__(self, repo: SandboxRepositoryPort) -> None:
        self._repo = repo

    async def execute(self) -> list[SandboxResponseDTO]:
        sandboxes = await self._repo.find_all()
        return [
            SandboxResponseDTO(id=s.id, branch=s.branch, port=s.port, status=s.status.value)
            for s in sandboxes
        ]
