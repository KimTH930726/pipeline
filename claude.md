# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
GitHub/GitLab 대체용 자체 SCM & 배포 포탈 (StarbucksCSP Agentic Deployment).
브랜치 관리 → 코드 리뷰(AI 분석 + 승인) → 배포(빌드→머지→Docker) → 원복. 사용자 인증 + 사용자별 LLM Key.

## Tech Stack
- **Frontend**: React 19 + TypeScript, Tailwind CSS, Vite, Zustand, react-markdown
- **Backend**: Python 3.11, FastAPI (async), SQLAlchemy 2.0 async + aiosqlite
- **SCM**: GitPython (싱글턴 `get_git_repo()`)
- **LLM**: DevX MCP API (InHouse Gemini) — 사용자별 API Key, 미설정 시 400 에러
- **Auth**: JWT (python-jose) + bcrypt + Fernet (API Key 암호화)
- **Real-time**: WebSocket (빌드 로그 + 파이프라인 단계 스트리밍)

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
| **git** | 브랜치 CRUD, diff(`main..branch`), squash merge(fallback checkout), revert HEAD, 충돌 감지/해결, 배포간 diff |
| **review** | 코드 리뷰 승인/반려 + acted_by 추적, 배포 성공 시 PENDING 자동 초기화 |
| **deployment** | 빌드→충돌체크→squash 머지→Docker 재기동(backend restart/frontend --no-cache rebuild), 이력(상태+날짜 필터, 페이징), 배포 비교, 파이프라인 4단계 실시간 UI, 배포 성공 시 샌드박스 자동 삭제 |
| **analysis** | AI 영향도 + AI 코드리뷰 + 머지 충돌 AI 해결(LLM 실패 시 수기 보정 유도) + RCA + 수정 프롬프트 |
| **rollback** | git revert HEAD + 자동 재배포(머지 스킵), 원복 배포 구분 태그, 원복 배포에 재원복 방지 |
| **sandbox** | 브랜치별 Docker 컨테이너 (backend+frontend, 동적 포트, 컨테이너 내부 docker build) |
| **audit** | SHA-256 해시체인 감사 로그 (브랜치/이벤트 필터, 페이징, acted_by 추적) |

### Key Patterns
- **GitPythonRepository 싱글턴** + `_with_main_checkout()` 헬퍼 (stash/checkout/restore 공통화)
- **Git router async**: `run_in_executor`로 blocking 작업 thread pool 실행
- **Squash Merge**: `git merge --squash` + fallback (`git checkout branch -- .`) — 원복 후 재배포 시 Already up to date 방지
- **Deploy 검증**: 승인 여부 + 브랜치 존재 + 인증 필수 (API 레벨)
- **Deploy Docker**: Docker 재기동 전 `git checkout main` 강제, backend=`compose restart`, frontend=`compose build --no-cache` + `up --no-deps` (compose `-p` 프로젝트명 지정)
- **Rollback**: `git revert HEAD` → `BuildProcessRunner.run(is_rollback=True)` — 머지 단계 스킵, Docker 재기동만 수행
- **Subprocess**: stdout/stderr 합침(`STDOUT`), `read(4096)` 청크 단위 — Docker compose 출력 hang 방지
- **LLM**: DevX InHouse API (blocking 모드, Bearer 인증, 사용자별 키)
- **Auth**: JWT access(8h)/refresh(7d), 회원가입→관리자 승인→활성화
- **Frontend**: 탭 포커스 시 자동 리로드 (`useAutoRefresh`), 마크다운 렌더링
- **Sandbox 빌드**: 컨테이너 내부 `docker build` (Dockerfile 캐시 레이어 활용, 폐쇄망 호환 — 패키지 변경 없을 시)
- **Datetime**: 서버 UTC 저장, API 응답에 `+00:00` timezone 명시 → 브라우저 자동 로컬 시간 변환

