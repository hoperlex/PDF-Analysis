"""`CRIT-SEAL-50`: ``0064_precedents_seal`` -- the storage of the «Прецеденты» programme (plan-v5 section 3.1), against real PostgreSQL.

Each rule shown by a row that obeys next to a row that does not, with every trigger on:

* **the step changes no stored row**: a decision written before it has no label and no history verdict, a run is ``text_only``;
* **the forget guard and the guard on INSERT** (``D-497`` item 1): the comments, the block evidence, the encoder's queue and the vectors of a case
  refuse a ``DELETE`` that is not beside a ``forget`` event of the same case in the same transaction, and refuse a new row for a case that was
  forgotten. The queue keeps its state transitions (an ``UPDATE`` of the state is accepted, of its identity refused);
* **the freeze trigger**: ``audit_run.publication_mode`` is part of ``trg_audit_run_frozen_guard``, and ``one_list`` needs a stage plan;
* the closed vocabularies, the unit norm of a vector, the pairs of a state and its reason, the settings' shapes and their numbering, the vectors'
  control and its journal, the delivery journal with no foreign key;
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
    AnalysisProfileId,
    DecisionId,
    DecisionMemoryCommentId,
    DecisionMemoryDecisionId,
    DecisionMemoryEmbeddingIntentId,
    DecisionMemoryStatusEventId,
    DocumentUid,
    ExecutorTaskContextDeliveryId,
    ExecutorTaskId,
    FindingObservationId,
    FindingUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    StageLayoutRevisionId,
    VectorControlEventId,
    VersionUid,
)
from tests.support.expected_facts import FACTS
from tests.support.memory_seed import seed_case

THIS = "0064_precedents_seal"
PREVIOUS = "0063_drop_ar_v3_beta"
REF = "owner message 2026-11-10, forget test"
SHA = "a" * 64
BLOCK = "blk_" + "c" * 32
UNIT_VECTOR = "[" + ",".join(["1"] + ["0"] * 1023) + "]"
DOUBLE_VECTOR = "[" + ",".join(["2"] + ["0"] * 1023) + "]"
SHORT_VECTOR = "[" + ",".join(["1"] + ["0"] * 1022) + "]"
NEW_TABLES = (
    "decision_memory_comment", "decision_memory_block_evidence", "decision_memory_embedding_intent", "decision_memory_embedding",
    "decision_memory_probe", "decision_memory_precedent_run", "decision_memory_precedent_advice", "finding_block_evidence",
    "precedent_setting_event", "vector_control", "vector_control_event", "executor_task_context_delivery",
)
#: The triggers the migration declares: (table, name, function, tgtype). 7 = ROW|BEFORE|INSERT, 11 = ... DELETE, 19 = ... UPDATE, 27 = ... DELETE|UPDATE.
TRIGGERS = {
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
    ("executor_task_context_delivery", "trg_executor_task_context_delivery_immutable", "am_immutable_row", 27),
    ("finding_block_evidence", "trg_finding_block_evidence_immutable", "am_immutable_row", 27),
    ("precedent_setting_event", "trg_precedent_setting_event_immutable", "am_immutable_row", 27),
    ("precedent_setting_event", "trg_precedent_setting_event_number", "am_check_gapless_number", 7),
    ("vector_control", "trg_vector_control_frozen_guard", "am_guard_frozen_columns", 19),
    ("vector_control", "trg_vector_control_no_delete", "am_immutable_row", 11),
    ("vector_control_event", "trg_vector_control_event_append_only", "am_append_only", 27),
    ("vector_control_event", "trg_vector_control_event_number", "am_check_gapless_number", 7),
}


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


def _admin(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())


def _forget(connection: Connection, case_id: str, actor: str) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
        "forgotten_content_sha256) VALUES (:id, :c, 'forget', 'other', :a, :ref, :digest)"),
        {"id": DecisionMemoryStatusEventId.new().value, "c": case_id, "a": actor, "ref": REF, "digest": SHA})


def _run(connection: Connection, *, plan: bool = False, mode: str = "text_only", legacy: bool = False) -> dict[str, str]:
    """A run of a fresh project, optionally with a stage plan (a pending planned run) and a publication mode (``legacy``: as ``0063`` wrote
    one, with no such column)."""
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "version": str(VersionUid.new()), "run": str(RunId.new())}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'precedents')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'D')"), ids)
    connection.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
        "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"), {**ids, "sha": SHA})
    stage_plan = json.dumps({"layout_revision_id": str(StageLayoutRevisionId.new()), "cells": [
        {"cell_key": "review:main", "model_id": "claude-opus-5-5", "effort": "medium", "access": "subscription"}]})
    column, value = ("", "") if legacy else (", publication_mode", ", :mode")
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest, "
        f"binding_state, stage_plan{column}) VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, :state, "
        f"CAST(:plan AS jsonb){value})"),
        {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()), "digest": "b" * 64,
         "state": "pending" if plan else "frozen_at_start", "plan": stage_plan if plan else None,
         **({} if legacy else {"mode": mode})})
    return ids


def _finding(connection: Connection, ids: dict[str, str], *, category: str = "internal_contradiction") -> tuple[str, str]:
    """A finding and its one observation, of the run ``ids`` names; returns the finding and the observation identities."""
    finding, observation = str(FindingUid.new()), str(FindingObservationId.new())
    connection.execute(text(
        "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
        "VALUES (:f, :project, :version, :run, :category)"), {**ids, "f": finding, "category": category})
    connection.execute(text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, recommendation_text, "
        "grounded, analysis_profile_id, prompt_bundle_id, provider_mode) VALUES (:o, :run, :f, 'text_analysis', :category, 't', 't', true, "
        ":profile, :bundle, 'recorded')"),
        {**ids, "o": observation, "f": finding, "category": category, "profile": str(AnalysisProfileId.new()),
         "bundle": str(PromptBundleId.new())})
    return finding, observation


# -- the four content tables the forget reaches ---------------------------------------------------------------------


def _comment(connection: Connection, case_id: str) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_comment (comment_id, case_id, source_decision_id, comment, decided_at) "
        "VALUES (:id, :c, :s, 'the expert wrote this', clock_timestamp())"),
        {"id": DecisionMemoryCommentId.new().value, "c": case_id, "s": DecisionId.new().value})


def _block_evidence(connection: Connection, case_id: str) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_block_evidence (case_id, revision, ordinal, page_number, portal_block_id, bbox_x0, bbox_y0, bbox_x1, "
        "bbox_y1, crop_sha256) VALUES (:c, 1, 0, 1, :b, 0.1, 0.1, 0.5, 0.5, :sha)"), {"c": case_id, "b": BLOCK, "sha": SHA})


def _intent(connection: Connection, case_id: str) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_embedding_intent (intent_id, case_id, revision, view_kind, embedding_profile, input_sha256) "
        "VALUES (:id, :c, 1, 'finding_v1', 'bge-m3-dense-v1', :sha)"),
        {"id": DecisionMemoryEmbeddingIntentId.new().value, "c": case_id, "sha": SHA})


def _embedding(connection: Connection, case_id: str) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_embedding (case_id, revision, view_kind, embedding_profile, model_revision, input_sha256, "
        "embedding_sha256, embedding) VALUES (:c, 1, 'finding_v1', 'bge-m3-dense-v1', :rev, :sha, :sha, CAST(:v AS vector))"),
        {"c": case_id, "rev": "d" * 40, "sha": SHA, "v": UNIT_VECTOR})


#: table -> (the insert that obeys for an active case, the DELETE of its rows by case)
CONTENT: dict[str, Any] = {
    "decision_memory_comment": _comment,
    "decision_memory_block_evidence": _block_evidence,
    "decision_memory_embedding_intent": _intent,
    "decision_memory_embedding": _embedding,
}


# -- fixtures -------------------------------------------------------------------------------------


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


def test_the_step_changes_no_stored_row_and_an_old_decision_has_no_label(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    with engine.begin() as connection:
        seeded = seed_case(connection)
        _run(connection, legacy=True)
    before = {table: _count(engine, table) for table in ("decision_memory_case", "decision_memory_decision", "audit_run", "finding")}
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    assert {table: _count(engine, table) for table in before} == before
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT precedent_label_at_decision, precedent_revision, precedent_history_verdict_shown FROM decision_memory_decision "
            "WHERE case_id = :c"), {"c": seeded["case_id"]}).one()
        assert tuple(row) == (None, None, None)
        assert connection.execute(text("SELECT DISTINCT publication_mode FROM audit_run")).scalar_one() == "text_only"
        assert connection.execute(text("SELECT count(*) FROM vector_control")).scalar_one() == 1
        for table in NEW_TABLES:
            if table != "vector_control":
                assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0, table


def test_the_triggers_of_the_new_tables_are_what_the_migration_declares(at_head: Engine) -> None:
    with at_head.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == FACTS.migration_head
        found = {tuple(row) for row in connection.execute(text(
            "SELECT c.relname, t.tgname, p.proname, t.tgtype::integer FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_proc p ON p.oid = t.tgfoid WHERE NOT t.tgisinternal AND c.relname = ANY(:names)"),
            {"names": list(NEW_TABLES)})}
    assert found == TRIGGERS


# -- the forget guard and the guard on INSERT --------------------------------------------------------------------------


@pytest.mark.parametrize("table", sorted(CONTENT))
def test_a_row_is_added_to_an_active_case_and_refused_for_a_forgotten_one(at_head: Engine, table: str) -> None:
    admin = _admin(at_head)
    insert = CONTENT[table]
    holder: dict[str, str] = {}

    def active(connection: Connection) -> None:
        holder["case"] = seed_case(connection)["case_id"]
        insert(connection, holder["case"])

    def forgotten(connection: Connection) -> None:
        holder["case"] = seed_case(connection)["case_id"]
        _forget(connection, holder["case"], admin)
        insert(connection, holder["case"])

    _accepted(at_head, active)
    with pytest.raises(DBAPIError) as caught:
        with at_head.begin() as connection:
            forgotten(connection)
    assert _sqlstate(caught.value) == "AM003" and "was forgotten" in str(caught.value.orig), caught.value
    # a withdrawn case is not a forgotten one: the rows of a case the administrator may restore are still accepted
    def withdrawn(connection: Connection) -> None:
        holder["case"] = seed_case(connection)["case_id"]
        connection.execute(text(
            "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid) "
            "VALUES (:id, :c, 'withdraw', 'other', :a)"),
            {"id": DecisionMemoryStatusEventId.new().value, "c": holder["case"], "a": admin})
        insert(connection, holder["case"])

    _accepted(at_head, withdrawn)


@pytest.mark.parametrize("table", sorted(CONTENT))
def test_a_row_is_deleted_only_beside_a_forget_of_its_case_in_the_same_transaction(at_head: Engine, table: str) -> None:
    admin = _admin(at_head)
    insert = CONTENT[table]
    holder: dict[str, str] = {}

    def seeded(connection: Connection) -> None:
        holder["a"] = seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAA")["case_id"]
        holder["b"] = seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAB")["case_id"]
        insert(connection, holder["a"])

    def delete(connection: Connection) -> None:
        connection.execute(text(f"DELETE FROM {table} WHERE case_id = :c"), {"c": holder["a"]})

    # no event at all: refused
    _refused(at_head, lambda c: (seeded(c), delete(c)), "AM003")
    # a forget of ANOTHER case does not open this one
    _refused(at_head, lambda c: (seeded(c), _forget(c, holder["b"], admin), delete(c)), "AM003")
    # a withdraw of this case is not a forget
    def withdrawn(connection: Connection) -> None:
        seeded(connection)
        connection.execute(text(
            "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid) "
            "VALUES (:id, :c, 'withdraw', 'other', :a)"), {"id": DecisionMemoryStatusEventId.new().value, "c": holder["a"], "a": admin})
        delete(connection)

    _refused(at_head, withdrawn, "AM003")

    # a forget of THIS case in this transaction opens it; the row is gone
    def forgotten(connection: Connection) -> None:
        seeded(connection)
        # the forget deletes before the forget event of its own transaction would forbid an INSERT, so the row is already there
        _forget(connection, holder["a"], admin)
        delete(connection)
        assert connection.execute(text(f"SELECT count(*) FROM {table} WHERE case_id = :c"), {"c": holder["a"]}).scalar_one() == 0

    _accepted(at_head, forgotten)


@pytest.mark.parametrize("table", ["decision_memory_comment", "decision_memory_block_evidence", "decision_memory_embedding"])
def test_a_row_of_the_memory_is_never_updated(at_head: Engine, table: str) -> None:
    admin = _admin(at_head)
    columns = {
        "decision_memory_comment": "comment = 'x'",
        "decision_memory_block_evidence": "page_number = 2",
        "decision_memory_embedding": "model_revision = '" + "e" * 40 + "'",
    }
    for forget in (False, True):  # not even beside a forget
        def write(connection: Connection, forget: bool = forget) -> None:
            case = seed_case(connection)["case_id"]
            CONTENT[table](connection, case)
            if forget:
                _forget(connection, case, admin)
            connection.execute(text(f"UPDATE {table} SET {columns[table]} WHERE case_id = :c"), {"c": case})

        _refused(at_head, write, "AM003")


def test_the_encoder_queue_changes_state_and_nothing_of_its_identity(at_head: Engine) -> None:
    holder: dict[str, str] = {}

    def queued(connection: Connection) -> None:
        holder["case"] = seed_case(connection)["case_id"]
        _intent(connection, holder["case"])

    def update(sql: str) -> Any:
        return lambda c: (queued(c), c.execute(text(sql), {"c": holder["case"]}))

    _accepted(at_head, update("UPDATE decision_memory_embedding_intent SET state = 'done', state_changed_at = clock_timestamp() "
                              "WHERE case_id = :c"))
    _accepted(at_head, update("UPDATE decision_memory_embedding_intent SET attempts = 3 WHERE case_id = :c"))
    _accepted(at_head, update("UPDATE decision_memory_embedding_intent SET state = 'poisoned', poison_reason = 'too_long' WHERE case_id = :c"))
    for column, value in (("input_sha256", "'" + "f" * 64 + "'"), ("view_kind", "'evidence_v1'"), ("revision", "2"),
                          ("embedding_profile", "'other-profile'")):
        _refused(at_head, update(f"UPDATE decision_memory_embedding_intent SET {column} = {value} WHERE case_id = :c"), "AM003")
    # a state and its reason go together; five tries at most; a closed state
    _refused(at_head, update("UPDATE decision_memory_embedding_intent SET state = 'poisoned' WHERE case_id = :c"), "23514")
    _refused(at_head, update("UPDATE decision_memory_embedding_intent SET poison_reason = 'too_long' WHERE case_id = :c"), "23514")
    _refused(at_head, update("UPDATE decision_memory_embedding_intent SET attempts = 6 WHERE case_id = :c"), "23514")
    _refused(at_head, update("UPDATE decision_memory_embedding_intent SET state = 'running' WHERE case_id = :c"), "23514")


def test_one_intent_per_view_of_a_case_and_the_digest_is_indexed_not_unique(at_head: Engine) -> None:
    def twice(connection: Connection) -> None:
        case = seed_case(connection)["case_id"]
        _intent(connection, case)
        _intent(connection, case)

    _refused(at_head, twice, "23505")

    def same_digest_two_cases(connection: Connection) -> None:
        for observation in ("fobs_01ARZ3NDEKTSV4RRFFQ69G5FAA", "fobs_01ARZ3NDEKTSV4RRFFQ69G5FAB"):
            _intent(connection, seed_case(connection, observation=observation)["case_id"])

    _accepted(at_head, same_digest_two_cases)


# -- the vectors ------------------------------------------------------------------------------------------------------


def test_a_vector_has_the_dimension_and_the_unit_norm_of_the_profile(at_head: Engine) -> None:
    def vector(value: str) -> Any:
        def write(connection: Connection) -> None:
            case = seed_case(connection)["case_id"]
            connection.execute(text(
                "INSERT INTO decision_memory_embedding (case_id, revision, view_kind, embedding_profile, model_revision, input_sha256, "
                "embedding_sha256, embedding) VALUES (:c, 1, 'finding_v1', 'bge-m3-dense-v1', :rev, :sha, :sha, CAST(:v AS vector))"),
                {"c": case, "rev": "d" * 40, "sha": SHA, "v": value})
        return write

    _accepted(at_head, vector(UNIT_VECTOR))
    _refused(at_head, vector(DOUBLE_VECTOR), "23514")
    _refused(at_head, vector(SHORT_VECTOR), "22000")
    with at_head.connect() as connection:
        # no HNSW index on the memory's vectors: the search is an exact scan of one section
        assert connection.execute(text(
            "SELECT count(*) FROM pg_indexes WHERE tablename = 'decision_memory_embedding' AND indexdef ILIKE '%hnsw%'")).scalar_one() == 0


def _probe(connection: Connection, run: str, *, state: str = "pending", vector: str | None = None) -> None:
    connection.execute(text(
        "INSERT INTO decision_memory_probe (run_id, input_id, text_sha256, embedding_profile, input_sha256, state, model_revision, "
        "embedding_sha256, embedding) VALUES (:r, 'candidate-1', :sha, 'bge-m3-dense-v1', :sha, :state, "
        "CASE WHEN :state = 'done' THEN :rev END, CASE WHEN :state = 'done' THEN :sha END, CAST(:v AS vector))"),
        {"r": run, "sha": SHA, "state": state, "rev": "d" * 40, "v": vector})


def test_a_probe_belongs_to_a_run_only_and_gets_its_observation_once(at_head: Engine) -> None:
    holder: dict[str, str] = {}

    def probed(connection: Connection) -> None:
        holder["run"] = _run(connection)["run"]
        _probe(connection, holder["run"])

    _accepted(at_head, probed)
    # the one foreign key of a probe is to the run: not to a finding, not to an observation
    with at_head.connect() as connection:
        targets = {row[0] for row in connection.execute(text(
            "SELECT confrelid::regclass::text FROM pg_constraint WHERE conrelid = 'decision_memory_probe'::regclass AND contype = 'f'"))}
    assert targets == {"audit_run"}
    # a done probe has its vector, a pending one has none, and the vector has the unit norm
    _accepted(at_head, lambda c: _probe(c, _run(c)["run"], state="done", vector=UNIT_VECTOR))
    _refused(at_head, lambda c: _probe(c, _run(c)["run"], state="done"), "23514")
    _refused(at_head, lambda c: _probe(c, _run(c)["run"], state="pending", vector=UNIT_VECTOR), "23514")
    _refused(at_head, lambda c: _probe(c, _run(c)["run"], state="done", vector=DOUBLE_VECTOR), "23514")
    _refused(at_head, lambda c: _probe(c, "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"), "23503")

    def link(connection: Connection) -> None:
        probed(connection)
        connection.execute(text("UPDATE decision_memory_probe SET finding_observation_id = :o WHERE run_id = :r"),
                           {"o": "fobs_01ARZ3NDEKTSV4RRFFQ69G5FAV", "r": holder["run"]})

    _accepted(at_head, link)

    def relink(connection: Connection) -> None:
        link(connection)
        connection.execute(text("UPDATE decision_memory_probe SET finding_observation_id = :o WHERE run_id = :r"),
                           {"o": "fobs_01ARZ3NDEKTSV4RRFFQ69G5FAW", "r": holder["run"]})

    _refused(at_head, relink, "AM003")
    _refused(at_head, lambda c: (probed(c), c.execute(text("UPDATE decision_memory_probe SET input_id = 'other' WHERE run_id = :r"),
                                                      {"r": holder["run"]})), "AM003")


def test_the_pass_and_its_advice(at_head: Engine) -> None:
    def advised(**over: Any) -> Any:
        values = {"label": "often_rejected", "reviewed": True, "votes": json.dumps({"total": 8, "rejected": 7}), "hints": "{p1}",
                  "revision": 1, **over}

        def write(connection: Connection) -> None:
            ids = _run(connection)
            finding, _ = _finding(connection, ids)
            connection.execute(text("INSERT INTO decision_memory_precedent_run (run_id) VALUES (:r)"), {"r": ids["run"]})
            connection.execute(text(
                "INSERT INTO decision_memory_precedent_advice (run_id, finding_uid, revision, label, critic_reviewed, votes, hint_codes) "
                "VALUES (:r, :f, :revision, :label, :reviewed, CAST(:votes AS jsonb), CAST(:hints AS text[]))"),
                {"r": ids["run"], "f": finding, **values})
        return write

    _accepted(at_head, advised())
    _accepted(at_head, advised(label="few", reviewed=False, hints="{}"))
    _refused(at_head, advised(label="cancel_suggested", reviewed=False), "23514")   # В3: a finding the critic did not review is not in the queue
    _refused(at_head, advised(label="unknown"), "23514")
    _refused(at_head, advised(hints="{p1,p4,p5}"), "23514")                         # at most two hints
    _refused(at_head, advised(hints="{p2}"), "23514")                               # the hints of AR v3 do not exist
    _refused(at_head, advised(votes="[]"), "23514")
    _refused(at_head, advised(revision=0), "23514")

    def rewritten(connection: Connection) -> None:
        advised()(connection)
        connection.execute(text("UPDATE decision_memory_precedent_advice SET label = 'mixed'"))

    _refused(at_head, rewritten, "AM003")

    def failed(state: str, code: str | None) -> Any:
        def write(connection: Connection) -> None:
            ids = _run(connection)
            connection.execute(text("INSERT INTO decision_memory_precedent_run (run_id, state, failure_code) VALUES (:r, :s, :c)"),
                               {"r": ids["run"], "s": state, "c": code})
        return write

    _accepted(at_head, failed("failed", "encoder_unavailable"))
    _accepted(at_head, failed("done", None))
    _refused(at_head, failed("failed", None), "23514")
    _refused(at_head, failed("done", "encoder_unavailable"), "23514")
    _refused(at_head, failed("running_late", None), "23514")


# -- block evidence ---------------------------------------------------------------------------------------------------


def test_block_evidence_names_a_portal_block_and_a_box_on_the_page(at_head: Engine) -> None:
    def evidence(**over: Any) -> Any:
        values = {"block": BLOCK, "x0": 0.1, "y0": 0.1, "x1": 0.5, "y1": 0.5, "sha": SHA, "quote": None, "page": 1, **over}

        def write(connection: Connection) -> None:
            _, observation = _finding(connection, _run(connection))
            connection.execute(text(
                "INSERT INTO finding_block_evidence (finding_observation_id, ordinal, page_number, portal_block_id, bbox_x0, bbox_y0, "
                "bbox_x1, bbox_y1, crop_sha256, recognised_quote) VALUES (:o, 0, :page, :block, :x0, :y0, :x1, :y1, :sha, :quote)"),
                {"o": observation, **values})
        return write

    _accepted(at_head, evidence())
    _accepted(at_head, evidence(quote="the recognised text"))
    _refused(at_head, evidence(block="b_000001"), "23514")        # the old block_ref form is not reused
    _refused(at_head, evidence(block="blk_" + "C" * 32), "23514")
    _refused(at_head, evidence(x1=1.5), "23514")
    _refused(at_head, evidence(x1=0.05), "23514")
    _refused(at_head, evidence(sha="A" * 64), "23514")
    _refused(at_head, evidence(quote=""), "23514")
    _refused(at_head, evidence(page=0), "23514")

    def rewritten(connection: Connection) -> None:
        evidence()(connection)
        connection.execute(text("UPDATE finding_block_evidence SET page_number = 2"))

    _refused(at_head, rewritten, "AM003")
    with at_head.connect() as connection:
        # finding_evidence and its old columns are not touched
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = 'finding_evidence' "
            "AND column_name IN ('portal_block_id', 'crop_sha256')")).scalar_one() == 0


def test_an_observation_is_grounded_on_a_span_by_default_and_the_vocabularies_are_widened(at_head: Engine) -> None:
    def observation(**over: Any) -> Any:
        values = {"category": "internal_contradiction", "kind": "text_span", "reason": "quotation_absent", "ref": None, "related": None,
                  **over}

        def write(connection: Connection) -> None:
            ids = _run(connection)
            connection.execute(text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
                "recommendation_text, grounded, ungrounded_reason, grounding_kind, extended_observation_ref, related_finding_uid, "
                "analysis_profile_id, prompt_bundle_id, provider_mode) VALUES (:o, :run, NULL, 'text_analysis', :category, 't', 't', "
                "false, :reason, :kind, :ref, :related, :profile, :bundle, 'recorded')"),
                {**ids, "o": str(FindingObservationId.new()), "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
                 **values})
        return write

    _accepted(at_head, observation())
    _accepted(at_head, observation(category="drawing_discrepancy", kind="portal_block", ref="cand-0001"))
    _accepted(at_head, observation(category="cross_source", related=str(FindingUid.new())))
    for reason in ("block_not_in_run_geometry", "block_crop_mismatch", "block_quote_not_in_recognised"):
        _accepted(at_head, observation(reason=reason))
    _refused(at_head, observation(category="parameter_mismatch"), "23514")          # the second seal's, not this one
    _refused(at_head, observation(reason="looked_wrong"), "23514")
    _refused(at_head, observation(kind="image"), "23514")
    _refused(at_head, observation(ref=""), "23514")
    _refused(at_head, observation(related="doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"), "23514")
    # the finding's own category takes the two new values too
    _accepted(at_head, lambda c: _finding(c, _run(c), category="cross_source"))
    _accepted(at_head, lambda c: _finding(c, _run(c), category="drawing_discrepancy"))
    _refused(at_head, lambda c: _finding(c, _run(c), category="parameter_mismatch"), "23514")


# -- the freeze trigger ---------------------------------------------------------------------------------------------


def test_the_publication_mode_is_frozen_at_the_start_of_the_run(at_head: Engine) -> None:
    holder: dict[str, str] = {}
    with at_head.connect() as connection:
        arguments = connection.execute(text(
            "SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t WHERE t.tgname = 'trg_audit_run_frozen_guard'")).scalar_one()
    assert "'publication_mode'" in arguments and "'stage_plan'" in arguments, arguments

    def run(connection: Connection) -> None:
        holder["run"] = _run(connection, plan=True)["run"]

    def change(value: str) -> Any:
        return lambda c: (run(c), c.execute(text("UPDATE audit_run SET publication_mode = :m WHERE run_id = :r"),
                                            {"m": value, "r": holder["run"]}))

    _refused(at_head, change("one_list"), "AM003")
    # a run is born with its mode, and a run that has a stage plan may be born as one_list
    _accepted(at_head, lambda c: _run(c, plan=True, mode="one_list"))
    _accepted(at_head, lambda c: _run(c, plan=False, mode="text_only"))
    # but one_list needs a stage plan (plan-v5 section 3.6): the legacy run is always text_only
    _refused(at_head, lambda c: _run(c, plan=False, mode="one_list"), "23514")
    _refused(at_head, lambda c: _run(c, plan=True, mode="two_lists"), "23514")
    # the rest of the frozen list still holds
    _refused(at_head, lambda c: (run(c), c.execute(text("UPDATE audit_run SET stage_plan = NULL WHERE run_id = :r"),
                                                   {"r": holder["run"]})), "AM003")


# -- the settings and the vectors' control ---------------------------------------------------------------------------


def _setting(connection: Connection, name: str, revision: int, value: dict[str, Any], actor: str) -> None:
    connection.execute(text(
        "INSERT INTO precedent_setting_event (setting_name, revision, value, actor_user_uid) "
        "VALUES (:n, :rev, CAST(:v AS jsonb), :a)"), {"n": name, "rev": revision, "v": json.dumps(value), "a": actor})


def test_the_settings_are_a_closed_numbered_immutable_journal(at_head: Engine) -> None:
    admin = _admin(at_head)
    window = {"start": "01:00", "end": "06:00", "tz": "Asia/Almaty"}
    _accepted(at_head, lambda c: _setting(c, "one_list", 1, {"enabled": True}, admin))
    _accepted(at_head, lambda c: _setting(c, "vector_window", 1, window, admin))
    _accepted(at_head, lambda c: _setting(c, "stop_words", 1, {"words": ["срочно"]}, admin))
    _accepted(at_head, lambda c: (_setting(c, "one_list", 1, {"enabled": True}, admin), _setting(c, "one_list", 2, {"enabled": False}, admin),
                                  _setting(c, "stop_words", 1, {"words": []}, admin)))
    # numbered per name without a gap: 1, 2, 3
    _refused(at_head, lambda c: _setting(c, "one_list", 2, {"enabled": True}, admin), "AM001")
    _refused(at_head, lambda c: (_setting(c, "one_list", 1, {"enabled": True}, admin), _setting(c, "one_list", 3, {"enabled": True}, admin)),
             "AM001")
    _refused(at_head, lambda c: (_setting(c, "one_list", 1, {"enabled": True}, admin), _setting(c, "one_list", 1, {"enabled": False}, admin)),
             "AM001")                                                   # the number is checked before the key
    # a closed list of names, an object value, the shape of a switch and of the window
    _refused(at_head, lambda c: _setting(c, "ar_v3", 1, {"enabled": True}, admin), "23514")
    _refused(at_head, lambda c: _setting(c, "one_list", 1, {"enabled": "yes"}, admin), "23514")
    _refused(at_head, lambda c: _setting(c, "critic_context", 1, {}, admin), "23514")
    _refused(at_head, lambda c: _setting(c, "vector_window", 1, {"start": "01:00", "end": "06:00"}, admin), "23514")
    _refused(at_head, lambda c: c.execute(text(
        "INSERT INTO precedent_setting_event (setting_name, revision, value, actor_user_uid) VALUES ('thresholds', 1, '[1]'::jsonb, :a)"),
        {"a": admin}), "23514")
    # the actor is an account that exists (RESTRICT)
    _refused(at_head, lambda c: _setting(c, "one_list", 1, {"enabled": True}, "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"), "23503")
    with at_head.connect() as connection:
        assert connection.execute(text(
            "SELECT confdeltype::text FROM pg_constraint WHERE conname = 'fk_precedent_setting_event_actor'")).scalar_one() == "r"
    # nothing journalled means every switch is off
    assert _count(at_head, "precedent_setting_event") == 0
    # immutable
    for statement in ("UPDATE precedent_setting_event SET revision = 5", "DELETE FROM precedent_setting_event"):
        _refused(at_head, lambda c, statement=statement: (_setting(c, "one_list", 1, {"enabled": True}, admin), c.execute(text(statement))),
                 "AM003")


def _control_event(connection: Connection, kind: str, *, actor: str | None = None, reason: str | None = None, number: int = 1) -> None:
    connection.execute(text(
        "INSERT INTO vector_control_event (control_event_id, control_key, event_no, kind, reason, actor_user_uid) "
        "VALUES (:id, 'default', :n, :k, :r, :a)"),
        {"id": VectorControlEventId.new().value, "n": number, "k": kind, "r": reason, "a": actor})


def test_the_vectors_control_is_one_row_and_its_journal_names_who_paused(at_head: Engine) -> None:
    admin = _admin(at_head)
    with at_head.connect() as connection:
        row = connection.execute(text(
            "SELECT control_key, paused, paused_since, window_state, window_reason FROM vector_control")).all()
    assert [tuple(r) for r in row] == [("default", False, None, "closed", None)]
    # the state moves; the key does not, and the row is never deleted
    _accepted(at_head, lambda c: c.execute(text("UPDATE vector_control SET paused = true, paused_since = clock_timestamp()")))
    _accepted(at_head, lambda c: c.execute(text(
        "UPDATE vector_control SET window_state = 'skipped', window_reason = 'out_of_memory', window_changed_at = clock_timestamp()")))
    _refused(at_head, lambda c: c.execute(text("UPDATE vector_control SET control_key = 'other'")), "AM003")
    _refused(at_head, lambda c: c.execute(text("DELETE FROM vector_control")), "AM003")
    _refused(at_head, lambda c: c.execute(text("INSERT INTO vector_control (control_key) VALUES ('second')")), "23514")
    _refused(at_head, lambda c: c.execute(text("UPDATE vector_control SET paused = true")), "23514")                  # a pause has its time
    _refused(at_head, lambda c: c.execute(text("UPDATE vector_control SET window_state = 'skipped'")), "23514")        # a skip has its reason
    _refused(at_head, lambda c: c.execute(text("UPDATE vector_control SET window_reason = 'out_of_memory'")), "23514")
    _refused(at_head, lambda c: c.execute(text("UPDATE vector_control SET window_state = 'paused'")), "23514")
    # the journal: the administrator's pause and resume carry the actor, the window's states carry none; numbered; append-only
    _accepted(at_head, lambda c: (_control_event(c, "paused", actor=admin, number=1), _control_event(c, "resumed", actor=admin, number=2),
                                  _control_event(c, "window_draining", number=3), _control_event(c, "window_skipped", reason="timeout", number=4)))
    _refused(at_head, lambda c: _control_event(c, "paused"), "23514")
    _refused(at_head, lambda c: _control_event(c, "window_encoding", actor=admin), "23514")
    _refused(at_head, lambda c: _control_event(c, "window_skipped"), "23514")
    _refused(at_head, lambda c: _control_event(c, "window_closed", reason="timeout"), "23514")
    _refused(at_head, lambda c: _control_event(c, "paused", actor=admin, number=2), "AM001")
    _refused(at_head, lambda c: _control_event(c, "paused", actor="usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"), "23503")
    for statement in ("UPDATE vector_control_event SET kind = 'resumed'", "DELETE FROM vector_control_event"):
        _refused(at_head, lambda c, statement=statement: (_control_event(c, "window_draining"), c.execute(text(statement))), "AM002")


# -- the delivery journal ---------------------------------------------------------------------------------------------


def test_the_delivery_journal_has_no_foreign_key_and_no_text(at_head: Engine) -> None:
    with at_head.connect() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND (conrelid = 'executor_task_context_delivery'::regclass "
            "OR confrelid = 'executor_task_context_delivery'::regclass)")).scalar_one() == 0
        columns = {row[0]: row[1] for row in connection.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'executor_task_context_delivery'"))}
    assert set(columns) == {"delivery_id", "task_id", "run_id", "model_call_id", "kind", "status", "reason", "case_ids", "characters",
                            "block_sha256", "delivered_at"}
    assert {name for name, kind in columns.items() if kind == "text"} == {"delivery_id", "task_id", "run_id", "model_call_id", "kind", "status",
                                                                         "reason", "block_sha256"}  # identities, codes and a digest; no text

    task = str(ExecutorTaskId.new())

    def delivery(**over: Any) -> Any:
        values = {"task": task, "kind": "similar_cases", "status": "delivered", "reason": None, "cases": "{}", "chars": 0, "block": SHA, **over}

        def write(connection: Connection) -> None:
            connection.execute(text(
                "INSERT INTO executor_task_context_delivery (delivery_id, task_id, run_id, kind, status, reason, case_ids, characters, "
                "block_sha256) VALUES (:id, :task, :run, :kind, :status, :reason, CAST(:cases AS text[]), :chars, :block)"),
                {"id": ExecutorTaskContextDeliveryId.new().value, "run": str(RunId.new()), **values})
        return write

    _accepted(at_head, delivery())
    _accepted(at_head, delivery(cases="{dmc_01ARZ3NDEKTSV4RRFFQ69G5FAV,dmc_01ARZ3NDEKTSV4RRFFQ69G5FAW}", chars=1200))
    _accepted(at_head, delivery(status="unavailable", reason="until_move", block=None))
    _refused(at_head, delivery(status="unavailable", block=None), "23514")                  # unavailable says why
    _refused(at_head, delivery(reason="until_move"), "23514")
    _refused(at_head, delivery(block=None), "23514")                                          # delivered carries the digest of its block
    _refused(at_head, delivery(cases="{case-1}"), "23514")
    _refused(at_head, delivery(kind="norm_excerpts"), "23514")                                # the kinds are similar_cases and patterns
    _refused(at_head, lambda c: (delivery()(c), delivery()(c)), "23505")                       # idempotent by (task, kind)
    _accepted(at_head, lambda c: (delivery()(c), delivery(kind="patterns")(c)))
    _refused(at_head, lambda c: (delivery()(c), c.execute(text("UPDATE executor_task_context_delivery SET characters = 5"))), "AM003")


# -- the downgrade ---------------------------------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_any_of_it_exists_and_only_then(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    admin = _admin(engine)

    # a setting
    with engine.begin() as connection:
        _setting(connection, "one_list", 1, {"enabled": True}, admin)
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "refusing to downgrade 0064_precedents_seal" in (refused.stdout + refused.stderr), refused.describe()
    assert "precedent_setting_event" in (refused.stdout + refused.stderr)
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(text("DELETE FROM precedent_setting_event"))

    # a one-list run
    with engine.begin() as connection:
        _run(connection, plan=True, mode="one_list")
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "audit_run.publication_mode" in (refused.stdout + refused.stderr), refused.describe()
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(text("DELETE FROM audit_run"))

    # a decision under a label
    # (the memory's decision rows are immutable: the columns are written at insertion, so the decision is a second one of the case)
    with engine.begin() as connection:
        case = seed_case(connection)
        connection.execute(text(
            "INSERT INTO decision_memory_decision (memory_decision_id, case_id, source_decision_id, event_type, verdict, origin_kind, "
            "decided_at, precedent_label_at_decision, precedent_revision, precedent_history_verdict_shown) "
            "VALUES (:d, :c, :s, 'reject', 'rejected', 'direct', clock_timestamp() + interval '1 minute', 'often_rejected', 1, 'rejected')"),
            {"d": DecisionMemoryDecisionId.new().value, "c": case["case_id"], "s": DecisionId.new().value})
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "precedent_label_at_decision" in (refused.stdout + refused.stderr), refused.describe()
    # a pair (label, revision) and a history verdict alone
    _refused(engine, lambda c: c.execute(text(
        "INSERT INTO decision_memory_decision (memory_decision_id, case_id, source_decision_id, event_type, verdict, origin_kind, decided_at, "
        "precedent_label_at_decision) VALUES (:d, :c, :s, 'reject', 'rejected', 'direct', now(), 'none')"),
        {"d": DecisionMemoryDecisionId.new().value, "c": case["case_id"], "s": DecisionId.new().value}), "23514")
    _refused(engine, lambda c: c.execute(text(
        "INSERT INTO decision_memory_decision (memory_decision_id, case_id, source_decision_id, event_type, verdict, origin_kind, decided_at, "
        "precedent_history_verdict_shown) VALUES (:d, :c, :s, 'reject', 'rejected', 'direct', now(), 'pending')"),
        {"d": DecisionMemoryDecisionId.new().value, "c": case["case_id"], "s": DecisionId.new().value}), "23514")
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        for table in ("decision_memory_decision_text", "decision_memory_decision", "decision_memory_crop", "decision_memory_norm_ref",
                      "decision_memory_evidence", "decision_memory_content", "decision_memory_case"):
            connection.execute(text(f"DELETE FROM {table}"))

    # a finding of a new category
    with engine.begin() as connection:
        _finding(connection, _run(connection), category="cross_source")
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "new category" in (refused.stdout + refused.stderr), refused.describe()
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        for table in ("finding_observation", "finding", "audit_run", "document_version", "document", "project"):
            connection.execute(text(f"DELETE FROM {table}"))

    # nothing left: the downgrade restores the schema of 0063
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        assert connection.execute(text(
            "SELECT count(*) FROM pg_class WHERE relname = ANY(:t) AND relkind = 'r'"), {"t": list(NEW_TABLES)}).scalar_one() == 0
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE (table_name = 'audit_run' AND column_name = 'publication_mode') "
            "OR (table_name = 'finding_observation' AND column_name IN ('grounding_kind', 'extended_observation_ref', 'related_finding_uid')) "
            "OR (table_name = 'decision_memory_decision' AND column_name LIKE 'precedent_%')")).scalar_one() == 0
        for table, constraint, value in (("finding", "ck_finding_category", "cross_source"),
                                         ("finding_observation", "ck_finding_observation_category", "drawing_discrepancy"),
                                         ("finding_observation", "ck_finding_observation_ungrounded_reason", "block_crop_mismatch")):
            definition = connection.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n AND conrelid = CAST(:t AS regclass)"),
                {"n": constraint, "t": table}).scalar_one()
            assert value not in definition, (constraint, definition)
        assert connection.execute(text("SELECT count(*) FROM pg_proc WHERE proname = 'am_guard_decision_memory_forgotten_insert'")).scalar_one() == 0
        arguments = connection.execute(text(
            "SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t WHERE t.tgname = 'trg_audit_run_frozen_guard'")).scalar_one()
        assert "'publication_mode'" not in arguments and "'stage_plan'" in arguments
    upgraded = foundation_command(_alembic("upgrade", THIS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
