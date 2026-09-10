"""Fixtures for the database integration suite.

Every test here runs against a real PostgreSQL server. There is no SQLite fallback
and no in-memory substitute: the schema's invariants are triggers, partial unique
indexes, ``jsonb`` predicates and custom SQLSTATEs, none of which SQLite has, so a
suite that could fall back would be asserting nothing about what actually ships.

Each test that needs a database gets its **own freshly created, empty** one, and it
is dropped afterwards. That is what makes "migrations apply from an empty database"
a repeatable claim rather than a statement about whatever the last run left behind.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The literal invocations recorded in docs/program/FOUNDATION_LOCK.json. The suite
#: runs these, rather than an approximation of them through the Python API, so that
#: "make migrate exits 0" and "the suite passes" cannot diverge.
MIGRATE_ARGV = [
    ".venv/bin/python",
    "-m",
    "alembic",
    "--config",
    "db/migrations/alembic.ini",
    "upgrade",
    "head",
]
CHECK_DB_ARGV = [".venv/bin/python", "-m", "auditmanager.shared.db.check"]


@dataclass(frozen=True, slots=True)
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def output_lines(self) -> list[str]:
        return [line for line in self.stdout.splitlines() if line.strip()]

    @property
    def last_output_line(self) -> str:
        lines = self.output_lines
        return lines[-1] if lines else ""

    def describe(self) -> str:
        return (
            f"$ {' '.join(self.argv)}\n"
            f"exit {self.returncode}\n"
            f"--- stdout ---\n{self.stdout}\n--- stderr ---\n{self.stderr}"
        )


def run_foundation_command(argv: list[str], database_url: str) -> CommandResult:
    """Run one foundation command exactly as the Makefile does.

    ``PYTHONPATH=src`` is the module-invocation mechanism named in the import
    contract; nothing here manipulates ``sys.path``.
    """
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src"
    environment["DATABASE_URL"] = database_url
    completed = subprocess.run(
        argv,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return CommandResult(
        argv=argv,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


@pytest.fixture(scope="session")
def foundation_command():
    """The literal-command runner, handed to tests as a fixture.

    Deliberately a fixture rather than an import: pytest runs this repository with
    ``--import-mode=importlib`` and the suite directories carry no ``__init__.py``,
    so ``from .conftest import ...`` is not a supported import path here. The import
    contract in FOUNDATION_LOCK.json forbids working around that with ``sys.path``
    juggling, and a fixture needs neither.
    """
    return run_foundation_command


@pytest.fixture(scope="session")
def migrate_argv() -> list[str]:
    return list(MIGRATE_ARGV)


@pytest.fixture(scope="session")
def check_db_argv() -> list[str]:
    return list(CHECK_DB_ARGV)


@pytest.fixture(scope="session")
def configured_settings() -> DatabaseSettings:
    """The lane's configured database, from ``DATABASE_URL``.

    An absent value is a hard failure, never a skip. A skipped integration suite
    reports success while proving nothing, which is exactly the vacuous pass this
    programme's gate discipline refuses.
    """
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. tests/integration/db runs against a real "
            "PostgreSQL instance; export this lane's value before running it. "
            "This suite never falls back to SQLite and never skips itself."
        )
    settings = DatabaseSettings(url=parse_database_url(raw))
    if settings.url.get_backend_name() != "postgresql":
        pytest.fail(f"DATABASE_URL is not PostgreSQL: {settings.render_safe()}")
    return settings


@pytest.fixture(scope="session")
def maintenance_engine(configured_settings: DatabaseSettings) -> Iterator[Engine]:
    """An autocommit engine on the maintenance database, for CREATE/DROP DATABASE."""
    maintenance = configured_settings.url.set(database="postgres")
    engine = create_database_engine(DatabaseSettings(url=maintenance)).execution_options(
        isolation_level="AUTOCOMMIT"
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        engine.dispose()
        pytest.fail(
            "could not reach the PostgreSQL maintenance database. This suite creates a "
            f"throwaway database per test and needs CREATEDB. Underlying: {exc}"
        )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def empty_database(
    configured_settings: DatabaseSettings, maintenance_engine: Engine
) -> Iterator[DatabaseSettings]:
    """A freshly created, completely empty database, dropped when the test ends.

    Empty means empty: no ``alembic_version``, no tables. Tests that assert on a
    clean install depend on that, and a suite that reused one database would only be
    asserting it on its very first run.
    """
    name = f"a1_probe_{secrets.token_hex(6)}"
    with maintenance_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    settings = DatabaseSettings(url=configured_settings.url.set(database=name))
    try:
        yield settings
    finally:
        with maintenance_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))


@pytest.fixture
def empty_database_url(empty_database: DatabaseSettings) -> str:
    return empty_database.url.render_as_string(hide_password=False)


@pytest.fixture
def migrated_database(empty_database: DatabaseSettings) -> DatabaseSettings:
    """An empty database with the migration head applied, via the literal command."""
    url = empty_database.url.render_as_string(hide_password=False)
    result = run_foundation_command(MIGRATE_ARGV, url)
    assert result.returncode == 0, result.describe()
    return empty_database


@pytest.fixture
def migrated_engine(migrated_database: DatabaseSettings) -> Iterator[Engine]:
    engine = create_database_engine(migrated_database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _refuse_a_non_repository_working_tree() -> None:
    """Guard the assumption every subprocess in this suite makes."""
    if not (REPOSITORY_ROOT / "db" / "migrations" / "alembic.ini").is_file():
        pytest.fail(f"expected the repository root at {REPOSITORY_ROOT}")
    if not (REPOSITORY_ROOT / ".venv" / "bin" / "python").is_file():
        pytest.fail(
            f"{REPOSITORY_ROOT}/.venv/bin/python is missing. Run `make bootstrap` "
            "first; this suite runs the literal foundation commands."
        )
    assert sys.version_info[:2] == (3, 12)
