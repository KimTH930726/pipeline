from __future__ import annotations

from app.shared.domain.exceptions import EntityNotFound


class DeploymentNotFound(EntityNotFound):
    def __init__(self, deployment_id: int) -> None:
        super().__init__("Deployment", str(deployment_id))
