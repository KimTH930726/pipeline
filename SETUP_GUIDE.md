# 팀원 개발 환경 세팅 가이드

> 포탈의 **시작 가이드** 탭에서도 동일한 내용을 복사 버튼과 함께 볼 수 있습니다.

## 1. 회원가입
1. `http://서버IP:3000/signup` 접속
2. 아이디, 비밀번호, LLM API Key 입력
3. 관리자 승인 대기 → 승인 후 로그인 가능

## 2. 프로젝트 클론 (최초 1회)
```bash
git clone ssh://user@서버IP/srv/repos/SMAgentLab.git
cd SMAgentLab
code .
```

## 3. 개발 흐름
```bash
# 포탈에서 브랜치 생성 후
git fetch
git checkout feature/내브랜치

# 코드 수정 후
git add .
git commit -m "feat: 기능 설명"
git push origin feature/내브랜치

# 포탈에서 코드 리뷰 → 승인 → 배포
```

## 4. 커밋 메시지 규칙
```
feat: 새 기능       fix: 버그 수정
chore: 설정/기타    docs: 문서
refactor: 리팩터링  test: 테스트
```

## 5. 주의사항
- **main 브랜치에 직접 push 금지**
- 반드시 브랜치 → 리뷰 → 배포 경로
- LLM API Key는 설정(톱니바퀴)에서 등록
