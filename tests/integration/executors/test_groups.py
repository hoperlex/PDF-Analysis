"""`EXEC2-GROUP-STORE-01` (ADR-0026 decisions 10, 11 and 14) -- executor groups, routing rules and the capacity of a group,
over real PostgreSQL, one rolled-back transaction per test.

Written and **not run** in EXEC-2 (`R-149d`, D-292); each test would pass against PostgreSQL at head ``0048``.

* B3 section 11 item 1 -- an administrator creates a two-member group of one model: the group, its first revision (with the
  provider lock's rates) and the members' revision snapshots are stored and journaled once; a mismatched pin, gateway model
  or billing, a duplicate member, a revision that is not the connection's current one and an archived connection are each
  refused with their typed detail and **leave nothing behind, not even the key**; the database refuses a mixed member again
  when the application is bypassed;
* item 2 -- rules are set per work kind and append-only; naming the current revision again appends nothing; an archive is
  soft (every revision, member and rule stays, the name is free again), is refused while a rule names the group, and an
  archived group takes no revision and no rule; the database keeps a revision immutable;
* item 19 -- the capacity of a group is read from the units of a connection (``EXEC2-CAP-01``): per member its occupancy
  and the first reason dispatch would not choose it, counting only members in service; the facts the dispatcher reads
  feed the pure selection, and the persisted rotation moves on;
* through the served API -- the eight operations, any role's four reads and the administrator's four writes, and the
  explicit refusal of ``executor_group_id`` by ``startRun`` and ``estimateRunCost`` until ``EXEC2-GROUP-RUN-01``.

The Runs that occupy units are made with the ``EXEC-PAR-QUEUE-01`` rows (``tests/integration/jobs/connection_limit_support.py``)
through a session factory that hands out this test's own session, whose ``commit`` the harness joins to the transaction it
rolls back, so no row outlives the test. The pure parts are ``tests/unit/executors/test_group_selection.py`` and
``test_groups.py``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.executors.group_selection import choose, member_issue
from auditmanager.executors.public import (
    GroupSettings,
    MemberRequest,
    RevisionSettings,
    advance_group_rotation,
    archive_group,
    create_connection,
    create_group,
    group_capacity,
    group_detail,
    group_summary,
    issue_runner_token,
    list_group_summaries,
    list_routing_rules,
    member_facts,
    pinned_models,
    record_probe_result,
    record_probe_started,
    request_probe,
    resolve_rule,
    revise_connection,
    revise_group,
    set_routing_rule,
)
from auditmanager.jobs.public import JobRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorRoutingModeEventId
from tests.integration.executors.conftest import ADMIN, driver

_SUPPORT_NAME = "exec2_cap_connection_capacity_support"
if _SUPPORT_NAME in sys.modules:
    cap: ModuleType = sys.modules[_SUPPORT_NAME]
else:
    _spec = importlib.util.spec_from_file_location(
        _SUPPORT_NAME, Path(__file__).resolve().parents[1] / "jobs" / "connection_capacity_support.py"
    )
    assert _spec is not None and _spec.loader is not None
    cap = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT_NAME] = cap
    _spec.loader.exec_module(cap)

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
GROUP_TABLES = ("executor_group", "executor_group_revision", "executor_group_member", "executor_routing_rule_revision")


def key() -> str:
    return f"exec-{uuid4().hex}"


def factory(session):
    """A session factory that hands out the test's own session, for the helpers that take one."""
    return lambda: nullcontext(session)


def unpaused(session) -> None:
    JobRepository().set_paused(session, paused=False)


def pull_connection(session, settings: RevisionSettings = PULL, name: str = "member") -> tuple[str, str]:
    """A ``pull`` connection with one revision: ``(connection_id, revision_id)``."""
    connection_id = create_connection(
        session, kind="pull", display_name=name, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN,
    ).connection_id
    revision = revise_connection(
        session, connection_id=connection_id, settings=settings, pinned_model_ids=PIN_IDS,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN,
    )
    return connection_id, revision.revision_id


def revised(session, connection_id: str, settings: RevisionSettings = PULL) -> str:
    return revise_connection(
        session, connection_id=connection_id, settings=settings, pinned_model_ids=PIN_IDS,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN,
    ).revision_id


