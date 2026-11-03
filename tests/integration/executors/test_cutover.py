"""`EXEC2-CUTOVER-01` (ADR-0026 decision 17) over real PostgreSQL, one rolled-back transaction per test: the cut-over
preview, the confirmed cut-over, the rollback and the read-only legacy routes (B3 section 11 items 15, 16 and 22).

Written and **not run** in EXEC-2 (`R-149d`, D-292); each test would pass against PostgreSQL at head ``0048``. B3 section 11 is
not in the repository, so the numbers are the plan's table (``EXEC2-PLAN.md`` section 8), and the integrator re-maps them:

* item 15 -- **the preview**: the primary of each legacy route is proposed as a one-member group of its *current*
  revision, a standby is shown and not converted, an archived primary is flagged ``incompatible`` and a work kind with no
  route ``no_route``; the digest is over what is shown; the preview writes no row, no key and no event; an administrator
  only;
* item 16 -- **the confirmed cut-over**: in one transaction the one-member groups (``member_count`` 1, the member's
  current revision snapshotted), the rules and the ``rules`` event are made, the event carries the confirmed digest and what
  the change created, the journal's advisory lock is held, a work kind left out of the mapping has no rule and is refused by
  admission (``no_rule_for_work_kind``) instead of falling back to the legacy primary; a stale digest, an entry that is not
  ``ready`` and a name an active group holds are each refused and **leave nothing behind, not even the key** -- the last one
  after the first group was made, which only the transaction can take back; a repeat under the key replays; the mode it
  already is is ``routing_mode_unchanged``; under ``rules`` ``setExecutorRoute`` is ``conflict`` / ``routing_mode_rules`` and
  writes nothing while ``listExecutorRoutes`` is still readable;
* item 22 -- **the rollback**: ``legacy`` writes one event and touches no group, revision, rule or admitted work; the
  revision a start froze under ``rules`` is still read from its group, new starts follow the legacy route again, and a
  second cut-over appends new rules.

**What these cannot show.** The harness has one connection, so two administrators who confirm the same preview at once
are shown as one after the other (``routing_mode_unchanged``), which is what the journal's lock makes of them; the lock itself
is shown to be held (:func:`test_the_cut_over_holds_the_journals_advisory_lock`). A Run or comparison job that was *admitted*
by a rule is not built here (``tests/integration/runs/test_group_admission.py`` and ``tests/integration/jobs/
test_group_dispatch.py`` build them): what a rollback must not do to one is shown on the group revision and the rule revision it
froze, which dispatch reads and never the mode (nothing under ``jobs/`` reads the routing mode).
"""

from __future__ import annotations

import json
from contextlib import nullcontext
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.executors.public import (
    GroupSettings,
    MappingEntry,
    MemberRequest,
    RevisionSettings,
    archive_group,
    create_connection,
    create_group,
    group_capacity,
    group_revision_of,
    issue_runner_token,
    list_routes,
    list_routing_rules,
    pinned_models,
    preview_routing,
    record_probe_result,
    record_probe_started,
    request_probe,
    resolve_rule,
    revise_connection,
    set_route,
    set_routing_mode,
    set_routing_rule,
)
from auditmanager.executors.resolver import admit_group
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.executors.conftest import ADMIN, driver

Request, dispatch = driver.Request, driver.dispatch

ADMIN_ROLES = frozenset({"admin"})
PINS = pinned_models()
PIN_IDS = {pin.model_id for pin in PINS}
SONNET_PIN = next(pin for pin in PINS if pin.model_id == "claude-sonnet-5")
PULL = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered",
    allow_client_documents=False, timeout_seconds=600, pull_client="claude_code_session",
    answer_deadline_seconds=600, max_claimed_tasks=2, max_active_runs=2,
)
SONNET = GroupSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", strategy="least_loaded")
WORK_KINDS = (
    "text_analysis", "comparison_pair_check", "comparison_sheet_changes", "comparison_spec", "comparison_report",
    "comparison_stage_review",
)
COUNTED = (
    "executor_group", "executor_group_revision", "executor_group_member", "executor_routing_rule_revision",
    "executor_routing_mode_event", "executor_route_event", "command_record", "audit_event",
)


