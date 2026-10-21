"""Fixtures for the recovery suite that need the real, migrated schema.

Most of this directory drives the recovery tooling through fakes. The schema-coverage guard
(`RECOVERY-REBASE-01`) cannot: its whole point is to compare the tooling's declared view of
the schema with the schema the migrations actually build, so it needs a real PostgreSQL
database migrated to head by the literal command. The fixtures are the ones
``tests/integration/db/conftest.py`` defines (a session-local migrated template, one fresh
clone per consumer, dropped afterwards); this file only re-exports them, the way
``tests/integration/optimisation/conftest.py`` does. A missing ``DATABASE_URL`` fails; nothing
here skips itself. The seed test also needs the lane's ``S3_*`` names, read from ``.env`` the same way.
"""

from __future__ import annotations

import os
from pathlib import Path

from auditmanager.storage.settings import REQUIRED_VARS
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    empty_database,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _load_lane_environment_if_needed() -> None:
    """Fill missing ``DATABASE_URL`` and ``S3_*`` names from the worktree's ``.env`` (data)."""
    wanted = (*REQUIRED_VARS, "DATABASE_URL")
    if all(os.environ.get(name) for name in wanted):
        return
    dotenv = _REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or name not in wanted or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


_load_lane_environment_if_needed()