def probed_ok(session, connection_id: str) -> None:
    """Request a probe of the current revision and finish it as the worker would."""
    probe = request_probe(
        session, connection_id=connection_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    assert record_probe_started(session, probe.probe_id)
    assert record_probe_result(
        session, probe.probe_id, outcome="ok", reported_model="claude-sonnet-5", identity_basis="declared",
        rate_check="not_metered")


def runner_seen(session, connection_id: str) -> str:
    token = issue_runner_token(
        session, connection_id=connection_id, expires_in_days=None, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN,
    ).record.token_id
    session.execute(text(
        "UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - make_interval(secs => 5) "
        "WHERE token_id = :id"), {"id": token})
    return token


def ready_member(session, name: str = "member") -> tuple[str, str]:
    """A ``pull`` connection that dispatch would choose: probed ``ok`` on its current revision, a runner seen."""
    connection_id, revision_id = pull_connection(session, name=name)
    probed_ok(session, connection_id)
    runner_seen(session, connection_id)
    return connection_id, revision_id


def make(session, name: str, *members: tuple[str, str], settings: GroupSettings = SONNET, orders=()):
    requested = [
        MemberRequest(connection_id, revision_id, orders[index] if index < len(orders) else None)
        for index, (connection_id, revision_id) in enumerate(members)
    ]
    return create_group(
        session, display_name=name, settings=settings, members=requested, pins=PINS, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN)


def revise(session, group_id: str, *members: tuple[str, str], settings: GroupSettings = SONNET):
    return revise_group(
        session, group_id=group_id, settings=settings,
        members=[MemberRequest(connection_id, revision_id) for connection_id, revision_id in members],
        pins=PINS, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)


def rule(session, work_kind: str, group_revision_id: str):
    return set_routing_rule(
        session, work_kind=work_kind, group_revision_id=group_revision_id, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN)


def archive(session, group_id: str):
    return archive_group(
        session, group_id=group_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)


def rows(session) -> dict[str, int]:
    """What a refused request must not change: the group tables, the commands recorded for them and their events."""
    counted = {
        table: int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in GROUP_TABLES
    }
    counted["commands"] = int(session.execute(text(
        "SELECT count(*) FROM command_record WHERE command_type IN ('create_executor_group', "
        "'revise_executor_group', 'archive_executor_group', 'set_executor_routing_rule')"
    )).scalar_one())
    counted["events"] = int(session.execute(text(
        "SELECT count(*) FROM audit_event WHERE event_type IN ('executor.group_created', "
        "'executor.group_revised', 'executor.group_archived', 'executor.routing_rule_set')"
    )).scalar_one())
    return counted


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


def events_of(session, aggregate_id: str) -> list[tuple[str, dict[str, Any]]]:
    found = session.execute(text(
        "SELECT event_type, payload FROM audit_event WHERE aggregate_id = :id"), {"id": aggregate_id}).all()
    return sorted(((str(row[0]), dict(row[1])) for row in found), key=lambda item: item[0])


# --- item 1: a two-member group of one model ------------------------------------------------------------------------


def test_a_two_member_group_of_one_model_is_stored_as_a_snapshot_and_journaled_once(session, admin_account) -> None:
    first, second = ready_member(session, "one"), ready_member(session, "two")
    created = make(session, "Pool", first, second)
    group_id, revision = created.group.group_id, created.current_revision

    stored = session.execute(text(
        "SELECT display_name, rotation_cursor, archived_at, created_by FROM executor_group WHERE group_id = :g"
    ), {"g": group_id}).one()
    assert tuple(stored) == ("Pool", 0, None, ADMIN)
    row = session.execute(text(
        "SELECT revision_no, pin_id, gateway_model, billing, input_per_mtok_usd, output_per_mtok_usd, strategy "
        "FROM executor_group_revision WHERE group_revision_id = :r"), {"r": revision.group_revision_id}).one()
    assert (row[0], row[1], row[2], row[3], row[6]) == (1, "claude-sonnet-5", "claude-sonnet-5", "not_metered",
                                                        "least_loaded")
    assert (float(row[4]), float(row[5])) == (SONNET_PIN.input_per_mtok_usd, SONNET_PIN.output_per_mtok_usd), (
        "the rates are the provider lock's, copied when the revision was made")
    members = session.execute(text(
        "SELECT connection_id, connection_revision_id, tie_break_order FROM executor_group_member "
        "WHERE group_revision_id = :r ORDER BY connection_id"), {"r": revision.group_revision_id}).all()
    assert [tuple(m) for m in members] == sorted([(first[0], first[1], None), (second[0], second[1], None)])

    assert events_of(session, group_id) == [("executor.group_created", {
        "actor_uid": ADMIN, "revision_id": revision.group_revision_id, "revision_no": 1})]
    assert rows(session)["commands"] == 1 and rows(session)["executor_group_member"] == 2


def test_the_snapshot_is_the_revision_and_a_later_revision_of_the_connection_does_not_move_it(
    session, admin_account,
) -> None:
    first, second = ready_member(session), ready_member(session)
    created = make(session, "Pool", first, second)
    later = revised(session, first[0])
    assert later != first[1]
    detail_ = group_detail(session, created.group.group_id)
    assert [(m.connection_id, m.connection_revision_id) for m in detail_.summary.current_revision.members] == sorted(
        [(first[0], first[1]), (second[0], second[1])]), "the group still holds the revision it snapshotted"


@pytest.mark.parametrize(("what", "other", "field", "constraint"), [
    ("pin", replace(PULL, pin_id="claude-opus-5", gateway_model="claude-sonnet-5"), "pin_id", "member_pin_mismatch"),
    ("model", replace(PULL, gateway_model="claude-sonnet-5-preview"), "gateway_model", "member_model_mismatch"),
    ("billing", replace(PULL, billing="metered"), "billing", "member_billing_mismatch"),
])
def test_a_mismatched_member_is_refused_with_its_typed_detail_and_leaves_nothing_behind(
    session, admin_account, what: str, other: RevisionSettings, field: str, constraint: str,
) -> None:
    ok = pull_connection(session)
    odd = pull_connection(session, other, name=what)
    error = refused_cleanly(session, lambda: make(session, "Mixed", ok, odd))
    assert detail(error) == ("validation_failed", {"field": field, "constraint": constraint})


def test_a_duplicate_member_a_stale_revision_and_an_archived_connection_are_refused_and_leave_nothing(
    session, admin_account,
) -> None:
    from auditmanager.executors.public import archive_connection

    one, two = pull_connection(session, name="one"), pull_connection(session, name="two")

    error = refused_cleanly(session, lambda: make(session, "Twice", one, one))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "member_repeated"})

    stale = revised(session, two[0])                         # `two` has a newer revision than the one named
    assert stale != two[1]
    error = refused_cleanly(session, lambda: make(session, "Stale", one, two))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "member_revision_not_of_connection"})
    assert make(session, "Current", one, (two[0], stale)).current_revision.revision_no == 1, "the current one is accepted"

    error = refused_cleanly(session, lambda: make(session, "Another's", (one[0], two[1]), two))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "member_revision_not_of_connection"})

    gone = pull_connection(session, name="gone")
    archive_connection(session, connection_id=gone[0], roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    error = refused_cleanly(session, lambda: make(session, "Archived", one, gone))
    assert detail(error) == ("conflict", {"conflict_reason": "connection_archived"})

    error = refused_cleanly(session, lambda: make(session, "Unknown", one, ("exc_" + "0" * 26, "excr_" + "0" * 26)))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "unknown_executor_connection"})


