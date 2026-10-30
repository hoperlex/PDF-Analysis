"""Targeted PostgreSQL acceptance/replay; no provider or S3 writes."""
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.access.public import UserRepository
from auditmanager.analysis.public import ProviderConfig, ProviderMode
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.documents.public import DocumentRepository, ManifestEntry
from auditmanager.runs.commands import start_audit_run
from auditmanager.runs.cost_policy import read_run_cost_policy
from auditmanager.runs.preflight import RunCostPreflight
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role


@pytest.fixture
def world(session):
    """Only relational metadata is needed: these tests never request blob bytes."""
    documents = DocumentRepository()
    project = documents.create_project(session, "Cost preflight synthetic")
    document = documents.create_document(session, project_uid=project.project_uid, display_title="Cost", section="AI")
    payload = uuid4().bytes
    digest = sha256(payload).hexdigest()
    blob_id = derive_blob_id(sha256=digest, size=len(payload))
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(blob_id, "cost-test-only", digest, len(payload),
        parse_blob_role("source_document"), "application/pdf"))
    blobs.mark_available(session, blob_id)
    version = documents.publish_version(session, document_uid=document, media_type="application/pdf",
        byte_size=len(payload), sha256=digest, page_count=500, source_filename=None,
        entries=(ManifestEntry("source.document", blob_id, digest, len(payload), "application/pdf"),),
        text_character_count=20_000_000, recognised_character_count=0, textless_pages=())
    actor = UserRepository().create_user(session, "cost-"+uuid4().hex, "cost-test-password")
    documents.insert_classification(session, version_uid=version, project_stage="P", section_code="AI",
        confirmed_by_user_uid=str(actor.user_uid))
    registry = load_text_profile_registry()
    preflight = RunCostPreflight(section_profiles=registry.section_profiles(), text_profiles=registry.resolve,
        provider_config=ProviderConfig(ProviderMode.RECORDED, "claude-opus-5", 1., None, False), provider_mode="recorded")
    return version, registry, preflight, str(actor.user_uid)


def start(session, world, key, consent, *, relaxed=False):
    version, registry, preflight, actor = world
    return start_audit_run(session, version_uid=version, provider_mode="recorded", idempotency_key=key,
        section_profiles=registry.section_profiles(), text_profiles=registry.resolve,
        input_budget_characters=100, operational_model_id="claude-opus-5", norms_snapshot=lambda _: None,
        cost_preflight=preflight, cost_consent=consent, cost_actor_uid=actor, relaxed_limits=relaxed)


def counters(session):
    return tuple(session.execute(text("SELECT count(*) FROM "+table)).scalar_one()
                 for table in ("audit_run", "job", "command_record", "model_call"))


@pytest.mark.parametrize("relaxed", [False, True])
def test_large_start_requires_sufficient_consent_and_replays_accepted_cap(session, world, relaxed):
    version, _registry, preflight, actor = world
    value = preflight.estimate_run(session, version_uid=str(version), relaxed_limits=relaxed)
    estimate = value.as_dict()
    assert estimate["windows"] > 12
    before = counters(session)
    with pytest.raises(DomainError) as missing:
        start(session, world, "cost-missing", None, relaxed=relaxed)
    assert missing.value.code is ErrorCode.VALIDATION_FAILED
    assert counters(session) == before
    consent = {"estimate_digest": value.estimate_digest,
               "ceiling_micros": estimate["estimated_cost_micros"]-1, "confirmed": True}
    with pytest.raises(DomainError):
        start(session, world, "cost-low", consent, relaxed=relaxed)
    assert counters(session) == before
    consent["ceiling_micros"] = estimate["recommended_ceiling_micros"]
    first = start(session, world, "cost-accepted", consent, relaxed=relaxed)
    accepted_counts = counters(session)
    policy = read_run_cost_policy(session, run_id=first.run_id, default_ceiling_usd=1.)
    assert policy.approved and policy.enforce_ceiling
    assert policy.ceiling_usd == consent["ceiling_micros"] / 1_000_000
    assert policy.max_windows >= estimate["windows"]
    # A restart / changed operator price table cannot reprice accepted work.
    preflight.prices = lambda: ()
    replay = start(session, world, "cost-accepted", consent, relaxed=relaxed)
    assert replay.replayed and replay.run_id == first.run_id
    assert counters(session) == accepted_counts
    saved = session.execute(text("SELECT outcome FROM command_record WHERE command_id=(SELECT command_id FROM audit_run WHERE run_id=:r)"), {"r": first.run_id}).scalar_one()
    assert saved["cost_consent"]["approved_by_user_uid"] == actor
    assert saved["cost_consent"]["ceiling_micros"] == consent["ceiling_micros"]


def test_changed_classification_digest_refuses_before_any_run_or_call(session, world):
    version, _registry, preflight, _actor = world
    value = preflight.estimate_run(session, version_uid=str(version))
    consent = {"estimate_digest": "f"*64, "ceiling_micros": value.as_dict()["recommended_ceiling_micros"], "confirmed": True}
    before = counters(session)
    with pytest.raises(DomainError) as error:
        start(session, world, "cost-stale", consent)
    assert error.value.code is ErrorCode.CONFLICT
    assert counters(session) == before


def test_reaudit_demands_new_source_bound_consent_and_replays_it(session, world):
    from auditmanager.runs.commands import reaudit_run
    from auditmanager.runs.repository import RunRepository
    version, registry, preflight, actor = world
    old = preflight.estimate_run(session, version_uid=str(version))
    old_consent = {"estimate_digest": old.estimate_digest,
        "ceiling_micros": old.as_dict()["recommended_ceiling_micros"], "confirmed": True}
    source = start(session, world, "cost-source", old_consent)
    runs = RunRepository()
    runs.advance(session, run_id=source.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=source.run_id, from_state="queued", to_state="running")
    runs.terminate(session, run_id=source.run_id, from_state="running", to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value)
    fresh = preflight.estimate_reaudit(session, run_id=source.run_id)
    assert fresh.estimate_digest != old.estimate_digest
    before = counters(session)
    kwargs = dict(source_run_id=source.run_id, roles=frozenset({"expert"}), provider_mode="recorded",
        section_profiles=registry.section_profiles(), input_budget_characters=100,
        norms_snapshot=lambda _: None, cost_preflight=preflight, cost_actor_uid=actor)
    for consent in [None, old_consent]:
        with pytest.raises(DomainError):
            reaudit_run(session, idempotency_key="cost-reaudit-refuse", cost_consent=consent, **kwargs)
        assert counters(session) == before
    consent = {"estimate_digest": fresh.estimate_digest,
        "ceiling_micros": fresh.as_dict()["recommended_ceiling_micros"], "confirmed": True}
    new = reaudit_run(session, idempotency_key="cost-reaudit-ok", cost_consent=consent, **kwargs)
    assert runs.get(session, new.run_id).reaudit_of_run_id == source.run_id
    assert runs.get(session, new.run_id).state == "queued"
    policy = read_run_cost_policy(session, run_id=new.run_id, default_ceiling_usd=1.)
    assert policy.approved and policy.ceiling_usd == consent["ceiling_micros"]/1_000_000
    accepted = counters(session)
    preflight.prices = lambda: ()
    replay = reaudit_run(session, idempotency_key="cost-reaudit-ok", cost_consent=consent, **kwargs)
    assert replay.replayed and replay.run_id == new.run_id
    assert counters(session) == accepted
