from __future__ import annotations

from datetime import datetime

from app.audit.domain.entities import AuditEntry
from app.audit.domain.repositories import AuditRepositoryPort
from app.audit.domain.services import AuditDomainService
from app.audit.application.dtos import AuditEntryDTO, AuditTimelineDTO


class AppendAuditEntry:
    def __init__(self, repo: AuditRepositoryPort) -> None:
        self._repo = repo

    async def execute(
        self,
        event_type: str,
        branch: str,
        commit_sha: str | None = None,
        ai_report: dict | None = None,
        metadata: dict | None = None,
    ) -> AuditEntryDTO:
        prev_hash = await self._repo.get_last_hash()
        now = datetime.utcnow()

        event_data = {
            "event_type": event_type,
            "branch": branch,
            "commit_sha": commit_sha,
            "ai_report": ai_report,
            "metadata": metadata,
        }
        entry_hash = AuditDomainService.compute_entry_hash(
            prev_hash, event_data, now.isoformat()
        )

        entry = AuditEntry(
            event_type=event_type,
            branch=branch,
            commit_sha=commit_sha,
            ai_report=ai_report,
            metadata=metadata,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            created_at=now,
        )
        saved = await self._repo.save(entry)
        return self._to_dto(saved)

    @staticmethod
    def _to_dto(e: AuditEntry) -> AuditEntryDTO:
        return AuditEntryDTO(
            id=e.id,
            event_type=e.event_type,
            branch=e.branch,
            commit_sha=e.commit_sha,
            ai_report=e.ai_report,
            metadata=e.metadata,
            created_at=e.created_at,
        )


class GetTimeline:
    def __init__(self, repo: AuditRepositoryPort) -> None:
        self._repo = repo

    async def execute(
        self,
        branch: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditTimelineDTO:
        entries, total = await self._repo.find_timeline(branch, event_type, limit, offset)
        return AuditTimelineDTO(
            entries=[
                AuditEntryDTO(
                    id=e.id,
                    event_type=e.event_type,
                    branch=e.branch,
                    commit_sha=e.commit_sha,
                    ai_report=e.ai_report,
                    metadata=e.metadata,
                    created_at=e.created_at,
                )
                for e in entries
            ],
            total=total,
        )


class GetAuditEntry:
    def __init__(self, repo: AuditRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, entry_id: int) -> AuditEntryDTO | None:
        entry = await self._repo.find_by_id(entry_id)
        if not entry:
            return None
        return AuditEntryDTO(
            id=entry.id,
            event_type=entry.event_type,
            branch=entry.branch,
            commit_sha=entry.commit_sha,
            ai_report=entry.ai_report,
            metadata=entry.metadata,
            created_at=entry.created_at,
        )
