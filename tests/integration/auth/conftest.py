"""Fixtures for the credential-exchange suite.

One decision, and it is the same one ``tests/integration/api/conftest.py`` made: **the
database is real and this suite never skips.** What is under test is an exchange that
reads a row `W34-DOM`'s migration created, verifies a PBKDF2 digest that migration's
column shapes, and mints a credential from it. A fixture that fell back to an in-memory
user would be asserting that this suite's own dictionary lookup works.

``DATABASE_URL`` is read from the process environment, and from the lane's ``.env`` when
the process does not carry it -- the same two places and the same order the API suite
uses, so ``pytest tests/integration/auth`` works from a bare shell in a provisioned lane.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _load_database_url() -> str:
    """``DATABASE_URL`` from the process, else from the lane's ``.env``, else a failure."""
    configured = os.environ.get("DATABASE_URL")
    if configured:
        return configured
    dotenv = REPOSITORY_ROOT / ".env"
    if dotenv.is_file():
        for raw in dotenv.read_text(encoding="utf-8").splitlines():
            line = raw.strip().removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() != "DATABASE_URL":
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if value:
                os.environ["DATABASE_URL"] = value
                return value
    pytest.fail(
        "DATABASE_URL is not set and the lane's .env does not carry one. "
        "tests/integration/auth exchanges a login and a password for a credential "
        "against real rows in app_user; there is no in-memory equivalent worth "
        "asserting against, and this suite never skips."
    )


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    built = create_database_engine(
        DatabaseSettings(url=parse_database_url(_load_database_url()))
    )
    try:
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """The factory the adapter is constructed with, over this lane's database.

    The adapter opens its own session per call, exactly as it does in the application, so
    this suite exercises the transaction ownership the composition root really wires
    rather than a session a fixture kept open.
    """
    from auditmanager.shared.db.session import create_session_factory

    return create_session_factory(engine)


@pytest.fixture
def app_user_table(engine: Engine) -> Engine:
    """Refuse loudly, rather than erroring three frames deep, when the head is older."""
    with engine.connect() as connection:
        present = connection.execute(
            text("SELECT to_regclass('public.app_user') IS NOT NULL")
        ).scalar()
    assert present, (
        "app_user does not exist in this database. The credential exchange reads it, and "
        "`W34-DOM`'s migration 0006_app_user creates it: run `make migrate` against this "
        "lane's database."
    )
    return engine