def test_a_pin_the_lock_does_not_hold_and_a_name_that_is_not_a_label_are_refused_before_the_key_is_claimed(
    session, admin_account,
) -> None:
    one = pull_connection(session)
    error = refused_cleanly(session, lambda: make(session, "X", one, settings=replace(SONNET, pin_id="not-in-the-lock")))
    assert detail(error) == ("validation_failed", {"field": "pin_id", "constraint": "model_not_pinned"})
    error = refused_cleanly(session, lambda: make(session, "   ", one))
    assert detail(error) == ("validation_failed", {"field": "display_name", "constraint": "required"})
    assert refused_cleanly(session, lambda: make(session, "No members")).code is ErrorCode.VALIDATION_FAILED


def test_the_database_refuses_a_mixed_member_even_when_the_application_is_bypassed(session, admin_account) -> None:
    ok = pull_connection(session)
    odd = pull_connection(session, replace(PULL, billing="metered"), name="odd")
    created = make(session, "Pool", ok)
    with pytest.raises(DBAPIError) as refused:
        with session.begin_nested():
            session.execute(text(
                "INSERT INTO executor_group_member (group_revision_id, connection_id, connection_revision_id) "
                "VALUES (:r, :c, :cr)"),
                {"r": created.current_revision.group_revision_id, "c": odd[0], "cr": odd[1]})
    assert "not the pin, model and billing" in str(refused.value)
    assert rows(session)["executor_group_member"] == 1


