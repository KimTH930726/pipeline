from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.infrastructure.database import get_db
from app.analysis.application.dtos import (
    ImpactAnalysisRequestDTO,
    ImpactAnalysisResponseDTO,
    CodeReviewResponseDTO,
    CodeReviewCommentDTO,
    MergeConflictResponseDTO,
    ConflictResolutionDTO,
    ApplyResolutionRequestDTO,
    RCARequestDTO,
    RCAResponseDTO,
)

from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter
from app.analysis.domain.ports import LLMPort
from app.git.infrastructure.git_python_adapter import get_git_repo
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

logger = __import__("logging").getLogger(__name__)


def _llm(user: dict | None = None) -> LLMPort:
    if not settings.LLM_CLIENT_ID or not settings.LLM_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="LLM_CLIENT_ID/LLM_CLIENT_SECRET가 설정되지 않았습니다. 운영자에게 문의하세요.",
        )
    user_identifier = (user or {}).get("username") or str((user or {}).get("id") or "system")
    return VPCLLMAdapter(user_identifier=user_identifier)


@router.post("/impact", response_model=ImpactAnalysisResponseDTO)
async def analyze_impact(req: ImpactAnalysisRequestDTO, user: dict = Depends(get_current_user)):
    llm = _llm(user)
    git_repo = get_git_repo()
    diff_text = git_repo.get_full_diff(req.branch)
    changes = git_repo.get_changed_files(req.branch)
    file_paths = req.file_paths or [c.path for c in changes]
    report = await llm.analyze_impact(diff_text, file_paths)
    return ImpactAnalysisResponseDTO(
        risk_level=report.risk_level.value, summary=report.summary,
        affected_services=report.affected_services, recommendations=report.recommendations,
    )


@router.post("/review", response_model=CodeReviewResponseDTO)
async def review_code(req: ImpactAnalysisRequestDTO, user: dict = Depends(get_current_user)):
    llm = _llm(user)
    git_repo = get_git_repo()
    diff_text = git_repo.get_full_diff(req.branch)
    changes = git_repo.get_changed_files(req.branch)
    file_paths = req.file_paths or [c.path for c in changes]
    report = await llm.review_code(diff_text, file_paths)
    return CodeReviewResponseDTO(
        summary=report.summary,
        comments=[CodeReviewCommentDTO(
            file_path=c.file_path, line=c.line, severity=c.severity,
            category=c.category, message=c.message, suggested_code=c.suggested_code,
        ) for c in report.comments],
        overall_quality=report.overall_quality,
    )


@router.post("/conflicts", response_model=MergeConflictResponseDTO)
async def check_conflicts(req: ImpactAnalysisRequestDTO, user: dict = Depends(get_current_user)):
    conflicts = get_git_repo().check_merge_conflicts(req.branch)
    if not conflicts:
        return MergeConflictResponseDTO(has_conflicts=False)

    llm = _llm(user)
    try:
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
    except Exception:
        return MergeConflictResponseDTO(
            has_conflicts=True,
            conflicting_files=list(conflicts.keys()),
            resolutions=[
                ConflictResolutionDTO(
                    file_path=fp, original_content=content,
                    resolved_content=content, explanation="AI 해결안 생성 실패 — 충돌 마커를 직접 제거해주세요.",
                )
                for fp, content in conflicts.items()
            ],
            summary="AI 충돌 해결에 실패했습니다. 각 파일의 충돌 마커(<<<<<<, ======, >>>>>>)를 직접 제거하고 해결안을 작성해주세요.",
        )


@router.post("/conflicts/apply")
async def apply_resolution(req: ApplyResolutionRequestDTO):
    sha = get_git_repo().apply_conflict_resolution(req.branch, req.resolutions)
    return {"status": "merged", "commit_sha": sha}


@router.post("/rca", response_model=RCAResponseDTO)
async def analyze_rca(
    req: RCARequestDTO,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    build_log = req.build_log
    if not build_log and req.deployment_id:
        dep = await SQLAlchemyDeploymentRepository(db).find_by_id(req.deployment_id)
        if not dep:
            raise HTTPException(status_code=404, detail="Deployment not found")
        build_log = dep.build_log or dep.error_log or ""

    if not build_log:
        raise HTTPException(status_code=400, detail="No build log available")

    llm = _llm(user)
    report = await llm.analyze_failure(build_log)
    return RCAResponseDTO(
        root_cause=report.root_cause, affected_files=report.affected_files,
        suggested_fix=report.suggested_fix, confidence_score=report.confidence_score,
        ai_fix_prompt=report.ai_fix_prompt,
    )
