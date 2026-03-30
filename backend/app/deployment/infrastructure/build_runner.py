from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.deployment.domain.entities import Deployment, DeploymentStatus
from app.deployment.domain.events import DeploymentSucceeded, DeploymentFailed
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository
from app.deployment.infrastructure.websocket_manager import ws_manager
from app.analysis.domain.ports import LLMPort
from app.analysis.infrastructure.log_parser import extract_error_context
from app.git.domain.repositories import GitRepositoryPort
from app.shared.infrastructure.event_bus import InMemoryEventBus

logger = logging.getLogger(__name__)


class BuildProcessRunner:
    """Runs build → merge → docker rebuild pipeline."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        llm: LLMPort,
        event_bus: InMemoryEventBus,
        git_repo: GitRepositoryPort | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._llm = llm
        self._event_bus = event_bus
        self._git = git_repo

    async def run(self, deployment_id: int, branch: str) -> None:
        dep_id_str = str(deployment_id)
        full_log: list[str] = []

        try:
            await ws_manager.broadcast(dep_id_str, {"type": "status", "data": "BUILDING"})

            # ── Step 1: 브랜치 빌드 테스트 ──
            await self._log(dep_id_str, full_log, "[PIPELINE] 브랜치 빌드 검증 시작...")
            build_ok = await self._run_branch_build(dep_id_str, full_log, branch)

            if not build_ok:
                await self._handle_failure(deployment_id, dep_id_str, full_log, exit_code=1)
                return

            # ── Step 2: main 머지 ──
            await self._log(dep_id_str, full_log, "[PIPELINE] main 브랜치에 머지 중...")
            merge_sha = None
            if self._git:
                try:
                    merge_sha = self._git.merge_to_main(branch)
                    await self._log(dep_id_str, full_log, f"[PIPELINE] 머지 완료: {merge_sha[:8]}")
                except Exception as e:
                    await self._log(dep_id_str, full_log, f"[ERROR] 머지 실패: {e}", "stderr")
                    await self._handle_failure(deployment_id, dep_id_str, full_log, exit_code=2)
                    return

            # ── Step 3: Docker 재빌드 & 재기동 ──
            deploy_ok = await self._run_docker_deploy(dep_id_str, full_log)

            if not deploy_ok:
                await self._handle_failure(deployment_id, dep_id_str, full_log, exit_code=3)
                return

            # ── 성공 ──
            await self._log(dep_id_str, full_log, "[PIPELINE] 배포 파이프라인 완료!")
            log_text = "\n".join(full_log)

            async with self._session_factory() as db:
                repo = SQLAlchemyDeploymentRepository(db)
                dep = await repo.find_by_id(deployment_id)
                if not dep:
                    return
                dep.transition_to(DeploymentStatus.SUCCESS)
                dep.build_log = log_text
                if merge_sha:
                    dep.commit_sha = merge_sha
                await repo.update(dep)

            await ws_manager.broadcast(dep_id_str, {"type": "status", "data": "SUCCESS"})
            await self._event_bus.publish(DeploymentSucceeded(
                deployment_id=deployment_id,
                branch=branch,
                commit_sha=merge_sha,
            ))

        except Exception as exc:
            logger.exception("Build runner error for deployment %s", deployment_id)
            async with self._session_factory() as db:
                repo = SQLAlchemyDeploymentRepository(db)
                dep = await repo.find_by_id(deployment_id)
                if dep and not dep.is_terminal:
                    dep.transition_to(DeploymentStatus.FAILED)
                    dep.error_log = str(exc)
                    await repo.update(dep)
            await ws_manager.broadcast(dep_id_str, {
                "type": "status", "data": "FAILED", "error": str(exc),
            })

    async def _run_branch_build(self, dep_id_str: str, full_log: list[str], branch: str) -> bool:
        """브랜치의 코드를 검증 빌드 (docker compose build --dry-run 또는 syntax check)"""
        target_path = settings.DEPLOY_TARGET_PATH

        if not target_path:
            # DEPLOY_TARGET_PATH 미설정 시 시뮬레이션 빌드
            await self._log(dep_id_str, full_log,
                            "[BUILD] DEPLOY_TARGET_PATH 미설정 - 시뮬레이션 빌드 실행")
            return await self._run_subprocess(
                dep_id_str, full_log,
                ["python3", "-c", self._simulation_build_script(branch)],
            )

        # 실제 빌드: 대상 경로에서 docker compose build
        compose_file = settings.DEPLOY_COMPOSE_FILE
        service = settings.DEPLOY_SERVICE_NAME
        cmd = ["docker", "compose", "-f", f"{target_path}/{compose_file}", "build"]
        if service:
            cmd.append(service)
        await self._log(dep_id_str, full_log, f"[BUILD] 실행: {' '.join(cmd)}")
        return await self._run_subprocess(dep_id_str, full_log, cmd)

    async def _run_docker_deploy(self, dep_id_str: str, full_log: list[str]) -> bool:
        """Docker 재빌드 및 무중단 재기동"""
        target_path = settings.DEPLOY_TARGET_PATH

        if not target_path:
            await self._log(dep_id_str, full_log,
                            "[DEPLOY] DEPLOY_TARGET_PATH 미설정 - Docker 재기동 스킵")
            return True

        compose_file = settings.DEPLOY_COMPOSE_FILE
        service = settings.DEPLOY_SERVICE_NAME

        # docker compose up -d --build (무중단: 새 컨테이너 준비 후 교체)
        cmd = ["docker", "compose", "-f", f"{target_path}/{compose_file}",
               "up", "-d", "--build", "--remove-orphans"]
        if service:
            cmd.append(service)
        await self._log(dep_id_str, full_log, f"[DEPLOY] 실행: {' '.join(cmd)}")
        return await self._run_subprocess(dep_id_str, full_log, cmd)

    async def _run_subprocess(
        self, dep_id_str: str, full_log: list[str], cmd: list[str],
    ) -> bool:
        """서브프로세스 실행, stdout/stderr 실시간 스트리밍. 성공 시 True 반환."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def _stream(stream, name: str) -> None:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode().rstrip()
                    full_log.append(text)
                    await ws_manager.broadcast(dep_id_str, {
                        "type": "log_line", "data": text, "stream": name,
                    })

            await asyncio.gather(
                _stream(process.stdout, "stdout"),
                _stream(process.stderr, "stderr"),
            )
            exit_code = await process.wait()
            return exit_code == 0
        except FileNotFoundError as e:
            await self._log(dep_id_str, full_log, f"[ERROR] 명령어를 찾을 수 없음: {e}", "stderr")
            return False

    async def _handle_failure(
        self, deployment_id: int, dep_id_str: str, full_log: list[str], exit_code: int,
    ) -> None:
        log_text = "\n".join(full_log)

        async with self._session_factory() as db:
            repo = SQLAlchemyDeploymentRepository(db)
            dep = await repo.find_by_id(deployment_id)
            if not dep:
                return
            dep.transition_to(DeploymentStatus.FAILED)
            dep.build_log = log_text
            dep.error_log = extract_error_context(log_text)
            await repo.update(dep)

        await ws_manager.broadcast(dep_id_str, {
            "type": "status", "data": "FAILED", "exit_code": exit_code,
        })

        # RCA 분석
        rca = await self._llm.analyze_failure(log_text)
        rca_dict = {
            "root_cause": rca.root_cause,
            "affected_files": rca.affected_files,
            "suggested_fix": rca.suggested_fix,
            "confidence_score": rca.confidence_score,
        }
        await ws_manager.broadcast(dep_id_str, {"type": "rca", "data": rca_dict})
        await self._event_bus.publish(DeploymentFailed(
            deployment_id=deployment_id,
            branch=dep.branch if dep else "",
            commit_sha=dep.commit_sha if dep else None,
            exit_code=exit_code,
            rca_report=rca_dict,
        ))

    async def _log(self, dep_id_str: str, full_log: list[str], msg: str, stream: str = "stdout") -> None:
        full_log.append(msg)
        await ws_manager.broadcast(dep_id_str, {
            "type": "log_line", "data": msg, "stream": stream,
        })

    @staticmethod
    def _simulation_build_script(branch: str) -> str:
        return f"""
import time, sys
print("[BUILD] Starting build for branch: {branch}")
print("[BUILD] Installing dependencies...")
time.sleep(1)
print("[BUILD] Running linter...")
time.sleep(0.5)
print("[BUILD] Compiling...")
time.sleep(1)
print("[BUILD] Running tests...")
time.sleep(1)
print("[BUILD] Build successful!")
"""
