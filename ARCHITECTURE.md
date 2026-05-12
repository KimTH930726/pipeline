# Agentic Deployment Portal — 아키텍처 및 프로젝트 개요

## 1. 프로젝트 개요

GitHub/GitLab 대체용 **자체 SCM & 배포 포탈**. 폐쇄망 환경에서도 동작하도록 설계됨.

> 브랜치 생성 → 샌드박스 테스트 → 코드 리뷰(AI 분석 + 승인) → 배포(충돌체크 → squash 머지 → Docker 재기동) → 원복

### 핵심 특징
- **폐쇄망 호환** — Docker 캐시 기반 빌드, npm/pip 네트워크 불필요 (패키지 변경 없을 시)
- **AI 분석** — 영향도 분석, 코드 리뷰, 충돌 해결, 실패 원인 분석(RCA), 샌드박스 에러 분석
- **실시간 파이프라인** — WebSocket으로 4단계(충돌확인→빌드검증→머지→Docker재기동) 실시간 표시
- **사용자 추적** — 모든 행동에 acted_by 기록 (배포/원복/리뷰/감사로그)
- **동시 실행 방지** — 배포/원복 진행 중 새 작업 차단 (deploy lock)

---

## 2. 기술 스택

| 레이어 | 기술 |
|--------|------|
| **Frontend** | React 19, TypeScript, Tailwind CSS, Vite, Zustand, react-markdown |
| **Backend** | Python 3.11, FastAPI (async), SQLAlchemy 2.0 async + aiosqlite |
| **SCM** | GitPython (싱글턴 패턴) |
| **LLM** | DevX Gateway — client_credentials OAuth2 + SSE streaming. 하이브리드 자격증명(사용자 DB 개별 → `.env` 팀 fallback) |
| **Auth** | JWT (python-jose) + bcrypt + Fernet (시크릿 암호화) |
| **Real-time** | WebSocket (빌드 로그 + 파이프라인 단계 스트리밍) |
| **DB** | SQLite (5개 테이블, 서버 기동 시 자동 생성) |
| **Container** | Docker + Docker Compose |

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 (브라우저)                           │
│   React 19 + Tailwind + Zustand + WebSocket                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────────────────┐
│              Pipeline Portal (Docker)                        │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │  Frontend (:3000) │  │  Backend (:8080)                 │ │
│  │  nginx + React    │  │  FastAPI (async)                 │ │
│  │  빌드 정적 파일    │  │  ├─ auth (JWT/bcrypt)           │ │
│  └──────────────────┘  │  ├─ git (GitPython)              │ │
│                         │  ├─ review (승인/반려)            │ │
│                         │  ├─ deployment (배포 파이프라인)   │ │
│                         │  ├─ analysis (LLM AI 분석)       │ │
│                         │  ├─ rollback (원복)              │ │
│                         │  ├─ sandbox (브랜치별 환경)       │ │
│                         │  └─ audit (감사 로그)            │ │
│                         │                                  │ │
│                         │  SQLite (/data/audit.db)         │ │
│                         └──────────────────────────────────┘ │
│                                    │                         │
│                         Docker Socket (/var/run/docker.sock) │
└────────────────────────────────────┬─────────────────────────┘
                                     │ docker compose 명령
┌────────────────────────────────────▼─────────────────────────┐
│              배포 대상 (SMAgentLab)                            │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ Backend    │ │ Frontend   │ │ Postgres │ │ Redis       │ │
│  │ (:8000)    │ │ (:8501)    │ │ (:5432)  │ │             │ │
│  │ 소스 볼륨  │ │ 이미지 빌드 │ │ pgvector │ │ 7-alpine    │ │
│  └────────────┘ └────────────┘ └──────────┘ └─────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 백엔드 아키텍처 (DDD Bounded Context)

```
backend/app/<context>/
  interface/router.py        ← API 엔드포인트 (FastAPI Router)
  application/use_cases.py   ← 비즈니스 로직
  application/dtos.py        ← 요청/응답 DTO
  domain/entities.py         ← 도메인 모델
  domain/repositories.py     ← 포트 (추상 인터페이스)
  infrastructure/            ← 어댑터 (SQLAlchemy, Git, LLM)
```

| Context | 역할 |
|---------|------|
| **auth** | JWT 인증, 회원가입(관리자 승인), 비밀번호 변경 |
| **git** | 브랜치 CRUD, diff(`main..branch`), squash merge(+fallback), revert, 충돌 감지/해결 |
| **review** | 코드 리뷰 승인/반려, 배포 성공 시 PENDING 자동 초기화 |
| **deployment** | 배포 파이프라인 (빌드검증→머지→Docker재기동), 이력 관리(상태/날짜 필터, 페이징) |
| **analysis** | AI 영향도 분석, 코드 리뷰, 충돌 해결(LLM 실패 시 수기 유도), RCA, 샌드박스 에러 분석 |
| **rollback** | git revert HEAD + 자동 재배포(머지 스킵), 원복 배포 태그, 재원복 방지 |
| **sandbox** | 브랜치별 독립 Docker 환경 (backend+frontend, 동적 포트 할당) |
| **audit** | SHA-256 해시체인 감사 로그, acted_by 추적 |