def test_an_active_name_is_unique_without_regard_to_case_in_the_command_and_in_the_index(session, admin_account) -> None:
    one = pull_connection(session)
    first = make(session, "Pool", one)
    error = refused_cleanly(session, lambda: make(session, "  pOOL ", one))
    assert detail(error) == ("conflict", {"conflict_reason": "group_name_in_use", "aggregate_type": "ExecutorGroup"})
    with pytest.raises(DBAPIError) as indexed:
        with session.begin_nested():
            session.execute(text(
                "INSERT INTO executor_group (group_id, display_name, created_by) VALUES (:g, 'POOL', :a)"),
                {"g": "exg_" + "1" * 26, "a": ADMIN})
    assert getattr(indexed.value.orig, "sqlstate", None) == "23505"
    archive(session, first.group.group_id)
    assert make(session, "pool", one).group.display_name == "pool", "the name is free once the group is archived"


def test_a_repeated_key_replays_the_group_and_writes_nothing_more(session, admin_account) -> None:
    one = pull_connection(session)
    shared = key()
    args = dict(display_name="Pool", settings=SONNET, members=[MemberRequest(one[0], one[1])], pins=PINS,
                roles=ADMIN_ROLES, idempotency_key=shared, actor_uid=ADMIN)
    first = create_group(session, **args)
    before = rows(session)
    again = create_group(session, **args)
    assert again.group.group_id == first.group.group_id and rows(session) == before
    with pytest.raises(DomainError) as reused:
        create_group(session, **{**args, "display_name": "Other"})
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_only_an_administrator_creates_a_group(session, admin_account) -> None:
    one = pull_connection(session)
    for roles in (frozenset(), frozenset({"expert"})):
        before = rows(session)
        with pytest.raises(DomainError) as denied:
            create_group(
                session, display_name="Pool", settings=SONNET, members=[MemberRequest(*one)], pins=PINS,
                roles=roles, idempotency_key=key(), actor_uid=ADMIN)
        assert denied.value.code is ErrorCode.PERMISSION_DENIED and rows(session) == before


# --- item 2: revisions, rules and the archive -------------------------------------------------------------------------


def test_a_revision_is_added_and_the_database_keeps_every_revision_as_it_was(session, admin_account) -> None:
    one, two, three = (ready_member(session) for _ in range(3))
    created = make(session, "Pool", one, two)
    first_revision = created.current_revision
    revised_group = revise(session, created.group.group_id, one, two, three)

    assert revised_group.current_revision.revision_no == 2 and len(revised_group.current_revision.members) == 3
    listed = group_detail(session, created.group.group_id).revisions
    assert [r.revision_no for r in listed] == [2, 1] and listed[1] == first_revision
    assert [e[0] for e in events_of(session, created.group.group_id)] == ["executor.group_created", "executor.group_revised"]

    for statement in (
        "UPDATE executor_group_revision SET pin_id = 'other' WHERE group_revision_id = :r",
        "DELETE FROM executor_group_revision WHERE group_revision_id = :r",
        "DELETE FROM executor_group_member WHERE group_revision_id = :r",
    ):
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text(statement), {"r": first_revision.group_revision_id})
    assert group_detail(session, created.group.group_id).revisions[1] == first_revision


def test_a_rule_is_set_per_work_kind_is_append_only_and_naming_the_current_revision_appends_nothing(
    session, admin_account,
) -> None:
    one = ready_member(session)
    first = make(session, "First", one)
    second = make(session, "Second", one)
    first_revision, second_revision = first.current_revision.group_revision_id, second.current_revision.group_revision_id

    a = rule(session, "text_analysis", first_revision)
    b = rule(session, "comparison_report", first_revision)
    moved = rule(session, "text_analysis", second_revision)
    assert (a.rule_no, b.rule_no, moved.rule_no) == (1, 1, 2)
    before = rows(session)
    assert rule(session, "text_analysis", second_revision) == moved
    assert rows(session)["executor_routing_rule_revision"] == before["executor_routing_rule_revision"] == 3
    assert rows(session)["events"] == before["events"], "the repeat journaled nothing"

    listing = list_routing_rules(session)
    assert [(r.work_kind, r.group_revision_id) for r in listing.rules] == [
        ("comparison_report", first_revision), ("text_analysis", second_revision)]
    assert resolve_rule(session, "text_analysis") == moved and resolve_rule(session, "comparison_spec") is None
    assert group_summary(session, first.group.group_id).routed_work_kinds == ("comparison_report",)
    assert group_summary(session, second.group.group_id).routed_work_kinds == ("text_analysis",)
    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(text("DELETE FROM executor_routing_rule_revision WHERE rule_revision_id = :r"),
                            {"r": a.rule_revision_id})


