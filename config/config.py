"""Belle configuration.

Reads from:
1. ENV variables (highest priority)
2. belle.conf next to this file (KEY=VALUE)
3. Defaults

В контейнере файл монтируется в /etc/belle/config.py — правки на хосте
подхватываются без пересборки образа (конфиг как код).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["BelleConfig"]


def _load_conf_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE file. Lines without '=' and comments (#) are skipped."""
    if not path.is_file():
        return {}
    config: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        config[key.strip()] = value.strip()
    return config


@dataclass(frozen=True)
class BelleConfig:
    """Application configuration.

    Priority: ENV > belle.conf (рядом с этим файлом) > defaults.
    """

    health_port: int
    modules_dir: str
    log_level: str

    @classmethod
    def from_env(cls, conf_path: Path | None = None) -> BelleConfig:
        """Create config: file first, then ENV overrides.

        conf_path по умолчанию — belle.conf рядом с этим файлом
        (/etc/belle/belle.conf в контейнере, config/belle.conf в репозитории).
        """
        conf_path = conf_path or Path(__file__).resolve().parent / "belle.conf"
        file_config = _load_conf_file(conf_path)

        def _get(env_key: str, default: str) -> str:
            """ENV has priority over file."""
            return os.environ.get(env_key, file_config.get(env_key, default))

        return cls(
            health_port=int(_get("BELLE_HEALTH_PORT", "8000")),
            modules_dir=_get("BELLE_MODULES_DIR", "mia/modules"),
            log_level=_get("LOG_LEVEL", "INFO"),
        )