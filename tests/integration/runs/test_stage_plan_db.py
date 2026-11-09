"""`HOSTS-LAYOUT-01` on real PostgreSQL (migration ``0062``): the layout store's numbering and journal, and a run frozen with a stage plan.

One rolled-back transaction per test, no object store, no model. Written and **not run** by the lane (the HOSTS plan allows no database in
the lanes; the slot holder runs it on a throwaway database). Each case would pass at head ``0062_hosts_stage_models``:

* the revisions are numbered 1, 2, 3 and returned newest first; the switch in force is the latest event, and the database refuses a
  switch-on while the layout has no revision;
* a start with the layout on writes the run ``pending`` with its plan, no connection, group or preset (the fourth shape of
  ``ck_audit_run_binding_shape``); the plan reads back equal; the command outcome holds the consent v2 that ``read_run_cost_policy`` reads;
* ``stage_plan`` is a frozen column of the run;
* a planned run with no consent is refused by the policy reader, and a bound-state read finds no cell binding yet.
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
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.commands import start_audit_run
from auditmanager.runs.cost_policy import read_run_cost_policy
from auditmanager.runs.preflight import RunCostPreflight
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.stage_layout_store import SqlStageLayoutStore
from auditmanager.runs.stage_plan import ModelAvailability, StagePlanDraft
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role

ACTOR = f"usr_{'0' * 26}"
SUBSCRIPTION = ModelAvailability(subscription=True, api=True)


def key() -> str:
    return f"plan-{uuid4().hex}"


@pytest.fixture
def world(session):  # type: ignore[no-untyped-def]
    documents = DocumentRepository()
    project = documents.create_project(session, "Stage plan synthetic")
    document = documents.create_document(session, project_uid=project.project_uid, display_title="Plan", section="AI")
    payload = uuid4().bytes
    digest = sha256(payload).hexdigest()
    blob_id = derive_blob_id(sha256=digest, size=len(payload))
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(blob_id, "plan-test-only", digest, len(payload),
        parse_blob_role("source_document"), "application/pdf"))
    blobs.mark_available(session, blob_id)
    version = documents.publish_version(session, document_uid=document, media_type="application/pdf",
        byte_size=len(payload), sha256=digest, page_count=2, source_filename=None,
        entries=(ManifestEntry("source.document", blob_id, digest, len(payload), "application/pdf"),),
        text_character_count=2_000, recognised_character_count=0, textless_pages=())
    actor = UserRepository().create_user(session, "plan-" + uuid4().hex, "plan-test-password")
    documents.insert_classification(session, version_uid=version, project_stage="P", section_code="AI",
        confirmed_by_user_uid=str(actor.user_uid))
    registry = load_text_profile_registry()
    return {"version": version, "registry": registry, "actor": str(actor.user_uid)}


def draft() -> StagePlanDraft:
    cells = layout.preset_cells("claude_only")
    return StagePlanDraft("slr_01M2545JSD15ETSNNV904X991J", "claude_only", cells, {c.model_id: SUBSCRIPTION for c in cells})


def planned_start(session, world, **options):  # type: ignore[no-untyped-def]
    registry = world["registry"]
    flight = RunCostPreflight(
        section_profiles=registry.section_profiles(), text_profiles=registry.resolve,
        provider_config=ProviderConfig(ProviderMode.RECORDED, "claude-sonnet-5-5", 1.0, None, False), provider_mode="recorded")
    plan = draft()
    shown = flight.estimate_run(session, version_uid=str(world["version"]), stage_plan=plan)
    consent = {"estimate_digest": shown.estimate_digest, "ceiling_micros": 0, "confirmed": True}
    return start_audit_run(
        session, version_uid=world["version"], provider_mode="recorded", idempotency_key=key(),
        section_profiles=registry.section_profiles(), text_profiles=registry.resolve, input_budget_characters=100,
        operational_model_id="claude-sonnet-5-5", norms_snapshot=lambda _: None, cost_preflight=flight, cost_consent=consent,
        cost_actor_uid=world["actor"], stage_plans=lambda _: plan, **options), shown


# --- the store ------------------------------------------------------------------------------------------------------------------


def test_the_revisions_are_numbered_and_the_switch_in_force_is_the_latest_event(session) -> None:  # type: ignore[no-untyped-def]
    store = SqlStageLayoutStore()
    user = str(UserRepository().create_user(session, "layout-" + uuid4().hex, "layout-test-password").user_uid)
    assert store.current_revision(session) is None and store.enabled(session) is False
    first = store.append_revision(session, kit="claude_only", cells=layout.preset_cells("claude_only"), created_by=user)
    second = store.append_revision(session, kit="codex_only", cells=layout.preset_cells("codex_only"), created_by=user)
    assert (first.revision_no, second.revision_no) == (1, 2)
    assert [r.revision_no for r in store.history(session, limit=10)] == [2, 1] and store.current_revision(session).kit == "codex_only"
    assert [c.cell_key for c in store.current_revision(session).cells] == [f"{row}:main" for row in layout.STAGE_ROWS]
    store.append_switch(session, enabled=True, set_by=user)
    assert store.enabled(session) is True
    store.append_switch(session, enabled=False, set_by=user)
    assert store.enabled(session) is False and [e.enabled for e in store.switch_journal(session, limit=10)] == [False, True]


def test_the_database_refuses_a_switch_on_while_the_layout_has_no_revision(session) -> None:  # type: ignore[no-untyped-def]
    user = str(UserRepository().create_user(session, "layout-" + uuid4().hex, "layout-test-password").user_uid)
    with pytest.raises(DBAPIError):
        SqlStageLayoutStore().append_switch(session, enabled=True, set_by=user)


# --- a run frozen with a plan ---------------------------------------------------------------------------------------------------


def test_a_start_with_the_layout_on_writes_a_pending_run_with_its_plan_and_no_executor(session, world) -> None:  # type: ignore[no-untyped-def]
    started, shown = planned_start(session, world)
    row = dict(session.execute(text(
        "SELECT binding_state, executor_group_revision_id, routing_rule_revision_id, connection_revision_id, preset_revision_id, "
        "stage_plan FROM audit_run WHERE run_id = :r"), {"r": started.run_id}).mappings().one())
    assert row["binding_state"] == "pending" and row["stage_plan"] is not None
    assert row["executor_group_revision_id"] is None and row["connection_revision_id"] is None and row["preset_revision_id"] is None
    assert layout.parse_plan(row["stage_plan"]) == shown.stage_plan
    run = RunRepository().get(session, started.run_id)
    assert layout.parse_plan(run.stage_plan).digest == shown.stage_plan.digest
    assert RunRepository().cell_bindings(session, started.run_id) == {}, "nothing is bound before dispatch"
    event = session.execute(text(
        "SELECT payload FROM audit_event WHERE aggregate_id = :r AND event_type = 'audit_run.stage_plan_frozen'"),
        {"r": started.run_id}).scalar_one()
    assert event["revision_id"] == "slr_01M2545JSD15ETSNNV904X991J" and event["state"] == "pending"


def test_the_consent_v2_of_a_planned_run_is_read_back_by_the_cost_authority(session, world) -> None:  # type: ignore[no-untyped-def]
    started, shown = planned_start(session, world)
    policy = read_run_cost_policy(session, run_id=started.run_id, default_ceiling_usd=1.0)
    assert policy.approved and policy.stage_plan_digest == shown.stage_plan.digest and policy.models is not None
    assert set(policy.models) == set(shown.stage_plan.models) and policy.connection_revision_id is None
    assert policy.enforce_ceiling is False, "every cell is on a subscription: nothing is charged"


def test_the_plan_of_a_run_is_frozen(session, world) -> None:  # type: ignore[no-untyped-def]
    started, _ = planned_start(session, world)
    with pytest.raises(DBAPIError):
        session.execute(text("UPDATE audit_run SET stage_plan = NULL WHERE run_id = :r"), {"r": started.run_id})
