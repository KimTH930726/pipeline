# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
GitHub/GitLab 대체용 자체 SCM & 배포 포탈. 브랜치 관리 → 코드 리뷰(승인/반려) → 배포(빌드→main 머지→Docker 재기동) → 원복까지 한 곳에서 처리.

## Tech Stack
- **Frontend**: React 19 + TypeScript, Tailwind CSS, Vite, Zustand, Axios
- **Backend**: Python 3.11, FastAPI (async), SQLAlchemy 2.0 async + aiosqlite
- **SCM**: GitPython (싱글턴 인스턴스, `get_git_repo()`)
- **AI Engine**: LLM behind abstract port — `MockLLMAdapter` (dev) / `VPCLLMAdapter` (prod)
- **Real-time**: WebSocket for build log streaming

## Commands
```bash
make install          # pip install + npm install
make backend          # uvicorn --reload --port 8000
make frontend         # vite dev server (port 5173, proxies /api to backend)
make dev              # Run both concurrently
npm run lint          # ESLint (frontend only)
docker compose up -d  # Full stack (frontend:3000, backend:8080)
```

## Architecture

### DDD Bounded Contexts (7개)
```
backend/app/<context>/
  interface/router.py        # FastAPI endpoints (HTTP + WS)
  application/use_cases.py   # Orchestration
  application/dtos.py        # Pydantic DTOs with field_validator
  domain/entities.py         # Pure domain models (dataclasses)
  domain/repositories.py     # Abstract ports (ABC)
  infrastructure/            # Concrete adapters
```

| Context | Responsibility |
|---------|---------------|
| **git** | 브랜치 CRUD, diff, merge_to_main, revert_to, commit messages, 충돌 감지/해결, 배포간 diff |
| **review** | 코드 리뷰 승인/반려 (PENDING→APPROVED/REJECTED) |
| **deployment** | 빌드→충돌체크→머지→Docker 재기동, 배포 이력(페이징), rolled_back, 배포 비교 |
| **analysis** | AI 영향도 분석 + AI 코드 리뷰 + 머지 충돌 AI 해결 + RCA (ai_fix_prompt) |
| **rollback** | git revert -m 1 + 자동 재배포 |
| **sandbox** | 브랜치별 Docker compose 환경 (backend+frontend 동적 포트, worktree) |
| **audit** | SHA-256 해시체인 감사 로그 (브랜치/이벤트 필터) |

### Cross-Cutting (`backend/app/shared/`)
- **Event Bus**: In-process async pub/sub. Wired in `main.py` lifespan.
- **Database**: Async SQLAlchemy, `SessionFactory`, `init_db()` auto-creates tables.
- **Exceptions**: `DomainException` base → HTTP status mapping (NOT_FOUND:404, CONFLICT:409, FORBIDDEN:403).

### Key Patterns
- **GitPythonRepository 싱글턴**: `get_git_repo()` — 앱 수준 1개 인스턴스. 매 요청 생성 안 함.
- **Git router async**: `run_in_executor`로 blocking git 작업을 thread pool에서 실행.
- **State Machines**: Deployment (PENDING→BUILDING→SUCCESS|FAILED), Review (PENDING→APPROVED|REJECTED).
- **Build Pipeline**: 빌드 검증 → main 머지 (stash→checkout→merge→pop) → Docker 재빌드.
- **Deploy 검증**: API에서 승인 여부 + 브랜치 존재 여부 검증 후 배포 허용.
- **Rollback**: `git revert -m 1`로 머지 커밋 안전 revert. rolled_back 플래그로 중복 방지.
- **AI 코드 리뷰**: 버그/보안/성능/스타일/제안 자동 감지. 영향도 분석과 별도 버튼.
- **머지 충돌 AI 해결**: 배포 시 충돌 감지 → AI가 해결안 생성 → 사용자 승인 후 머지.
- **배포 비교**: 두 배포 간 commit SHA diff. 비교 모드에서 체크박스로 선택.
- **Index 정리**: `_cleanup_index()`로 깨진 git 상태 자동 복구 (merge --abort + reset).
- **Sandbox**: git worktree + docker compose up (backend+frontend만, DB/Redis 공유).
- **RCA + AI Fix Prompt**: 실패 분석 시 수정 프롬프트까지 생성 (Cursor/Claude에 복사 가능).

### Frontend Structure
- **Pages**: Dashboard(`/`), Branch(`/branches`), Review(`/review`), Deploy(`/deploy`), Sandbox(`/sandbox`), Audit(`/audit`)
- **State**: Zustand store — deployment state, build log, RCA report
- **API Layer**: Typed wrappers in `api/{deployApi,gitApi,reviewApi,auditApi}.ts`
- **Deploy Page**: 승인 브랜치만 표시, 변경사항 미리보기, 충돌 해결 UI, 이력 페이징+토글+비교 모드, 원복

## Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `REPO_PATH` | `~/agentic-scm-portal/sample-repo` | Git repo 경로 |
| `DATABASE_URL` | `sqlite+aiosqlite:///...` | SQLite DB |
| `LLM_MODE` | `mock` | `mock` / `vpc` |
| `LLM_ENDPOINT` | — | VPC LLM URL |
| `DEPLOY_TARGET_PATH` | (미설정) | 배포 대상 docker-compose 경로 |
| `DEPLOY_COMPOSE_FILE` | `docker-compose.yml` | compose 파일명 |
| `DEPLOY_SERVICE_NAME` | (전체) | 특정 서비스만 재빌드 시 |
| `SANDBOX_PORT_MIN/MAX` | `9100`/`9199` | 샌드박스 포트 범위 |

## API Routes
- `GET/POST/DELETE /api/git/branches` — 브랜치 CRUD
- `POST /api/review/approve|reject`, `GET /api/review/approved`
- `POST /api/deploy/`, `GET /api/deploy/recent?page=&size=`, `GET /api/deploy/status/{id}`
- `WS /api/deploy/ws/{id}` — 실시간 빌드 로그
- `POST /api/analysis/impact|review|conflicts|rca`
- `POST /api/analysis/conflicts/apply` — 충돌 해결안 적용
- `GET /api/deploy/compare/{id_from}/{id_to}` — 배포 간 diff
- `POST /api/rollback/`
- `POST /api/sandbox/`, `POST /api/sandbox/{id}/stop`, `DELETE /api/sandbox/{id}`
- `GET /api/audit/timeline?branch=&event_type=`

## Database
SQLite, 4개 테이블: `deployments`, `reviews`, `audit_logs`, `sandboxes`. Auto-created on startup.
