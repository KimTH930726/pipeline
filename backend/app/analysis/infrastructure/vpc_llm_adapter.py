from __future__ import annotations

import json

import httpx

from app.analysis.domain.entities import ImpactReport, RCAReport, RiskLevel
from app.analysis.domain.ports import LLMPort
from app.analysis.domain.exceptions import LLMConnectionError
from app.analysis.infrastructure.log_parser import extract_error_context


class VPCLLMAdapter(LLMPort):
    def __init__(self, endpoint: str, timeout: float = 30.0) -> None:
        self._endpoint = endpoint
        self._timeout = timeout

    async def analyze_impact(self, diff_text: str, file_list: list[str]) -> ImpactReport:
        prompt = (
            "다음 코드 변경사항의 영향도를 분석해주세요.\n\n"
            f"변경 파일: {json.dumps(file_list)}\n\nDiff:\n{diff_text[:3000]}\n\n"
            'JSON 형식으로 응답: {"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", '
            '"summary": "...", "affected_services": [...], "recommendations": [...]}'
        )
        data = json.loads(await self._call(prompt))
        return ImpactReport(
            risk_level=RiskLevel(data["risk_level"]),
            summary=data["summary"],
            affected_services=data["affected_services"],
            recommendations=data["recommendations"],
        )

    async def analyze_failure(self, build_log: str) -> RCAReport:
        error_ctx = extract_error_context(build_log)
        prompt = (
            "빌드 실패 로그를 분석하여 원인과 해결책을 제시해주세요.\n\n"
            f"에러 컨텍스트:\n{error_ctx}\n\n"
            'JSON 형식으로 응답: {"root_cause": "...", "affected_files": [...], '
            '"suggested_fix": "...", "confidence_score": 0.0~1.0}'
        )
        data = json.loads(await self._call(prompt))
        return RCAReport(**data)

    async def _call(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._endpoint,
                    json={"prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                return resp.json().get("response", "{}")
        except httpx.HTTPError as exc:
            raise LLMConnectionError(self._endpoint) from exc
