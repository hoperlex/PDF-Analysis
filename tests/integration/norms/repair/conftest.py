"""Fixtures for the durable repair suite. **No test here can reach a provider.**

`W54-REPAIR-01` has one hard rule: zero live provider calls. :func:`_no_network` is autouse:
it replaces ``urllib.request.urlopen`` and Python's socket connect for every test in this
directory, so a code path that tried to open a connection fails loudly instead of paying.
(PostgreSQL is reached through libpq, which does not use Python sockets, so the database
cases are unaffected.) ``test_the_suite_cannot_open_a_connection`` proves the guard bites.

The runner is exercised against two stores. ``memory`` mirrors ``trg_norm_repair_call_guard``
(`0018`) and runs container-free; ``postgres`` is the real ``SqlCallStore`` on a throwaway
database migrated to head, a heavy step for the owner's window (it fails, never skips,
without ``DATABASE_URL``). Select with ``-k memory`` or ``-k postgres``.
"""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.integration.norms.repair.support import (
    REPOSITORY_ROOT,
    Kit,
    LiveCallAttempted,
    MemoryStore,
    PostgresStore,
    ScriptedTransport,
    _load_dotenv_if_needed,
)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise LiveCallAttempted("a test in the repair suite tried to open a network connection")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture(scope="session")
def repair_database() -> Iterator[Any]:
    from sqlalchemy import text

    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    _load_dotenv_if_needed()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set; the postgres repair cases need a real PostgreSQL.")
    configured = DatabaseSettings(url=parse_database_url(raw))
    maintenance = create_database_engine(
        DatabaseSettings(url=configured.url.set(database="postgres"))
    ).execution_options(isolation_level="AUTOCOMMIT")
    name = f"w54_repair_{secrets.token_hex(6)}"
    try:
        with maintenance.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        settings = DatabaseSettings(url=configured.url.set(database=name))
        environment = dict(os.environ)
        environment["PYTHONPATH"] = "src"
        environment["DATABASE_URL"] = settings.url.render_as_string(hide_password=False)
        completed = subprocess.run(
            [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini",
             "upgrade", "head"],
            cwd=REPOSITORY_ROOT, env=environment, capture_output=True, text=True, timeout=300,
            check=False,
        )
        if completed.returncode != 0:
            pytest.fail(f"could not apply the migration head:\n{completed.stdout}\n{completed.stderr}")
        yield settings
    finally:
        with maintenance.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        maintenance.dispose()


@pytest.fixture(scope="session")
def repair_engine(repair_database: Any) -> Iterator[Any]:
    from auditmanager.shared.db.engine import create_database_engine

    engine = create_database_engine(repair_database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(params=["memory", "postgres"])
def store(request: pytest.FixtureRequest) -> Any:
    if request.param == "memory":
        return MemoryStore()
    engine = request.getfixturevalue("repair_engine")
    postgres = PostgresStore(engine)
    postgres.truncate()
    return postgres


@pytest.fixture
def kit(tmp_path: Path, store: Any) -> Iterator[Kit]:
    built = Kit(directory=tmp_path / "repairs", store=store, transport=ScriptedTransport())
    try:
        yield built
    finally:
        built.close()