def test_the_rules_list_carries_the_routing_mode_which_is_legacy_until_the_journal_says_otherwise(
    session, admin_account,
) -> None:
    assert list_routing_rules(session).routing_mode.mode == "legacy"
    assert list_routing_rules(session).routing_mode.mode_event_id is None
    event_id = str(ExecutorRoutingModeEventId.new())
    session.execute(text(
        "INSERT INTO executor_routing_mode_event (mode_event_id, event_no, mode, preview_digest, mapping, changed_by) "
        "VALUES (:id, 1, 'rules', :digest, CAST(:mapping AS jsonb), :actor)"),
        {"id": event_id, "digest": "a" * 64, "mapping": json.dumps([{"work_kind": "text_analysis"}]),
         "actor": ADMIN})
    state = list_routing_rules(session).routing_mode
    assert (state.mode, state.mode_event_id, state.changed_by) == ("rules", event_id, ADMIN)


def test_an_archive_is_soft_and_every_revision_member_and_rule_stays_readable(session, admin_account) -> None:
    one, two = ready_member(session), ready_member(session)
    old = make(session, "Old", one, two)
    new = make(session, "New", one, two)
    old_revision = old.current_revision
    rule(session, "text_analysis", old_revision.group_revision_id)

    error = refused_cleanly(session, lambda: archive(session, old.group.group_id))
    assert detail(error) == ("conflict", {"conflict_reason": "group_routed", "aggregate_type": "ExecutorGroup"})

    rule(session, "text_analysis", new.current_revision.group_revision_id)       # the rule moves on; now it can go
    archived = archive(session, old.group.group_id)
    assert archived.group.archived_at is not None and archived.group.archived_by == ADMIN

    assert group_detail(session, old.group.group_id).revisions[0] == old_revision
    assert [(m.connection_id, m.connection_revision_id) for m in old_revision.members] == sorted(
        [(one[0], one[1]), (two[0], two[1])])
    names = [(s.group.display_name, s.group.archived_at is not None) for s in list_group_summaries(session)]
    assert names == [("New", False), ("Old", True)], "archived groups are listed, after the active ones"
    assert rows(session)["executor_group_revision"] == 2 and rows(session)["executor_routing_rule_revision"] == 2

    again = archive(session, old.group.group_id)                               # as it stands, nothing written
    assert again.group.archived_at == archived.group.archived_at
    assert [e[0] for e in events_of(session, old.group.group_id)].count("executor.group_archived") == 1


def test_an_archived_group_takes_no_revision_and_no_rule(session, admin_account) -> None:
    one = ready_member(session)
    created = make(session, "Pool", one)
    archive(session, created.group.group_id)

    error = refused_cleanly(session, lambda: revise(session, created.group.group_id, one))
    assert detail(error) == ("conflict", {"conflict_reason": "group_archived", "aggregate_type": "ExecutorGroup"})
    error = refused_cleanly(
        session, lambda: rule(session, "text_analysis", created.current_revision.group_revision_id))
    assert detail(error) == ("conflict", {"conflict_reason": "group_archived", "aggregate_type": "ExecutorGroup"})
    with pytest.raises(DBAPIError):                      # and the database says the same when the application is bypassed
        with session.begin_nested():
            session.execute(text(
                "INSERT INTO executor_routing_rule_revision (rule_revision_id, work_kind, rule_no, group_revision_id, "
                "set_by) VALUES (:id, 'text_analysis', 1, :r, :a)"),
                {"id": "exrr_" + "1" * 26, "r": created.current_revision.group_revision_id, "a": ADMIN})


