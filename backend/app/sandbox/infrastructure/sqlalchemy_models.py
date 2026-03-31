from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime
from app.shared.infrastructure.database import Base


class SandboxORM(Base):
    __tablename__ = "sandboxes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch = Column(String(255), nullable=False)
    backend_port = Column(Integer, nullable=False)
    frontend_port = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="CREATING")
    worktree_path = Column(String(500), nullable=True)
    project_name = Column(String(255), nullable=True)
    error_log = Column(String, nullable=True, default="")
    created_at = Column(DateTime, nullable=False)
