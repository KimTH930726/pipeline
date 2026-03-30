from __future__ import annotations

from app.git.domain.repositories import GitRepositoryPort
from app.git.application.dtos import BranchInfoDTO, FileChangeDTO, DiffResponseDTO


class ListBranches:
    def __init__(self, repo: GitRepositoryPort) -> None:
        self._repo = repo

    def execute(self) -> list[BranchInfoDTO]:
        return [
            BranchInfoDTO(
                name=b.name,
                is_active=b.is_active,
                last_commit_sha=b.last_commit_sha,
                last_commit_message=b.last_commit_message,
            )
            for b in self._repo.list_branches()
        ]


class GetChangedFiles:
    def __init__(self, repo: GitRepositoryPort) -> None:
        self._repo = repo

    def execute(self, branch: str) -> list[FileChangeDTO]:
        return [
            FileChangeDTO(path=f.path, status=f.status)
            for f in self._repo.get_changed_files(branch)
        ]


class CreateBranch:
    def __init__(self, repo: GitRepositoryPort) -> None:
        self._repo = repo

    def execute(self, new_branch: str, base_branch: str) -> BranchInfoDTO:
        branch = self._repo.create_branch(new_branch, base_branch)
        return BranchInfoDTO(
            name=branch.name,
            is_active=branch.is_active,
            last_commit_sha=branch.last_commit_sha,
            last_commit_message=branch.last_commit_message,
        )


class DeleteBranch:
    def __init__(self, repo: GitRepositoryPort) -> None:
        self._repo = repo

    def execute(self, branch: str) -> None:
        self._repo.delete_branch(branch)


class GetDiff:
    def __init__(self, repo: GitRepositoryPort) -> None:
        self._repo = repo

    def execute(self, branch: str, file_path: str) -> DiffResponseDTO:
        diff_text = self._repo.get_diff(branch, file_path)
        return DiffResponseDTO(branch=branch, file_path=file_path, diff_text=diff_text)
