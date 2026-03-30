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
            "빌드 실패 로그를 분석하여 원인, 해결책, 그리고 AI 코드 어시스턴트에게 "
            "수정을 요청할 수 있는 프롬프트를 함께 제시해주세요.\n\n"
            f"에러 컨텍스트:\n{error_ctx}\n\n"
            "JSON 형식으로 응답:\n"
            "{\n"
            '  "root_cause": "실패 원인 분석",\n'
            '  "affected_files": ["영향받은 파일 경로"],\n'
            '  "suggested_fix": "개발자를 위한 수정 가이드",\n'
            '  "confidence_score": 0.0~1.0,\n'
            '  "ai_fix_prompt": "AI 코드 어시스턴트(Cursor, Claude 등)에 붙여넣기할 수 있는 구체적인 수정 요청 프롬프트. 에러 내용, 파일 경로, 기대 동작을 포함해주세요."\n'
            "}"
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
