from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.database import get_db
from app.shared.infrastructure.security import decode_token
from app.auth.schemas import (
    LoginRequest, SignupRequest, RegisterRequest, TokenResponse, RefreshRequest,
    AccessTokenResponse, UserOut, LLMCredentialsRequest, PasswordChangeRequest,
)
from app.auth.service import (
    authenticate, signup_user, create_user, activate_user, get_user_by_id,
    list_users, update_llm_credentials, change_password, make_tokens,
)
from app.auth.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_out(user) -> UserOut:
    return UserOut(
        id=user.id, username=user.username, role=user.role,
        is_active=user.is_active,
        has_llm_credentials=bool(user.encrypted_llm_client_id and user.encrypted_llm_client_secret),
        llm_user_id=user.llm_user_id,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    tokens = make_tokens(user)
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user=_to_user_out(user),
    )


@router.post("/signup", response_model=UserOut)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """셀프 회원가입 (관리자 승인 전까지 비활성)"""
    try:
        user = await signup_user(db, body.username, body.password)
        return _to_user_out(user)
    except Exception:
        raise HTTPException(status_code=409, detail="이미 존재하는 사용자입니다.")


@router.post("/register", response_model=UserOut)
async def register(body: RegisterRequest, admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """관리자가 직접 사용자 등록"""
    try:
        user = await create_user(db, body.username, body.password, body.role)
        return _to_user_out(user)
    except Exception:
        raise HTTPException(status_code=409, detail="이미 존재하는 사용자입니다.")


@router.put("/users/{user_id}/activate")
async def activate(user_id: int, admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    user = await activate_user(db, user_id, True)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return _to_user_out(user)


@router.put("/users/{user_id}/deactivate")
async def deactivate(user_id: int, admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    user = await activate_user(db, user_id, False)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return _to_user_out(user)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")
    user = await get_user_by_id(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    tokens = make_tokens(user)
    return AccessTokenResponse(access_token=tokens["access_token"])


@router.get("/me", response_model=UserOut)
async def get_me(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    u = await get_user_by_id(db, user["id"])
    return _to_user_out(u)


@router.put("/me/password")
async def change_my_password(body: PasswordChangeRequest, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ok = await change_password(db, user["id"], body.current_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")
    return {"status": "ok"}


@router.put("/me/llm-credentials")
async def update_my_llm_credentials(
    body: LLMCredentialsRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """개별 DevX Gateway 자격증명 등록/갱신. 빈 값은 .env의 팀 자격증명으로 fallback."""
    await update_llm_credentials(
        db, user["id"],
        client_id=body.client_id,
        client_secret=body.client_secret,
        llm_user_id=body.llm_user_id,
    )
    return {"status": "ok"}


@router.get("/users", response_model=list[UserOut])
async def get_users(admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    users = await list_users(db)
    return [_to_user_out(u) for u in users]
