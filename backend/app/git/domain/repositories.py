from __future__ import annotations

from abc import ABC, abstractmethod
from app.git.domain.entities import Branch, FileChange


class GitRepositoryPort(ABC):
    @abstractmethod
    def list_branches(self) -> list[Branch]: ...

    @abstractmethod
    def get_changed_files(self, branch: str) -> list[FileChange]: ...

    @abstractmethod
    def get_diff(self, branch: str, file_path: str) -> str: ...

    @abstractmethod
    def get_full_diff(self, branch: str) -> str: ...

    @abstractmethod
    def get_current_sha(self, branch: str) -> str: ...

    @abstractmethod
    def get_last_stable_sha(self, branch: str) -> str | None: ...

    @abstractmethod
    def revert_to(self, branch: str, target_sha: str) -> str: ...

    @abstractmethod
    def create_branch(self, new_branch: str, base_branch: str) -> Branch: ...

    @abstractmethod
    def delete_branch(self, branch: str) -> None: ...

    @abstractmethod
    def check_merge_conflicts(self, branch: str) -> dict[str, str]:
        """Dry-run merge to detect conflicts. Returns {file_path: conflict_content}."""
        ...

    @abstractmethod
    def apply_conflict_resolution(self, branch: str, resolutions: dict[str, str]) -> str:
        """Apply resolved files and complete merge. Returns new commit SHA."""
        ...

    @abstractmethod
    def get_diff_between(self, sha_from: str, sha_to: str) -> str:
        """Get diff between two commit SHAs."""
        ...

    @abstractmethod
    def get_commit_messages(self, branch: str) -> list[str]:
        """Get commit messages unique to this branch (not in main)."""
        ...

    @abstractmethod
    def merge_to_main(self, branch: str) -> str:
        """Merge branch into main. Returns new main commit SHA."""
        ...

    def get_commit_changed_files(self, commit_sha: str) -> list[str]:
        """Get list of changed file paths in a specific commit."""
        return []
