from __future__ import annotations

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Agentic SCM Portal"
    REPO_PATH: str = str(Path.home() / "agentic-scm-portal" / "sample-repo")
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path.home() / 'agentic-scm-portal' / 'data' / 'audit.db'}"
    # === LLM (DevX Gateway, client_credentials OAuth2 + SSE streaming) ===
    LLM_MODE: str = "inhouse"
    LLM_AUTH_ENDPOINT: str = "https://devx-gw.shinsegae-inc.com/api/v1/auth/token"
    LLM_CHAT_ENDPOINT: str = "https://devx-gw.shinsegae-inc.com/api/v1/agent/chat"
    LLM_CLIENT_ID: str = ""
    LLM_CLIENT_SECRET: str = ""
    LLM_AGENT_CODE: str = "playground"
    LLM_AGENT_ID: str = "b6958377-73f2-4234-a49c-2aa878350a2e"
    SANDBOX_PORT_MIN: int = 9100
    SANDBOX_PORT_MAX: int = 9199
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # === 인증 설정 ===
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FERNET_SECRET_KEY: str = ""
    ADMIN_DEFAULT_PASSWORD: str = "admin1234"
    GIT_CLONE_URL: str = ""  # 팀원용 clone URL (예: ssh://user@서버IP/srv/repos/SMAgentLab.git)

    # === 배포 대상 설정 ===
    # DEPLOY_TARGET_PATH: 배포 대상 프로젝트의 docker-compose.yml이 있는 경로
    # 예: /home/deploy/SMAgentLab 또는 D:/projects/SMAgentLab
    # DEPLOY_TARGET_PATH: 호스트 절대 경로 (볼륨 마운트, docker compose 실행 시 사용)
    DEPLOY_TARGET_PATH: str = ""
    # DEPLOY_COMPOSE_PATH: 컨테이너 내부 경로 (compose 파일 읽기용)
    DEPLOY_COMPOSE_PATH: str = "/deploy-target"
    DEPLOY_COMPOSE_FILE: str = "docker-compose.yml"
    # 추가 compose 오버라이드 (콤마 구분, 폐쇄망 prod 환경: docker-compose.prod.yml)
    DEPLOY_COMPOSE_OVERRIDES: str = ""
    DEPLOY_SERVICE_NAME: str = "backend frontend"
    DEPLOY_MODE: str = "restart"
    DEPLOY_COMPOSE_PROJECT: str = "smagentlab"
    SANDBOX_HOST_PATH: str = "/tmp/pipeline-sandboxes"
    SANDBOX_CONTAINER_PATH: str = "/sandboxes"

    class Config:
        env_file = ".env"


settings = Settings()
