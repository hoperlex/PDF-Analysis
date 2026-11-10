"""`DECISION-MEMORY-01` phase M2: ``0061_decision_memory_m2`` -- the actor's key, the transition guard, the forget guard, the settings and the
read model, on a clone of the migrated schema, against real PostgreSQL.

Shown, each by a row that obeys next to a row that does not:

* the status event's actor is a ``RESTRICT`` foreign key to ``app_user`` (``D-393``), and a ``forget`` event carries the digest of the
  content it forgot;
* the transition rule is the database's too (``am_guard_decision_memory_status``): no second withdraw, no restore of an active case, nothing
  after a forget -- every refusal ``AM003``;
* the content tables refuse ``UPDATE`` always and ``DELETE`` unless a ``forget`` event of the same case was inserted by THE SAME
  transaction (``am_guard_decision_memory_forget``, ``D-394``): not another case's event, not a withdraw, not an event an earlier
  transaction committed, not one made in a savepoint; and the identity tables stay immutable;
* the settings journal is closed, immutable, defaults to nothing journalled, and an ``on`` needs the owner's permission;
* ``decision_memory_case_current`` reads the standing and the current verdict;
* the downgrade refuses over a status event or a setting and, with none, restores the old guards.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import DecisionMemoryStatusEventId
from tests.support.memory_seed import ensure_blob
from tests.support.memory_seed import seed_case as _seed_case

HEAD = "0062_hosts_stage_models"  # the head the fixture migrates to; 0061 is the migration under test, one step below it
PREVIOUS = "0060_run_from_stage"
CONTENT_TABLES = (
    "decision_memory_content", "decision_memory_decision_text", "decision_memory_evidence", "decision_memory_norm_ref",
    "decision_memory_crop",
)
IDENTITY_TABLES = ("decision_memory_case", "decision_memory_decision", "decision_memory_status_event")
BLOB = "blob_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64
REF = "owner message 2026-11-09, forget test"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


@pytest.fixture
def at_head(migrated_database: Any) -> Iterator[tuple[Engine, str]]:
    engine = create_database_engine(migrated_database)
    try:
        yield engine, migrated_database.url.render_as_string(hide_password=False)
    finally:
        engine.dispose()


def _admin(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())


def seed_case(connection: Connection, *, observation: str = "fobs_01ARZ3NDEKTSV4RRFFQ69G5FAV", crop: bool = True,
              verdicts: tuple[str, ...] = ("accept",)) -> dict[str, Any]:
    """The shared seed (``tests/support/memory_seed.py``) with this file's one Blob for the crop."""
    if crop:
        ensure_blob(connection, BLOB)
    return _seed_case(connection, observation=observation, blob=BLOB if crop else None, verdicts=verdicts)


def _status(connection: Connection, case_id: str, kind: str, actor: str, *, reason: str = "other", ref: str | None = None,
            digest: str | None = None) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
        "forgotten_content_sha256) VALUES (:id, :c, :k, :r, :a, :ref, :digest)"),
        {"id": DecisionMemoryStatusEventId.new().value, "c": case_id, "k": kind, "r": reason, "a": actor, "ref": ref, "digest": digest})


def _refusal(engine: Engine, setup: Any, statement: str, values: dict[str, Any] | None = None) -> str:
    """Run ``setup(connection)`` and then the statement in one transaction; the SQLSTATE and message of its refusal, or ``'accepted'``.
    The transaction is always rolled back, so nothing is left behind and the refusal does not abort the next try."""
    with engine.connect() as connection, connection.begin() as transaction:
        try:
            if setup is not None:
                setup(connection)
            try:
                connection.execute(text(statement), values or {})
            except DBAPIError as error:
                return f"{getattr(error.orig, 'sqlstate', '?')}: {error.orig}"
            return "accepted"
        finally:
            transaction.rollback()


@contextmanager
def committed(engine: Engine) -> Iterator[Connection]:
    with engine.begin() as connection:
        yield connection


# --- the migration's objects ----------------------------------------------------------------------------------------


