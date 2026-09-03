"""BelleApp: нет хардкод-списка, health по is_system с ФС."""
from __future__ import annotations

from types import SimpleNamespace

import app as app_mod
from app import BelleApp
from modules_system.module_base import ModuleMeta


def test_required_modules_removed() -> None:
    assert not hasattr(app_mod, "_REQUIRED_MODULES")


def test_health_uses_fs_system_modules(monkeypatch) -> None:
    belle = BelleApp.__new__(BelleApp)
    belle._config = SimpleNamespace()
    metas = {
        "log": ModuleMeta(is_system=True, load_on="all"),
        "auth": ModuleMeta(is_system=True, load_on="all"),
        "workspace": ModuleMeta(is_system=False, load_on="all"),
        "apiproxy": ModuleMeta(is_system=True, load_on="api"),
        "worker": ModuleMeta(is_system=True, load_on="worker"),
        "sample": ModuleMeta(is_system=False, is_example=True),
    }
    modules = SimpleNamespace(
        discover=lambda: list(metas),
        read_meta=lambda name: metas[name],
        list_all=lambda: ["log", "auth", "workspace", "apiproxy"],
    )
    belle._app = SimpleNamespace(modules=modules)
    belle._loaded_modules = ["log", "auth", "workspace", "apiproxy"]
    belle._runtime_registry = None
    assert belle.is_healthy() is True

    belle._loaded_modules = ["log", "auth", "workspace"]
    assert belle.is_healthy() is False
