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


def allocate_port(used_ports: set[int]) -> int:
    """Find the lowest free port in the configured range."""
    for port in range(settings.SANDBOX_PORT_MIN, settings.SANDBOX_PORT_MAX + 1):
        if port not in used_ports and _is_port_free(port):
            return port
    raise NoAvailablePorts()
