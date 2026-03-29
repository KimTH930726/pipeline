from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.shared.infrastructure.database import Base


class DeploymentORM(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch = Column(String(255), nullable=False, index=True)
    commit_sha = Column(String(40))
    status = Column(String(20), nullable=False, default="PENDING")
    build_log = Column(Text, nullable=True)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
