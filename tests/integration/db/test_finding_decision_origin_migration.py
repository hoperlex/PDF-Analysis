"""`UI-A-73`: ``0058_finding_decision_origin`` gives a finding decision event an optional source, and refuses to go back over history.

On a clone of the migrated schema, against real PostgreSQL:

* ``carried_from_decision_id`` is nullable, references the event table itself without cascading, has its partial index, and
  every row written before the migration (a direct decision) has it ``NULL``;
* the column is held by three CHECKs that keep their names: the ``dec_<ULID>`` shape, "not its own source" and "only an
  accept or a reject is carried" -- each is proved able to fail by a row that breaks it, and by one that obeys it;
* the downgrade REFUSES while a carried event exists (the test proves the guard can fail by writing one), leaves the head
  where it was, and with no carried event left removes the column, the constraints and the index, after which the revision
  upgrades once more.

The rows reference a finding and an observation that do not exist: ``session_replication_role = replica`` switches off the
foreign keys and the append-only trigger for the statements that plant and remove them, as a superuser (the lane's database
user is one). The CHECKs are not triggers and stay in force.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine

HEAD = "0059_decision_memory"  # the head the fixture migrates to; 0058 is a step below it
PREVIOUS = "0057_decision_carryover"
TABLE = "expert_decision_event"
FORMAT = "ck_expert_decision_event_carried_from_format"
NOT_SELF = "ck_expert_decision_event_carried_from_not_self"
VERDICT = "ck_expert_decision_event_carried_from_verdict"
FOREIGN_KEY = "fk_expert_decision_event_carried_from"
INDEX = "ix_expert_decision_event_carried_from"

FINDING = "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_FINDING = "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAW"
OBSERVATION = "fobs_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SOURCE = "dec_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CARRIED = "dec_01ARZ3NDEKTSV4RRFFQ69G5FAW"

_VERDICT_OF = {"accept": "accepted", "reject": "rejected", "revoke": "pending", "comment": None}


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


@contextmanager
def _planting(engine: Engine) -> Iterator[Connection]:
    """One transaction in which the foreign keys and the append-only trigger are off."""
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
    finding: str = FINDING,
    event_type: str = "accept",
    carried_from: str | None = None,
) -> None:
    connection.execute(
        text(
            f"INSERT INTO {TABLE} (decision_id, finding_uid, finding_observation_id, event_type, verdict, comment, "
            "author_label, carried_from_decision_id) "
            "VALUES (:id, :finding, :observation, :event_type, :verdict, :comment, 'Эксперт', :carried)"
        ),
        {
            "id": decision, "finding": finding, "observation": OBSERVATION, "event_type": event_type,
            "verdict": _VERDICT_OF[event_type], "carried": carried_from,
            "comment": "заметка" if event_type == "comment" else None,  # a comment event carries one, by its own CHECK
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
        assert tuple(reference) == (TABLE, "r", True)  # RESTRICT: nothing is deleted from under a carried decision
        index = connection.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = :name"), {"name": INDEX}
        ).scalar_one()
        assert "(carried_from_decision_id)" in index and "WHERE (carried_from_decision_id IS NOT NULL)" in index


def test_a_direct_event_has_no_source_and_a_carried_one_names_the_source(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    with _planting(engine) as connection:
        _insert(connection, decision=SOURCE)
        _insert(connection, decision=CARRIED, finding=OTHER_FINDING, carried_from=SOURCE)
    with engine.connect() as connection:
        sources = dict(connection.execute(text(f"SELECT decision_id, carried_from_decision_id FROM {TABLE}")).all())
    assert sources == {SOURCE: None, CARRIED: SOURCE}
    _clear(engine)


def test_the_three_checks_hold_the_column_and_each_can_fail(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    # The shape: anything that is not `dec_<ULID>` is refused, and a well-formed identity is not.
    for malformed in ("", "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV", "dec_short", "dec_01ARZ3NDEKTSV4RRFFQ69G5FAV0"):
        assert _breaks(engine, FORMAT, decision=CARRIED, finding=OTHER_FINDING, carried_from=malformed), malformed
    assert not _breaks(engine, FORMAT, decision=CARRIED, finding=OTHER_FINDING, carried_from=SOURCE)
    # An event is not its own source.
    assert _breaks(engine, NOT_SELF, decision=CARRIED, finding=OTHER_FINDING, carried_from=CARRIED)
    assert not _breaks(engine, NOT_SELF, decision=CARRIED, finding=OTHER_FINDING, carried_from=SOURCE)
    # Only an accept or a reject is carried; a comment and a withdrawal are not, but are stored when made directly.
    for event_type in ("comment", "revoke"):
        assert _breaks(engine, VERDICT, decision=CARRIED, finding=OTHER_FINDING, event_type=event_type, carried_from=SOURCE)
        assert not _breaks(engine, VERDICT, decision=CARRIED, finding=OTHER_FINDING, event_type=event_type)
    for event_type in ("accept", "reject"):
        assert not _breaks(engine, VERDICT, decision=CARRIED, finding=OTHER_FINDING, event_type=event_type, carried_from=SOURCE)


def _delete_with_the_append_only_trigger_off(engine: Engine, where: str) -> int:
    """What ``scripts/recovery/project_erase.py`` does: the one named trigger off, a DELETE, the trigger on again."""
    trigger = "trg_expert_decision_event_append_only"
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {TABLE} DISABLE TRIGGER {trigger}"))
        deleted = connection.execute(text(f"DELETE FROM {TABLE} WHERE {where}")).rowcount
        connection.execute(text(f"ALTER TABLE {TABLE} ENABLE TRIGGER {trigger}"))
    return int(deleted)


def test_the_foreign_key_restricts_a_delete_of_a_cited_source_but_one_statement_may_remove_both(
    at_head: tuple[Engine, str],
) -> None:
    engine, _ = at_head
    with _planting(engine) as connection:
        _insert(connection, decision=SOURCE)
        _insert(connection, decision=CARRIED, finding=OTHER_FINDING, carried_from=SOURCE)
    # The source alone is held by the carried event that cites it (RESTRICT) -- with the append-only trigger off, the
    # foreign key is the only thing in the way, so this proves it can refuse.
    with pytest.raises(DBAPIError) as refused:
        _delete_with_the_append_only_trigger_off(engine, f"decision_id = '{SOURCE}'")
    assert FOREIGN_KEY in str(refused.value.orig)
    with engine.connect() as connection:
        assert connection.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar_one() == 2
    # The project erase deletes a whole project's ledger in one statement; a carried event and its source in that
    # statement go together, so a carried event does not make a project impossible to erase.
    assert _delete_with_the_append_only_trigger_off(engine, f"decision_id IN ('{SOURCE}', '{CARRIED}')") == 2
    with engine.connect() as connection:
        assert connection.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar_one() == 0
        trigger = connection.execute(
            text("SELECT tgenabled FROM pg_trigger WHERE tgname = 'trg_expert_decision_event_append_only'")
        ).scalar_one()
        assert trigger == "O"  # enabled again: the erase tool compares the whole trigger state afterwards


def test_the_downgrade_refuses_over_a_carried_event_and_removes_the_column_without_one(
    at_head: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_head
    with _planting(engine) as connection:
        _insert(connection, decision=SOURCE)
        _insert(connection, decision=CARRIED, finding=OTHER_FINDING, carried_from=SOURCE)

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "carried-over" in (refused.stdout + refused.stderr), refused.describe()
    assert _head(engine) == HEAD  # the refusal left the schema at 0058, with the carried event in it
    with engine.connect() as connection:
        assert connection.execute(
            text(f"SELECT count(*) FROM {TABLE} WHERE carried_from_decision_id IS NOT NULL")
        ).scalar_one() == 1

    _clear(engine)
    with _planting(engine) as connection:
        _insert(connection, decision=SOURCE)  # direct events do not hold the downgrade back
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
            {"names": [FORMAT, NOT_SELF, VERDICT, FOREIGN_KEY]},
        ).scalar_one()
        assert gone == 0
        assert connection.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = :n"), {"n": INDEX}).scalar_one() == 0
        assert connection.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar_one() == 1  # the direct event stays

    _clear(engine)
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    assert _head(engine) == HEAD
    assert not _breaks(engine, FORMAT, decision=CARRIED, finding=OTHER_FINDING, carried_from=SOURCE)
