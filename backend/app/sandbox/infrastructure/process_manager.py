from __future__ import annotations

import asyncio
import shutil
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class SandboxProcessManager:
    """Manages sandbox Docker compose lifecycle using git worktree."""

    @staticmethod
    async def create_worktree(branch: str, sandbox_id: int) -> str:
        """Create a git worktree for the branch. Returns worktree path."""
        worktree_path = f"/tmp/sandbox_{sandbox_id}"
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "-C", settings.REPO_PATH,
                "worktree", "add", worktree_path, branch,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()
            return worktree_path
        except Exception:
            logger.exception("Failed to create worktree for sandbox %s", sandbox_id)
            raise

    @staticmethod
    async def start(
        worktree_path: str,
        project_name: str,
        backend_port: int,
        frontend_port: int,
    ) -> bool:
        """Start backend + frontend via docker compose with custom ports."""
        compose_file = f"{worktree_path}/docker-compose.yml"

        env_overrides = {
            "BACKEND_PORT": str(backend_port),
            "FRONTEND_PORT": str(frontend_port),
            "CONTAINER_PREFIX": project_name,
        }

        cmd = (
            f"docker compose -f {compose_file} -p {project_name} "
            f"up -d backend frontend"
        )

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    **dict(__import__('os').environ),
                    **env_overrides,
                },
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error("Sandbox start failed: %s", stderr.decode())
                return False
            return True
        except Exception:
            logger.exception("Failed to start sandbox %s", project_name)
            return False

    @staticmethod
    async def stop(project_name: str, worktree_path: str) -> None:
        """Stop sandbox containers."""
        compose_file = f"{worktree_path}/docker-compose.yml"
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "compose", "-f", compose_file, "-p", project_name,
                "stop",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()
        except Exception:
            logger.exception("Failed to stop sandbox %s", project_name)

    @staticmethod
    async def destroy(project_name: str, worktree_path: str) -> None:
        """Remove sandbox containers, volumes, and worktree."""
        compose_file = f"{worktree_path}/docker-compose.yml"

        # docker compose down
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "compose", "-f", compose_file, "-p", project_name,
                "down", "--remove-orphans", "-v", "--rmi", "local",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()
        except Exception:
            logger.exception("Failed to docker compose down for %s", project_name)

        # Remove git worktree
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "-C", settings.REPO_PATH,
                "worktree", "remove", "--force", worktree_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()
        except Exception:
            # Fallback: just delete the directory
            try:
                shutil.rmtree(worktree_path, ignore_errors=True)
            except Exception:
                pass
