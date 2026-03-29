from __future__ import annotations

from app.shared.domain.exceptions import DomainException


class ChainIntegrityViolation(DomainException):
    def __init__(self) -> None:
        super().__init__("Audit hash-chain integrity violation detected", "INTEGRITY_ERROR")
