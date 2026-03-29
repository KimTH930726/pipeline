from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.audit.application.use_cases import AppendAuditEntry
from app.audit.infrastructure.sqlalchemy_repository import SQLAlchemyAuditRepository
from app.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class AuditEventHandler:
    """Subscribes to domain events from all bounded contexts and records them."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def handle_deployment_succeeded(self, event: DomainEvent) -> None:
        await self._record(
            event_type="DEPLOY",
            branch=event.branch,
            commit_sha=getattr(event, "commit_sha", None),
            metadata={"deployment_id": event.deployment_id, "result": "SUCCESS"},
        )

    async def handle_deployment_failed(self, event: DomainEvent) -> None:
        await self._record(
            event_type="FAILURE",
            branch=event.branch,
            commit_sha=getattr(event, "commit_sha", None),
            ai_report=getattr(event, "rca_report", None),
            metadata={
                "deployment_id": event.deployment_id,
                "exit_code": getattr(event, "exit_code", None),
            },
        )

    async def handle_rollback_executed(self, event: DomainEvent) -> None:
        await self._record(
            event_type="ROLLBACK",
            branch=event.branch,
            commit_sha=getattr(event, "new_commit_sha", None),
            metadata={
                "reverted_to": getattr(event, "target_sha", None),
                "new_commit": getattr(event, "new_commit_sha", None),
            },
        )

    async def _record(
        self,
        event_type: str,
        branch: str,
        commit_sha: str | None = None,
        ai_report: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        async with self._session_factory() as db:
            repo = SQLAlchemyAuditRepository(db)
            use_case = AppendAuditEntry(repo)
            await use_case.execute(
                event_type=event_type,
                branch=branch,
                commit_sha=commit_sha,
                ai_report=ai_report,
                metadata=metadata,
            )
