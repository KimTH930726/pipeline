from __future__ import annotations

import asyncio

from app.rollback.domain.events import RollbackExecuted
from app.rollback.domain.exceptions import NoStableCommitFound
from app.rollback.application.dtos import RollbackResultDTO
from app.deployment.domain.entities import Deployment, DeploymentStatus
from app.deployment.domain.repositories import DeploymentRepositoryPort
from app.deployment.infrastructure.build_runner import BuildProcessRunner
from app.git.domain.repositories import GitRepositoryPort
from app.shared.infrastructure.event_bus import InMemoryEventBus


class ExecuteRollback:
    def __init__(
        self,
        git_repo: GitRepositoryPort,
        deploy_repo: DeploymentRepositoryPort,
        build_runner: BuildProcessRunner,
        event_bus: InMemoryEventBus,
    ) -> None:
        self._git = git_repo
        self._deploy_repo = deploy_repo
        self._runner = build_runner
        self._event_bus = event_bus

    async def execute(self, branch: str, target_sha: str | None = None) -> RollbackResultDTO:
        if target_sha is None:
            last_success = await self._deploy_repo.find_last_successful(branch)
            if last_success and last_success.commit_sha:
                target_sha = last_success.commit_sha
            else:
                target_sha = self._git.get_last_stable_sha(branch)

        if not target_sha:
            raise NoStableCommitFound(branch)

        new_sha = self._git.revert_to(branch, target_sha)

        # Create re-deploy
        deployment = Deployment(branch=branch, commit_sha=new_sha, status=DeploymentStatus.BUILDING)
        deployment = await self._deploy_repo.save(deployment)

        asyncio.create_task(self._runner.run(deployment.id, branch))

        await self._event_bus.publish(RollbackExecuted(
            branch=branch,
            target_sha=target_sha,
            new_commit_sha=new_sha,
            deployment_id=deployment.id,
        ))

        return RollbackResultDTO(
            status="ROLLBACK_INITIATED",
            reverted_to=target_sha,
            new_commit=new_sha,
            deployment_id=deployment.id,
        )
