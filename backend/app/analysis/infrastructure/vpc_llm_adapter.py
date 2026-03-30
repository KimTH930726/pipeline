from __future__ import annotations

import json
import logging

import httpx

from app.analysis.domain.entities import ImpactReport, RCAReport, RiskLevel
from app.analysis.domain.ports import LLMPort
from app.analysis.domain.exceptions import LLMConnectionError
from app.analysis.infrastructure.log_parser import extract_error_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 시니어 DevOps 엔지니어이자 코드 리뷰 전문가입니다.
Python/FastAPI 기반 프로젝트의 배포 파이프라인에서 코드 변경 영향도 분석과 빌드 실패 원인 분석을 담당합니다.

규칙:
- 반드시 유효한 JSON만 응답하세요. 마크다운이나 설명 텍스트를 JSON 밖에 포함하지 마세요.
- 한국어로 응답하세요.
- 구체적이고 실행 가능한 조언을 제공하세요."""


class VPCLLMAdapter(LLMPort):
    def __init__(self, endpoint: str, timeout: float = 60.0) -> None:
        self._endpoint = endpoint
        self._timeout = timeout

    async def analyze_impact(self, diff_text: str, file_list: list[str]) -> ImpactReport:
        # diff가 너무 길면 핵심 변경사항만 추출
        trimmed_diff = self._trim_diff(diff_text, max_chars=8000)
        file_summary = json.dumps(file_list, ensure_ascii=False)

        prompt = f"""## 작업
아래 코드 변경사항의 배포 영향도를 분석해주세요.

## 변경 파일 ({len(file_list)}개)
{file_summary}

## Diff (main 브랜치 대비)
```diff
{trimmed_diff}
```

## 분석 기준
- **risk_level**: 변경 범위, 핵심 로직 수정 여부, 외부 의존성 변경 여부를 종합 판단
  - LOW: 문서, 설정, 테스트만 변경
  - MEDIUM: 비즈니스 로직 일부 변경, 기존 인터페이스 유지
  - HIGH: API 인터페이스 변경, DB 스키마 수정, 다수 모듈 영향
  - CRITICAL: 인증/보안 관련 변경, 데이터 마이그레이션 필요
- **affected_services**: 변경이 영향을 주는 시스템 영역 (예: "API Layer", "Database", "Authentication", "Frontend UI")
- **recommendations**: 배포 전 반드시 확인해야 할 사항 (구체적인 테스트 케이스, 확인 포인트)

## 응답 형식 (JSON만 출력)
- summary, recommendations 항목은 **Markdown 형식**으로 작성하세요 (볼드, 리스트, 코드블록 등 활용)
```json
{{
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "## 변경 요약\\n변경 내용을 **마크다운**으로 구조화하여 작성",
  "affected_services": ["영향받는 서비스/레이어"],
  "recommendations": ["**확인 필요**: 구체적인 내용을 마크다운으로 작성"]
}}
```"""

        data = json.loads(await self._call(prompt))
        return ImpactReport(
            risk_level=RiskLevel(data["risk_level"]),
            summary=data["summary"],
            affected_services=data["affected_services"],
            recommendations=data["recommendations"],
        )

    async def analyze_failure(self, build_log: str) -> RCAReport:
        error_ctx = extract_error_context(build_log)

        prompt = f"""## 작업
빌드 실패 로그를 분석하여 근본 원인, 해결 방법, 그리고 AI 코드 어시스턴트에게 전달할 수정 프롬프트를 작성해주세요.

## 빌드 로그 (에러 컨텍스트)
```
{error_ctx}
```

## 분석 요구사항
1. **root_cause**: 실패의 직접적인 원인을 1-2문장으로 명확하게 설명
2. **affected_files**: 수정이 필요한 파일 경로 목록 (빌드 로그에서 추출)
3. **suggested_fix**: 개발자가 수동으로 수정할 때의 단계별 가이드
4. **confidence_score**: 분석 정확도 (0.0~1.0)
   - 에러 메시지가 명확하면 0.9 이상
   - 간접 추론이면 0.6~0.8
5. **ai_fix_prompt**: AI 코드 어시스턴트(Cursor, Claude Code 등)에 **그대로 복사-붙여넣기**하면 수정이 진행되는 프롬프트.
   아래 내용을 반드시 포함:
   - 현재 에러 상황 설명
   - 수정 대상 파일 경로
   - 기대하는 수정 결과
   - 수정 시 주의사항

## 응답 형식 (JSON만 출력)
- root_cause, suggested_fix, ai_fix_prompt 항목은 **Markdown 형식**으로 작성하세요 (볼드, 리스트, 코드블록 등 활용)
```json
{{
  "root_cause": "## 실패 원인\\n원인을 **마크다운**으로 구조화",
  "affected_files": ["파일 경로"],
  "suggested_fix": "## 수정 가이드\\n1. 첫 번째 단계\\n2. 두 번째 단계\\n```python\\n코드 예시\\n```",
  "confidence_score": 0.0,
  "ai_fix_prompt": "마크다운 형식의 AI 수정 요청 프롬프트"
}}
```"""

        data = json.loads(await self._call(prompt))
        return RCAReport(**data)

    async def _call(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._endpoint,
                    json={
                        "prompt": prompt,
                        "system": SYSTEM_PROMPT,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                raw = resp.json().get("response", "{}")

                # JSON 블록 추출 (마크다운 코드블록 안에 있을 수 있음)
                return self._extract_json(raw)
        except json.JSONDecodeError as exc:
            logger.error("LLM response JSON parse error: %s", exc)
            raise LLMConnectionError(self._endpoint) from exc
        except httpx.HTTPError as exc:
            raise LLMConnectionError(self._endpoint) from exc

    @staticmethod
    def _extract_json(raw: str) -> str:
        """LLM 응답에서 JSON 부분만 추출 (마크다운 코드블록 처리)"""
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            # 첫 줄(```json)과 마지막 줄(```) 제거
            json_lines = []
            inside = False
            for line in lines:
                if line.strip().startswith("```") and not inside:
                    inside = True
                    continue
                if line.strip() == "```" and inside:
                    break
                if inside:
                    json_lines.append(line)
            return "\n".join(json_lines)
        return raw

    @staticmethod
    def _trim_diff(diff_text: str, max_chars: int = 8000) -> str:
        """diff가 너무 길면 핵심부만 남김"""
        if len(diff_text) <= max_chars:
            return diff_text

        lines = diff_text.split("\n")
        result = []
        current_len = 0
        for line in lines:
            if current_len + len(line) > max_chars:
                result.append(f"\n... (이하 {len(lines) - len(result)}줄 생략)")
                break
            result.append(line)
            current_len += len(line) + 1
        return "\n".join(result)
