from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.shared.infrastructure.database import Base


class SandboxORM(Base):
    __tablename__ = "sandboxes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, unique=True)
    pid = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="CREATING")
    created_at = Column(DateTime, default=datetime.utcnow)
