from __future__ import annotations

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Agentic SCM Portal"
    REPO_PATH: str = str(Path.home() / "agentic-scm-portal" / "sample-repo")
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path.home() / 'agentic-scm-portal' / 'data' / 'audit.db'}"
    LLM_MODE: str = "inhouse"
    LLM_ENDPOINT: str = "https://devx-mcp-api.shinsegae-inc.com/api/v1/mcp-command/chat"
    LLM_API_KEY: str = ""
    LLM_USECASE_CODE: str = "playground"
    LLM_USECASE_ID: str = "b6958377-73f2-4234-a49c-2aa878350a2e"
    LLM_PROJECT_ID: str = "eb01fb40-909b-4a0a-b86e-824c6a3bea2e"
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
    DEPLOY_TARGET_PATH: str = ""
    DEPLOY_COMPOSE_FILE: str = "docker-compose.yml"
    DEPLOY_SERVICE_NAME: str = ""
    # DEPLOY_MODE: build (인터넷 환경) / restart (폐쇄망 - 소스 볼륨 마운트)
    DEPLOY_MODE: str = "restart"

    class Config:
        env_file = ".env"


settings = Settings()
