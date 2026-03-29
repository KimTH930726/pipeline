from __future__ import annotations

from pydantic import BaseModel


class SandboxCreateDTO(BaseModel):
    branch: str


class SandboxResponseDTO(BaseModel):
    id: int
    branch: str
    port: int
    status: str
