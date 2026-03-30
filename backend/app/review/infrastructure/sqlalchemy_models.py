from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime
from app.shared.infrastructure.database import Base


class ReviewModel(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="PENDING")
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
