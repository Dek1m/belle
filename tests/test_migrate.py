"""ADR-005 шаг 8: migrate без кортежа _MODULES."""
from __future__ import annotations

from types import SimpleNamespace

import migrate as migrate_mod
from modules_system.module_base import ModuleMeta


def test_modules_tuple_removed() -> None:
    assert not hasattr(migrate_mod, "_MODULES")


def test_schema_modules_skips_binders_and_examples() -> None:
    order = ["log", "db", "auth", "apiproxy", "rest", "worker", "fs", "sample", "system"]
    metas = {
        "log": ModuleMeta(is_example=False),
        "db": ModuleMeta(is_example=False),
        "auth": ModuleMeta(is_example=False),
        "apiproxy": ModuleMeta(load_on="api", is_system=True),
        "rest": ModuleMeta(load_on="api", is_system=True),
        "worker": ModuleMeta(load_on="worker", is_system=True),
        "fs": ModuleMeta(is_example=False),
        "sample": ModuleMeta(is_example=True),
        "system": ModuleMeta(is_example=False),
    }
    registry = SimpleNamespace(
        discover_and_sort=lambda: list(order),
        read_meta=lambda name: metas[name],
    )
    names = migrate_mod.schema_modules(registry)
    assert names == ["log", "db", "auth", "fs", "system"]
    assert "rest" not in names
    assert "apiproxy" not in names
    assert "worker" not in names
    assert "sample" not in names
    assert names.index("auth") < names.index("system")
    assert names.index("auth") < names.index("fs")
