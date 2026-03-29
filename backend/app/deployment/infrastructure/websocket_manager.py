from __future__ import annotations

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per deployment for real-time log streaming."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, deployment_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(deployment_id, []).append(websocket)

    def disconnect(self, deployment_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(deployment_id)
        if conns:
            conns.remove(websocket)
            if not conns:
                del self._connections[deployment_id]

    async def broadcast(self, deployment_id: str, message: dict) -> None:
        conns = self._connections.get(deployment_id, [])
        if not conns:
            return
        data = json.dumps(message, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)


ws_manager = ConnectionManager()