def test_an_unknown_group_and_an_unknown_group_revision_are_not_found(session, admin_account) -> None:
    missing_group, missing_revision = "exg_" + "0" * 26, "exgr_" + "0" * 26
    member = pull_connection(session)
    for read in (group_summary, group_detail, group_capacity):
        assert refused_cleanly(session, lambda read=read: read(session, missing_group)).code is ErrorCode.NOT_FOUND
    error = refused_cleanly(session, lambda: revise(session, missing_group, member))
    assert error.code is ErrorCode.NOT_FOUND
    error = refused_cleanly(session, lambda: archive(session, missing_group))
    assert error.code is ErrorCode.NOT_FOUND
    error = refused_cleanly(session, lambda: rule(session, "text_analysis", missing_revision))
    assert detail(error) == ("not_found", {"aggregate_type": "ExecutorGroupRevision"})
    error = refused_cleanly(session, lambda: rule(session, "not_a_kind", missing_revision))
    assert detail(error) == ("validation_failed", {"field": "work_kind", "constraint": "enum"})


# --- item 19: the capacity of a group and the selection among its members ----------------------------------------------


def test_the_capacity_of_a_group_is_the_units_of_its_members_in_service(session, admin_account) -> None:
    unpaused(session)
    sessions = factory(session)
    one, two = ready_member(session, "one"), ready_member(session, "two")
    created = make(session, "Pool", one, two)
    gid = created.group.group_id
    by_id = lambda answer: {m.connection_id: m for m in answer.members}          # noqa: E731

    idle = group_capacity(session, gid)
    assert (idle.capacity, idle.used, idle.waiting) == (4, 0, 0)
    assert all(m.eligible and m.issue is None and m.occupancy.capacity == 2 for m in idle.members)

    first_run = cap.queue_run(sessions, one[1])
    cap.claim(sessions, first_run)
    busy = group_capacity(session, gid)
    assert (busy.capacity, busy.used) == (4, 1)
    assert by_id(busy)[one[0]].occupancy.active_runs == 1 and by_id(busy)[one[0]].eligible

    cap.claim(sessions, cap.queue_run(sessions, one[1]))
    full = group_capacity(session, gid)
    assert (by_id(full)[one[0]].eligible, by_id(full)[one[0]].issue) == (False, "at_capacity")
    assert (full.capacity, full.used) == (4, 2), "a full member is still in service"
    assert by_id(full)[two[0]].eligible

    newer = revised(session, one[0])                                              # the snapshot is no longer current
    changed = group_capacity(session, gid)
    member = by_id(changed)[one[0]]
    assert (member.snapshot_revision_id, member.current_revision_id, member.issue) == (one[1], newer, "revision_changed")
    assert (changed.capacity, changed.used) == (2, 0), "a member out of service is not counted"
    assert changed.group_revision_id == created.current_revision.group_revision_id


def test_each_reason_a_member_would_not_be_chosen_is_reported_from_the_rows(session, admin_account) -> None:
    from auditmanager.executors.public import archive_connection

    ready = ready_member(session, "ready")
    unprobed = pull_connection(session, name="unprobed")
    runner_seen(session, unprobed[0])
    offline = pull_connection(session, name="offline")
    probed_ok(session, offline[0])
    gone = ready_member(session, "gone")
    created = make(session, "Pool", ready, unprobed, offline, gone)
    archive_connection(session, connection_id=gone[0], roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)

    answer = group_capacity(session, created.group.group_id)
    issues = {m.connection_id: m.issue for m in answer.members}
    assert issues == {
        ready[0]: None, unprobed[0]: "probe_not_ok", offline[0]: "runner_offline", gone[0]: "connection_archived"}


