from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.shared.infrastructure.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    # 옛 단일 API Key (호환 보존, 새 코드는 안 씀)
    encrypted_llm_api_key = Column(String, nullable=True)
    # DevX Gateway 개별 자격증명 (Fernet 암호화). 없으면 .env의 팀 자격증명으로 fallback.
    encrypted_llm_client_id = Column(String, nullable=True)
    encrypted_llm_client_secret = Column(String, nullable=True)
    # dify에 등록된 user ID (시크릿 아님, 평문 저장)
    llm_user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
