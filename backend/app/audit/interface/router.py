from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.database import get_db
from app.audit.application.dtos import AuditEntryDTO, AuditTimelineDTO
from app.audit.application.use_cases import GetTimeline, GetAuditEntry
from app.audit.infrastructure.sqlalchemy_repository import SQLAlchemyAuditRepository

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _get_timeline_uc(db: AsyncSession = Depends(get_db)) -> GetTimeline:
    return GetTimeline(SQLAlchemyAuditRepository(db))


def _get_entry_uc(db: AsyncSession = Depends(get_db)) -> GetAuditEntry:
    return GetAuditEntry(SQLAlchemyAuditRepository(db))


@router.get("/timeline", response_model=AuditTimelineDTO)
async def get_timeline(
    branch: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    uc: GetTimeline = Depends(_get_timeline_uc),
):
    return await uc.execute(branch, event_type, limit, offset)


@router.get("/{log_id}", response_model=AuditEntryDTO)
async def get_audit_entry(
    log_id: int,
    uc: GetAuditEntry = Depends(_get_entry_uc),
):
    entry = await uc.execute(log_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry
