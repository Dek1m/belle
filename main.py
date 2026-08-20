"""Belle entry point.

Starts BelleApp + HTTP health server.
Run: python main.py (requires PYTHONPATH=/app/mia:/app)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# В контейнере конфиги монтируются в /etc/belle — импортируем config оттуда
# (хостовый config.py имеет приоритет над версией из образа).
_ETC_BELLE = "/etc/belle"
if os.path.isdir(_ETC_BELLE) and _ETC_BELLE not in sys.path:
    sys.path.insert(0, _ETC_BELLE)

try:
    from argenta_logging import setup_logging
except ImportError:
    setup_logging = None  # type: ignore[assignment]

from app import BelleApp  # noqa: E402
from config import BelleConfig  # noqa: E402

logger = logging.getLogger(__name__)

# HTTP response constants
_RESPONSE_OK = 200
_RESPONSE_UNHEALTHY = 503
_RESPONSE_NOT_FOUND = 404
_CONTENT_TYPE_JSON = "application/json"


class _HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for healthcheck endpoint."""

    # Injected via class attribute (shared across handler instances)
    belle_app: BelleApp

    def do_GET(self) -> None:
        if self.path == "/health":
            body = self.belle_app.health()
            code = _RESPONSE_OK if body.get("status") == "ok" else _RESPONSE_UNHEALTHY
            self._send_json(code, body)
        else:
            self._send_json(_RESPONSE_NOT_FOUND, {"error": "not found"})

    def _send_json(self, code: int, body: dict[str, object]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", _CONTENT_TYPE_JSON)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Suppress per-request logging for healthcheck."""
        pass


def _run_server(app: BelleApp, port: int) -> ThreadingHTTPServer:
    """Create and start HTTP server."""
    handler_class = type(
        "Handler",
        (_HealthHandler,),
        {"belle_app": app},
    )
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_class)
    server.daemon_threads = True
    logger.info("Health server listening on :%d", port)
    return server


def main() -> None:
    """Config -> app -> server -> wait for signal."""
    config = BelleConfig.from_env()

    # Чтобы mia LogModule не перетёр имя сервиса и уровень
    os.environ.setdefault("SERVICE_NAME", "belle")
    os.environ.setdefault("MIA_LOG_LEVEL", config.log_level)

    # Используем argenta_logging для стандартизированного формата [ISO8601-UTC] [LEVEL] [service] message
    if setup_logging is not None:
        setup_logging(service="belle", level=config.log_level)
    else:
        # Fallback: пакет не установлен (локальная разработка)
        logging.basicConfig(
            level=getattr(logging, config.log_level.upper(), logging.INFO),
            format="[%(asctime)s] [%(levelname)s] [belle] %(message)s",
        )

    app = BelleApp(config)

    try:
        app.start()
    except Exception:
        logger.exception("Failed to start belle")
        sys.exit(1)

    server = _run_server(app, config.health_port)

    # Graceful shutdown on SIGINT/SIGTERM
    def _shutdown(sig: int, frame: object) -> None:
        signame = signal.Signals(sig).name
        logger.info("Received %s, shutting down...", signame)
        server.shutdown()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Block in serve_forever — wait for signals
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
        logger.info("Bye.")


if __name__ == "__main__":
    main()