def key() -> str:
    return f"cut-{uuid4().hex}"


def factory(session):
    """A session factory that hands out the test's own session, for the adapters."""
    return lambda: nullcontext(session)


# --- the world ---------------------------------------------------------------------------------------------------------------


def pull_connection(session, name: str) -> tuple[str, str]:
    """A ``pull`` connection with one revision: ``(connection_id, revision_id)``."""
    connection_id = create_connection(
        session, kind="pull", display_name=name, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN,
    ).connection_id
    revision = revise_connection(
        session, connection_id=connection_id, settings=PULL, pinned_model_ids=PIN_IDS, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN)
    return connection_id, revision.revision_id


def revised(session, connection_id: str) -> str:
    return revise_connection(
        session, connection_id=connection_id, settings=PULL, pinned_model_ids=PIN_IDS, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN).revision_id


def ready_member(session, name: str) -> tuple[str, str]:
    """A ``pull`` connection a route accepts: probed ``ok`` on its current revision, and a runner seen."""
    connection_id, revision_id = pull_connection(session, name)
    probe = request_probe(
        session, connection_id=connection_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    assert record_probe_started(session, probe.probe_id)
    assert record_probe_result(
        session, probe.probe_id, outcome="ok", reported_model="claude-sonnet-5", identity_basis="declared",
        rate_check="not_metered")
    token = issue_runner_token(
        session, connection_id=connection_id, expires_in_days=None, roles=ADMIN_ROLES, idempotency_key=key(),
        actor_uid=ADMIN).record.token_id
    session.execute(text(
        "UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - make_interval(secs => 5) "
        "WHERE token_id = :id"), {"id": token})
    return connection_id, revision_id


def route(session, work_kind: str, primary: str, standby: str | None = None):
    return set_route(
        session, work_kind=work_kind, primary_connection_id=primary, standby_connection_id=standby,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)


def archive_in_place(session, connection_id: str) -> None:
    """Archive a connection a route still names -- a state ``archiveExecutorConnection`` refuses to make
    (``connection_routed``), so the preview's ``connection_archived`` is reached by the row, as a restore would."""
    session.execute(text(
        "UPDATE executor_connection SET archived_at = clock_timestamp(), archived_by = :actor "
        "WHERE connection_id = :id"), {"actor": ADMIN, "id": connection_id})


def propose(session):
    return preview_routing(session, roles=ADMIN_ROLES)


def mapping_of(shown, *kinds: str) -> list[MappingEntry]:
    """The administrator's confirmation of the proposal as shown: each named kind, or every ready one."""
    return [MappingEntry(item.work_kind, item.proposed_group_name) for item in shown.items
            if item.status == "ready" and (not kinds or item.work_kind in kinds)]


def confirm(session, shown, *kinds: str, idempotency_key: str | None = None, mapping=None, digest: str | None = None):
    return set_routing_mode(
        session, mode="rules", preview_digest=shown.preview_digest if digest is None else digest,
        mapping=mapping_of(shown, *kinds) if mapping is None else mapping, pins=PINS, roles=ADMIN_ROLES,
        idempotency_key=idempotency_key or key(), actor_uid=ADMIN)


def roll_back(session, *, idempotency_key: str | None = None):
    return set_routing_mode(
        session, mode="legacy", preview_digest=None, mapping=None, pins=PINS, roles=ADMIN_ROLES,
        idempotency_key=idempotency_key or key(), actor_uid=ADMIN)


def rows(session) -> dict[str, int]:
    """What a refused request must not change: the group, rule, route and mode-journal tables, the command records
    and the events."""
    return {table: int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in COUNTED}


def refused_cleanly(session, call) -> DomainError:
    """Run a command that must be refused, in a savepoint, and show it left no row, no command record and no event."""
    before = rows(session)
    with pytest.raises(DomainError) as error:
        with session.begin_nested():
            call()
    assert rows(session) == before, "a refused request leaves nothing behind, not even its key"
    return error.value


def detail(error: DomainError) -> tuple[str, dict[str, Any]]:
    return error.code.value, dict(error.detail_fields)


def mode_events(session) -> list[dict[str, Any]]:
    return [dict(row) for row in session.execute(text(
        "SELECT event_no, mode, preview_digest, mapping, changed_by FROM executor_routing_mode_event ORDER BY event_no"
    )).mappings().all()]


def events_of(session, aggregate_ids) -> list[str]:
    """The types of the events written for these aggregates (a group, a rule revision, a mode event), sorted."""
    return sorted(str(row[0]) for row in session.execute(text(
        "SELECT event_type FROM audit_event WHERE aggregate_id = ANY(:ids)"), {"ids": list(aggregate_ids)}).all())


def member_count(session, group_revision_id: str) -> int:
    return int(session.execute(text(
        "SELECT member_count FROM executor_group_revision WHERE group_revision_id = :r"
    ), {"r": group_revision_id}).scalar_one())


def another_backend_can_take(engine, name: str) -> bool:
    """Can a second connection take the advisory lock ``hashtextextended(name, 0)`` without waiting? The test's own
    transaction is uncommitted, so a lock it holds is a lock the second connection cannot get."""
    with engine.connect() as other:
        return bool(other.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:name, 0))"), {"name": name}).scalar_one())


