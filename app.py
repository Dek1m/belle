"""Belle application core.

Wraps mia Application: loads modules, exposes health status.
"""

from __future__ import annotations

import logging
import os

from core.application import Application
from modules_system.module_base import should_load
from modules_system.runtime_registry import ModuleRuntimeRegistry

from config import BelleConfig

logger = logging.getLogger(__name__)

__version__ = "0.1.0"

_API_ROLE = "api"


class BelleApp:
    """Main application class.

    Manages mia Application lifecycle and loaded modules.
    """

    def __init__(self, config: BelleConfig | None = None) -> None:
        self._config = config or BelleConfig.from_env()
        self._app: Application | None = None
        self._loaded_modules: list[str] = []
        self._runtime_registry: ModuleRuntimeRegistry | None = None

    def start(self) -> None:
        """Init: Application -> startup -> load_all_modules(role=api) -> registry."""
        logger.info("belle_starting", extra={"version": __version__})

        self._app = Application(modules_dir=self._config.modules_dir)
        self._app.startup()

        registry = ModuleRuntimeRegistry.from_env("belle")
        self._runtime_registry = registry
        self._app.set_runtime_registry(registry)
        self._app.load_all_modules(role=_API_ROLE)
        self._loaded_modules = list(self._app.modules.list_all())
        self._app.publish_runtime()
        registry.start_heartbeat_loop()

        if os.environ.get("MIA_SCHEMA_APPLY", "").strip().lower() == "on_start":
            logger.warning("schema_apply_on_start")
            self._app.apply_schemas()

        logger.info("belle_started", extra={"modules": list(self._loaded_modules)})

    def stop(self) -> None:
        """Graceful shutdown."""
        if self._runtime_registry is not None:
            self._runtime_registry.stop_heartbeat_loop()
            self._runtime_registry = None
        if self._app is None:
            return
        logger.info("belle_shutting_down")
        self._app.shutdown()
        self._app = None
        self._loaded_modules.clear()
        logger.info("belle_stopped")

    def health(self) -> dict[str, object]:
        """Current status for healthcheck."""
        ok = self.is_healthy()
        return {
            "status": "ok" if ok else "unhealthy",
            "version": __version__,
            "modules": list(self._loaded_modules),
        }

    def is_healthy(self) -> bool:
        """Ядро с ФС loaded. Продукт fail не валит health."""
        if self._app is None:
            return False
        loaded = set(self._loaded_modules)
        discover = getattr(self._app.modules, "discover", None)
        read_meta = getattr(self._app.modules, "read_meta", None)
        if not callable(discover) or not callable(read_meta):
            return bool(loaded)
        for name in discover():
            meta = read_meta(name)
            if not getattr(meta, "is_system", False):
                continue
            if not should_load(meta, _API_ROLE):
                continue
            if name not in loaded:
                return False
        return True

    @property
    def app(self) -> Application | None:
        """Direct access to mia Application."""
        return self._app

    @property
    def config(self) -> BelleConfig:
        return self._config
