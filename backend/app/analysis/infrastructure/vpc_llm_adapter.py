from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

import httpx

from app.analysis.domain.entities import (
    ImpactReport, RCAReport, RiskLevel,
    CodeReviewReport, CodeReviewComment,
    MergeConflictReport, ConflictResolution,
)
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
    # 시스템 단일 토큰 캐시 (client_credentials).
    # 인스턴스마다 새로 만들기보다 클래스 단위로 공유 — token 발급 호출 절감.
    _token_state: dict = {"token": None, "expires_at": 0.0}
    _token_lock: asyncio.Lock | None = None

    def __init__(self, user_identifier: str | None = None, timeout: float = 120.0) -> None:
        # user 필드는 dify에 등록된 ID여야 응답이 옴.
        # 우선순위: settings.LLM_USER_ID > 호출자 user_identifier > "system"
        from app.config import settings
        self._user = settings.LLM_USER_ID or user_identifier or "system"
        self._timeout = timeout
        self._auth_endpoint = settings.LLM_AUTH_ENDPOINT
        self._chat_endpoint = settings.LLM_CHAT_ENDPOINT
        self._client_id = settings.LLM_CLIENT_ID
        self._client_secret = settings.LLM_CLIENT_SECRET
        self._agent_code = settings.LLM_AGENT_CODE
        self._agent_id = settings.LLM_AGENT_ID
        self._conversation_id = settings.LLM_CONVERSATION_ID

    async def analyze_impact(self, diff_text: str, file_list: list[str]) -> ImpactReport:
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
        return self._parse_impact(data)

    async def review_code(self, diff_text: str, file_list: list[str]) -> CodeReviewReport:
        trimmed_diff = self._trim_diff(diff_text, max_chars=10000)
        file_summary = json.dumps(file_list, ensure_ascii=False)

        prompt = f"""## 작업
아래 코드 변경사항에 대해 시니어 개발자 관점에서 코드 리뷰를 수행해주세요.

## 변경 파일 ({len(file_list)}개)
{file_summary}

## Diff (main 브랜치 대비)
```diff
{trimmed_diff}
```

## 리뷰 기준
각 변경사항에 대해 다음 관점으로 리뷰해주세요:
- **bug**: 로직 오류, NPE 가능성, 경계값 미처리, 비동기 처리 누락
- **security**: SQL Injection, XSS, 하드코딩된 시크릿, 인증/인가 누락
- **performance**: N+1 쿼리, 불필요한 반복, 메모리 누수 가능성
- **style**: 네이밍 컨벤션, 불필요한 코드, 가독성
- **suggestion**: 더 나은 구현 방법, 리팩터링 제안

## severity 기준
- **critical**: 반드시 수정 필요 (버그, 보안 취약점)
- **warning**: 수정 권장 (잠재적 문제)
- **info**: 참고 사항 (개선 제안)

## 응답 형식 (JSON만 출력, 내용은 마크다운으로)
```json
{{
  "summary": "전체 리뷰 요약을 **마크다운**으로 작성",
  "comments": [
    {{
      "file_path": "파일 경로",
      "line": null,
      "severity": "critical|warning|info",
      "category": "bug|security|performance|style|suggestion",
      "message": "리뷰 내용을 **마크다운**으로 작성",
      "suggested_code": "수정 제안 코드 (없으면 빈 문자열)"
    }}
  ],
  "overall_quality": "good|needs_improvement|poor"
}}
```"""

        data = json.loads(await self._call(prompt))
        return CodeReviewReport(
            summary=data["summary"],
            comments=[
                CodeReviewComment(
                    file_path=c["file_path"], line=c.get("line"),
                    severity=c["severity"], category=c["category"],
                    message=c["message"], suggested_code=c.get("suggested_code", ""),
                )
                for c in data.get("comments", [])
            ],
            overall_quality=data.get("overall_quality", "needs_improvement"),
        )

    async def resolve_conflicts(self, conflicts: dict[str, str]) -> MergeConflictReport:
        conflict_details = "\n\n".join(
            f"### {fp}\n```\n{content[:3000]}\n```"
            for fp, content in conflicts.items()
        )

        prompt = f"""## 작업
Git 머지 충돌이 발생했습니다. 각 파일의 충돌을 분석하고 해결해주세요.

## 충돌 파일 ({len(conflicts)}개)
{conflict_details}

## 규칙
- `<<<<<<<`, `=======`, `>>>>>>>` 마커를 모두 제거하고 올바른 코드를 작성하세요
- 양쪽 변경사항의 **의도를 모두 보존**하세요
- 코드가 문법적으로 유효해야 합니다
- explanation은 **마크다운**으로 작성하세요

## 응답 형식 (JSON만 출력)
```json
{{
  "conflicting_files": ["파일 경로"],
  "resolutions": [
    {{
      "file_path": "파일 경로",
      "resolved_content": "충돌이 해결된 전체 파일 내용",
      "explanation": "해결 방법 설명 (마크다운)"
    }}
  ],
  "summary": "전체 해결 요약 (마크다운)"
}}
```"""

        data = json.loads(await self._call(prompt))
        return MergeConflictReport(
            conflicting_files=data["conflicting_files"],
            resolutions=[
                ConflictResolution(
                    file_path=r["file_path"],
                    original_content=conflicts.get(r["file_path"], ""),
                    resolved_content=r["resolved_content"],
                    explanation=r["explanation"],
                )
                for r in data.get("resolutions", [])
            ],
            summary=data["summary"],
        )

    @staticmethod
    def _parse_impact(data: dict) -> ImpactReport:
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

    # ─── 토큰 발급 + 캐싱 (시스템 단일 client_credentials) ──────────────
    @classmethod
    async def _get_access_token(
        cls,
        auth_endpoint: str,
        client_id: str,
        client_secret: str,
        timeout: float,
    ) -> str:
        if cls._token_lock is None:
            cls._token_lock = asyncio.Lock()

        async with cls._token_lock:
            now = time.time()
            state = cls._token_state
            # 만료 30초 전부터 갱신
            if state["token"] and state["expires_at"] > now + 30:
                return state["token"]

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        auth_endpoint,
                        data={
                            "grant_type": "client_credentials",
                            "client_id": client_id,
                            "client_secret": client_secret,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.HTTPError as exc:
                logger.error("LLM token 발급 실패: %s", exc)
                raise LLMConnectionError(auth_endpoint) from exc

            token = data.get("access_token")
            if not token:
                logger.error("LLM token 응답에 access_token 없음: %s", data)
                raise LLMConnectionError(auth_endpoint)

            # expires_in 없으면 1시간 기본
            state["token"] = token
            state["expires_at"] = now + int(data.get("expires_in", 3600))
            return token

    # ─── SSE 호출 → 응답 모아서 JSON 추출 ──────────────────────────────
    async def _call(self, prompt: str) -> str:
        if not self._client_id or not self._client_secret:
            logger.error("LLM_CLIENT_ID/LLM_CLIENT_SECRET 미설정")
            raise LLMConnectionError(self._auth_endpoint)

        token = await self._get_access_token(
            self._auth_endpoint, self._client_id, self._client_secret, self._timeout,
        )

        query = f"{SYSTEM_PROMPT}\n\n{prompt}"
        # dify는 사전 등록된 conversation_id만 응답. 미설정 시 새 UUID 시도(빈 응답 가능).
        conversation_id = self._conversation_id or str(uuid.uuid4())
        payload = {
            "user": self._user,
            "query": query,
            "agent_id": self._agent_id,
            "agent_code": self._agent_code,
            "conversation_id": conversation_id,
            "knowledge_ids": [],
            "response_mode": "streaming",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }

        try:
            answer_parts: list[str] = []
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST", self._chat_endpoint, json=payload, headers=headers,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        chunk = self._parse_sse_line(line)
                        if chunk is None:
                            continue
                        # 가능한 응답 필드: answer(점진적) / delta.content / message
                        if isinstance(chunk, dict):
                            piece = (
                                chunk.get("answer")
                                or chunk.get("delta", {}).get("content")
                                or chunk.get("message")
                                or ""
                            )
                            if piece:
                                answer_parts.append(piece)
        except httpx.HTTPError as exc:
            logger.error("LLM HTTP error: %s", exc)
            raise LLMConnectionError(self._chat_endpoint) from exc

        raw = "".join(answer_parts).strip()
        if not raw:
            logger.error("LLM SSE 응답 비어있음")
            raise LLMConnectionError(self._chat_endpoint)
        return self._extract_json(raw)

    @staticmethod
    def _parse_sse_line(line: str) -> dict | None:
        """SSE 한 줄을 파싱. data: <json> 형태만 처리, 종료/주석/빈줄은 None."""
        if not line or not line.startswith("data: "):
            return None
        payload = line[6:].strip()
        if not payload or payload == "[DONE]":
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_json(raw: str) -> str:
        """LLM 응답에서 JSON 부분만 추출 (마크다운 코드블록 처리)"""
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
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
