from __future__ import annotations

import logging
import threading
from pathlib import Path

from git import Repo

from app.git.domain.entities import Branch, FileChange
from app.git.domain.repositories import GitRepositoryPort
from app.git.domain.exceptions import RepositoryNotFound

logger = logging.getLogger(__name__)

_instance: GitPythonRepository | None = None
_instance_lock = threading.Lock()


def get_git_repo() -> GitPythonRepository:
    """App-level singleton for GitPythonRepository."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                from app.config import settings
                _instance = GitPythonRepository(settings.REPO_PATH)
    return _instance


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
        branches = []
        for b in self._repo.branches:
            try:
                branches.append(Branch(
                    name=b.name,
                    is_active=b.name == active,
                    last_commit_sha=b.commit.hexsha[:8],
                    last_commit_message=b.commit.message.strip()[:100],
                ))
            except (ValueError, Exception) as e:
                logger.warning("Skipping invalid branch ref: %s", e)
        return branches

    def _branch_names(self) -> list[str]:
        names = []
        for b in self._repo.branches:
            try:
                names.append(b.name)
            except (ValueError, Exception):
                pass
        return names

    def get_changed_files(self, branch: str) -> list[FileChange]:
        from app.git.domain.exceptions import BranchNotFound
        if branch not in self._branch_names():
            raise BranchNotFound(branch)
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

    def check_merge_conflicts(self, branch: str) -> dict[str, str]:
        """Dry-run merge to detect conflicts. Returns {file: conflict_content} or empty if no conflicts."""
        import os
        with self._lock:
            original = (
                self._repo.active_branch.name
                if not self._repo.head.is_detached
                else None
            )
            stashed = False
            try:
                self._repo.git.stash("push", "-m", "auto-stash before conflict check")
                stashed = True
            except Exception:
                pass

            try:
                self._repo.git.checkout("main")
                try:
                    self._repo.git.merge("--no-commit", "--no-ff", branch)
                    # No conflict
                    self._repo.git.merge("--abort")
                    return {}
                except Exception:
                    # Conflict detected - read conflicting files
                    conflicts = {}
                    status = self._repo.git.status("--porcelain")
                    for line in status.split("\n"):
                        if line.startswith("UU ") or line.startswith("AA "):
                            file_path = line[3:].strip()
                            full_path = os.path.join(self._repo.working_dir, file_path)
                            try:
                                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                                    conflicts[file_path] = f.read()
                            except Exception:
                                conflicts[file_path] = ""
                    try:
                        self._repo.git.merge("--abort")
                    except Exception:
                        pass
                    return conflicts
            finally:
                if original and original != "main":
                    self._repo.git.checkout(original)
                if stashed:
                    try:
                        self._repo.git.stash("pop")
                    except Exception:
                        logger.warning("Failed to pop stash after conflict check")

    def apply_conflict_resolution(self, branch: str, resolutions: dict[str, str]) -> str:
        """Apply resolved files and complete merge."""
        import os
        with self._lock:
            original = (
                self._repo.active_branch.name
                if not self._repo.head.is_detached
                else None
            )
            stashed = False
            try:
                self._repo.git.stash("push", "-m", "auto-stash before resolution")
                stashed = True
            except Exception:
                pass

            try:
                self._repo.git.checkout("main")
                try:
                    self._repo.git.merge("--no-commit", "--no-ff", branch)
                except Exception:
                    pass  # Expected conflict

                # Write resolved files
                for file_path, content in resolutions.items():
                    full_path = os.path.join(self._repo.working_dir, file_path)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self._repo.git.add(file_path)

                self._repo.git.commit("-m", f"Merge branch '{branch}' into main (AI conflict resolution)")
                return self._repo.head.commit.hexsha
            finally:
                if original and original != "main":
                    self._repo.git.checkout(original)
                if stashed:
                    try:
                        self._repo.git.stash("pop")
                    except Exception:
                        logger.warning("Failed to pop stash after resolution")

    def get_diff_between(self, sha_from: str, sha_to: str) -> str:
        try:
            return self._repo.git.diff(sha_from, sha_to)
        except Exception:
            return ""

    def get_commit_messages(self, branch: str) -> list[str]:
        try:
            output = self._repo.git.log("--oneline", f"main..{branch}")
            if not output.strip():
                return []
            return [line.split(" ", 1)[1] if " " in line else line for line in output.strip().split("\n")]
        except Exception:
            return []

    def get_current_sha(self, branch: str) -> str:
        return self._repo.branches[branch].commit.hexsha

    def get_last_stable_sha(self, branch: str) -> str | None:
        try:
            commit = self._repo.branches[branch].commit
            if commit.parents:
                return commit.parents[0].hexsha
        except Exception:
            logger.debug("No parent commit found for branch %s", branch)
        return None

    def _cleanup_index(self) -> None:
        """Clean up broken git index state before operations."""
        try:
            self._repo.git.merge("--abort")
        except Exception:
            pass
        try:
            self._repo.git.reset("HEAD")
        except Exception:
            pass

    def merge_to_main(self, branch: str) -> str:
        from app.git.domain.exceptions import BranchNotFound

        with self._lock:
            if branch not in self._branch_names():
                raise BranchNotFound(branch)

            self._cleanup_index()

            original = (
                self._repo.active_branch.name
                if not self._repo.head.is_detached
                else None
            )
            stashed = False
            try:
                self._repo.git.stash("push", "-m", "auto-stash before merge")
                stashed = True
            except Exception:
                logger.debug("Nothing to stash before merge")

            try:
                self._repo.git.checkout("main")
                self._repo.git.merge(branch, "--no-ff", "-m", f"Merge branch '{branch}' into main")
                return self._repo.head.commit.hexsha
            finally:
                if original and original != "main":
                    self._repo.git.checkout(original)
                if stashed:
                    try:
                        self._repo.git.stash("pop")
                    except Exception:
                        logger.warning("Failed to pop stash after merge")

    def delete_branch(self, branch: str) -> None:
        from app.git.domain.exceptions import BranchNotFound, CannotDeleteMainBranch

        if branch == "main":
            raise CannotDeleteMainBranch()
        with self._lock:
            if branch not in self._branch_names():
                raise BranchNotFound(branch)
            self._repo.git.branch("-D", branch)

    def create_branch(self, new_branch: str, base_branch: str) -> Branch:
        from app.git.domain.exceptions import BranchAlreadyExists, BranchNotFound

        with self._lock:
            if new_branch in self._branch_names():
                raise BranchAlreadyExists(new_branch)
            if base_branch not in self._branch_names():
                raise BranchNotFound(base_branch)

            base_ref = self._repo.branches[base_branch]
            new_ref = self._repo.create_head(new_branch, base_ref.commit)
            return Branch(
                name=new_ref.name,
                is_active=False,
                last_commit_sha=new_ref.commit.hexsha[:8],
                last_commit_message=new_ref.commit.message.strip()[:100],
            )

    def revert_to(self, branch: str, target_sha: str) -> str:
        with self._lock:
            self._cleanup_index()
            original = (
                self._repo.active_branch.name
                if not self._repo.head.is_detached
                else None
            )
            stashed = False
            try:
                self._repo.git.stash("push", "-m", "auto-stash before revert")
                stashed = True
            except Exception:
                logger.debug("Nothing to stash before revert")

            try:
                self._repo.git.checkout("main")
                head = self._repo.head.commit
                if len(head.parents) > 1:
                    self._repo.git.revert("--no-edit", "-m", "1", head.hexsha)
                else:
                    self._repo.git.revert("--no-edit", head.hexsha)
                return self._repo.head.commit.hexsha
            finally:
                if original and original != "main":
                    self._repo.git.checkout(original)
                if stashed:
                    try:
                        self._repo.git.stash("pop")
                    except Exception:
                        logger.warning("Failed to pop stash after revert")
