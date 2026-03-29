# Agentic SCM & Deployment Portal

## Project Overview
Python AI 서비스 전용 자율 배포 가드레일 플랫폼.
"투명한 배포와 지능형 복구" - AI가 배포 전/후를 감시하여 실패 시 원인 분석과 원복을 동시에 처리.

## Tech Stack
- **Frontend**: React + TypeScript, Tailwind CSS, Vite
- **Backend**: Python FastAPI
- **SCM**: GitPython
- **AI Engine**: Internal LLM (VPC 격리, 개발 시 Mock)
- **Database**: SQLite (aiosqlite + SQLAlchemy async)

## Commands
- `make backend` - Run backend dev server (uvicorn --reload)
- `make frontend` - Run frontend dev server (vite)
- `make dev` - Run both concurrently

## Architecture
- Backend: Router → Service → Model (3-layer)
- Real-time: WebSocket for build log streaming
- Audit: Hash-chained immutable log
