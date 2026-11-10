"""`CRIT-SEAL-50`: the forget tool reaches the four tables `0064_precedents_seal` adds to the content side of a case, on a migrated database, with no object store.

The whole forget (`test_memory_forget.py`) needs the lane's object store; what this file shows needs only PostgreSQL:

* **the catalogue guard of the tool is satisfied**: ``check_schema`` answers the head only when the forget guard is installed and enabled on exactly the
  tables of ``CONTENT_TABLES`` -- so the four new ones (comments, block evidence, the encoder's queue and the vectors) are on both sides, and a table on one
  side only is a refusal;
* **the deletes in the tool's own order and with its own predicates remove every row of the forgotten case** -- the vector, the queued job, the block evidence and the
  comment among them -- and nothing of another case, with the foreign keys to the case's content satisfied by the order (they go before the content);
* **a vector derived from the forgotten text does not survive it**: without the deletes of the new tables the content could not be deleted at all
  (``RESTRICT``), which is the guard against forgetting the text and keeping its projection.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import DecisionMemoryCommentId, DecisionMemoryEmbeddingIntentId, DecisionMemoryStatusEventId, DecisionId
from scripts.recovery import memory_forget as tool
from scripts.recovery.schema_coverage import HEAD
from tests.support.memory_seed import seed_case

SHA = "a" * 64
UNIT_VECTOR = "[" + ",".join(["1"] + ["0"] * 1023) + "]"
NEW_CONTENT_TABLES = {
    "decision_memory_comment", "decision_memory_block_evidence", "decision_memory_embedding_intent", "decision_memory_embedding",
}


@pytest.fixture
def engine(migrated_database: Any) -> Iterator[Engine]:
    built = create_database_engine(migrated_database)
    try:
        yield built
    finally:
        built.dispose()


def _admin(connection: Connection) -> str:
    return str(connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())


def _fill(connection: Connection, case_id: str) -> None:
    """One row of each of the four new tables for the case."""
    connection.execute(text(
        "INSERT INTO decision_memory_comment (comment_id, case_id, source_decision_id, comment, decided_at) "
        "VALUES (:id, :c, :s, 'a comment', clock_timestamp())"),
        {"id": DecisionMemoryCommentId.new().value, "c": case_id, "s": DecisionId.new().value})
    connection.execute(text(
        "INSERT INTO decision_memory_block_evidence (case_id, revision, ordinal, page_number, portal_block_id, bbox_x0, bbox_y0, bbox_x1, bbox_y1, "
        "crop_sha256) VALUES (:c, 1, 0, 1, :b, 0.1, 0.1, 0.5, 0.5, :sha)"), {"c": case_id, "b": "blk_" + "c" * 32, "sha": SHA})
    connection.execute(text(
        "INSERT INTO decision_memory_embedding_intent (intent_id, case_id, revision, view_kind, embedding_profile, input_sha256, state) "
        "VALUES (:id, :c, 1, 'finding_v1', 'bge-m3-dense-v1', :sha, 'done')"),
        {"id": DecisionMemoryEmbeddingIntentId.new().value, "c": case_id, "sha": SHA})
    connection.execute(text(
        "INSERT INTO decision_memory_embedding (case_id, revision, view_kind, embedding_profile, model_revision, input_sha256, embedding_sha256, embedding) "
        "VALUES (:c, 1, 'finding_v1', 'bge-m3-dense-v1', :rev, :sha, :sha, CAST(:v AS vector))"),
        {"c": case_id, "rev": "d" * 40, "sha": SHA, "v": UNIT_VECTOR})


def _count(connection: Connection, table: str, case_id: str) -> int:
    return int(connection.execute(text(f"SELECT count(*) FROM {table} WHERE case_id = :c"), {"c": case_id}).scalar_one())


def _forget_in_the_tools_order(connection: Connection, case_ids: list[str]) -> None:
    """The deletes of ``phase_commit``: the tool's own table order and predicates, after a forget event of each case in the same transaction."""
    admin = _admin(connection)
    for case_id in case_ids:
        connection.execute(text(
            "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
            "forgotten_content_sha256) VALUES (:id, :c, 'forget', 'other', :a, 'forget test', :sha)"),
            {"id": DecisionMemoryStatusEventId.new().value, "c": case_id, "a": admin, "sha": SHA})
    for table, predicate in tool.CONTENT_TABLES.items():
        connection.execute(text(f"DELETE FROM public.{table} t WHERE {predicate}"), {"cases": case_ids})


