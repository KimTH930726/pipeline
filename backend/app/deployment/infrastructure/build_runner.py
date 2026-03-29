from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.deployment.domain.entities import Deployment, DeploymentStatus
from app.deployment.domain.events import DeploymentSucceeded, DeploymentFailed
from app.deployment.infrastructure.sqlalchemy_repository import SQLAlchemyDeploymentRepository
from app.deployment.infrastructure.websocket_manager import ws_manager
from app.analysis.domain.ports import LLMPort
from app.analysis.infrastructure.log_parser import extract_error_context
from app.shared.infrastructure.event_bus import InMemoryEventBus

logger = logging.getLogger(__name__)


class BuildProcessRunner:
    """Runs build process in background with its own DB session (no session leak)."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        llm: LLMPort,
        event_bus: InMemoryEventBus,
    ) -> None:
        self._session_factory = session_factory
        self._llm = llm
        self._event_bus = event_bus

    async def run(self, deployment_id: int, branch: str) -> None:
        dep_id_str = str(deployment_id)
        full_log: list[str] = []

        try:
            await ws_manager.broadcast(dep_id_str, {"type": "status", "data": "BUILDING"})

            process = await asyncio.create_subprocess_exec(
                "python3", "-c", self._build_script(branch),
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
            log_text = "\n".join(full_log)

            async with self._session_factory() as db:
                repo = SQLAlchemyDeploymentRepository(db)
                dep = await repo.find_by_id(deployment_id)
                if not dep:
                    return

                if exit_code == 0:
                    dep.transition_to(DeploymentStatus.SUCCESS)
                    dep.build_log = log_text
                    await repo.update(dep)
                    await ws_manager.broadcast(dep_id_str, {"type": "status", "data": "SUCCESS"})
                    await self._event_bus.publish(DeploymentSucceeded(
                        deployment_id=dep.id,
                        branch=dep.branch,
                        commit_sha=dep.commit_sha,
                    ))
                else:
                    dep.transition_to(DeploymentStatus.FAILED)
                    dep.build_log = log_text
                    dep.error_log = extract_error_context(log_text)
                    await repo.update(dep)
                    await ws_manager.broadcast(dep_id_str, {
                        "type": "status", "data": "FAILED", "exit_code": exit_code,
                    })

                    rca = await self._llm.analyze_failure(log_text)
                    rca_dict = {
                        "root_cause": rca.root_cause,
                        "affected_files": rca.affected_files,
                        "suggested_fix": rca.suggested_fix,
                        "confidence_score": rca.confidence_score,
                    }
                    await ws_manager.broadcast(dep_id_str, {"type": "rca", "data": rca_dict})
                    await self._event_bus.publish(DeploymentFailed(
                        deployment_id=dep.id,
                        branch=dep.branch,
                        commit_sha=dep.commit_sha,
                        exit_code=exit_code,
                        rca_report=rca_dict,
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

    @staticmethod
    def _build_script(branch: str) -> str:
        return f"""
import time, sys, random
print("[BUILD] Starting build for branch: {branch}")
print("[BUILD] Installing dependencies...")
time.sleep(1)
print("[BUILD] Running linter...")
time.sleep(0.5)
print("[BUILD] Compiling...")
time.sleep(1)
if random.random() < 0.3:
    print("[ERROR] ModuleNotFoundError: No module named 'missing_module'", file=sys.stderr)
    sys.exit(1)
print("[BUILD] Running tests...")
time.sleep(1)
if random.random() < 0.2:
    print("[ERROR] AssertionError: test_api_endpoint failed", file=sys.stderr)
    print("FAILED: 2 tests failed", file=sys.stderr)
    sys.exit(1)
print("[BUILD] Build successful!")
print("[BUILD] Deploying...")
time.sleep(0.5)
print("[BUILD] Deploy complete!")
"""
