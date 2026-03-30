from __future__ import annotations

from app.analysis.domain.ports import LLMPort
from app.analysis.application.dtos import ImpactAnalysisResponseDTO, CodeReviewResponseDTO, CodeReviewCommentDTO, RCAResponseDTO
from app.git.domain.repositories import GitRepositoryPort


def _get_diff_and_files(
    git_repo: GitRepositoryPort, branch: str, file_paths: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Extract diff text and file list from branch (shared by impact + review)."""
    diff_text = git_repo.get_full_diff(branch)
    if not file_paths:
        changes = git_repo.get_changed_files(branch)
        file_paths = [c.path for c in changes]
    return diff_text, file_paths


class AnalyzeImpact:
    def __init__(self, llm: LLMPort, git_repo: GitRepositoryPort) -> None:
        self._llm = llm
        self._git = git_repo

    async def execute(
        self, branch: str, file_paths: list[str] | None = None
    ) -> ImpactAnalysisResponseDTO:
        diff_text, file_paths = _get_diff_and_files(self._git, branch, file_paths)
        report = await self._llm.analyze_impact(diff_text, file_paths)
        return ImpactAnalysisResponseDTO(
            risk_level=report.risk_level.value,
            summary=report.summary,
            affected_services=report.affected_services,
            recommendations=report.recommendations,
        )


class ReviewCode:
    def __init__(self, llm: LLMPort, git_repo: GitRepositoryPort) -> None:
        self._llm = llm
        self._git = git_repo

    async def execute(
        self, branch: str, file_paths: list[str] | None = None
    ) -> CodeReviewResponseDTO:
        diff_text, file_paths = _get_diff_and_files(self._git, branch, file_paths)
        report = await self._llm.review_code(diff_text, file_paths)
        return CodeReviewResponseDTO(
            summary=report.summary,
            comments=[
                CodeReviewCommentDTO(
                    file_path=c.file_path, line=c.line, severity=c.severity,
                    category=c.category, message=c.message, suggested_code=c.suggested_code,
                )
                for c in report.comments
            ],
            overall_quality=report.overall_quality,
        )


class AnalyzeFailure:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def execute(self, build_log: str) -> RCAResponseDTO:
        report = await self._llm.analyze_failure(build_log)
        return RCAResponseDTO(
            root_cause=report.root_cause,
            affected_files=report.affected_files,
            suggested_fix=report.suggested_fix,
            confidence_score=report.confidence_score,
            ai_fix_prompt=report.ai_fix_prompt,
        )
