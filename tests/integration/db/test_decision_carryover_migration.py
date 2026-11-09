"""`UI-B-14`: ``0057_decision_carryover`` gives a proposal decision an optional source, and refuses to go back over history.

On a clone of the migrated schema, against real PostgreSQL:

* ``carried_from_decision_id`` is nullable, references the decision table itself without cascading, has its partial index,
  and every row written before the migration (a direct decision) has it ``NULL``;
* the column is held by three CHECKs that keep their names: the ``opd_<ULID>`` shape, "not its own source" and "not a
  withdrawal" -- each is proved able to fail by a row that breaks it, and by one that obeys it;
* the downgrade REFUSES while a carried decision exists (the test proves the guard can fail by writing one), leaves the
  head where it was, and with no carried decision left removes the column, the constraints and the index, after which the
  revision upgrades once more.

The rows reference a proposal, an account and a command that do not exist: ``session_replication_role = replica`` switches
off the foreign keys and the immutability trigger for the statements that plant and remove them, as a superuser (the lane's
database user is one). The CHECKs are not triggers and stay in force.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine

HEAD = "0060_run_from_stage"  # the head the fixture migrates to; 0057 is three steps below it
PREVIOUS = "0056_optimisation_decisions"
TABLE = "optimisation_proposal_decision"
FORMAT = "ck_optimisation_proposal_decision_carried_from_format"
NOT_SELF = "ck_optimisation_proposal_decision_carried_from_not_self"
NOT_REVOKE = "ck_optimisation_proposal_decision_carried_from_not_revoke"
FOREIGN_KEY = "fk_optimisation_proposal_decision_carried_from"
INDEX = "ix_optimisation_proposal_decision_carried_from"

PROPOSAL = "opr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PROPOSAL = "opr_01ARZ3NDEKTSV4RRFFQ69G5FAW"
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SOURCE = "opd_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CARRIED = "opd_01ARZ3NDEKTSV4RRFFQ69G5FAW"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


@contextmanager
def _planting(engine: Engine) -> Iterator[Connection]:
    """One transaction in which the foreign keys and the immutability trigger are off."""
    with engine.begin() as connection:
        assert connection.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar_one(), (
            "this test plants rows that reference nothing; it needs the superuser of the lane's database"
        )
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        yield connection


def _insert(
    connection: Connection,
    *,
    decision: str,
    proposal: str,
    verdict: str = "accept",
    carried_from: str | None = None,
    command: str | None = None,
) -> None:
    connection.execute(
        text(
            f"INSERT INTO {TABLE} (proposal_decision_id, optimisation_proposal_id, seq, verdict, comment, actor_user_uid, "
            "command_id, carried_from_decision_id) VALUES (:id, :proposal, 1, :verdict, :comment, :actor, :command, :carried)"
        ),
        {
            "id": decision, "proposal": proposal, "verdict": verdict, "actor": ACTOR,
            "command": command or "cmd_" + decision[4:], "carried": carried_from,
            "comment": "уточнить" if verdict == "revise" else None,  # ``revise`` carries one, by its own CHECK
        },
    )


def _clear(engine: Engine) -> None:
    with _planting(engine) as connection:
        connection.execute(text(f"DELETE FROM {TABLE}"))


def _head(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


def _breaks(engine: Engine, constraint: str, **row: Any) -> bool:
    """Whether the row is refused by exactly this constraint; any other refusal is a defect of the test."""
    try:
        with _planting(engine) as connection:
            _insert(connection, **row)
    except DBAPIError as error:
        assert constraint in str(error.orig), error
        return True
    finally:
        _clear(engine)
    return False


@pytest.fixture
def at_head(migrated_database: Any) -> Iterator[tuple[Engine, str]]:
    engine = create_database_engine(migrated_database)
    try:
        yield engine, migrated_database.url.render_as_string(hide_password=False)
    finally:
        engine.dispose()


def test_the_column_is_optional_references_the_table_itself_and_is_indexed(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    assert _head(engine) == HEAD
    with engine.connect() as connection:
        column = connection.execute(
            text(
                "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = 'carried_from_decision_id'"
            ),
            {"table": TABLE},
        ).one()
        assert tuple(column) == ("text", "YES", None)
        reference = connection.execute(
            text(
                "SELECT confrelid::regclass::text, confdeltype, convalidated FROM pg_constraint "
                "WHERE conname = :name AND conrelid = CAST(:table AS regclass)"
            ),
            {"name": FOREIGN_KEY, "table": TABLE},
        ).one()
        assert tuple(reference) == (TABLE, "r", True)  # RESTRICT: nothing is ever deleted from under a carried decision
        index = connection.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = :name"), {"name": INDEX}
        ).scalar_one()
        assert "(carried_from_decision_id)" in index and "WHERE (carried_from_decision_id IS NOT NULL)" in index


def test_a_direct_decision_has_no_source_and_a_carried_one_names_the_source(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    with _planting(engine) as connection:
        _insert(connection, decision=SOURCE, proposal=PROPOSAL)
        _insert(connection, decision=CARRIED, proposal=OTHER_PROPOSAL, carried_from=SOURCE)
    with engine.connect() as connection:
        sources = dict(connection.execute(text(f"SELECT proposal_decision_id, carried_from_decision_id FROM {TABLE}")).all())
    assert sources == {SOURCE: None, CARRIED: SOURCE}
    _clear(engine)


def test_the_three_checks_hold_the_column_and_each_can_fail(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    # The shape: anything that is not `opd_<ULID>` is refused, and a well-formed identity is not.
    for malformed in ("", "opr_01ARZ3NDEKTSV4RRFFQ69G5FAV", "opd_short", "opd_01ARZ3NDEKTSV4RRFFQ69G5FAV0"):
        assert _breaks(engine, FORMAT, decision=CARRIED, proposal=OTHER_PROPOSAL, carried_from=malformed), malformed
    assert not _breaks(engine, FORMAT, decision=CARRIED, proposal=OTHER_PROPOSAL, carried_from=SOURCE)
    # A decision is not its own source.
    assert _breaks(engine, NOT_SELF, decision=CARRIED, proposal=OTHER_PROPOSAL, carried_from=CARRIED)
    assert not _breaks(engine, NOT_SELF, decision=CARRIED, proposal=OTHER_PROPOSAL, carried_from=SOURCE)
    # A withdrawal is not carried; the three verdicts in force are.
    assert _breaks(engine, NOT_REVOKE, decision=CARRIED, proposal=OTHER_PROPOSAL, verdict="revoke", carried_from=SOURCE)
    for verdict in ("accept", "reject", "revise"):
        assert not _breaks(engine, NOT_REVOKE, decision=CARRIED, proposal=OTHER_PROPOSAL, verdict=verdict, carried_from=SOURCE)
    # A direct withdrawal is still stored (0056 is untouched).
    assert not _breaks(engine, NOT_REVOKE, decision=CARRIED, proposal=OTHER_PROPOSAL, verdict="revoke")


def test_the_downgrade_refuses_over_a_carried_decision_and_removes_the_column_without_one(
    at_head: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_head
    with _planting(engine) as connection:
        _insert(connection, decision=SOURCE, proposal=PROPOSAL)
        _insert(connection, decision=CARRIED, proposal=OTHER_PROPOSAL, carried_from=SOURCE)

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "carried-over" in (refused.stdout + refused.stderr), refused.describe()
    assert _head(engine) == HEAD  # the refusal rolled the whole downgrade back (0058 included), with the carried decision in it
    with engine.connect() as connection:
        assert connection.execute(
            text(f"SELECT count(*) FROM {TABLE} WHERE carried_from_decision_id IS NOT NULL")
        ).scalar_one() == 1

    _clear(engine)
    with _planting(engine) as connection:
        _insert(connection, decision=SOURCE, proposal=PROPOSAL)  # direct decisions do not hold the downgrade back
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    assert _head(engine) == PREVIOUS
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM information_schema.columns WHERE table_name = :t AND column_name = 'carried_from_decision_id'"),
            {"t": TABLE},
        ).scalar_one() == 0
        gone = connection.execute(
            text("SELECT count(*) FROM pg_constraint WHERE conname = ANY(:names)"),
            {"names": [FORMAT, NOT_SELF, NOT_REVOKE, FOREIGN_KEY]},
        ).scalar_one()
        assert gone == 0
        assert connection.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = :n"), {"n": INDEX}).scalar_one() == 0
        assert connection.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar_one() == 1  # the direct decision stays

    _clear(engine)
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    assert _head(engine) == HEAD
    assert not _breaks(engine, FORMAT, decision=CARRIED, proposal=OTHER_PROPOSAL, carried_from=SOURCE)