---

## 5. 배포 파이프라인 흐름

```
배포 실행 클릭
    │
    ▼
[1. 충돌 확인] ──충돌 발생──▶ AI 해결안 제시 → 승인 → 재배포
    │ 충돌 없음
    ▼
[2. 빌드 검증] ──실패──▶ RCA 분석 → 오류 원인 표시
    │ 성공
    ▼
[3. main 머지] ──squash merge──▶ 원복 후 재배포 시 fallback checkout
    │ 성공
    ▼
[4. Docker 재기동]
    ├─ backend: docker compose restart (볼륨 마운트)
    └─ frontend: docker compose build --no-cache + up --no-deps
    │
    ▼
배포 성공 → 리뷰 PENDING 초기화 + 샌드박스 자동 삭제
```

### 원복 흐름
```
원복 실행 → git revert HEAD → Docker 재기동 (머지 스킵)
         → 배포 이력에 "원복 배포" 태그
         → 원복 후 같은 브랜치 재배포 가능 (squash merge)
```

---

## 6. 프론트엔드 페이지 구조

| Route | 페이지 | 설명 |
|-------|--------|------|
| `/` | 대시보드 | 배포 현황 카드 + 이력 (상태/날짜 필터, 페이징) |
| `/branches` | 브랜치 관리 | 생성(기본: main), 삭제, 목록 |
| `/review` | 코드 리뷰 | AI 영향도/코드리뷰 + 승인/반려, 머지 완료 안내 |
| `/sandbox` | 샌드박스 | 브랜치별 독립 환경, 좌우 스크롤 카드, 에러 AI 분석 |
| `/deploy` | 배포 | 배포 실행 전용, 4단계 파이프라인 UI, 실시간 빌드 로그 |
| `/history` | 배포 이력 | 상세(커밋/변경파일/빌드로그 토글), 원복, 배포 비교, 필터 |
| `/guide` | 시작 가이드 | 9단계 가이드 (클론→브랜치→샌드박스→리뷰→배포→원복→설정) |
| `/settings` | 설정 | 비밀번호 변경 + 개별 LLM 자격증명 등록 |
| `/admin` | 관리자 | 사용자 관리 (승인/비활성화) |

---

## 7. 주요 설계 결정

### Git 전략
- **squash merge** — 원복(`git revert`) 후 재배포 시 "Already up to date" 방지
- **fallback checkout** — squash가 빈 결과일 때 `git checkout branch -- .`로 강제 적용
- **main 고정** — `_with_main_checkout()` 후 원래 브랜치로 돌아가지 않음 (Docker 빌드 소스 오염 방지)

### Docker 재기동
- **backend** — 소스 볼륨 마운트 → `restart`로 충분
- **frontend** — 이미지 내 정적 파일 → `build --no-cache` + `up --no-deps` (의존 서비스 미간섭)
- **프로젝트명** — `compose -p smagentlab`으로 기존 컨테이너 인식

### 동시성 제어
- **deploy lock** — BUILDING 상태 배포 존재 시 새 배포/원복/샌드박스 생성 409 거부
- **git lock** — `threading.Lock()`으로 git 명령 직렬화

### 폐쇄망 호환
- Docker 캐시 레이어로 `npm install`/`pip install` 스킵 (패키지 변경 없을 시)
- `export-images.sh` — pipeline + SMAgentLab + 의존 이미지 8개 일괄 내보내기
- `import-and-run.sh` — 이미지 로드 → bare repo → .env 자동 생성 → 서비스 기동

---

## 8. 환경 변수

| 변수 | 용도 | 기본값 |
|------|------|--------|
| `REPO_PATH` | Git repo 경로 | ~/agentic-scm-portal/sample-repo |
| `DATABASE_URL` | SQLite 경로 | sqlite+aiosqlite:///~/audit.db |
| `LLM_AUTH_ENDPOINT` | DevX Gateway 토큰 발급 URL | https://devx-gw.../auth/token |
| `LLM_CHAT_ENDPOINT` | DevX Gateway 채팅 URL (SSE) | https://devx-gw.../agent/chat |
| `LLM_CLIENT_ID` / `LLM_CLIENT_SECRET` | 시스템 단일 자격증명 | - |
| `LLM_AGENT_ID` / `LLM_AGENT_CODE` | 호출 대상 Agent | b6958377.../playground |
| `JWT_SECRET_KEY` | JWT 서명 키 | change-this-secret... |
| `FERNET_SECRET_KEY` | 시크릿 암호화 키 | (자동 생성) |
| `DEPLOY_TARGET_PATH` | 배포 대상 호스트 경로 | - |
| `DEPLOY_COMPOSE_PROJECT` | Docker Compose 프로젝트명 | smagentlab |
| `DEPLOY_COMPOSE_OVERRIDES` | 추가 compose 오버라이드 (콤마 구분) | - |
| `DEPLOY_SERVICE_NAME` | 재기동 대상 서비스 | backend frontend |
| `DEPLOY_MODE` | restart(폐쇄망) / rebuild(인터넷) | restart |
| `IMAGE_TAG` | prod compose의 이미지 태그 | latest |
| `ADMIN_DEFAULT_PASSWORD` | 초기 관리자 비밀번호 | admin1234 |

