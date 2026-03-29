from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    DEPLOY = "DEPLOY"
    FAILURE = "FAILURE"
    RCA = "RCA"
    ROLLBACK = "ROLLBACK"
    SANDBOX_CREATED = "SANDBOX_CREATED"
    SANDBOX_DESTROYED = "SANDBOX_DESTROYED"


@dataclass(frozen=True)
class BranchName:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Branch name cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CommitSha:
    value: str

    def __post_init__(self) -> None:
        if self.value and not re.match(r"^[0-9a-f]{7,40}$", self.value):
            raise ValueError(f"Invalid commit SHA: {self.value}")

    @property
    def short(self) -> str:
        return self.value[:8]

    def __str__(self) -> str:
        return self.value
