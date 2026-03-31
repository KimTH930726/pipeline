from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deployment.domain.entities import Deployment, DeploymentStatus
from app.deployment.domain.repositories import DeploymentRepositoryPort
from app.deployment.infrastructure.sqlalchemy_models import DeploymentORM


class SQLAlchemyDeploymentRepository(DeploymentRepositoryPort):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, deployment: Deployment) -> Deployment:
        orm = DeploymentORM(
            branch=deployment.branch,
            commit_sha=deployment.commit_sha,
            status=deployment.status.value,
            build_log=deployment.build_log,
            error_log=deployment.error_log,
            commit_messages=deployment.commit_messages,
            acted_by=deployment.acted_by,
            started_at=deployment.started_at,
            finished_at=deployment.finished_at,
        )
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        deployment.id = orm.id
        return deployment

    async def update(self, deployment: Deployment) -> None:
        result = await self._db.execute(
            select(DeploymentORM).where(DeploymentORM.id == deployment.id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return
        orm.status = deployment.status.value
        orm.build_log = deployment.build_log
        orm.error_log = deployment.error_log
        orm.commit_messages = deployment.commit_messages
        orm.rolled_back = 1 if deployment.rolled_back else 0
        orm.finished_at = deployment.finished_at
        await self._db.commit()

    async def find_by_id(self, deployment_id: int) -> Deployment | None:
        result = await self._db.execute(
            select(DeploymentORM).where(DeploymentORM.id == deployment_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def count(self, branch: str | None = None) -> int:
        from sqlalchemy import func
        query = select(func.count(DeploymentORM.id))
        if branch:
            query = query.where(DeploymentORM.branch == branch)
        result = await self._db.execute(query)
        return result.scalar() or 0

    async def find_recent(self, branch: str | None = None, limit: int = 10, offset: int = 0) -> list[Deployment]:
        query = select(DeploymentORM).order_by(DeploymentORM.started_at.desc()).limit(limit).offset(offset)
        if branch:
            query = query.where(DeploymentORM.branch == branch)
        result = await self._db.execute(query)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def find_last_successful(self, branch: str) -> Deployment | None:
        result = await self._db.execute(
            select(DeploymentORM)
            .where(DeploymentORM.branch == branch, DeploymentORM.status == "SUCCESS")
            .order_by(DeploymentORM.finished_at.desc())
            .limit(1)
        )
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    @staticmethod
    def _to_entity(orm: DeploymentORM) -> Deployment:
        return Deployment(
            id=orm.id,
            branch=orm.branch,
            commit_sha=orm.commit_sha,
            status=DeploymentStatus(orm.status),
            build_log=orm.build_log,
            error_log=orm.error_log,
            commit_messages=orm.commit_messages,
            acted_by=orm.acted_by,
            rolled_back=bool(orm.rolled_back),
            started_at=orm.started_at,
            finished_at=orm.finished_at,
        )
