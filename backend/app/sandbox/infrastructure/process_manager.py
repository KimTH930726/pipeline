from __future__ import annotations

import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class SandboxProcessManager:
    """Manages sandbox Docker compose lifecycle."""

    @staticmethod
    async def start(
        project_name: str,
        backend_port: int,
        frontend_port: int,
    ) -> bool:
        """Start backend + frontend with custom ports using existing images."""
        compose_file = f"{settings.DEPLOY_TARGET_PATH}/docker-compose.yml"

        env_overrides = {
            "BACKEND_PORT": str(backend_port),
            "FRONTEND_PORT": str(frontend_port),
            "CONTAINER_PREFIX": project_name,
        }

        # --no-deps: postgres/redis 새로 만들지 않음
        cmd = (
            f"docker compose -f {compose_file} -p {project_name} "
            f"up -d --no-deps backend frontend"
        )

        # 생성 후 기존 운영 네트워크에 연결 (DB/Redis 공유)
        post_cmd = (
            f"docker network connect smagentlab_default {project_name}-backend 2>/dev/null; "
            f"docker network connect smagentlab_default {project_name}-frontend 2>/dev/null"
        )

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**dict(__import__('os').environ), **env_overrides},
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error("Sandbox start failed: %s", stderr.decode())
                return False

            # 기존 운영 네트워크에 연결
            net_process = await asyncio.create_subprocess_shell(
                post_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await net_process.communicate()
            return True
        except Exception:
            logger.exception("Failed to start sandbox %s", project_name)
            return False

    @staticmethod
    async def stop(project_name: str) -> None:
        """Stop sandbox containers."""
        compose_file = f"{settings.DEPLOY_TARGET_PATH}/docker-compose.yml"
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "compose", "-f", compose_file, "-p", project_name,
                "stop", "backend", "frontend",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()
        except Exception:
            logger.exception("Failed to stop sandbox %s", project_name)

    @staticmethod
    async def destroy(project_name: str) -> None:
        """Remove sandbox containers only (DB/볼륨 보호)."""
        # stop + rm으로 컨테이너만 제거 (down -v 사용 안 함 — 운영 볼륨 보호)
        for suffix in ["backend", "frontend"]:
            container = f"{project_name}-{suffix}"
            try:
                process = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.wait()
            except Exception:
                pass

        # 샌드박스 전용 네트워크 정리
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "network", "rm", f"{project_name}_default",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()
        except Exception:
            pass
