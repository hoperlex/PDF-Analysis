"""RECOVERY-REBASE-01: the recovery tooling must know the schema the migrations build.

The W58 drill was written at migration head ``0023`` and its only real run was driven there.
Migrations ``0024``-``0028`` then added eleven tables, three views, a Blob-reference column
and twenty-odd guard triggers without anything in the recovery tooling noticing. Every test in
this module runs against a real PostgreSQL database migrated to head by the literal command
(``conftest.py`` re-exports the DB suite's template-clone fixtures), so a future migration
cannot pass here while the tooling is still describing the old schema:

* the declared head is the alembic head;
* the declared tables, views, triggers, sequences, constraint and index counts equal the live
  catalog (``audit_restored_schema``), and the Blob-reference catalog equals the audit's closed
  set (``audit_blob_references``);
* the fingerprint exemption is the one the frozen SQL implements, and the frozen SQL, run
  here, counts exactly the tables the tooling says a restore proves equal;
* each guard has a test that makes it fail: a table, view, Blob-reference column, trigger,
  trigger event set or constraint that the declaration does not name is introduced into a
  fresh clone and the audit must refuse it.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from auditmanager.shared.db.migrations import head_revision
from scripts.recovery import blob_reference_audit as blob_audit
from scripts.recovery import isolated_postgres_restore as pg_restore
from scripts.recovery.blob_reference_audit import BlobReferenceAuditRefused, audit_blob_references
from scripts.recovery.schema_coverage import (
    EXEMPT_FROM_FINGERPRINT,
    FINGERPRINTED_TABLES,
    GUARD_FUNCTIONS,
    HEAD,
    SEQUENCES,
    TABLES,
    TRIGGERS,
    VIEWS,
    RestoredSchemaRefused,
    audit_restored_schema,
)

#: The tables migrations ``0024``-``0028`` added. Each is immutable or append-only, so each
#: must come back from a restore with its guard trigger.
TABLES_ADDED_AFTER_0023 = frozenset((
    "document_version_classification", "document_version_classification_correction",
    "work_assignment", "work_assignment_event",
    "price_list_revision", "price_list_position", "vendor_list_revision", "vendor_list_entry",
    "optimisation_pass", "optimisation_proposal", "optimisation_proposal_decision",
))
VIEWS_ADDED_AFTER_0023 = frozenset((
    "version_classification_current", "version_classification_revision", "work_assignment_current",
))


def _audit(engine: Engine) -> object:
    with Session(engine) as session:
        return audit_restored_schema(session)


def _blob_audit(engine: Engine) -> object:
    with Session(engine) as session:
        return audit_blob_references(session)


def _run(engine: Engine, *statements: str) -> None:
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


# --- the declaration is the migrated schema -----------------------------------------------


def test_the_declared_head_is_the_alembic_head() -> None:
    assert HEAD == head_revision()


def test_the_declared_schema_equals_the_migrated_schema(migrated_engine: Engine) -> None:
    result = _audit(migrated_engine)
    assert (result.tables, result.views, result.triggers) == (len(TABLES), len(VIEWS), len(TRIGGERS))  # type: ignore[attr-defined]
    assert {name for name, _, _ in result.sequences} == set(SEQUENCES)  # type: ignore[attr-defined]


def test_the_blob_reference_catalog_equals_the_audits_closed_set(migrated_engine: Engine) -> None:
    assert _blob_audit(migrated_engine).available_blobs == ()  # type: ignore[attr-defined]
    with Session(migrated_engine) as session:
        live = {
            (row["schema_name"], row["table_name"], row["column_name"])
            for row in session.execute(blob_audit._CATALOG).mappings()
        }
    assert live == blob_audit._CATALOG_EXPECTED
    assert ("public", "price_list_revision", "blob_id") in live  # `0026_price_lists`


def test_every_table_added_after_0023_is_declared_and_guarded() -> None:
    guarded = {table for table, _, function, _ in TRIGGERS if function in GUARD_FUNCTIONS}
    assert TABLES_ADDED_AFTER_0023 <= TABLES
    assert TABLES_ADDED_AFTER_0023 <= guarded, sorted(TABLES_ADDED_AFTER_0023 - guarded)
    assert VIEWS_ADDED_AFTER_0023 <= VIEWS


def test_every_table_is_either_fingerprinted_or_explicitly_exempt() -> None:
    assert FINGERPRINTED_TABLES | EXEMPT_FROM_FINGERPRINT == TABLES
    assert not FINGERPRINTED_TABLES & EXEMPT_FROM_FINGERPRINT
    assert EXEMPT_FROM_FINGERPRINT <= TABLES


# --- the fingerprint the restore compares counts exactly what the declaration says ------------


def _frozen_fingerprint_table_names(engine: Engine) -> set[str]:
    """Run the frozen ``stand-fingerprint-v1`` table selector and the statements it generates.

    ``psql`` would run the generated statements with ``\\gexec``; this does the same through
    the driver, so the test needs no client binary and reads the SQL out of the one frozen
    source (its own SHA-256 is checked by ``_fingerprint_sql``).
    """
    sql = pg_restore._fingerprint_sql(pg_restore._STAND_SQL_SOURCE)
    generator = re.search(r"(SELECT format\(.*?)\n\\gexec", sql, re.DOTALL)
    assert generator is not None, "the frozen fingerprint SQL no longer ends in \\gexec"
    names: set[str] = set()
    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(generator.group(1))
            statements = [row[0] for row in cursor.fetchall()]
            for statement in statements:
                cursor.execute(statement)
                (line,) = cursor.fetchall()
                names.add(line[0].split("|", 1)[0] if "|" in line[0] else line[0])
    finally:
        connection.rollback()
        connection.close()
    return names


def test_the_frozen_fingerprint_counts_exactly_the_declared_tables(migrated_engine: Engine) -> None:
    assert "NOT LIKE 'norm%'" in pg_restore._fingerprint_sql(pg_restore._STAND_SQL_SOURCE)
    assert {name for name in TABLES if name.startswith("norm")} == EXEMPT_FROM_FINGERPRINT
    assert _frozen_fingerprint_table_names(migrated_engine) == FINGERPRINTED_TABLES


def test_an_unlisted_norm_table_would_fall_out_of_the_fingerprint_unseen(
    migrated_engine: Engine,
) -> None:
    """Why the exemption list is literal: a new ``norm*`` table is not counted by the SQL."""
    _run(migrated_engine, "CREATE TABLE norm_zz_new (id integer PRIMARY KEY)")
    assert "norm_zz_new" not in _frozen_fingerprint_table_names(migrated_engine)
    with pytest.raises(RestoredSchemaRefused, match=r"tables differ.*norm_zz_new"):
        _audit(migrated_engine)


# --- every guard can fail ---------------------------------------------------------------------

_SCHEMA_MUTATIONS = {
    "unregistered table": (
        ("CREATE TABLE zz_unregistered (id integer PRIMARY KEY)",), r"tables differ.*zz_unregistered",
    ),
    "dropped table": (("DROP TABLE vendor_list_entry CASCADE",), r"tables differ.*vendor_list_entry"),
    "unregistered view": (
        ("CREATE VIEW zz_view AS SELECT project_uid FROM project",), r"views differ.*zz_view",
    ),
    "dropped view": (("DROP VIEW work_assignment_current",), r"views differ.*work_assignment_current"),
    "materialised view": (
        ("CREATE MATERIALIZED VIEW zz_mat AS SELECT project_uid FROM project",), "materialised view",
    ),
    "dropped immutable trigger": (
        ("DROP TRIGGER trg_work_assignment_event_immutable ON work_assignment_event",),
        r"triggers differ.*trg_work_assignment_event_immutable",
    ),
    "dropped append-only trigger": (
        ("DROP TRIGGER trg_audit_event_append_only ON audit_event",),
        r"triggers differ.*trg_audit_event_append_only",
    ),
    "disabled trigger": (
        ("ALTER TABLE price_list_revision DISABLE TRIGGER trg_price_list_revision_immutable",),
        r"triggers are not enabled.*trg_price_list_revision_immutable",
    ),
    "trigger on a narrower event set": (
        ("DROP TRIGGER trg_model_call_immutable ON model_call",
         "CREATE TRIGGER trg_model_call_immutable BEFORE DELETE ON model_call "
         "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"),
        r"triggers differ.*trg_model_call_immutable.*'ROW BEFORE DELETE'\)",
    ),
    "extra trigger": (
        ("CREATE TRIGGER trg_zz_extra BEFORE UPDATE ON project "
         "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()",),
        r"triggers differ.*trg_zz_extra",
    ),
    "deferred co-commit trigger made immediate": (
        ("DROP TRIGGER trg_optimisation_pass_has_proposals ON optimisation_pass",
         "CREATE CONSTRAINT TRIGGER trg_optimisation_pass_has_proposals AFTER INSERT "
         "ON optimisation_pass FOR EACH ROW EXECUTE FUNCTION am_require_optimisation_proposals()"),
        r"trigger deferral differs.*trg_optimisation_pass_has_proposals",
    ),
    "dropped check constraint": (
        ("ALTER TABLE price_list_revision DROP CONSTRAINT ck_price_list_revision_row_counts",),
        "constraint counts differ",
    ),
    "unvalidated constraint": (
        ("ALTER TABLE project ADD CONSTRAINT ck_zz_never CHECK (name <> '') NOT VALID",),
        "constraint counts differ",
    ),
    "dropped index": (("DROP INDEX ix_price_list_revision_blob",), "index count differs"),
    "wrong head": (
        ("UPDATE alembic_version SET version_num = '0027_optimisation_proposals'",),
        "migration head differs",
    ),
}


@pytest.mark.parametrize("name", sorted(_SCHEMA_MUTATIONS))
def test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration(
    migrated_engine: Engine, name: str
) -> None:
    statements, message = _SCHEMA_MUTATIONS[name]
    _audit(migrated_engine)  # the unmutated clone passes, so the refusal below is the mutation's
    _run(migrated_engine, *statements)
    with pytest.raises(RestoredSchemaRefused, match=message):
        _audit(migrated_engine)


def test_a_sequence_behind_its_rows_is_refused(migrated_engine: Engine) -> None:
    _run(
        migrated_engine,
        "INSERT INTO release (version, sort_key) VALUES ('0.0.1', 'a'), ('0.0.2', 'b')",
    )
    assert _audit(migrated_engine)
    _run(migrated_engine, "ALTER SEQUENCE release_pk_seq RESTART WITH 1")
    with pytest.raises(RestoredSchemaRefused, match="sequence release_pk_seq is behind release.pk"):
        _audit(migrated_engine)


_BLOB_REFERENCE_MUTATIONS = {
    "foreign key to blob under any name": (
        "ALTER TABLE project ADD COLUMN cover text REFERENCES blob (blob_id)",
        r"unknown=\[\('public', 'project', 'cover'\)\]",
    ),
    "blob_id column without a foreign key": (
        "ALTER TABLE project ADD COLUMN cover_blob_id text",
        r"unknown=\[\('public', 'project', 'cover_blob_id'\)\]",
    ),
    "second blob column on a declared table": (
        "ALTER TABLE price_list_revision ADD COLUMN preview_blob_id text",
        r"unknown=\[\('public', 'price_list_revision', 'preview_blob_id'\)\]",
    ),
    "declared column dropped": (
        "ALTER TABLE input_manifest_entry DROP COLUMN blob_id CASCADE",
        r"missing=\[\('public', 'input_manifest_entry', 'blob_id'\)\]",
    ),
}


@pytest.mark.parametrize("name", sorted(_BLOB_REFERENCE_MUTATIONS))
def test_the_blob_audit_refuses_a_blob_reference_the_tooling_does_not_know(
    migrated_engine: Engine, name: str
) -> None:
    statement, message = _BLOB_REFERENCE_MUTATIONS[name]
    _blob_audit(migrated_engine)
    _run(migrated_engine, statement)
    with pytest.raises(BlobReferenceAuditRefused, match=message):
        _blob_audit(migrated_engine)


def test_the_declared_head_must_move_with_the_audits_head() -> None:
    """One head, not two: the Blob audit imports the declaration's."""
    assert blob_audit._HEAD == HEAD


def test_every_declaration_names_only_what_it_can_audit() -> None:
    assert {table for table, _, _, _ in TRIGGERS} <= TABLES
    assert all(table in TABLES for table, _ in SEQUENCES.values())
    assert len({(table, name) for table, name, _, _ in TRIGGERS}) == len(TRIGGERS)
