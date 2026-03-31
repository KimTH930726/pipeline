# 팀원 개발 환경 세팅 가이드

## 1. 사전 준비
- Git 설치
- VSCode 설치
- 서버 SSH 접속 가능 (관리자에게 계정 요청)

## 2. 포탈 회원가입
1. 브라우저에서 포탈 접속 (예: `http://서버IP:3000`)
2. **회원가입** 클릭 → 아이디, 비밀번호, LLM API Key 입력
3. 관리자 승인 대기 → 승인 후 로그인 가능

## 3. 프로젝트 클론
```bash
git clone ssh://user@서버IP/srv/repos/SMAgentLab.git
cd SMAgentLab
```

## 4. VSCode로 열기
```bash
code .
```

## 5. 개발 흐름

### 브랜치 생성
포탈 → **브랜치 관리** → 기준 브랜치(main) 선택 → 새 브랜치 이름 입력 → 생성

### 브랜치 전환 (VSCode)
```bash
git fetch
git checkout feature/내브랜치
```

### 코드 수정 → 커밋 → 푸쉬
```bash
# 코드 수정 후
git add .
git commit -m "feat: 기능 설명"
git push origin feature/내브랜치
```

### 코드 리뷰 요청
포탈 → **코드 리뷰** → 브랜치 선택 → 변경사항/diff 확인 → 리뷰어에게 승인 요청

### 배포
포탈 → **배포** → 승인된 브랜치 선택 → 배포 실행
- 빌드 성공 → main 자동 머지 → Docker 재기동
- 빌드 실패 → AI 원인 분석 → 원복 가능

## 6. 커밋 메시지 규칙
```
feat: 새 기능
fix: 버그 수정
chore: 설정/기타
docs: 문서
refactor: 리팩터링
```

## 7. 주의사항
- **main 브랜치에 직접 push 금지** — 반드시 브랜치 → 리뷰 → 배포 경로
- 배포 전 **AI 영향도 분석 / 코드 리뷰** 활용 권장
- LLM API Key는 포탈 **설정**(톱니바퀴) 에서 등록/변경
