"""Transaction semantics of the shared session boundary, against real PostgreSQL.

The task's failure case is "a failed transaction rolls back". These tests assert it
where it matters - a committed side effect visible to a *second* connection - rather
than by inspecting the session object, which would prove only that SQLAlchemy tracks
its own state.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from auditmanager.shared.db.config import DATABASE_URL_VAR, DatabaseSettings, load_settings
from auditmanager.shared.db.errors import DatabaseConfigurationError, DatabaseUnavailableError
from auditmanager.shared.db.engine import create_database_engine, verify_connectivity
from auditmanager.shared.db.session import (
    create_session_factory,
    nested_transaction,
    session_scope,
)

PROJECT_A = "prj_01M2545JSD15ETSNNV904X0001"
PROJECT_B = "prj_01M2545JSD15ETSNNV904X0002"
PROJECT_C = "prj_01M2545JSD15ETSNNV904X0003"

INSERT_PROJECT = text("INSERT INTO project (project_uid, name) VALUES (:uid, :name)")


class DeliberateFailure(RuntimeError):
    """Raised inside a unit of work to force the rollback path."""


def _project_uids(engine: Engine) -> set[str]:
    """Read committed state on a *separate* connection."""
    with engine.connect() as connection:
        return set(connection.execute(text("SELECT project_uid FROM project")).scalars())


def test_a_clean_unit_of_work_commits(migrated_engine: Engine) -> None:
    factory = create_session_factory(migrated_engine)
    with session_scope(factory) as session:
        session.execute(INSERT_PROJECT, {"uid": PROJECT_A, "name": "committed"})
    assert PROJECT_A in _project_uids(migrated_engine)


def test_a_failed_unit_of_work_rolls_back(migrated_engine: Engine) -> None:
    factory = create_session_factory(migrated_engine)
    with pytest.raises(DeliberateFailure):
        with session_scope(factory) as session:
            session.execute(INSERT_PROJECT, {"uid": PROJECT_B, "name": "doomed"})
            session.flush()
            raise DeliberateFailure("the command failed after writing")
    assert PROJECT_B not in _project_uids(migrated_engine), (
        "the write survived a failed unit of work; a half-applied command must never "
        "become visible"
    )


def test_a_constraint_violation_rolls_back_the_whole_unit(migrated_engine: Engine) -> None:
    """A database-level refusal aborts everything the command had written."""
    factory = create_session_factory(migrated_engine)
    with pytest.raises(IntegrityError):
        with session_scope(factory) as session:
            session.execute(INSERT_PROJECT, {"uid": PROJECT_C, "name": "first"})
            session.flush()
            # Same primary key: refused by the database.
            session.execute(INSERT_PROJECT, {"uid": PROJECT_C, "name": "second"})
            session.flush()
    assert PROJECT_C not in _project_uids(migrated_engine)


def test_a_nested_transaction_rolls_back_without_losing_the_outer_one(
    migrated_engine: Engine,
) -> None:
    """A SAVEPOINT contains the failure; the enclosing unit of work still commits."""
    outer = "prj_01M2545JSD15ETSNNV904X0004"
    inner = "prj_01M2545JSD15ETSNNV904X0005"
    factory = create_session_factory(migrated_engine)
    with session_scope(factory) as session:
        session.execute(INSERT_PROJECT, {"uid": outer, "name": "outer"})
        with pytest.raises(DeliberateFailure):
            with nested_transaction(session):
                session.execute(INSERT_PROJECT, {"uid": inner, "name": "inner"})
                session.flush()
                raise DeliberateFailure("the optional step failed")
    committed = _project_uids(migrated_engine)
    assert outer in committed
    assert inner not in committed


def test_rollback_survives_a_base_exception(migrated_engine: Engine) -> None:
    """``KeyboardInterrupt`` is not an ``Exception``; the rollback path still runs."""
    uid = "prj_01M2545JSD15ETSNNV904X0006"
    factory = create_session_factory(migrated_engine)
    with pytest.raises(KeyboardInterrupt):
        with session_scope(factory) as session:
            session.execute(INSERT_PROJECT, {"uid": uid, "name": "interrupted"})
            session.flush()
            raise KeyboardInterrupt
    assert uid not in _project_uids(migrated_engine)


def test_connectivity_probe_returns_the_server_version(migrated_engine: Engine) -> None:
    assert "PostgreSQL" in verify_connectivity(migrated_engine)


# ---------------------------------------------------------------------------
# Explicit configuration failures. "Invalid/unavailable DATABASE_URL fails
# explicitly" is a required failure case, so each shape is asserted.
# ---------------------------------------------------------------------------


def test_a_missing_database_url_fails_explicitly() -> None:
    with pytest.raises(DatabaseConfigurationError) as raised:
        load_settings({})
    assert DATABASE_URL_VAR in str(raised.value)
    assert "No default connection is assumed" in str(raised.value)


def test_an_empty_database_url_fails_explicitly() -> None:
    with pytest.raises(DatabaseConfigurationError):
        load_settings({DATABASE_URL_VAR: "   "})


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///./local.db",
        "sqlite+pysqlite:///:memory:",
        "postgresql://user:pw@localhost:5432/db",
        "postgresql+psycopg2://user:pw@localhost:5432/db",
        "mysql+pymysql://user:pw@localhost/db",
    ],
)
def test_a_wrong_driver_is_refused(url: str) -> None:
    """SQLite in particular, because a fallback would make this whole suite vacuous."""
    with pytest.raises(DatabaseConfigurationError) as raised:
        load_settings({DATABASE_URL_VAR: url})
    assert "postgresql+psycopg" in str(raised.value)


def test_a_url_without_a_database_name_is_refused() -> None:
    with pytest.raises(DatabaseConfigurationError):
        load_settings({DATABASE_URL_VAR: "postgresql+psycopg://user:pw@localhost:5432/"})


def test_an_unparseable_url_does_not_echo_its_value() -> None:
    """The value can carry a password, so the message names the fault, not the value."""
    with pytest.raises(DatabaseConfigurationError) as raised:
        load_settings({DATABASE_URL_VAR: "postgresql+psycopg://user:sup3rs3cret@:::/x"})
    assert "sup3rs3cret" not in str(raised.value)


def test_an_unreachable_database_fails_explicitly(
    configured_settings: DatabaseSettings,
) -> None:
    unreachable = DatabaseSettings(url=configured_settings.url.set(port=1))
    engine = create_database_engine(unreachable)
    try:
        with pytest.raises(DatabaseUnavailableError) as raised:
            verify_connectivity(engine)
        assert "could not connect" in str(raised.value)
    finally:
        engine.dispose()


def test_settings_never_render_the_password(configured_settings: DatabaseSettings) -> None:
    rendered = configured_settings.render_safe()
    assert "***" in rendered
    password = configured_settings.url.password
    if password:
        assert password not in rendered
        assert password not in str(configured_settings.url)
        assert password not in repr(configured_settings)
