from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import settings
from app.git.application.dtos import BranchInfoDTO, FileChangeDTO, DiffResponseDTO
from app.git.application.use_cases import ListBranches, GetChangedFiles, GetDiff
from app.git.infrastructure.git_python_adapter import GitPythonRepository

router = APIRouter(prefix="/api/git", tags=["git"])


def _git_repo() -> GitPythonRepository:
    return GitPythonRepository(settings.REPO_PATH)


def _list_branches_uc(repo=Depends(_git_repo)) -> ListBranches:
    return ListBranches(repo)


def _get_changed_files_uc(repo=Depends(_git_repo)) -> GetChangedFiles:
    return GetChangedFiles(repo)


def _get_diff_uc(repo=Depends(_git_repo)) -> GetDiff:
    return GetDiff(repo)


@router.get("/branches", response_model=list[BranchInfoDTO])
def list_branches(uc: ListBranches = Depends(_list_branches_uc)):
    return uc.execute()


@router.get("/branches/files", response_model=list[FileChangeDTO])
def get_changed_files(branch: str, uc: GetChangedFiles = Depends(_get_changed_files_uc)):
    return uc.execute(branch)


@router.get("/diff", response_model=DiffResponseDTO)
def get_diff(branch: str, path: str, uc: GetDiff = Depends(_get_diff_uc)):
    return uc.execute(branch, path)
