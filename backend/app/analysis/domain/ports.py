from __future__ import annotations

from abc import ABC, abstractmethod
from app.analysis.domain.entities import ImpactReport, RCAReport, CodeReviewReport, MergeConflictReport


class LLMPort(ABC):
    @abstractmethod
    async def analyze_impact(self, diff_text: str, file_list: list[str]) -> ImpactReport: ...

    @abstractmethod
    async def review_code(self, diff_text: str, file_list: list[str]) -> CodeReviewReport: ...

    @abstractmethod
    async def resolve_conflicts(self, conflicts: dict[str, str]) -> MergeConflictReport: ...

    @abstractmethod
    async def analyze_failure(self, build_log: str) -> RCAReport: ...