@pytest.fixture
def stand(session, admin_account):
    """Three ready connections; ``text_analysis`` and ``comparison_pair_check`` routed to the first (with the second as
    the standby of the first), ``comparison_spec`` to the third, the other three work kinds unrouted."""
    one, two, three = ready_member(session, "Gateway one"), ready_member(session, "Gateway two"), ready_member(
        session, "Gateway three")
    route(session, "text_analysis", one[0], two[0])
    route(session, "comparison_pair_check", one[0])
    route(session, "comparison_spec", three[0])
    return {"one": one, "two": two, "three": three}


# --- item 15: the preview ---------------------------------------------------------------------------------------------------


def test_the_preview_proposes_a_one_member_group_per_primary_and_shows_a_standby_without_converting_it(
    session, stand,
) -> None:
    shown = propose(session)
    assert shown.routing_mode.mode == "legacy" and shown.routing_mode.mode_event_id is None
    assert [item.work_kind for item in shown.items] == list(WORK_KINDS)
    by_kind = {item.work_kind: item for item in shown.items}

    text_analysis = by_kind["text_analysis"]
    assert (text_analysis.status, text_analysis.primary_connection_id, text_analysis.standby_connection_id) == (
        "ready", stand["one"][0], stand["two"][0])
    assert text_analysis.connection_revision_id == stand["one"][1]
    assert (text_analysis.pin_id, text_analysis.gateway_model, text_analysis.billing) == (
        "claude-sonnet-5", "claude-sonnet-5", "not_metered")
    assert text_analysis.proposed_group_name == "Gateway one / text_analysis"
    assert by_kind["comparison_pair_check"].standby_connection_id is None
    assert by_kind["comparison_spec"].connection_revision_id == stand["three"][1]
    for kind in ("comparison_sheet_changes", "comparison_report", "comparison_stage_review"):
        assert by_kind[kind].as_wire() == {"work_kind": kind, "status": "no_route"}
    assert len({item.proposed_group_name for item in shown.items if item.proposed_group_name}) == 3


def test_the_preview_follows_the_current_revision_and_does_not_check_the_probe(session, stand) -> None:
    newer = revised(session, stand["one"][0])
    item = propose(session).items[0]
    assert item.status == "ready" and item.connection_revision_id == newer != stand["one"][1], (
        "the revision the group would snapshot is the connection's current one, not the one the route was set under")
    # Whether the new revision has passed a probe is not a preview status (the contract names no such issue); the
    # capacity of the group the cut-over makes says it, as dispatch will see it.
    shown = propose(session)
    created = confirm(session, shown, "text_analysis")
    (group,) = created.groups
    status = group_capacity(session, group.group.group_id).members[0]
    assert (status.snapshot_revision_id, status.eligible, status.issue) == (newer, False, "probe_not_ok")


