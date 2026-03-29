from __future__ import annotations

from abc import ABC, abstractmethod
from app.analysis.domain.entities import ImpactReport, RCAReport


class LLMPort(ABC):
    @abstractmethod
    async def analyze_impact(self, diff_text: str, file_list: list[str]) -> ImpactReport: ...

    @abstractmethod
    async def analyze_failure(self, build_log: str) -> RCAReport: ...
