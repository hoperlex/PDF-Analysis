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
from pathlib import Path

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


# -- what a test creates ends with the test (`CMP-C1-FIX-A` item 3) -------------------------------------------------------------
#
# Every subdirectory of this directory runs against the one lane database, and some things in it look at *everything* that is
# live: the queue's hosting tests (`work/test_worker_hosting.py`) refuse to start a worker while an item of a kind they do not
# register is live (`UnhandledKindError`), the engine's queue tests claim *any* queued item, and the intake refuses a new batch
# when the installation already has two active ones (`comparison_upload_active`, `series/test_upload_flag.py`). The matrix tests
# queue `matrix_build` items they never run, a series queues its pairs, and the overview tests seed batches that are still
# being uploaded. Run in one process, the directory failed the hosting tests (`CMP-SERIES-01` section 9 item 6). The series
# directory already ended its own items; this fixture does it for every test of the directory: the work items that are live
# after a test and were not before it, and the upload batches that are active after it and were not before it, are ended
# with it.

_DOTENV_NAMES = ("DATABASE_URL",)
_LIVE_WORK = text("SELECT comparison_work_id FROM comparison_work WHERE terminal_at IS NULL")
_ACTIVE_UPLOADS = text("SELECT comparison_upload_id FROM comparison_upload WHERE terminal_at IS NULL")
_IN_FLIGHT = " AND state IN ('leased', 'running')"
_MINE_WORK = " WHERE comparison_work_id = ANY(CAST(:ids AS text[])) AND terminal_at IS NULL"


def _database_url() -> str | None:
    if not os.environ.get("DATABASE_URL"):
        dotenv = Path(__file__).resolve().parents[3] / ".env"
        if dotenv.is_file():
            for raw in dotenv.read_text(encoding="utf-8").splitlines():
                name, separator, value = raw.strip().partition("=")
                if separator and name in _DOTENV_NAMES:
                    os.environ.setdefault(name, value.strip().strip("\"'"))
    return os.environ.get("DATABASE_URL")


@pytest.fixture(scope="session")
def _work_ledger() -> Iterator[Engine | None]:
    """A connection of its own to the lane database, or ``None`` when there is no database (the tests that need one fail
    on their own, and the pure tests of the directory need none)."""
    raw = _database_url()
    if not raw:
        yield None
        return
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with built.connect() as connection:
            present = connection.execute(
                text("SELECT to_regclass('public.comparison_work') IS NOT NULL AND to_regclass('public.comparison_upload') IS NOT NULL")
            ).scalar_one()
        yield built if present else None
    finally:
        built.dispose()


def live_work_ids(engine: Engine) -> frozenset[str]:
    with engine.connect() as connection:
        return frozenset(str(value) for value in connection.execute(_LIVE_WORK).scalars())


def active_upload_ids(engine: Engine) -> frozenset[str]:
    with engine.connect() as connection:
        return frozenset(str(value) for value in connection.execute(_ACTIVE_UPLOADS).scalars())


def end_work(engine: Engine, ids: frozenset[str]) -> None:
    """End the live items ``ids``. An item in flight is asked to stop, its lease expired and reclaimed (the queue's own way
    to settle an attempt); every item still live after that -- one at rest, or one a test wrote into flight without any
    attempt -- is cancelled, an edge the state machine allows from every live state. Nothing is deleted."""
    from auditmanager.comparison.public import ComparisonWorkRepository

    parameters = {"ids": sorted(ids)}
    with engine.begin() as connection:
        connection.execute(text("UPDATE comparison_work SET cancel_requested_at = clock_timestamp()" + _MINE_WORK + _IN_FLIGHT), parameters)
        connection.execute(
            text(
                "UPDATE comparison_work_attempt SET lease_expires_at = clock_timestamp() - interval '1 hour' "
                "WHERE comparison_work_id = ANY(CAST(:ids AS text[])) AND state IN ('leased', 'running')"
            ),
            parameters,
        )
    with sessionmaker(bind=engine, expire_on_commit=False, future=True)() as session:
        ComparisonWorkRepository().reclaim_expired(session)
        session.commit()
    with engine.begin() as connection:
        connection.execute(text("UPDATE comparison_work SET state = 'cancelled', terminal_at = clock_timestamp()" + _MINE_WORK), parameters)


def end_uploads(engine: Engine, ids: frozenset[str]) -> None:
    """Cancel the active batches ``ids`` (``uploading``, ``proposed``, ``processing`` and ``paused`` all have the edge)."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE comparison_upload SET state = 'cancelled', terminal_at = clock_timestamp() "
                "WHERE comparison_upload_id = ANY(CAST(:ids AS text[])) AND terminal_at IS NULL"
            ),
            {"ids": sorted(ids)},
        )


@pytest.fixture(autouse=True)
def _end_what_a_test_creates(_work_ledger: Engine | None) -> Iterator[None]:
    if _work_ledger is None:
        yield
        return
    work_before, uploads_before = live_work_ids(_work_ledger), active_upload_ids(_work_ledger)
    yield
    work = live_work_ids(_work_ledger) - work_before
    uploads = active_upload_ids(_work_ledger) - uploads_before
    if work:
        end_work(_work_ledger, work)
    if uploads:
        end_uploads(_work_ledger, uploads)
    assert not (live_work_ids(_work_ledger) & work), f"work items of this test are still live after it: {sorted(work)}"
    assert not (active_upload_ids(_work_ledger) & uploads), f"upload batches of this test are still active after it: {sorted(uploads)}"