def test_an_archived_primary_is_flagged_incompatible_and_a_work_kind_with_no_route_is_no_route(session, stand) -> None:
    archive_in_place(session, stand["three"][0])
    by_kind = {item.work_kind: item for item in propose(session).items}
    spec = by_kind["comparison_spec"]
    assert (spec.status, spec.incompatible_reason, spec.primary_connection_id) == (
        "incompatible", "connection_archived", stand["three"][0])
    assert spec.proposed_group_name is None
    assert by_kind["comparison_report"].status == "no_route"
    assert by_kind["text_analysis"].status == "ready"


def test_the_preview_writes_nothing_and_is_the_same_until_something_it_shows_changes(session, stand) -> None:
    before = rows(session)
    first, second = propose(session), propose(session)
    assert rows(session) == before, "no row, no command record, no event"
    assert first == second and len(first.preview_digest) == 64
    route(session, "comparison_report", stand["three"][0])
    assert propose(session).preview_digest != first.preview_digest


def test_only_an_administrator_previews(session, stand) -> None:
    error = refused_cleanly(session, lambda: preview_routing(session, roles=frozenset({"expert"})))
    assert detail(error) == ("permission_denied", {"required_capability": "role:admin"})


# --- item 16: the confirmed cut-over -------------------------------------------------------------------------------------------


def test_the_confirmed_cut_over_makes_the_groups_the_rules_and_the_rules_event_in_one_transaction(session, stand) -> None:
    shown = propose(session)

    changed = confirm(session, shown)

    assert changed.routing_mode.mode == "rules" and changed.routing_mode.changed_by == ADMIN
    assert [g.group.display_name for g in changed.groups] == [
        i.proposed_group_name for i in shown.items if i.status == "ready"]
    assert list_routing_rules(session).routing_mode == changed.routing_mode
    ready = {item.work_kind: item for item in shown.items if item.status == "ready"}
    assert [rule.work_kind for rule in changed.rules] == sorted(ready)
    for group in changed.groups:
        revision = group.current_revision
        assert (revision.revision_no, revision.strategy, member_count(session, revision.group_revision_id)) == (
            1, "least_loaded", 1)
        (member,) = revision.members
        (kind,) = group.routed_work_kinds
        assert (member.connection_id, member.connection_revision_id) == (
            ready[kind].primary_connection_id, ready[kind].connection_revision_id)
        assert (revision.pin_id, revision.gateway_model, revision.billing) == ("claude-sonnet-5", "claude-sonnet-5", "not_metered")
        assert (float(revision.input_per_mtok_usd), float(revision.output_per_mtok_usd)) == (
            SONNET_PIN.input_per_mtok_usd, SONNET_PIN.output_per_mtok_usd), "the provider lock's rates"
    assert all(resolve_rule(session, kind).group_revision_id == next(
        r.group_revision_id for r in changed.rules if r.work_kind == kind) for kind in ready)

    (event,) = mode_events(session)
    assert (event["event_no"], event["mode"], event["preview_digest"], event["changed_by"]) == (
        1, "rules", shown.preview_digest, ADMIN)
    by_kind = {entry["work_kind"]: entry for entry in event["mapping"]}
    assert sorted(by_kind) == sorted(ready)
    for rule in changed.rules:
        entry = by_kind[rule.work_kind]
        assert set(entry) == {"work_kind", "group_id", "group_revision_id", "rule_revision_id"}
        assert (entry["group_id"], entry["group_revision_id"], entry["rule_revision_id"]) == (
            rule.group_id, rule.group_revision_id, rule.rule_revision_id)
    assert changed.routing_mode.mode_event_id is not None
    assert session.execute(text(
        "SELECT mode_event_id FROM executor_routing_mode_event WHERE event_no = 1")).scalar_one() == (
            changed.routing_mode.mode_event_id)

    written = events_of(session, [g.group.group_id for g in changed.groups]
                        + [r.rule_revision_id for r in changed.rules] + [changed.routing_mode.mode_event_id])
    assert written == sorted(["executor.group_created"] * 3 + ["executor.routing_rule_set"] * 3
                             + ["executor.routing_mode_changed"]), "each group, each rule and the change, journaled once"
    kept = session.execute(text(
        "SELECT state FROM command_record WHERE command_type = 'set_executor_routing_mode'")).scalars().all()
    assert list(kept) == ["succeeded"]


