"""`RUN-DELETE-01`: ``0066_run_deletion`` -- the tombstone of a run deleted from the run lists, against real PostgreSQL.

``audit_run_deletion`` is a table of its own and not a column of ``audit_run``, because ``trg_audit_run_frozen_guard`` refuses any update of a
terminal run. Each rule is shown by a row that obeys beside a row that does not, with the trigger on:

* **the step changes no stored row** (an existing run stays as it is) and creates the table empty;
* **the key and the references**: the run is the identity (at most one tombstone per run), the run, the account and the command receipt must exist
  (RESTRICT, all three), and one command receipt serves one tombstone;
* **the shape**: the identity formats of the run, the account and the command;
* **immutable**: ``UPDATE`` and ``DELETE`` are refused (``AM003``), and the run it names cannot be removed from under it;
* **the downgrade drops the table** and leaves every run; up again restores it empty.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import AnalysisProfileId, CommandId, PromptBundleId, RunId
from auditmanager.shared.identity.ids import UserUid
from tests.integration.documents.seeding import Seeder
from tests.support.expected_facts import FACTS

THIS = "0066_run_deletion"
PREVIOUS = "0065_norm_crop_render"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _refused(engine: Engine, write: Any, sqlstate: str) -> None:
    """The write is refused by the database with the given SQLSTATE (``AM003`` a guard, ``23514`` a CHECK, ``23503`` a key, ``23505`` a unique)."""
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


def _accepted(engine: Engine, write: Any) -> None:
    """The write is accepted; the transaction is rolled back, so the next try starts from the same rows."""
    with engine.connect() as connection, connection.begin() as transaction:
        try:
            write(connection)
        finally:
            transaction.rollback()


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _rows(engine: Engine) -> tuple[str, str, str, str]:
    """Committed: a failed run, a second run, an account and a command receipt. Returns (run, other run, account, command)."""
    run, other = str(RunId.new()), str(RunId.new())
    with Session(engine) as session:
        seed = Seeder(session)
        project = seed.project("Проект")
        version = seed.version(seed.document(project, "Документ"), classified=("R", "AR"))
        for run_id in (run, other):
            session.execute(text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
                "frozen_input_digest) VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :d)"),
                {"r": run_id, "p": project, "v": version, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()),
                 "d": hashlib.sha256(run_id.encode()).hexdigest()})
            session.execute(text("UPDATE audit_run SET state = 'cancelled', terminal_at = now() WHERE run_id = :r"), {"r": run_id})
        account = seed.expert
        command = str(CommandId.new())
        session.execute(text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
            "VALUES (:c, 'delete_audit_run', :k, :f)"), {"c": command, "k": f"rd01-{command[-12:]}", "f": "f" * 64})
        session.commit()
    return run, other, account, command


def _command(engine: Engine) -> str:
    """One more committed command receipt, unused by any tombstone."""
    command = str(CommandId.new())
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
            "VALUES (:c, 'delete_audit_run', :k, :f)"), {"c": command, "k": f"rd01-{command[-12:]}", "f": "e" * 64})
    return command


def _tombstone(connection: Connection, *, run: str, account: str, command: str) -> None:
    connection.execute(text(
        "INSERT INTO audit_run_deletion (run_id, deleted_by_user_uid, command_id) VALUES (:r, :u, :c)"), {"r": run, "u": account, "c": command})


@pytest.fixture
def at_head(migrated_database: Any) -> Iterator[Engine]:
    engine = create_database_engine(migrated_database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str]]:
    url = empty_database.url.render_as_string(hide_password=False)
    done = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert done.returncode == 0, done.describe()
    engine = create_database_engine(empty_database)
    try:
        yield engine, url
    finally:
        engine.dispose()


# -- the step -------------------------------------------------------------------------------------


def test_the_head_of_the_tree_is_this_revision_or_a_later_one() -> None:
    assert FACTS.migration_head >= THIS


def test_the_revision_id_fits_the_version_column() -> None:
    assert len(THIS) <= 32


def test_the_step_changes_no_stored_row_and_creates_the_table_empty(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    run, _, _, _ = _rows(engine)
    tables = ("audit_run", "app_user", "command_record", "document_version", "project")
    before = {table: _count(engine, table) for table in tables}
    assert before["audit_run"] == 2
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('audit_run_deletion')")).scalar_one() is None      # the control: not there before
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    assert {table: _count(engine, table) for table in tables} == before
    assert _count(engine, "audit_run_deletion") == 0
    with engine.connect() as connection:
        assert connection.execute(text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": run}).scalar_one() == "cancelled"


def test_the_table_has_the_columns_the_key_the_references_and_the_trigger_the_migration_declares(at_head: Engine) -> None:
    with at_head.connect() as connection:
        columns = {row[0]: (row[1], row[2], row[3]) for row in connection.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'audit_run_deletion'"))}
        assert set(columns) == {"run_id", "deleted_at", "deleted_by_user_uid", "command_id"}
        assert all(nullable == "NO" for _, nullable, _ in columns.values())
        assert columns["deleted_at"][0] == "timestamp with time zone" and "clock_timestamp()" in columns["deleted_at"][2]
        constraints = {row[0]: row[1] for row in connection.execute(text(
            "SELECT conname, contype FROM pg_constraint WHERE conrelid = 'audit_run_deletion'::regclass"))}
        assert constraints == {
            "pk_audit_run_deletion": "p", "uq_audit_run_deletion_command": "u",
            "fk_audit_run_deletion_run": "f", "fk_audit_run_deletion_deleted_by": "f", "fk_audit_run_deletion_command": "f",
            "ck_audit_run_deletion_run_id_format": "c", "ck_audit_run_deletion_deleted_by_format": "c", "ck_audit_run_deletion_command_id_format": "c",
        }
        actions = {row[0]: row[1] for row in connection.execute(text(
            "SELECT conname, confdeltype FROM pg_constraint WHERE conrelid = 'audit_run_deletion'::regclass AND contype = 'f'"))}
        assert set(actions.values()) == {"r"}, "every reference is RESTRICT"
        triggers = connection.execute(text(
            "SELECT t.tgname, p.proname FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid "
            "WHERE t.tgrelid = 'audit_run_deletion'::regclass AND NOT t.tgisinternal")).all()
        assert [tuple(row) for row in triggers] == [("trg_audit_run_deletion_immutable", "am_immutable_row")]


def test_the_key_and_the_references(at_head: Engine) -> None:
    run, other, account, command = _rows(at_head)
    _accepted(at_head, lambda c: _tombstone(c, run=run, account=account, command=command))
    with at_head.begin() as connection:
        _tombstone(connection, run=run, account=account, command=command)
    _refused(at_head, lambda c: _tombstone(c, run=run, account=account, command=str(CommandId.new())), "23505")     # one tombstone per run
    _refused(at_head, lambda c: _tombstone(c, run=other, account=account, command=command), "23505")                # one receipt per tombstone
    spare = _command(at_head)
    _accepted(at_head, lambda c: _tombstone(c, run=other, account=account, command=spare))                          # the control: a spare receipt serves
    _refused(at_head, lambda c: _tombstone(c, run=str(RunId.new()), account=account, command=spare), "23503")       # the run must exist
    _refused(at_head, lambda c: _tombstone(c, run=other, account=str(UserUid.new()), command=spare), "23503")       # the account must exist
    _refused(at_head, lambda c: _tombstone(c, run=other, account=account, command=str(CommandId.new())), "23503")   # the receipt must exist


def test_the_shape(at_head: Engine) -> None:
    run, other, account, command = _rows(at_head)
    _refused(at_head, lambda c: _tombstone(c, run="run_not-an-identity", account=account, command=command), "23514")
    _refused(at_head, lambda c: _tombstone(c, run=other, account="usr_not-an-identity", command=command), "23514")
    _refused(at_head, lambda c: _tombstone(c, run=other, account=account, command="cmd_not-an-identity"), "23514")
    _accepted(at_head, lambda c: _tombstone(c, run=other, account=account, command=command))                       # the control: the same row, well formed


def test_a_tombstone_is_immutable_and_its_run_cannot_be_removed_from_under_it(at_head: Engine) -> None:
    run, _, account, command = _rows(at_head)
    with at_head.begin() as connection:
        _tombstone(connection, run=run, account=account, command=command)
    _refused(at_head, lambda c: c.execute(text("UPDATE audit_run_deletion SET deleted_at = now() WHERE run_id = :r"), {"r": run}), "AM003")
    _refused(at_head, lambda c: c.execute(text("DELETE FROM audit_run_deletion WHERE run_id = :r"), {"r": run}), "AM003")
    _refused(at_head, lambda c: c.execute(text("DELETE FROM audit_run WHERE run_id = :r"), {"r": run}), "23503")    # RESTRICT: or the frozen guard
    assert _count(at_head, "audit_run_deletion") == 1


# -- the downgrade ---------------------------------------------------------------------------------


def test_the_downgrade_drops_the_table_and_touches_no_run_and_up_again_restores_it_empty(
    at_previous: tuple[Engine, str], foundation_command: Any,
) -> None:
    engine, url = at_previous
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    run, other, account, command = _rows(engine)
    with engine.begin() as connection:
        _tombstone(connection, run=run, account=account, command=command)
    assert _count(engine, "audit_run_deletion") == 1

    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        assert connection.execute(text("SELECT to_regclass('audit_run_deletion')")).scalar_one() is None
        assert connection.execute(text("SELECT count(*) FROM audit_run WHERE run_id IN (:a, :b)"), {"a": run, "b": other}).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM command_record WHERE command_id = :c"), {"c": command}).scalar_one() == 1

    upgraded = foundation_command(_alembic("upgrade", THIS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
    assert _count(engine, "audit_run_deletion") == 0
