from __future__ import annotations

from pydantic import BaseModel


class ImpactAnalysisRequestDTO(BaseModel):
    branch: str
    file_paths: list[str] | None = None


class ImpactAnalysisResponseDTO(BaseModel):
    risk_level: str
    summary: str
    affected_services: list[str]
    recommendations: list[str]


class RCARequestDTO(BaseModel):
    deployment_id: int
    build_log: str | None = None


class RCAResponseDTO(BaseModel):
    root_cause: str
    affected_files: list[str]
    suggested_fix: str
    confidence_score: float
