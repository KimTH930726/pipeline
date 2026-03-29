from __future__ import annotations

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Agentic SCM Portal"
    REPO_PATH: str = str(Path.home() / "agentic-scm-portal" / "sample-repo")
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path.home() / 'agentic-scm-portal' / 'data' / 'audit.db'}"
    LLM_MODE: str = "mock"  # mock | vpc
    LLM_ENDPOINT: str = "http://localhost:11434/api/generate"
    SANDBOX_PORT_MIN: int = 9100
    SANDBOX_PORT_MAX: int = 9199
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
