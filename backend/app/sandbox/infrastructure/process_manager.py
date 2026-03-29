from __future__ import annotations

import asyncio
import os
import signal
import logging

logger = logging.getLogger(__name__)


class SandboxProcessManager:
    """Manages sandbox subprocess lifecycle."""

    @staticmethod
    async def start(port: int) -> int | None:
        """Start a sandbox HTTP server, return PID."""
        try:
            process = await asyncio.create_subprocess_exec(
                "python3", "-c",
                f"""
import http.server, socketserver
PORT = {port}
handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Sandbox running on port {{PORT}}")
    httpd.serve_forever()
""",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            return process.pid
        except Exception:
            logger.exception("Failed to start sandbox on port %s", port)
            return None

    @staticmethod
    def stop(pid: int) -> None:
        """Stop a sandbox process by PID."""
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception:
            logger.exception("Failed to stop sandbox process %s", pid)