def test_the_catalogue_guard_of_the_tool_is_satisfied_and_names_the_four_new_tables(engine: Engine) -> None:
    assert NEW_CONTENT_TABLES <= set(tool.CONTENT_TABLES)
    # the content table is last: the tables that point at it are deleted before it
    assert list(tool.CONTENT_TABLES)[-1] == "decision_memory_content"
    order = list(tool.CONTENT_TABLES)
    # the block evidence, the queue and the vectors point at the content (RESTRICT): they go before it. The comments point at the case only.
    assert all(order.index(table) < order.index("decision_memory_content")
               for table in ("decision_memory_block_evidence", "decision_memory_embedding_intent", "decision_memory_embedding"))
    with engine.connect() as connection:
        assert tool.check_schema(connection) == HEAD


def test_a_table_the_tool_does_not_know_is_a_refusal_and_so_is_one_whose_guard_is_gone(engine: Engine) -> None:
    from scripts.recovery.memory_forget import ForgetRefused

    # the guard of a new table switched off: the tool refuses before it touches anything
    with engine.connect() as connection, connection.begin() as transaction:
        try:
            connection.execute(text("ALTER TABLE decision_memory_embedding DISABLE TRIGGER trg_decision_memory_embedding_forget_guard"))
            with pytest.raises(ForgetRefused, match="forget guard is not installed and enabled"):
                tool.check_schema(connection)
        finally:
            transaction.rollback()
    # a table the tool does not list: the guard sits on one more table than the tool's list
    original = dict(tool.CONTENT_TABLES)
    try:
        del tool.CONTENT_TABLES["decision_memory_embedding"]
        with engine.connect() as connection:
            with pytest.raises(ForgetRefused, match="forget guard is not installed and enabled"):
                tool.check_schema(connection)
    finally:
        tool.CONTENT_TABLES.clear()
        tool.CONTENT_TABLES.update(original)


def test_the_forget_removes_every_row_of_the_case_and_nothing_of_another(engine: Engine) -> None:
    with engine.begin() as connection:
        gone = seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAA")["case_id"]
        kept = seed_case(connection, observation="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAB")["case_id"]
        _fill(connection, gone)
        _fill(connection, kept)
    with engine.begin() as connection:
        for table in NEW_CONTENT_TABLES:
            assert _count(connection, table, gone) == 1 and _count(connection, table, kept) == 1, table
        _forget_in_the_tools_order(connection, [gone])
    with engine.connect() as connection:
        for table in (*NEW_CONTENT_TABLES, "decision_memory_content", "decision_memory_evidence"):
            assert _count(connection, table, gone) == 0, table
            assert _count(connection, table, kept) >= 1, table
        # the identity tables are untouched: the case keeps its tombstone and its decisions
        assert _count(connection, "decision_memory_case", gone) == 1 and _count(connection, "decision_memory_decision", gone) >= 1


def test_without_the_deletes_of_the_new_tables_the_content_cannot_be_forgotten(engine: Engine) -> None:
    """The vector is a projection of the forgotten text: it cannot outlive its content (the key is RESTRICT), so a tool that forgot to delete it fails
    loudly and rolls back -- it never leaves the vector behind."""
    with engine.begin() as connection:
        case = seed_case(connection)["case_id"]
        _fill(connection, case)
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            admin = _admin(connection)
            connection.execute(text(
                "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
                "forgotten_content_sha256) VALUES (:id, :c, 'forget', 'other', :a, 'forget test', :sha)"),
                {"id": DecisionMemoryStatusEventId.new().value, "c": case, "a": admin, "sha": SHA})
            for table, predicate in tool.CONTENT_TABLES.items():
                if table in NEW_CONTENT_TABLES:
                    continue
                connection.execute(text(f"DELETE FROM public.{table} t WHERE {predicate}"), {"cases": [case]})
    assert getattr(caught.value.orig, "sqlstate", "") == "23503", caught.value
    with engine.connect() as connection:
        assert _count(connection, "decision_memory_embedding", case) == 1 and _count(connection, "decision_memory_content", case) == 1
