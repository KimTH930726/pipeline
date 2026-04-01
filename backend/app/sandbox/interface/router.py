from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.database import get_db
from app.sandbox.application.dtos import SandboxCreateDTO, SandboxResponseDTO
from app.sandbox.application.use_cases import CreateSandbox, StopSandbox, DestroySandbox, ListSandboxes
from app.sandbox.infrastructure.sqlalchemy_repository import SQLAlchemySandboxRepository
from app.auth.dependencies import get_current_user
from app.analysis.infrastructure.vpc_llm_adapter import VPCLLMAdapter
from app.config import settings
from app.auth.service import get_user_by_id, get_user_api_key
from fastapi import HTTPException

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


def _repo(db: AsyncSession = Depends(get_db)) -> SQLAlchemySandboxRepository:
    return SQLAlchemySandboxRepository(db)


@router.post("/", response_model=SandboxResponseDTO)
async def create_sandbox(req: SandboxCreateDTO, repo=Depends(_repo), user: dict = Depends(get_current_user)):
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
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
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

    user_obj = await get_user_by_id(db, user["id"])
    user_key = get_user_api_key(user_obj) if user_obj else None
    llm = VPCLLMAdapter(settings.LLM_ENDPOINT, api_key=user_key or settings.LLM_API_KEY)
    rca = await llm.analyze_failure(error_context)
    return {
        "root_cause": rca.root_cause,
        "suggested_fix": rca.suggested_fix,
        "confidence_score": rca.confidence_score,
    }
