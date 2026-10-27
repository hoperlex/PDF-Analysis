"""`ANALYSIS-PRESETS-01`: a preset is executor configuration, so recovery treats it like the connections.

* the declarations (no database): the table is KEEP and append-only, its three command receipts are
  KEEP, and the three ``executor.preset_*`` event types fall in a KEEP prefix and in no PRODUCT one;
* the real product purge, on a private clone of the stand in miniature: a preset, its audit event and
  its command receipts survive byte for byte, while a run that recorded the preset (a PRODUCT row that
  references the KEEP table, never the reverse) is purged with the rest of the product data.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from auditmanager.executors import preset_audit
from auditmanager.executors.public import create_connection, create_preset
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ExecutorConnectionRevisionId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from scripts.recovery import grant_classification as grants
from scripts.recovery import product_purge as tool
from scripts.recovery import schema_coverage as coverage
from tests.integration.recovery.purge_seed import digest_of
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, full_purge, seeded, stand,
)

ACTOR = "usr_01M5F21PBT7E8WRN3M61BDQFDD"
TABLE = "analysis_preset_revision"
COMMAND_TYPES = {"create_analysis_preset", "revise_analysis_preset", "archive_analysis_preset"}


def test_the_table_is_kept_by_the_purge_and_append_only_for_the_application_role() -> None:
    assert TABLE in coverage.TABLES
    assert TABLE in tool.KEEP_TABLES and TABLE not in tool.PRODUCT_TABLES | tool.MIXED_TABLES
    assert TABLE in grants.APPEND_ONLY and grants.table_privileges(TABLE) == ("SELECT", "INSERT")


def test_the_three_receipts_are_kept_and_no_product_command_claims_them() -> None:
    assert COMMAND_TYPES <= tool.KEEP_COMMAND_TYPES
    assert not COMMAND_TYPES & tool.PRODUCT_COMMAND_TYPES


def test_the_three_event_types_are_kept_and_no_product_family_claims_them() -> None:
    for event_type in preset_audit.PRESET_EVENT_TYPES:
        assert event_type.startswith(tool.KEEP_EVENT_PREFIXES), event_type
        assert not event_type.startswith(tool.PRODUCT_EVENT_PREFIXES), event_type


def test_the_purge_keeps_the_presets_their_events_and_receipts_and_removes_the_run_that_used_one(
    stand: Stand, tmp_path: Path
) -> None:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
           "version": str(VersionUid.new()), "run": str(RunId.new()),
           "revision": str(ExecutorConnectionRevisionId.new())}
    with create_session_factory(stand.engine).begin() as session:
        connection = create_connection(
            session, kind="http_api", display_name="proxy", roles=frozenset({"admin"}),
            idempotency_key=f"conn-{uuid4().hex}", actor_uid=ACTOR).connection_id
        preset = create_preset(
            session, name="Основной", executor_connection_id=connection, roles=frozenset({"admin"}),
            idempotency_key=f"preset-{uuid4().hex}", actor_uid=ACTOR)
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'p')"), ids)
        session.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                             "VALUES (:document, :project, 'D')"), ids)
        session.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"),
            {**ids, "sha": "a" * 64})
        session.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, "
            "pin_id, gateway_model, billing, allow_client_documents, timeout_seconds, api_flavour, base_url, "
            "transport) VALUES (:revision, :c, 1, :actor, 'claude-opus-5', 'anthropic/claude-opus-5', "
            "'metered', false, 60, 'openai_chat', 'https://proxy.test', 'direct')"),
            {**ids, "c": connection, "actor": ACTOR})
        session.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
            "provider_mode, frozen_input_digest, connection_revision_id, preset_revision_id) VALUES (:run, "
            ":project, :version, :profile, :bundle, 'recorded', :digest, :revision, :preset)"),
            {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
             "digest": "b" * 64, "preset": preset.revision_id})

    def count(sql: str, **params: object) -> int:
        with stand.engine.connect() as raw:
            return int(raw.execute(text(sql), params).scalar_one())

    receipts = "SELECT count(*) FROM command_record WHERE command_type = 'create_analysis_preset'"
    events = "SELECT count(*) FROM audit_event WHERE event_type = 'executor.preset_created'"
    kept_before = digest_of(stand.engine, TABLE)
    assert kept_before[0] == 1 and count(receipts) == 1 and count(events) == 1
    assert count("SELECT count(*) FROM audit_run WHERE run_id = :r", r=ids["run"]) == 1

    steps = full_purge(tool, stand, tmp_path / "dump")

    assert steps["apply"][0] == 0 and steps["delete"][0] == 0, steps
    assert digest_of(stand.engine, TABLE) == kept_before  # the preset is the same row
    assert count(receipts) == 1 and count(events) == 1
    assert count("SELECT count(*) FROM audit_run WHERE run_id = :r", r=ids["run"]) == 0
    assert count("SELECT count(*) FROM executor_connection_revision WHERE revision_id = :r", r=ids["revision"]) == 1
