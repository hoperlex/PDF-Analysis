"""`W55A-SEAL-01`: migration ``0020_norms_search`` on an empty and on a populated database.

Plan `W55-PLAN.md` section A4, `W55A-SEAL-01`, requires: a fresh upgrade; an upgrade from
``0019`` with norms rows, the generated columns filled and the declared-column digest
unchanged; and a refused downgrade with retained data. Beside them: the current snapshot
moves only with its own history event, the history is append-only, the generated columns are
never written by a caller, and the designation fold does not depend on the database's
``lc_ctype`` (section A3.4: "never ``lower()``; a test asserts the ctype").

HEAVY: every test here needs a real PostgreSQL (the lane's ``57210``), so it runs in the
owner's window (R-102, R-111, D-157). Each refusal has a control write that succeeds, so a
refusal cannot pass because the statement was malformed.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AuditEventId,
    NormDocumentId,
    NormParagraphId,
    NormsSnapshotId,
    UserUid,
)

HEAD = "0020_norms_search"
PREVIOUS = "0019_execution_workers"
MIGRATION = Path(__file__).resolve().parents[3] / "db/migrations/versions/20261012_0020_norms_search.py"

SP54 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP542 = "СП_542_1325800_2024__Свод_правил__Защитные_ограждающие_конс"
BODY = "Здания жилые многоквартирные проектируют с учётом требований"
UNRELIABLE = "Нечитаемый фрагмент здания"

#: The declared columns of the two tables 0020 extends, as W54's canonical row digest reads
#: them: everything the importer writes, never a generated column.
DECLARED_DOCUMENT = (
    "norm_document_id, norms_snapshot_id, source_document_ref, slug, title, doc_type, drawn_on, "
    "source_attribution, pdf_page_count, block_count, page_heading_count, "
    "recognised_characters, paragraph_count"
)
DECLARED_PARAGRAPH = (
    "norm_paragraph_id, norms_snapshot_id, ordinal, page_label, block_ref, char_offset, "
    "char_length, kind, clause_number, text, text_reliability"
)


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _head(connection) -> str:
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _sqlstate(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _refused(connection, statement: str, parameters: dict, *, sqlstate: str) -> None:
    with pytest.raises(DBAPIError) as refused:
        with connection.begin_nested():
            connection.execute(text(statement), parameters)
    assert _sqlstate(refused) == sqlstate, refused.value


def _python_tokens(value: str) -> list[str]:
    """The fold restated from the migration's own tables (see the contract test)."""
    spec = importlib.util.spec_from_file_location("w55a_seal_0020_db", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folded = value.split("__", 1)[0].translate(str.maketrans(module.FOLD_FROM, module.FOLD_TO))
    return [token for token in re.split(r"[ ._-]+", folded) if token]


def _snapshot(connection, *, slugs: tuple[str, ...] = (SP54,)) -> dict[str, object]:
    """One snapshot with one reliable and one unreliable paragraph per document."""
    snapshot = str(NormsSnapshotId.new())
    key = f"2026-07-23+{len(slugs)}d.{snapshot[-12:].lower()}"
    connection.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, repair_count, segmentation_profile, "
        "unreliable_count) VALUES (:s, :ck, :bk, :d, 0, :n, 0, 'markdown-v1', :n)"
    ), {"s": snapshot, "ck": f"{key}+{len(slugs)}u", "bk": key, "d": "d" * 64, "n": len(slugs)})
    documents: list[str] = []
    for index, slug in enumerate(slugs):
        document = str(NormDocumentId.new())
        documents.append(document)
        pk = connection.execute(text(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, source_document_ref, "
            "slug, title, doc_type, source_attribution, pdf_page_count, block_count, "
            "page_heading_count, recognised_characters, paragraph_count) VALUES (:d, :s, :ref, "
            ":slug, 'Свод правил', 'СП', 'consultant_plus', 3, 2, 0, 80, 2) "
            "RETURNING norm_document_pk"
        ), {"d": document, "s": snapshot, "ref": f"source-{index}", "slug": slug}).scalar_one()
        for ordinal, (body, reliability, clause) in enumerate(
            ((BODY, "reliable", "7.1.4"), (UNRELIABLE, "unreliable", None))
        ):
            connection.execute(text(
                "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, "
                "norm_document_pk, ordinal, page_label, block_ref, char_offset, char_length, "
                "kind, clause_number, text, text_reliability) VALUES (:p, :s, :pk, :o, :page, "
                ":block, 0, :n, 'body', :clause, :body, :reliability)"
            ), {"p": str(NormParagraphId.new()), "s": snapshot, "pk": pk, "o": ordinal,
                "page": ordinal + 1, "block": f"block-{ordinal}", "n": len(body),
                "clause": clause, "body": body, "reliability": reliability})
    return {"snapshot": snapshot, "documents": documents}


