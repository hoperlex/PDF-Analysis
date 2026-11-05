"""`EXEC2-GROUP-STORE-01`: the group and rule commands, homogeneity and the capacity read (B3 section 11 items 1, 2 and 19).

No database: the repositories, the command ledger and the journal are stand-ins that record what they were asked, so
what matters is visible -- a refusal writes nothing at all, a replay writes nothing, a revision is added and never
changed, an archive deletes nothing, and the journal carries identities and classifiers only. The same flows on real rows
and through the served API are ``tests/integration/executors/test_groups.py``.

* item 1 -- an administrator creates a two-member group whose members share ``pin_id``, ``gateway_model`` and billing;
  a mismatched pin, gateway model or billing, a duplicate member, a revision that is not the connection's current one,
  an archived or unknown connection and a kind this release does not serve are each refused with their typed detail,
  and before anything is written;
* item 2 -- a rule is set per work kind, append-only; naming the current revision again appends nothing; an archived
  group (and every one of its revisions) stays readable; the archive of a group a rule names is refused;
* item 19 -- the capacity of a group is read from the units of ``EXEC2-CAP-01``: per member its occupancy and the first
  reason dispatch would not choose it; only members in service are counted.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin
from auditmanager.executors import group_commands
from auditmanager.executors.group_repository import GroupRepository
from auditmanager.executors.group_commands import (
    archive_group,
    create_group,
    group_capacity,
    group_detail,
    group_summary,
    list_group_summaries,
    list_routing_rules,
    resolve_rule,
    revise_group,
    set_routing_rule,
)
from auditmanager.executors.groups import (
    GroupMemberRecord,
    GroupRecord,
    GroupRevisionRecord,
    GroupSettings,
    MemberRequest,
    ModeState,
    RuleRecord,
    clean_display_name,
    refuse_settings,
    refuse_work_kind,
)
from auditmanager.executors.model import (
    WORK_KINDS,
    ConnectionRecord,
    RevisionRecord,
    RevisionSettings,
)
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.jobs.events import _SAFE_KEYS
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorGroupId, ExecutorGroupRevisionId, ExecutorRoutingRuleRevisionId

T0 = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
C1, C2, C3 = (f"exc_01M2545JSD15ETSNNV904X991{tail}" for tail in "ABC")
R1, R2, R3, R4 = (f"excr_01M2545JSD15ETSNNV904X991{tail}" for tail in "ABCD")
SESSION = object()
PINS = [ModelPin("claude-sonnet-5", 3.0, 15.0), ModelPin("claude-opus-5", 15.0, 75.0)]
SONNET = GroupSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", strategy="least_loaded")


def pull_settings(**over: Any) -> RevisionSettings:
    base = dict(
        pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered",
        allow_client_documents=False, timeout_seconds=600, pull_client="claude_code_session",
        answer_deadline_seconds=600, max_claimed_tasks=4, max_active_runs=2,
    )
    return RevisionSettings(**{**base, **over})


def refusal(call) -> DomainError:
    with pytest.raises(DomainError) as refused:
        call()
    return refused.value


def detail(error: DomainError) -> tuple[str, dict[str, Any]]:
    return error.code.value, dict(error.detail_fields)


# --- stand-ins -----------------------------------------------------------------------------------------------


class FakeLedger:
    def __init__(self, replay: dict[str, Any] | None = None) -> None:
        self.replay = replay
        self.began: list[tuple[str, str]] = []
        self.fingerprints: list[str] = []
        self.succeeded: list[dict[str, Any]] = []

    def begin(self, session, *, command_type, idempotency_key, fingerprint):
        self.began.append((command_type, str(idempotency_key)))
        self.fingerprints.append(str(fingerprint))
        if self.replay is not None:
            return CommandReplay(command_id="cmd_replay", outcome=self.replay)  # type: ignore[arg-type]
        return CommandStarted(command_id="cmd_1")  # type: ignore[arg-type]

    def succeed(self, session, command_id, outcome) -> None:
        self.succeeded.append(dict(outcome))


class Journal:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def __call__(self, session, *, event_type, aggregate_type, aggregate_id, payload=None, **_) -> None:
        self.events.append({"event_type": event_type, "aggregate_type": aggregate_type,
                            "aggregate_id": aggregate_id, "payload": dict(payload or {})})

    def types(self) -> list[str]:
        return [event["event_type"] for event in self.events]


class FakeExecutors:
    """``ExecutorRepository`` in memory: connections, their revisions, probes, runners and units."""

    def __init__(self) -> None:
        self.connections: dict[str, ConnectionRecord] = {}
        self.revisions: dict[str, RevisionRecord] = {}
        self.chain: dict[str, list[str]] = {}
        self.probe_ok: dict[str, bool] = {}
        self.online: set[str] = set()
        self.units: dict[str, tuple[int, int, int]] = {}
        self.swept = 0

    def connect(
        self, connection_id: str, revision_id: str, *, kind: str = "pull", archived: bool = False,
        probed: bool = True, online: bool = True, **settings: Any,
    ) -> RevisionRecord:
        self.connections[connection_id] = ConnectionRecord(
            connection_id=connection_id, kind=kind, display_name=connection_id[-1], created_at=T0,
            created_by=ADMIN, archived_at=T0 if archived else None, archived_by=ADMIN if archived else None)
        if online:
            self.online.add(connection_id)
        return self.revise(connection_id, revision_id, probed=probed, **settings)

    def revise(self, connection_id: str, revision_id: str, *, probed: bool = True, **settings: Any) -> RevisionRecord:
        chain = self.chain.setdefault(connection_id, [])
        record = RevisionRecord(
            revision_id=revision_id, connection_id=connection_id, revision_no=len(chain) + 1,
            created_at=T0, created_by=ADMIN, settings=pull_settings(**settings))
        self.revisions[revision_id] = record
        chain.append(revision_id)
        self.probe_ok[revision_id] = probed
        capacity = record.settings.max_active_runs or 1
        previous = self.units.get(connection_id, (0, 0, 0))
        self.units[connection_id] = (capacity, previous[1], previous[2])
        return record

    def occupy(self, connection_id: str, *, runs: int = 0, calls: int = 0) -> None:
        self.units[connection_id] = (self.units[connection_id][0], runs, calls)

    # -- the ExecutorRepository surface the commands use ---------------------------------------------
    def get_connection(self, session, connection_id, *, lock=False):
        return self.connections.get(connection_id)

    def get_revision(self, session, revision_id):
        return self.revisions.get(revision_id)

    def current_revisions(self, session, connection_ids):
        return {cid: self.revisions[self.chain[cid][-1]] for cid in connection_ids if cid in self.chain}

    def unit_counts(self, session, connection_ids):
        return {cid: self.units[cid] for cid in connection_ids if cid in self.units}

    def sweep_probes(self, session):
        self.swept += 1
        return 0

    def runner_online(self, session, connection_id):
        return connection_id in self.online

    def latest_finished_probe(self, session, revision_id, secret_id):
        return SimpleNamespace(outcome="ok" if self.probe_ok.get(revision_id) else "credential_refused")

    def current_secrets(self, session, connection_ids):
        return {}


class FakeGroups:
    """``GroupRepository`` in memory. ``writes`` records every row written, so a refusal can be shown to write none."""

    def __init__(self, executors: FakeExecutors) -> None:
        self.executors = executors
        self.groups: dict[str, GroupRecord] = {}
        self.revisions: dict[str, GroupRevisionRecord] = {}
        self.rules: list[RuleRecord] = []
        self.mode = ModeState()
        self.pending = 0
        self.writes: list[str] = []
        self.locked_connections: list[list[str]] = []
        self.member_counts: list[int] = []
        self.rotation = 0

    # -- groups
    def lock_name(self, session, display_name):
        pass

    def name_in_use(self, session, display_name):
        return any(group.display_name.lower() == display_name.lower() and group.archived_at is None
                   for group in self.groups.values())

    def insert_group(self, session, *, display_name, actor_uid):
        record = GroupRecord(
            group_id=str(ExecutorGroupId.new()), display_name=display_name, rotation_cursor=0,
            created_at=T0, created_by=actor_uid)
        self.groups[record.group_id] = record
        self.writes.append("group")
        return record

    def get_group(self, session, group_id, *, lock=False):
        return self.groups.get(group_id)

    def list_groups(self, session, *, limit=500):
        return sorted(self.groups.values(), key=lambda g: (g.archived_at is not None, g.created_at))

    def archive_group(self, session, group_id, *, actor_uid):
        archived = replace(self.groups[group_id], archived_at=T0 + timedelta(hours=1), archived_by=actor_uid)
        self.groups[group_id] = archived
        self.writes.append("archive")
        return archived

    def lock_connections(self, session, connection_ids):
        self.locked_connections.append(sorted(set(connection_ids)))
        return {cid for cid in connection_ids if cid in self.executors.connections}

    # -- revisions
    def next_revision_no(self, session, group_id):
        return 1 + sum(1 for r in self.revisions.values() if r.group_id == group_id)

    def insert_revision(
        self, session, *, group_id, revision_no, settings, input_per_mtok_usd, output_per_mtok_usd, members,
        actor_uid,
    ):
        self.member_counts.append(len(members))
        stored = tuple(sorted(
            (GroupMemberRecord(m.connection_id, m.connection_revision_id, m.tie_break_order) for m in members),
            key=lambda m: (m.tie_break_order is None, m.tie_break_order or 0, m.connection_id)))
        record = GroupRevisionRecord(
            group_revision_id=str(ExecutorGroupRevisionId.new()), group_id=group_id, revision_no=revision_no,
            pin_id=settings.pin_id, gateway_model=settings.gateway_model, billing=settings.billing,
            input_per_mtok_usd=input_per_mtok_usd, output_per_mtok_usd=output_per_mtok_usd,
            strategy=settings.strategy, created_at=T0, created_by=actor_uid, members=stored)
        self.revisions[record.group_revision_id] = record
        self.writes.append("revision")
        return record

    def get_revision(self, session, group_revision_id):
        return self.revisions.get(group_revision_id)

    def list_revisions(self, session, group_id):
        return sorted((r for r in self.revisions.values() if r.group_id == group_id),
                      key=lambda r: -r.revision_no)

    def current_revisions(self, session, group_ids):
        return {gid: self.list_revisions(session, gid)[0] for gid in group_ids
                if any(r.group_id == gid for r in self.revisions.values())}

    # -- rules
    def lock_rule(self, session, work_kind):
        pass

    def insert_rule(self, session, *, work_kind, group_revision_id, actor_uid):
        number = 1 + sum(1 for rule in self.rules if rule.work_kind == work_kind)
        rule = RuleRecord(
            rule_revision_id=str(ExecutorRoutingRuleRevisionId.new()), work_kind=work_kind, rule_no=number,
            group_revision_id=group_revision_id, group_id=self.revisions[group_revision_id].group_id,
            set_at=T0, set_by=actor_uid)
        self.rules.append(rule)
        self.writes.append("rule")
        return rule

    def get_rule(self, session, rule_revision_id):
        return next((rule for rule in self.rules if rule.rule_revision_id == rule_revision_id), None)

    def current_rules(self, session):
        latest: dict[str, RuleRecord] = {}
        for rule in self.rules:
            if rule.work_kind not in latest or rule.rule_no > latest[rule.work_kind].rule_no:
                latest[rule.work_kind] = rule
        return [latest[kind] for kind in sorted(latest)]

    def current_rule(self, session, work_kind):
        return next((rule for rule in self.current_rules(session) if rule.work_kind == work_kind), None)

    def current_mode(self, session):
        return self.mode

    def pending_count(self, session, group_id):
        return self.pending

    def advance_rotation(self, session, group_id):
        self.rotation += 1
        return self.rotation


class World:
    """Two pull connections of one model and the stand-ins around them."""

    def __init__(self, *, replay: dict[str, Any] | None = None, second: dict[str, Any] | None = None) -> None:
        self.executors = FakeExecutors()
        self.groups = FakeGroups(self.executors)
        self.ledger = FakeLedger(replay)
        self.journal = Journal()
        self.first = self.executors.connect(C1, R1)
        self.second = self.executors.connect(C2, R2, **(second or {}))

    @property
    def members(self) -> list[MemberRequest]:
        return [MemberRequest(C1, R1), MemberRequest(C2, R2)]

    def create(self, *, name: str = "Pool", members=None, settings=SONNET, roles=("admin",), key: str = "k1",
               pins=PINS, actor: str = ADMIN):
        return create_group(
            SESSION, display_name=name, settings=settings, members=self.members if members is None else members,
            pins=pins, roles=roles, idempotency_key=key, actor_uid=actor, repository=self.executors,
            groups=self.groups, commands=self.ledger, journal=self.journal)

    def revise(self, group_id: str, *, members=None, settings=SONNET, roles=("admin",), key: str = "k2"):
        return revise_group(
            SESSION, group_id=group_id, settings=settings, members=self.members if members is None else members,
            pins=PINS, roles=roles, idempotency_key=key, actor_uid=ADMIN, repository=self.executors,
            groups=self.groups, commands=self.ledger, journal=self.journal)

    def archive(self, group_id: str, *, roles=("admin",), key: str = "k3"):
        return archive_group(
            SESSION, group_id=group_id, roles=roles, idempotency_key=key, actor_uid=ADMIN,
            groups=self.groups, commands=self.ledger, journal=self.journal)

    def rule(self, work_kind: str, group_revision_id: str, *, roles=("admin",), key: str = "k4"):
        return set_routing_rule(
            SESSION, work_kind=work_kind, group_revision_id=group_revision_id, roles=roles,
            idempotency_key=key, actor_uid=ADMIN, groups=self.groups, commands=self.ledger,
            journal=self.journal)

    def nothing_written(self) -> bool:
        return (self.groups.writes == [] and self.journal.events == [] and self.ledger.succeeded == [])


# --- item 1: a two-member group of one model -------------------------------------------------------------------


def test_an_administrator_creates_a_two_member_group_of_one_model() -> None:
    world = World()
    summary = world.create()

    assert summary.group.display_name == "Pool" and summary.group.archived_at is None
    revision = summary.current_revision
    assert (revision.revision_no, revision.pin_id, revision.gateway_model, revision.billing, revision.strategy) == (
        1, "claude-sonnet-5", "claude-sonnet-5", "not_metered", "least_loaded")
    assert [(m.connection_id, m.connection_revision_id, m.tie_break_order) for m in revision.members] == [
        (C1, R1, None), (C2, R2, None)]
    assert summary.routed_work_kinds == ()
    assert world.groups.writes == ["group", "revision"]


def test_the_rates_are_the_provider_locks_for_the_pin_and_not_the_requests() -> None:
    sonnet = World().create().current_revision
    assert (sonnet.input_per_mtok_usd, sonnet.output_per_mtok_usd) == (Decimal("3.0"), Decimal("15.0"))
    opus_world = World()
    opus_world.executors.revise(C1, R3, pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5")
    opus_world.executors.connect(C3, R4, pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5")
    opus = GroupSettings("claude-opus-5", "anthropic/claude-opus-5", "not_metered", "least_loaded")
    group = opus_world.create(settings=opus, members=[MemberRequest(C1, R3), MemberRequest(C3, R4)]).current_revision
    assert (group.input_per_mtok_usd, group.output_per_mtok_usd) == (Decimal("15.0"), Decimal("75.0"))


def test_the_member_connections_are_locked_in_ascending_order_before_they_are_read() -> None:
    world = World()
    world.create(members=[MemberRequest(C2, R2), MemberRequest(C1, R1)])
    assert world.groups.locked_connections == [[C1, C2]]


def test_the_command_is_recorded_under_the_kept_type_and_journaled_with_identities_only() -> None:
    world = World()
    summary = world.create()
    assert world.ledger.began == [("create_executor_group", "k1")]
    assert world.ledger.succeeded == [{
        "group_id": summary.group.group_id,
        "group_revision_id": summary.current_revision.group_revision_id}]
    (event,) = world.journal.events
    assert event["event_type"] == "executor.group_created" and event["aggregate_type"] == "ExecutorGroup"
    assert event["aggregate_id"] == summary.group.group_id
    assert event["payload"] == {
        "revision_id": summary.current_revision.group_revision_id, "revision_no": 1, "actor_uid": ADMIN}


@pytest.mark.parametrize(("member_setting", "value", "field", "constraint"), [
    ("pin_id", "claude-opus-5", "pin_id", "member_pin_mismatch"),
    ("gateway_model", "claude-sonnet-5-preview", "gateway_model", "member_model_mismatch"),
    ("billing", "metered", "billing", "member_billing_mismatch"),
])
def test_a_member_that_is_not_the_pin_the_model_or_the_billing_of_the_group_is_refused_and_nothing_is_written(
    member_setting: str, value: str, field: str, constraint: str,
) -> None:
    world = World(second={member_setting: value})
    error = refusal(world.create)
    assert detail(error) == ("validation_failed", {"field": field, "constraint": constraint})
    assert world.nothing_written(), "a refused group leaves no row, no event and no recorded outcome"


def test_a_group_whose_own_settings_are_not_the_members_is_refused_for_every_member() -> None:
    world = World()
    error = refusal(lambda: world.create(settings=replace(SONNET, billing="metered")))
    assert detail(error) == ("validation_failed", {"field": "billing", "constraint": "member_billing_mismatch"})
    assert world.nothing_written()


def test_the_refusal_names_a_field_and_a_classifier_and_never_a_value() -> None:
    world = World(second={"gateway_model": "secret-looking/model-name"})
    error = refusal(world.create)
    assert "secret-looking" not in repr(error.detail_fields) and "secret-looking" not in str(error)


def test_a_duplicate_member_is_refused() -> None:
    world = World()
    error = refusal(lambda: world.create(members=[MemberRequest(C1, R1), MemberRequest(C1, R1)]))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "member_repeated"})
    assert world.nothing_written() and world.ledger.began == [], "a malformed request is refused before the key is claimed"


def test_a_tie_break_order_given_twice_is_refused() -> None:
    world = World()
    members = [MemberRequest(C1, R1, 1), MemberRequest(C2, R2, 1)]
    error = refusal(lambda: world.create(members=members))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "tie_break_order_repeated"})


def test_a_group_of_one_member_is_a_group() -> None:
    summary = World().create(members=[MemberRequest(C1, R1)])
    assert [m.connection_id for m in summary.current_revision.members] == [C1]


@pytest.mark.parametrize("count", [0, 17])
def test_a_group_has_one_to_sixteen_members_and_no_other_number(count: int) -> None:
    world = World()
    members = [MemberRequest(f"exc_{i:026d}", f"excr_{i:026d}") for i in range(count)]
    error = refusal(lambda: world.create(members=members))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "range"})


def test_a_revision_that_is_not_the_connections_current_one_is_refused() -> None:
    world = World()
    world.executors.revise(C1, R3)                     # C1 now has a newer revision: R1 is no longer current
    error = refusal(lambda: world.create(members=[MemberRequest(C1, R1), MemberRequest(C2, R2)]))
    assert detail(error) == (
        "validation_failed", {"field": "members", "constraint": "member_revision_not_of_connection"})
    assert world.nothing_written()
    # The current one is accepted: the snapshot is what the connection is now.
    assert [m.connection_revision_id for m in
            world.create(members=[MemberRequest(C1, R3), MemberRequest(C2, R2)]).current_revision.members] == [R3, R2]


@pytest.mark.parametrize("named", [R2, "excr_01M2545JSD15ETSNNV904X99ZZ"])
def test_a_revision_of_another_connection_or_of_none_is_refused(named: str) -> None:
    world = World()
    error = refusal(lambda: world.create(members=[MemberRequest(C1, named), MemberRequest(C2, R2)]))
    assert detail(error) == (
        "validation_failed", {"field": "members", "constraint": "member_revision_not_of_connection"})
    assert world.nothing_written()


def test_an_unknown_connection_is_refused() -> None:
    world = World()
    error = refusal(lambda: world.create(members=[MemberRequest(C1, R1), MemberRequest(C3, R3)]))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "unknown_executor_connection"})
    assert world.nothing_written()


def test_an_archived_connection_is_a_conflict_and_not_a_member() -> None:
    world = World(second={})
    world.executors.connections[C2] = replace(world.executors.connections[C2], archived_at=T0, archived_by=ADMIN)
    error = refusal(world.create)
    assert detail(error) == ("conflict", {"conflict_reason": "connection_archived"})
    assert world.nothing_written()


def test_a_kind_this_release_does_not_serve_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World()
    monkeypatch.setattr(group_commands, "is_served", lambda connection, revision: connection.connection_id != C2)
    error = refusal(world.create)
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "member_kind_not_served"})
    assert world.nothing_written()


def test_a_pin_the_provider_lock_does_not_hold_is_refused_before_the_key_is_claimed() -> None:
    world = World()
    error = refusal(lambda: world.create(settings=replace(SONNET, pin_id="not-in-the-lock")))
    assert detail(error) == ("validation_failed", {"field": "pin_id", "constraint": "model_not_pinned"})
    assert world.ledger.began == [] and world.nothing_written()


def test_an_active_groups_name_is_taken_without_regard_to_case_and_free_again_after_the_archive() -> None:
    world = World()
    first = world.create(name="Pool", key="k1")
    error = refusal(lambda: world.create(name="  pOOL ", key="k1b"))
    assert detail(error) == ("conflict", {"conflict_reason": "group_name_in_use", "aggregate_type": "ExecutorGroup"})
    assert world.groups.writes == ["group", "revision"], "the second attempt wrote nothing"
    world.archive(first.group.group_id)
    assert world.create(name="pool", key="k1c").group.display_name == "pool"


@pytest.mark.parametrize(("raw", "constraint"), [
    (None, "type"), ("   ", "required"), ("a\x00b", "printable"), ("x" * 121, "max_length"),
])
def test_a_name_that_is_not_a_label_is_refused(raw: object, constraint: str) -> None:
    error = refusal(lambda: clean_display_name(raw))
    assert detail(error) == ("validation_failed", {"field": "display_name", "constraint": constraint})
    assert clean_display_name("  Pool  ") == "Pool" and clean_display_name("x" * 120) == "x" * 120


@pytest.mark.parametrize("raw", ["Gateway A / text_analysis", "a b", "a  b", "Пул моделей / text_analysis", "text_analysis (2)"])
def test_a_label_may_hold_spaces(raw: str) -> None:
    """The proposed names of a cut-over are ``<connection name> / <work kind>``: a space is part of a label.

    The unprintable class once held two ordinary spaces where the line and paragraph separators belong (the file lost
    the two characters), so every name of a cut-over, and every group named with a space, was refused as ``printable``.
    """
    assert clean_display_name(raw) == raw


@pytest.mark.parametrize("raw", ["a\u2028b", "a\u2029b", "a\x7fb", "a\x85b", "a\ud800b", "a\nb"])
def test_a_line_or_paragraph_separator_and_the_other_unprintable_characters_are_still_refused(raw: str) -> None:
    error = refusal(lambda: clean_display_name(raw))
    assert detail(error) == ("validation_failed", {"field": "display_name", "constraint": "printable"})


def test_only_an_administrator_creates_a_group_and_the_key_is_not_claimed_for_anybody_else() -> None:
    world = World()
    error = refusal(lambda: world.create(roles=("expert",)))
    assert error.code is ErrorCode.PERMISSION_DENIED and dict(error.detail_fields) == {"required_capability": "role:admin"}
    assert world.ledger.began == [] and world.nothing_written()


def test_an_identical_request_replays_the_group_and_writes_nothing() -> None:
    world = World()
    first = world.create()
    written, events = list(world.groups.writes), list(world.journal.events)
    world.ledger.replay = {"group_id": first.group.group_id}
    again = world.create()
    assert again.group.group_id == first.group.group_id
    assert world.groups.writes == written and world.journal.events == events


def fingerprint_of(**kwargs: Any) -> str:
    """What the ledger is asked to compare for one create. A fresh world each time, so the name is never taken."""
    world = World()
    world.create(key="same", **kwargs)
    return world.ledger.fingerprints[0]


def test_the_ledger_compares_the_members_by_connection_and_the_actor_who_spent_the_key() -> None:
    forward = [MemberRequest(C1, R1), MemberRequest(C2, R2)]
    assert fingerprint_of(members=forward) == fingerprint_of(members=list(reversed(forward))), (
        "the order the members were listed in is not a difference")
    assert fingerprint_of(members=[MemberRequest(C1, R1, 1), MemberRequest(C2, R2)]) != fingerprint_of(
        members=[MemberRequest(C1, R1, 2), MemberRequest(C2, R2)]), "a tie-break order is"
    assert fingerprint_of() != fingerprint_of(actor="usr_01M2545JSD15ETSNNV904X991M"), (
        "a key belongs to the actor who spent it")
    assert fingerprint_of(name="One") != fingerprint_of(name="Two")


def test_the_command_types_are_the_ones_the_product_purge_keeps() -> None:
    from scripts.recovery.product_purge import KEEP_COMMAND_TYPES

    world = World()
    group = world.create(key="k1")
    world.revise(group.group.group_id, key="k2")
    world.rule("text_analysis", group.current_revision.group_revision_id, key="k3")
    other = world.create(name="Other", key="k4")
    world.archive(other.group.group_id, key="k5")
    kinds = {kind for kind, _ in world.ledger.began}
    assert kinds == {
        "create_executor_group", "revise_executor_group", "set_executor_routing_rule", "archive_executor_group"}
    assert kinds <= set(KEEP_COMMAND_TYPES)


# --- item 2: revisions, rules, the archive ---------------------------------------------------------------------


def test_a_revision_is_added_and_the_earlier_one_is_kept_as_it_was() -> None:
    world = World()
    created = world.create()
    first = created.current_revision
    world.executors.revise(C1, R3)
    revised = world.revise(created.group.group_id, members=[MemberRequest(C1, R3), MemberRequest(C2, R2)])

    assert revised.current_revision.revision_no == 2
    assert revised.current_revision.group_revision_id != first.group_revision_id
    detail_ = group_detail(SESSION, created.group.group_id, world.groups)
    assert [r.revision_no for r in detail_.revisions] == [2, 1], "newest first"
    assert detail_.revisions[1] == first, "the earlier revision is unchanged"
    assert world.journal.types() == ["executor.group_created", "executor.group_revised"]
    assert world.journal.events[1]["payload"]["revision_no"] == 2


def test_a_revision_of_an_unchanged_group_is_still_a_revision() -> None:
    world = World()
    created = world.create()
    assert world.revise(created.group.group_id).current_revision.revision_no == 2


def test_a_revision_of_a_group_that_does_not_exist_is_not_found() -> None:
    world = World()
    error = refusal(lambda: world.revise(str(ExecutorGroupId.new())))
    assert detail(error) == ("not_found", {"aggregate_type": "ExecutorGroup"})
    assert world.nothing_written()


def test_a_revision_whose_member_does_not_fit_is_refused_and_adds_nothing() -> None:
    world = World(second={"billing": "metered"})
    group = world.create(members=[MemberRequest(C1, R1)])           # the first member alone is not mixed
    written = list(world.groups.writes)
    error = refusal(lambda: world.revise(group.group.group_id))     # now both members: one is metered
    assert detail(error) == ("validation_failed", {"field": "billing", "constraint": "member_billing_mismatch"})
    assert world.groups.writes == written


def test_an_archived_group_takes_no_revision() -> None:
    world = World()
    gid = world.create().group.group_id
    world.archive(gid)
    written = list(world.groups.writes)
    error = refusal(lambda: world.revise(gid))
    assert detail(error) == ("conflict", {"conflict_reason": "group_archived", "aggregate_type": "ExecutorGroup"})
    assert world.groups.writes == written


def test_archiving_is_soft_and_every_revision_and_member_stays_readable() -> None:
    world = World()
    created = world.create()
    gid, revision = created.group.group_id, created.current_revision
    archived = world.archive(gid)

    assert archived.group.archived_at is not None and archived.group.archived_by == ADMIN
    assert world.groups.get_revision(SESSION, revision.group_revision_id) == revision
    assert [r.group_revision_id for r in group_detail(SESSION, gid, world.groups).revisions] == [
        revision.group_revision_id]
    assert [(m.connection_id, m.connection_revision_id) for m in archived.current_revision.members] == [
        (C1, R1), (C2, R2)]
    assert [s.group.group_id for s in list_group_summaries(SESSION, world.groups)] == [gid]
    assert world.journal.types()[-1] == "executor.group_archived"


def test_archiving_an_archived_group_answers_it_as_it_stands_and_writes_nothing() -> None:
    world = World()
    gid = world.create().group.group_id
    first = world.archive(gid, key="a1")
    written, events = list(world.groups.writes), list(world.journal.events)
    again = world.archive(gid, key="a2")
    assert again.group.archived_at == first.group.archived_at
    assert world.groups.writes == written and world.journal.events == events


def test_a_group_a_rule_still_names_cannot_be_archived_until_the_rule_moves() -> None:
    world = World()
    first = world.create(name="First", key="g1")
    second = world.create(name="Second", key="g2")
    world.rule("text_analysis", first.current_revision.group_revision_id, key="r1")

    error = refusal(lambda: world.archive(first.group.group_id))
    assert detail(error) == ("conflict", {"conflict_reason": "group_routed", "aggregate_type": "ExecutorGroup"})
    assert world.groups.groups[first.group.group_id].archived_at is None
    assert group_summary(SESSION, first.group.group_id, world.groups).routed_work_kinds == ("text_analysis",)

    world.rule("text_analysis", second.current_revision.group_revision_id, key="r2")
    assert world.archive(first.group.group_id).group.archived_at is not None


def test_a_rule_is_set_per_work_kind_and_is_append_only() -> None:
    world = World()
    first = world.create(name="First", key="g1")
    second = world.create(name="Second", key="g2")
    one = world.rule("text_analysis", first.current_revision.group_revision_id, key="r1")
    other_kind = world.rule("comparison_report", first.current_revision.group_revision_id, key="r2")
    moved = world.rule("text_analysis", second.current_revision.group_revision_id, key="r3")

    assert (one.work_kind, one.rule_no, other_kind.work_kind, other_kind.rule_no, moved.rule_no) == (
        "text_analysis", 1, "comparison_report", 1, 2)
    assert len(world.groups.rules) == 3, "the earlier rule revision is still there"
    listing = list_routing_rules(SESSION, world.groups)
    assert [(r.work_kind, r.rule_revision_id) for r in listing.rules] == [
        ("comparison_report", other_kind.rule_revision_id), ("text_analysis", moved.rule_revision_id)]
    assert resolve_rule(SESSION, "text_analysis", world.groups) == moved
    assert resolve_rule(SESSION, "comparison_spec", world.groups) is None
    assert world.journal.types().count("executor.routing_rule_set") == 3


def test_naming_the_revision_that_is_already_current_appends_nothing() -> None:
    world = World()
    created = world.create()
    revision = created.current_revision.group_revision_id
    one = world.rule("text_analysis", revision, key="r1")
    events, writes = list(world.journal.events), list(world.groups.writes)
    again = world.rule("text_analysis", revision, key="r2")
    assert again == one
    assert world.groups.writes == writes and world.journal.events == events
    assert world.ledger.succeeded[-1] == {"rule_revision_id": one.rule_revision_id}


def test_a_rule_may_name_any_revision_of_an_active_group_and_not_only_the_current_one() -> None:
    world = World()
    created = world.create()
    first = created.current_revision.group_revision_id
    world.revise(created.group.group_id)
    assert world.rule("text_analysis", first, key="r1").group_revision_id == first


def test_a_rule_is_refused_for_an_archived_groups_revision_for_an_unknown_one_and_for_a_work_kind_not_named() -> None:
    world = World()
    created = world.create()
    revision = created.current_revision.group_revision_id
    world.archive(created.group.group_id)
    written = list(world.groups.writes)

    archived = refusal(lambda: world.rule("text_analysis", revision))
    assert detail(archived) == ("conflict", {"conflict_reason": "group_archived", "aggregate_type": "ExecutorGroup"})
    unknown = refusal(lambda: world.rule("text_analysis", str(ExecutorGroupRevisionId.new())))
    assert unknown.code is ErrorCode.NOT_FOUND and dict(unknown.detail_fields) == {
        "aggregate_type": "ExecutorGroupRevision"}
    began = len(world.ledger.began)
    kind = refusal(lambda: world.rule("not_a_work_kind", revision))
    assert detail(kind) == ("validation_failed", {"field": "work_kind", "constraint": "enum"})
    assert len(world.ledger.began) == began, "refused before the key is claimed"
    assert world.groups.writes == written


def test_the_six_work_kinds_are_the_only_ones_a_rule_may_name() -> None:
    for kind in WORK_KINDS:
        refuse_work_kind(kind)
    assert len(WORK_KINDS) == 6
    for kind in ("", "text", "TEXT_ANALYSIS"):
        assert refusal(lambda: refuse_work_kind(kind)).code is ErrorCode.VALIDATION_FAILED


def test_a_repeated_rule_key_returns_the_rule_that_command_recorded() -> None:
    world = World()
    revision = world.create().current_revision.group_revision_id
    one = world.rule("text_analysis", revision, key="r1")
    world.ledger.replay = {"rule_revision_id": one.rule_revision_id}
    writes = list(world.groups.writes)
    assert world.rule("text_analysis", revision, key="r1") == one
    assert world.groups.writes == writes


def test_the_routing_mode_is_legacy_until_a_journal_event_says_otherwise() -> None:
    world = World()
    assert list_routing_rules(SESSION, world.groups).routing_mode == ModeState()
    assert ModeState().mode == "legacy" and ModeState().mode_event_id is None
    world.groups.mode = ModeState("rules", "exrm_01M2545JSD15ETSNNV904X991K", T0, ADMIN)
    assert list_routing_rules(SESSION, world.groups).routing_mode.mode == "rules"


def test_every_event_is_executor_prefixed_and_carries_identities_and_classifiers_only() -> None:
    world = World()
    created = world.create()
    world.revise(created.group.group_id)
    world.rule("text_analysis", created.current_revision.group_revision_id)
    other = world.create(name="Other", key="k9")
    world.archive(other.group.group_id, key="k10")
    assert world.journal.types() == [
        "executor.group_created", "executor.group_revised", "executor.routing_rule_set",
        "executor.group_created", "executor.group_archived"]
    for event in world.journal.events:
        assert set(event["payload"]) <= _SAFE_KEYS, event
        assert all(isinstance(value, (str, int, bool, type(None))) for value in event["payload"].values())
        assert event["payload"]["actor_uid"] == ADMIN


def test_the_validation_of_a_request_needs_no_row() -> None:
    members = [MemberRequest(C1, R1), MemberRequest(C2, R2)]
    refuse_settings(SONNET, members, pinned_model_ids={"claude-sonnet-5"})
    for settings, constraint, field in [
        (replace(SONNET, billing="free"), "enum", "billing"),
        (replace(SONNET, strategy="round_robin"), "enum", "strategy"),
    ]:
        error = refusal(lambda: refuse_settings(settings, members, pinned_model_ids={"claude-sonnet-5"}))
        assert detail(error) == ("validation_failed", {"field": field, "constraint": constraint})
    out_of_range = [MemberRequest(C1, R1, 17), MemberRequest(C2, R2)]
    error = refusal(lambda: refuse_settings(SONNET, out_of_range, pinned_model_ids={"claude-sonnet-5"}))
    assert detail(error) == ("validation_failed", {"field": "members", "constraint": "range"})


# --- item 19: the capacity of a group ---------------------------------------------------------------------------


def capacity_world() -> tuple[World, str]:
    world = World()
    return world, world.create().group.group_id


def read_capacity(world: World, group_id: str):
    return group_capacity(SESSION, group_id, world.executors, world.groups)


def test_the_capacity_of_a_group_is_the_sum_of_its_members_and_every_member_is_eligible_when_healthy() -> None:
    world, gid = capacity_world()
    world.executors.occupy(C1, runs=1)
    world.executors.occupy(C2, calls=1)
    world.groups.pending = 3
    answer = read_capacity(world, gid)

    assert (answer.capacity, answer.used, answer.waiting) == (4, 2, 3)
    assert answer.group_revision_id == world.groups.current_revisions(SESSION, [gid])[gid].group_revision_id
    assert [(m.connection_id, m.snapshot_revision_id, m.current_revision_id, m.eligible, m.issue)
            for m in answer.members] == [(C1, R1, R1, True, None), (C2, R2, R2, True, None)]
    assert [(m.occupancy.capacity, m.occupancy.active_runs, m.occupancy.active_calls) for m in answer.members] == [
        (2, 1, 0), (2, 0, 1)]
    assert world.executors.swept == 1, "the read ends the probes nobody can still be running"


def test_a_member_at_capacity_is_not_eligible_but_is_still_counted_in_the_groups_capacity() -> None:
    world, gid = capacity_world()
    world.executors.occupy(C1, runs=2)
    answer = read_capacity(world, gid)
    first = answer.members[0]
    assert (first.eligible, first.issue) == (False, "at_capacity")
    assert (answer.capacity, answer.used) == (4, 2)


def test_a_member_whose_connection_has_a_newer_revision_is_out_of_service_and_not_counted() -> None:
    world, gid = capacity_world()
    world.executors.revise(C1, R3)
    world.executors.occupy(C1, runs=1)
    answer = read_capacity(world, gid)
    first = answer.members[0]
    assert (first.snapshot_revision_id, first.current_revision_id, first.issue) == (R1, R3, "revision_changed")
    assert (answer.capacity, answer.used) == (2, 0), "only the member still in service counts"


@pytest.mark.parametrize(("what", "issue"), [
    ("archive", "connection_archived"),
    ("unprobed", "probe_not_ok"),
    ("offline", "runner_offline"),
])
def test_each_reason_a_member_would_not_be_chosen_is_reported(what: str, issue: str) -> None:
    world, gid = capacity_world()
    if what == "archive":
        world.executors.connections[C1] = replace(world.executors.connections[C1], archived_at=T0, archived_by=ADMIN)
    elif what == "unprobed":
        world.executors.probe_ok[R1] = False
    else:
        world.executors.online.discard(C1)
    answer = read_capacity(world, gid)
    assert (answer.members[0].eligible, answer.members[0].issue) == (False, issue)
    assert (answer.members[1].eligible, answer.members[1].issue) == (True, None)


def test_a_kind_this_release_does_not_serve_is_reported_not_served(monkeypatch: pytest.MonkeyPatch) -> None:
    world, gid = capacity_world()
    monkeypatch.setattr(group_commands, "is_served", lambda connection, revision: connection.connection_id != C1)
    assert read_capacity(world, gid).members[0].issue == "not_served"


def test_when_several_reasons_apply_the_first_of_the_enumeration_is_the_one_reported() -> None:
    world, gid = capacity_world()
    world.executors.revise(C1, R3, probed=False)            # revision_changed, and the new one is not probed
    world.executors.online.discard(C1)                       # and its runner is gone
    world.executors.occupy(C1, runs=2)                       # and it is full
    assert read_capacity(world, gid).members[0].issue == "revision_changed"


def test_an_unknown_group_has_no_capacity_and_no_detail() -> None:
    world = World()
    missing = str(ExecutorGroupId.new())
    assert refusal(lambda: read_capacity(world, missing)).code is ErrorCode.NOT_FOUND
    assert refusal(lambda: group_summary(SESSION, missing, world.groups)).code is ErrorCode.NOT_FOUND
    assert refusal(lambda: group_detail(SESSION, missing, world.groups)).code is ErrorCode.NOT_FOUND


def test_the_list_shows_active_groups_first_each_with_its_current_revision_and_routed_kinds() -> None:
    world = World()
    older = world.create(name="Older", key="g1")
    newer = world.create(name="Newer", key="g2")
    world.rule("text_analysis", newer.current_revision.group_revision_id, key="r1")
    world.archive(older.group.group_id, key="a1")
    summaries = list_group_summaries(SESSION, world.groups)
    assert [s.group.display_name for s in summaries] == ["Newer", "Older"]
    assert summaries[0].routed_work_kinds == ("text_analysis",) and summaries[1].routed_work_kinds == ()
    assert all(s.current_revision.revision_no == 1 for s in summaries)


# --- a revision's membership is closed when the revision is made -----------------------------------------------


def test_a_revision_is_written_with_the_members_of_the_request_and_no_others() -> None:
    """``revise_group`` hands the repository the members of *this* request -- the revision declares their number, so
    a revision cannot inherit the previous one's members or keep a different count."""
    world = World()
    created = world.create()
    world.revise(created.group.group_id, members=[MemberRequest(C1, R1)])
    assert world.groups.member_counts == [2, 1]
    assert [len(r.members) for r in world.groups.list_revisions(SESSION, created.group.group_id)] == [1, 2]


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_Result":
        return self

    def one(self) -> dict[str, Any]:
        return self._rows[0]

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class RecordingSession:
    """Just enough of a session for ``GroupRepository.insert_revision``: it keeps every statement in order, answers
    the revision insert with the row it was given and answers the read of the members with the members written."""

    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []
        self.members: list[dict[str, Any]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql, bound = str(statement), dict(params or {})
        self.statements.append((sql, bound))
        if sql.startswith("INSERT INTO executor_group_revision"):
            return _Result([{
                "group_revision_id": bound["id"], "group_id": bound["group_id"], "revision_no": bound["no"],
                "pin_id": bound["pin"], "gateway_model": bound["model"], "billing": bound["billing"],
                "input_per_mtok_usd": bound["rate_in"], "output_per_mtok_usd": bound["rate_out"],
                "strategy": bound["strategy"], "created_at": T0, "created_by": bound["actor"]}])
        if sql.startswith("INSERT INTO executor_group_member"):
            self.members.append({
                "group_revision_id": bound["revision"], "connection_id": bound["connection"],
                "connection_revision_id": bound["connection_revision"], "tie_break_order": bound["tie"]})
            return _Result([])
        return _Result(self.members)


@pytest.mark.parametrize("count", [1, 2, 16])
def test_the_repository_declares_exactly_the_number_of_members_it_then_writes(count: int) -> None:
    """The database refuses a member beyond ``member_count`` and a commit that holds fewer, so the count written with
    the revision must be the number of member rows that follow it in the same transaction -- never more, never less."""
    session = RecordingSession()
    members = [MemberRequest(f"exc_{index:026d}", f"excr_{index:026d}") for index in range(count)]
    stored = GroupRepository().insert_revision(
        session, group_id=str(ExecutorGroupId.new()), revision_no=1, settings=SONNET,  # type: ignore[arg-type]
        input_per_mtok_usd=Decimal("3"), output_per_mtok_usd=Decimal("15"), members=members, actor_uid=ADMIN)

    inserts = [(sql, bound) for sql, bound in session.statements if sql.startswith("INSERT")]
    (revision_sql, revision_bound), *member_inserts = inserts
    assert revision_sql.startswith("INSERT INTO executor_group_revision") and "member_count" in revision_sql
    assert revision_bound["member_count"] == count
    assert len(member_inserts) == count, "one member row per declared member, after the revision row"
    assert all(sql.startswith("INSERT INTO executor_group_member") for sql, _ in member_inserts)
    assert len(stored.members) == count
