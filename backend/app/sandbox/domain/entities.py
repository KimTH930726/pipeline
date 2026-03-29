from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.shared.domain.exceptions import InvalidStateTransition


class SandboxStatus(str, Enum):
    CREATING = "CREATING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class Sandbox:
    branch: str
    port: int
    status: SandboxStatus = SandboxStatus.CREATING
    pid: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None

    def mark_running(self, pid: int) -> None:
        self.status = SandboxStatus.RUNNING
        self.pid = pid

    def mark_error(self) -> None:
        self.status = SandboxStatus.ERROR
