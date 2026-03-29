from __future__ import annotations

import threading
from pathlib import Path

from git import Repo

from app.git.domain.entities import Branch, FileChange
from app.git.domain.repositories import GitRepositoryPort
from app.git.domain.exceptions import RepositoryNotFound


class GitPythonRepository(GitRepositoryPort):
    def __init__(self, repo_path: str) -> None:
        path = Path(repo_path)
        if not path.exists():
            raise RepositoryNotFound(repo_path)
        self._repo = Repo(str(path))
        self._lock = threading.Lock()

    def list_branches(self) -> list[Branch]:
        active = (
            self._repo.active_branch.name
            if not self._repo.head.is_detached
            else None
        )
        return [
            Branch(
                name=b.name,
                is_active=b.name == active,
                last_commit_sha=b.commit.hexsha[:8],
                last_commit_message=b.commit.message.strip()[:100],
            )
            for b in self._repo.branches
        ]

    def get_changed_files(self, branch: str) -> list[FileChange]:
        output = self._repo.git.diff("--name-status", f"main...{branch}")
        if not output.strip():
            return []
        changes = []
        for line in output.strip().split("\n"):
            parts = line.split("\t", 1)
            if len(parts) == 2:
                changes.append(FileChange(status=parts[0], path=parts[1]))
        return changes

    def get_diff(self, branch: str, file_path: str) -> str:
        return self._repo.git.diff("main", branch, "--", file_path)

    def get_full_diff(self, branch: str) -> str:
        return self._repo.git.diff("main", branch)

    def get_current_sha(self, branch: str) -> str:
        return self._repo.branches[branch].commit.hexsha

    def get_last_stable_sha(self, branch: str) -> str | None:
        try:
            commit = self._repo.branches[branch].commit
            if commit.parents:
                return commit.parents[0].hexsha
        except Exception:
            pass
        return None

    def revert_to(self, branch: str, target_sha: str) -> str:
        with self._lock:
            original = (
                self._repo.active_branch.name
                if not self._repo.head.is_detached
                else None
            )
            try:
                self._repo.git.checkout(branch)
                self._repo.git.revert("--no-edit", "--no-commit", f"{target_sha}..HEAD")
                self._repo.git.commit("-m", f"Rollback to {target_sha[:8]}")
                return self._repo.head.commit.hexsha
            finally:
                if original and original != branch:
                    self._repo.git.checkout(original)
