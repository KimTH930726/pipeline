from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    has_llm_credentials: bool = False
    llm_user_id: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LLMCredentialsRequest(BaseModel):
    """사용자별 DevX Gateway 자격증명 등록.
    빈 문자열로 보내면 해당 필드 제거(.env 팀 fallback 사용)."""
    client_id: str = ""
    client_secret: str = ""
    llm_user_id: str = ""


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
