from __future__ import annotations

import socket

from app.config import settings
from app.sandbox.domain.exceptions import NoAvailablePorts


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False


def allocate_port_pair(used_ports: set[int]) -> tuple[int, int]:
    """Find two consecutive free ports: (backend_port, frontend_port)."""
    start = settings.SANDBOX_PORT_MIN
    end = settings.SANDBOX_PORT_MAX

    for port in range(start, end, 2):
        backend_port = port
        frontend_port = port + 1
        if (
            backend_port not in used_ports
            and frontend_port not in used_ports
            and _is_port_free(backend_port)
            and _is_port_free(frontend_port)
        ):
            return backend_port, frontend_port

    raise NoAvailablePorts()
