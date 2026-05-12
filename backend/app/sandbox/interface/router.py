from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.database import get_db
from app.sandbox.application.dtos import SandboxCreateDTO, SandboxResponseDTO
from app.sandbox.application.use_cases import CreateSandbox, StopSandbox, DestroySandbox, ListSandboxes
from app.sandbox.infrastructure.sqlalchemy_repository import SQLAlchemySandboxRepository
from app.auth.dependencies import get_current_user
from app.shared.infrastructure.deploy_lock import check_no_active_deployment
from app.shared.llm_factory import get_llm_for_user
from app.analysis.domain.ports import LLMPort
from app.config import settings

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


def _repo(db: AsyncSession = Depends(get_db)) -> SQLAlchemySandboxRepository:
    return SQLAlchemySandboxRepository(db)


@router.post("/", response_model=SandboxResponseDTO)
async def create_sandbox(req: SandboxCreateDTO, repo=Depends(_repo), db=Depends(get_db), user: dict = Depends(get_current_user)):
    await check_no_active_deployment(db)
    return await CreateSandbox(repo).execute(req.branch)


@router.get("/", response_model=list[SandboxResponseDTO])
async def list_sandboxes(repo=Depends(_repo)):
    return await ListSandboxes(repo).execute()


@router.post("/{sandbox_id}/stop", response_model=SandboxResponseDTO)
async def stop_sandbox(sandbox_id: int, repo=Depends(_repo), user: dict = Depends(get_current_user)):
    return await StopSandbox(repo).execute(sandbox_id)


@router.delete("/{sandbox_id}")
async def destroy_sandbox(sandbox_id: int, repo=Depends(_repo), user: dict = Depends(get_current_user)):
    await DestroySandbox(repo).execute(sandbox_id)
    return {"status": "destroyed"}


@router.post("/{sandbox_id}/analyze")
async def analyze_sandbox_error(
    sandbox_id: int,
    repo=Depends(_repo),
    llm: LLMPort = Depends(get_llm_for_user),
):
    import re
    from pathlib import Path

    sandbox = await repo.find_by_id(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    if not sandbox.error_log:
        raise HTTPException(status_code=400, detail="No error log to analyze")

    # 에러 로그에서 파일명 + 라인 번호 추출하여 소스 첨부
    error_context = sandbox.error_log
    file_pattern = re.findall(r'([\w/.-]+\.(?:tsx?|py|jsx?)):?\((\d+)', sandbox.error_log)
    sandbox_dir = f"{settings.SANDBOX_CONTAINER_PATH}/{sandbox.project_name}"

    for file_path, line_str in file_pattern[:3]:
        full_path = Path(sandbox_dir) / file_path
        if full_path.exists():
            try:
                lines = full_path.read_text(encoding='utf-8').splitlines()
                line_num = int(line_str)
                start = max(0, line_num - 5)
                end = min(len(lines), line_num + 5)
                snippet = "\n".join(f"{i+1:4d} | {lines[i]}" for i in range(start, end))
                error_context += f"\n\n--- {file_path} (line {line_num} 부근) ---\n{snippet}"
            except Exception:
                pass

    rca = await llm.analyze_failure(error_context)
    return {
        "root_cause": rca.root_cause,
        "suggested_fix": rca.suggested_fix,
        "confidence_score": rca.confidence_score,
    }
