"""`F8-PUBLISH` on real PostgreSQL: the publication marker of a run, written at its start (migration ``0064``, plan-v5 section 3.6).

``audit_run.publication_mode`` is ``one_list`` only when the run has a ``stage_plan`` **and** the latest journalled ``one_list`` switch is on;
otherwise it is ``text_only``. The switch is read once, when the run is created, and the database freezes the column, so a later change of the
switch (or an old run) never moves it. Every case is a rolled-back transaction; the real ``start_audit_run`` with a stage plan is the start.

Each case that expects ``one_list`` has its control with one condition removed, so a start that wrote ``one_list`` always (or never) fails here.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.access.public import UserRepository
from auditmanager.analysis.public import ProviderConfig, ProviderMode
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.documents.public import DocumentRepository, ManifestEntry
from auditmanager.precedents.public import latest_setting_value, one_list_enabled
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.commands import start_audit_run
from auditmanager.runs.preflight import RunCostPreflight
from auditmanager.runs.repository import PUBLICATION_MODES, PUBLICATION_ONE_LIST, PUBLICATION_TEXT_ONLY, RunRepository
from auditmanager.runs.stage_plan import ModelAvailability, StagePlanDraft
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId, RunId
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role

SUBSCRIPTION = ModelAvailability(subscription=True, api=True)


def key() -> str:
    return f"marker-{uuid4().hex}"


@pytest.fixture
def world(session):  # type: ignore[no-untyped-def]
    documents = DocumentRepository()
    project = documents.create_project(session, "Marker synthetic")
    document = documents.create_document(session, project_uid=project.project_uid, display_title="Plan", section="AI")
    payload = uuid4().bytes
    digest = sha256(payload).hexdigest()
    blob_id = derive_blob_id(sha256=digest, size=len(payload))
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(blob_id, "marker-test-only", digest, len(payload),
        parse_blob_role("source_document"), "application/pdf"))
    blobs.mark_available(session, blob_id)
    version = documents.publish_version(session, document_uid=document, media_type="application/pdf",
        byte_size=len(payload), sha256=digest, page_count=2, source_filename=None,
        entries=(ManifestEntry("source.document", blob_id, digest, len(payload), "application/pdf"),),
        text_character_count=2_000, recognised_character_count=0, textless_pages=())
    actor = UserRepository().create_user(session, "marker-" + uuid4().hex, "marker-test-password")
    documents.insert_classification(session, version_uid=version, project_stage="P", section_code="AI",
        confirmed_by_user_uid=str(actor.user_uid))
    registry = load_text_profile_registry()
    return {"version": version, "project": str(project.project_uid), "registry": registry, "actor": str(actor.user_uid)}


def planned_start(session, world):  # type: ignore[no-untyped-def]
    """The real start of a run with a stage plan (the layout on)."""
    registry = world["registry"]
    flight = RunCostPreflight(
        section_profiles=registry.section_profiles(), text_profiles=registry.resolve,
        provider_config=ProviderConfig(ProviderMode.RECORDED, "claude-sonnet-5-5", 1.0, None, False), provider_mode="recorded")
    cells = layout.preset_cells("claude_only")
    plan = StagePlanDraft("slr_01M2545JSD15ETSNNV904X991J", "claude_only", cells, {c.model_id: SUBSCRIPTION for c in cells})
    shown = flight.estimate_run(session, version_uid=str(world["version"]), stage_plan=plan)
    consent = {"estimate_digest": shown.estimate_digest, "ceiling_micros": 0, "confirmed": True}
    return start_audit_run(
        session, version_uid=world["version"], provider_mode="recorded", idempotency_key=key(),
        section_profiles=registry.section_profiles(), text_profiles=registry.resolve, input_budget_characters=100,
        operational_model_id="claude-sonnet-5-5", norms_snapshot=lambda _: None, cost_preflight=flight, cost_consent=consent,
        cost_actor_uid=world["actor"], stage_plans=lambda _: plan)


def journal(session, world, enabled: Any, *, name: str = "one_list") -> None:  # type: ignore[no-untyped-def]
    """One row of the switch journal, numbered after the last (the database numbers without a gap)."""
    revision = session.execute(
        text("SELECT coalesce(max(revision), 0) + 1 FROM precedent_setting_event WHERE setting_name = :n"), {"n": name}).scalar_one()
    session.execute(
        text("INSERT INTO precedent_setting_event (setting_name, revision, value, actor_user_uid) VALUES (:n, :r, CAST(:v AS jsonb), :a)"),
        {"n": name, "r": revision, "v": '{"enabled": %s}' % ("true" if enabled else "false"), "a": world["actor"]})


def mode_of(session, run_id: str) -> str:  # type: ignore[no-untyped-def]
    column = session.execute(text("SELECT publication_mode FROM audit_run WHERE run_id = :r"), {"r": run_id}).scalar_one()
    assert RunRepository().get(session, run_id).publication_mode == column, "the row the executor reads carries the column"
    return column


def legacy_run(session, world) -> str:  # type: ignore[no-untyped-def]
    """A run with no stage plan, written by the repository the way the legacy start writes it."""
    run_id = RunId.new().value
    RunRepository().create(
        session, run_id=run_id, project_uid=world["project"], version_uid=str(world["version"]),
        analysis_profile_id=AnalysisProfileId.new().value, prompt_bundle_id=PromptBundleId.new().value, provider_mode="recorded",
        frozen_input_digest=sha256(run_id.encode()).hexdigest(), command_id=None)
    return run_id


# --- the switch ---------------------------------------------------------------------------------------------------------------


def test_the_switch_reads_off_when_nothing_is_journalled_and_follows_the_latest_row(session, world) -> None:  # type: ignore[no-untyped-def]
    assert latest_setting_value(session, "one_list") is None and one_list_enabled(session) is False
    journal(session, world, True)
    assert one_list_enabled(session) is True and latest_setting_value(session, "one_list") == {"enabled": True}
    journal(session, world, False)
    assert one_list_enabled(session) is False, "the latest row wins, not the first"
    journal(session, world, True)
    assert one_list_enabled(session) is True


def test_another_switch_is_not_this_one(session, world) -> None:  # type: ignore[no-untyped-def]
    journal(session, world, True, name="critic_context")
    assert one_list_enabled(session) is False


# --- the marker ---------------------------------------------------------------------------------------------------------------


def test_the_vocabulary_is_the_databases() -> None:
    assert set(PUBLICATION_MODES) == {PUBLICATION_TEXT_ONLY, PUBLICATION_ONE_LIST} == {"text_only", "one_list"}


def test_a_planned_run_with_the_switch_on_is_one_list(session, world) -> None:  # type: ignore[no-untyped-def]
    journal(session, world, True)
    started = planned_start(session, world)
    assert mode_of(session, started.run_id) == "one_list"
    assert session.execute(text("SELECT stage_plan IS NOT NULL FROM audit_run WHERE run_id = :r"), {"r": started.run_id}).scalar_one() is True


def test_the_control_the_same_planned_start_with_nothing_journalled_is_text_only(session, world) -> None:  # type: ignore[no-untyped-def]
    assert mode_of(session, planned_start(session, world).run_id) == "text_only"


def test_the_control_the_same_planned_start_with_the_switch_turned_off_again_is_text_only(session, world) -> None:  # type: ignore[no-untyped-def]
    journal(session, world, True)
    journal(session, world, False)
    assert mode_of(session, planned_start(session, world).run_id) == "text_only"


def test_a_run_without_a_stage_plan_is_text_only_even_with_the_switch_on(session, world) -> None:  # type: ignore[no-untyped-def]
    assert mode_of(session, legacy_run(session, world)) == "text_only", "the control: the switch is off here"
    journal(session, world, True)
    run_id = legacy_run(session, world)
    assert mode_of(session, run_id) == "text_only"
    assert session.execute(text("SELECT stage_plan IS NULL FROM audit_run WHERE run_id = :r"), {"r": run_id}).scalar_one() is True


def test_a_switch_journalled_later_does_not_move_a_run_already_started(session, world) -> None:  # type: ignore[no-untyped-def]
    before = planned_start(session, world)
    journal(session, world, True)
    after = planned_start(session, world)
    assert (mode_of(session, before.run_id), mode_of(session, after.run_id)) == ("text_only", "one_list")
    journal(session, world, False)
    assert (mode_of(session, before.run_id), mode_of(session, after.run_id)) == ("text_only", "one_list")


def test_the_database_freezes_the_marker(session, world) -> None:  # type: ignore[no-untyped-def]
    journal(session, world, True)
    run_id = planned_start(session, world).run_id
    assert mode_of(session, run_id) == "one_list"
    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(text("UPDATE audit_run SET publication_mode = 'text_only' WHERE run_id = :r"), {"r": run_id})
    assert mode_of(session, run_id) == "one_list"


def test_the_database_refuses_one_list_for_a_run_without_a_plan_even_when_a_caller_asks_for_it(session, world) -> None:  # type: ignore[no-untyped-def]
    run_id = RunId.new().value
    with pytest.raises(DomainError):
        with session.begin_nested():
            RunRepository().create(
                session, run_id=run_id, project_uid=world["project"], version_uid=str(world["version"]),
                analysis_profile_id=AnalysisProfileId.new().value, prompt_bundle_id=PromptBundleId.new().value, provider_mode="recorded",
                frozen_input_digest=sha256(run_id.encode()).hexdigest(), command_id=None, publication_mode="one_list")


def test_a_mode_the_database_does_not_know_is_refused_before_it_is_written(session, world) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        RunRepository().create(
            session, run_id=RunId.new().value, project_uid=world["project"], version_uid=str(world["version"]),
            analysis_profile_id=AnalysisProfileId.new().value, prompt_bundle_id=PromptBundleId.new().value, provider_mode="recorded",
            frozen_input_digest="0" * 64, command_id=None, publication_mode="both")
