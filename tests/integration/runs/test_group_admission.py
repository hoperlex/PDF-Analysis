"""`EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12 and 13) on real PostgreSQL -- a Run is admitted on a group or by a rule, and not given a
connection.

One rolled-back transaction per test, no object store, no model: the version is relational metadata only (as in
``test_cost_preflight.py``) and the members are ``pull`` connections made by the executors context's own commands. Written and **not
run** in EXEC-2 (`R-149d`, D-292); each would pass against PostgreSQL at head ``0048``. B3 section 11 is not in the repository, so the
numbers are the task file's reading of it (the integrator re-maps them):

* **3 -- admission freezes intent, not an executor.** The Run row is ``pending`` with the group revision, no connection revision,
  no preset; the estimate carries the group and the planned pin and **no** connection and its digest binds them; the consent snapshot
  stays in the command outcome and names the group revision; the budget follows the group revision's pin; one admission event;
* a **named group** is admitted on its **current** revision, a start routed by a **rule** (mode ``rules``) on the revision the rule
  names and with the rule revision recorded; mode ``legacy`` with no selector, and an explicit connection in either mode, are
  ``frozen_at_start`` exactly as before;
* **the refusals leave nothing behind** -- no Run, no command record, no event: a group with a connection, an unknown group, an
  archived group, the ``environment`` source, a work kind with no rule;
* **20 -- a re-audit keeps the kind of selector the original start used.**
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.access.public import UserRepository
from auditmanager.analysis.public import ProviderConfig, ProviderMode
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.bootstrap.providers import GroupAdmission
from auditmanager.documents.public import DocumentRepository, ManifestEntry
from auditmanager.executors.public import (
    GroupSettings,
    MemberRequest,
    RevisionSettings,
    archive_group,
    create_connection,
    create_group,
    pinned_models,
    revise_connection,
    revise_group,
    set_routing_rule,
)
from auditmanager.runs.commands import reaudit_run, start_audit_run
from auditmanager.runs.cost_policy import read_run_cost_policy
from auditmanager.runs.preflight import RunCostPreflight
from auditmanager.runs.provider import FrozenRoute
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorRoutingModeEventId
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role

ACTOR = f"usr_{'0' * 26}"
ROLES = frozenset({"admin"})
PINS = pinned_models()
PIN_IDS = {pin.model_id for pin in PINS}
PULL = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", allow_client_documents=False,
    timeout_seconds=600, pull_client="claude_code_session", answer_deadline_seconds=600, max_claimed_tasks=1,
    max_active_runs=1,
)
SETTINGS = GroupSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", strategy="least_loaded")


def key() -> str:
    return f"adm-{uuid4().hex}"


# --- the world -----------------------------------------------------------------------------------------------------------------


@pytest.fixture
def world(session):  # type: ignore[no-untyped-def]
    """A classified version of a few thousand characters, and a preflight that can admit on a group."""
    documents = DocumentRepository()
    project = documents.create_project(session, "Group admission synthetic")
    document = documents.create_document(session, project_uid=project.project_uid, display_title="Group", section="AI")
    payload = uuid4().bytes
    digest = sha256(payload).hexdigest()
    blob_id = derive_blob_id(sha256=digest, size=len(payload))
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(blob_id, "group-test-only", digest, len(payload),
        parse_blob_role("source_document"), "application/pdf"))
    blobs.mark_available(session, blob_id)
    version = documents.publish_version(session, document_uid=document, media_type="application/pdf",
        byte_size=len(payload), sha256=digest, page_count=2, source_filename=None,
        entries=(ManifestEntry("source.document", blob_id, digest, len(payload), "application/pdf"),),
        text_character_count=2_000, recognised_character_count=0, textless_pages=())
    actor = UserRepository().create_user(session, "group-" + uuid4().hex, "group-test-password")
    documents.insert_classification(session, version_uid=version, project_stage="P", section_code="AI",
        confirmed_by_user_uid=str(actor.user_uid))
    registry = load_text_profile_registry()
    admitter = GroupAdmission(ceiling_usd=1.0)

    def preflight(**options: Any) -> RunCostPreflight:
        return RunCostPreflight(
            section_profiles=registry.section_profiles(), text_profiles=registry.resolve,
            provider_config=ProviderConfig(ProviderMode.RECORDED, "claude-opus-5", 1., None, False),
            provider_mode="recorded", **{"group_admitter": admitter, **options})

    return {"version": version, "registry": registry, "actor": str(actor.user_uid), "admitter": admitter,
            "preflight": preflight()}, preflight


def pull_member(session, name: str = "member") -> tuple[str, str]:  # type: ignore[no-untyped-def]
    connection_id = create_connection(
        session, kind="pull", display_name=f"{name}-{uuid4().hex[:8]}", roles=ROLES, idempotency_key=key(),
        actor_uid=ACTOR).connection_id
    revision_id = revise_connection(
        session, connection_id=connection_id, settings=PULL, pinned_model_ids=PIN_IDS, roles=ROLES,
        idempotency_key=key(), actor_uid=ACTOR).revision_id
    return connection_id, revision_id


def make_group(session, *members: tuple[str, str]):  # type: ignore[no-untyped-def]
    return create_group(
        session, display_name=f"Pool {uuid4().hex[:8]}", settings=SETTINGS,
        members=[MemberRequest(connection_id, revision_id, None) for connection_id, revision_id in members], pins=PINS,
        roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)


def rules_mode(session) -> None:  # type: ignore[no-untyped-def]
    session.execute(text(
        "INSERT INTO executor_routing_mode_event (mode_event_id, event_no, mode, preview_digest, mapping, changed_by) "
        "VALUES (:id, (SELECT coalesce(max(event_no), 0) + 1 FROM executor_routing_mode_event), 'rules', :digest, "
        "CAST(:mapping AS jsonb), :actor)"),
        {"id": str(ExecutorRoutingModeEventId.new()), "digest": "a" * 64,
         "mapping": json.dumps([{"work_kind": "text_analysis"}]), "actor": ACTOR})


def rule(session, group_revision_id: str):  # type: ignore[no-untyped-def]
    return set_routing_rule(
        session, work_kind="text_analysis", group_revision_id=group_revision_id, roles=ROLES, idempotency_key=key(),
        actor_uid=ACTOR)


def consent_for(value: Any) -> dict[str, Any]:
    return {"estimate_digest": value.estimate_digest,
            "ceiling_micros": value.as_dict()["recommended_ceiling_micros"], "confirmed": True}


def start(session, world, preflight=None, *, idempotency_key: str | None = None, **named: Any):  # type: ignore[no-untyped-def]
    """The start the served application makes: priced against a fresh estimate of the same selector."""
    shown, _ = world
    flight = preflight or shown["preflight"]
    estimate = flight.estimate_run(
        session, version_uid=str(shown["version"]),
        **{name: value for name, value in named.items() if name in {"executor_group_id", "executor_connection_id"}})
    return start_audit_run(
        session, version_uid=shown["version"], provider_mode="recorded", idempotency_key=idempotency_key or key(),
        section_profiles=shown["registry"].section_profiles(), text_profiles=shown["registry"].resolve,
        input_budget_characters=100, operational_model_id="claude-opus-5", norms_snapshot=lambda _: None,
        cost_preflight=flight, cost_consent=consent_for(estimate), cost_actor_uid=shown["actor"],
        group_admitter=shown["admitter"], **named)


def run_row(session, run_id: str) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return dict(session.execute(text(
        "SELECT state, binding_state, executor_group_revision_id, routing_rule_revision_id, connection_revision_id, "
        "preset_revision_id, wait_reason FROM audit_run WHERE run_id = :r"), {"r": run_id}).mappings().one())


def counters(session) -> tuple[int, ...]:  # type: ignore[no-untyped-def]
    return tuple(session.execute(text("SELECT count(*) FROM " + table)).scalar_one()
                 for table in ("audit_run", "job", "command_record", "audit_event"))


def outcome(session, run_id: str) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return dict(session.execute(text(
        "SELECT outcome FROM command_record WHERE command_id = (SELECT command_id FROM audit_run WHERE run_id = :r)"),
        {"r": run_id}).scalar_one())


# --- 3: admission freezes intent, not an executor -----------------------------------------------------------------------------


def test_the_estimate_of_a_group_carries_the_group_and_the_pin_and_no_connection_and_binds_them(session, world) -> None:  # type: ignore[no-untyped-def]
    shown, _ = world
    created = make_group(session, pull_member(session), pull_member(session))
    group_id, revision = created.group.group_id, created.current_revision
    plain = shown["preflight"].estimate_run(session, version_uid=str(shown["version"]))
    grouped = shown["preflight"].estimate_run(session, version_uid=str(shown["version"]), executor_group_id=group_id)
    estimate = grouped.as_dict()
    assert estimate["executor_group_id"] == group_id and estimate["executor_group_revision_id"] == revision.group_revision_id
    assert estimate["pin_id"] == "claude-sonnet-5" and estimate["model_id"] == "claude-sonnet-5"
    assert estimate["billing"] == "unmetered"
    assert "connection_revision_id" not in estimate and "routing_rule_revision_id" not in estimate
    assert grouped.estimate_digest != plain.estimate_digest, "the digest binds the group"
    assert grouped.admitted_group is not None and grouped.admitted_group.group_revision_id == revision.group_revision_id
    revised = revise_group(
        session, group_id=group_id, settings=SETTINGS, members=[MemberRequest(m.connection_id, m.connection_revision_id) for m in revision.members],
        pins=PINS, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
    again = shown["preflight"].estimate_run(session, version_uid=str(shown["version"]), executor_group_id=group_id)
    assert again.estimate_digest != grouped.estimate_digest, "a new revision of the group is a new estimate"
    assert again.as_dict()["executor_group_revision_id"] == revised.current_revision.group_revision_id


def test_a_start_that_names_a_group_admits_the_run_pending_with_no_connection_and_keeps_the_consent_snapshot(
    session, world,
) -> None:  # type: ignore[no-untyped-def]
    created = make_group(session, pull_member(session), pull_member(session))
    started = start(session, world, executor_group_id=created.group.group_id)
    row = run_row(session, started.run_id)
    assert row == {
        "state": "created", "binding_state": "pending",
        "executor_group_revision_id": created.current_revision.group_revision_id, "routing_rule_revision_id": None,
        "connection_revision_id": None, "preset_revision_id": None, "wait_reason": None}
    snapshot = outcome(session, started.run_id)["cost_consent"]
    assert snapshot["executor_group_revision_id"] == created.current_revision.group_revision_id
    assert snapshot["connection_revision_id"] is None and snapshot["model_id"] == "claude-sonnet-5"
    assert snapshot["billing"] == "unmetered" and "routing_rule_revision_id" not in snapshot
    policy = read_run_cost_policy(session, run_id=started.run_id, default_ceiling_usd=1.0)
    assert policy.approved and policy.executor_group_revision_id == created.current_revision.group_revision_id
    assert policy.connection_revision_id is None, "pending, not environment"
    (event,) = session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'audit_run.group_admitted' AND aggregate_id = :r"),
        {"r": started.run_id}).scalars().all()
    assert dict(event) == {"run_id": started.run_id, "work_kind": "text_analysis", "state": "pending", "reason": "group"}


def test_the_consent_follows_the_binding_the_database_allows_once(session, world) -> None:  # type: ignore[no-untyped-def]
    one, two = pull_member(session), pull_member(session)
    created = make_group(session, one, two)
    started = start(session, world, executor_group_id=created.group.group_id)
    session.execute(text(
        "UPDATE audit_run SET connection_revision_id = :c, binding_state = 'bound' WHERE run_id = :r"),
        {"c": two[1], "r": started.run_id})
    policy = read_run_cost_policy(session, run_id=started.run_id, default_ceiling_usd=1.0)
    assert (policy.executor_group_revision_id, policy.connection_revision_id) == (
        created.current_revision.group_revision_id, two[1]), "the bound member, from the row"
    with pytest.raises(Exception):
        with session.begin_nested():
            session.execute(text("UPDATE audit_run SET connection_revision_id = :c WHERE run_id = :r"),
                            {"c": one[1], "r": started.run_id})


# --- the selectors and the mode ------------------------------------------------------------------------------------------------


def test_with_the_mode_rules_a_start_that_names_nothing_is_admitted_on_the_revision_the_rule_names(session, world) -> None:  # type: ignore[no-untyped-def]
    created = make_group(session, pull_member(session))
    ruled = rule(session, created.current_revision.group_revision_id)
    rules_mode(session)
    revised = revise_group(
        session, group_id=created.group.group_id, settings=SETTINGS,
        members=[MemberRequest(m.connection_id, m.connection_revision_id) for m in created.current_revision.members],
        pins=PINS, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
    by_rule = start(session, world)
    by_name = start(session, world, executor_group_id=created.group.group_id)
    ruled_row, named_row = run_row(session, by_rule.run_id), run_row(session, by_name.run_id)
    assert ruled_row["binding_state"] == "pending" and ruled_row["connection_revision_id"] is None
    assert ruled_row["executor_group_revision_id"] == created.current_revision.group_revision_id, (
        "the immutable revision the rule names, not the group's newer one")
    assert ruled_row["routing_rule_revision_id"] == ruled.rule_revision_id
    assert named_row["executor_group_revision_id"] == revised.current_revision.group_revision_id, "a named group: its current one"
    assert named_row["routing_rule_revision_id"] is None
    assert outcome(session, by_rule.run_id)["cost_consent"]["routing_rule_revision_id"] == ruled.rule_revision_id


def test_with_the_mode_legacy_a_start_that_names_nothing_is_what_it_always_was(session, world) -> None:  # type: ignore[no-untyped-def]
    created = make_group(session, pull_member(session))
    rule(session, created.current_revision.group_revision_id)           # a rule exists; nothing reads it in legacy
    started = start(session, world)
    row = run_row(session, started.run_id)
    assert (row["binding_state"], row["executor_group_revision_id"], row["routing_rule_revision_id"]) == (
        "frozen_at_start", None, None)
    assert "executor_group_revision_id" not in outcome(session, started.run_id)["cost_consent"]


def test_an_explicit_connection_stays_frozen_at_start_in_either_mode(session, world) -> None:  # type: ignore[no-untyped-def]
    shown, make_preflight = world
    connection_id, revision_id = pull_member(session)
    made = make_group(session, (connection_id, revision_id))
    rule(session, made.current_revision.group_revision_id)
    rules_mode(session)

    def freezer(sess: Any, *, connection_id: str | None = None) -> FrozenRoute:
        assert connection_id is not None, "an explicit connection: the route is not read"
        return FrozenRoute(revision_id=revision_id, input_budget_characters=10**9, model_id="claude-sonnet-5",
                           chosen_connection_id=connection_id, billing="unmetered")

    flight = make_preflight(connection_route=freezer)
    started = start_audit_run(
        session, version_uid=shown["version"], provider_mode="recorded", idempotency_key=key(),
        section_profiles=shown["registry"].section_profiles(), text_profiles=shown["registry"].resolve,
        input_budget_characters=100, operational_model_id="claude-opus-5", norms_snapshot=lambda _: None,
        cost_preflight=flight,
        cost_consent=consent_for(flight.estimate_run(session, version_uid=str(shown["version"]),
                                                      executor_connection_id=connection_id)),
        cost_actor_uid=shown["actor"], executor_connection_id=connection_id, connection_route=freezer,
        group_admitter=shown["admitter"])
    row = run_row(session, started.run_id)
    assert (row["binding_state"], row["connection_revision_id"], row["executor_group_revision_id"]) == (
        "frozen_at_start", revision_id, None)


# --- the refusals leave nothing behind ----------------------------------------------------------------------------------------


def _refused(session, world, expected: ErrorCode, details: dict[str, Any], **named: Any) -> None:  # type: ignore[no-untyped-def]
    before = counters(session)
    with pytest.raises(DomainError) as caught:
        with session.begin_nested():
            start(session, world, **named)
    assert caught.value.code is expected and dict(caught.value.detail_fields) == details
    assert counters(session) == before, "no Run, no Job, no command record and no event"


def test_a_group_together_with_a_connection_is_refused(session, world) -> None:  # type: ignore[no-untyped-def]
    created = make_group(session, pull_member(session))
    shown, _ = world
    before = counters(session)
    with pytest.raises(DomainError) as caught:
        shown["preflight"].estimate_run(
            session, version_uid=str(shown["version"]), executor_group_id=created.group.group_id,
            executor_connection_id="exc_01M2545JSD15ETSNNV904X991N")
    assert dict(caught.value.detail_fields) == {
        "field": "executor_group_id", "constraint": "conflicts_with_executor_connection_id"}
    assert counters(session) == before


def test_an_unknown_group_is_validation_failed_on_the_field(session, world) -> None:  # type: ignore[no-untyped-def]
    _refused(session, world, ErrorCode.VALIDATION_FAILED,
             {"field": "executor_group_id", "constraint": "unknown_executor_group"},
             executor_group_id="exg_01M2545JSD15ETSNNV904X999G")


def test_an_archived_group_is_a_conflict_with_its_reason(session, world) -> None:  # type: ignore[no-untyped-def]
    created = make_group(session, pull_member(session))
    archive_group(session, group_id=created.group.group_id, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
    _refused(session, world, ErrorCode.CONFLICT, {"conflict_reason": "group_archived"},
             executor_group_id=created.group.group_id)


def test_with_the_mode_rules_and_no_rule_the_start_is_refused_not_run_on_the_route(session, world) -> None:  # type: ignore[no-untyped-def]
    rules_mode(session)
    _refused(session, world, ErrorCode.DEPENDENCY_UNAVAILABLE, {"dependency": "no_rule_for_work_kind"})


def test_the_environment_source_has_no_admitter_and_refuses_a_group(session, world) -> None:  # type: ignore[no-untyped-def]
    shown, make_preflight = world
    created = make_group(session, pull_member(session))
    before = counters(session)
    with pytest.raises(DomainError) as caught:
        make_preflight(group_admitter=None).estimate_run(
            session, version_uid=str(shown["version"]), executor_group_id=created.group.group_id)
    assert dict(caught.value.detail_fields) == {"field": "executor_group_id", "constraint": "environment_source"}
    assert counters(session) == before


# --- the key -----------------------------------------------------------------------------------------------------------------------


def test_the_same_key_with_the_same_group_replays_and_with_another_group_is_a_conflict(session, world) -> None:  # type: ignore[no-untyped-def]
    first, second = make_group(session, pull_member(session)), make_group(session, pull_member(session))
    shown, _ = world
    estimate = shown["preflight"].estimate_run(
        session, version_uid=str(shown["version"]), executor_group_id=first.group.group_id)
    consent = consent_for(estimate)

    def again(group_id: str, idempotency_key: str):  # type: ignore[no-untyped-def]
        return start_audit_run(
            session, version_uid=shown["version"], provider_mode="recorded", idempotency_key=idempotency_key,
            section_profiles=shown["registry"].section_profiles(), text_profiles=shown["registry"].resolve,
            input_budget_characters=100, operational_model_id="claude-opus-5", norms_snapshot=lambda _: None,
            cost_preflight=shown["preflight"], cost_consent=consent, cost_actor_uid=shown["actor"],
            group_admitter=shown["admitter"], executor_group_id=group_id)

    same_key = key()
    created = again(first.group.group_id, same_key)
    after_first = counters(session)
    replay = again(first.group.group_id, same_key)
    assert replay.replayed is True and replay.run_id == created.run_id and counters(session) == after_first
    with pytest.raises(DomainError) as reused:
        again(second.group.group_id, same_key)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE and counters(session) == after_first


# --- 20: a re-audit keeps the kind of selector the original start used -----------------------------------------------------------


def _ended(session, run_id: str) -> None:  # type: ignore[no-untyped-def]
    runs = RunRepository()
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    runs.terminate(session, run_id=run_id, from_state="queued", to_state="failed",
                   terminal_reason=ErrorCode.ANALYSIS_FAILED.value)


def _repeat(session, world, source_id: str):  # type: ignore[no-untyped-def]
    shown, _ = world
    estimate = shown["preflight"].estimate_reaudit(session, run_id=source_id)
    return reaudit_run(
        session, source_run_id=source_id, roles=frozenset({"expert"}), idempotency_key=key(), provider_mode="recorded",
        section_profiles=shown["registry"].section_profiles(), input_budget_characters=100,
        norms_snapshot=lambda _: None, cost_preflight=shown["preflight"], cost_consent=consent_for(estimate),
        cost_actor_uid=shown["actor"], group_admitter=shown["admitter"])


def test_a_repeat_of_a_group_start_is_admitted_again_on_the_groups_current_revision(session, world) -> None:  # type: ignore[no-untyped-def]
    created = make_group(session, pull_member(session))
    source = start(session, world, executor_group_id=created.group.group_id)
    _ended(session, source.run_id)
    revised = revise_group(
        session, group_id=created.group.group_id, settings=SETTINGS,
        members=[MemberRequest(m.connection_id, m.connection_revision_id) for m in created.current_revision.members],
        pins=PINS, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
    repeated = _repeat(session, world, source.run_id)
    row = run_row(session, repeated.run_id)
    assert (row["binding_state"], row["executor_group_revision_id"], row["routing_rule_revision_id"]) == (
        "pending", revised.current_revision.group_revision_id, None)
    assert row["state"] == "queued" and session.execute(text(
        "SELECT reaudit_of_run_id FROM audit_run WHERE run_id = :r"), {"r": repeated.run_id}).scalar_one() == source.run_id


def test_a_repeat_of_a_rule_start_names_nothing_and_follows_the_current_rule(session, world) -> None:  # type: ignore[no-untyped-def]
    first, second = make_group(session, pull_member(session)), make_group(session, pull_member(session))
    rule(session, first.current_revision.group_revision_id)
    rules_mode(session)
    source = start(session, world)
    assert run_row(session, source.run_id)["executor_group_revision_id"] == first.current_revision.group_revision_id
    _ended(session, source.run_id)
    moved = rule(session, second.current_revision.group_revision_id)
    repeated = _repeat(session, world, source.run_id)
    row = run_row(session, repeated.run_id)
    assert row["executor_group_revision_id"] == second.current_revision.group_revision_id
    assert row["routing_rule_revision_id"] == moved.rule_revision_id, "re-admitted by the current rule"


def test_a_repeat_of_a_group_start_whose_group_was_archived_is_refused_and_writes_nothing(session, world) -> None:  # type: ignore[no-untyped-def]
    created = make_group(session, pull_member(session))
    source = start(session, world, executor_group_id=created.group.group_id)
    _ended(session, source.run_id)
    archive_group(session, group_id=created.group.group_id, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
    shown, _ = world
    before = counters(session)
    with pytest.raises(DomainError) as caught:
        with session.begin_nested():
            shown["preflight"].estimate_reaudit(session, run_id=source.run_id)
    assert caught.value.code is ErrorCode.CONFLICT and dict(caught.value.detail_fields) == {"conflict_reason": "group_archived"}
    assert counters(session) == before
