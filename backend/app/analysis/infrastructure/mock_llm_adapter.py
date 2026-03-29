from __future__ import annotations

import re

from app.analysis.domain.entities import ImpactReport, RCAReport, RiskLevel
from app.analysis.domain.ports import LLMPort


class MockLLMAdapter(LLMPort):
    async def analyze_impact(self, diff_text: str, file_list: list[str]) -> ImpactReport:
        count = len(file_list)
        risk = RiskLevel.HIGH if count > 10 else RiskLevel.MEDIUM if count > 5 else RiskLevel.LOW

        services: set[str] = set()
        for f in file_list:
            if "api" in f or "router" in f:
                services.add("API Layer")
            if "model" in f or "database" in f:
                services.add("Database")
            if "service" in f:
                services.add("Business Logic")
            if "test" in f:
                services.add("Test Suite")
        if not services:
            services.add("General")

        return ImpactReport(
            risk_level=risk,
            summary=f"{count}개 파일 변경 감지. {', '.join(services)} 영역에 영향.",
            affected_services=sorted(services),
            recommendations=[
                "변경된 모듈의 단위 테스트 실행 권장",
                "의존성 그래프 확인 필요" if count > 5 else "영향 범위 제한적",
                "스테이징 환경 테스트 후 배포 권장" if risk != RiskLevel.LOW else "샌드박스 테스트 후 배포 가능",
            ],
        )

    async def analyze_failure(self, build_log: str) -> RCAReport:
        root_cause = "빌드 실패 원인 분석 결과"
        affected: list[str] = []
        fix = "해당 파일을 확인하고 수정하세요."
        confidence = 0.85

        if "ModuleNotFoundError" in build_log or "ImportError" in build_log:
            match = re.search(r"No module named '(\S+)'", build_log)
            module = match.group(1) if match else "unknown"
            root_cause = f"모듈 '{module}'을(를) 찾을 수 없습니다. requirements.txt에 해당 패키지가 누락된 것으로 보입니다."
            affected = ["requirements.txt"]
            fix = f"`pip install {module}` 실행 후 requirements.txt에 추가하세요."
            confidence = 0.95
        elif "SyntaxError" in build_log:
            match = re.search(r'File "([^"]+)", line (\d+)', build_log)
            if match:
                affected = [match.group(1)]
                root_cause = f"{match.group(1)}의 {match.group(2)}번째 줄에 문법 오류가 있습니다."
                fix = f"{match.group(1)}:{match.group(2)} 위치의 문법을 확인하세요."
            confidence = 0.92
        elif "AssertionError" in build_log or "FAILED" in build_log:
            root_cause = "테스트 실패가 감지되었습니다. 최근 변경사항이 기존 테스트를 깨뜨린 것으로 보입니다."
            fix = "실패한 테스트 케이스를 확인하고, 변경된 로직에 맞게 테스트를 업데이트하세요."
            confidence = 0.80
        elif "ConnectionError" in build_log or "timeout" in build_log.lower():
            root_cause = "외부 서비스 연결 실패. 네트워크 또는 의존 서비스 상태를 확인하세요."
            fix = "외부 API 엔드포인트 상태와 네트워크 설정을 확인하세요."
            confidence = 0.70
        else:
            error_lines = [l for l in build_log.split("\n") if "error" in l.lower()]
            if error_lines:
                root_cause = f"빌드 로그에서 에러 감지: {error_lines[0][:200]}"
            fix = "빌드 로그의 에러 메시지를 확인하고 해당 코드를 수정하세요."
            confidence = 0.60

        return RCAReport(
            root_cause=root_cause,
            affected_files=affected,
            suggested_fix=fix,
            confidence_score=confidence,
        )
