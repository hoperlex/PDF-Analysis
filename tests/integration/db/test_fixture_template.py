"""The migrated-template shortcut must preserve independent database state."""

from __future__ import annotations

import subprocess
from collections.abc import Callable

import pytest
from sqlalchemy import text

from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine


def test_one_migration_supplies_isolated_clones_and_empty_stays_empty(
    migrated_template: str,
    migrated_database_factory: Callable[[], DatabaseSettings],
    empty_database: DatabaseSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert migrated_template.startswith("a1_tpl_")

    def refuse_second_migration(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a clone tried to run Alembic again")

    # The session template has already run the literal command. A second invocation
    # from either clone now fails, while direct PostgreSQL cloning remains available.
    monkeypatch.setattr(subprocess, "run", refuse_second_migration)
    first = migrated_database_factory()
    second = migrated_database_factory()
    assert first.url.database != second.url.database

    first_engine = create_database_engine(first)
    second_engine = create_database_engine(second)
    empty_engine = create_database_engine(empty_database)
    try:
        with first_engine.begin() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0017_execution_queue"
            )
            connection.execute(text("CREATE TABLE fixture_marker (value integer NOT NULL)"))
            connection.execute(text("INSERT INTO fixture_marker VALUES (1)"))
        with second_engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0017_execution_queue"
            )
            assert connection.execute(text("SELECT to_regclass('public.fixture_marker')")).scalar() is None
        with empty_engine.connect() as connection:
            assert connection.execute(text("SELECT to_regclass('public.alembic_version')")).scalar() is None
            assert connection.execute(text("SELECT to_regclass('public.app_user')")).scalar() is None
    finally:
        first_engine.dispose()
        second_engine.dispose()
        empty_engine.dispose()
