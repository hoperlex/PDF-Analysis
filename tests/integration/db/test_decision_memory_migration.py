"""`ADR-0027`, phase M1: ``0059_decision_memory`` creates eight append-only tables that hold the case of an expert decision.

On a clone of the migrated schema, against real PostgreSQL:

* every table refuses ``UPDATE`` and ``DELETE`` (``am_immutable_row``), and the application's idea of identity is held by CHECKs
  that keep their names -- each is proved able to fail by a row that breaks it, next to the row that obeys it;
* no table has a foreign key into a project, a document, a finding or the ledger: the only references are between memory tables,
  to ``blob`` and, for a status event, to ``command_record``;
* one case per observation and one memory decision per ledger event (the two UNIQUE constraints that make capture idempotent);
* the downgrade REFUSES while any memory row exists, leaves the head where it was, and with the tables empty drops them, after
  which the revision upgrades once more.

Rows are written as the lane's superuser through a transaction that is rolled back, so nothing is left behind; the downgrade tests
plant a row with the guards off (``session_replication_role = replica``) and remove it the same way.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    DecisionMemoryCaseId,
    DecisionMemoryCropId,
    DecisionMemoryDecisionId,
    DecisionMemoryStatusEventId,
)

HEAD = "0065_norm_crop_render"  # the head the fixture migrates to; 0059 is the migration under test, six steps below it
#: `0061` (phase M2) adds the settings' journal to the family and replaces the content tables' guard; its own test is `test_decision_memory_m2_migration.py`.
M2_TABLES = {"decision_memory_setting_event"}
CONTENT_TABLES = {"decision_memory_content", "decision_memory_decision_text", "decision_memory_evidence", "decision_memory_norm_ref", "decision_memory_crop"}
#: `0064_precedents_seal` (`CRIT-SEAL-50`) adds seven more tables whose names start with the family's: four on the content side of a case (KEEP: comments,
#: block evidence, the encoder's queue and the vectors) and three of a run's own (PRODUCT: the probe, the pass and its advice), which point into the
#: product by design (its own test is `test_precedents_seal_migration.py`).
SEAL_CONTENT_TABLES = {"decision_memory_comment", "decision_memory_block_evidence", "decision_memory_embedding_intent", "decision_memory_embedding"}
SEAL_PRODUCT_TABLES = {"decision_memory_probe", "decision_memory_precedent_run", "decision_memory_precedent_advice"}
SEAL_TRIGGERS = {
    ("decision_memory_comment", "trg_decision_memory_comment_forget_guard", "am_guard_decision_memory_forget", 27),
    ("decision_memory_comment", "trg_decision_memory_comment_forgotten_insert", "am_guard_decision_memory_forgotten_insert", 7),
    ("decision_memory_block_evidence", "trg_decision_memory_block_evidence_forget_guard", "am_guard_decision_memory_forget", 27),
    ("decision_memory_block_evidence", "trg_decision_memory_block_evidence_forgotten_insert", "am_guard_decision_memory_forgotten_insert", 7),
    ("decision_memory_embedding", "trg_decision_memory_embedding_forget_guard", "am_guard_decision_memory_forget", 27),
    ("decision_memory_embedding", "trg_decision_memory_embedding_forgotten_insert", "am_guard_decision_memory_forgotten_insert", 7),
    ("decision_memory_embedding_intent", "trg_decision_memory_embedding_intent_forget_guard", "am_guard_decision_memory_forget", 11),
    ("decision_memory_embedding_intent", "trg_decision_memory_embedding_intent_forgotten_insert", "am_guard_decision_memory_forgotten_insert", 7),
    ("decision_memory_embedding_intent", "trg_decision_memory_embedding_intent_frozen_guard", "am_guard_frozen_columns", 19),
    ("decision_memory_precedent_advice", "trg_decision_memory_precedent_advice_immutable", "am_immutable_row", 27),
    ("decision_memory_precedent_run", "trg_decision_memory_precedent_run_frozen_guard", "am_guard_frozen_columns", 19),
    ("decision_memory_probe", "trg_decision_memory_probe_frozen_guard", "am_guard_frozen_columns", 19),
    ("decision_memory_probe", "trg_decision_memory_probe_write_once", "am_guard_write_once_columns", 19),
}
PREVIOUS = "0058_finding_decision_origin"
TABLES = (
    "decision_memory_case", "decision_memory_decision", "decision_memory_decision_text", "decision_memory_status_event",
    "decision_memory_content", "decision_memory_evidence", "decision_memory_norm_ref", "decision_memory_crop",
)

OBSERVATION = "fobs_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SOURCE = "dec_01ARZ3NDEKTSV4RRFFQ69G5FAV"
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
BLOB = "blob_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


@pytest.fixture
def at_head(migrated_database: Any) -> Iterator[tuple[Engine, str]]:
    engine = create_database_engine(migrated_database)
    try:
        yield engine, migrated_database.url.render_as_string(hide_password=False)
    finally:
        engine.dispose()


def _head(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


@contextmanager
def _unguarded(engine: Engine) -> Iterator[Connection]:
    """A committed transaction in which foreign keys and triggers are off (the lane's database user is a superuser)."""
    with engine.begin() as connection:
        assert connection.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar_one()
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        yield connection


def _case_values(**over: Any) -> dict[str, Any]:
    values: dict[str, Any] = dict(
        case_id=DecisionMemoryCaseId.new().value, observation=OBSERVATION, finding="fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        project="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", document="doc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        version="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", run="run_01ARZ3NDEKTSV4RRFFQ69G5FAV", category="internal_contradiction",
        section="AR", data_class="test", crop_state="none_available", capture_version="dm-capture/1", sha=SHA,
    )
    values.update(over)
    return values


_CASE = (
    "INSERT INTO decision_memory_case (case_id, origin_observation_id, origin_finding_uid, origin_project_uid, "
    "origin_document_uid, origin_version_uid, origin_run_id, category, section_code, data_class, crop_state, "
    "capture_version, content_sha256) VALUES (:case_id, :observation, :finding, :project, :document, :version, :run, "
    ":category, :section, :data_class, :crop_state, :capture_version, :sha)"
)


def _decision(case_id: str, **over: Any) -> tuple[str, dict[str, Any]]:
    values: dict[str, Any] = dict(
        id=DecisionMemoryDecisionId.new().value, case_id=case_id, source=SOURCE, event_type="accept", verdict="accepted",
        severity=None, author=USER, origin_kind="direct",
    )
    values.update(over)
    return (
        "INSERT INTO decision_memory_decision (memory_decision_id, case_id, source_decision_id, event_type, verdict, "
        "severity, author_user_uid, origin_kind, decided_at) VALUES (:id, :case_id, :source, :event_type, :verdict, "
        ":severity, :author, :origin_kind, now())",
        values,
    )


def _breaks(engine: Engine, constraint: str, statement: str, values: dict[str, Any], *, before: tuple[str, dict[str, Any]] | None = None) -> bool:
    """Whether the statement is refused by exactly this constraint (any other refusal is a defect of the test)."""
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            try:
                if before is not None:
                    connection.execute(text(before[0]), before[1])
                connection.execute(text(statement), values)
            finally:
                transaction.rollback()
    except DBAPIError as error:
        assert constraint in str(error.orig), error
        return True
    return False


def _breaks_after(engine: Engine, constraint: str, setup: list[tuple[str, dict[str, Any]]], statement: str, values: dict[str, Any]) -> bool:
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            try:
                for sql, parameters in setup:
                    connection.execute(text(sql), parameters)
                connection.execute(text(statement), values)
            finally:
                transaction.rollback()
    except DBAPIError as error:
        assert constraint in str(error.orig), error
        return True
    return False


def test_the_eight_tables_exist_at_head_and_are_append_only(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    assert _head(engine) == HEAD
    with engine.connect() as connection:
        found = {
            name for (name,) in connection.execute(text("SELECT relname FROM pg_class WHERE starts_with(relname, 'decision_memory_') AND relkind = 'r'"))
        }
        assert found - M2_TABLES - SEAL_CONTENT_TABLES - SEAL_PRODUCT_TABLES == set(TABLES)
        assert found >= SEAL_CONTENT_TABLES | SEAL_PRODUCT_TABLES
        triggers = {
            (table, name, function, mask) for table, name, function, mask in connection.execute(text(
                "SELECT c.relname, t.tgname, p.proname, t.tgtype::integer FROM pg_trigger t "
                "JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_proc p ON p.oid = t.tgfoid "
                "WHERE NOT t.tgisinternal AND starts_with(c.relname, 'decision_memory_')"))
        }
    # `0059` made all eight append-only; `0061` (`D-394`) swapped the five content tables' guard for the forget guard (still 27: UPDATE
    # is refused, a DELETE only beside a same-transaction forget event) and added the transition rule on the status event's INSERT.
    identity = {(table, f"trg_{table}_immutable", "am_immutable_row", 27) for table in set(TABLES) - CONTENT_TABLES}
    content = {(table, f"trg_{table}_forget_guard", "am_guard_decision_memory_forget", 27) for table in CONTENT_TABLES}
    later = {("decision_memory_setting_event", "trg_decision_memory_setting_event_immutable", "am_immutable_row", 27),
             ("decision_memory_status_event", "trg_decision_memory_status_event_transition", "am_guard_decision_memory_status", 7)}
    assert triggers == identity | content | later | SEAL_TRIGGERS


def test_a_case_and_its_decision_are_refused_an_update_and_a_delete(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    values = _case_values()
    with _unguarded(engine) as connection:
        connection.execute(text(_CASE), values)
        statement, decision = _decision(values["case_id"])
        connection.execute(text(statement), decision)
    try:
        for statement in (
            "UPDATE decision_memory_case SET category = 'x'", "DELETE FROM decision_memory_case",
            "UPDATE decision_memory_decision SET severity = 'critical'", "DELETE FROM decision_memory_decision",
        ):
            with pytest.raises(DBAPIError) as refused, engine.begin() as connection:
                connection.execute(text(statement))
            assert "immutable once written" in str(refused.value.orig), refused.value
    finally:
        with _unguarded(engine) as connection:
            connection.execute(text("DELETE FROM decision_memory_decision"))
            connection.execute(text("DELETE FROM decision_memory_case"))


def test_no_table_has_a_foreign_key_into_the_product(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    with engine.connect() as connection:
        references = {
            (child, parent) for child, parent in connection.execute(text(
                "SELECT conrelid::regclass::text, confrelid::regclass::text FROM pg_constraint "
                "WHERE contype = 'f' AND starts_with(conrelid::regclass::text, 'decision_memory_')"))
        }
    # `0064_precedents_seal`: the four KEEP tables it adds to the content side point at the case, its content or nothing else; the three of a run's own
    # (PRODUCT) are the ones that point into the product -- an `audit_run`, a `finding` -- and only those.
    seal_keys = {(child, parent) for child, parent in references if child in SEAL_CONTENT_TABLES | SEAL_PRODUCT_TABLES}
    assert {parent for child, parent in seal_keys if child in SEAL_CONTENT_TABLES} <= {"decision_memory_case", "decision_memory_content"}
    assert seal_keys - {(c, p) for c, p in seal_keys if c in SEAL_CONTENT_TABLES} == {
        ("decision_memory_probe", "audit_run"), ("decision_memory_precedent_run", "audit_run"),
        ("decision_memory_precedent_advice", "audit_run"), ("decision_memory_precedent_advice", "finding")}
    references = {(child, parent) for child, parent in references if child not in SEAL_CONTENT_TABLES | SEAL_PRODUCT_TABLES}
    allowed_outside = {"blob", "command_record", "app_user"}
    outside = {(child, parent) for child, parent in references if parent not in TABLES}
    # `0061` gives the actor of a status event (and of a setting) its RESTRICT key to the account; still no key into a project, document,
    # finding or the ledger.
    assert outside == {("decision_memory_crop", "blob"), ("decision_memory_status_event", "command_record"),
                       ("decision_memory_status_event", "app_user"), ("decision_memory_setting_event", "app_user")}
    assert {parent for _, parent in outside} <= allowed_outside
    assert {child for child, parent in references if parent in TABLES} == set(TABLES) - {"decision_memory_case"}


@pytest.mark.parametrize(("constraint", "over"), [
    ("ck_decision_memory_case_origin_project_uid_format", {"project": "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"}),
    ("ck_decision_memory_case_origin_observation_id_format", {"observation": "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV"}),
    ("ck_decision_memory_case_data_class", {"data_class": "production"}),
    ("ck_decision_memory_case_crop_state", {"crop_state": "pending"}),
    ("ck_decision_memory_case_content_sha256", {"sha": "A" * 64}),
    ("ck_decision_memory_case_section_code", {"section": ""}),
    ("ck_decision_memory_case_case_id_format", {"case_id": "dmd_01ARZ3NDEKTSV4RRFFQ69G5FAV"}),
])
def test_a_case_is_held_by_its_checks(at_head: tuple[Engine, str], constraint: str, over: dict[str, str]) -> None:
    engine, _ = at_head
    assert _breaks(engine, constraint, _CASE, _case_values(**over))
    assert not _breaks(engine, constraint, _CASE, _case_values())  # the same row, obeying them, is accepted


def test_one_case_per_observation_and_one_decision_per_ledger_event(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    first = _case_values()
    assert _breaks(engine, "uq_decision_memory_case_origin_observation", _CASE, _case_values(), before=(_CASE, first))
    statement, decision = _decision(first["case_id"])
    again, repeated = _decision(first["case_id"])  # another memory decision for the SAME ledger event
    assert _breaks_after(engine, "uq_decision_memory_decision_source", [(_CASE, first), (statement, decision)], again, repeated)
    other, different = _decision(first["case_id"], source="dec_01ARZ3NDEKTSV4RRFFQ69G5FAW")  # a different event is accepted
    assert not _breaks_after(engine, "uq_decision_memory_decision_source", [(_CASE, first), (statement, decision)], other, different)


@pytest.mark.parametrize(("constraint", "over"), [
    ("ck_decision_memory_decision_event_type", {"event_type": "comment", "verdict": "accepted"}),
    ("ck_decision_memory_decision_verdict_matches_event", {"event_type": "reject", "verdict": "accepted"}),
    ("ck_decision_memory_decision_severity_accept_only", {"event_type": "reject", "verdict": "rejected", "severity": "critical"}),
    ("ck_decision_memory_decision_severity", {"severity": "fatal"}),
    ("ck_decision_memory_decision_origin_kind", {"origin_kind": "invented"}),
    ("ck_decision_memory_decision_author_user_uid_format", {"author": "someone"}),
    ("ck_decision_memory_decision_source_decision_id_format", {"source": "fobs_01ARZ3NDEKTSV4RRFFQ69G5FAV"}),
])
def test_a_decision_is_held_by_its_checks(at_head: tuple[Engine, str], constraint: str, over: dict[str, Any]) -> None:
    engine, _ = at_head
    case = _case_values()
    broken_statement, broken = _decision(case["case_id"], **over)
    assert _breaks(engine, constraint, broken_statement, broken, before=(_CASE, case))
    good_statement, good = _decision(case["case_id"])
    assert not _breaks(engine, constraint, good_statement, good, before=(_CASE, case))
    # the author may be unknown (a ledger event with no account), and then it is NULL and not refused
    unknown_statement, unknown = _decision(case["case_id"], author=None)
    assert not _breaks(engine, "ck_decision_memory_decision_author_user_uid_format", unknown_statement, unknown, before=(_CASE, case))


def test_a_decision_and_its_content_need_their_case(at_head: tuple[Engine, str]) -> None:
    engine, _ = at_head
    statement, orphan = _decision(DecisionMemoryCaseId.new().value)
    assert _breaks(engine, "fk_decision_memory_decision_case", statement, orphan)
    assert _breaks(engine, "fk_decision_memory_content_case",
                   "INSERT INTO decision_memory_content (case_id, revision, finding_text, recommendation_text, stage_id, "
                   "analysis_profile_id, prompt_bundle_id, provider_mode) VALUES (:c, 1, 'a', 'b', 'text_analysis', "
                   "'ap_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'pb_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'recorded')",
                   {"c": DecisionMemoryCaseId.new().value})


def _content(case_id: str) -> tuple[str, dict[str, Any]]:
    return (
        "INSERT INTO decision_memory_content (case_id, revision, finding_text, recommendation_text, stage_id, "
        "analysis_profile_id, prompt_bundle_id, provider_mode) VALUES (:c, 1, 'a', 'b', 'text_analysis', "
        "'ap_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'pb_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'recorded')",
        {"c": case_id},
    )


def _with_content(case: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(_CASE, case), _content(case["case_id"])]


_EVIDENCE = (
    "INSERT INTO decision_memory_evidence (case_id, revision, ordinal, page_number, quote, char_start, char_end, block_ref, "
    "bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_unit, bbox_origin) VALUES (:c, 1, 0, 1, :quote, 0, :end, :block, "
    ":x0, :y0, :x1, :y1, :unit, :origin)"
)


@pytest.mark.parametrize(("constraint", "over"), [
    ("ck_decision_memory_evidence_span", {"end": 7}),                            # the span is not the quote's length
    ("ck_decision_memory_evidence_block_ref", {"block": "block-1"}),
    ("ck_decision_memory_evidence_bbox_whole", {"x0": None}),                    # a box is all four numbers with unit and origin
    ("ck_decision_memory_evidence_bbox_whole", {"unit": None}),
])
def test_an_evidence_item_is_held_by_its_checks(at_head: tuple[Engine, str], constraint: str, over: dict[str, Any]) -> None:
    engine, _ = at_head
    case = _case_values()
    good = dict(c=case["case_id"], quote="Цитата", end=6, block="b_000001", x0=1.0, y0=2.0, x1=3.0, y1=4.0, unit="pt", origin="top_left")
    assert _breaks_after(engine, constraint, _with_content(case), _EVIDENCE, {**good, **over})
    assert not _breaks_after(engine, constraint, _with_content(case), _EVIDENCE, good)
    unboxed = {**good, "x0": None, "y0": None, "x1": None, "y1": None, "unit": None, "origin": None}
    assert not _breaks_after(engine, constraint, _with_content(case), _EVIDENCE, unboxed)  # no box at all is a valid state


_CROP = (
    "INSERT INTO decision_memory_crop (crop_id, case_id, revision, crop_ordinal, evidence_ordinal, kind, selection_rule, "
    "page_number, bbox_x0, bbox_y0, bbox_x1, bbox_y1, blob_id, sha256, size_bytes, media_type, width_px, height_px, source_ref) "
    "VALUES (:crop, :c, 1, :ordinal, 0, 'portal_image_block', 'page_images/1', 1, :x0, :y0, :x1, :y1, :blob, :sha, 10, "
    "'image/png', 800, 600, :source)"
)


@pytest.mark.parametrize(("constraint", "over"), [
    ("ck_decision_memory_crop_crop_ordinal", {"ordinal": 5}),                    # at most four crops per case
    ("ck_decision_memory_crop_bbox", {"x1": 0.05}),                              # an empty or inverted box
    ("ck_decision_memory_crop_bbox", {"x1": 1.5}),
    ("ck_decision_memory_crop_source_ref", {"source": "blk_short"}),
    ("fk_decision_memory_crop_blob", {"blob": "blob_01ARZ3NDEKTSV4RRFFQ69G5FAW"}),  # a crop is a binding to a Blob that exists
])
def test_a_crop_reference_is_held_by_its_checks(at_head: tuple[Engine, str], constraint: str, over: dict[str, Any]) -> None:
    engine, _ = at_head
    case = _case_values()
    setup = [*_with_content(case), ("INSERT INTO blob (blob_id) VALUES (:b)", {"b": BLOB})]
    good = dict(crop=DecisionMemoryCropId.new().value, c=case["case_id"], ordinal=1, x0=0.1, y0=0.1, x1=0.5, y1=0.5, blob=BLOB, sha=SHA,
                source="blk_" + "a" * 32)
    assert _breaks_after(engine, constraint, setup, _CROP, {**good, **over})
    assert not _breaks_after(engine, constraint, setup, _CROP, good)


_STATUS = (
    "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
    "forgotten_content_sha256) VALUES (:id, :c, :kind, :reason, :actor, :ref, :digest)"
)


@pytest.mark.parametrize(("constraint", "over"), [
    ("ck_decision_memory_status_event_forget_permission", {"kind": "forget", "digest": SHA}),    # a forget names the owner's permission
    ("ck_decision_memory_status_event_forget_permission", {"ref": "owner message"}),  # and nothing else does
    ("ck_decision_memory_status_event_reason_code", {"reason": "because I said so"}),
    ("ck_decision_memory_status_event_kind", {"kind": "delete"}),
    ("ck_decision_memory_status_event_actor_user_uid_format", {"actor": "admin"}),
])
def test_a_status_event_is_held_by_its_checks(at_head: tuple[Engine, str], constraint: str, over: dict[str, Any]) -> None:
    engine, _ = at_head
    case = _case_values()
    with engine.connect() as connection:   # `0061` (`D-393`): the actor is a real account now, so the rows that obey name one
        admin = str(connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
    good = dict(id=DecisionMemoryStatusEventId.new().value, c=case["case_id"], kind="withdraw", reason="wrong_decision", actor=admin, ref=None,
                digest=None)
    assert _breaks_after(engine, constraint, [(_CASE, case)], _STATUS, {**good, **over})
    assert not _breaks_after(engine, constraint, [(_CASE, case)], _STATUS, good)
    assert not _breaks_after(engine, constraint, [(_CASE, case)], _STATUS, {**good, "kind": "forget", "ref": "owner message 2026-11-09",
                                                                             "digest": SHA})


def test_the_downgrade_refuses_over_a_memory_row_and_drops_the_tables_without_one(
    at_head: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_head
    values = _case_values()
    with _unguarded(engine) as connection:
        connection.execute(text(_CASE), values)

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "decision memory holds rows" in (refused.stdout + refused.stderr), refused.describe()
    assert _head(engine) == HEAD  # the refusal left the schema where it was, with the case in it
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM decision_memory_case")).scalar_one() == 1

    with _unguarded(engine) as connection:
        connection.execute(text("DELETE FROM decision_memory_case"))
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    assert _head(engine) == PREVIOUS
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM pg_class WHERE starts_with(relname, 'decision_memory_')")).scalar_one() == 0

    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    assert _head(engine) == HEAD
    assert _breaks(engine, "ck_decision_memory_case_data_class", _CASE, _case_values(data_class="production"))
