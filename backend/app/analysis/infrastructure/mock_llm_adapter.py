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
        ai_prompt = ""
        confidence = 0.85

        if "ModuleNotFoundError" in build_log or "ImportError" in build_log:
            match = re.search(r"No module named '(\S+)'", build_log)
            module = match.group(1) if match else "unknown"
            root_cause = f"모듈 '{module}'을(를) 찾을 수 없습니다. requirements.txt에 해당 패키지가 누락된 것으로 보입니다."
            affected = ["requirements.txt"]
            fix = f"`pip install {module}` 실행 후 requirements.txt에 추가하세요."
            ai_prompt = (
                f"빌드 중 ModuleNotFoundError가 발생했습니다. "
                f"'{module}' 모듈이 requirements.txt에 누락되어 있습니다.\n\n"
                f"다음을 수행해주세요:\n"
                f"1. requirements.txt에 '{module}' 패키지를 적절한 버전과 함께 추가\n"
                f"2. 해당 모듈을 import하는 코드에서 버전 호환성 확인\n"
                f"3. 의존성 충돌이 없는지 확인"
            )
            confidence = 0.95
        elif "SyntaxError" in build_log:
            match = re.search(r'File "([^"]+)", line (\d+)', build_log)
            file_path = match.group(1) if match else "unknown"
            line_num = match.group(2) if match else "unknown"
            if match:
                affected = [file_path]
                root_cause = f"{file_path}의 {line_num}번째 줄에 문법 오류가 있습니다."
                fix = f"{file_path}:{line_num} 위치의 문법을 확인하세요."
            ai_prompt = (
                f"{file_path} 파일의 {line_num}번째 줄 근처에서 SyntaxError가 발생했습니다.\n\n"
                f"다음을 수행해주세요:\n"
                f"1. {file_path}:{line_num} 위치의 문법 오류를 찾아 수정\n"
                f"2. 괄호, 콜론, 들여쓰기 등 Python 문법 규칙 확인\n"
                f"3. 수정 후 해당 파일의 전체 구문이 유효한지 검증"
            )
            confidence = 0.92
        elif "AssertionError" in build_log or "FAILED" in build_log:
            root_cause = "테스트 실패가 감지되었습니다. 최근 변경사항이 기존 테스트를 깨뜨린 것으로 보입니다."
            fix = "실패한 테스트 케이스를 확인하고, 변경된 로직에 맞게 테스트를 업데이트하세요."
            ai_prompt = (
                "빌드 중 테스트 실패(AssertionError/FAILED)가 발생했습니다.\n\n"
                "다음을 수행해주세요:\n"
                "1. 실패한 테스트 케이스를 식별하고 실패 원인 분석\n"
                "2. 최근 변경된 비즈니스 로직과 테스트의 기대값이 일치하는지 확인\n"
                "3. 테스트를 새로운 로직에 맞게 수정하되, 기존 기능이 깨지지 않도록 주의\n"
                "4. 수정 후 전체 테스트 스위트 실행하여 회귀 검증"
            )
            confidence = 0.80
        elif "ConnectionError" in build_log or "timeout" in build_log.lower():
            root_cause = "외부 서비스 연결 실패. 네트워크 또는 의존 서비스 상태를 확인하세요."
            fix = "외부 API 엔드포인트 상태와 네트워크 설정을 확인하세요."
            ai_prompt = (
                "빌드 중 외부 서비스 연결 실패(ConnectionError/Timeout)가 발생했습니다.\n\n"
                "다음을 수행해주세요:\n"
                "1. 외부 API 호출 부분에 적절한 타임아웃 설정과 재시도(retry) 로직 추가\n"
                "2. 연결 실패 시 fallback 처리 또는 graceful degradation 구현\n"
                "3. 테스트 환경에서 외부 서비스를 mock으로 대체할 수 있도록 구조 개선"
            )
            confidence = 0.70
        else:
            error_lines = [l for l in build_log.split("\n") if "error" in l.lower()]
            if error_lines:
                root_cause = f"빌드 로그에서 에러 감지: {error_lines[0][:200]}"
            fix = "빌드 로그의 에러 메시지를 확인하고 해당 코드를 수정하세요."
            error_summary = error_lines[0][:200] if error_lines else "알 수 없는 에러"
            ai_prompt = (
                f"빌드 중 다음 에러가 발생했습니다:\n{error_summary}\n\n"
                "다음을 수행해주세요:\n"
                "1. 에러 메시지를 분석하여 근본 원인 파악\n"
                "2. 관련 파일을 찾아 에러를 수정\n"
                "3. 수정 후 빌드가 정상적으로 통과하는지 확인"
            )
            confidence = 0.60

        return RCAReport(
            root_cause=root_cause,
            affected_files=affected,
            suggested_fix=fix,
            confidence_score=confidence,
            ai_fix_prompt=ai_prompt,
        )