---

## 9. 폐쇄망 배포 가이드 (prod 모드)

운영 시 `docker-compose.yml` + `docker-compose.prod.yml`을 함께 사용. 이미지 태그는 `IMAGE_TAG` 변수로 명시(롤백·멀티버전 보존). 상세 절차는 [`docs/deployment-closed-network.md`](docs/deployment-closed-network.md) 참고.

```bash
# 빌드 PC (인터넷)
cd pipeline
bash scripts/export-images.sh v1.0          # → pipeline-images-v1.0.tar.gz
# Windows: powershell -ExecutionPolicy Bypass -File scripts\export-images.ps1 -Tag v1.0

# SMAgentLab 이미지는 SMAgentLab 리포에서 별도 빌드
bash ../SMAgentLab/scripts/export-images.sh v2.16

# 폐쇄망 서버 (최초)
cd /opt/pipeline
bash scripts/import-and-run.sh pipeline-images-v1.0.tar.gz \
  --project-path /opt/smagentlab \
  --smagent-images smagentlab-images-v2.16.tar.gz

# 업데이트
bash scripts/update-images.sh pipeline-images-v1.1.tar.gz
```

### 포함 이미지 (pipeline 묶음)
| 이미지 | 용도 |
|--------|------|
| `pipeline-backend:${IMAGE_TAG}` | 포탈 백엔드 |
| `pipeline-frontend:${IMAGE_TAG}` | 포탈 프론트엔드 |
| `node:20-alpine` | 샌드박스 프론트엔드 빌드 |
| `nginx:alpine` | 프론트엔드 서빙 |

> SMAgentLab 이미지(`smagentlab-backend/frontend`, `pgvector`, `redis`)는 SMAgentLab 묶음에서 반입.

### prod 모드 핵심 차이
- `build: !reset null` — 사전 빌드 이미지만 사용
- `pull_policy: never` — 외부 레지스트리 접근 차단
- pipeline `volumes`(repo, deploy-target, sandboxes, db-data, docker.sock)는 base 그대로 유지 — 운영에 필수
- SMAgentLab은 backend의 호스트 소스 마운트 유지 (pipeline 배포가 git merge → restart로 작동하기 위함)

---

## 10. 디렉토리 구조

```
pipeline/
├── backend/
│   ├── app/
│   │   ├── auth/           # 인증/인가
│   │   ├── git/            # Git 관리
│   │   ├── review/         # 코드 리뷰
│   │   ├── deployment/     # 배포 파이프라인
│   │   ├── analysis/       # AI 분석 (LLM)
│   │   ├── rollback/       # 원복
│   │   ├── sandbox/        # 샌드박스
│   │   ├── audit/          # 감사 로그
│   │   ├── shared/         # 공통 (DB, 이벤트 버스, deploy lock)
│   │   ├── config.py       # 환경 설정
│   │   └── main.py         # FastAPI 앱 진입점
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # API 클라이언트
│   │   ├── components/     # 공통 컴포넌트
│   │   ├── hooks/          # 커스텀 훅 (WebSocket, 자동 리프레시)
│   │   ├── pages/          # 페이지 컴포넌트
│   │   ├── store/          # Zustand 상태 관리
│   │   └── types/          # TypeScript 타입
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/
│   ├── export-images.sh    # 이미지 빌드+내보내기 (Linux/macOS)
│   ├── export-images.ps1   # 이미지 빌드+내보내기 (Windows PowerShell)
│   ├── import-and-run.sh   # 폐쇄망 최초 배포
│   ├── update-images.sh    # 폐쇄망 이미지 업데이트 (백업 자동 제안)
│   ├── backup-db.sh        # SQLite DB 백업
│   └── restore-db.sh       # SQLite DB 복원
├── docs/
│   └── deployment-closed-network.md  # 폐쇄망 운영 가이드
├── docker-compose.yml          # base
├── docker-compose.prod.yml     # 운영(폐쇄망) 오버라이드
├── .env                        # 환경 변수 (git 제외)
├── CLAUDE.md                   # Claude Code 가이드
└── ARCHITECTURE.md              # 이 문서
```
