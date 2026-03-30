from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter, Depends

from app.git.application.dtos import BranchInfoDTO, FileChangeDTO, DiffResponseDTO, CreateBranchRequestDTO
from app.git.application.use_cases import ListBranches, GetChangedFiles, GetDiff, CreateBranch, DeleteBranch
from app.git.infrastructure.git_python_adapter import get_git_repo

router = APIRouter(prefix="/api/git", tags=["git"])


def _git_repo():
    return get_git_repo()


async def _run_sync(func, *args):
    """Run blocking git operations in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args))


@router.get("/branches", response_model=list[BranchInfoDTO])
async def list_branches(repo=Depends(_git_repo)):
    return await _run_sync(ListBranches(repo).execute)


@router.get("/branches/files", response_model=list[FileChangeDTO])
async def get_changed_files(branch: str, repo=Depends(_git_repo)):
    return await _run_sync(GetChangedFiles(repo).execute, branch)


@router.post("/branches", response_model=BranchInfoDTO, status_code=201)
async def create_branch(body: CreateBranchRequestDTO, repo=Depends(_git_repo)):
    return await _run_sync(CreateBranch(repo).execute, body.new_branch, body.base_branch)


@router.delete("/branches/{branch:path}", status_code=204)
async def delete_branch(branch: str, repo=Depends(_git_repo)):
    await _run_sync(DeleteBranch(repo).execute, branch)


@router.get("/diff", response_model=DiffResponseDTO)
async def get_diff(branch: str, path: str, repo=Depends(_git_repo)):
    return await _run_sync(GetDiff(repo).execute, branch, path)
