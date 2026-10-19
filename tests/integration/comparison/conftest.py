"""PostgreSQL fixtures for the served comparison's database tests.

Only ``test_service_db.py`` asks for them; the pure comparison modules beside it
need no database. A missing ``DATABASE_URL`` is a hard failure for the tests that
do: a skipped database test reports success while proving nothing. Isolation is a
transaction that is always rolled back, because ``document_version`` refuses
DELETE by trigger and that guarantee is not this suite's to defeat.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine


@pytest.fixture(scope="session")
def comparison_engine() -> Iterator[Engine]:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. The comparison database tests read real "
            "document_version rows through the version reader's one SELECT; run "
            "`make up` and `make migrate` for this lane first. They never skip."
        )
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with built.connect() as connection:
            present = connection.execute(
                text("SELECT to_regclass('public.document_version')")
            ).scalar_one_or_none()
        if present is None:
            pytest.fail("the configured database has no document_version table; run `make migrate`")
        yield built
    finally:
        built.dispose()


@pytest.fixture
def comparison_session(comparison_engine: Engine) -> Iterator[Session]:
    connection = comparison_engine.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False, future=True)()
    try:
        yield opened
    finally:
        opened.close()
        transaction.rollback()
        connection.close()
