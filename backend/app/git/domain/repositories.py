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
