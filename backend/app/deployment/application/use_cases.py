from __future__ import annotations

import asyncio

from app.deployment.domain.entities import Deployment, DeploymentStatus
from app.deployment.domain.repositories import DeploymentRepositoryPort
from app.deployment.application.dtos import DeployStatusDTO
from app.deployment.infrastructure.build_runner import BuildProcessRunner
from app.git.domain.repositories import GitRepositoryPort


class TriggerDeploy:
    def __init__(
        self,
        repo: DeploymentRepositoryPort,
        git_repo: GitRepositoryPort,
        build_runner: BuildProcessRunner,
    ) -> None:
        self._repo = repo
        self._git = git_repo
        self._runner = build_runner

    async def execute(self, branch: str) -> DeployStatusDTO:
        try:
            sha = self._git.get_current_sha(branch)
        except Exception:
            sha = None

        deployment = Deployment(branch=branch, commit_sha=sha, status=DeploymentStatus.BUILDING)
        deployment = await self._repo.save(deployment)

        asyncio.create_task(self._runner.run(deployment.id, branch))

        return self._to_dto(deployment)

    @staticmethod
    def _to_dto(d: Deployment) -> DeployStatusDTO:
        return DeployStatusDTO(
            id=d.id,
            branch=d.branch,
            commit_sha=d.commit_sha,
            status=d.status.value,
            started_at=d.started_at,
            finished_at=d.finished_at,
        )


class GetDeployment:
    def __init__(self, repo: DeploymentRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, deployment_id: int) -> DeployStatusDTO | None:
        dep = await self._repo.find_by_id(deployment_id)
        if not dep:
            return None
        return DeployStatusDTO(
            id=dep.id, branch=dep.branch, commit_sha=dep.commit_sha,
            status=dep.status.value, started_at=dep.started_at, finished_at=dep.finished_at,
        )


class GetRecentDeployments:
    def __init__(self, repo: DeploymentRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str | None = None) -> list[DeployStatusDTO]:
        deps = await self._repo.find_recent(branch)
        return [
            DeployStatusDTO(
                id=d.id, branch=d.branch, commit_sha=d.commit_sha,
                status=d.status.value, started_at=d.started_at, finished_at=d.finished_at,
            )
            for d in deps
        ]
