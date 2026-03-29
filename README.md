# Agentic SCM & Deployment Portal

> Python AI 서비스 전용 **자율 배포 가드레일 플랫폼**
> "투명한 배포와 지능형 복구" — AI가 배포 전/후를 감시하여 실패 시 원인 분석과 원복을 동시에 처리합니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [핵심 기능](#2-핵심-기능)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [기술 스택](#4-기술-스택)
5. [프로젝트 구조](#5-프로젝트-구조)
6. [설치 및 실행](#6-설치-및-실행)
7. [API 명세](#7-api-명세)
8. [화면 구성](#8-화면-구성)
9. [핵심 워크플로우](#9-핵심-워크플로우)
10. [설정](#10-설정)

---

## 1. 프로젝트 개요

### 배경
배포 실패 시 "왜 실패했는지" 파악하는 데 시간이 걸리고, 그 동안 운영 환경이 불안정한 상태로 남는 문제를 해결합니다.

### 해결 방안
| 문제 | 해결 |
|------|------|
| 배포 실패 원인 파악에 시간 소요 | AI(LLM)가 빌드 로그를 즉시 분석하여 원인과 해결책 제시 |
| 실패 후 수동 원복 필요 | 원클릭 자동 원복(git revert + 재배포) |
| 변경사항의 영향 범위 불명확 | 배포 전 AI 영향도 분석 리포트 제공 |
| 배포 이력 추적 어려움 | 해시체인 기반 변조 불가능한 감사 로그 |

---

## 2. 핵심 기능

### R1. 코드 리뷰 & AI 영향도 분석
- 브랜치별 변경 파일 목록 및 Unified Diff 뷰어
- AI가 변경사항을 분석하여 **위험도(LOW/MEDIUM/HIGH/CRITICAL)** 판정
- 영향받는 서비스 목록 및 권장사항 제공

### R2. 독립 샌드박스
- 브랜치별 독립 포트(9100~9199) 할당
- 격리된 테스트 환경에서 사전 검증 가능
- 생성/삭제/목록 관리 UI

### R3. AI 빌드 실패 분석 (RCA)
- 빌드 실패 시 CI/CD 로그 자동 수집
- LLM이 **실패 원인(Root Cause)**, **영향 파일**, **수정 가이드**를 즉시 도출
- 신뢰도 점수(0~100%) 함께 제공
- 배포 화면에 실시간으로 분석 결과 표시

### R4. 지능형 원복 (Agentic Rollback)
- 빌드 실패 즉시 **원복 버튼 활성화**
- `git revert`로 안정적인 이전 커밋으로 회귀
- 원복 후 자동 재배포 트리거
- 확인 다이얼로그로 오조작 방지

### R5. 감사 로그 & 투명성
- 모든 배포/실패/원복 이벤트의 타임라인 기록
- **SHA-256 해시체인**으로 변조 감지 가능
- AI 분석 리포트 영구 보존
- 이벤트 타입별 필터링 및 상세 조회

---

## 3. 시스템 아키텍처

### 전체 구조
```
┌─────────────────┐       ┌──────────────────────────────────────┐
│                 │       │           Backend (FastAPI)           │
│   Frontend      │       │                                      │
│   React SPA     │──────▶│  ┌─────┐ ┌──────┐ ┌────────┐       │
│   (Nginx:3000)  │  API  │  │ Git │ │Deploy│ │Analysis│       │
│                 │◀──────│  └──┬──┘ └──┬───┘ └───┬────┘       │
│  - Dashboard    │       │     │       │         │             │
│  - Review       │  WS   │     ▼       ▼         ▼             │
│  - Deploy       │◀─────▶│  ┌──────────────────────────┐      │
│  - Sandbox      │       │  │     Domain Event Bus      │      │
│  - Audit        │       │  └────────────┬─────────────┘      │
│                 │       │               │                      │
└─────────────────┘       │  ┌────────┐  │  ┌─────────┐        │
                          │  │Rollback│  ▼  │  Audit   │        │
                          │  └────────┘     │(HashChain)│        │
                          │                 └──────────┘        │
                          │                      │               │
                          │              ┌───────▼──────┐       │
                          │              │  SQLite DB    │       │
                          │              └──────────────┘       │
                          └──────────────────────────────────────┘
```

### DDD Bounded Contexts
```
┌──────────┐    ┌───────────┐    ┌──────────┐
│   Git    │───▶│ Analysis  │    │ Sandbox  │
│(upstream)│    │  (LLM)    │    │(isolated)│
└────┬─────┘    └─────┬─────┘    └────┬─────┘
     │                │               │
     ▼                ▼               │
┌──────────┐  domain events    ┌─────▼─────┐
│Deployment│──────────────────▶│   Audit   │
└────┬─────┘                   │(hash-chain)│
     │                         └─────▲─────┘
     ▼                               │
┌──────────┐  domain events          │
│ Rollback │─────────────────────────┘
└──────────┘
```

### 레이어 구조 (각 Bounded Context 내부)
```
interface/       ← FastAPI Router (얇은 컨트롤러)
application/     ← Use Case, DTO (오케스트레이션)
domain/          ← Entity, Repository Port, Event, Exception (순수 비즈니스 로직)
infrastructure/  ← SQLAlchemy, GitPython, LLM Adapter (외부 연동)
```

**의존성 규칙**: `interface → application → domain ← infrastructure`
도메인 레이어는 프레임워크(SQLAlchemy, FastAPI)를 절대 import하지 않습니다.

---

## 4. 기술 스택

### Backend
| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11 | 런타임 |
| FastAPI | ≥0.115 | 웹 프레임워크 |
| SQLAlchemy | ≥2.0 (async) | ORM |
| aiosqlite | ≥0.20 | 비동기 SQLite |
| GitPython | ≥3.1.40 | Git 조작 |
| httpx | ≥0.27 | 비동기 HTTP (LLM 호출) |
| Pydantic | v2 | 데이터 검증 |
| uvicorn | ≥0.30 | ASGI 서버 |

### Frontend
| 기술 | 버전 | 용도 |
|------|------|------|
| React | 19.x | UI 라이브러리 |
| TypeScript | 5.9 | 타입 안전성 |
| Vite | 8.x | 빌드 도구 |
| Tailwind CSS | 4.x | 스타일링 |
| Zustand | 5.x | 상태 관리 |
| React Router | 7.x | SPA 라우팅 |
| Axios | 1.x | HTTP 클라이언트 |
| Lucide React | 1.x | 아이콘 |

### Infrastructure
| 기술 | 용도 |
|------|------|
| Docker + Docker Compose | 컨테이너화 |
| Nginx | 프론트엔드 서빙 + API 리버스 프록시 |
| SQLite | 데이터 저장 (감사 로그, 배포 이력) |

---

## 5. 프로젝트 구조

```
agentic-scm-portal/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI 앱 팩토리 + 이벤트 버스 연결
│       ├── config.py               # 환경 설정
│       ├── shared/                 # 공유 커널
│       │   ├── domain/             #   Value Objects, Events, Exceptions
│       │   ├── infrastructure/     #   Database, Event Bus
│       │   └── interfaces/         #   Global Error Handlers
│       ├── git/                    # Git 바운디드 컨텍스트
│       ├── deployment/             # 배포 바운디드 컨텍스트
│       ├── analysis/               # AI 분석 바운디드 컨텍스트
│       ├── rollback/               # 원복 바운디드 컨텍스트
│       ├── sandbox/                # 샌드박스 바운디드 컨텍스트
│       └── audit/                  # 감사 로그 바운디드 컨텍스트
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── pages/                  # 5개 페이지
│       ├── components/             # UI 컴포넌트
│       ├── api/                    # API 클라이언트
│       ├── hooks/                  # WebSocket 훅
│       ├── store/                  # Zustand 스토어
│       └── types/                  # TypeScript 타입
├── sample-repo/                    # 테스트용 Git 리포지토리
├── docker-compose.yml
└── Makefile
```

---

## 6. 설치 및 실행

### Docker (권장)
```bash
# 빌드 & 실행
docker compose up -d

# 접속
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs

# 중지
docker compose down
```

### 로컬 개발
```bash
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Makefile
```bash
make install    # 의존성 설치
make backend    # 백엔드 실행
make frontend   # 프론트엔드 실행
make dev        # 둘 다 동시 실행
```

---

## 7. API 명세

### Health Check
```
GET /api/health
→ { "status": "ok", "app": "Agentic SCM Portal" }
```

### Git Operations

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/git/branches` | 브랜치 목록 조회 |
| `GET` | `/api/git/branches/files?branch={name}` | 변경 파일 목록 |
| `GET` | `/api/git/diff?branch={name}&path={file}` | 파일별 Diff |

### Deployment

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/deploy/` | 배포 실행 `{ "branch": "..." }` |
| `GET` | `/api/deploy/status/{id}` | 배포 상태 조회 |
| `GET` | `/api/deploy/recent` | 최근 배포 이력 |
| `WS` | `/api/deploy/ws/{id}` | 실시간 빌드 로그 스트림 |

**WebSocket 메시지 형식:**
```json
{ "type": "log_line", "data": "[BUILD] Compiling...", "stream": "stdout" }
{ "type": "status",   "data": "FAILED", "exit_code": 1 }
{ "type": "rca",      "data": { "root_cause": "...", "suggested_fix": "..." } }
```

### Analysis

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/analysis/impact` | AI 영향도 분석 `{ "branch": "..." }` |
| `POST` | `/api/analysis/rca` | AI 실패 원인 분석 `{ "deployment_id": 1 }` |

### Rollback

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/rollback/` | 원복 실행 `{ "branch": "...", "target_sha": null }` |

### Sandbox

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/sandbox/` | 샌드박스 생성 `{ "branch": "..." }` |
| `GET` | `/api/sandbox/` | 샌드박스 목록 |
| `DELETE` | `/api/sandbox/{id}` | 샌드박스 삭제 |

### Audit

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/audit/timeline` | 감사 로그 타임라인 (필터: branch, event_type) |
| `GET` | `/api/audit/{id}` | 감사 로그 상세 |

---

## 8. 화면 구성

### 대시보드 (`/`)
배포 현황 요약 대시보드
- 통계 카드: 최근 배포 수, 성공, 실패, 원복 횟수
- 최근 배포 목록 (브랜치, 상태, 시간)
- 최근 이벤트 타임라인

### 코드 리뷰 (`/review`)
배포 전 변경사항 검토 화면
- 브랜치 선택 → 변경 파일 목록 (A/M/D 상태 표시)
- 파일 선택 → Unified Diff 뷰 (추가: 초록, 삭제: 빨강)
- **AI 영향도 분석** 버튼 → 위험도, 영향 서비스, 권장사항

### 배포 (`/deploy`)
빌드 실행 및 모니터링 화면
- 브랜치 선택 → 배포 실행 버튼
- **실시간 빌드 로그** (WebSocket, 자동 스크롤)
- 상태 뱃지 (대기/빌드 중/성공/실패)
- 실패 시:
  - **AI RCA 리포트** (원인, 영향 파일, 수정 가이드, 신뢰도)
  - **원복 실행 버튼** (확인 다이얼로그 포함)
- 최근 배포 이력 테이블

### 샌드박스 (`/sandbox`)
독립 테스트 환경 관리
- 브랜치 선택 → 샌드박스 생성
- 카드 그리드: 브랜치명, 포트, 상태, 접속 링크
- 삭제 버튼

### 감사 로그 (`/audit`)
전체 이벤트 이력 조회
- 이벤트 타입 필터 (전체/배포/실패/AI 분석/원복)
- 수직 타임라인 (아이콘 + 색상으로 이벤트 구분)
- 항목 클릭 → 상세 모달 (AI 분석 리포트, 메타데이터 JSON)

---

## 9. 핵심 워크플로우

### 배포 → 실패 → AI 분석 → 원복 → 감사기록

```
① 개발자가 [배포] 페이지에서 브랜치 선택 후 "배포 실행" 클릭
                    │
                    ▼
② POST /api/deploy/ → Deployment 생성 (status: BUILDING)
   WebSocket 연결 → 실시간 빌드 로그 스트리밍
                    │
           ┌────────┴────────┐
           ▼                 ▼
   ③-A 빌드 성공         ③-B 빌드 실패 (exit code ≠ 0)
   status → SUCCESS       status → FAILED
   Event: Deployed        │
   Succeeded              ▼
           │         ④ AI가 빌드 로그 자동 분석 (LLM)
           │            - 에러 키워드 주변 컨텍스트 추출
           │            - 원인, 영향 파일, 수정 가이드 도출
           │            Event: DeploymentFailed (with RCA)
           │                    │
           │                    ▼
           │         ⑤ UI에 RCA 리포트 + [원복 실행] 버튼 표시
           │            개발자가 원인 확인 후 원복 결정
           │                    │
           │                    ▼
           │         ⑥ POST /api/rollback/
           │            - git revert로 안정 커밋으로 회귀
           │            - 자동 재배포 트리거
           │            Event: RollbackExecuted
           │                    │
           ▼                    ▼
⑦ 모든 이벤트가 Domain Event Bus를 통해
   Audit Context로 전달 → 해시체인 감사 로그에 영구 저장
```

---

## 10. 설정

### 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `REPO_PATH` | `~/agentic-scm-portal/sample-repo` | Git 리포지토리 경로 |
| `DATABASE_URL` | `sqlite+aiosqlite:///...` | DB 연결 문자열 |
| `LLM_MODE` | `mock` | AI 엔진 모드 (`mock` / `vpc`) |
| `LLM_ENDPOINT` | `http://localhost:11434/...` | VPC LLM 엔드포인트 |
| `SANDBOX_PORT_MIN` | `9100` | 샌드박스 포트 범위 시작 |
| `SANDBOX_PORT_MAX` | `9199` | 샌드박스 포트 범위 끝 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | CORS 허용 오리진 |

### Docker 환경 변수 (docker-compose.yml)
```yaml
REPO_PATH: /repo
DATABASE_URL: sqlite+aiosqlite:////data/audit.db
LLM_MODE: mock
CORS_ORIGINS: '["http://localhost","http://localhost:3000"]'
```

---

## 라이선스

Private Project
