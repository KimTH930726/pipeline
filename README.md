# Agentic SCM & Deployment Portal

> Python AI 서비스 전용 **자율 배포 가드레일 플랫폼**
> GitHub/GitLab 없이 자체 Git 서버로 운영하는 브랜치 관리 + 코드 리뷰 + 배포 + 원복 시스템

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [핵심 워크플로우](#2-핵심-워크플로우)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [기능 상세](#4-기능-상세)
5. [기술 스택](#5-기술-스택)
6. [프로젝트 구조](#6-프로젝트-구조)
7. [설치 및 실행](#7-설치-및-실행)
8. [API 명세](#8-api-명세)
9. [화면 구성](#9-화면-구성)
10. [설정](#10-설정)

---

## 1. 프로젝트 개요

### 배경
8~9명이 협업하는 프로젝트에서 GitHub/GitLab 없이 **자체 Git 서버**로 브랜치 관리부터 배포까지 한 곳에서 처리하는 플랫폼입니다.

### 해결하는 문제
| 문제 | 해결 |
|------|------|
| 중앙 Git 서버 없이 협업 불가 | 서버에 bare repo 구성 + 포탈에서 브랜치 생성/삭제/관리 |
| 배포 전 변경사항 검토 어려움 | 코드 리뷰 페이지에서 diff 확인 + AI 영향도 분석 + 승인/반려 |
| 승인 없는 배포로 인한 사고 | **승인된 브랜치만** 배포 가능 (API 레벨 검증) |
| 배포 실패 시 원인 파악에 시간 소요 | AI(LLM)가 빌드 로그 즉시 분석 → 원인 + 수정 프롬프트 제시 |
| 수동 원복의 위험성 | 원클릭 원복 (git revert -m 1 + 자동 재배포) |
| 배포 이력 추적 어려움 | SHA-256 해시체인 감사 로그 |

---

## 2. 핵심 워크플로우

```
┌─────────────────────────────────────────────────────────────────┐
│                        개발자 워크플로우                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ① 포탈에서 브랜치 생성 (main 기준)                               │
│       │                                                         │
│       ▼                                                         │
│  ② VSCode에서 git checkout → 코드 개발 → git commit/push        │
│       │                                                         │
│       ▼                                                         │
│  ③ 포탈 코드 리뷰에서 diff 확인 + AI 영향도 분석                   │
│       │                                                         │
│       ├── 반려 → 개발자에게 수정 요청 (②로 돌아감)                  │
│       │                                                         │
│       ▼                                                         │
│  ④ 승인 → 배포 페이지에서 변경사항 확인 후 배포 실행                 │
│       │                                                         │
│       ▼                                                         │
│  ⑤ 빌드 검증 → main 자동 머지 → Docker 재빌드/재기동              │
│       │                                                         │
│       ├── 실패 → AI 원인 분석(RCA) + 수정 프롬프트 제시             │
│       │          → 원복 실행 가능                                  │
│       │                                                         │
│       ▼                                                         │
│  ⑥ 배포 완료 → 감사 로그 자동 기록 (해시체인)                      │
│       │                                                         │
│       ▼                                                         │
│  ⑦ 대시보드에서 배포 이력 + 커밋 메시지 확인                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 서버 배포 구조 (운영 환경)
```
[팀원 PC]                    [서버]
  VSCode ──git push──→  bare repo (Git 중앙 저장소)
                              ↑
                         Pipeline 포탈이 읽고 관리
                              │
                              ├── 머지 시 → Docker 재빌드/재기동
                              └── 샌드박스 → 브랜치별 독립 Docker 환경
```

---

## 3. 시스템 아키텍처

### 전체 구조
```
┌─────────────────┐       ┌──────────────────────────────────────────┐
│                 │       │           Backend (FastAPI)               │
│   Frontend      │       │                                          │
│   React SPA     │──────▶│  ┌─────┐ ┌──────┐ ┌────────┐ ┌──────┐ │
│   (Nginx:3000)  │  API  │  │ Git │ │Review│ │Deploy  │ │Analys│ │
│                 │◀──────│  └──┬──┘ └──┬───┘ └──┬─────┘ └──┬───┘ │
│  - Dashboard    │       │     │       │        │           │      │
│  - Branches     │  WS   │     ▼       ▼        ▼           ▼      │
│  - Review       │◀─────▶│  ┌──────────────────────────────────┐  │
│  - Deploy       │       │  │       Domain Event Bus            │  │
│  - Sandbox      │       │  └────────┬──────────┬──────────────┘  │
│  - Audit        │       │           │          │                  │
└─────────────────┘       │  ┌────────┴┐  ┌─────┴──────┐          │
                          │  │Rollback │  │   Audit    │          │
                          │  └─────────┘  │(Hash Chain)│          │
                          │               └─────┬──────┘          │
                          │              ┌──────┴───────┐         │
                          │              │  SQLite DB    │         │
                          │              │ (배포이력,     │         │
                          │              │  리뷰상태,     │         │
                          │              │  감사로그)     │         │
                          │              └──────────────┘         │
                          └──────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│            대상 프로젝트 서버               │
│  ┌──────────┐  ┌──────────┐               │
│  │ Backend  │  │ Frontend │  ← 머지 후    │
│  │ (Docker) │  │ (Docker) │    자동 재빌드 │
│  └──────────┘  └──────────┘               │
│  ┌──────────┐  ┌──────────┐               │
│  │ Postgres │  │  Redis   │  ← 공유 인프라 │
│  └──────────┘  └──────────┘               │
└────────────────────────────────────────────┘
```

### DDD Bounded Contexts (7개)
```
┌──────────┐    ┌──────────┐    ┌──────────┐
│   Git    │───▶│ Analysis │    │ Sandbox  │
│ 브랜치관리│    │ AI 분석   │    │ 테스트환경│
└────┬─────┘    └─────┬────┘    └──────────┘
     │                │
     ▼                ▼
┌──────────┐    ┌──────────┐    domain events
│  Review  │───▶│Deployment│──────────────────┐
│ 코드리뷰  │    │ 배포/빌드 │                   │
└──────────┘    └────┬─────┘                   ▼
                     │                   ┌──────────┐
                     ▼                   │  Audit   │
                ┌──────────┐    ────────▶│ 감사로그  │
                │ Rollback │             │(해시체인) │
                │  원복     │─────────── └──────────┘
                └──────────┘
```

### 레이어 구조 (각 Context 공통)
```
interface/       ← FastAPI Router (HTTP/WS 엔드포인트)
application/     ← Use Case, DTO (오케스트레이션)
domain/          ← Entity, Repository Port, Event, Exception
infrastructure/  ← SQLAlchemy, GitPython, LLM Adapter
```
**의존성 규칙**: `interface → application → domain ← infrastructure`

---

## 4. 기능 상세

### 사용자 인증
- JWT 기반 인증 (access 8시간, refresh 7일)
- 회원가입: 셀프 신청(비활성) → 관리자 승인 → 로그인 가능
- 사용자별 LLM API Key 관리 (Fernet 암호화)
- 비밀번호 변경 (설정 페이지)
- 역할: admin / user

### 브랜치 관리
- 기준 브랜치 선택 → 새 브랜치 생성 / 삭제 (main 삭제 방지)

### 코드 리뷰
- 변경 파일 목록 + Unified Diff 뷰어
- **AI 영향도 분석** / **AI 코드 리뷰** (별도 버튼, 마크다운 렌더링)
- 승인/반려 + 수행자(acted_by) 기록

### 배포
- 승인된 브랜치만 배포 (인증 + API 레벨 검증)
- 머지 충돌 자동 감지 → AI 해결안 → 사용자 승인 후 머지
- 빌드 → main 머지 → Docker 재기동 + 실시간 로그(WebSocket)
- 배포 이력 페이징 + 토글 상세 + 수행자 표시
- 배포 비교: 2개 선택 → diff

### AI 실패 분석 (RCA)
- 빌드 로그 → LLM 분석 → 원인/수정가이드/AI 수정 프롬프트(클립보드 복사)

### 원복
- 성공/실패 모두 원복 가능, `git revert -m 1`, 중복 방지

### 샌드박스
- 브랜치별 Docker 환경 (backend+frontend, 포트 9100~9199, main 제외)

### 감사 로그
- 배포/실패/원복 자동 기록, SHA-256 해시체인, 브랜치/이벤트 필터, 페이징

### 대시보드
- 통계 카드 + main 배포 이력(수행자, 커밋 메시지) + 토글 상세

### 공통
- 탭 포커스 시 자동 데이터 리로드 (전 페이지)

---

## 5. 기술 스택

### Backend
| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11 | 런타임 |
| FastAPI | ≥0.115 | 웹 프레임워크 (async) |
| SQLAlchemy | ≥2.0 | ORM (async) |
| aiosqlite | ≥0.20 | 비동기 SQLite |
| GitPython | ≥3.1.40 | Git 조작 (싱글턴) |
| httpx | ≥0.27 | 비동기 HTTP (LLM 호출) |
| Pydantic | v2 | 데이터 검증 + field_validator |

### Frontend
| 기술 | 버전 | 용도 |
|------|------|------|
| React | 19.x | UI |
| TypeScript | 5.9 | 타입 안전성 |
| Vite | 8.x | 빌드 |
| Tailwind CSS | 4.x | 스타일링 |
| Zustand | 5.x | 상태 관리 (배포 상태, 빌드 로그) |
| Axios | 1.x | HTTP 클라이언트 |

### Infrastructure
| 기술 | 용도 |
|------|------|
| Docker + Docker Compose | 컨테이너화 |
| Nginx | 프론트엔드 서빙 + API 리버스 프록시 |
| SQLite | 배포 이력, 리뷰 상태, 감사 로그 저장 |

---

## 6. 프로젝트 구조

```
pipeline/
├── backend/
│   ├── Dockerfile              # Python 3.11 + Git + Docker CLI
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI 앱 + 이벤트 버스 연결
│       ├── config.py           # 환경 설정 (배포 대상 경로 포함)
│       ├── shared/             # 공유 커널 (DB, EventBus, Exceptions)
│       ├── git/                # 브랜치 CRUD, diff, merge, revert
│       ├── review/             # 코드 리뷰 승인/반려
│       ├── deployment/         # 배포 파이프라인 (빌드→머지→Docker)
│       ├── analysis/           # AI 영향도 분석 + RCA
│       ├── rollback/           # 원복 (git revert + 재배포)
│       ├── sandbox/            # 브랜치별 Docker 샌드박스
│       └── audit/              # 해시체인 감사 로그
├── frontend/
│   ├── Dockerfile              # Node 빌드 → Nginx
│   ├── nginx.conf              # API 프록시 + WebSocket
│   └── src/
│       ├── pages/              # Dashboard, Branch, Review, Deploy, Sandbox, Audit
│       ├── components/         # UI 컴포넌트
│       ├── api/                # API 클라이언트 (deploy, git, review, audit)
│       ├── hooks/              # WebSocket 훅
│       ├── store/              # Zustand (배포 상태)
│       └── types/              # TypeScript 타입
├── docker-compose.yml          # 포탈 실행 + 배포 대상 가이드
└── Makefile
```

---

## 7. 설치 및 실행

### Docker (권장)
```bash
docker compose up -d --build

# 접속
# Frontend: http://localhost:3000
# Backend:  http://localhost:8080
# API Docs: http://localhost:8080/docs
```

### 로컬 개발
```bash
make install    # pip + npm install
make dev        # backend + frontend 동시 실행
```

### 대상 프로젝트 연결
`docker-compose.yml`에서 볼륨과 환경변수를 설정합니다:
```yaml
volumes:
  - /path/to/your-project:/repo          # Git 레포
  - /path/to/your-project:/deploy-target  # 배포 대상
environment:
  - REPO_PATH=/repo
  - DEPLOY_TARGET_PATH=/deploy-target
```

---

## 8. API 명세

### Git
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/git/branches` | 브랜치 목록 |
| `POST` | `/api/git/branches` | 브랜치 생성 `{new_branch, base_branch}` |
| `DELETE` | `/api/git/branches/{name}` | 브랜치 삭제 |
| `GET` | `/api/git/branches/files?branch=` | 변경 파일 목록 |
| `GET` | `/api/git/diff?branch=&path=` | 파일 Diff |

### Review
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/review/approve` | 브랜치 승인 |
| `POST` | `/api/review/reject` | 브랜치 반려 |
| `GET` | `/api/review/status/{branch}` | 리뷰 상태 |
| `GET` | `/api/review/approved` | 승인된 브랜치 목록 |

### Deploy
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/deploy/` | 배포 실행 (승인 필수) |
| `GET` | `/api/deploy/status/{id}` | 배포 상세 (빌드로그 포함) |
| `GET` | `/api/deploy/recent?page=&size=` | 배포 이력 (페이징) |
| `POST` | `/api/deploy/status/{id}/rolled-back` | 원복 표시 |
| `GET` | `/api/deploy/compare/{id_from}/{id_to}` | 배포 간 diff 비교 |
| `WS` | `/api/deploy/ws/{id}` | 실시간 빌드 로그 |

### Auth
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/auth/login` | 로그인 → JWT 토큰 |
| `POST` | `/api/auth/signup` | 회원가입 (관리자 승인 필요) |
| `POST` | `/api/auth/refresh` | 토큰 갱신 |
| `GET` | `/api/auth/me` | 내 정보 |
| `PUT` | `/api/auth/me/password` | 비밀번호 변경 |
| `PUT` | `/api/auth/me/api-key` | LLM API Key 등록/변경 |
| `GET` | `/api/auth/users` | 사용자 목록 (admin) |
| `PUT` | `/api/auth/users/{id}/activate\|deactivate` | 승인/비활성 (admin) |

### Analysis / Rollback / Sandbox / Audit
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/analysis/impact` | AI 영향도 분석 |
| `POST` | `/api/analysis/review` | AI 코드 리뷰 |
| `POST` | `/api/analysis/conflicts` | 머지 충돌 감지 + AI 해결 |
| `POST` | `/api/analysis/conflicts/apply` | 충돌 해결안 적용 |
| `POST` | `/api/analysis/rca` | AI 실패 분석 |
| `POST` | `/api/rollback/` | 원복 실행 |
| `POST` | `/api/sandbox/` | 샌드박스 생성 |
| `DELETE` | `/api/sandbox/{id}` | 샌드박스 삭제 |
| `GET` | `/api/audit/timeline` | 감사 로그 (필터, 페이징) |

---

## 9. 화면 구성

| 페이지 | 경로 | 설명 |
|--------|------|------|
| **로그인** | `/login` | JWT 인증 |
| **회원가입** | `/signup` | 셀프 신청 (관리자 승인 대기) |
| **대시보드** | `/` | main 배포 이력 + 수행자 + 커밋 메시지 |
| **브랜치 관리** | `/branches` | 생성/삭제/목록 |
| **코드 리뷰** | `/review` | diff + AI 영향도/코드리뷰 + 승인/반려 |
| **배포** | `/deploy` | 배포 + 충돌 해결 + 이력 비교 + 원복 |
| **샌드박스** | `/sandbox` | 브랜치별 Docker 환경 |
| **감사 로그** | `/audit` | 이벤트 타임라인 (필터, 페이징) |
| **설정** | `/settings` | 비밀번호 변경 + API Key 관리 |
| **사용자 관리** | `/admin` | 승인/비활성화/등록 (admin만) |

---

## 10. 설정

### 환경 변수 (.env로 관리)
| 변수 | 설명 |
|------|------|
| `REPO_PATH` | Git 레포 경로 |
| `DATABASE_URL` | SQLite 경로 |
| `LLM_ENDPOINT` | DevX MCP API URL |
| `LLM_API_KEY` | 시스템 LLM Key (사용자 키 없을 때 fallback) |
| `JWT_SECRET_KEY` | JWT 서명 키 |
| `FERNET_SECRET_KEY` | API Key 암호화 키 |
| `ADMIN_DEFAULT_PASSWORD` | 초기 admin 비밀번호 (기본: admin1234) |
| `DEPLOY_TARGET_PATH` | 배포 대상 docker-compose 경로 |
| `DEPLOY_COMPOSE_FILE` | compose 파일명 |

---

## 라이선스

Private Project
