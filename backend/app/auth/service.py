from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserModel
from app.shared.infrastructure.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    encrypt_api_key, decrypt_api_key,
)


async def signup_user(db: AsyncSession, username: str, password: str) -> UserModel:
    """셀프 회원가입 — is_active=False (관리자 승인 필요)"""
    user = UserModel(
        username=username,
        hashed_password=hash_password(password),
        role="user",
        is_active=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def activate_user(db: AsyncSession, user_id: int, active: bool = True) -> UserModel | None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    user.is_active = active
    await db.commit()
    await db.refresh(user)
    return user


async def create_user(db: AsyncSession, username: str, password: str, role: str = "user") -> UserModel:
    user = UserModel(
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, username: str, password: str) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession) -> list[UserModel]:
    result = await db.execute(select(UserModel).order_by(UserModel.created_at.desc()))
    return list(result.scalars().all())


async def update_llm_credentials(
    db: AsyncSession,
    user_id: int,
    client_id: str,
    client_secret: str,
    llm_user_id: str,
) -> bool:
    """사용자별 DevX Gateway 자격증명 등록/갱신."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    user.encrypted_llm_client_id = encrypt_api_key(client_id) if client_id else None
    user.encrypted_llm_client_secret = encrypt_api_key(client_secret) if client_secret else None
    user.llm_user_id = llm_user_id or None
    await db.commit()
    return True


def get_user_llm_credentials(user: UserModel) -> tuple[str, str, str] | None:
    """사용자의 (client_id, client_secret, llm_user_id) 복호화 반환. 미등록 시 None."""
    if not user.encrypted_llm_client_id or not user.encrypted_llm_client_secret:
        return None
    try:
        return (
            decrypt_api_key(user.encrypted_llm_client_id),
            decrypt_api_key(user.encrypted_llm_client_secret),
            user.llm_user_id or "",
        )
    except Exception:
        return None


async def change_password(db: AsyncSession, user_id: int, current_pw: str, new_pw: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user or not verify_password(current_pw, user.hashed_password):
        return False
    user.hashed_password = hash_password(new_pw)
    await db.commit()
    return True


def make_tokens(user: UserModel) -> dict:
    payload = {"sub": str(user.id), "username": user.username, "role": user.role}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
    }
