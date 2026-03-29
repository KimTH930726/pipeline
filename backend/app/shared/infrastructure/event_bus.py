from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Type

from app.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class InMemoryEventBus:
    """Async in-process event bus for domain event pub/sub."""

    def __init__(self) -> None:
        self._handlers: dict[Type[DomainEvent], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.error(
                    "Event handler %s failed for %s: %s",
                    handler.__name__ if hasattr(handler, "__name__") else handler,
                    type(event).__name__,
                    exc,
                )

    async def publish_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
