from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.infrastructure.database import get_db
from app.analysis.application.dtos import (
    ImpactAnalysisRequestDTO,
    ImpactAnalysisResponseDTO,
    CodeReviewResponseDTO,
    MergeConflictResponseDTO,
    ConflictResolutionDTO,
    ApplyResolutionRequestDTO,
    RCARequestDTO,
    RCAResponseDTO,
)
from app.analysis.application.use_cases import AnalyzeImpact, ReviewCode, AnalyzeFailure
from app.analysis.infrastructure.mock_llm_adapter import MockLLMAdapter
from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter
from app.analysis.domain.ports import LLMPort
from app.git.infrastructure.git_python_adapter import get_git_repo
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository
from app.auth.dependencies import get_current_user
from app.auth.service import get_user_by_id, get_user_api_key

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


async def _get_user_llm_key(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> str | None:
    u = await get_user_by_id(db, user["id"])
    return get_user_api_key(u) if u else None


def _llm_with_key(user_key: str | None = None) -> LLMPort:
    if settings.LLM_MODE == "inhouse":
        return VPCLLMAdapter(settings.LLM_ENDPOINT, user_api_key=user_key)
    return MockLLMAdapter()


@router.post("/impact", response_model=ImpactAnalysisResponseDTO)
async def analyze_impact(req: ImpactAnalysisRequestDTO, user_key: str | None = Depends(_get_user_llm_key)):
    llm = _llm_with_key(user_key)
    uc = AnalyzeImpact(llm, get_git_repo())
    return await uc.execute(req.branch, req.file_paths)


@router.post("/review", response_model=CodeReviewResponseDTO)
async def review_code(req: ImpactAnalysisRequestDTO, user_key: str | None = Depends(_get_user_llm_key)):
    llm = _llm_with_key(user_key)
    uc = ReviewCode(llm, get_git_repo())
    return await uc.execute(req.branch, req.file_paths)


@router.post("/conflicts", response_model=MergeConflictResponseDTO)
async def check_conflicts(req: ImpactAnalysisRequestDTO, user_key: str | None = Depends(_get_user_llm_key)):
    llm = _llm_with_key(user_key)
    conflicts = get_git_repo().check_merge_conflicts(req.branch)
    if not conflicts:
        return MergeConflictResponseDTO(has_conflicts=False)

    report = await llm.resolve_conflicts(conflicts)
    return MergeConflictResponseDTO(
        has_conflicts=True,
        conflicting_files=report.conflicting_files,
        resolutions=[
            ConflictResolutionDTO(
                file_path=r.file_path, original_content=r.original_content,
                resolved_content=r.resolved_content, explanation=r.explanation,
            )
            for r in report.resolutions
        ],
        summary=report.summary,
    )


@router.post("/conflicts/apply")
async def apply_resolution(req: ApplyResolutionRequestDTO):
    sha = get_git_repo().apply_conflict_resolution(req.branch, req.resolutions)
    return {"status": "merged", "commit_sha": sha}


@router.post("/rca", response_model=RCAResponseDTO)
async def analyze_rca(
    req: RCARequestDTO,
    db: AsyncSession = Depends(get_db),
    user_key: str | None = Depends(_get_user_llm_key),
):
    build_log = req.build_log
    if not build_log and req.deployment_id:
        dep = await SQLAlchemyDeploymentRepository(db).find_by_id(req.deployment_id)
        if not dep:
            raise HTTPException(status_code=404, detail="Deployment not found")
        build_log = dep.build_log or dep.error_log or ""

    if not build_log:
        raise HTTPException(status_code=400, detail="No build log available")

    uc = AnalyzeFailure(_llm_with_key(user_key))
    return await uc.execute(build_log)
