from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.deployment.domain.entities import DeploymentStatus
from app.deployment.domain.events import DeploymentSucceeded, DeploymentFailed
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository
from app.deployment.infrastructure.websocket_manager import ws_manager
from app.sandbox.infrastructure.sqlalchemy_repository import SQLAlchemySandboxRepository
from app.sandbox.infrastructure.process_manager import SandboxProcessManager
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

    async def run(self, deployment_id: int, branch: str, is_rollback: bool = False) -> None:
        dep_id_str = str(deployment_id)
        full_log: list[str] = []

        try:
            await ws_manager.broadcast(dep_id_str, {"type": "status", "data": "BUILDING"})

            # ── Step 1: 브랜치 빌드 테스트 ──
            await self._stage(dep_id_str, "BUILD_VALIDATION", "started")
            await self._log(dep_id_str, full_log, "[PIPELINE] 브랜치 빌드 검증 시작...")
            build_ok = await self._run_branch_build(dep_id_str, full_log, branch)

            if not build_ok:
                await self._stage(dep_id_str, "BUILD_VALIDATION", "failed")
                await self._handle_failure(deployment_id, dep_id_str, full_log, exit_code=1)
                return
            await self._stage(dep_id_str, "BUILD_VALIDATION", "completed")

            # ── Step 2: main 머지 (원복 배포 시 스킵) ──
            await self._stage(dep_id_str, "MERGE", "started")
            merge_sha = None
            if is_rollback:
                await self._log(dep_id_str, full_log, "[PIPELINE] 원복 배포 — 머지 스킵 (이미 revert 완료)")
            elif self._git:
                await self._log(dep_id_str, full_log, "[PIPELINE] main 브랜치에 머지 중...")
                try:
                    merge_sha = self._git.merge_to_main(branch)
                    await self._log(dep_id_str, full_log, f"[PIPELINE] 머지 완료: {merge_sha[:8]}")
                except Exception as e:
                    await self._log(dep_id_str, full_log, f"[ERROR] 머지 실패: {e}", "stderr")
                    await self._stage(dep_id_str, "MERGE", "failed")
                    await self._handle_failure(deployment_id, dep_id_str, full_log, exit_code=2)
                    return
            await self._stage(dep_id_str, "MERGE", "completed")

            # ── Step 3: Docker 재빌드 & 재기동 ──
            await self._stage(dep_id_str, "DOCKER_RESTART", "started")
            deploy_ok = await self._run_docker_deploy(dep_id_str, full_log)

            if not deploy_ok:
                await self._stage(dep_id_str, "DOCKER_RESTART", "failed")
                await self._handle_failure(deployment_id, dep_id_str, full_log, exit_code=3)
                return
            await self._stage(dep_id_str, "DOCKER_RESTART", "completed")

            # ── 성공: 해당 브랜치 샌드박스 자동 정리 ──
            await self._cleanup_sandboxes(dep_id_str, full_log, branch)
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
        """브랜치 코드 검증"""
        target_path = settings.DEPLOY_TARGET_PATH

        if not target_path:
            await self._log(dep_id_str, full_log,
                            "[BUILD] DEPLOY_TARGET_PATH 미설정 - 시뮬레이션 빌드 실행")
            return await self._run_subprocess(
                dep_id_str, full_log,
                ["python3", "-c", self._simulation_build_script(branch)],
            )

        compose_file = f"{settings.DEPLOY_COMPOSE_PATH}/{settings.DEPLOY_COMPOSE_FILE}"
        services = settings.DEPLOY_SERVICE_NAME.split() if settings.DEPLOY_SERVICE_NAME else []
        deploy_mode = settings.DEPLOY_MODE

        if deploy_mode == "restart":
            await self._log(dep_id_str, full_log, "[BUILD] 폐쇄망 모드 - 소스 검증 중...")
            cmd = ["python3", "-c", self._syntax_check_script(settings.DEPLOY_COMPOSE_PATH)]
            return await self._run_subprocess(dep_id_str, full_log, cmd)
        else:
            cmd = ["docker", "compose", "-f", compose_file, "build"] + services
            await self._log(dep_id_str, full_log, f"[BUILD] 실행: {' '.join(cmd)}")
            return await self._run_subprocess(dep_id_str, full_log, cmd)

    async def _run_docker_deploy(self, dep_id_str: str, full_log: list[str]) -> bool:
        """Docker 재기동 (backend=restart, frontend=rebuild)"""
        target_path = settings.DEPLOY_TARGET_PATH

        if not target_path:
            await self._log(dep_id_str, full_log,
                            "[DEPLOY] DEPLOY_TARGET_PATH 미설정 - Docker 재기동 스킵")
            return True

        # Docker 빌드 전 main checkout 보장 (머지/원복 후 다른 브랜치에 남아있을 수 있음)
        checkout_proc = await asyncio.create_subprocess_exec(
            "git", "-C", settings.DEPLOY_COMPOSE_PATH, "checkout", "main",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await checkout_proc.communicate()

        compose_dir = settings.DEPLOY_COMPOSE_PATH
        host_compose = f"{compose_dir}/{settings.DEPLOY_COMPOSE_FILE}"
        compose_base = ["docker", "compose", "-f", host_compose, "-p", settings.DEPLOY_COMPOSE_PROJECT]
        services = settings.DEPLOY_SERVICE_NAME.split() if settings.DEPLOY_SERVICE_NAME else []
        deploy_mode = settings.DEPLOY_MODE

        if deploy_mode == "restart":
            # backend: 볼륨 마운트라 restart로 충분
            restart_svcs = [s for s in services if s != "frontend"]
            # frontend: 이미지 재빌드 필요
            rebuild_svcs = [s for s in services if s == "frontend"]

            if restart_svcs:
                cmd = compose_base + ["restart"] + restart_svcs
                await self._log(dep_id_str, full_log, f"[DEPLOY] backend 재기동: {' '.join(cmd)}")
                if not await self._run_subprocess(dep_id_str, full_log, cmd):
                    return False

            if rebuild_svcs:
                cmd = compose_base + ["build", "--no-cache"] + rebuild_svcs
                await self._log(dep_id_str, full_log, f"[DEPLOY] frontend 이미지 빌드: {' '.join(cmd)}")
                if not await self._run_subprocess(dep_id_str, full_log, cmd):
                    return False
                cmd = compose_base + ["up", "-d", "--no-deps"] + rebuild_svcs
                await self._log(dep_id_str, full_log, f"[DEPLOY] frontend 재빌드: {' '.join(cmd)}")
                if not await self._run_subprocess(dep_id_str, full_log, cmd):
                    return False

            return True
        else:
            cmd = compose_base + ["up", "-d", "--build", "--remove-orphans"] + services
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
                stderr=asyncio.subprocess.STDOUT,
            )

            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    break
                for line in chunk.decode(errors="replace").splitlines():
                    line = line.rstrip()
                    if line:
                        full_log.append(line)
                        await ws_manager.broadcast(dep_id_str, {
                            "type": "log_line", "data": line, "stream": "stdout",
                        })

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
        rca_dict: dict | None = None
        try:
            rca = await self._llm.analyze_failure(log_text)
            rca_dict = {
                "root_cause": rca.root_cause,
                "affected_files": rca.affected_files,
                "suggested_fix": rca.suggested_fix,
                "confidence_score": rca.confidence_score,
                "ai_fix_prompt": rca.ai_fix_prompt,
            }
            await ws_manager.broadcast(dep_id_str, {"type": "rca", "data": rca_dict})
        except Exception:
            logger.warning("RCA 분석 실패 (deployment %s)", deployment_id, exc_info=True)
        await self._event_bus.publish(DeploymentFailed(
            deployment_id=deployment_id,
            branch=dep.branch if dep else "",
            commit_sha=dep.commit_sha if dep else None,
            exit_code=exit_code,
            rca_report=rca_dict,
        ))

    async def _cleanup_sandboxes(self, dep_id_str: str, full_log: list[str], branch: str) -> None:
        """배포 성공 시 해당 브랜치의 샌드박스 자동 삭제"""
        try:
            async with self._session_factory() as db:
                repo = SQLAlchemySandboxRepository(db)
                sandboxes = await repo.find_all()
                targets = [s for s in sandboxes if s.branch == branch]
                for s in targets:
                    if s.project_name:
                        await SandboxProcessManager.destroy(s.project_name)
                    await repo.delete(s.id)
                    await self._log(dep_id_str, full_log,
                                    f"[PIPELINE] 샌드박스 자동 삭제: {s.branch} (ID: {s.id})")
        except Exception:
            logger.warning("샌드박스 자동 정리 실패: %s", branch, exc_info=True)

    async def _stage(self, dep_id_str: str, stage: str, status: str) -> None:
        await ws_manager.broadcast(dep_id_str, {
            "type": "stage", "stage": stage, "status": status,
        })

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

    @staticmethod
    def _syntax_check_script(target_path: str) -> str:
        return f"""
import sys, os, py_compile

src_dir = os.path.join("{target_path}", "backend")
errors = []
checked = 0

for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            checked += 1
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(str(e))

print(f"[BUILD] Python 구문 검사: {{checked}}개 파일 검사")
if errors:
    for e in errors:
        print(f"[ERROR] {{e}}", file=sys.stderr)
    print(f"[BUILD] {{len(errors)}}개 구문 오류 발견", file=sys.stderr)
    sys.exit(1)
else:
    print("[BUILD] 구문 오류 없음")
    print("[BUILD] Build successful!")
"""
