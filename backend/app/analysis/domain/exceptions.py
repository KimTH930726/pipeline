from __future__ import annotations

from app.shared.domain.exceptions import DomainException


class AnalysisUnavailable(DomainException):
    def __init__(self, reason: str = "Analysis service unavailable") -> None:
        super().__init__(reason, "SERVICE_UNAVAILABLE")


class LLMConnectionError(DomainException):
    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Cannot connect to LLM at {endpoint}", "INFRASTRUCTURE_ERROR")