## Environment Variables
| Variable | Purpose |
|----------|---------|
| `REPO_PATH` | Git repo 경로 |
| `DATABASE_URL` | SQLite 경로 |
| `LLM_ENDPOINT` | DevX MCP API URL |
| `LLM_API_KEY` | 시스템 LLM Key (fallback) |
| `JWT_SECRET_KEY` | JWT 서명 키 |
| `FERNET_SECRET_KEY` | API Key 암호화 키 (.env로 관리) |
| `DEPLOY_TARGET_PATH` | 배포 대상 호스트 경로 (docker-compose + 샌드박스 빌드) |
| `DEPLOY_COMPOSE_PROJECT` | 배포 대상 Docker Compose 프로젝트명 (기본: smagentlab) |
| `DEPLOY_SERVICE_NAME` | 재기동 대상 서비스 (기본: backend frontend) |
| `DEPLOY_MODE` | restart(폐쇄망) / rebuild(인터넷) |
| `ADMIN_DEFAULT_PASSWORD` | 초기 admin 비밀번호 |

## API Routes
```
Auth:     POST /api/auth/login|signup|register|refresh
          GET  /api/auth/me|users  PUT /api/auth/me/password|api-key
          PUT  /api/auth/users/{id}/activate|deactivate
Git:      GET/POST/DELETE /api/git/branches
          GET /api/git/branches/files|diff
Review:   POST /api/review/approve|reject|request
          GET  /api/review/approved|status/{branch}|list
Deploy:   POST /api/deploy/
          GET  /api/deploy/recent?status=&branch=&date_from=&date_to=
          GET  /api/deploy/status/{id}|compare/{a}/{b}
          POST /api/deploy/status/{id}/rolled-back
          WS   /api/deploy/ws/{id}
Analysis: POST /api/analysis/impact|review|conflicts|conflicts/apply|rca
Rollback: POST /api/rollback/
Sandbox:  POST /api/sandbox/  POST /api/sandbox/{id}/stop  DELETE /api/sandbox/{id}
Audit:    GET  /api/audit/timeline?branch=&event_type=&limit=&offset=
```

## WebSocket Messages (deploy/ws/{id})
| type | data | 설명 |
|------|------|------|
| `status` | BUILDING/SUCCESS/FAILED | 배포 상태 변경 |
| `stage` | {stage, status} | 파이프라인 단계 진행 (BUILD_VALIDATION/MERGE/DOCKER_RESTART × started/completed/failed) |
| `log_line` | string | 빌드 로그 실시간 라인 |
| `rca` | RCAReport | 실패 시 AI 원인 분석 |

## Frontend Pages
| Route | Page | 설명 |
|-------|------|------|
| `/` | DashboardPage | 배포 현황 카드 + 이력 (상태/날짜 필터, 페이징) |
| `/branches` | BranchPage | 브랜치 생성/삭제/목록 |
| `/review` | ReviewPage | 코드 리뷰 (AI 분석 + 승인/반려) |
| `/deploy` | DeployPage | 배포 실행 전용 (충돌체크 → 빌드 → 머지 → 재기동) |
| `/history` | DeployHistoryPage | 배포 이력 (상세/원복/비교/필터) |
| `/sandbox` | SandboxPage | 샌드박스 관리 |
| `/guide` | GuidePage | 시작 가이드 |
| `/settings` | SettingsPage | 사용자 설정 |
| `/admin` | AdminPage | 관리자 (사용자 관리) |

## Database
SQLite, 5개 테이블: `users`, `deployments`, `reviews`, `audit_logs`, `sandboxes`. Auto-created on startup.

## 폐쇄망 배포
```bash
# 인터넷 PC에서 이미지 내보내기
bash scripts/export-images.sh    # → pipeline-images.tar.gz (node:20-alpine 포함)

# 폐쇄망 서버에서 실행
bash scripts/import-and-run.sh   # 이미지 로드 → bare repo → .env 생성 → 서비스 기동
```
패키지(pip/npm) 변경 없으면 Docker 캐시로 오프라인 동작. 패키지 변경 시 이미지 재빌드 필요.
