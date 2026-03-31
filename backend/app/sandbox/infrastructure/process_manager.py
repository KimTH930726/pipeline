from __future__ import annotations

import asyncio
import shutil
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class SandboxProcessManager:
    """브랜치별 소스 추출 + Docker 컨테이너 기동."""

    @staticmethod
    async def start(
        project_name: str,
        branch: str,
        backend_port: int,
        frontend_port: int,
    ) -> tuple[bool, str]:
        """Returns: (success, error_log)"""
        backend_name = f"{project_name}-backend"
        frontend_name = f"{project_name}-frontend"
        network = "smagentlab_default"
        # 컨테이너 내부 경로 (소스 추출용)
        sandbox_dir = f"{settings.SANDBOX_CONTAINER_PATH}/{project_name}"
        # 호스트 경로 (docker run 볼륨 마운트용)
        host_sandbox_dir = f"{settings.SANDBOX_HOST_PATH}/{project_name}"
        src = settings.DEPLOY_COMPOSE_PATH  # /deploy-target

        try:
            # 1. 기존 정리
            if Path(sandbox_dir).exists():
                shutil.rmtree(sandbox_dir)
            Path(sandbox_dir).mkdir(parents=True)

            # 2. 브랜치 소스 추출 (git archive)
            process = await asyncio.create_subprocess_shell(
                f"cd {src} && git archive {branch} -- backend/ | tar -x -C {sandbox_dir}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0 or not Path(f"{sandbox_dir}/backend").exists():
                return False, f"브랜치 '{branch}' 소스 추출 실패: {stderr.decode()}"

            # 3. 환경변수 추출 (.env 파일에서)
            env_flags = (
                "-e DATABASE_URL=postgresql://ops:ops1234@ops-postgres:5432/opsdb "
                "-e REDIS_URL=redis://ops-redis:6379/0 "
            )
            env_file = f"{src}/.env"
            if Path(env_file).exists():
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            env_flags += f"-e {line} "

            # 4. 컨테이너 기동
            host_backend = f"{host_sandbox_dir}/backend"

            backend_cmd = (
                f"docker run -d --name {backend_name} "
                f"--network {network} "
                f"-p {backend_port}:8000 "
                f"-v {host_backend}:/app "
                f"{env_flags}"
                f"smagentlab-backend:latest"
            )

            frontend_cmd = (
                f"docker run -d --name {frontend_name} "
                f"--network {network} "
                f"-p {frontend_port}:80 "
                f"smagentlab-frontend:latest"
            )

            for cmd_name, cmd in [("backend", backend_cmd), ("frontend", frontend_cmd)]:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    return False, f"{cmd_name} 컨테이너 기동 실패: {stderr.decode()}"

            # 5. backend 기동 확인 (15초 대기)
            await asyncio.sleep(15)
            process = await asyncio.create_subprocess_shell(
                f"docker logs {backend_name} 2>&1 | tail -10",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            log = stdout.decode()

            if "Error" in log or "error" in log.lower():
                return True, f"기동 경고:\n{log}"

            return True, ""

        except Exception as e:
            return False, f"샌드박스 생성 실패: {str(e)}"

    @staticmethod
    async def stop(project_name: str) -> None:
        for suffix in ["backend", "frontend"]:
            try:
                p = await asyncio.create_subprocess_exec(
                    "docker", "stop", f"{project_name}-{suffix}",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await p.wait()
            except Exception:
                pass

    @staticmethod
    async def destroy(project_name: str) -> None:
        for suffix in ["backend", "frontend"]:
            try:
                p = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", f"{project_name}-{suffix}",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await p.wait()
            except Exception:
                pass
        shutil.rmtree(f"{settings.SANDBOX_CONTAINER_PATH}/{project_name}", ignore_errors=True)
