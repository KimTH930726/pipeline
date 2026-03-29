from __future__ import annotations

from app.shared.domain.exceptions import DomainException, EntityNotFound


class NoAvailablePorts(DomainException):
    def __init__(self) -> None:
        super().__init__("No available ports in configured range", "RESOURCE_EXHAUSTED")


class SandboxNotFound(EntityNotFound):
    def __init__(self, sandbox_id: int) -> None:
        super().__init__("Sandbox", str(sandbox_id))
