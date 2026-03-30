from __future__ import annotations

from app.analysis.domain.ports import LLMPort
from app.analysis.application.dtos import ImpactAnalysisResponseDTO, RCAResponseDTO
from app.git.domain.repositories import GitRepositoryPort


class AnalyzeImpact:
    def __init__(self, llm: LLMPort, git_repo: GitRepositoryPort) -> None:
        self._llm = llm
        self._git = git_repo

    async def execute(
        self, branch: str, file_paths: list[str] | None = None
    ) -> ImpactAnalysisResponseDTO:
        diff_text = self._git.get_full_diff(branch)
        if not file_paths:
            changes = self._git.get_changed_files(branch)
            file_paths = [c.path for c in changes]

        report = await self._llm.analyze_impact(diff_text, file_paths)
        return ImpactAnalysisResponseDTO(
            risk_level=report.risk_level.value,
            summary=report.summary,
            affected_services=report.affected_services,
            recommendations=report.recommendations,
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
