"""Belle application core.

Wraps mia Application: loads modules, exposes health status.
"""

from __future__ import annotations

import logging
import os
from core.application import Application

from config import BelleConfig

logger = logging.getLogger(__name__)

__version__ = "0.1.0"

# Modules loaded at startup
_REQUIRED_MODULES: tuple[str, ...] = (
    "log", "db", "auth", "workspace", "llm", "admin", "apiproxy", "rest",
)


class BelleApp:
    """Main application class.

    Manages mia Application lifecycle and loaded modules.
    """

    def __init__(self, config: BelleConfig | None = None) -> None:
        self._config = config or BelleConfig.from_env()
        self._app: Application | None = None
        self._loaded_modules: list[str] = []

    # -- lifecycle --

    def start(self) -> None:
        """Init: Application -> startup -> load modules."""
        logger.info("belle_starting", extra={"version": __version__})

        self._app = Application(modules_dir=self._config.modules_dir)
        self._app.startup()

        for module_name in _REQUIRED_MODULES:
            try:
                self._app.load_module(module_name)
                self._loaded_modules.append(module_name)
            except Exception:
                logger.exception(
                    "module_load_failed", extra={"module_name": module_name},
                )
                raise

        if os.environ.get("MIA_SCHEMA_APPLY", "").strip().lower() == "on_start":
            logger.warning("schema_apply_on_start")
            self._app.apply_schemas()

        logger.info("belle_started", extra={"modules": list(self._loaded_modules)})

    def stop(self) -> None:
        """Graceful shutdown."""
        if self._app is None:
            return
        logger.info("belle_shutting_down")
        self._app.shutdown()
        self._app = None
        self._loaded_modules.clear()
        logger.info("belle_stopped")

    # -- health --

    def health(self) -> dict[str, object]:
        """Current status for healthcheck."""
        ok = self.is_healthy()
        return {
            "status": "ok" if ok else "unhealthy",
            "version": __version__,
            "modules": list(self._loaded_modules),
        }

    def is_healthy(self) -> bool:
        """True if app is running and all modules loaded."""
        return (
            self._app is not None
            and len(self._loaded_modules) == len(_REQUIRED_MODULES)
        )

    # -- access --

    @property
    def app(self) -> Application | None:
        """Direct access to mia Application."""
        return self._app

    @property
    def config(self) -> BelleConfig:
        return self._config
