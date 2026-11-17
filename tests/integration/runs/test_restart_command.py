"""`RUN-RESTART-01`: the command ``restart_run`` and the price of a restart, on real PostgreSQL.

The sources are runs of the **stage layout** (the only runs a restart accepts), started by the real command with the real cost preflight and the
consent v2 it binds, then moved to an ended state with the stage rows, blobs and model calls a finished run would hold. What is measured:

* a restart creates ONE new run that copies every setting the source froze, links it to the source by ``started_from_run_id`` and ``restart_point``
  (never ``start_stage_id``), names the command and the starter, and queues it; the source is not touched and not tombstoned (that is the executor's, when
  the new run publishes);
* each refusal of the contract is typed with the words the contract gives and **writes nothing, the idempotency key included**;
* the same key replays the run it created and another chip under it is ``idempotency_key_reuse``;
* the price is for the chips the restart computes, bounded by the calls the source chain made, and its digest is bound to this source and this chip.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.access.public import UserRepository
from auditmanager.analysis.public import ARTIFACT_ROLE as TEXT_OBSERVATIONS_ROLE
from auditmanager.analysis.public import ProviderConfig, ProviderMode, TEXT_STAGE_VERSION, default_registry
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.documents.public import DocumentRepository, ManifestEntry
from auditmanager.jobs.public import JobRepository
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.commands import cancel_audit_run, delete_audit_run, restart_run, start_audit_run
from auditmanager.runs.preflight import RunCostPreflight
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.restart import (
    RESTART_POINTS, chain_calls, has_live_lease, lineage_of, replaced_by, restart_chain, tombstone_lineage,
)
from auditmanager.runs.stage_plan import ModelAvailability, StagePlanDraft
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AnalysisProfileId, ModelCallId
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role

SUBSCRIPTION = ModelAvailability(subscription=True, api=True)
EXPERT = frozenset({"expert"})
EXTENDED_REVIEW_ROLE = "analysis.extended_review"
PLAN_REVISION = "slr_01M2545JSD15ETSNNV904X991J"


def key() -> str:
    return f"restart-{uuid4().hex}"


def _sha(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def draft() -> StagePlanDraft:
    cells = layout.preset_cells("claude_only")
    return StagePlanDraft(PLAN_REVISION, "claude_only", cells, {c.model_id: SUBSCRIPTION for c in cells})


class World:
    """One classified version of two pages and the services a planned start and a restart need."""

    def __init__(self, session) -> None:  # type: ignore[no-untyped-def]
        self.session = session
        documents = DocumentRepository()
        project = documents.create_project(session, "Restart synthetic")
        document = documents.create_document(session, project_uid=project.project_uid, display_title="Restart", section="AI")
        payload = uuid4().bytes
        digest = sha256(payload).hexdigest()
        blob_id = derive_blob_id(sha256=digest, size=len(payload))
        self.blobs = BlobMetadataRepository()
        self.blobs.record_verified(session, VerifiedBlob(blob_id, "restart-test-only", digest, len(payload),
            parse_blob_role("source_document"), "application/pdf"))
        self.blobs.mark_available(session, blob_id)
        self.version = documents.publish_version(session, document_uid=document, media_type="application/pdf", byte_size=len(payload),
            sha256=digest, page_count=2, source_filename=None,
            entries=(ManifestEntry("source.document", blob_id, digest, len(payload), "application/pdf"),),
            text_character_count=2_000, recognised_character_count=0, textless_pages=())
        self.actor = str(UserRepository().create_user(session, "restart-" + uuid4().hex, "restart-test-password").user_uid)
        documents.insert_classification(session, version_uid=self.version, project_stage="P", section_code="AI", confirmed_by_user_uid=self.actor)
        self.registry = load_text_profile_registry()
        self.plan = draft()
        self.flight = RunCostPreflight(
            section_profiles=self.registry.section_profiles(), text_profiles=self.registry.resolve,
            provider_config=ProviderConfig(ProviderMode.RECORDED, "claude-sonnet-5-5", 1.0, None, False), provider_mode="recorded")
        self.runs = RunRepository()

    # -- a planned source ---------------------------------------------------------------------------------------------------------
    def planned_run(self) -> str:
        shown = self.flight.estimate_run(self.session, version_uid=str(self.version), stage_plan=self.plan)
        started = start_audit_run(
            self.session, version_uid=self.version, provider_mode="recorded", idempotency_key=key(),
            section_profiles=self.registry.section_profiles(), text_profiles=self.registry.resolve, input_budget_characters=100,
            operational_model_id="claude-sonnet-5-5", norms_snapshot=lambda _: None, cost_preflight=self.flight,
            cost_consent={"estimate_digest": shown.estimate_digest, "ceiling_micros": 0, "confirmed": True},
            cost_actor_uid=self.actor, stage_plans=lambda _: self.plan, started_by_user_uid=self.actor)
        return str(started.run_id)

    def legacy_run(self) -> str:
        """A run of the legacy route (no stage plan): a claim of it binds no cell, so a test may hold its lease."""
        shown = self.flight.estimate_run(self.session, version_uid=str(self.version), stage_plan=None)
        started = start_audit_run(
            self.session, version_uid=self.version, provider_mode="recorded", idempotency_key=key(),
            section_profiles=self.registry.section_profiles(), text_profiles=self.registry.resolve, input_budget_characters=100,
            operational_model_id="claude-sonnet-5-5", norms_snapshot=lambda _: None, cost_preflight=self.flight,
            cost_consent={"estimate_digest": shown.estimate_digest, "ceiling_micros": shown.as_dict()["recommended_ceiling_micros"] or 1_000_000,
                          "confirmed": True}, cost_actor_uid=self.actor, stage_plans=lambda _: None, started_by_user_uid=self.actor)
        return str(started.run_id)

    def artifact(self, role: str, *, size: int = 11) -> dict[str, Any]:
        sha = _sha(f"{uuid4().hex}:{role}")
        blob_id = derive_blob_id(sha256=sha, size=size)
        self.blobs.record_verified(self.session, VerifiedBlob(blob_id, "restart-test-only", sha, size, parse_blob_role("source_document"),
            "application/json"))
        self.blobs.mark_available(self.session, blob_id)
        return {"role": role, "blob_id": str(blob_id), "sha256": sha, "size_bytes": size, "media_type": "application/json"}

    def stage_row(self, run_id: str, stage_id: str, *, status: str = "succeeded", artifacts=None, metrics=None) -> None:  # type: ignore[no-untyped-def]
        definition = default_registry().stage(stage_id)
        refs = [self.artifact(role) for role in definition.required_output_roles] if artifacts is None else artifacts
        self.session.execute(text(
            "INSERT INTO stage_result (run_id, stage_id, stage_version, status, artifacts, metrics, error, started_at, finished_at) "
            "VALUES (:r, :s, :v, :st, CAST(:a AS jsonb), CAST(:m AS jsonb), CAST(:e AS jsonb), now(), now())"),
            {"r": run_id, "s": stage_id, "v": TEXT_STAGE_VERSION if stage_id == "text_analysis" else definition.stage_version, "st": status,
             "a": json.dumps(refs), "m": json.dumps(metrics or {}),
             "e": None if status == "succeeded" else json.dumps({"code": "analysis_failed", "message": "a procedure of the extended review fell short", "retryable": False})})

    def model_call(self, run_id: str, phase: str, *, status: str = "succeeded", reply: bool = True) -> None:
        parameters = {"extended_phase": phase, "extended_unit_key": _sha(f"{run_id}:{phase}:{uuid4().hex}")}
        if reply:
            blob = self.artifact("analysis.extended_reply", size=5)
            parameters.update(extended_reply_blob_id=blob["blob_id"], extended_reply_sha256=blob["sha256"], extended_reply_size=5)
        self.session.execute(text(
            "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, provider_mode, parameters, request_sha256, "
            "response_sha256, status, error_code, cost_micros, cost_basis) VALUES (:id, :r, 'text_analysis', 'anthropic', 'claude-sonnet-5-5', "
            "'recorded', CAST(:p AS jsonb), :q, :s, :st, :e, 0, 'measured')"),
            {"id": str(ModelCallId.new()), "r": run_id, "p": json.dumps(parameters), "q": _sha("q" + phase), "s": _sha("s" + phase) if status != "failed" else None,
             "st": status, "e": "analysis_failed" if status == "failed" else None})

    def running(self, run_id: str) -> None:
        """Walk a run the start left ``created`` to ``running`` along the declared edges, as the executor does."""
        if self.runs.get(self.session, run_id).state == "created":
            self.runs.advance(self.session, run_id=run_id, from_state="created", to_state="queued")
        self.runs.advance(self.session, run_id=run_id, from_state="queued", to_state="running")

    def end(self, run_id: str, state: str = "partial") -> None:
        """Walk a run the start left ``created`` to an ended state through the repository, as the executor does."""
        self.running(run_id)
        if state == "failed":
            self.runs.terminate(self.session, run_id=run_id, from_state="running", to_state="failed", terminal_reason="analysis_failed",
                                degradation_set=("text_analysis",))
            return
        self.runs.advance(self.session, run_id=run_id, from_state="running", to_state="validating")
        if state == "partial":
            self.runs.terminate(self.session, run_id=run_id, from_state="validating", to_state="partial", degradation_set=("text_analysis",))
        else:
            self.runs.terminate(self.session, run_id=run_id, from_state="validating", to_state="published")

    def ended_source(self, state: str = "partial", *, completed: bool = True, no_reply: tuple[str, ...] = ()) -> str:
        """A planned run that ran its four stages and the extended review as far as ``completed`` says, and ended ``state``."""
        run_id = self.planned_run()
        for stage_id in ("source_preparation", "page_geometry_extraction", "document_context_build"):
            self.stage_row(run_id, stage_id)
        done = {"extended_block_analysis": "completed", "extended_comprehensive_analysis": "completed", "extended_finding_merge": "completed",
                "extended_norm_verification": "completed" if completed else "failed", "extended_finding_review": "completed" if completed else "queued"}
        self.stage_row(run_id, "text_analysis", status="partial", artifacts=[self.artifact(TEXT_OBSERVATIONS_ROLE), self.artifact(EXTENDED_REVIEW_ROLE)],
                       metrics={"pages_total": 2, "pages_analysed": 2, "provider_mode": "recorded", **done})
        for phase in ("v2:blocks:0", "v2:comprehensive:0", "v2:norm_verification:0", "v2:finding_review:substantive:0"):
            self.model_call(run_id, phase, reply=phase not in no_reply)
        self.end(run_id, state)
        return run_id

    def restart(self, source: str, point: str, *, idempotency_key: str | None = None, consent: bool = True, roles=EXPERT, **extra: Any):  # type: ignore[no-untyped-def]
        digest = None
        if consent:
            digest = self.flight.estimate_restart(self.session, run_id=source, restart_point=point, stage_plan=self.plan).estimate_digest
        return restart_run(
            self.session, source_run_id=source, restart_point=point, roles=roles, user_uid=self.actor, idempotency_key=idempotency_key or key(),
            provider_mode="recorded", section_profiles=self.registry.section_profiles(), cost_preflight=self.flight,
            cost_consent=None if digest is None else {"estimate_digest": digest, "ceiling_micros": 0, "confirmed": True},
            cost_actor_uid=self.actor, stage_plans=lambda _: self.plan, **extra)

    def counts(self) -> dict[str, int]:
        return {table: int(self.session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
                for table in ("audit_run", "command_record", "job", "audit_event")}


@pytest.fixture
def world(session) -> World:  # type: ignore[no-untyped-def]
    return World(session)


def _refused(world: World, call, code: ErrorCode, **details: Any) -> DomainError:  # type: ignore[no-untyped-def]
    """The call is refused with ``code`` and these details, and wrote nothing (not a row, not the key)."""
    before = world.counts()
    with pytest.raises(DomainError) as refusal:
        with world.session.begin_nested():
            call()
    assert refusal.value.code is code
    for name, value in details.items():
        assert refusal.value.detail_fields.get(name) == value, (name, refusal.value.detail_fields)
    assert world.counts() == before, "a refused restart leaves no run, no job, no event and no idempotency key"
    return refusal.value


# -- the new run ----------------------------------------------------------------------------------------------------------------------


def test_a_restart_creates_one_queued_run_with_the_settings_of_its_source(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    before = dict(world.session.execute(text("SELECT to_jsonb(r) FROM audit_run r WHERE run_id = :r"), {"r": source}).scalar_one())
    started = world.restart(source, "norms")
    assert started.replayed is False
    old, new = world.runs.get(world.session, source), world.runs.get(world.session, started.run_id)
    assert (new.started_from_run_id, new.restart_point, new.start_stage_id, new.reaudit_of_run_id) == (source, "norms", None, None)
    assert new.state == "queued" and new.command_id == started.command_id and new.started_by_user_uid == world.actor
    for column in ("version_uid", "project_uid", "analysis_profile_id", "prompt_bundle_id", "provider_mode", "frozen_input_digest",
                   "norms_snapshot_id", "publication_mode"):
        assert getattr(new, column) == getattr(old, column), column
    assert [(c.cell_key, c.model_id, c.effort, c.access) for c in layout.parse_plan(new.stage_plan).cells] == [
        (c.cell_key, c.model_id, c.effort, c.access) for c in layout.parse_plan(old.stage_plan).cells], "the cells are the source's"
    assert new.binding_state == "pending" and new.connection_revision_id is None, "dispatch binds the cells of the new run"
    assert world.runs.cell_bindings(world.session, started.run_id) == {}
    outcome = world.session.execute(text("SELECT outcome FROM command_record WHERE command_id = :c"), {"c": started.command_id}).scalar_one()
    assert outcome["restart_of_run_id"] == source and outcome["restart_point"] == "norms" and outcome["cost_consent"]["stage_plan_digest"]
    assert world.session.execute(text("SELECT state FROM job WHERE run_id = :r"), {"r": started.run_id}).scalar_one() == "queued"
    # The source is exactly what it was, and listed: the tombstone is written when the new run publishes, never here.
    assert dict(world.session.execute(text("SELECT to_jsonb(r) FROM audit_run r WHERE run_id = :r"), {"r": source}).scalar_one()) == before
    assert world.runs.is_deleted(world.session, source) is False and replaced_by(world.session, source) is None


@pytest.mark.parametrize("point", RESTART_POINTS)
def test_every_chip_can_be_restarted_from_a_partial_source(world, point) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    started = world.restart(source, point)
    assert world.runs.get(world.session, started.run_id).restart_point == point


@pytest.mark.parametrize("state", ["failed", "cancelled"])
def test_a_failed_or_a_cancelled_source_is_restarted_too(world, state) -> None:  # type: ignore[no-untyped-def]
    if state == "failed":
        source = world.ended_source("failed")
    else:
        source = world.planned_run()
        for stage_id in ("source_preparation", "page_geometry_extraction", "document_context_build"):
            world.stage_row(source, stage_id)
        cancel_audit_run(world.session, run_id=source, roles=EXPERT, idempotency_key=key())
    # A cancelled run has no text: it can only be restarted from where the text is computed.
    started = world.restart(source, "text")
    assert world.runs.get(world.session, started.run_id).started_from_run_id == source


def test_the_key_replays_the_run_it_created_and_another_chip_under_it_is_a_reuse(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    first_key = key()
    first = world.restart(source, "norms", idempotency_key=first_key)
    counts = world.counts()
    again = world.restart(source, "norms", idempotency_key=first_key)
    assert again.replayed is True and again.run_id == first.run_id and world.counts() == counts
    other = _refused(world, lambda: world.restart(source, "review", idempotency_key=first_key), ErrorCode.IDEMPOTENCY_KEY_REUSE)
    assert other.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


# -- the refusals ---------------------------------------------------------------------------------------------------------------------


def test_a_run_that_is_published_or_has_not_ended_is_not_restarted(world) -> None:  # type: ignore[no-untyped-def]
    published = world.ended_source("published")
    _refused(world, lambda: world.restart(published, "text"), ErrorCode.STATE_TRANSITION_NOT_ALLOWED, machine="audit_run",
             current_state="published", requested_state="restart")
    running = world.planned_run()
    world.running(running)
    _refused(world, lambda: world.restart(running, "text"), ErrorCode.STATE_TRANSITION_NOT_ALLOWED, current_state="running", requested_state="restart")


def test_an_unknown_run_is_not_found_and_a_viewer_may_not_restart(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    _refused(world, lambda: world.restart("run_" + "0" * 26, "text", consent=False), ErrorCode.NOT_FOUND)
    _refused(world, lambda: world.restart(source, "text", roles=frozenset({"viewer"})), ErrorCode.PERMISSION_DENIED)


def test_a_source_that_was_deleted_is_not_restarted(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    delete_audit_run(world.session, run_id=source, roles=EXPERT, user_uid=world.actor, idempotency_key=key())
    _refused(world, lambda: world.restart(source, "text", consent=False), ErrorCode.CONFLICT, conflict_reason="restart_source_deleted")


def test_a_source_whose_work_still_holds_a_lease_is_not_restarted(world) -> None:  # type: ignore[no-untyped-def]
    source = world.legacy_run()
    world.runs.advance(world.session, run_id=source, from_state="created", to_state="queued")
    JobRepository().start_execution(world.session, run_id=source)  # the claim: an Attempt and its Lease
    world.running(source)
    world.runs.terminate(world.session, run_id=source, from_state="running", to_state="failed", terminal_reason="analysis_failed",
                         degradation_set=("text_analysis",))
    assert has_live_lease(world.session, source) is True
    _refused(world, lambda: world.restart(source, "text", consent=False), ErrorCode.CONFLICT, conflict_reason="restart_source_leased")
    clean = world.ended_source("partial")
    assert has_live_lease(world.session, clean) is False


def test_one_restart_of_a_lineage_is_active_at_a_time(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    first = world.restart(source, "norms")
    _refused(world, lambda: world.restart(source, "review"), ErrorCode.CONFLICT, conflict_reason="restart_in_progress")
    # Stopped, the source can be restarted again.
    cancel_audit_run(world.session, run_id=first.run_id, roles=EXPERT, idempotency_key=key())
    second = world.restart(source, "review")
    assert second.run_id != first.run_id
    # A restart of a restart of the lineage while one runs is refused as well: the lineage, not only the source, has one active restart.
    cancel_audit_run(world.session, run_id=second.run_id, roles=EXPERT, idempotency_key=key())
    assert restart_chain(world.session, second.run_id) == [second.run_id, source]
    assert [member.run_id for member in lineage_of(world.session, source)] == [source, first.run_id, second.run_id]


def test_the_database_maps_a_second_active_restart_of_one_source_to_the_same_refusal(world) -> None:  # type: ignore[no-untyped-def]
    """Were two restarts to race past the command's own read, ``ux_audit_run_active_restart`` (SQLSTATE 23505) refuses the second."""
    source = world.ended_source("partial")
    first = world.restart(source, "norms")
    command = world.session.execute(text("SELECT command_id FROM audit_run WHERE run_id = :r"), {"r": first.run_id}).scalar_one()
    from auditmanager.shared.identity import RunId

    with pytest.raises(DomainError) as refusal:
        with world.session.begin_nested():
            old = world.runs.get(world.session, source)
            world.runs.create(
                world.session, run_id=str(RunId.new()), project_uid=old.project_uid, version_uid=old.version_uid,
                analysis_profile_id=old.analysis_profile_id, prompt_bundle_id=old.prompt_bundle_id, provider_mode="recorded",
                frozen_input_digest=old.frozen_input_digest, command_id=command, started_from_run_id=source, restart_point="review",
                started_by_user_uid=world.actor)
    assert refusal.value.code is ErrorCode.CONFLICT and refusal.value.detail_fields["conflict_reason"] == "restart_in_progress"


