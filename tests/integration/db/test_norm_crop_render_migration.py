"""`CRIT-SEAL-52` (`D-681`): ``0065_norm_crop_render`` -- the PNG of a norm page, against real PostgreSQL.

``norm_crop_render`` is the norm side's derived row: one per (custody binding, render profile), naming the Blob that holds the rendered PNG. Each rule
is shown by a row that obeys beside a row that does not, with the trigger on:

* **the step changes no stored row**, and creates the table empty;
* **the key and the references**: (binding, profile) is the identity; the binding and the Blob must exist (RESTRICT, both); the same bytes may serve two
  renders (the Blob is content-addressed), and one binding may have a render per profile;
* **the shape**: the identity formats, the profile, the digest, a positive size and pixel size, and ``image/png`` as the only media type;
* **immutable**: a render is a derived fact of a binding that never changes, so ``UPDATE`` and ``DELETE`` are refused (``AM003``);
* **the downgrade is refused while a render exists**, and only then; up, down and up again restores the table.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    NormCustodyAdmissionId,
    NormCustodyBindingId,
    NormDocumentId,
    NormsSnapshotId,
)
from auditmanager.storage.models import derive_blob_id
from tests.support.expected_facts import FACTS

THIS = "0065_norm_crop_render"
PREVIOUS = "0064_precedents_seal"
PDF_SHA, PDF_SIZE = "c" * 64, 4096
PNG_SHA, PNG_SIZE = "e" * 64, 20480
PROFILE = "png-150dpi-v1"


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


def _available_blob(connection: Connection, *, sha256: str, size: int, media_type: str) -> str:
    blob_id = str(derive_blob_id(sha256=sha256, size=size))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b) ON CONFLICT DO NOTHING"), {"b": blob_id})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b AND state = 'temporary'"), {"b": blob_id})
    connection.execute(text(
        "UPDATE blob SET state = 'available', sha256 = :d, size_bytes = :s, media_type = :m WHERE blob_id = :b AND state = 'verifying'"),
        {"b": blob_id, "d": sha256, "s": size, "m": media_type})
    return blob_id


def _binding(connection: Connection, *, sha: str = PDF_SHA) -> str:
    """A custody binding of a one-page PDF of a norm document: a snapshot, a document, an available Blob, a confirmed admission, the binding."""
    snapshot, document, admission, binding = (
        str(NormsSnapshotId.new()), str(NormDocumentId.new()), str(NormCustodyAdmissionId.new()), str(NormCustodyBindingId.new()))
    key = f"2026-07-23+1d.{snapshot[-12:].lower()}"
    connection.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, content_digest, undated_documents, document_count, "
        "repair_count, segmentation_profile) VALUES (:s, :k, :k, :d, 0, 1, 0, 'markdown-v1')"), {"s": snapshot, "k": key, "d": "d" * 64})
    connection.execute(text(
        "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, source_document_ref, slug, title, doc_type, source_attribution, "
        "pdf_page_count, block_count, page_heading_count, recognised_characters, paragraph_count) VALUES "
        "(:doc, :s, 'source-1', 'slug-1', 'title.pdf', 'СП', 'unattributed', 1, 1, 0, 10, 1)"), {"doc": document, "s": snapshot})
    blob = _available_blob(connection, sha256=sha, size=PDF_SIZE, media_type="application/pdf")
    connection.execute(text(
        "INSERT INTO norm_custody_admission (norm_custody_admission_id, role, target_kind, target_id, anchor_kind, anchor, blob_id, "
        "declared_size_bytes, declared_sha256, media_type) VALUES (:a, 'norm_source', 'norm_document', :doc, 'crop', 'page-1', :b, :n, :h, "
        "'application/pdf')"), {"a": admission, "doc": document, "b": blob, "n": PDF_SIZE, "h": sha})
    connection.execute(text(
        "UPDATE norm_custody_admission SET state = 'confirmed', confirmed_at = clock_timestamp(), attempt_count = 1 "
        "WHERE norm_custody_admission_id = :a"), {"a": admission})
    connection.execute(text(
        "INSERT INTO norm_custody_binding (norm_custody_binding_id, norm_custody_admission_id, role, target_kind, target_id, anchor_kind, anchor, "
        "blob_id) VALUES (:id, :a, 'norm_source', 'norm_document', :doc, 'crop', 'page-1', :b)"),
        {"id": binding, "a": admission, "doc": document, "b": blob})
    return binding


def _png(connection: Connection) -> str:
    return _available_blob(connection, sha256=PNG_SHA, size=PNG_SIZE, media_type="image/png")


def _render(connection: Connection, binding: str, blob: str, **over: Any) -> None:
    values = {"binding": binding, "profile": PROFILE, "blob": blob, "sha": PNG_SHA, "size": PNG_SIZE, "media": "image/png", "w": 1240, "h": 1754, **over}
    connection.execute(text(
        "INSERT INTO norm_crop_render (norm_custody_binding_id, render_profile, blob_id, sha256, size_bytes, media_type, width_px, height_px) "
        "VALUES (:binding, :profile, :blob, :sha, :size, :media, :w, :h)"), values)


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


def test_the_step_changes_no_stored_row_and_creates_the_table_empty(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    with engine.begin() as connection:
        _binding(connection)
    tables = ("norm_custody_binding", "norm_custody_admission", "norm_document", "norms_snapshot", "blob")
    before = {table: _count(engine, table) for table in tables}
    assert before["norm_custody_binding"] == 1
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('norm_crop_render')")).scalar_one() is None      # the control: not there before
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    assert {table: _count(engine, table) for table in tables} == before
    assert _count(engine, "norm_crop_render") == 0


def test_the_table_has_the_columns_the_key_the_references_and_the_trigger_the_migration_declares(at_head: Engine) -> None:
    with at_head.connect() as connection:
        columns = {row[0]: (row[1], row[2]) for row in connection.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'norm_crop_render'"))}
        assert columns == {
            "norm_custody_binding_id": ("text", "NO"), "render_profile": ("text", "NO"), "blob_id": ("text", "NO"), "sha256": ("text", "NO"),
            "size_bytes": ("bigint", "NO"), "media_type": ("text", "NO"), "width_px": ("integer", "NO"), "height_px": ("integer", "NO"),
            "rendered_at": ("timestamp with time zone", "NO")}
        key = connection.execute(text(
            "SELECT array_agg(a.attname::text ORDER BY k.ord) FROM pg_constraint c "
            "CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) "
            "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum WHERE c.conname = 'pk_norm_crop_render'")).scalar_one()
        assert key == ["norm_custody_binding_id", "render_profile"]
        keys = {row[0]: (row[1], row[2]) for row in connection.execute(text(
            "SELECT conname, confrelid::regclass::text, confdeltype::text FROM pg_constraint "
            "WHERE conrelid = 'norm_crop_render'::regclass AND contype = 'f'"))}
        assert keys == {"fk_norm_crop_render_binding": ("norm_custody_binding", "r"), "fk_norm_crop_render_blob": ("blob", "r")}
        triggers = [tuple(row) for row in connection.execute(text(
            "SELECT t.tgname, p.proname, t.tgtype FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid "
            "WHERE t.tgrelid = 'norm_crop_render'::regclass AND NOT t.tgisinternal"))]
        assert triggers == [("trg_norm_crop_render_immutable", "am_immutable_row", 27)]
        assert connection.execute(text(
            "SELECT count(*) FROM pg_indexes WHERE tablename = 'norm_crop_render' AND indexname IN ('pk_norm_crop_render', 'ix_norm_crop_render_blob')"
        )).scalar_one() == 2


# -- the rules ------------------------------------------------------------------------------------


def test_the_key_and_the_references(at_head: Engine) -> None:
    with at_head.begin() as connection:
        binding, other = _binding(connection), _binding(connection, sha="f" * 64)
        blob = _png(connection)
    ghost_binding = str(NormCustodyBindingId.new())
    ghost_blob = str(derive_blob_id(sha256="9" * 64, size=1))

    _accepted(at_head, lambda c: _render(c, binding, blob))                                                       # the control
    _accepted(at_head, lambda c: (_render(c, binding, blob), _render(c, binding, blob, profile="png-300dpi-v1")))  # a render per profile
    _accepted(at_head, lambda c: (_render(c, binding, blob), _render(c, other, blob)))                            # the same bytes serve two renders
    _refused(at_head, lambda c: (_render(c, binding, blob), _render(c, binding, blob)), "23505")                  # (binding, profile) is the identity
    _refused(at_head, lambda c: _render(c, ghost_binding, blob), "23503")                                         # the binding exists
    _refused(at_head, lambda c: _render(c, binding, ghost_blob), "23503")                                         # the Blob exists


def test_the_shape(at_head: Engine) -> None:
    with at_head.begin() as connection:
        binding, blob = _binding(connection), _png(connection)
    _accepted(at_head, lambda c: _render(c, binding, blob, profile="a"))                                          # the shortest profile
    _accepted(at_head, lambda c: _render(c, binding, blob, profile="p" * 64))                                     # the longest
    for refused in (
        {"profile": ""}, {"profile": "P"}, {"profile": "-x"}, {"profile": "p" * 65}, {"profile": "png 150"},      # a profile is a lower-case code
        {"sha": "e" * 63}, {"sha": "E" * 64},
        {"size": 0}, {"w": 0}, {"h": 0},
        {"media": "image/jpeg"}, {"media": "application/pdf"},                                                    # a render is a PNG
    ):
        _refused(at_head, lambda c, refused=refused: _render(c, binding, blob, **refused), "23514")
    _refused(at_head, lambda c: _render(c, "nbd_short", blob), "23514")                                           # the identities have their formats
    _refused(at_head, lambda c: _render(c, binding, "blob_short"), "23514")
    _refused(at_head, lambda c: _render(c, "adm_" + binding[4:], blob), "23514")                                  # a binding is an ``nbd``


def test_a_render_is_immutable(at_head: Engine) -> None:
    with at_head.begin() as connection:
        binding, blob = _binding(connection), _png(connection)
    for statement in ("UPDATE norm_crop_render SET width_px = 5", "UPDATE norm_crop_render SET render_profile = 'other'", "DELETE FROM norm_crop_render"):
        _refused(at_head, lambda c, statement=statement: (_render(c, binding, blob), c.execute(text(statement))), "AM003")
    # the control: the same statements are not what is refused when no row is there
    _accepted(at_head, lambda c: c.execute(text("DELETE FROM norm_crop_render")))


# -- the forget and the purge: a render is the norm side's, never memory content ------------------------------------------


def test_a_forget_keeps_a_blob_a_norm_page_render_names(at_head: Engine) -> None:
    """``norm_crop_render.blob_id`` is in the closed registry of Blob references (``blob_reference_audit._SOURCES``), so the forget tool's catalogue guard
    accepts the schema and its ``classify_blobs`` counts the render as another owner of the Blob: a crop of the forgotten case that names the same
    bytes is **shared**, and the object stays. Without the render the same crop's Blob is exclusive and leaves with the case (the control)."""
    from scripts.recovery import memory_forget as forget
    from scripts.recovery.blob_reference_audit import _CATALOG, _CATALOG_EXPECTED, _SOURCES
    from tests.support.memory_seed import seed_case

    assert ("public", "norm_crop_render", "blob_id") in _SOURCES
    with at_head.begin() as connection:
        found = {tuple(row) for row in connection.execute(_CATALOG).all()}
        assert found == {tuple(item) for item in _CATALOG_EXPECTED}                       # the guard of the tool is satisfied by the migrated schema
        blob, binding = _png(connection), _binding(connection)
        case = seed_case(connection, blob=blob)["case_id"]
        exclusive, shared = forget.classify_blobs(connection, [case])
        assert [fact.blob_id for fact in exclusive] == [blob] and shared == []             # the control: nothing else names it
        _render(connection, binding, blob)
        exclusive, shared = forget.classify_blobs(connection, [case])
        assert exclusive == [] and shared == [blob]                                        # a render names it: it stays
        assert "norm_crop_render" not in forget.CONTENT_TABLES                              # and the forget never deletes a render


