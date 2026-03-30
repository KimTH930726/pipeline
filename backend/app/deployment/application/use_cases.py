from __future__ import annotations

import asyncio

from app.deployment.domain.entities import Deployment, DeploymentStatus
from app.deployment.domain.repositories import DeploymentRepositoryPort
from app.deployment.application.dtos import DeployStatusDTO, DeployDetailDTO
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

        messages = self._git.get_commit_messages(branch)
        deployment = Deployment(
            branch=branch,
            commit_sha=sha,
            status=DeploymentStatus.BUILDING,
            commit_messages="\n".join(messages) if messages else None,
        )
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
            rolled_back=d.rolled_back,
            commit_messages=d.commit_messages,
            started_at=d.started_at,
            finished_at=d.finished_at,
        )


class GetDeployment:
    def __init__(self, repo: DeploymentRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, deployment_id: int) -> DeployDetailDTO | None:
        dep = await self._repo.find_by_id(deployment_id)
        if not dep:
            return None
        return DeployDetailDTO(
            id=dep.id, branch=dep.branch, commit_sha=dep.commit_sha,
            status=dep.status.value, rolled_back=dep.rolled_back,
            commit_messages=dep.commit_messages,
            started_at=dep.started_at, finished_at=dep.finished_at,
            build_log=dep.build_log, error_log=dep.error_log,
        )


class MarkRolledBack:
    def __init__(self, repo: DeploymentRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, deployment_id: int) -> None:
        dep = await self._repo.find_by_id(deployment_id)
        if dep:
            dep.rolled_back = True
            await self._repo.update(dep)


class GetRecentDeployments:
    def __init__(self, repo: DeploymentRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str | None = None, page: int = 1, size: int = 10) -> tuple[list[DeployStatusDTO], int]:
        offset = (page - 1) * size
        total = await self._repo.count(branch)
        deps = await self._repo.find_recent(branch, limit=size, offset=offset)
        items = [
            DeployStatusDTO(
                id=d.id, branch=d.branch, commit_sha=d.commit_sha,
                status=d.status.value, rolled_back=d.rolled_back,
                commit_messages=d.commit_messages,
                started_at=d.started_at, finished_at=d.finished_at,
            )
            for d in deps
        ]
        return items, total
