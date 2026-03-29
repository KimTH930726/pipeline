from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.infrastructure.database import get_db
from app.analysis.application.dtos import (
    ImpactAnalysisRequestDTO,
    ImpactAnalysisResponseDTO,
    RCARequestDTO,
    RCAResponseDTO,
)
from app.analysis.application.use_cases import AnalyzeImpact, AnalyzeFailure
from app.analysis.infrastructure.mock_llm_adapter import MockLLMAdapter
from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter
from app.analysis.domain.ports import LLMPort
from app.git.infrastructure.git_python_adapter import GitPythonRepository
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _llm() -> LLMPort:
    if settings.LLM_MODE == "vpc":
        return VPCLLMAdapter(settings.LLM_ENDPOINT)
    return MockLLMAdapter()


def _impact_uc(llm: LLMPort = Depends(_llm)) -> AnalyzeImpact:
    return AnalyzeImpact(llm, GitPythonRepository(settings.REPO_PATH))


def _failure_uc(llm: LLMPort = Depends(_llm)) -> AnalyzeFailure:
    return AnalyzeFailure(llm)


@router.post("/impact", response_model=ImpactAnalysisResponseDTO)
async def analyze_impact(
    req: ImpactAnalysisRequestDTO,
    uc: AnalyzeImpact = Depends(_impact_uc),
):
    return await uc.execute(req.branch, req.file_paths)


@router.post("/rca", response_model=RCAResponseDTO)
async def analyze_rca(
    req: RCARequestDTO,
    db: AsyncSession = Depends(get_db),
    uc: AnalyzeFailure = Depends(_failure_uc),
):
    build_log = req.build_log
    if not build_log and req.deployment_id:
        repo = SQLAlchemyDeploymentRepository(db)
        dep = await repo.find_by_id(req.deployment_id)
        if not dep:
            raise HTTPException(status_code=404, detail="Deployment not found")
        build_log = dep.build_log or dep.error_log or ""

    if not build_log:
        raise HTTPException(status_code=400, detail="No build log available")

    return await uc.execute(build_log)