def test_the_head_and_the_triggers_are_what_the_migration_declares(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        triggers = {tuple(row) for row in connection.execute(text(
            "SELECT c.relname, t.tgname, p.proname, t.tgtype::integer FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_proc p ON p.oid = t.tgfoid WHERE NOT t.tgisinternal AND starts_with(c.relname, 'decision_memory_')"))}
    expected = {(t, f"trg_{t}_forget_guard", "am_guard_decision_memory_forget", 27) for t in CONTENT_TABLES}
    expected |= {(t, f"trg_{t}_immutable", "am_immutable_row", 27) for t in (*IDENTITY_TABLES, "decision_memory_setting_event")}
    expected.add(("decision_memory_status_event", "trg_decision_memory_status_event_transition", "am_guard_decision_memory_status", 7))
    assert triggers == expected


def test_the_status_events_actor_is_a_restrict_key_to_app_user_and_a_forget_carries_its_digest(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    admin = _admin(engine)
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT confdeltype::text FROM pg_constraint WHERE conname = 'fk_decision_memory_status_event_actor'")).scalar_one() == "r"

    def insert(actor: str, **over: Any) -> str:
        holder: dict[str, str] = {}

        def setup(connection: Connection) -> None:
            holder["case"] = seed_case(connection)["case_id"]

        with engine.connect() as connection, connection.begin() as transaction:
            try:
                setup(connection)
                try:
                    _status(connection, holder["case"], over.pop("kind", "withdraw"), actor, **over)
                except DBAPIError as error:
                    return str(error.orig)
                return "accepted"
            finally:
                transaction.rollback()

    assert insert(admin) == "accepted"
    assert "fk_decision_memory_status_event_actor" in insert("usr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    # a forget names the owner's permission AND the digest of what it forgot, and nothing else carries either
    assert insert(admin, kind="forget", ref=REF, digest=SHA) == "accepted"
    assert "ck_decision_memory_status_event_forget_digest" in insert(admin, kind="forget", ref=REF)
    assert "ck_decision_memory_status_event_forget_digest" in insert(admin, kind="withdraw", digest=SHA)
    assert "ck_decision_memory_status_event_forgotten_content_sha256" in insert(admin, kind="forget", ref=REF, digest="A" * 64)


# --- the transition rule, repeated by the database -------------------------------------------------------------------


def test_the_database_repeats_the_transition_rule(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    admin = _admin(engine)

    def after(*kinds: str) -> Any:
        def setup(connection: Connection) -> None:
            case = seed_case(connection)["case_id"]
            setup.case = case  # type: ignore[attr-defined]
            for kind in kinds:
                _status(connection, case, kind, admin, ref=REF if kind == "forget" else None, digest=SHA if kind == "forget" else None)
        return setup

    def attempt(kinds: tuple[str, ...], kind: str) -> str:
        setup = after(*kinds)
        with engine.connect() as connection, connection.begin() as transaction:
            try:
                setup(connection)
                try:
                    _status(connection, setup.case, kind, admin, ref=REF if kind == "forget" else None,  # type: ignore[attr-defined]
                            digest=SHA if kind == "forget" else None)
                except DBAPIError as error:
                    return f"{getattr(error.orig, 'sqlstate', '?')}: {error.orig}"
                return "accepted"
            finally:
                transaction.rollback()

    allowed = [((), "withdraw"), ((), "forget"), (("withdraw",), "restore"), (("withdraw",), "forget"),
               (("withdraw", "restore"), "withdraw"), (("withdraw", "restore"), "forget")]
    refused = [((), "restore"), (("withdraw",), "withdraw"), (("withdraw", "restore"), "restore"),
               (("forget",), "withdraw"), (("forget",), "restore"), (("forget",), "forget"),
               (("withdraw", "forget"), "restore")]
    for kinds, kind in allowed:
        assert attempt(kinds, kind) == "accepted", (kinds, kind)
    for kinds, kind in refused:
        outcome = attempt(kinds, kind)
        assert outcome.startswith("AM003: state_transition_not_allowed"), (kinds, kind, outcome)


# --- the forget guard ---------------------------------------------------------------------------------------------


def _every_content_delete(case_id: str, decision_id: str) -> list[tuple[str, dict[str, str]]]:
    by_case = {"c": case_id}
    return [
        ("DELETE FROM decision_memory_crop WHERE case_id = :c", by_case),
        ("DELETE FROM decision_memory_evidence WHERE case_id = :c", by_case),
        ("DELETE FROM decision_memory_norm_ref WHERE case_id = :c", by_case),
        ("DELETE FROM decision_memory_decision_text WHERE memory_decision_id = :d", {"d": decision_id}),
        ("DELETE FROM decision_memory_content WHERE case_id = :c", by_case),
    ]


def test_a_content_row_is_never_updated_and_deleted_only_beside_a_forget_of_its_case_in_the_same_transaction(
    at_head: tuple[Engine, str]
) -> None:
    engine, _ = at_head
    admin = _admin(engine)
    holder: dict[str, Any] = {}

    def seed(connection: Connection) -> None:
        a = seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAA")
        b = seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAB")
        holder.update(a=a["case_id"], da=a["decisions"][0], b=b["case_id"], db=b["decisions"][0])

    def forgotten(connection: Connection) -> None:
        seed(connection)
        _status(connection, holder["a"], "forget", admin, ref=REF, digest=SHA)

    def deletes(setup: Any, which: str) -> list[str]:
        outcomes = []
        with engine.connect() as connection, connection.begin() as transaction:
            try:
                setup(connection)
                # in the order the foreign keys allow (crop, evidence, norm_ref, comment, content): an accepted delete stays
                for statement, values in _every_content_delete(holder[which], holder["d" + which]):
                    nested = connection.begin_nested()
                    try:
                        connection.execute(text(statement), values)
                        nested.commit()
                        outcomes.append("accepted")
                    except DBAPIError as error:
                        nested.rollback()
                        outcomes.append(f"{getattr(error.orig, 'sqlstate', '?')}")
            finally:
                transaction.rollback()
        return outcomes

    # no event at all: every content table refuses the delete
    assert deletes(seed, "a") == ["AM003"] * 5
    # a forget of THIS case in this transaction: every one is accepted
    assert deletes(forgotten, "a") == ["accepted"] * 5
    # a forget of ANOTHER case does not open this one
    assert deletes(forgotten, "b") == ["AM003"] * 5
    # a withdraw is not a forget
    assert deletes(lambda c: (seed(c), _status(c, holder["a"], "withdraw", admin)), "a") == ["AM003"] * 5

    # an UPDATE is refused even beside a forget, on every content table
    updates = {
        "decision_memory_content": "UPDATE decision_memory_content SET finding_text = 'x' WHERE case_id = :c",
        "decision_memory_evidence": "UPDATE decision_memory_evidence SET quote = 'x' WHERE case_id = :c",
        "decision_memory_norm_ref": "UPDATE decision_memory_norm_ref SET designation = 'x' WHERE case_id = :c",
        "decision_memory_crop": "UPDATE decision_memory_crop SET width_px = 1 WHERE case_id = :c",
        "decision_memory_decision_text": "UPDATE decision_memory_decision_text SET comment = 'x' WHERE memory_decision_id = :d",
    }
    for table, statement in updates.items():
        with engine.connect() as connection, connection.begin() as transaction:
            try:
                forgotten(connection)
                with pytest.raises(DBAPIError) as refused:
                    connection.execute(text(statement), {"c": holder["a"], "d": holder["da"]})
                assert refused.value.orig.sqlstate == "AM003", table  # type: ignore[union-attr]
            finally:
                transaction.rollback()


def test_a_forget_event_an_earlier_transaction_committed_does_not_open_the_guard(at_head: tuple[Engine, str]) -> None:
    """The guard reads the event's ``xmin``: a forget committed by another transaction -- or this one, in a savepoint -- is history,
    not permission. The operator tool inserts the event and deletes in ONE transaction; nothing else can."""
    engine, _ = at_head
    admin = _admin(engine)
    with committed(engine) as connection:
        case = seed_case(connection)
        _status(connection, case["case_id"], "forget", admin, ref=REF, digest=SHA)
    try:
        for statement, values in _every_content_delete(case["case_id"], case["decisions"][0]):
            assert _refusal(engine, None, statement, values).startswith("AM003"), statement

        # ... and a savepoint inside the deleting transaction is not "the same transaction" either (the event's xmin is the subtransaction's)
        other = {}

        def in_a_savepoint(connection: Connection) -> None:
            other.update(seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAW"))

        with engine.connect() as connection, connection.begin() as transaction:
            try:
                in_a_savepoint(connection)
                nested = connection.begin_nested()
                _status(connection, other["case_id"], "forget", admin, ref=REF, digest=SHA)
                nested.commit()
                with pytest.raises(DBAPIError) as refused:
                    connection.execute(text("DELETE FROM decision_memory_evidence WHERE case_id = :c"), {"c": other["case_id"]})
                assert refused.value.orig.sqlstate == "AM003"  # type: ignore[union-attr]
            finally:
                transaction.rollback()
    finally:
        # the committed rows are removed the way the tool removes them: the event is in the deleting transaction
        with committed(engine) as connection:
            connection.execute(text("SET LOCAL session_replication_role = replica"))
            for table in ("decision_memory_status_event", "decision_memory_decision_text", "decision_memory_decision",
                          "decision_memory_crop", "decision_memory_norm_ref", "decision_memory_evidence", "decision_memory_content",
                          "decision_memory_case"):
                connection.execute(text(f"DELETE FROM {table}"))
            connection.execute(text("DELETE FROM blob WHERE blob_id = :b"), {"b": BLOB})


def test_the_identity_tables_stay_immutable_even_beside_a_forget(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    admin = _admin(engine)
    holder: dict[str, Any] = {}

    def forgotten(connection: Connection) -> None:
        holder.update(seed_case(connection))
        _status(connection, holder["case_id"], "forget", admin, ref=REF, digest=SHA)

    for statement in ("DELETE FROM decision_memory_case WHERE true", "DELETE FROM decision_memory_decision WHERE true",
                      "DELETE FROM decision_memory_status_event WHERE true", "UPDATE decision_memory_case SET category = 'x'",
                      "UPDATE decision_memory_decision SET severity = 'critical'",
                      "UPDATE decision_memory_status_event SET reason_code = 'other'"):
        outcome = _refusal(engine, forgotten, statement)
        assert outcome.startswith("AM003") and "immutable once written" in outcome, (statement, outcome)


# --- the settings journal ---------------------------------------------------------------------------------------------


_SETTING = ("INSERT INTO decision_memory_setting_event (setting_name, revision, value, actor_user_uid, owner_permission_ref) "
            "VALUES (:n, :r, :v, :a, :ref)")


def test_the_settings_journal_is_closed_immutable_and_an_on_names_the_owners_permission(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    admin = _admin(engine)
    good = {"n": "data_class", "r": 1, "v": "real", "a": admin, "ref": None}
    assert _refusal(engine, None, _SETTING, good) == "accepted"
    assert _refusal(engine, None, _SETTING, {**good, "n": "training_use", "v": "off"}) == "accepted"
    assert _refusal(engine, None, _SETTING, {**good, "n": "training_use", "v": "on", "ref": REF}) == "accepted"
    for over, constraint in [
        ({"n": "retention"}, "ck_decision_memory_setting_event_setting_name"),
        ({"v": "production"}, "ck_decision_memory_setting_event_value"),
        ({"v": "on", "ref": REF}, "ck_decision_memory_setting_event_value_for_name"),  # on is not a data class
        ({"n": "training_use", "v": "real"}, "ck_decision_memory_setting_event_value_for_name"),
        ({"n": "training_use", "v": "on"}, "ck_decision_memory_setting_event_on_needs_permission"),
        ({"r": 0}, "ck_decision_memory_setting_event_revision"),
        ({"a": "admin"}, "ck_decision_memory_setting_event_actor_user_uid_format"),
        ({"a": "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"}, "fk_decision_memory_setting_event_actor"),
        ({"ref": ""}, "ck_decision_memory_setting_event_owner_permission_ref"),
    ]:
        outcome = _refusal(engine, None, _SETTING, {**good, **over})
        assert constraint in outcome, (over, outcome)
    with committed(engine) as connection:
        connection.execute(text(_SETTING), good)
    try:
        assert "pk_decision_memory_setting_event" in _refusal(engine, None, _SETTING, good)   # a revision is written once
        for statement in ("UPDATE decision_memory_setting_event SET value = 'test'", "DELETE FROM decision_memory_setting_event"):
            outcome = _refusal(engine, None, statement)
            assert outcome.startswith("AM003") and "immutable once written" in outcome, outcome
    finally:
        with committed(engine) as connection:
            connection.execute(text("SET LOCAL session_replication_role = replica"))
            connection.execute(text("DELETE FROM decision_memory_setting_event"))


# --- the read model ---------------------------------------------------------------------------------------------------


def test_the_view_reads_the_standing_from_the_latest_event_and_the_verdict_from_the_latest_decision(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    admin = _admin(engine)
    with engine.connect() as connection, connection.begin() as transaction:
        try:
            case = seed_case(connection, verdicts=("accept", "reject"))
            other = seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAB", crop=False)

            def row(case_id: str) -> Any:
                return connection.execute(text("SELECT * FROM decision_memory_case_current WHERE case_id = :c"), {"c": case_id}).mappings().one()

            fresh = row(case["case_id"])
            assert (fresh["status"], fresh["current_verdict"], fresh["decision_count"], fresh["status_event_id"]) == (
                "active", "rejected", 2, None)           # the later decision is the current one
            assert row(other["case_id"])["current_verdict"] == "accepted" and row(other["case_id"])["decision_count"] == 1

            _status(connection, case["case_id"], "withdraw", admin, reason="wrong_decision")
            withdrawn = row(case["case_id"])
            assert (withdrawn["status"], withdrawn["status_reason_code"]) == ("withdrawn", "wrong_decision")
            assert withdrawn["status_changed_at"] is not None and withdrawn["status_event_id"].startswith("dmw_")
            _status(connection, case["case_id"], "restore", admin, reason="other")
            assert row(case["case_id"])["status"] == "active" and row(other["case_id"])["status"] == "active"
            _status(connection, case["case_id"], "forget", admin, ref=REF, digest=SHA)
            assert row(case["case_id"])["status"] == "forgotten" and row(other["case_id"])["status"] == "active"
        finally:
            transaction.rollback()


# --- the downgrade ----------------------------------------------------------------------------------------------------


def test_the_downgrade_refuses_over_a_status_event_or_a_setting_and_otherwise_restores_the_old_guards(
    at_head: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_head
    admin = _admin(engine)
    with committed(engine) as connection:
        case = seed_case(connection)
        _status(connection, case["case_id"], "withdraw", admin)
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "holds status events or settings" in (refused.stdout + refused.stderr), refused.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD

    with committed(engine) as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        for table in ("decision_memory_status_event", "decision_memory_decision_text", "decision_memory_decision",
                      "decision_memory_crop", "decision_memory_norm_ref", "decision_memory_evidence", "decision_memory_content",
                      "decision_memory_case"):
            connection.execute(text(f"DELETE FROM {table}"))
        connection.execute(text("DELETE FROM blob WHERE blob_id = :b"), {"b": BLOB})
        connection.execute(text(_SETTING), {"n": "data_class", "r": 1, "v": "real", "a": admin, "ref": None})
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "holds status events or settings" in (refused.stdout + refused.stderr), refused.describe()

    with committed(engine) as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(text("DELETE FROM decision_memory_setting_event"))
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        triggers = {(t, n, f) for t, n, f in connection.execute(text(
            "SELECT c.relname, t.tgname, p.proname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_proc p ON p.oid = t.tgfoid "
            "WHERE NOT t.tgisinternal AND starts_with(c.relname, 'decision_memory_')"))}
        assert triggers == {(t, f"trg_{t}_immutable", "am_immutable_row")
                            for t in (*IDENTITY_TABLES, *CONTENT_TABLES)}
        assert connection.execute(text(
            "SELECT count(*) FROM pg_proc WHERE proname IN ('am_guard_decision_memory_forget', 'am_guard_decision_memory_status')")
        ).scalar_one() == 0
        assert connection.execute(text("SELECT to_regclass('decision_memory_case_current')")).scalar_one() is None
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
