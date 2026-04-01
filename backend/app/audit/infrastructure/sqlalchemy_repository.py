from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.domain.entities import AuditEntry
from app.audit.domain.repositories import AuditRepositoryPort
from app.audit.infrastructure.sqlalchemy_models import AuditLogORM


class SQLAlchemyAuditRepository(AuditRepositoryPort):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_last_hash(self) -> str | None:
        result = await self._db.execute(
            select(AuditLogORM.entry_hash).order_by(AuditLogORM.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, entry: AuditEntry) -> AuditEntry:
        orm = AuditLogORM(
            event_type=entry.event_type,
            branch=entry.branch,
            commit_sha=entry.commit_sha,
            acted_by=entry.acted_by,
            ai_report=entry.ai_report,
            metadata_=entry.metadata,
            prev_hash=entry.prev_hash,
            entry_hash=entry.entry_hash,
            created_at=entry.created_at,
        )
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        entry.id = orm.id
        return entry

    async def find_by_id(self, entry_id: int) -> AuditEntry | None:
        result = await self._db.execute(
            select(AuditLogORM).where(AuditLogORM.id == entry_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def find_timeline(
        self,
        branch: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditEntry], int]:
        query = select(AuditLogORM).order_by(AuditLogORM.created_at.desc())
        count_q = select(func.count(AuditLogORM.id))

        if branch:
            query = query.where(AuditLogORM.branch == branch)
            count_q = count_q.where(AuditLogORM.branch == branch)
        if event_type:
            query = query.where(AuditLogORM.event_type == event_type)
            count_q = count_q.where(AuditLogORM.event_type == event_type)

        total = (await self._db.execute(count_q)).scalar_one()
        result = await self._db.execute(query.offset(offset).limit(limit))
        return [self._to_entity(r) for r in result.scalars().all()], total

    @staticmethod
    def _to_entity(orm: AuditLogORM) -> AuditEntry:
        return AuditEntry(
            id=orm.id,
            event_type=orm.event_type,
            branch=orm.branch,
            commit_sha=orm.commit_sha,
            acted_by=orm.acted_by,
            ai_report=orm.ai_report,
            metadata=orm.metadata_,
            prev_hash=orm.prev_hash,
            entry_hash=orm.entry_hash,
            created_at=orm.created_at,
        )