def _event(connection, *, to: str, before: str | None) -> str:
    event = str(AuditEventId.new())
    connection.execute(text(
        "INSERT INTO norm_current_snapshot_event (event_id, from_snapshot_id, to_snapshot_id, "
        "actor_user_uid) VALUES (:e, :f, :t, :a)"
    ), {"e": event, "f": before, "t": to, "a": str(UserUid.new())})
    return event


def _declared_digest(connection, snapshot: str) -> tuple[str, str]:
    """md5 over the declared columns, ordered by identity -- what the bundle digest reads."""
    documents = connection.execute(text(
        f"SELECT md5(string_agg(row({DECLARED_DOCUMENT})::text, '|' ORDER BY norm_document_id)) "
        "FROM norm_document WHERE norms_snapshot_id = :s"
    ), {"s": snapshot}).scalar_one()
    paragraphs = connection.execute(text(
        f"SELECT md5(string_agg(row({DECLARED_PARAGRAPH})::text, '|' ORDER BY norm_paragraph_id)) "
        "FROM norm_paragraph WHERE norms_snapshot_id = :s"
    ), {"s": snapshot}).scalar_one()
    return documents, paragraphs


# --- the migration lifecycle -------------------------------------------------------------


def test_a_fresh_upgrade_creates_the_current_snapshot_and_the_search_columns(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        assert _head(connection) == HEAD
        for table in ("norm_current_snapshot", "norm_current_snapshot_event"):
            assert connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one()
        generated = dict(connection.execute(text(
            "SELECT attrelid::regclass::text || '.' || attname, attgenerated FROM pg_attribute "
            "WHERE attname IN ('designation_tokens', 'text_tsv') AND NOT attisdropped"
        )).all())
        assert generated == {"norm_document.designation_tokens": "s", "norm_paragraph.text_tsv": "s"}
        volatility = connection.execute(text(
            "SELECT provolatile FROM pg_proc WHERE proname = 'norm_designation_tokens'"
        )).scalar_one()
        assert volatility == "i", "the designation key must be IMMUTABLE to be generated"
        predicate = connection.execute(text(
            "SELECT pg_get_indexdef('ix_norm_paragraph_text_tsv'::regclass)"
        )).scalar_one()
        assert "USING gin (text_tsv)" in predicate and "text_reliability = 'reliable'" in predicate
        triggers = set(connection.execute(text(
            "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN "
            "('norm_current_snapshot'::regclass, 'norm_current_snapshot_event'::regclass)"
        )).scalars())
        assert triggers == {"trg_norm_current_snapshot_guard", "trg_norm_current_snapshot_event_immutable"}


def test_a_populated_0019_upgrades_and_fills_the_generated_columns(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_0019 = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert at_0019.returncode == 0, at_0019.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            seeded = _snapshot(connection, slugs=(SP54, SP542))
            before = _declared_digest(connection, seeded["snapshot"])  # type: ignore[arg-type]
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert _head(connection) == HEAD
            assert _declared_digest(connection, seeded["snapshot"]) == before  # type: ignore[arg-type]
            keys = dict(connection.execute(text(
                "SELECT slug, designation_tokens FROM norm_document WHERE norms_snapshot_id = :s"
            ), {"s": seeded["snapshot"]}).all())
            assert keys == {SP54: ["сп", "54", "13330", "2022"],
                            SP542: ["сп", "542", "1325800", "2024"]}
            assert connection.execute(text(
                "SELECT count(*) FROM norm_paragraph WHERE norms_snapshot_id = :s AND text_tsv IS NULL"
            ), {"s": seeded["snapshot"]}).scalar_one() == 0
            # Russian morphology: the stored vector of «Здания жилые ...» answers «зданий».
            found = connection.execute(text(
                "SELECT count(*) FROM norm_paragraph WHERE norms_snapshot_id = :s "
                "AND text_reliability = 'reliable' "
                "AND text_tsv @@ websearch_to_tsquery('russian', 'зданий жилых')"
            ), {"s": seeded["snapshot"]}).scalar_one()
            assert found == 2
            # «СП 54» names one document, never «СП 542».
            matched = connection.execute(text(
                "SELECT slug FROM norm_document WHERE norms_snapshot_id = :s "
                "AND designation_tokens[1:cardinality(norm_designation_tokens(:q))] "
                "= norm_designation_tokens(:q)"
            ), {"s": seeded["snapshot"], "q": "СП 54"}).scalars().all()
            assert matched == [SP54]
    finally:
        engine.dispose()


@pytest.mark.parametrize("retained", ["norm_current_snapshot", "norm_current_snapshot_event"])
def test_a_retained_current_snapshot_or_history_refuses_the_downgrade(
    empty_database, foundation_command, retained: str,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            snapshot = str(_snapshot(connection)["snapshot"])
            event = _event(connection, to=snapshot, before=None)
            if retained == "norm_current_snapshot":
                connection.execute(text(
                    "INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id) VALUES (:s, :e)"
                ), {"s": snapshot, "e": event})
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0
        assert "refusing to downgrade 0020_norms_search" in refused.stderr
        assert retained in refused.stderr
        with engine.connect() as connection:
            assert _head(connection) == HEAD
            assert connection.execute(text(
                "SELECT count(*) FROM norm_current_snapshot_event"
            )).scalar_one() == 1
            assert connection.execute(text(
                "SELECT designation_tokens FROM norm_document WHERE norms_snapshot_id = :s"
            ), {"s": snapshot}).scalar_one() == ["сп", "54", "13330", "2022"]
    finally:
        engine.dispose()


def test_an_empty_0020_downgrades_and_upgrades_again(empty_database, foundation_command) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            snapshot = str(_snapshot(connection)["snapshot"])
        down = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert down.returncode == 0, down.describe()
        with engine.connect() as connection:
            assert _head(connection) == PREVIOUS
            for table in ("norm_current_snapshot", "norm_current_snapshot_event"):
                assert connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one() is None
            assert connection.execute(text(
                "SELECT count(*) FROM pg_proc WHERE proname = 'norm_designation_tokens'"
            )).scalar_one() == 0
            # The generated columns are derived data; the declared rows stay.
            assert connection.execute(text(
                "SELECT count(*) FROM norm_paragraph WHERE norms_snapshot_id = :s"
            ), {"s": snapshot}).scalar_one() == 2
        again = foundation_command(_alembic("upgrade", "head"), url)
        assert again.returncode == 0, again.describe()
    finally:
        engine.dispose()


# --- the current snapshot and its history ------------------------------------------------


def test_the_current_snapshot_changes_only_with_its_own_history_event(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        first = str(_snapshot(connection)["snapshot"])
        second = str(_snapshot(connection, slugs=(SP542,))["snapshot"])
        insert = "INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id) VALUES (:s, :e)"
        # No history row for the designation: refused before the foreign key is consulted.
        _refused(connection, insert, {"s": first, "e": str(AuditEventId.new())}, sqlstate="AM003")
        # A history row that records another change: refused.
        wrong = _event(connection, to=second, before=None)
        _refused(connection, insert, {"s": first, "e": wrong}, sqlstate="AM003")
        # The control: the first designation, from nothing.
        designated = _event(connection, to=first, before=None)
        connection.execute(text(insert), {"s": first, "e": designated})
        # One row only.
        _refused(connection, insert, {"s": second, "e": _event(connection, to=second, before=first)},
                 sqlstate="23505")
        _refused(connection, "INSERT INTO norm_current_snapshot (singleton, norms_snapshot_id, "
                 "event_id) VALUES (false, :s, :e)",
                 {"s": second, "e": _event(connection, to=second, before=first)}, sqlstate="23514")
        update = "UPDATE norm_current_snapshot SET norms_snapshot_id = :s, event_id = :e"
        # Reusing the designation's own event, or naming one from the wrong predecessor.
        _refused(connection, update, {"s": second, "e": designated}, sqlstate="AM003")
        _refused(connection, update, {"s": second, "e": _event(connection, to=second, before=None)},
                 sqlstate="AM003")
        # The control: a change recorded from the current snapshot to the new one.
        connection.execute(text(update), {"s": second, "e": _event(connection, to=second, before=first)})
        assert connection.execute(text(
            "SELECT norms_snapshot_id FROM norm_current_snapshot"
        )).scalar_one() == second
        # There is no unset.
        _refused(connection, "DELETE FROM norm_current_snapshot", {}, sqlstate="AM003")


def test_the_history_is_append_only_and_records_a_change(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        snapshot = str(_snapshot(connection)["snapshot"])
        event = _event(connection, to=snapshot, before=None)
        _refused(connection, "UPDATE norm_current_snapshot_event SET actor_user_uid = :a "
                 "WHERE event_id = :e", {"a": str(UserUid.new()), "e": event}, sqlstate="AM003")
        _refused(connection, "DELETE FROM norm_current_snapshot_event WHERE event_id = :e",
                 {"e": event}, sqlstate="AM003")
        _refused(connection, "INSERT INTO norm_current_snapshot_event (event_id, from_snapshot_id, "
                 "to_snapshot_id, actor_user_uid) VALUES (:e, :s, :s, :a)",
                 {"e": str(AuditEventId.new()), "s": snapshot, "a": str(UserUid.new())},
                 sqlstate="23514")
        _refused(connection, "INSERT INTO norm_current_snapshot_event (event_id, to_snapshot_id, "
                 "actor_user_uid) VALUES (:e, :s, 'admin@example')",
                 {"e": str(AuditEventId.new()), "s": snapshot}, sqlstate="23514")


def test_a_caller_never_writes_a_generated_column(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        snapshot = str(_snapshot(connection)["snapshot"])
        _refused(connection, "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, "
                 "source_document_ref, slug, title, doc_type, source_attribution, pdf_page_count, "
                 "block_count, page_heading_count, recognised_characters, paragraph_count, "
                 "designation_tokens) VALUES (:d, :s, 'other', 'ГОСТ_1-2000__x', 't', 'ГОСТ', "
                 "'unattributed', 1, 0, 0, 0, 0, ARRAY['гост'])",
                 {"d": str(NormDocumentId.new()), "s": snapshot}, sqlstate="428C9")


# --- the designation fold and the ctype -----------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [SP54, SP542, "ГОСТ_10140-2003__Плиты", "ГОСТ 10140", "CП 54", "ГOCT_12_1_005-88__x",
     "ВСН_25-09_67-85__Ведомственные", "Ёлка Ё.ё", "ISO 9001", "СП.54..13330", "__", "-"],
)
def test_the_sql_fold_equals_the_declared_tables(migrated_engine: Engine, value: str) -> None:
    with migrated_engine.connect() as connection:
        tokens = connection.execute(
            text("SELECT norm_designation_tokens(:v)"), {"v": value}
        ).scalar_one()
    assert tokens == _python_tokens(value)


def test_the_fold_does_not_depend_on_the_ctype(migrated_engine: Engine) -> None:
    """Under the ``C`` collation ``lower()`` leaves Cyrillic untouched -- which is why the
    key is not built with it. The function answers the same under ``C`` and under the
    database's own ctype, whatever that is."""
    with migrated_engine.connect() as connection:
        ctype = connection.execute(text(
            "SELECT datctype FROM pg_database WHERE datname = current_database()"
        )).scalar_one()
        assert ctype, "the database's ctype must be readable for this assertion to mean anything"
        assert connection.execute(text("SELECT lower('ГОСТ' COLLATE \"C\")")).scalar_one() == "ГОСТ"
        under_c = connection.execute(text(
            "SELECT norm_designation_tokens('ГОСТ_10140-2003__x' COLLATE \"C\")"
        )).scalar_one()
        native = connection.execute(text(
            "SELECT norm_designation_tokens('ГОСТ_10140-2003__x')"
        )).scalar_one()
        definition = connection.execute(text(
            "SELECT pg_get_functiondef('norm_designation_tokens(text)'::regprocedure)"
        )).scalar_one()
    assert under_c == native == ["гост", "10140", "2003"], (ctype, under_c, native)
    assert "lower(" not in definition and "upper(" not in definition
