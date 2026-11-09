"""`R-151i`: the price and the consent of a start from a stage are those of the stages it computes, and are bound to the source and the stage.

Targeted PostgreSQL acceptance and replay, as ``test_cost_preflight.py``: the source's stage rows are written directly (with real, available
blob rows) so that no provider call and no S3 write is needed.
"""
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.access.public import UserRepository
from auditmanager.analysis.public import ProviderConfig, ProviderMode, default_registry
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.documents.public import DocumentRepository, ManifestEntry
from auditmanager.runs.commands import start_audit_run, start_run_from_stage
from auditmanager.runs.cost_policy import read_run_cost_policy
from auditmanager.runs.preflight import RunCostPreflight
from auditmanager.runs.repository import PC01_STAGES, RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role


@pytest.fixture
def world(session):
    documents = DocumentRepository()
    project = documents.create_project(session, "Start from a stage synthetic")
    document = documents.create_document(session, project_uid=project.project_uid, display_title="Stage", section="AI")
    payload = uuid4().bytes
    digest = sha256(payload).hexdigest()
    blob_id = derive_blob_id(sha256=digest, size=len(payload))
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(blob_id, "stage-test-only", digest, len(payload),
        parse_blob_role("source_document"), "application/pdf"))
    blobs.mark_available(session, blob_id)
    version = documents.publish_version(session, document_uid=document, media_type="application/pdf",
        byte_size=len(payload), sha256=digest, page_count=500, source_filename=None,
        entries=(ManifestEntry("source.document", blob_id, digest, len(payload), "application/pdf"),),
        text_character_count=20_000_000, recognised_character_count=0, textless_pages=())
    actor = UserRepository().create_user(session, "stage-" + uuid4().hex, "stage-test-password")
    documents.insert_classification(session, version_uid=version, project_stage="P", section_code="AI",
        confirmed_by_user_uid=str(actor.user_uid))
    registry = load_text_profile_registry()
    preflight = RunCostPreflight(section_profiles=registry.section_profiles(), text_profiles=registry.resolve,
        provider_config=ProviderConfig(ProviderMode.RECORDED, "claude-opus-5", 1., None, False), provider_mode="recorded")
    return version, registry, preflight, str(actor.user_uid)


def _consent(value):
    return {"estimate_digest": value.estimate_digest,
            "ceiling_micros": value.as_dict()["recommended_ceiling_micros"], "confirmed": True}


@pytest.fixture
def source(session, world):
    """A terminal run whose first three stages succeeded, each with its registry's required outputs as available blobs."""
    version, registry, preflight, actor = world
    old = preflight.estimate_run(session, version_uid=str(version))
    started = start_audit_run(session, version_uid=version, provider_mode="recorded", idempotency_key="stage-cost-source",
        section_profiles=registry.section_profiles(), text_profiles=registry.resolve, input_budget_characters=100,
        operational_model_id="claude-opus-5", norms_snapshot=lambda _: None, cost_preflight=preflight,
        cost_consent=_consent(old), cost_actor_uid=actor)
    runs, blobs = RunRepository(), BlobMetadataRepository()
    for stage_id in PC01_STAGES[:3]:
        definition = default_registry().stage(stage_id)
        artifacts = []
        for role in definition.required_output_roles:
            payload = uuid4().bytes
            digest = sha256(payload).hexdigest()
            blob_id = derive_blob_id(sha256=digest, size=len(payload))
            blobs.record_verified(session, VerifiedBlob(blob_id, "stage-test-only", digest, len(payload),
                parse_blob_role("source_document"), "application/json"))
            blobs.mark_available(session, blob_id)
            artifacts.append({"role": role, "blob_id": str(blob_id), "sha256": digest, "size_bytes": len(payload),
                              "media_type": "application/json"})
        runs.record_stage_result(session, run_id=started.run_id, document={
            "stage_id": stage_id, "stage_version": definition.stage_version, "status": "succeeded",
            "artifacts": artifacts, "metrics": {"pages": 500}})
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    runs.terminate(session, run_id=started.run_id, from_state="running", to_state="failed",
                   terminal_reason=ErrorCode.ANALYSIS_FAILED.value)
    return started.run_id


