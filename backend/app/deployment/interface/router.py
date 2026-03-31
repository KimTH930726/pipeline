from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.infrastructure.database import get_db, SessionFactory
from app.shared.infrastructure.event_bus import InMemoryEventBus
from app.deployment.application.dtos import DeployRequestDTO, DeployStatusDTO, DeployDetailDTO, DeployPageDTO
from app.deployment.application.use_cases import TriggerDeploy, GetDeployment, GetRecentDeployments, MarkRolledBack
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository
from app.deployment.infrastructure.build_runner import BuildProcessRunner
from app.deployment.infrastructure.websocket_manager import ws_manager
from app.analysis.infrastructure.mock_llm_adapter import MockLLMAdapter
from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter
from app.git.infrastructure.git_python_adapter import get_git_repo
from app.review.infrastructure.sqlalchemy_repository import SQLAlchemyReviewRepository
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/deploy", tags=["deploy"])

_event_bus: InMemoryEventBus | None = None


def set_event_bus(bus: InMemoryEventBus) -> None:
    global _event_bus
    _event_bus = bus


def _get_event_bus() -> InMemoryEventBus:
    if _event_bus is None:
        raise RuntimeError("Event bus not initialized")
    return _event_bus


def _build_runner(bus: InMemoryEventBus = Depends(_get_event_bus)) -> BuildProcessRunner:
    llm = VPCLLMAdapter(settings.LLM_ENDPOINT) if settings.LLM_MODE == "inhouse" else MockLLMAdapter()
    return BuildProcessRunner(SessionFactory, llm, bus, git_repo=get_git_repo())


def _trigger_uc(
    db: AsyncSession = Depends(get_db),
    runner: BuildProcessRunner = Depends(_build_runner),
) -> TriggerDeploy:
    return TriggerDeploy(
        SQLAlchemyDeploymentRepository(db),
        get_git_repo(),
        runner,
    )


def _get_uc(db: AsyncSession = Depends(get_db)) -> GetDeployment:
    return GetDeployment(SQLAlchemyDeploymentRepository(db))


def _recent_uc(db: AsyncSession = Depends(get_db)) -> GetRecentDeployments:
    return GetRecentDeployments(SQLAlchemyDeploymentRepository(db))


@router.post("/", response_model=DeployStatusDTO)
async def trigger_deploy(
    req: DeployRequestDTO,
    uc: TriggerDeploy = Depends(_trigger_uc),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    review = await SQLAlchemyReviewRepository(db).find_by_branch(req.branch)
    if not review or not review.is_approved:
        raise HTTPException(status_code=403, detail="Branch not approved for deployment")

    branches = [b.name for b in get_git_repo().list_branches()]
    if req.branch not in branches:
        raise HTTPException(status_code=404, detail=f"Branch '{req.branch}' not found")

    return await uc.execute(req.branch)


@router.get("/status/{deployment_id}", response_model=DeployDetailDTO)
async def get_status(deployment_id: int, uc: GetDeployment = Depends(_get_uc)):
    result = await uc.execute(deployment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return result


@router.post("/status/{deployment_id}/rolled-back")
async def mark_rolled_back(deployment_id: int, db: AsyncSession = Depends(get_db)):
    await MarkRolledBack(SQLAlchemyDeploymentRepository(db)).execute(deployment_id)
    return {"status": "marked"}


@router.get("/recent", response_model=DeployPageDTO)
async def get_recent(
    branch: str | None = None,
    page: int = 1,
    size: int = 10,
    uc: GetRecentDeployments = Depends(_recent_uc),
):
    items, total = await uc.execute(branch, page=page, size=size)
    return DeployPageDTO(items=items, total=total, page=page, size=size)


@router.get("/compare/{id_from}/{id_to}")
async def compare_deploys(id_from: int, id_to: int, db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyDeploymentRepository(db)
    dep_from = await repo.find_by_id(id_from)
    dep_to = await repo.find_by_id(id_to)
    if not dep_from or not dep_to:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not dep_from.commit_sha or not dep_to.commit_sha:
        raise HTTPException(status_code=400, detail="Commit SHA not available")

    git_repo = get_git_repo()
    diff_text = git_repo.get_diff_between(dep_from.commit_sha, dep_to.commit_sha)
    return {
        "from": {"id": dep_from.id, "branch": dep_from.branch, "commit_sha": dep_from.commit_sha},
        "to": {"id": dep_to.id, "branch": dep_to.branch, "commit_sha": dep_to.commit_sha},
        "diff_text": diff_text,
    }


@router.websocket("/ws/{deployment_id}")
async def build_websocket(websocket: WebSocket, deployment_id: str):
    await ws_manager.connect(deployment_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(deployment_id, websocket)
