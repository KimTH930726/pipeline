from __future__ import annotations

from pydantic import BaseModel


class SandboxCreateDTO(BaseModel):
    branch: str


class SandboxResponseDTO(BaseModel):
    id: int
    branch: str
    backend_port: int
    frontend_port: int
    status: str
    error_log: str = ""
