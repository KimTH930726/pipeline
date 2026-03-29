from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.shared.infrastructure.database import Base


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    branch = Column(String(255), nullable=False, index=True)
    commit_sha = Column(String(40))
    ai_report = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    prev_hash = Column(String(64))
    entry_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
