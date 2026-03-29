from __future__ import annotations


class DomainException(Exception):
    """Base for all domain errors."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class EntityNotFound(DomainException):
    def __init__(self, entity: str, identifier: str | int):
        super().__init__(f"{entity} '{identifier}' not found", "NOT_FOUND")


class InvalidStateTransition(DomainException):
    def __init__(self, entity: str, from_state: str, to_state: str):
        super().__init__(
            f"Cannot transition {entity} from {from_state} to {to_state}",
            "INVALID_TRANSITION",
        )


class InfrastructureError(DomainException):
    def __init__(self, message: str):
        super().__init__(message, "INFRASTRUCTURE_ERROR")
