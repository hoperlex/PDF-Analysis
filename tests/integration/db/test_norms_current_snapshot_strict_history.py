"""`W55A-FIX`: the current-snapshot history of ``0020`` holds against direct SQL.

JUDGE-X M4 and JUDGE-Y Y-3 found four ways around the history by plain SQL, each closed in
``0020``'s guard triggers and each attacked here on a fresh clone of the migration head:

* an **older event reused** -- ``A -> B`` named again after ``B -> A`` -- passed the guard,
  whose ``from``/``to`` check it satisfies; the guard now requires the newest event;
* an **event without a designation** -- inserted while the current row stays put -- made a
  never-current snapshot "once current" and so searchable by explicit scope; a deferred
  constraint trigger now refuses it at COMMIT;
* **TRUNCATE** skipped the row triggers and could erase the history and the current row;
  both tables now refuse it, also when it arrives by CASCADE from ``norms_snapshot``;
* an **explicit ``changed_at``** could backdate an event (or post-date one above every later
  designation); the database now stamps its own clock.

Each refusal has a control that succeeds, so it cannot pass because the statement was
malformed. HEAVY: real PostgreSQL (the lane's private stack).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.identity import AuditEventId, NormsSnapshotId
from auditmanager.shared.identity.ids import UserUid
from tests.integration.norms.reset import truncate_tables


def _sqlstate(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _snapshot(connection: Connection) -> str:
    snapshot = str(NormsSnapshotId.new())
    key = f"w55a-fix-{snapshot[-12:].lower()}"
    connection.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, segmentation_profile) "
        "VALUES (:s, :k, :k, :d, 0, 1, 'w55a-fix')"
    ), {"s": snapshot, "k": key, "d": "a" * 64})
    return snapshot


def _event(connection: Connection, *, to: str, before: str | None,
           changed_at: datetime | None = None) -> str:
    event = str(AuditEventId.new())
    columns, values = "", ""
    parameters: dict[str, object] = {
        "e": event, "f": before, "t": to, "a": str(UserUid.new()),
    }
    if changed_at is not None:
        columns, values = ", changed_at", ", :at"
        parameters["at"] = changed_at
    connection.execute(text(
        "INSERT INTO norm_current_snapshot_event (event_id, from_snapshot_id, to_snapshot_id, "
        f"actor_user_uid{columns}) VALUES (:e, :f, :t, :a{values})"
    ), parameters)
    return event


def _point(connection: Connection, snapshot: str, event: str) -> None:
    """The current row onto ``event``: INSERT for the first designation, UPDATE after."""
    if connection.execute(text("SELECT count(*) FROM norm_current_snapshot")).scalar_one():
        connection.execute(text(
            "UPDATE norm_current_snapshot SET norms_snapshot_id = :s, event_id = :e"
        ), {"s": snapshot, "e": event})
    else:
        connection.execute(text(
            "INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id) VALUES (:s, :e)"
        ), {"s": snapshot, "e": event})


def _designate(engine: Engine, snapshot: str, before: str | None) -> str:
    """One committed designation, as the setter writes it."""
    with engine.begin() as connection:
        event = _event(connection, to=snapshot, before=before)
        _point(connection, snapshot, event)
    return event


def _current(engine: Engine) -> tuple[str, str] | None:
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT norms_snapshot_id, event_id FROM norm_current_snapshot"
        )).one_or_none()
    return None if row is None else (str(row[0]), str(row[1]))


def _history(engine: Engine) -> list[tuple[str | None, str]]:
    with engine.connect() as connection:
        return [
            (row[0], row[1]) for row in connection.execute(text(
                "SELECT from_snapshot_id, to_snapshot_id FROM norm_current_snapshot_event "
                "ORDER BY changed_at, event_id COLLATE \"C\""
            ))
        ]


def _snapshots(engine: Engine, count: int) -> list[str]:
    with engine.begin() as connection:
        return [_snapshot(connection) for _ in range(count)]


# --- an older event reused ------------------------------------------------------------------


def test_an_older_event_cannot_designate_again(migrated_engine: Engine) -> None:
    a, b = _snapshots(migrated_engine, 2)
    _designate(migrated_engine, a, None)
    a_to_b = _designate(migrated_engine, b, a)
    _designate(migrated_engine, a, b)  # B -> A: A is current again
    # The attack: A -> B once more by the old event, whose from/to match the change.
    with pytest.raises(DBAPIError) as refused:
        with migrated_engine.begin() as connection:
            connection.execute(text(
                "UPDATE norm_current_snapshot SET norms_snapshot_id = :s, event_id = :e"
            ), {"s": b, "e": a_to_b})
    assert _sqlstate(refused) == "AM003", refused.value
    assert "newest history event" in str(refused.value)
    assert _current(migrated_engine) is not None and _current(migrated_engine)[0] == a
    # The control: the same change with its own new event.
    _designate(migrated_engine, b, a)
    assert _current(migrated_engine)[0] == b  # type: ignore[index]
    assert _history(migrated_engine) == [(None, a), (a, b), (b, a), (a, b)]


# --- an event without a designation ---------------------------------------------------------


def test_an_event_the_current_row_does_not_name_is_refused_at_commit(
    migrated_engine: Engine,
) -> None:
    current, never = _snapshots(migrated_engine, 2)
    designated = _designate(migrated_engine, current, None)
    # The attack: a history row "current -> never" with the current row left alone, which
    # would make `never` pass `has_been_current` and so be searchable by explicit scope.
    with pytest.raises(DBAPIError) as refused:
        with migrated_engine.begin() as connection:
            _event(connection, to=never, before=current)
    assert _sqlstate(refused) == "AM003", refused.value
    assert "when its transaction commits" in str(refused.value)
    with migrated_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM norm_current_snapshot_event WHERE to_snapshot_id = :s"
        ), {"s": never}).scalar_one() == 0
    assert _current(migrated_engine) == (current, designated)
    # The control: the same history row, with the current row moved to it.
    _designate(migrated_engine, never, current)
    assert _current(migrated_engine)[0] == never  # type: ignore[index]


def test_an_orphan_event_beside_a_real_designation_is_refused_at_commit(
    migrated_engine: Engine,
) -> None:
    """The check is per event, not per transaction: an orphan does not hide behind a
    designation committed with it, and two designations in one transaction are refused
    because the first one's event is no longer current at COMMIT."""
    first, second, never = _snapshots(migrated_engine, 3)
    _designate(migrated_engine, first, None)
    with pytest.raises(DBAPIError) as orphan:
        with migrated_engine.begin() as connection:
            _event(connection, to=never, before=first)
            event = _event(connection, to=second, before=first)
            _point(connection, second, event)
    assert _sqlstate(orphan) == "AM003", orphan.value
    with pytest.raises(DBAPIError) as twice:
        with migrated_engine.begin() as connection:
            event = _event(connection, to=second, before=first)
            _point(connection, second, event)
            event = _event(connection, to=never, before=second)
            _point(connection, never, event)
    assert _sqlstate(twice) == "AM003", twice.value
    assert _history(migrated_engine) == [(None, first)]
    assert _current(migrated_engine)[0] == first  # type: ignore[index]