def test_the_facts_the_dispatcher_reads_feed_the_pure_selection_and_the_rotation_moves_on(
    session, admin_account,
) -> None:
    unpaused(session)
    sessions = factory(session)
    one, two = ready_member(session, "one"), ready_member(session, "two")
    created = make(session, "Pool", one, two)
    gid, revision = created.group.group_id, created.current_revision

    def pick(rotation: int):
        facts = member_facts(session, revision)
        eligible = [f for f in facts if member_issue(f) in (None, "at_capacity")]
        return choose(
            [f.as_member() for f in eligible], {f.connection_id: f.used for f in eligible},
            {f.connection_id: f.capacity for f in eligible}, rotation)

    tied = sorted([one[0], two[0]])
    assert [pick(0), pick(1), pick(2)] == [tied[0], tied[1], tied[0]]

    cap.claim(sessions, cap.queue_run(sessions, one[1]))                          # one is now the busier member
    assert {pick(0), pick(1), pick(2)} == {two[0]}

    cap.claim(sessions, cap.queue_run(sessions, one[1]))
    cap.claim(sessions, cap.queue_run(sessions, two[1]))
    cap.claim(sessions, cap.queue_run(sessions, two[1]))
    assert pick(0) is None, "no free unit anywhere: the work waits, it is sent nowhere"

    assert group_summary(session, gid).group.rotation_cursor == 0
    assert (advance_group_rotation(session, gid), advance_group_rotation(session, gid)) == (1, 2)
    assert group_summary(session, gid).group.rotation_cursor == 2


# --- through the served API -------------------------------------------------------------------------------------------


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
        headers["Idempotency-Key"] = f"exec-{uuid4().hex}"
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def group_body(name: str, *members: tuple[str, str]) -> dict[str, Any]:
    return {
        "display_name": name, "pin_id": "claude-sonnet-5", "gateway_model": "claude-sonnet-5",
        "billing": "not_metered",
        "members": [{"connection_id": c, "connection_revision_id": r} for c, r in members],
    }


def test_the_eight_operations_through_the_served_application(session, served) -> None:
    one, two = ready_member(session), ready_member(session)

    created = call(served, "POST", "/executor-groups", group_body("Pool", one, two))
    assert created.status == 201, created.body
    body = created.json()
    gid = body["group_id"]
    assert body["display_name"] == "Pool" and body["routed_work_kinds"] == [] and "archived_at" not in body
    revision = body["current_revision"]
    assert (revision["revision_no"], revision["pin_id"], revision["billing"], revision["strategy"]) == (
        1, "claude-sonnet-5", "not_metered", "least_loaded")
    assert sorted(m["connection_id"] for m in revision["members"]) == sorted([one[0], two[0]])
    assert all("tie_break_order" not in m for m in revision["members"]), "an optional property is absent, never null"
    assert (revision["input_per_mtok_usd"], revision["output_per_mtok_usd"]) == (
        SONNET_PIN.input_per_mtok_usd, SONNET_PIN.output_per_mtok_usd)

    listed = call(served, "GET", "/executor-groups", keyed=False)
    assert listed.status == 200 and [g["group_id"] for g in listed.json()["items"]] == [gid]
    detail_ = call(served, "GET", f"/executor-groups/{gid}", keyed=False)
    assert detail_.status == 200 and [r["revision_no"] for r in detail_.json()["revisions"]] == [1]
    assert detail_.json()["group"]["group_id"] == gid

    capacity = call(served, "GET", f"/executor-groups/{gid}/capacity", keyed=False)
    assert capacity.status == 200, capacity.body
    shown = capacity.json()
    assert (shown["capacity"], shown["used"], shown["waiting"], shown["group_id"]) == (4, 0, 0, gid)
    assert all(m["eligible"] is True and "ineligible_reason" not in m for m in shown["members"])
    assert all(m["occupancy"] == {"capacity": 2, "active_runs": 0, "active_calls": 0} for m in shown["members"])

    revised_ = call(served, "POST", f"/executor-groups/{gid}/revisions", {
        key_: value for key_, value in group_body("ignored", one).items() if key_ != "display_name"})
    assert revised_.status == 201, revised_.body
    assert revised_.json()["current_revision"]["revision_no"] == 2 and len(revised_.json()["current_revision"]["members"]) == 1

    first_revision = revision["group_revision_id"]
    ruled = call(served, "PUT", "/executor-routing-rules/text_analysis", {"group_revision_id": first_revision})
    assert ruled.status == 200, ruled.body
    assert (ruled.json()["work_kind"], ruled.json()["group_id"], ruled.json()["group_revision_id"]) == (
        "text_analysis", gid, first_revision)

    rules = call(served, "GET", "/executor-routing-rules", keyed=False)
    assert rules.status == 200
    assert rules.json()["routing_mode"] == {"mode": "legacy"}
    assert [r["work_kind"] for r in rules.json()["items"]] == ["text_analysis"]
    assert call(served, "GET", f"/executor-groups/{gid}", keyed=False).json()["group"]["routed_work_kinds"] == [
        "text_analysis"]

    routed = call(served, "POST", f"/executor-groups/{gid}/archive")
    assert routed.status == 409 and routed.json()["details"]["conflict_reason"] == "group_routed"

    other = call(served, "POST", "/executor-groups", group_body("Other", one)).json()
    moved = call(served, "PUT", "/executor-routing-rules/text_analysis", {
        "group_revision_id": other["current_revision"]["group_revision_id"]})
    assert moved.status == 200
    archived = call(served, "POST", f"/executor-groups/{gid}/archive")
    assert archived.status == 200 and "archived_at" in archived.json()
    assert call(served, "POST", f"/executor-groups/{gid}/revisions", {
        key_: value for key_, value in group_body("x", one).items() if key_ != "display_name"}).status == 409
    assert call(served, "GET", f"/executor-groups/{gid}", keyed=False).status == 200, "an archived group stays readable"


