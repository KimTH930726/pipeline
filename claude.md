# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
GitHub/GitLab 대체용 자체 SCM & 배포 포탈 (StarbucksCSP Agentic Deployment).
브랜치 관리 → 코드 리뷰(AI 분석 + 승인) → 배포(빌드→머지→Docker) → 원복. 사용자 인증 + 사용자별 LLM Key.

## Tech Stack
- **Frontend**: React 19 + TypeScript, Tailwind CSS, Vite, Zustand, Axios, react-markdown
- **Backend**: Python 3.11, FastAPI (async), SQLAlchemy 2.0 async + aiosqlite
- **SCM**: GitPython (싱글턴 `get_git_repo()`)
- **LLM**: DevX MCP API (InHouse Gemini) — 사용자별 API Key, 미설정 시 400 에러
- **Auth**: JWT (python-jose) + bcrypt + Fernet (API Key 암호화)
- **Real-time**: WebSocket (빌드 로그 스트리밍)

## Commands
```bash
make dev              # backend + frontend 동시 실행
docker compose up -d  # Full stack (frontend:3000, backend:8080)
```

## Architecture

### Bounded Contexts
```
backend/app/<context>/
  interface/router.py → application/use_cases.py → domain/entities.py ← infrastructure/
```

| Context | Responsibility |
|---------|---------------|
| **auth** | JWT 인증, 회원가입(관리자 승인), 비밀번호 변경, API Key 관리 |
| **git** | 브랜치 CRUD, diff, merge, revert, 충돌 감지/해결, 배포간 diff |
| **review** | 코드 리뷰 승인/반려 + acted_by 추적 |
| **deployment** | 빌드→충돌체크→머지→Docker 재기동, 이력(페이징), 배포 비교, acted_by |
| **analysis** | AI 영향도 + AI 코드리뷰 + 머지 충돌 AI 해결 + RCA + 수정 프롬프트 |
| **rollback** | git revert -m 1 + 자동 재배포 |
| **sandbox** | 브랜치별 Docker 컨테이너 (backend+frontend, 동적 포트, node:20-alpine 빌드) |
| **audit** | SHA-256 해시체인 감사 로그 (브랜치/이벤트 필터, 페이징) |

### Key Patterns
- **GitPythonRepository 싱글턴** + `_with_main_checkout()` 헬퍼 (stash/checkout/restore 공통화)
- **Git router async**: `run_in_executor`로 blocking 작업 thread pool 실행
- **Deploy 검증**: 승인 여부 + 브랜치 존재 + 인증 필수 (API 레벨)
- **LLM**: DevX InHouse API (blocking 모드, Bearer 인증, 사용자별 키)
- **Auth**: JWT access(8h)/refresh(7d), 회원가입→관리자 승인→활성화
- **Frontend**: 탭 포커스 시 자동 리로드 (`useAutoRefresh`), 마크다운 렌더링
- **Sandbox 빌드**: 컨테이너 내부 `docker build` (Dockerfile 캐시 레이어 활용, 폐쇄망 호환 — 패키지 변경 없을 시)

## Environment Variables
| Variable | Purpose |
|----------|---------|
| `REPO_PATH` | Git repo 경로 |
| `DATABASE_URL` | SQLite 경로 |
| `LLM_ENDPOINT` | DevX MCP API URL |
| `LLM_API_KEY` | 시스템 LLM Key (fallback) |
| `JWT_SECRET_KEY` | JWT 서명 키 |
| `FERNET_SECRET_KEY` | API Key 암호화 키 (.env로 관리) |
| `DEPLOY_TARGET_PATH` | 배포 대상 호스트 경로 (docker-compose + 샌드박스 node_modules 참조) |
| `ADMIN_DEFAULT_PASSWORD` | 초기 admin 비밀번호 |

## API Routes
```
Auth:     POST /api/auth/login|signup|register|refresh
          GET  /api/auth/me|users  PUT /api/auth/me/password|api-key
          PUT  /api/auth/users/{id}/activate|deactivate
Git:      GET/POST/DELETE /api/git/branches
          GET /api/git/branches/files|diff
Review:   POST /api/review/approve|reject  GET /api/review/approved|status/{branch}
Deploy:   POST /api/deploy/  GET /api/deploy/recent|status/{id}|compare/{a}/{b}
          WS /api/deploy/ws/{id}
Analysis: POST /api/analysis/impact|review|conflicts|conflicts/apply|rca
Rollback: POST /api/rollback/
Sandbox:  POST /api/sandbox/  POST /api/sandbox/{id}/stop  DELETE /api/sandbox/{id}
Audit:    GET /api/audit/timeline?branch=&event_type=&limit=&offset=
```

## Database
SQLite, 5개 테이블: `users`, `deployments`, `reviews`, `audit_logs`, `sandboxes`. Auto-created on startup.
