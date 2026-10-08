"""Database fixtures for the ``access`` suite: the ``db`` suite's, re-exported.

Each test that needs a database gets its own clone of a session-local database migrated
to head by the literal command, and it is dropped afterwards
(``tests/integration/db/conftest.py``). The
fixtures are imported rather than re-implemented so that "a fresh database at head" means
one thing in both suites. Tests in this directory that need no database -- the password and
name rules -- request none of these and run without one.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    empty_database,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    """A session on the fresh database. The test commits what it means to keep."""
    with Session(migrated_engine) as opened:
        yield opened
