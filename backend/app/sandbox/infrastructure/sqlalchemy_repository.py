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
            port=sandbox.port,
            pid=sandbox.pid,
            status=sandbox.status.value,
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
            orm.pid = sandbox.pid
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
        result = await self._db.execute(select(SandboxORM.port))
        return {row[0] for row in result.all()}

    @staticmethod
    def _to_entity(orm: SandboxORM) -> Sandbox:
        return Sandbox(
            id=orm.id,
            branch=orm.branch,
            port=orm.port,
            pid=orm.pid,
            status=SandboxStatus(orm.status),
            created_at=orm.created_at,
        )