def test_a_run_of_the_legacy_route_is_not_restarted(world) -> None:  # type: ignore[no-untyped-def]
    source = world.legacy_run()
    world.end(source, "partial")
    _refused(world, lambda: world.restart(source, "text", consent=False), ErrorCode.ANALYSIS_INPUT_INVALID,
             reason="restart_source_not_stage_layout")


def test_a_source_of_the_extended_review_v3_is_refused(world, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v3")
    source = world.ended_source("partial")
    monkeypatch.delenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN")
    _refused(world, lambda: world.restart(source, "text", consent=False), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_source_not_v2")


def test_settings_that_moved_since_the_source_started_are_refused_not_followed(world, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    monkeypatch.setenv("AUDITMANAGER_V2_QUALITY", "0")  # today's extended-review policy is not the one the source froze
    _refused(world, lambda: world.flight.estimate_restart(world.session, run_id=source, restart_point="text", stage_plan=world.plan),
             ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_settings_differ")
    _refused(world, lambda: world.restart(source, "text", consent=False), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_settings_differ")


def test_today_routing_that_is_not_the_sources_profile_is_refused(world) -> None:  # type: ignore[no-untyped-def]
    """The source froze one analysis profile; a version routed to another today would be asked other questions, so its replies would not replay."""
    source = world.ended_source("partial")
    world.session.execute(text("SET LOCAL session_replication_role = replica"))  # the column is frozen: the test moves it as a corrupted row would be
    world.session.execute(text("UPDATE audit_run SET analysis_profile_id = :p WHERE run_id = :r"), {"p": str(AnalysisProfileId.new()), "r": source})
    world.session.execute(text("SET LOCAL session_replication_role = origin"))
    _refused(world, lambda: world.restart(source, "text", consent=False), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_settings_differ")


@pytest.mark.parametrize("point", ["blocks", "review"])
def test_a_text_that_cannot_be_taken_byte_for_byte_refuses_the_chips_after_the_text(world, point) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    world.session.execute(text(
        "UPDATE stage_result SET metrics = jsonb_set(metrics, '{pages_analysed}', '1') WHERE run_id = :r AND stage_id = 'text_analysis'"), {"r": source})
    _refused(world, lambda: world.restart(source, point), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_text_not_reusable",
             restart_point="text", stage_id="text_analysis")
    # The chips that compute the text do not need it.
    assert world.restart(source, "text").run_id


def test_a_chip_whose_calls_have_no_saved_reply_refuses_the_chips_after_it(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial", no_reply=("v2:comprehensive:0",))
    _refused(world, lambda: world.restart(source, "norms"), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_reply_missing",
             restart_point="cross_check", stage_id="comprehensive_analysis")
    # Restarting from that chip, or earlier, computes it: nothing is missing.
    assert world.restart(source, "cross_check").run_id


def test_a_saved_reply_whose_blob_is_gone_refuses_the_chips_after_it(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    blob = world.session.execute(text(
        "SELECT parameters ->> 'extended_reply_blob_id' FROM model_call WHERE run_id = :r AND parameters ->> 'extended_phase' = 'v2:blocks:0'"),
        {"r": source}).scalar_one()
    world.session.execute(text("SET LOCAL session_replication_role = replica"))
    world.session.execute(text("DELETE FROM blob WHERE blob_id = :b"), {"b": blob})
    world.session.execute(text("SET LOCAL session_replication_role = origin"))
    _refused(world, lambda: world.restart(source, "cross_check"), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_reply_missing", restart_point="blocks")


def test_a_failed_call_with_no_reply_is_a_reply_a_replay_cannot_take(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    world.model_call(source, "v2:blocks:1:leg2", status="failed", reply=False)  # a leg that failed after its retries
    _refused(world, lambda: world.restart(source, "merge"), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_reply_missing", restart_point="blocks")
    calls = chain_calls(world.session, [source])
    assert calls.unanswered_by_row == {"blocks": frozenset({"v2:blocks:1:leg2"})}


def test_a_kept_procedure_that_did_not_reach_its_end_refuses_the_chips_after_it(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial", completed=False)  # norm verification failed, the critic never started
    _refused(world, lambda: world.restart(source, "review"), ErrorCode.ANALYSIS_INPUT_INVALID, reason="restart_reply_missing", restart_point="norms")
    # From the chip that failed the source can be restarted: it is computed again.
    assert world.restart(source, "norms").run_id


def test_a_preparation_output_that_cannot_be_taken_is_refused_with_the_start_from_stage_reasons(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    world.session.execute(text(
        "UPDATE stage_result SET status = 'failed', error = CAST(:e AS jsonb) WHERE run_id = :r AND stage_id = 'page_geometry_extraction'"),
        {"r": source, "e": json.dumps({"code": "analysis_failed", "message": "x", "retryable": False})})
    for point in ("text", "review"):
        _refused(world, lambda point=point: world.restart(source, point), ErrorCode.ANALYSIS_INPUT_INVALID,
                 reason="source_stage_not_completed", stage_id="page_geometry_extraction")
    # «Подготовка» takes nothing from the source but its settings and its link: it is a full rerun and does not look at the source's outputs.
    started = world.restart(source, "preparation")
    assert world.runs.get(world.session, started.run_id).restart_point == "preparation"


# -- the price ------------------------------------------------------------------------------------------------------------------------


def test_the_price_is_for_the_chips_the_restart_computes(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    estimates = {point: world.flight.estimate_restart(world.session, run_id=source, restart_point=point, stage_plan=world.plan).as_dict()
                 for point in RESTART_POINTS}
    for position, point in enumerate(RESTART_POINTS):
        public = estimates[point]
        assert public["start_from_run_id"] == source and public["restart_point"] == point
        assert public["reused_restart_points"] == list(RESTART_POINTS[:position])
        assert public["computed_restart_points"] == list(RESTART_POINTS[position:])
        assert public.get("start_stage_id") is None
    calls = [estimates[point]["calls"] for point in RESTART_POINTS]
    assert calls == sorted(calls, reverse=True), "the later the chip, the fewer calls are priced"
    assert estimates["preparation"]["calls"] == estimates["text"]["calls"] > estimates["blocks"]["calls"] > estimates["norms"]["calls"] > 0
    assert estimates["correction"]["calls"] == 0, "the corrector calls no model: a restart from it computes nothing paid"
    assert estimates["merge"]["calls"] == estimates["norms"]["calls"], "«Свод» is not a call: the chips before «Нормы» cost the same"
    # Every model of the plan keeps its line, even at zero, so the consent still binds the whole plan.
    assert {line["model_id"] for line in estimates["correction"]["models"]} == {line["model_id"] for line in estimates["preparation"]["models"]}


def test_a_row_the_source_ran_to_its_end_is_priced_by_the_calls_it_made(world) -> None:  # type: ignore[no-untyped-def]
    unbounded = world.ended_source("partial", completed=False)  # norm verification failed: no bound is known for it
    bounded = world.ended_source("partial")  # the norms completed with one call
    full = world.flight.estimate_restart(world.session, run_id=unbounded, restart_point="norms", stage_plan=world.plan).as_dict()
    short = world.flight.estimate_restart(world.session, run_id=bounded, restart_point="norms", stage_plan=world.plan).as_dict()
    assert 0 < short["calls"] < full["calls"], "the chain made one norm call and one critic call; the estimate's own bound is far higher"


def test_the_consent_is_bound_to_this_source_and_this_chip(world) -> None:  # type: ignore[no-untyped-def]
    source, other = world.ended_source("partial"), world.ended_source("partial")
    shown = world.flight.estimate_restart(world.session, run_id=source, restart_point="norms", stage_plan=world.plan)
    wrong_chip = {"estimate_digest": world.flight.estimate_restart(world.session, run_id=source, restart_point="review", stage_plan=world.plan).estimate_digest,
                  "ceiling_micros": 0, "confirmed": True}
    for consent in (wrong_chip, {"estimate_digest": "0" * 64, "ceiling_micros": 0, "confirmed": True}):
        _refused(world, lambda consent=consent: restart_run(
            world.session, source_run_id=source, restart_point="norms", roles=EXPERT, user_uid=world.actor, idempotency_key=key(),
            provider_mode="recorded", section_profiles=world.registry.section_profiles(), cost_preflight=world.flight, cost_consent=consent,
            cost_actor_uid=world.actor, stage_plans=lambda _: world.plan), ErrorCode.ANALYSIS_INPUT_INVALID, reason="cost_estimate_binding_changed")
    # No consent at all is a validation failure, as for every served start.
    _refused(world, lambda: world.restart(source, "norms", consent=False), ErrorCode.VALIDATION_FAILED, field="cost_consent")
    assert shown.estimate_digest != world.flight.estimate_restart(world.session, run_id=other, restart_point="norms", stage_plan=world.plan).estimate_digest


def test_a_restart_names_a_point_of_the_eight_chips(world) -> None:  # type: ignore[no-untyped-def]
    source = world.ended_source("partial")
    _refused(world, lambda: world.restart(source, "stage", consent=False), ErrorCode.VALIDATION_FAILED, field="restart_point")


# -- the lineage ----------------------------------------------------------------------------------------------------------------------


def test_the_publication_of_a_restart_leaves_one_run_of_its_lineage_listed(world) -> None:  # type: ignore[no-untyped-def]
    """``tombstone_lineage`` is the executor's, called in the transaction that moved the new run to ``published`` or ``partial``: the direct source goes
    with the restart's own command (the guarded path), every other ended run of the lineage with a command record of its own."""
    root = world.ended_source("partial")
    cancelled = world.restart(root, "text")  # an earlier restart of the root that ended without a result
    world.runs.advance(world.session, run_id=cancelled.run_id, from_state="queued", to_state="running")
    for stage_id in ("source_preparation", "page_geometry_extraction", "document_context_build"):  # it took them by reference before it failed
        world.stage_row(cancelled.run_id, stage_id)
    world.runs.terminate(world.session, run_id=cancelled.run_id, from_state="running", to_state="failed", terminal_reason="analysis_failed",
                         degradation_set=("text_analysis",))
    failed_restart = world.restart(cancelled.run_id, "text")  # a restart of a failed restart: its source is that run
    assert world.runs.get(world.session, failed_restart.run_id).started_from_run_id == cancelled.run_id
    assert restart_chain(world.session, failed_restart.run_id) == [failed_restart.run_id, cancelled.run_id, root]
    # It publishes.
    world.runs.advance(world.session, run_id=failed_restart.run_id, from_state="queued", to_state="running")
    world.runs.advance(world.session, run_id=failed_restart.run_id, from_state="running", to_state="validating")
    world.runs.terminate(world.session, run_id=failed_restart.run_id, from_state="validating", to_state="partial", degradation_set=("text_analysis",))
    done = tombstone_lineage(world.session, run=world.runs.get(world.session, failed_restart.run_id), runs=world.runs)
    assert done == (cancelled.run_id, root), "the direct source first, then the rest of the lineage"
    listed = [row.run_id for row in world.runs.list_for_version(world.session, str(world.version))]
    assert listed == [failed_restart.run_id], "exactly one run of the lineage stays listed"
    for member in (cancelled.run_id, root):
        assert replaced_by(world.session, member) == failed_restart.run_id
    # The direct source's tombstone names the restart's command; the other's is a plain delete command whose outcome names the replacement.
    command_of = {row[0]: row[1] for row in world.session.execute(text("SELECT run_id, command_id FROM audit_run_deletion"))}
    assert command_of[cancelled.run_id] == failed_restart.command_id and command_of[root] != failed_restart.command_id
    assert world.session.execute(text("SELECT outcome FROM command_record WHERE command_id = :c"), {"c": command_of[root]}).scalar_one() == {
        "run_id": root, "replaced_by_run_id": failed_restart.run_id}
    # Idempotent: a second call writes nothing, and a plain deletion of an unrelated run replaces nothing.
    assert tombstone_lineage(world.session, run=world.runs.get(world.session, failed_restart.run_id), runs=world.runs) == ()
    stranger = world.ended_source("failed")
    delete_audit_run(world.session, run_id=stranger, roles=EXPERT, user_uid=world.actor, idempotency_key=key())
    assert replaced_by(world.session, stranger) is None
    # A restart that failed or has not ended replaces nothing, and the guard of the database is the last word.
    with pytest.raises(DomainError):
        tombstone_lineage(world.session, run=world.runs.get(world.session, cancelled.run_id), runs=world.runs)


def _hand_restart(world: World, source: str, point: str, state: str = "queued") -> str:
    """A restart run written directly (the command would refuse a second active restart of the lineage), with its own command record."""
    from auditmanager.ingest.public import CommandRepository, payload_fingerprint
    from auditmanager.shared.identity import IdempotencyKey, RunId

    ledger = CommandRepository()
    claimed = ledger.begin(world.session, command_type="restart_run", idempotency_key=IdempotencyKey(key()),
                           fingerprint=payload_fingerprint({"source": source, "point": point, "n": uuid4().hex}))
    old = world.runs.get(world.session, source)
    run_id = str(RunId.new())
    world.runs.create(
        world.session, run_id=run_id, project_uid=old.project_uid, version_uid=old.version_uid, analysis_profile_id=old.analysis_profile_id,
        prompt_bundle_id=old.prompt_bundle_id, provider_mode="recorded", frozen_input_digest=old.frozen_input_digest,
        command_id=str(claimed.command_id), started_from_run_id=source, restart_point=point, started_by_user_uid=world.actor)
    ledger.succeed(world.session, claimed.command_id, {"run_id": run_id})
    world.runs.advance(world.session, run_id=run_id, from_state="created", to_state="queued")
    if state in ("running", "validating", "partial", "published"):
        world.runs.advance(world.session, run_id=run_id, from_state="queued", to_state="running")
    if state in ("validating", "partial", "published"):
        world.runs.advance(world.session, run_id=run_id, from_state="running", to_state="validating")
    if state == "partial":
        world.runs.terminate(world.session, run_id=run_id, from_state="validating", to_state="partial", degradation_set=("text_analysis",))
    if state == "published":
        world.runs.terminate(world.session, run_id=run_id, from_state="validating", to_state="published")
    return run_id


def test_a_member_of_the_lineage_that_is_active_or_published_is_left_alone(world) -> None:  # type: ignore[no-untyped-def]
    root = world.ended_source("partial")
    failed = _hand_restart(world, root, "text")
    world.runs.advance(world.session, run_id=failed, from_state="queued", to_state="running")
    world.runs.terminate(world.session, run_id=failed, from_state="running", to_state="failed", terminal_reason="analysis_failed",
                         degradation_set=("text_analysis",))
    published = _hand_restart(world, root, "norms", "published")  # a sibling that published: its own tombstone of the root is not written here
    active = _hand_restart(world, root, "blocks", "running")  # a sibling that has not ended
    winner = _hand_restart(world, failed, "text", "partial")
    done = tombstone_lineage(world.session, run=world.runs.get(world.session, winner), runs=world.runs)
    assert done == (failed, root)
    assert {row.run_id for row in world.runs.list_for_version(world.session, str(world.version))} == {winner, active, published}
    assert lineage_of(world.session, winner) == lineage_of(world.session, root)
    assert replaced_by(world.session, failed) == winner and replaced_by(world.session, active) is None
    assert world.runs.is_deleted(world.session, root) and not world.runs.is_deleted(world.session, published)
