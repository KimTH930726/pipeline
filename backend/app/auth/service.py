from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserModel
from app.shared.infrastructure.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    encrypt_api_key, decrypt_api_key,
)


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


async def update_api_key(db: AsyncSession, user_id: int, plain_key: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    user.encrypted_llm_api_key = encrypt_api_key(plain_key)
    await db.commit()
    return True


def get_user_api_key(user: UserModel) -> str | None:
    if not user.encrypted_llm_api_key:
        return None
    try:
        return decrypt_api_key(user.encrypted_llm_api_key)
    except Exception:
        return None


def make_tokens(user: UserModel) -> dict:
    payload = {"sub": str(user.id), "username": user.username, "role": user.role}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
    }
