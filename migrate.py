"""One-shot накат системных схем. Не воркер и не API.

Run: python migrate.py (PYTHONPATH=/app/mia:/app, MIA_DISPATCH=local)
Lock: pg_advisory_lock на admin-DSN к целевой БД (postgres:5432), не через pgbouncer.
"""
from __future__ import annotations

import logging
import os
import sys

_ETC_BELLE = "/etc/belle"
if os.path.isdir(_ETC_BELLE) and _ETC_BELLE not in sys.path:
    sys.path.insert(0, _ETC_BELLE)

try:
    from argenta_logging import setup_logging
except ImportError:
    setup_logging = None

from core.application import Application
from modules.db.config import DatabaseConfig

from config import BelleConfig

log = logging.getLogger("migrate")

_LOCK_KEY = "mia.schema.system"
# rest — HTTP binder, apiproxy — API binder, worker — celery. Не грузить в migrate.
_BINDERS = frozenset({"rest", "apiproxy", "worker"})


def schema_modules(registry: object) -> list[str]:
    """discover+topo: ядро схем. Без example, без HTTP/celery binder."""
    discover = getattr(registry, "discover_and_sort")
    read_meta = getattr(registry, "read_meta")
    names: list[str] = []
    for name in discover():
        if name in _BINDERS:
            continue
        meta = read_meta(name)
        if getattr(meta, "is_example", False):
            continue
        names.append(name)
    return names


def _lock_conn(cfg: DatabaseConfig):
    from psycopg import connect

    dsn = cfg.get_admin_dsn(cfg.database)
    conn = connect(dsn, autocommit=True)
    conn.execute("SELECT pg_advisory_lock(hashtext(%s))", (_LOCK_KEY,))
    log.info("schema_lock_acquired", extra={"key": _LOCK_KEY, "dbname": cfg.database})
    return conn


def _unlock(conn: object) -> None:
    try:
        conn.execute("SELECT pg_advisory_unlock(hashtext(%s))", (_LOCK_KEY,))  # type: ignore[union-attr]
        log.info("schema_lock_released", extra={"key": _LOCK_KEY})
    finally:
        close = getattr(conn, "close", None)
        if callable(close):
            close()


def main() -> None:
    os.environ.setdefault("MIA_DISPATCH", "local")
    os.environ.setdefault("SERVICE_NAME", "belle-migrate")
    belle_cfg = BelleConfig.from_env()
    if setup_logging is not None:
        setup_logging(service="belle-migrate", level=belle_cfg.log_level)
    else:
        logging.basicConfig(level=logging.INFO)

    db_cfg = DatabaseConfig.from_env()
    app = Application(modules_dir=belle_cfg.modules_dir)
    app.startup()
    names = schema_modules(app.modules)
    log.info(
        "migrate_start",
        extra={"modules": names, "database": db_cfg.database},
    )
    for name in names:
        app.load_module(name)

    conn = _lock_conn(db_cfg)
    try:
        app.apply_schemas()
    finally:
        _unlock(conn)
        app.shutdown()

    log.info("migrate_done")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("migrate_failed")
        sys.exit(1)