def test_the_purge_keeps_the_blob_a_norm_page_render_names(at_head: Engine) -> None:
    """The purge derives the Blobs it keeps from the KEEP tables' reference columns of the live catalogue: ``norm_crop_render`` is KEEP (the norm corpus,
    by its prefix and ``EXEMPT_FROM_FINGERPRINT``), so the Blob of a render is kept, and a Blob nothing KEEP names is not."""
    from scripts.recovery import product_purge as purge

    with at_head.begin() as connection:
        keep, product = purge.blob_columns(connection)
        assert ("norm_crop_render", "blob_id") in keep and ("norm_crop_render", "blob_id") not in product
        blob, binding = _png(connection), _binding(connection)
        stray = _available_blob(connection, sha256="1" * 64, size=5, media_type="image/png")
        _render(connection, binding, blob)
        kept = set(connection.execute(text(purge._keep_blob_ids_sql(keep))).scalars())
        assert blob in kept and stray not in kept


# -- the downgrade ---------------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_a_render_exists_and_only_then(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    with engine.begin() as connection:
        binding, blob = _binding(connection), _png(connection)
        _render(connection, binding, blob)

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0 and "refusing to downgrade 0065_norm_crop_render" in (refused.stdout + refused.stderr), refused.describe()
    assert "norm_crop_render" in (refused.stdout + refused.stderr)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
    assert _count(engine, "norm_crop_render") == 1                                                                # nothing was dropped

    with engine.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))                                  # an immutable row: the test's own way out
        connection.execute(text("DELETE FROM norm_crop_render"))
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        assert connection.execute(text("SELECT to_regclass('norm_crop_render')")).scalar_one() is None
        assert connection.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = 'ix_norm_crop_render_blob'")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM norm_custody_binding")).scalar_one() == 1            # the binding it named stays

    upgraded = foundation_command(_alembic("upgrade", THIS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
    assert _count(engine, "norm_crop_render") == 0
