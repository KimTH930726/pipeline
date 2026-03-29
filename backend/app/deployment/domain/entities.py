from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.shared.domain.exceptions import InvalidStateTransition


class DeploymentStatus(str, Enum):
    PENDING = "PENDING"
    BUILDING = "BUILDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


_VALID_TRANSITIONS: dict[DeploymentStatus, set[DeploymentStatus]] = {
    DeploymentStatus.PENDING: {DeploymentStatus.BUILDING},
    DeploymentStatus.BUILDING: {DeploymentStatus.SUCCESS, DeploymentStatus.FAILED},
}


@dataclass
class Deployment:
    branch: str
    commit_sha: str | None = None
    status: DeploymentStatus = DeploymentStatus.PENDING
    build_log: str | None = None
    error_log: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    id: int | None = None

    def transition_to(self, new_status: DeploymentStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransition("Deployment", self.status.value, new_status.value)
        self.status = new_status
        if new_status in (DeploymentStatus.SUCCESS, DeploymentStatus.FAILED):
            self.finished_at = datetime.utcnow()

    @property
    def is_terminal(self) -> bool:
        return self.status in (DeploymentStatus.SUCCESS, DeploymentStatus.FAILED)
