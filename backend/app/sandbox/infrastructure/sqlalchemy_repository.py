from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.sandbox.domain.entities import Sandbox, SandboxStatus
from app.sandbox.domain.repositories import SandboxRepositoryPort
from app.sandbox.infrastructure.sqlalchemy_models import SandboxORM


class SQLAlchemySandboxRepository(SandboxRepositoryPort):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, sandbox: Sandbox) -> Sandbox:
        orm = SandboxORM(
            branch=sandbox.branch,
            backend_port=sandbox.backend_port,
            frontend_port=sandbox.frontend_port,
            status=sandbox.status.value,
            worktree_path=sandbox.worktree_path,
            project_name=sandbox.project_name,
            created_at=sandbox.created_at,
        )
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        sandbox.id = orm.id
        return sandbox

    async def update(self, sandbox: Sandbox) -> None:
        result = await self._db.execute(
            select(SandboxORM).where(SandboxORM.id == sandbox.id)
        )
        orm = result.scalar_one_or_none()
        if orm:
            orm.status = sandbox.status.value
            orm.worktree_path = sandbox.worktree_path
            orm.project_name = sandbox.project_name
            await self._db.commit()

    async def delete(self, sandbox_id: int) -> bool:
        result = await self._db.execute(
            select(SandboxORM).where(SandboxORM.id == sandbox_id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return False
        await self._db.delete(orm)
        await self._db.commit()
        return True

    async def find_by_id(self, sandbox_id: int) -> Sandbox | None:
        result = await self._db.execute(
            select(SandboxORM).where(SandboxORM.id == sandbox_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def find_all(self) -> list[Sandbox]:
        result = await self._db.execute(
            select(SandboxORM).order_by(SandboxORM.created_at.desc())
        )
        return [self._to_entity(r) for r in result.scalars().all()]

    async def get_used_ports(self) -> set[int]:
        result = await self._db.execute(
            select(SandboxORM.backend_port, SandboxORM.frontend_port)
        )
        ports = set()
        for row in result.all():
            ports.add(row[0])
            ports.add(row[1])
        return ports

    @staticmethod
    def _to_entity(orm: SandboxORM) -> Sandbox:
        return Sandbox(
            id=orm.id,
            branch=orm.branch,
            backend_port=orm.backend_port,
            frontend_port=orm.frontend_port,
            status=SandboxStatus(orm.status),
            worktree_path=orm.worktree_path,
            project_name=orm.project_name,
            created_at=orm.created_at,
        )
