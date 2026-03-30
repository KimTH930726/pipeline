from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.infrastructure.database import get_db, SessionFactory
from app.shared.infrastructure.event_bus import InMemoryEventBus
from app.rollback.application.dtos import RollbackRequestDTO, RollbackResultDTO
from app.rollback.application.use_cases import ExecuteRollback
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository
from app.deployment.infrastructure.build_runner import BuildProcessRunner
from app.git.infrastructure.git_python_adapter import get_git_repo
from app.analysis.infrastructure.mock_llm_adapter import MockLLMAdapter
from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter

router = APIRouter(prefix="/api/rollback", tags=["rollback"])

_event_bus: InMemoryEventBus | None = None


def set_event_bus(bus: InMemoryEventBus) -> None:
    global _event_bus
    _event_bus = bus


def _get_event_bus() -> InMemoryEventBus:
    if _event_bus is None:
        raise RuntimeError("Event bus not initialized")
    return _event_bus


def _rollback_uc(
    db: AsyncSession = Depends(get_db),
    bus: InMemoryEventBus = Depends(_get_event_bus),
) -> ExecuteRollback:
    llm = VPCLLMAdapter(settings.LLM_ENDPOINT) if settings.LLM_MODE == "vpc" else MockLLMAdapter()
    return ExecuteRollback(
        git_repo=get_git_repo(),
        deploy_repo=SQLAlchemyDeploymentRepository(db),
        build_runner=BuildProcessRunner(SessionFactory, llm, bus, git_repo=get_git_repo()),
        event_bus=bus,
    )


@router.post("/", response_model=RollbackResultDTO)
async def trigger_rollback(
    req: RollbackRequestDTO,
    uc: ExecuteRollback = Depends(_rollback_uc),
):
    return await uc.execute(req.branch, req.target_sha)
