from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SandboxStatus(str, Enum):
    CREATING = "CREATING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class Sandbox:
    branch: str
    backend_port: int
    frontend_port: int
    status: SandboxStatus = SandboxStatus.CREATING
    worktree_path: str | None = None
    project_name: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None

    def mark_running(self) -> None:
        self.status = SandboxStatus.RUNNING

    def mark_stopped(self) -> None:
        self.status = SandboxStatus.STOPPED

    def mark_error(self) -> None:
        self.status = SandboxStatus.ERROR
