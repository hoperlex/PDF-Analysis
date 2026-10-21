"""`W61-DISPATCHER-01`: ``0025_work_assignments`` on a populated ``0024`` database.

Against real PostgreSQL rows written at ``0024`` -- an account, a project with a document, a
published version and its expert classification:

* the upgrade creates two empty tables and a view beside them and changes no existing row;
* both tables refuse UPDATE and DELETE (``AM003``); the history's shape is checked (the six
  kinds, ``assigned`` first and only first, a new assignee only on ``reassigned``, a reason on
  every ``returned`` and only where a reason belongs, unique ``seq`` per assignment);
* an assignment without its ``assigned`` event is refused at COMMIT (``AM001``);
* every identity column carries its format CHECK, ``asg_`` included;
* every account column is a RESTRICT reference: an account named by any one of them alone
  cannot be deleted;
* the view derives the latest event and the current assignee from the history;
* the downgrade drops exactly the view, the two tables and the trigger function, keeps every
  ``0024`` row, and the head upgrades again.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from auditmanager.access.public import UserUid
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import AuditEventId, DocumentUid, ProjectUid, VersionUid, pattern_for

HEAD = "0025_work_assignments"  # this revision; every upgrade here targets it
PREVIOUS = "0024_version_classification"

ASSIGNMENT = "asg_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_ASSIGNMENT = "asg_01ARZ3NDEKTSV4RRFFQ69G5FAW"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _user(connection: Any) -> str:
    user = str(UserUid.new())
    connection.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash) VALUES (:u, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
        ),
        {"u": user, "login": user.lower(), "salt": "0" * 32, "hash": "0" * 64},
    )
    return user


def _seed_0024(connection: Any) -> dict[str, str]:
    ids = {
        "project": str(ProjectUid.new()),
        "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()),
        "expert": _user(connection),
        "admin": _user(connection),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'Школа')"), ids)
    connection.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title, section) "
            "VALUES (:document, :project, 'КЖ-1', 'KJ')"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "source_filename, media_type, byte_size, sha256, page_count) "
            "VALUES (:version, :document, 1, 'КЖ-1.pdf', 'application/pdf', 1024, :sha, 1)"
        ),
        {**ids, "sha": "c" * 64},
    )
    connection.execute(
        text(
            "INSERT INTO document_version_classification "
            "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
            "VALUES (:version, 'R', 'KJ', :expert)"
        ),
        ids,
    )
    return ids


def _assignment(
    connection: Any, ids: dict[str, str], uid: str = ASSIGNMENT, *, document: bool = True
) -> None:
    connection.execute(
        text(
            "INSERT INTO work_assignment (assignment_uid, project_uid, document_uid, "
            "assignee_user_uid, created_by_user_uid, note) "
            "VALUES (:a, :project, :document, :expert, :admin, 'проверить армирование')"
        ),
        {**ids, "a": uid, "document": ids["document"] if document else None},
    )


def _event(
    connection: Any,
    uid: str,
    seq: int,
    kind: str,
    actor: str,
    *,
    reason: str | None = None,
    new_assignee: str | None = None,
) -> None:
    connection.execute(
        text(
            "INSERT INTO work_assignment_event (event_id, assignment_uid, seq, kind, "
            "actor_user_uid, reason, new_assignee_user_uid) "
            "VALUES (:e, :a, :seq, :kind, :actor, :reason, :new)"
        ),
        {
            "e": str(AuditEventId.new()),
            "a": uid,
            "seq": seq,
            "kind": kind,
            "actor": actor,
            "reason": reason,
            "new": new_assignee,
        },
    )


@pytest.fixture
def at_previous(
    empty_database: Any, foundation_command: Any
) -> Iterator[tuple[Engine, str, dict[str, str]]]:
    url = empty_database.url.render_as_string(hide_password=False)
    upgraded = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_0024(connection)
        yield engine, url, ids
    finally:
        engine.dispose()


@pytest.fixture
def at_head(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> tuple[Engine, str, dict[str, str]]:
    engine, url, ids = at_previous
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    return engine, url, ids


def test_populated_0024_upgrades_and_no_existing_row_changes(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_previous
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('work_assignment')")).scalar_one() is None
        before = connection.execute(
            text(
                "SELECT p.name, d.display_title, d.section, v.sha256, c.section_code, "
                "c.confirmed_by_user_uid FROM project p JOIN document d USING (project_uid) "
                "JOIN document_version v USING (document_uid) "
                "JOIN document_version_classification c USING (version_uid)"
            )
        ).one()
        users_before = connection.execute(text("SELECT count(*) FROM app_user")).scalar_one()

    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        for relation in ("work_assignment", "work_assignment_event", "work_assignment_current"):
            assert connection.execute(text(f"SELECT count(*) FROM {relation}")).scalar_one() == 0
        after = connection.execute(
            text(
                "SELECT p.name, d.display_title, d.section, v.sha256, c.section_code, "
                "c.confirmed_by_user_uid FROM project p JOIN document d USING (project_uid) "
                "JOIN document_version v USING (document_uid) "
                "JOIN document_version_classification c USING (version_uid)"
            )
        ).one()
        assert tuple(after) == tuple(before) == ("Школа", "КЖ-1", "KJ", "c" * 64, "KJ", ids["expert"])
        assert connection.execute(text("SELECT count(*) FROM app_user")).scalar_one() == users_before


def test_both_tables_refuse_update_and_delete(at_head: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _assignment(connection, ids)
        _event(connection, ASSIGNMENT, 1, "assigned", ids["admin"])
    with engine.connect() as connection:
        for table, statement in (
            ("work_assignment", "UPDATE work_assignment SET note = 'другое' WHERE assignment_uid = :a"),
            ("work_assignment", "UPDATE work_assignment SET assignee_user_uid = :admin WHERE assignment_uid = :a"),
            ("work_assignment", "DELETE FROM work_assignment WHERE assignment_uid = :a"),
            ("work_assignment_event", "UPDATE work_assignment_event SET kind = 'cancelled' WHERE assignment_uid = :a"),
            ("work_assignment_event", "DELETE FROM work_assignment_event WHERE assignment_uid = :a"),
        ):
            # The WHERE matches a row, so a refusal cannot be an empty statement's silence.
            assert connection.execute(
                text(f"SELECT count(*) FROM {table} WHERE assignment_uid = :a"), {"a": ASSIGNMENT}
            ).scalar_one() == 1
            connection.rollback()
            with pytest.raises(DBAPIError) as refused:
                with connection.begin():
                    connection.execute(text(statement), {"a": ASSIGNMENT, "admin": ids["admin"]})
            assert _sqlstate(refused.value) == "AM003", statement
        assert connection.execute(
            text("SELECT count(*) FROM work_assignment_event WHERE assignment_uid = :a"),
            {"a": ASSIGNMENT},
        ).scalar_one() == 1


def test_an_assignment_without_its_assigned_event_is_refused_at_commit(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head
    with pytest.raises(DBAPIError) as refused:
        with engine.begin() as connection:
            _assignment(connection, ids)
    assert _sqlstate(refused.value) == "AM001"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM work_assignment")).scalar_one() == 0


@pytest.mark.parametrize(
    ("seq", "kind", "reason", "new_assignee", "expected"),
    [
        (2, "approved", None, None, "23514"),  # not one of the six kinds
        (2, "assigned", None, None, "23514"),  # assigned is the first event only
        (1, "started", None, None, "23514"),  # the first event is assigned
        (0, "assigned", None, None, "23514"),  # seq starts at 1
        (2, "returned", None, None, "23514"),  # a return carries its reason
        (2, "started", "почему-то", None, "23514"),  # a start carries none
        (2, "reassigned", None, None, "23514"),  # a reassignment names the new assignee
        (2, "cancelled", None, "expert", "23514"),  # only a reassignment names one
        (2, "returned", "", None, "23514"),  # an empty reason is not a reason
        (2, "returned", "я" * 2001, None, "23514"),  # bounded
        (1, "assigned", None, None, "23505"),  # one event per seq
        (2, "reassigned", None, "unknown", "23503"),  # the new assignee is an account
    ],
)
def test_the_history_shape_is_checked(
    at_head: tuple[Engine, str, dict[str, str]],
    seq: int,
    kind: str,
    reason: str | None,
    new_assignee: str | None,
    expected: str,
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _assignment(connection, ids)
        _event(connection, ASSIGNMENT, 1, "assigned", ids["admin"])
    named = {"expert": ids["expert"], "unknown": str(UserUid.new()), None: None}[new_assignee]
    with engine.connect() as connection:
        with pytest.raises(IntegrityError) as refused:
            with connection.begin():
                _event(connection, ASSIGNMENT, seq, kind, ids["expert"], reason=reason, new_assignee=named)
        assert _sqlstate(refused.value) == expected


def test_a_valid_history_is_accepted_and_the_view_derives_the_state(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        other_expert = _user(connection)
        _assignment(connection, ids)
        _event(connection, ASSIGNMENT, 1, "assigned", ids["admin"])
        _event(connection, ASSIGNMENT, 2, "started", ids["expert"])
        _event(connection, ASSIGNMENT, 3, "returned", ids["expert"], reason="нет исходных данных")
        _event(connection, ASSIGNMENT, 4, "reassigned", ids["admin"], new_assignee=other_expert)
        _event(connection, ASSIGNMENT, 5, "started", other_expert)
        _event(connection, ASSIGNMENT, 6, "cancelled", ids["admin"], reason="проект закрыт")
        _assignment(connection, ids, OTHER_ASSIGNMENT, document=False)
        _event(connection, OTHER_ASSIGNMENT, 1, "assigned", ids["admin"])
    with engine.connect() as connection:
        rows = {
            row.assignment_uid: row
            for row in connection.execute(
                text(
                    "SELECT assignment_uid, document_uid, first_assignee_user_uid, "
                    "current_assignee_user_uid, last_seq, last_kind, last_actor_user_uid, "
                    "last_reason FROM work_assignment_current"
                )
            )
        }
    first = rows[ASSIGNMENT]
    assert (first.first_assignee_user_uid, first.current_assignee_user_uid) == (ids["expert"], other_expert)
    assert (first.last_seq, first.last_kind, first.last_actor_user_uid, first.last_reason) == (
        6, "cancelled", ids["admin"], "проект закрыт",
    )
    second = rows[OTHER_ASSIGNMENT]
    assert second.document_uid is None
    assert (second.current_assignee_user_uid, second.last_kind, second.last_seq) == (ids["expert"], "assigned", 1)


def test_every_identity_column_carries_its_format_check(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, _ = at_head
    expected = {
        ("work_assignment", "assignment_uid"): "asg",
        ("work_assignment", "project_uid"): "prj",
        ("work_assignment", "document_uid"): "doc",
        ("work_assignment", "assignee_user_uid"): "usr",
        ("work_assignment", "created_by_user_uid"): "usr",
        ("work_assignment_event", "event_id"): "evt",
        ("work_assignment_event", "assignment_uid"): "asg",
        ("work_assignment_event", "actor_user_uid"): "usr",
        ("work_assignment_event", "new_assignee_user_uid"): "usr",
    }
    with engine.connect() as connection:
        definitions: dict[str, list[str]] = {}
        for table, definition in connection.execute(
            text(
                "SELECT t.relname, pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid WHERE c.contype = 'c' "
                "AND t.relname IN ('work_assignment', 'work_assignment_event')"
            )
        ):
            definitions.setdefault(table, []).append(definition)
    missing = [
        f"{table}.{column}"
        for (table, column), prefix in expected.items()
        if not any(
            column in definition and pattern_for(prefix) in definition
            for definition in definitions[table]
        )
    ]
    assert missing == []
    from auditmanager.dispatch.public import ASSIGNMENT_UID_PATTERN

    assert ASSIGNMENT_UID_PATTERN == pattern_for("asg")


@pytest.mark.parametrize(
    "column",
    [
        "work_assignment.assignee_user_uid",
        "work_assignment.created_by_user_uid",
        "work_assignment_event.actor_user_uid",
        "work_assignment_event.new_assignee_user_uid",
    ],
)
def test_each_account_column_alone_makes_an_account_undeletable(
    at_head: tuple[Engine, str, dict[str, str]], column: str
) -> None:
    """The subject is a fresh account named by exactly one column of this revision."""
    engine, _, ids = at_head
    with engine.begin() as connection:
        subject = _user(connection)
        bystander = _user(connection)
        people = {"expert": bystander, "admin": bystander}
        if column == "work_assignment.assignee_user_uid":
            people["expert"] = subject
        elif column == "work_assignment.created_by_user_uid":
            people["admin"] = subject
        _assignment(connection, {**ids, **people})
        _event(connection, ASSIGNMENT, 1, "assigned", bystander)
        if column == "work_assignment_event.actor_user_uid":
            _event(connection, ASSIGNMENT, 2, "cancelled", subject)
        elif column == "work_assignment_event.new_assignee_user_uid":
            _event(connection, ASSIGNMENT, 2, "reassigned", bystander, new_assignee=subject)
    with engine.connect() as connection:
        with pytest.raises(IntegrityError) as refused:
            with connection.begin():
                connection.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": subject})
        assert _sqlstate(refused.value) == "23503", column
        rules = dict(
            connection.execute(
                text(
                    "SELECT conname, confdeltype FROM pg_constraint "
                    "WHERE conrelid IN ('work_assignment'::regclass, "
                    "'work_assignment_event'::regclass) AND contype = 'f'"
                )
            ).all()
        )
    assert set(rules.values()) == {"r"}, rules  # every foreign key here is RESTRICT


def test_the_downgrade_drops_only_this_revision_and_upgrades_again(
    at_head: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_head
    with engine.begin() as connection:
        _assignment(connection, ids)
        _event(connection, ASSIGNMENT, 1, "assigned", ids["admin"])
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    assert "1 assignment(s) and 1 history event(s)" in downgraded.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        for relation in ("work_assignment", "work_assignment_event", "work_assignment_current"):
            assert connection.execute(text(f"SELECT to_regclass('{relation}')")).scalar_one() is None
        assert connection.execute(
            text("SELECT count(*) FROM pg_proc WHERE proname = 'am_require_work_assignment_event'")
        ).scalar_one() == 0
        kept = connection.execute(
            text(
                "SELECT (SELECT count(*) FROM project), (SELECT count(*) FROM document), "
                "(SELECT count(*) FROM document_version_classification), "
                "(SELECT count(*) FROM app_user WHERE user_uid IN (:expert, :admin))"
            ),
            ids,
        ).one()
        assert tuple(kept) == (1, 1, 1, 2)
    reupgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert reupgraded.returncode == 0, reupgraded.describe()
