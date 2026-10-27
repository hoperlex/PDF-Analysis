"""`COMPARE-PERSISTED-SUMMARY-01`: the product purge and the project erase handle the sheet-link history.

Migration ``0035_comparison_records`` added ``comparison_sheet_link`` and ``comparison_summary``, the
command types ``approve_sheet_pairing`` / ``withdraw_sheet_pairing`` / ``generate_comparison_summary``
and the ``comparison.*`` audit events. The
rest of this directory proves the classification on the stand in miniature (which holds no link);
this module proves it on rows written the way the product writes them, in a database of its own:
two projects, each with one document of two versions, one stored approval and one stored summary of
it, the receipts of the commands that wrote them and the audit events that went with them.

* a dry run of the product purge names the table with its exact count and changes nothing; the
  real run empties the table, its receipts and its audit events;
* the project erase of ONE project removes that project's link, its receipt and nothing of the
  other project's (checked with this test's own digest, not the tool's);
* the foreign keys of the table are pinned, so a later reference from a KEEP table, or from the
  history into a table the purge cannot leave consistent, fails here and not on a stand.

The database is a private clone of the migrated template and the bucket is private and empty (the
history writes no object).
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.audit import record_sheet_link_approved, record_summary_generated
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AuditEventId,
    CommandId,
    ComparisonId,
    DocumentUid,
    ProjectUid,
    SheetLinkId,
    VersionUid,
)
from auditmanager.storage import S3StorageSettings
from scripts.recovery import product_purge as purge
from scripts.recovery import project_erase as erase
from tests.integration.recovery.purge_seed import digest_of, s3
from tests.integration.recovery.purge_stand import (  # noqa: F401  (a fixture module imported by name)
    Stand, _empty_and_delete, _line, full_purge, invoke,
)

ACTOR = "usr_01M2545JSD15ETSNNV904XE001"
SEAL, SHA = "d" * 64, "c" * 64
REFERENCE = "owner message 2026-10-27, comparison records test"


def _write_project(engine, name: str) -> dict[str, str]:
    """A project with one document of two versions, one approval, its receipt and its audit event."""
    ids = {
        "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
        "v1": str(VersionUid.new()), "v2": str(VersionUid.new()),
        "comparison": str(ComparisonId.new()), "link": str(SheetLinkId.new()),
        "command": str(CommandId.new()), "summary_command": str(CommandId.new()),
        "summary": str(AuditEventId.new()),
    }
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, :n)"),
                           {"p": ids["project"], "n": name})
        connection.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'К')"),
            {"d": ids["document"], "p": ids["project"]})
        for key, ordinal in (("v1", 1), ("v2", 2)):
            connection.execute(
                text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                     "byte_size, sha256, page_count) VALUES (:v, :d, :o, 'application/pdf', 1024, :s, 5)"),
                {"v": ids[key], "d": ids["document"], "o": ordinal, "s": SHA})
        connection.execute(
            text("INSERT INTO command_record (command_id, command_type, idempotency_key, "
                 "payload_fingerprint, state) VALUES (:c, 'approve_sheet_pairing', :k, :f, 'in_progress')"),
            {"c": ids["command"], "k": secrets.token_hex(8), "f": SHA})
        connection.execute(
            text("UPDATE command_record SET state = 'succeeded', outcome = CAST('{}' AS jsonb) "
                 "WHERE command_id = :c"), {"c": ids["command"]})
        connection.execute(
            text("INSERT INTO comparison_sheet_link (comparison_id, link_revision, event_kind, "
                 "sheet_link_id, project_uid, document_uid, source_version_uid, target_version_uid, "
                 "source_page_number, target_page_number, source_page_text_sha256, "
                 "target_page_text_sha256, suggestion_sha256, raw_evidence_seal_sha256, "
                 "actor_user_uid, actor_label, command_id) VALUES (:cmp, 1, 'approved', :link, :p, :d, "
                 ":v1, :v2, 2, 3, :s, :s, :s, :seal, :actor, 'Иванов И.', :c)"),
            {"cmp": ids["comparison"], "link": ids["link"], "p": ids["project"], "d": ids["document"],
             "v1": ids["v1"], "v2": ids["v2"], "s": SHA, "seal": SEAL, "actor": ACTOR, "c": ids["command"]})
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO command_record (command_id, command_type, idempotency_key, "
                 "payload_fingerprint, state) VALUES (:c, 'generate_comparison_summary', :k, :f, 'in_progress')"),
            {"c": ids["summary_command"], "k": secrets.token_hex(8), "f": SHA})
        connection.execute(
            text("UPDATE command_record SET state = 'succeeded', outcome = CAST('{}' AS jsonb) "
                 "WHERE command_id = :c"), {"c": ids["summary_command"]})
        connection.execute(
            text("INSERT INTO comparison_summary (summary_id, comparison_id, link_revision, project_uid, "
                 "raw_evidence_seal_sha256, input_sha256, request_sha256, prompt_version, provider_mode, "
                 "model_identity, state, statements, cost_basis, cost_micros, actor_user_uid, actor_label, "
                 "command_id) VALUES (:id, :cmp, 1, :p, :seal, :s, :s, 'comparison-summary-v1', 'recorded', "
                 "'recorded', 'ready', CAST(:statements AS jsonb), 'unmetered', 0, :actor, 'Иванов И.', :c)"),
            {"id": ids["summary"], "cmp": ids["comparison"], "p": ids["project"], "seal": SEAL, "s": SHA,
             "statements": '[{"text": "Размер изменён.", "hunk_ids": ["' + ids["link"] + ':0"]}]',
             "actor": ACTOR, "c": ids["summary_command"]})
    with Session(engine) as session, session.begin():
        record_summary_generated(
            session, event_id=ids["summary"], comparison_id=ids["comparison"], link_revision=1,
            input_sha256=SHA, raw_evidence_seal_sha256=SEAL, state="ready", actor_uid=ACTOR,
            correlation_id=None)
        record_sheet_link_approved(
            session, comparison_id=ids["comparison"], sheet_link_id=ids["link"], link_revision=1,
            source_version_uid=ids["v1"], target_version_uid=ids["v2"], source_page_number=2,
            target_page_number=3, actor_uid=ACTOR, raw_evidence_seal_sha256=SEAL, correlation_id=None)
    return ids


@pytest.fixture
def linked(migrated_database, monkeypatch) -> Iterator[Stand]:
    """A migrated clone holding two projects with one stored approval each, and an empty private bucket."""
    base = S3StorageSettings.from_env()
    bucket = f"{base.bucket[:36]}-cmp-{secrets.token_hex(5)}"
    values = {
        "DATABASE_URL": migrated_database.url.render_as_string(hide_password=False),
        "S3_ENDPOINT_URL": base.endpoint_url, "S3_REGION": base.region,
        "S3_ACCESS_KEY_ID": base.access_key_id, "S3_SECRET_ACCESS_KEY": base.secret_access_key,
        "S3_BUCKET": bucket,
    }
    client = s3(values)
    client.create_bucket(Bucket=bucket)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    engine = create_database_engine(migrated_database)
    try:
        first, second = _write_project(engine, "Склад связей"), _write_project(engine, "Школа связей")
        yield Stand(str(migrated_database.url.database), bucket, migrated_database, engine, values,
                    client, {"first": first, "second": second})
    finally:
        engine.dispose()
        _empty_and_delete(client, bucket)


def _count(stand: Stand, table: str, where: str = "true", **parameters: object) -> int:
    with stand.engine.connect() as connection:
        return int(connection.execute(
            text(f'SELECT count(*) FROM public."{table}" WHERE {where}'), parameters).scalar_one())


def _events(stand: Stand) -> int:
    return _count(stand, "audit_event", "event_type LIKE 'comparison.%'")


def test_the_fixture_is_two_real_approvals_with_their_receipts_and_events(linked: Stand) -> None:
    """The premise of every other test here, measured."""
    assert _count(linked, "comparison_sheet_link") == 2
    assert _count(linked, "comparison_summary") == 2
    assert _count(linked, "command_record", "command_type LIKE '%_sheet_pairing' OR command_type = 'generate_comparison_summary'") == 4
    assert _events(linked) == 4


def test_the_command_types_and_the_event_prefix_are_classified_as_product() -> None:
    assert {"approve_sheet_pairing", "withdraw_sheet_pairing", "generate_comparison_summary"} <= (
        purge.PRODUCT_COMMAND_TYPES)
    assert "comparison." in purge.PRODUCT_EVENT_PREFIXES
    for table in ("comparison_sheet_link", "comparison_summary"):
        assert table in purge.PRODUCT_TABLES
        assert table not in purge.KEEP_TABLES | purge.MIXED_TABLES


def test_a_dry_run_names_the_table_and_its_receipts_and_changes_nothing(linked: Stand) -> None:
    before = (_count(linked, "comparison_sheet_link"), _count(linked, "comparison_summary"),
              _count(linked, "command_record"), _events(linked))
    code, out, err = invoke(purge, linked, "plan", "--dry-run")
    assert code == 0, err
    assert "  comparison_sheet_link  (2 rows)" in out
    assert "  comparison_summary  (2 rows)" in out
    assert "  command_record  (delete 4 rows, keep 0 rows)" in out
    assert "--dry-run: NOTHING ABOVE WAS CHANGED." in out
    assert (_count(linked, "comparison_sheet_link"), _count(linked, "comparison_summary"),
            _count(linked, "command_record"), _events(linked)) == before


def test_the_product_purge_empties_the_history_its_receipts_and_its_events(linked: Stand, tmp_path: Path) -> None:
    steps = full_purge(purge, linked, tmp_path / "dump")
    assert steps["apply"][0] == 0 and steps["delete"][0] == 0, steps
    assert _count(linked, "comparison_sheet_link") == 0
    assert _count(linked, "comparison_summary") == 0
    assert _count(linked, "command_record") == 0
    assert _events(linked) == 0
    code, out, err = invoke(purge, linked, "plan")
    assert code == 0, err
    assert "nothing-to-purge: yes" in out


def test_the_project_erase_removes_one_projects_link_and_receipt_and_nothing_else(
    linked: Stand, tmp_path: Path
) -> None:
    first, second = linked.summary["first"], linked.summary["second"]
    kept = digest_of(linked.engine, "comparison_sheet_link", f"project_uid = '{second['project']}'")
    kept_receipt = digest_of(linked.engine, "command_record", f"command_id = '{second['command']}'")
    kept_summary = digest_of(linked.engine, "comparison_summary", f"project_uid = '{second['project']}'")
    kept_summary_receipt = digest_of(
        linked.engine, "command_record", f"command_id = '{second['summary_command']}'")
    assert kept[0] == 1 and kept_receipt[0] == 1 and kept_summary[0] == 1 and kept_summary_receipt[0] == 1

    code, out, err = invoke(erase, linked, "--project", first["project"])
    assert code == 0, err
    assert "comparison_sheet_link" in out and "comparison_summary" in out
    sha = _line(out, "plan-sha256")
    code, out, err = invoke(
        erase, linked, "--apply", "--project", first["project"], "--plan-sha256", sha, "--actor", "admin",
        "--reason", "test_data", "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path / "dump"))
    assert code == 0, (out, err)

    assert _count(linked, "comparison_sheet_link", "project_uid = :p", p=first["project"]) == 0
    assert _count(linked, "comparison_summary", "project_uid = :p", p=first["project"]) == 0
    assert _count(linked, "command_record", "command_id = :c", c=first["command"]) == 0
    assert _count(linked, "command_record", "command_id = :c", c=first["summary_command"]) == 0
    # the other project's history, its receipt and the journal stay byte for byte
    assert digest_of(linked.engine, "comparison_sheet_link", f"project_uid = '{second['project']}'") == kept
    assert digest_of(linked.engine, "command_record", f"command_id = '{second['command']}'") == kept_receipt
    assert digest_of(linked.engine, "comparison_summary", f"project_uid = '{second['project']}'") == kept_summary
    assert digest_of(
        linked.engine, "command_record", f"command_id = '{second['summary_command']}'") == kept_summary_receipt
    assert _events(linked) == 4  # the identity-only journal is not the project's rows


def test_the_history_references_only_what_the_purge_can_leave_consistent(linked: Stand) -> None:
    """Pins the foreign keys of ``0035``. A new reference is a decision about the purge, taken here."""
    with linked.engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT confrelid::regclass::text FROM pg_constraint WHERE contype = 'f' "
            "AND conrelid = 'public.comparison_sheet_link'::regclass")).scalars().all()
        incoming = connection.execute(text(
            "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype = 'f' "
            "AND confrelid = 'public.comparison_sheet_link'::regclass")).scalars().all()
    assert sorted(rows) == ["command_record", "document", "document_version", "document_version", "project"]
    assert set(rows) <= purge.PRODUCT_TABLES | purge.KEEP_TABLES | purge.MIXED_TABLES
    # the summaries reference it, and they are PRODUCT too and are truncated with it
    assert set(incoming) == {"comparison_summary"} <= purge.PRODUCT_TABLES
    with linked.engine.connect() as connection:
        summary_references = connection.execute(text(
            "SELECT confrelid::regclass::text FROM pg_constraint WHERE contype = 'f' "
            "AND conrelid = 'public.comparison_summary'::regclass")).scalars().all()
    assert sorted(summary_references) == ["command_record", "comparison_sheet_link", "project"]