def test_a_standby_is_never_made_a_member(session, stand) -> None:
    changed = confirm(session, propose(session))
    members = {m.connection_id for g in changed.groups for m in g.current_revision.members}
    assert members == {stand["one"][0], stand["three"][0]}
    assert stand["two"][0] not in members, "the standby of text_analysis is shown by the preview and converted by nothing"


def test_a_work_kind_left_out_of_the_mapping_has_no_rule_and_is_refused_instead_of_following_the_legacy_primary(
    session, stand,
) -> None:
    shown = propose(session)
    changed = confirm(session, shown, "text_analysis")
    assert [rule.work_kind for rule in changed.rules] == ["text_analysis"] and len(changed.groups) == 1
    assert admit_group(session, "text_analysis").group_revision_id == changed.rules[0].group_revision_id
    assert resolve_rule(session, "comparison_spec") is None
    with pytest.raises(DomainError) as refused:
        admit_group(session, "comparison_spec")
    assert detail(refused.value) == ("dependency_unavailable", {"dependency": "no_rule_for_work_kind"})
    assert [r.work_kind for r in list_routes(session)] == ["comparison_pair_check", "comparison_spec", "text_analysis"], (
        "the legacy routes are still there, and nothing reads them")


def test_a_work_kind_with_a_rule_made_by_hand_keeps_it_when_the_mapping_leaves_the_kind_out(session, stand) -> None:
    made = create_group(
        session, display_name="By hand", settings=SONNET, members=[MemberRequest(*stand["three"])], pins=PINS,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    ruled = set_routing_rule(
        session, work_kind="comparison_report", group_revision_id=made.current_revision.group_revision_id,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    changed = confirm(session, propose(session), "text_analysis")
    current = {rule.work_kind: rule.rule_revision_id for rule in changed.rules}
    assert set(current) == {"comparison_report", "text_analysis"}
    assert current["comparison_report"] == ruled.rule_revision_id, "a rule that was already set is not touched"


def test_the_cut_over_holds_the_journals_advisory_lock_to_the_end_of_its_transaction(session, stand, engine) -> None:
    """Another backend cannot take ``hashtextextended('executor_routing_mode_event', 0)`` while the transaction is open --
    which is what makes a second cut-over, or a route change, wait for this one -- and can take a lock of another name (so
    the probe is able to say yes)."""
    shown = propose(session)
    confirm(session, shown, "text_analysis")
    assert not another_backend_can_take(engine, "executor_routing_mode_event")
    assert another_backend_can_take(engine, "executor_routing_mode_event:other"), "the probe can tell a free key"


def test_a_stale_digest_is_a_conflict_and_leaves_nothing_behind(session, stand) -> None:
    shown = propose(session)
    revised(session, stand["one"][0])                     # the world moved after the proposal was shown
    error = refused_cleanly(session, lambda: confirm(session, shown))
    assert detail(error) == ("conflict", {"conflict_reason": "preview_stale", "aggregate_type": "ExecutorRoutingModeEvent"})
    assert list_routing_rules(session).routing_mode.mode == "legacy"


def test_a_route_changed_after_the_proposal_makes_it_stale(session, stand) -> None:
    shown = propose(session)
    route(session, "text_analysis", stand["three"][0])
    assert refused_cleanly(session, lambda: confirm(session, shown)).detail_fields["conflict_reason"] == "preview_stale"


def test_an_entry_for_a_work_kind_that_is_not_ready_is_refused_and_leaves_nothing_behind(session, stand) -> None:
    archive_in_place(session, stand["three"][0])
    shown = propose(session)
    names = mapping_of(shown, "text_analysis") + [MappingEntry("comparison_spec", "Spec")]
    error = refused_cleanly(session, lambda: confirm(session, shown, mapping=names))
    assert detail(error) == ("validation_failed", {"field": "mapping", "constraint": "mapping_entry_not_ready"})
    empty = refused_cleanly(session, lambda: confirm(session, shown, mapping=[]))
    assert detail(empty) == ("validation_failed", {"field": "mapping", "constraint": "mapping_required"})
    missing = refused_cleanly(session, lambda: set_routing_mode(
        session, mode="rules", preview_digest=None, mapping=mapping_of(shown), pins=PINS, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN))
    assert detail(missing) == ("validation_failed", {"field": "preview_digest", "constraint": "preview_digest_required"})


def test_a_name_an_active_group_holds_takes_back_the_groups_already_made(session, stand) -> None:
    create_group(
        session, display_name="Taken", settings=SONNET, members=[MemberRequest(*stand["one"])], pins=PINS,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    shown = propose(session)
    mapping = [MappingEntry("text_analysis", "Fresh"), MappingEntry("comparison_spec", "taken")]
    error = refused_cleanly(session, lambda: confirm(session, shown, mapping=mapping))
    assert detail(error) == ("conflict", {"conflict_reason": "group_name_in_use", "aggregate_type": "ExecutorGroup"})
    assert mode_events(session) == [], "the first group was made and is gone with the transaction; no mode event exists"


def test_a_repeat_under_the_key_replays_and_the_mode_it_already_is_is_refused(session, stand) -> None:
    shown = propose(session)
    spent = key()
    first = confirm(session, shown, idempotency_key=spent)
    before = rows(session)

    again = confirm(session, shown, idempotency_key=spent)
    assert [g.group.group_id for g in again.groups] == [g.group.group_id for g in first.groups]
    assert again.routing_mode == first.routing_mode and again.rules == first.rules
    assert rows(session) == before, "a replay writes nothing"

    unchanged = refused_cleanly(session, lambda: confirm(session, propose(session)))
    assert detail(unchanged) == (
        "conflict", {"conflict_reason": "routing_mode_unchanged", "aggregate_type": "ExecutorRoutingModeEvent"})

    other = refused_cleanly(session, lambda: confirm(session, shown, "text_analysis", idempotency_key=spent))
    assert other.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_a_rollback_to_the_mode_it_already_is_is_refused(session, stand) -> None:
    error = refused_cleanly(session, lambda: roll_back(session))
    assert error.detail_fields["conflict_reason"] == "routing_mode_unchanged"


def test_under_rules_set_route_is_a_conflict_that_writes_nothing_and_the_routes_stay_readable(session, stand) -> None:
    confirm(session, propose(session))
    listed = list_routes(session)
    error = refused_cleanly(session, lambda: route(session, "text_analysis", stand["three"][0]))
    assert detail(error) == (
        "conflict", {"conflict_reason": "routing_mode_rules", "aggregate_type": "ExecutorRouteEvent"})
    assert list_routes(session) == listed, "listExecutorRoutes is history, and it is unchanged"


def test_before_the_cut_over_and_after_the_rollback_set_route_works(session, stand) -> None:
    route(session, "text_analysis", stand["three"][0])                 # legacy: allowed
    confirm(session, propose(session))
    roll_back(session)
    changed = route(session, "text_analysis", stand["one"][0])         # legacy again: allowed
    assert changed.primary_connection_id == stand["one"][0]


# --- item 22: the rollback ------------------------------------------------------------------------------------------------------------


def test_the_rollback_writes_one_legacy_event_and_touches_no_group_revision_rule_or_admitted_work(session, stand) -> None:
    cut = confirm(session, propose(session))
    admitted = admit_group(session, "text_analysis")                    # what a start under rules freezes
    assert admitted is not None and admitted.rule_revision_id is not None
    frozen = group_revision_of(session, admitted.group_revision_id)
    tables = ("executor_group", "executor_group_revision", "executor_group_member", "executor_routing_rule_revision")
    groups_before = {table: int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in tables}

    back = roll_back(session)

    assert back.routing_mode.mode == "legacy" and back.groups == ()
    assert back.rules == cut.rules, "the rules stay current and readable"
    assert {table: int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in tables} == (
        groups_before)
    legacy = mode_events(session)[1]
    assert (legacy["event_no"], legacy["mode"], legacy["preview_digest"], legacy["mapping"]) == (2, "legacy", None, [])
    assert events_of(session, [back.routing_mode.mode_event_id]) == ["executor.routing_mode_changed"]
    assert group_revision_of(session, admitted.group_revision_id) == frozen, (
        "the revision a Run froze under rules is read from its group, as it was")
    assert resolve_rule(session, "text_analysis").rule_revision_id == admitted.rule_revision_id
    assert admit_group(session, "text_analysis") is None, "a new start follows the legacy route again"
    assert [r.work_kind for r in list_routes(session)] == ["comparison_pair_check", "comparison_spec", "text_analysis"]


def test_the_rollback_takes_neither_a_digest_nor_a_mapping(session, stand) -> None:
    confirm(session, propose(session))
    error = refused_cleanly(session, lambda: set_routing_mode(
        session, mode="legacy", preview_digest="a" * 64, mapping=None, pins=PINS, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN))
    assert detail(error) == ("validation_failed", {"field": "mapping", "constraint": "mapping_not_accepted"})
    assert list_routing_rules(session).routing_mode.mode == "rules"


def test_a_second_cut_over_after_a_rollback_appends_new_rules_and_leaves_the_first_groups_free_to_archive(
    session, stand,
) -> None:
    first = confirm(session, propose(session))
    roll_back(session)
    shown = propose(session)
    assert [i.proposed_group_name for i in shown.items if i.status == "ready"] == [
        f"{g.group.display_name} (2)" for g in first.groups], "the first names are still held by active groups"
    second = confirm(session, shown)
    numbers = [int(row[0]) for row in session.execute(text(
        "SELECT rule_no FROM executor_routing_rule_revision WHERE rule_revision_id = ANY(:ids)"
    ), {"ids": [r.rule_revision_id for r in second.rules]}).all()]
    assert numbers == [2, 2, 2], "rules are append-only: the second cut-over is rule 2 of each work kind"
    assert [e["event_no"] for e in mode_events(session)] == [1, 2, 3], "the journal has no gap"
    archived = archive_group(
        session, group_id=first.groups[0].group.group_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    assert archived.group.archived_at is not None, "no rule names the first groups any more"


# --- through the served API -------------------------------------------------------------------------------------------------------------


def surface_for(session, rings, roles: frozenset[str]):
    from auditmanager.api.routers import build_router
    from auditmanager.bootstrap.adapters import ExecutorAdapter, ExecutorGroupAdapter

    return driver.Surface(build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=roles),
        accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(),
        executors=ExecutorAdapter(factory(session), ring=rings.public),  # type: ignore[arg-type]
        executor_groups=ExecutorGroupAdapter(factory(session)),  # type: ignore[arg-type]
    ))


@pytest.fixture
def served(session, admin_account, rings):
    return surface_for(session, rings, frozenset({"admin"}))


@pytest.fixture
def served_expert(session, admin_account, rings):
    return surface_for(session, rings, frozenset({"expert"}))


def call(surface, method: str, path: str, body: Any = None, *, keyed: bool = True):
    headers = {"Content-Type": "application/json"}
    if keyed:
        headers["Idempotency-Key"] = f"cut-{uuid4().hex}"
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def test_the_preview_and_the_mode_through_the_served_application(session, stand, served) -> None:
    previewed = call(served, "GET", "/executor-routing/preview", keyed=False)
    assert previewed.status == 200, previewed.body
    shown = previewed.json()
    assert shown["routing_mode"] == {"mode": "legacy"} and len(shown["preview_digest"]) == 64
    assert [item["work_kind"] for item in shown["items"]] == list(WORK_KINDS)
    first = shown["items"][0]
    assert (first["status"], first["standby_connection_id"], first["proposed_group_name"]) == (
        "ready", stand["two"][0], "Gateway one / text_analysis")
    assert shown["items"][4] == {"work_kind": "comparison_report", "status": "no_route"}, "absent, never null"

    mapping = [{"work_kind": item["work_kind"], "group_display_name": item["proposed_group_name"]}
               for item in shown["items"] if item["status"] == "ready"]
    changed = call(served, "POST", "/executor-routing/mode", {
        "mode": "rules", "preview_digest": shown["preview_digest"], "mapping": mapping})
    assert changed.status == 200, changed.body
    body = changed.json()
    assert body["routing_mode"]["mode"] == "rules" and "mode_event_id" in body["routing_mode"]
    assert [g["display_name"] for g in body["groups"]] == [entry["group_display_name"] for entry in mapping]
    assert sorted(rule["work_kind"] for rule in body["rules"]) == sorted(entry["work_kind"] for entry in mapping)
    assert all(len(g["current_revision"]["members"]) == 1 for g in body["groups"])

    rules = call(served, "GET", "/executor-routing-rules", keyed=False)
    assert rules.json()["routing_mode"]["mode"] == "rules"

    blocked = call(served, "PUT", "/executor-routes", {
        "work_kind": "text_analysis", "primary_connection_id": stand["three"][0]})
    assert blocked.status == 409 and blocked.json()["details"]["conflict_reason"] == "routing_mode_rules"
    assert call(served, "GET", "/executor-routes", keyed=False).status == 200, "the legacy routes stay readable"

    back = call(served, "POST", "/executor-routing/mode", {"mode": "legacy"})
    assert back.status == 200, back.body
    assert back.json()["routing_mode"]["mode"] == "legacy" and back.json()["groups"] == []
    assert len(back.json()["rules"]) == len(mapping), "the rules are kept"
    allowed = call(served, "PUT", "/executor-routes", {
        "work_kind": "text_analysis", "primary_connection_id": stand["three"][0]})
    assert allowed.status == 200, allowed.body


def test_the_refusals_over_http_carry_their_typed_detail(session, stand, served) -> None:
    shown = call(served, "GET", "/executor-routing/preview", keyed=False).json()
    mapping = [{"work_kind": "text_analysis", "group_display_name": "One"}]

    no_digest = call(served, "POST", "/executor-routing/mode", {"mode": "rules", "mapping": mapping})
    assert no_digest.status == 422 and no_digest.json()["error_code"] == "validation_failed"
    assert no_digest.json()["details"] == {"field": "preview_digest", "constraint": "preview_digest_required"}

    no_mapping = call(served, "POST", "/executor-routing/mode", {
        "mode": "rules", "preview_digest": shown["preview_digest"]})
    assert no_mapping.status == 422
    assert no_mapping.json()["details"] == {"field": "mapping", "constraint": "mapping_required"}

    twice = call(served, "POST", "/executor-routing/mode", {
        "mode": "rules", "preview_digest": shown["preview_digest"],
        "mapping": mapping + [{"work_kind": "text_analysis", "group_display_name": "Two"}]})
    assert twice.status == 422
    assert twice.json()["details"] == {"field": "mapping", "constraint": "mapping_work_kind_repeated"}

    legacy_with_mapping = call(served, "POST", "/executor-routing/mode", {"mode": "legacy", "mapping": mapping})
    assert legacy_with_mapping.status == 422
    assert legacy_with_mapping.json()["details"] == {"field": "mapping", "constraint": "mapping_not_accepted"}

    stale = call(served, "POST", "/executor-routing/mode", {
        "mode": "rules", "preview_digest": "0" * 64, "mapping": mapping})
    assert stale.status == 409 and stale.json()["details"]["conflict_reason"] == "preview_stale"

    unchanged = call(served, "POST", "/executor-routing/mode", {"mode": "legacy"})
    assert unchanged.status == 409 and unchanged.json()["details"]["conflict_reason"] == "routing_mode_unchanged"


def test_only_an_administrator_previews_or_changes_the_mode_over_http(session, stand, served_expert) -> None:
    denied = [
        call(served_expert, "GET", "/executor-routing/preview", keyed=False),
        call(served_expert, "POST", "/executor-routing/mode", {"mode": "legacy"}),
    ]
    assert [answer.status for answer in denied] == [403, 403]
    assert {answer.json()["details"]["required_capability"] for answer in denied} == {"role:admin"}
    assert mode_events(session) == []