def counters(session):
    return tuple(session.execute(text("SELECT count(*) FROM " + table)).scalar_one()
                 for table in ("audit_run", "job", "command_record", "model_call"))


def _start(session, world, source_run_id, stage_id, key, consent):
    _version, registry, preflight, actor = world
    return start_run_from_stage(
        session, source_run_id=source_run_id, start_stage_id=stage_id, roles=frozenset({"expert"}), provider_mode="recorded",
        idempotency_key=key, section_profiles=registry.section_profiles(), input_budget_characters=100,
        norms_snapshot=lambda _: None, cost_preflight=preflight, cost_consent=consent, cost_actor_uid=actor)


def test_the_estimate_names_the_stages_it_takes_and_the_stages_it_prices(session, world, source):
    _version, _registry, preflight, _actor = world
    value = preflight.estimate_from_stage(session, run_id=source, start_stage_id="text_analysis").as_dict()
    assert (value["start_from_run_id"], value["start_stage_id"]) == (source, "text_analysis")
    assert value["reused_stage_ids"] == list(PC01_STAGES[:3]) and value["computed_stage_ids"] == ["text_analysis"]
    middle = preflight.estimate_from_stage(session, run_id=source, start_stage_id="document_context_build").as_dict()
    assert middle["reused_stage_ids"] == list(PC01_STAGES[:2])
    assert middle["computed_stage_ids"] == list(PC01_STAGES[2:])
    # All model calls are text_analysis's, so the priced work is the same; the digests differ because the consent is bound.
    assert middle["estimated_cost_micros"] == value["estimated_cost_micros"]
    assert middle["estimate_digest"] != value["estimate_digest"]


def test_a_stage_that_cannot_be_taken_is_refused_by_the_estimate_before_any_consent(session, world, source):
    _version, _registry, preflight, _actor = world
    session.execute(text("UPDATE stage_result SET stage_version = '0.9.0' WHERE run_id = :r AND stage_id = 'document_context_build'"),
                    {"r": source})
    with pytest.raises(DomainError) as refusal:
        preflight.estimate_from_stage(session, run_id=source, start_stage_id="text_analysis")
    assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refusal.value.detail_fields["stage_id"] == "document_context_build"
    # ... and a start from the stage before it is not affected.
    assert preflight.estimate_from_stage(session, run_id=source, start_stage_id="document_context_build").as_dict()


def test_a_start_needs_a_consent_bound_to_this_source_and_stage_and_replays_it(session, world, source):
    _version, _registry, preflight, actor = world
    fresh = preflight.estimate_from_stage(session, run_id=source, start_stage_id="text_analysis")
    reaudit_estimate = preflight.estimate_reaudit(session, run_id=source)
    other_stage = preflight.estimate_from_stage(session, run_id=source, start_stage_id="document_context_build")
    assert len({fresh.estimate_digest, reaudit_estimate.estimate_digest, other_stage.estimate_digest}) == 3
    before = counters(session)
    for wrong in (None, _consent(reaudit_estimate), _consent(other_stage)):
        with pytest.raises(DomainError):
            _start(session, world, source, "text_analysis", "stage-cost-refused", wrong)
        assert counters(session) == before
    consent = _consent(fresh)
    new = _start(session, world, source, "text_analysis", "stage-cost-ok", consent)
    runs = RunRepository()
    run = runs.get(session, new.run_id)
    assert (run.started_from_run_id, run.start_stage_id, run.reaudit_of_run_id, run.state) == (source, "text_analysis", None, "queued")
    policy = read_run_cost_policy(session, run_id=new.run_id, default_ceiling_usd=1.)
    assert policy.approved and policy.ceiling_usd == consent["ceiling_micros"] / 1_000_000
    saved = session.execute(text("SELECT outcome FROM command_record WHERE command_id=(SELECT command_id FROM audit_run WHERE run_id=:r)"),
                            {"r": new.run_id}).scalar_one()
    assert saved["cost_consent"]["approved_by_user_uid"] == actor
    assert (saved["started_from_run_id"], saved["start_stage_id"]) == (source, "text_analysis")
    accepted = counters(session)
    preflight.prices = lambda: ()
    replay = _start(session, world, source, "text_analysis", "stage-cost-ok", consent)
    assert replay.replayed and replay.run_id == new.run_id
    assert counters(session) == accepted
