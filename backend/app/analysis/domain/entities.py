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
class CodeReviewComment:
    file_path: str
    line: int | None
    severity: str  # "critical" | "warning" | "info"
    category: str  # "bug" | "security" | "performance" | "style" | "suggestion"
    message: str
    suggested_code: str = ""


@dataclass(frozen=True)
class CodeReviewReport:
    summary: str
    comments: list[CodeReviewComment]
    overall_quality: str  # "good" | "needs_improvement" | "poor"


@dataclass(frozen=True)
class ConflictResolution:
    file_path: str
    original_content: str
    resolved_content: str
    explanation: str


@dataclass(frozen=True)
class MergeConflictReport:
    conflicting_files: list[str]
    resolutions: list[ConflictResolution]
    summary: str


@dataclass(frozen=True)
class RCAReport:
    root_cause: str
    affected_files: list[str]
    suggested_fix: str
    confidence_score: float
    ai_fix_prompt: str = ""
