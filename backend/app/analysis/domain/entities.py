from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ImpactReport:
    risk_level: RiskLevel
    summary: str
    affected_services: list[str]
    recommendations: list[str]


@dataclass(frozen=True)
class RCAReport:
    root_cause: str
    affected_files: list[str]
    suggested_fix: str
    confidence_score: float
