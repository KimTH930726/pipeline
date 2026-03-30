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


class CodeReviewCommentDTO(BaseModel):
    file_path: str
    line: int | None = None
    severity: str
    category: str
    message: str
    suggested_code: str = ""


class CodeReviewResponseDTO(BaseModel):
    summary: str
    comments: list[CodeReviewCommentDTO]
    overall_quality: str


class ConflictResolutionDTO(BaseModel):
    file_path: str
    original_content: str
    resolved_content: str
    explanation: str


class MergeConflictResponseDTO(BaseModel):
    has_conflicts: bool
    conflicting_files: list[str] = []
    resolutions: list[ConflictResolutionDTO] = []
    summary: str = ""


class ApplyResolutionRequestDTO(BaseModel):
    branch: str
    resolutions: dict[str, str]


class RCARequestDTO(BaseModel):
    deployment_id: int
    build_log: str | None = None


class RCAResponseDTO(BaseModel):
    root_cause: str
    affected_files: list[str]
    suggested_fix: str
    confidence_score: float
    ai_fix_prompt: str = ""
