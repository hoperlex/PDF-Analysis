"""`CRIT-SEAL-53`: ``0066_precedents_wave5`` -- failure patterns, parameter facts and cross-document evidence (plan-v5 section 3.7), against real PostgreSQL.

Each rule shown by a row that obeys next to a row that does not, with every trigger on:

* **the step changes no stored row**, and creates the four tables and the view empty;
* **a pattern** is a content table of a case: it takes the forget guard (``DELETE`` only beside a ``forget`` of its case in the same transaction, ``UPDATE``
  never) and the guard on ``INSERT`` (nothing is added for a forgotten case); one pattern per representative case; the counts are consistent;
* **its status journal**: ``proposed`` first and only first, ``approved`` from ``proposed`` or ``suspended``, ``rejected`` from ``proposed``, ``suspended``
  from ``approved`` -- the transition rule is the database's; the number is gapless per pattern; who and why are tied to the status (an expert review names
  an account and a command, the algorithm none); the view reads the latest event and says NULL for a pattern with none;
* **a parameter fact** and **cross evidence** are immutable, and the cross evidence names **another** version of the finding's **own** project;
* ``parameter_mismatch`` is a category of a finding and of an observation, and no other new value is;
* **the downgrade is refused while any of it exists**, and only then.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    CommandId,
    DecisionMemoryPatternId,
    DecisionMemoryPatternStatusEventId,
    DecisionMemoryStatusEventId,
    DocumentUid,
    VersionUid,
)
from tests.integration.db.test_precedents_seal_migration import _admin, _finding, _run
from tests.support.memory_seed import seed_case

THIS = "0066_precedents_wave5"
PREVIOUS = "0065_norm_crop_render"
REF = "owner message 2026-11-11, forget test"
SHA = "a" * 64
FACT = "ppf_" + "a" * 32
NEW_TABLES = ("decision_memory_pattern", "decision_memory_pattern_status_event", "project_parameter_fact", "finding_cross_evidence")


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _refused(engine: Engine, write: Any, sqlstate: str) -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


def _accepted(engine: Engine, write: Any) -> None:
    with engine.connect() as connection, connection.begin() as transaction:
        try:
            write(connection)
        finally:
            transaction.rollback()


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _forget(connection: Connection, case_id: str, actor: str) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
        "forgotten_content_sha256) VALUES (:id, :c, 'forget', 'other', :a, :ref, :digest)"),
        {"id": DecisionMemoryStatusEventId.new().value, "c": case_id, "a": actor, "ref": REF, "digest": SHA})


def _command(connection: Connection) -> str:
    command = CommandId.new().value
    connection.execute(text(
        "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
        "VALUES (:c, 'review_decision_pattern', :k, :f)"), {"c": command, "k": "key-" + command[-8:], "f": SHA})
    return command


def _pattern(connection: Connection, case_id: str, **over: Any) -> str:
    values = {"id": DecisionMemoryPatternId.new().value, "c": case_id, "section": "AR", "klass": "test", "t": "Размер указан в другом разделе.",
              "m": 8, "r": 7, "v": "pattern-rule-v1", **over}
    connection.execute(text(
        "INSERT INTO decision_memory_pattern (pattern_id, case_id, section_code, data_class, pattern_text, member_count, refusal_count, "
        "algorithm_version) VALUES (:id, :c, :section, :klass, :t, :m, :r, :v)"), values)
    return str(values["id"])


def _event(connection: Connection, pattern: str, case_id: str, number: int, status: str, cause: str, *, actor: str | None = None,
           command: str | None = None, counts: tuple[int, int] | None = None) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_pattern_status_event (pattern_event_id, pattern_id, case_id, event_no, status, cause, actor_user_uid, "
        "command_id, member_count, refusal_count) VALUES (:id, :p, :c, :n, :s, :cause, :a, :cmd, :m, :r)"),
        {"id": DecisionMemoryPatternStatusEventId.new().value, "p": pattern, "c": case_id, "n": number, "s": status, "cause": cause, "a": actor,
         "cmd": command, "m": None if counts is None else counts[0], "r": None if counts is None else counts[1]})


def _proposed(connection: Connection, case_id: str) -> str:
    pattern = _pattern(connection, case_id)
    _event(connection, pattern, case_id, 1, "proposed", "proposed")
    return pattern


def _review(connection: Connection, pattern: str, case_id: str, number: int, status: str, admin: str) -> None:
    _event(connection, pattern, case_id, number, status, "expert_review", actor=admin, command=_command(connection))


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


def test_the_step_creates_the_four_tables_and_the_view_empty(at_head: Engine) -> None:
    for table in NEW_TABLES:
        assert _count(at_head, table) == 0, table
    with at_head.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
        assert connection.execute(text("SELECT count(*) FROM decision_memory_pattern_current")).scalar_one() == 0
        triggers = {row[0] for row in connection.execute(text(
            "SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal AND c.relname = ANY(:n)"),
            {"n": list(NEW_TABLES)})}
    assert triggers == {
        "trg_decision_memory_pattern_forget_guard", "trg_decision_memory_pattern_forgotten_insert",
        "trg_decision_memory_pattern_status_event_forget_guard", "trg_decision_memory_pattern_status_event_forgotten_insert",
        "trg_decision_memory_pattern_status_event_number", "trg_decision_memory_pattern_status_event_transition",
        "trg_project_parameter_fact_immutable", "trg_finding_cross_evidence_immutable", "trg_finding_cross_evidence_version"}


def test_a_pattern_is_one_per_case_with_consistent_counts_and_a_closed_shape(at_head: Engine) -> None:
    with at_head.begin() as connection:
        case = seed_case(connection)["case_id"]
        _proposed(connection, case)
    # one pattern per representative case
    _refused(at_head, lambda c: _pattern(c, case), "23505")
    with at_head.begin() as connection:
        other = seed_case(connection)["case_id"]
    for over, sqlstate in (({"m": 3, "r": 4}, "23514"), ({"r": 0}, "23514"), ({"m": 0, "r": 0}, "23514"), ({"t": ""}, "23514"), ({"t": "x" * 2001}, "23514"),
                           ({"klass": "live"}, "23514"), ({"section": ""}, "23514"), ({"v": "Rule V1"}, "23514"),
                           ({"c": "dmc_01M2545JSD15ETSNNV904X991K"}, "23503")):
        _refused(at_head, lambda c, over=over: _pattern(c, over.get("c", other), **{k: v for k, v in over.items() if k != "c"}), sqlstate)
    _accepted(at_head, lambda c: _pattern(c, other, t="x" * 2000))
    # a pattern is never updated
    with at_head.connect() as connection:
        pid = connection.execute(text("SELECT pattern_id FROM decision_memory_pattern")).scalar_one()
    _refused(at_head, lambda c: c.execute(text("UPDATE decision_memory_pattern SET pattern_text = 'rewritten' WHERE pattern_id = :p"), {"p": pid}), "AM003")


def test_the_journal_has_the_databases_own_transition_rule(at_head: Engine) -> None:
    admin = _admin(at_head)
    with at_head.begin() as connection:
        case = seed_case(connection)["case_id"]
        pattern = _pattern(connection, case)
    # the first event is the proposal, and only the first
    for status, cause, kw in (("approved", "expert_review", {"actor": admin}), ("suspended", "group_dissolved", {"counts": (1, 1)})):
        _refused(at_head, lambda c, status=status, cause=cause, kw=kw: _event(
            c, pattern, case, 1, status, cause, command=_command(c) if cause == "expert_review" else None, **kw), "23514")
    with at_head.begin() as connection:
        _event(connection, pattern, case, 1, "proposed", "proposed")
    _refused(at_head, lambda c: _event(c, pattern, case, 2, "proposed", "proposed"), "23514")                  # a proposal is event 1 only
    _refused(at_head, lambda c: _review(c, pattern, case, 2, "suspended", admin), "AM003")                     # proposed -> suspended
    _refused(at_head, lambda c: _review(c, pattern, case, 3, "approved", admin), "AM001")                      # a gap in the numbers
    with at_head.begin() as connection:
        _review(connection, pattern, case, 2, "approved", admin)                                                # proposed -> approved
    _refused(at_head, lambda c: _review(c, pattern, case, 3, "approved", admin), "AM003")                      # approved -> approved
    _refused(at_head, lambda c: _review(c, pattern, case, 3, "rejected", admin), "AM003")                      # approved -> rejected
    with at_head.begin() as connection:
        _event(connection, pattern, case, 3, "suspended", "group_dissolved", counts=(2, 2))                    # the algorithm suspends a dissolved group
    with at_head.connect() as connection:
        row = connection.execute(text("SELECT status, status_cause, status_event_no FROM decision_memory_pattern_current")).one()
    assert tuple(row) == ("suspended", "group_dissolved", 3)
    with at_head.begin() as connection:
        _review(connection, pattern, case, 4, "approved", admin)                                                # suspended -> approved (resumed)
    with at_head.connect() as connection:
        assert connection.execute(text("SELECT status FROM decision_memory_pattern_current")).scalar_one() == "approved"
    # a rejected pattern is final
    with at_head.begin() as connection:
        second = seed_case(connection)["case_id"]
        pattern2 = _proposed(connection, second)
        _review(connection, pattern2, second, 2, "rejected", admin)
    for status in ("approved", "suspended", "rejected"):
        _refused(at_head, lambda c, status=status: _review(c, pattern2, second, 3, status, admin), "AM003")
    # the journal is append-only: no update
    _refused(at_head, lambda c: c.execute(text("UPDATE decision_memory_pattern_status_event SET status = 'approved'")), "AM003")


def test_who_and_why_are_tied_to_the_status(at_head: Engine) -> None:
    admin = _admin(at_head)
    with at_head.begin() as connection:
        case = seed_case(connection)["case_id"]
        pattern = _proposed(connection, case)
    # an expert review names an account and the command; the algorithm names neither; a suspension for a dissolved group carries the counts
    _refused(at_head, lambda c: _event(c, pattern, case, 2, "approved", "expert_review", actor=admin), "23514")           # no command
    _refused(at_head, lambda c: _event(c, pattern, case, 2, "approved", "expert_review", command=_command(c)), "23514")   # no actor
    _refused(at_head, lambda c: _event(c, pattern, case, 2, "approved", "group_dissolved", counts=(1, 1)), "23514")        # not the algorithm's status
    _refused(at_head, lambda c: _event(c, pattern, case, 2, "proposed", "expert_review", actor=admin, command=_command(c)), "23514")
    _refused(at_head, lambda c: _review(c, pattern, case, 2, "proposed", admin), "23514")
    _refused(at_head, lambda c: _event(c, pattern, case, 2, "approved", "proposed"), "23514")
    _refused(at_head, lambda c: _event(c, pattern, case, 2, "approved", "expert_review", actor=admin, command=_command(c), counts=(3, 4)), "23514")
    _refused(at_head, lambda c: c.execute(text(
        "INSERT INTO decision_memory_pattern_status_event (pattern_event_id, pattern_id, case_id, event_no, status, cause, member_count) "
        "VALUES (:id, :p, :c, 2, 'suspended', 'group_dissolved', 2)"),
        {"id": DecisionMemoryPatternStatusEventId.new().value, "p": pattern, "c": case}), "23514")                          # counts are a pair
    # the event of another case's pattern is refused: (pattern, case) is a composite key
    with at_head.begin() as connection:
        other = seed_case(connection)["case_id"]
    _refused(at_head, lambda c: _event(c, pattern, other, 2, "approved", "expert_review", actor=admin, command=_command(c)), "23503")


def test_a_pattern_without_an_event_has_no_status_and_is_never_read_as_approved(at_head: Engine) -> None:
    with at_head.begin() as connection:
        case = seed_case(connection)["case_id"]
        _pattern(connection, case)
    with at_head.connect() as connection:
        row = connection.execute(text("SELECT status, status_cause FROM decision_memory_pattern_current")).one()
        assert tuple(row) == (None, None)
        assert connection.execute(text("SELECT count(*) FROM decision_memory_pattern_current WHERE status = 'approved'")).scalar_one() == 0


@pytest.mark.parametrize("table", ["decision_memory_pattern", "decision_memory_pattern_status_event"])
def test_a_pattern_and_its_journal_leave_only_beside_a_forget_of_the_case_and_take_nothing_new_after_it(at_head: Engine, table: str) -> None:
    admin = _admin(at_head)
    with at_head.begin() as connection:
        case = seed_case(connection)["case_id"]
        pattern = _proposed(connection, case)
    # a DELETE alone is refused (the journal first: it references the pattern)
    _refused(at_head, lambda c: c.execute(text(f"DELETE FROM {table}")), "AM003")
    # beside a forget of the case in the same transaction the journal then the pattern may go
    with at_head.begin() as connection:
        _forget(connection, case, admin)
        connection.execute(text("DELETE FROM decision_memory_pattern_status_event WHERE case_id = :c"), {"c": case})
        connection.execute(text("DELETE FROM decision_memory_pattern WHERE case_id = :c"), {"c": case})
    assert _count(at_head, "decision_memory_pattern") == 0 and _count(at_head, "decision_memory_pattern_status_event") == 0
    # nothing is added for a forgotten case
    _refused(at_head, lambda c: _pattern(c, case), "AM003")
    _refused(at_head, lambda c: _event(c, pattern, case, 1, "proposed", "proposed"), "AM003")


def _fact(connection: Connection, run: str, **over: Any) -> None:
    values = {"run": run, "ref": FACT, "type": "area", "name": "Площадь застройки", "value": "1200", "number": 1200, "unit": "м2", "subject": None, "page": 3,
              "quote": "Площадь 1200 м2", "start": 10, "end": 25, **over}
    connection.execute(text(
        "INSERT INTO project_parameter_fact (run_id, fact_ref, parameter_type, name, value_text, value_number, unit, subject, page_number, quote, "
        "char_start, char_end) VALUES (:run, :ref, :type, :name, :value, :number, :unit, :subject, :page, :quote, :start, :end)"), values)


def test_a_parameter_fact_is_keyed_by_run_and_reference_and_is_immutable(at_head: Engine) -> None:
    with at_head.begin() as connection:
        ids = _run(connection)
        _fact(connection, ids["run"])
        _fact(connection, ids["run"], ref="ppf_" + "b" * 32, unit=None, number=None, value="не менее 2 этажей")
    _refused(at_head, lambda c: _fact(c, ids["run"]), "23505")
    for over in ({"ref": "ppf_short"}, {"type": "colour"}, {"name": ""}, {"value": ""}, {"unit": ""}, {"subject": ""}, {"page": 0}, {"quote": ""},
                 {"start": -1}, {"end": 10}, {"end": 26}):
        _refused(at_head, lambda c, over=over: _fact(c, ids["run"], **{"ref": "ppf_" + "c" * 32, **over}), "23514")
    _refused(at_head, lambda c: _fact(c, "run_01M2545JSD15ETSNNV904X991K", ref="ppf_" + "d" * 32), "23503")
    for statement in ("UPDATE project_parameter_fact SET unit = 'м'", "DELETE FROM project_parameter_fact"):
        _refused(at_head, lambda c, statement=statement: c.execute(text(statement)), "AM003")


def _cross(connection: Connection, observation: str, version: str, **over: Any) -> None:
    values = {"o": observation, "n": 0, "v": version, "page": 2, "quote": "Площадь 1250 м2", "start": 0, "end": 15, **over}
    connection.execute(text(
        "INSERT INTO finding_cross_evidence (finding_observation_id, evidence_ordinal, version_uid, page_number, quote, char_start, char_end) "
        "VALUES (:o, :n, :v, :page, :quote, :start, :end)"), values)


def _second_version(connection: Connection, ids: dict[str, str]) -> str:
    version = str(VersionUid.new())
    connection.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
        "VALUES (:v, :d, 2, 'application/pdf', 1, :sha, 1)"), {"v": version, "d": ids["document"], "sha": SHA})
    return version


def test_cross_evidence_names_another_version_of_the_findings_own_project_and_is_immutable(at_head: Engine) -> None:
    with at_head.begin() as connection:
        ids = _run(connection)
        _, observation = _finding(connection, ids, category="parameter_mismatch")
        other = _second_version(connection, ids)
        stranger = _run(connection)["version"]
    with at_head.begin() as connection:
        _cross(connection, observation, other)
    _refused(at_head, lambda c: _cross(c, observation, other), "23505")                                            # (observation, ordinal) is the key
    _refused(at_head, lambda c: _cross(c, observation, ids["version"], n=1), "AM003")                             # the finding's own version is not cross evidence
    _refused(at_head, lambda c: _cross(c, observation, stranger, n=1), "AM003")                                    # a version of another project
    _refused(at_head, lambda c: _cross(c, observation, "ver_01M2545JSD15ETSNNV904X991K", n=1), "AM003")           # no such version: not in the observation's project
    for over in ({"page": 0}, {"quote": ""}, {"start": -1}, {"end": 5}, {"end": 16}, {"n": -1}):
        _refused(at_head, lambda c, over=over: _cross(c, observation, other, **{"n": 5, **over}), "23514")
    for statement in ("UPDATE finding_cross_evidence SET page_number = 3", "DELETE FROM finding_cross_evidence"):
        _refused(at_head, lambda c, statement=statement: c.execute(text(statement)), "AM003")


def test_parameter_mismatch_is_a_category_and_no_other_new_value_is(at_head: Engine) -> None:
    with at_head.begin() as connection:
        ids = _run(connection)
        _finding(connection, ids, category="parameter_mismatch")
    for category in ("parameter_mismatches", "unit_mismatch", "cross_check"):
        _refused(at_head, lambda c, category=category: _finding(c, _run(c), category=category), "23514")
    with at_head.connect() as connection:
        for table, constraint in (("finding", "ck_finding_category"), ("finding_observation", "ck_finding_observation_category")):
            definition = connection.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n AND conrelid = CAST(:t AS regclass)"), {"n": constraint, "t": table}).scalar_one()
            assert all(value in definition for value in ("parameter_mismatch", "cross_source", "drawing_discrepancy", "sound")), definition


def test_the_downgrade_is_refused_while_any_of_it_exists_and_only_then(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    admin = _admin(engine)

    def refused(*needles: str) -> None:
        answer = foundation_command(_alembic("downgrade", PREVIOUS), url)
        output = answer.stdout + answer.stderr
        assert answer.returncode != 0 and "refusing to downgrade 0066_precedents_wave5" in output, answer.describe()
        for needle in needles:
            assert needle in output, (needle, output)

    def clear(*tables: str) -> None:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL session_replication_role = replica"))
            for table in tables:
                connection.execute(text(f"DELETE FROM {table}"))

    # a pattern with its journal
    with engine.begin() as connection:
        case = seed_case(connection)["case_id"]
        _proposed(connection, case)
    refused("decision_memory_pattern")
    clear("decision_memory_pattern_status_event", "decision_memory_pattern", "decision_memory_decision_text", "decision_memory_decision", "decision_memory_crop",
          "decision_memory_norm_ref", "decision_memory_evidence", "decision_memory_content", "decision_memory_case")
    # a parameter fact
    with engine.begin() as connection:
        ids = _run(connection)
        _fact(connection, ids["run"])
    refused("project_parameter_fact")
    clear("project_parameter_fact")
    # cross evidence, and a finding of the new category
    with engine.begin() as connection:
        _, observation = _finding(connection, ids, category="parameter_mismatch")
        _cross(connection, observation, _second_version(connection, ids))
    refused("finding_cross_evidence", "parameter_mismatch")
    clear("finding_cross_evidence")
    refused("parameter_mismatch")
    clear("finding_observation", "finding", "audit_run", "document_version", "document", "project")
    assert admin  # the journal's actor exists at every step

    # nothing left: the downgrade restores the schema of 0065
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        assert connection.execute(text("SELECT count(*) FROM pg_class WHERE relname = ANY(:t)"), {"t": [*NEW_TABLES, "decision_memory_pattern_current"]}).scalar_one() == 0
        assert connection.execute(text(
            "SELECT count(*) FROM pg_proc WHERE proname IN ('am_guard_decision_memory_pattern_status', 'am_check_finding_cross_evidence')")).scalar_one() == 0
        for table, constraint in (("finding", "ck_finding_category"), ("finding_observation", "ck_finding_observation_category")):
            definition = connection.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n AND conrelid = CAST(:t AS regclass)"), {"n": constraint, "t": table}).scalar_one()
            assert "parameter_mismatch" not in definition and "cross_source" in definition, definition
    upgraded = foundation_command(_alembic("upgrade", THIS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