def test_the_refusals_over_http_carry_their_typed_detail(session, served) -> None:
    one = ready_member(session)
    odd = pull_connection(session, replace(PULL, billing="metered"), name="odd")
    mixed = call(served, "POST", "/executor-groups", group_body("Mixed", one, odd))
    assert mixed.status == 422 and mixed.json()["error_code"] == "validation_failed"
    assert mixed.json()["details"] == {"field": "billing", "constraint": "member_billing_mismatch"}

    twice = call(served, "POST", "/executor-groups", group_body("Twice", one, one))
    assert twice.status == 422 and twice.json()["details"] == {"field": "members", "constraint": "member_repeated"}

    assert call(served, "POST", "/executor-groups", group_body("Pool", one)).status == 201
    taken = call(served, "POST", "/executor-groups", group_body("POOL", one))
    assert taken.status == 409 and taken.json()["details"]["conflict_reason"] == "group_name_in_use"

    unknown = call(served, "GET", "/executor-groups/exg_" + "0" * 26, keyed=False)
    assert unknown.status == 404 and unknown.json()["error_code"] == "not_found"
    bad_kind = call(served, "PUT", "/executor-routing-rules/not_a_kind", {"group_revision_id": "exgr_" + "0" * 26})
    assert bad_kind.status == 422 and bad_kind.json()["details"] == {"field": "work_kind", "constraint": "enum"}
    no_revision = call(served, "PUT", "/executor-routing-rules/text_analysis", {"group_revision_id": "exgr_" + "0" * 26})
    assert no_revision.status == 404


def test_the_four_reads_are_open_to_an_expert_and_the_four_writes_are_not(session, served_expert) -> None:
    for path in ("/executor-groups", "/executor-routing-rules"):
        assert call(served_expert, "GET", path, keyed=False).status == 200, path
    unknown = "exg_" + "0" * 26
    assert call(served_expert, "GET", f"/executor-groups/{unknown}", keyed=False).status == 404
    assert call(served_expert, "GET", f"/executor-groups/{unknown}/capacity", keyed=False).status == 404

    denied = [
        call(served_expert, "POST", "/executor-groups", group_body("Pool")),
        call(served_expert, "POST", f"/executor-groups/{unknown}/revisions", {}),
        call(served_expert, "POST", f"/executor-groups/{unknown}/archive"),
        call(served_expert, "PUT", "/executor-routing-rules/text_analysis", {"group_revision_id": "exgr_" + "0" * 26}),
    ]
    assert [answer.status for answer in denied] == [403, 403, 403, 403]
    assert {answer.json()["details"]["required_capability"] for answer in denied} == {"role:admin"}


def test_start_run_and_estimate_run_cost_refuse_an_executor_group_until_dispatch_exists(session, served) -> None:
    group = "exg_01M2545JSD15ETSNNV904X991K"
    version = "ver_01M2545JSD15ETSNNV904X991J"
    before = rows(session)
    for method, path, extra in (
        ("POST", "/runs", {}), ("POST", "/runs/cost-estimate", {}), ("POST", "/runs", {"relaxed_limits": True}),
    ):
        answer = call(served, method, path, {"version_uid": version, "executor_group_id": group, **extra})
        assert answer.status == 503, (path, answer.body)
        assert answer.json()["error_code"] == "dependency_unavailable"
        assert answer.json()["details"] == {"dependency": "executor_group_dispatch"}
    assert rows(session) == before