# --- TRUNCATE -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "TRUNCATE TABLE norm_current_snapshot",
        "TRUNCATE TABLE norm_current_snapshot_event CASCADE",
        "TRUNCATE TABLE norm_current_snapshot, norm_current_snapshot_event",
        # The cascade every corpus reset would use reaches both tables.
        "TRUNCATE TABLE norms_snapshot CASCADE",
    ],
)
def test_truncate_cannot_erase_the_current_snapshot_or_its_history(
    migrated_engine: Engine, statement: str,
) -> None:
    first, second = _snapshots(migrated_engine, 2)
    _designate(migrated_engine, first, None)
    _designate(migrated_engine, second, first)
    with pytest.raises(DBAPIError) as refused:
        with migrated_engine.begin() as connection:
            connection.execute(text(statement))
    assert _sqlstate(refused) == "AM003", refused.value
    assert "is not truncated" in str(refused.value)
    assert _history(migrated_engine) == [(None, first), (first, second)]
    assert _current(migrated_engine)[0] == second  # type: ignore[index]


def test_only_the_owners_ddl_lifts_the_truncate_refusal(migrated_engine: Engine) -> None:
    """The control for the case above, and the suites' reset: the statement is well formed,
    the refusal is the trigger, and it is back -- enabled -- once the reset commits."""
    first = _snapshots(migrated_engine, 1)[0]
    _designate(migrated_engine, first, None)
    with migrated_engine.begin() as connection:
        truncate_tables(connection, ("norms_snapshot",))
    assert _history(migrated_engine) == [] and _current(migrated_engine) is None
    with migrated_engine.connect() as connection:
        enabled = dict(connection.execute(text(
            "SELECT tgname, tgenabled FROM pg_trigger WHERE tgname IN "
            "('trg_norm_current_snapshot_no_truncate', "
            "'trg_norm_current_snapshot_event_no_truncate')"
        )).all())
    assert enabled == {
        "trg_norm_current_snapshot_no_truncate": "O",
        "trg_norm_current_snapshot_event_no_truncate": "O",
    }
    second = _snapshots(migrated_engine, 1)[0]
    _designate(migrated_engine, second, None)
    with pytest.raises(DBAPIError) as refused:
        with migrated_engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE norms_snapshot CASCADE"))
    assert _sqlstate(refused) == "AM003", refused.value


# --- changed_at -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "named",
    [
        datetime(2000, 1, 1, tzinfo=timezone.utc),   # backdated below the history
        datetime(2999, 1, 1, tzinfo=timezone.utc),   # post-dated above every later change
    ],
    ids=["backdated", "post-dated"],
)
def test_an_explicit_changed_at_is_replaced_by_the_databases_clock(
    migrated_engine: Engine, named: datetime,
) -> None:
    first, second = _snapshots(migrated_engine, 2)
    _designate(migrated_engine, first, None)
    with migrated_engine.begin() as connection:
        started = connection.execute(text("SELECT now()")).scalar_one()
        event = _event(connection, to=second, before=first, changed_at=named)
        _point(connection, second, event)
        stamped = connection.execute(text(
            "SELECT changed_at FROM norm_current_snapshot_event WHERE event_id = :e"
        ), {"e": event}).scalar_one()
        finished = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
    assert stamped != named
    assert started <= stamped <= finished
    # So the next designation is still the newest event, and the listing's first row is the
    # current one -- a post-dated event would otherwise block every later change.
    third = _snapshots(migrated_engine, 1)[0]
    _designate(migrated_engine, third, second)
    with migrated_engine.connect() as connection:
        newest = connection.execute(text(
            "SELECT event_id FROM norm_current_snapshot_event "
            "ORDER BY changed_at DESC, event_id COLLATE \"C\" DESC LIMIT 1"
        )).scalar_one()
    assert _current(migrated_engine) == (third, newest)
