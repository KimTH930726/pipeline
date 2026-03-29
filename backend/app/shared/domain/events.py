from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import uuid4


@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: uuid4().hex, init=False)
    occurred_at: datetime = field(default_factory=datetime.utcnow, init=False)


class EventHandler(Protocol):
    async def __call__(self, event: DomainEvent) -> None: ...
