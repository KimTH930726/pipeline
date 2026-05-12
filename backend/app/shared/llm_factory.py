"""LLM 어댑터 생성 공통 헬퍼.

사용자 DB에 개별 자격증명이 등록되어 있으면 그것을 사용하고,
없으면 .env의 팀 자격증명으로 fallback (하이브리드 패턴).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.domain.ports import LLMPort
from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter
from app.auth.dependencies import get_current_user
from app.auth.service import get_user_by_id, get_user_llm_credentials
from app.config import settings
from app.shared.infrastructure.database import get_db


def _ensure_team_credentials_configured() -> None:
    """팀 자격증명(.env)이 설정되어 있는지 확인. 사용자별 등록 없을 때만 호출."""
    if not settings.LLM_CLIENT_ID or not settings.LLM_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail=(
                "LLM 자격증명이 없습니다. "
                "설정 페이지에서 본인의 client_id/secret을 등록하거나, "
                "운영자에게 팀 자격증명(.env) 설정을 요청하세요."
            ),
        )


async def get_llm_for_user(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LLMPort:
    """FastAPI 의존성 — 사용자별 자격증명 우선, 없으면 팀 자격증명 fallback."""
    user_model = await get_user_by_id(db, user["id"])
    creds = get_user_llm_credentials(user_model) if user_model else None
    if creds:
        client_id, client_secret, llm_user_id = creds
        return VPCLLMAdapter(
            client_id=client_id,
            client_secret=client_secret,
            user_id=llm_user_id,
        )
    _ensure_team_credentials_configured()
    return VPCLLMAdapter(user_id=user_model.llm_user_id if user_model else None)


def make_system_llm() -> LLMPort:
    """background task용 — 항상 .env의 팀 자격증명 사용."""
    _ensure_team_credentials_configured()
    return VPCLLMAdapter()
