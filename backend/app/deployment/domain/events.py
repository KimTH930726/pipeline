from __future__ import annotations

from dataclasses import dataclass
from app.shared.domain.events import DomainEvent


@dataclass
class DeploymentStarted(DomainEvent):
    deployment_id: int = 0
    branch: str = ""
    commit_sha: str | None = None
    acted_by: str | None = None


@dataclass
class DeploymentSucceeded(DomainEvent):
    deployment_id: int = 0
    branch: str = ""
    commit_sha: str | None = None
    acted_by: str | None = None


@dataclass
class DeploymentFailed(DomainEvent):
    deployment_id: int = 0
    branch: str = ""
    commit_sha: str | None = None
    acted_by: str | None = None
    exit_code: int = 1
    rca_report: dict | None = None
