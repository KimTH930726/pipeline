from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.database import get_db
from app.sandbox.application.dtos import SandboxCreateDTO, SandboxResponseDTO
from app.sandbox.application.use_cases import CreateSandbox, DestroySandbox, ListSandboxes
from app.sandbox.infrastructure.sqlalchemy_repository import SQLAlchemySandboxRepository

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


def _repo(db: AsyncSession = Depends(get_db)) -> SQLAlchemySandboxRepository:
    return SQLAlchemySandboxRepository(db)


@router.post("/", response_model=SandboxResponseDTO)
async def create_sandbox(req: SandboxCreateDTO, repo=Depends(_repo)):
    return await CreateSandbox(repo).execute(req.branch)


@router.get("/", response_model=list[SandboxResponseDTO])
async def list_sandboxes(repo=Depends(_repo)):
    return await ListSandboxes(repo).execute()


@router.delete("/{sandbox_id}")
async def destroy_sandbox(sandbox_id: int, repo=Depends(_repo)):
    await DestroySandbox(repo).execute(sandbox_id)
    return {"status": "destroyed"}
