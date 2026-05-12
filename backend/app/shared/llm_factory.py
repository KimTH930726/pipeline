"""LLM 어댑터 생성 공통 헬퍼.

router마다 흩어진 자격증명 검증 + user_identifier 추출 + VPCLLMAdapter 생성을
한 곳으로 모은다. FastAPI Depends에 직접 꽂아 쓸 수 있는 의존성과,
background task용 system 호출 헬퍼 두 가지를 제공한다.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException

from app.analysis.domain.ports import LLMPort
from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter
from app.auth.dependencies import get_current_user
from app.config import settings


def _require_credentials() -> None:
    if not settings.LLM_CLIENT_ID or not settings.LLM_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="LLM_CLIENT_ID/LLM_CLIENT_SECRET가 설정되지 않았습니다. 운영자에게 문의하세요.",
        )


def _user_to_identifier(user: dict | None) -> str:
    if not user:
        return "system"
    return user.get("username") or str(user.get("id") or "system")


def get_llm_for_user(user: dict = Depends(get_current_user)) -> LLMPort:
    """FastAPI 의존성 — 인증된 사용자 컨텍스트로 LLM 어댑터 생성."""
    _require_credentials()
    return VPCLLMAdapter(user_identifier=_user_to_identifier(user))


def make_system_llm() -> LLMPort:
    """background task용 — system 식별자로 LLM 어댑터 생성."""
    _require_credentials()
    return VPCLLMAdapter(user_identifier="system")
