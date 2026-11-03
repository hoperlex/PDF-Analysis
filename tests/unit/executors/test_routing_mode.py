"""`EXEC2-CUTOVER-01` (ADR-0026 decision 17): the cut-over preview, the confirmed cut-over, the rollback and the read-only
legacy routes (B3 section 11 items 15, 16 and 22).

No database: the repositories, the command ledger and the journal are stand-ins that record what they were asked and the
order they were asked in, so what matters is visible -- the preview writes nothing, a refusal writes nothing, the journal's
lock comes before the first group, the mode event comes last, a standby is never a member, a work kind left out of the
mapping gets no rule, a rollback touches no group and no rule. The same flows on real rows and through the served API are
``tests/integration/executors/test_cutover.py``. B3 section 11 is not in the repository; the numbers are the plan's table
(``EXEC2-PLAN.md`` section 8):

* item 15 -- **the preview**: the six work kinds in order; the primary of a route proposed as a one-member group of its
  *current* revision; a standby shown and not converted; an archived primary, a primary with no revision and a kind this
  release does not serve flagged ``incompatible`` with their reason; a work kind with no route ``no_route``; proposed names
  that are unique; a digest over exactly what is shown; nothing written;
* item 16 -- **the confirmed cut-over**: the digest and the mapping are required, a stale digest is ``conflict`` /
  ``preview_stale``, an entry that is not ``ready`` is refused; the groups (``member_count`` 1), the rules and the ``rules``
  event are made in that order after the journal's lock; a work kind left out gets no rule; an unchanged mode is refused; a
  repeat under the same key replays; under ``rules`` ``setExecutorRoute`` is ``conflict`` / ``routing_mode_rules`` before a
  key is claimed;
* item 22 -- **the rollback**: ``legacy`` takes neither field and writes one event; no group, revision, rule or admitted work
  is touched; a later cut-over appends new rules and proposes new names.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin
from auditmanager.executors import commands, routing_mode
from auditmanager.executors.groups import (
    GroupMemberRecord,
    GroupRecord,
    GroupRevisionRecord,
    ModeState,
    RuleRecord,
)
from auditmanager.executors.model import (
    WORK_KINDS,
    ConnectionRecord,
    RevisionRecord,
    RevisionSettings,
    RouteRecord,
)
from auditmanager.executors.routing_mode import (
    DIGEST_DOMAIN,
    MappingEntry,
    classify_route,
    ensure_legacy_routing,
    preview_digest_of,
    preview_routing,
    propose_name,
    set_routing_mode,
)
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.jobs.events import _SAFE_KEYS
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    ExecutorGroupId,
    ExecutorGroupRevisionId,
    ExecutorRoutingModeEventId,
    ExecutorRoutingRuleRevisionId,
)

ROOT = Path(__file__).resolve().parents[3]
T0 = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
OTHER = "usr_01M2545JSD15ETSNNV904X991M"
C1, C2, C3, C4 = (f"exc_01M2545JSD15ETSNNV904X991{tail}" for tail in "ABCD")
R1, R2, R3, R4, R1B = (f"excr_01M2545JSD15ETSNNV904X991{tail}" for tail in "ABCDE")
SESSION = object()
_DEFAULT: Any = object()
PINS = [ModelPin("claude-sonnet-5", 3.0, 15.0), ModelPin("claude-opus-5", 15.0, 75.0)]


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
    """The command ledger with its memory: a key spent with a payload replays that payload's outcome, and with another
    payload is the ledger's own ``idempotency_key_reuse``. A refusal in a real transaction takes its key back; the tests
    that reuse a key after a refusal call :meth:`rollback`."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str], dict[str, Any]] = {}
        self.began: list[tuple[str, str]] = []

    def begin(self, session, *, command_type, idempotency_key, fingerprint):
        slot = (command_type, str(idempotency_key))
        self.began.append(slot)
        if slot in self.records:
            record = self.records[slot]
            if record["fingerprint"] != str(fingerprint):
                raise DomainError(ErrorCode.IDEMPOTENCY_KEY_REUSE, command_type=command_type)
            return CommandReplay(command_id=record["id"], outcome=record["outcome"])  # type: ignore[arg-type]
        command_id = f"cmd_{len(self.records) + 1}"
        self.records[slot] = {"id": command_id, "fingerprint": str(fingerprint), "outcome": None}
        return CommandStarted(command_id=command_id)  # type: ignore[arg-type]

    def succeed(self, session, command_id, outcome) -> None:
        for record in self.records.values():
            if record["id"] == command_id:
                record["outcome"] = dict(outcome)

    def rollback(self) -> None:
        self.records = {slot: record for slot, record in self.records.items() if record["outcome"] is not None}

    def fingerprints(self) -> list[str]:
        return [record["fingerprint"] for record in self.records.values()]


class Journal:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def __call__(self, session, *, event_type, aggregate_type, aggregate_id, payload=None, **_) -> None:
        self.events.append({"event_type": event_type, "aggregate_type": aggregate_type,
                            "aggregate_id": aggregate_id, "payload": dict(payload or {})})

    def types(self) -> list[str]:
        return [event["event_type"] for event in self.events]


class FakeExecutors:
    """``ExecutorRepository`` in memory: connections, their revisions and the legacy routes."""

    def __init__(self) -> None:
        self.connections: dict[str, ConnectionRecord] = {}
        self.revisions: dict[str, RevisionRecord] = {}
        self.chain: dict[str, list[str]] = {}
        self.routes: dict[str, RouteRecord] = {}
        self.route_writes: list[str] = []

    def connect(
        self, connection_id: str, revision_id: str | None, *, name: str, kind: str = "pull", archived: bool = False,
        **settings: Any,
    ) -> None:
        self.connections[connection_id] = ConnectionRecord(
            connection_id=connection_id, kind=kind, display_name=name, created_at=T0, created_by=ADMIN,
            archived_at=T0 if archived else None, archived_by=ADMIN if archived else None)
        if revision_id is not None:
            self.revise(connection_id, revision_id, **settings)

    def revise(self, connection_id: str, revision_id: str, **settings: Any) -> None:
        chain = self.chain.setdefault(connection_id, [])
        self.revisions[revision_id] = RevisionRecord(
            revision_id=revision_id, connection_id=connection_id, revision_no=len(chain) + 1, created_at=T0,
            created_by=ADMIN, settings=pull_settings(**settings))
        chain.append(revision_id)

    def route(self, work_kind: str, primary: str, standby: str | None = None) -> None:
        self.routes[work_kind] = RouteRecord(
            route_event_id=f"exre_{work_kind}", work_kind=work_kind, route_no=1, primary_connection_id=primary,
            standby_connection_id=standby, set_at=T0, set_by=ADMIN)

    # -- the ExecutorRepository surface the cut-over and the group commands use
    def current_routes(self, session):
        return [self.routes[kind] for kind in sorted(self.routes)]

    def get_connection(self, session, connection_id, *, lock=False):
        return self.connections.get(connection_id)

    def get_revision(self, session, revision_id):
        return self.revisions.get(revision_id)

    def current_revisions(self, session, connection_ids):
        return {cid: self.revisions[self.chain[cid][-1]] for cid in connection_ids if self.chain.get(cid)}

    def lock_route(self, session, work_kind):
        self.route_writes.append(f"lock:{work_kind}")

    def append_route(self, session, **_):
        self.route_writes.append("append")
        raise AssertionError("a route was written")


class FakeGroups:
    """``GroupRepository`` in memory. ``calls`` is the order of every lock and write, so the order can be asserted."""

    def __init__(self, executors: FakeExecutors) -> None:
        self.executors = executors
        self.groups: dict[str, GroupRecord] = {}
        self.revisions: dict[str, GroupRevisionRecord] = {}
        self.rules: list[RuleRecord] = []
        self.mode = ModeState()
        self.events: list[dict[str, Any]] = []
        self.calls: list[str] = []
        self.locked: list[list[str]] = []
        self.member_counts: list[int] = []

    # -- the routing mode
    def lock_mode_journal(self, session):
        self.calls.append("lock_mode")

    def current_mode(self, session):
        return self.mode

    def insert_mode_event(self, session, *, mode, preview_digest, mapping, actor_uid):
        # The CHECKs of ``executor_routing_mode_event`` (``ck_..._digest_shape`` and ``ck_..._mapping_shape``).
        assert (mode == "rules") == (preview_digest is not None)
        assert (mode == "rules" and 1 <= len(mapping) <= 6) or (mode == "legacy" and len(mapping) == 0)
        self.calls.append("insert_mode_event")
        number = len(self.events) + 1
        state = ModeState(mode, str(ExecutorRoutingModeEventId.new()), T0 + timedelta(minutes=number), actor_uid)
        self.events.append({"event_no": number, "mode": mode, "preview_digest": preview_digest,
                            "mapping": [dict(entry) for entry in mapping], "changed_by": actor_uid,
                            "mode_event_id": state.mode_event_id})
        self.mode = state
        return state, number

    # -- groups
    def active_group_names(self, session):
        self.calls.append("active_group_names")
        return {g.display_name.lower() for g in self.groups.values() if g.archived_at is None}

    def lock_name(self, session, display_name):
        self.calls.append("lock_name")

    def name_in_use(self, session, display_name):
        return display_name.lower() in {g.display_name.lower() for g in self.groups.values() if g.archived_at is None}

    def insert_group(self, session, *, display_name, actor_uid):
        self.calls.append("insert_group")
        record = GroupRecord(
            group_id=str(ExecutorGroupId.new()), display_name=display_name, rotation_cursor=0, created_at=T0,
            created_by=actor_uid)
        self.groups[record.group_id] = record
        return record

    def get_group(self, session, group_id, *, lock=False):
        return self.groups.get(group_id)

    def lock_connections(self, session, connection_ids):
        self.calls.append("lock_connections")
        self.locked.append(list(connection_ids))
        return {cid for cid in connection_ids if cid in self.executors.connections}

    # -- revisions
    def next_revision_no(self, session, group_id):
        return 1 + sum(1 for r in self.revisions.values() if r.group_id == group_id)

    def insert_revision(
        self, session, *, group_id, revision_no, settings, input_per_mtok_usd, output_per_mtok_usd, members, actor_uid,
    ):
        self.calls.append("insert_revision")
        self.member_counts.append(len(members))
        record = GroupRevisionRecord(
            group_revision_id=str(ExecutorGroupRevisionId.new()), group_id=group_id, revision_no=revision_no,
            pin_id=settings.pin_id, gateway_model=settings.gateway_model, billing=settings.billing,
            input_per_mtok_usd=input_per_mtok_usd, output_per_mtok_usd=output_per_mtok_usd,
            strategy=settings.strategy, created_at=T0, created_by=actor_uid,
            members=tuple(GroupMemberRecord(m.connection_id, m.connection_revision_id, m.tie_break_order)
                          for m in members))
        self.revisions[record.group_revision_id] = record
        return record

    def get_revision(self, session, group_revision_id):
        return self.revisions.get(group_revision_id)

    def current_revisions(self, session, group_ids):
        found = {}
        for gid in group_ids:
            mine = [r for r in self.revisions.values() if r.group_id == gid]
            if mine:
                found[gid] = max(mine, key=lambda r: r.revision_no)
        return found

    # -- rules
    def lock_rule(self, session, work_kind):
        self.calls.append(f"lock_rule:{work_kind}")

    def insert_rule(self, session, *, work_kind, group_revision_id, actor_uid):
        self.calls.append(f"insert_rule:{work_kind}")
        number = 1 + sum(1 for rule in self.rules if rule.work_kind == work_kind)
        rule = RuleRecord(
            rule_revision_id=str(ExecutorRoutingRuleRevisionId.new()), work_kind=work_kind, rule_no=number,
            group_revision_id=group_revision_id, group_id=self.revisions[group_revision_id].group_id, set_at=T0,
            set_by=actor_uid)
        self.rules.append(rule)
        return rule

    def current_rules(self, session):
        latest: dict[str, RuleRecord] = {}
        for rule in self.rules:
            if rule.work_kind not in latest or rule.rule_no > latest[rule.work_kind].rule_no:
                latest[rule.work_kind] = rule
        return [latest[kind] for kind in sorted(latest)]

    def current_rule(self, session, work_kind):
        return next((rule for rule in self.current_rules(session) if rule.work_kind == work_kind), None)

    # -- what a refusal must not have changed
    def written(self) -> tuple[int, int, int, int]:
        return len(self.groups), len(self.revisions), len(self.rules), len(self.events)


class World:
    """Four ``pull`` connections of one model and the stand-ins around them.

    ``C1`` and ``C2`` are ready, ``C3`` is archived, ``C4`` has no revision. Nothing is routed until a test routes it."""

    def __init__(self) -> None:
        self.executors = FakeExecutors()
        self.groups = FakeGroups(self.executors)
        self.ledger = FakeLedger()
        self.journal = Journal()
        self.executors.connect(C1, R1, name="Gateway A")
        self.executors.connect(C2, R2, name="Gateway B")
        self.executors.connect(C3, R3, name="Gateway C", archived=True)
        self.executors.connect(C4, None, name="Gateway D")

    def route_all(self) -> None:
        """Every work kind on a ready primary: the first three on ``C1`` and the rest on ``C2``."""
        for index, kind in enumerate(WORK_KINDS):
            self.executors.route(kind, C1 if index < 3 else C2)

    def preview(self, *, roles=("admin",)):
        return preview_routing(SESSION, roles=roles, repository=self.executors, groups=self.groups)

    def mapping(self, preview=None, *kinds: str) -> list[MappingEntry]:
        """The administrator's confirmation of the proposal as shown: each named kind (all ready ones when none is
        named) under the name proposed for it."""
        shown = preview or self.preview()
        return [MappingEntry(item.work_kind, item.proposed_group_name or "?") for item in shown.items
                if item.status == "ready" and (not kinds or item.work_kind in kinds)]

    def set_mode(
        self, mode: str, *, digest: Any = _DEFAULT, mapping: Any = _DEFAULT, key: str = "k1", roles=("admin",),
        actor: str = ADMIN,
    ):
        """Without ``digest`` and ``mapping``: under ``rules`` the digest of the preview as it stands now and the whole
        proposal under the names proposed; under ``legacy`` neither is sent. What a test names is sent as it is,
        ``None`` included. The recorded calls are cleared just before the command, so they are the command's own."""
        shown = self.preview() if mode == "rules" and _DEFAULT in (digest, mapping) else None
        if digest is _DEFAULT:
            digest = None if shown is None else shown.preview_digest
        if mapping is _DEFAULT:
            mapping = None if shown is None else self.mapping(shown)
        self.groups.calls.clear()
        return set_routing_mode(
            SESSION, mode=mode, preview_digest=digest, mapping=mapping, pins=PINS, roles=roles,
            idempotency_key=key, actor_uid=actor, repository=self.executors, groups=self.groups,
            commands=self.ledger, journal=self.journal)


@pytest.fixture
def world() -> World:
    found = World()
    found.route_all()
    return found


# --- item 15: the preview ---------------------------------------------------------------------------------------


def test_the_preview_has_one_item_per_work_kind_in_the_order_of_the_enumeration(world: World) -> None:
    shown = world.preview()
    assert [item.work_kind for item in shown.items] == list(WORK_KINDS)
    assert shown.routing_mode == ModeState(), "the mode is legacy until the journal says otherwise"
    assert len(shown.items) == 6


def test_a_primary_is_proposed_as_a_one_member_group_of_its_current_revision(world: World) -> None:
    world.executors.revise(C1, R1B, pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5")
    first = world.preview().items[0]
    assert (first.status, first.primary_connection_id, first.incompatible_reason) == ("ready", C1, None)
    assert first.connection_revision_id == R1B, "the current revision, not the one the route was set under"
    assert (first.pin_id, first.gateway_model, first.billing) == ("claude-sonnet-5", "claude-sonnet-5", "not_metered")
    assert first.proposed_group_name == "Gateway A / text_analysis"
    assert world.preview().items[3].connection_revision_id == R2


def test_a_work_kind_with_no_route_is_no_route_and_carries_nothing_else() -> None:
    world = World()
    world.executors.route("text_analysis", C1)
    items = {item.work_kind: item for item in world.preview().items}
    assert items["text_analysis"].status == "ready"
    for kind in WORK_KINDS[1:]:
        assert items[kind].as_wire() == {"work_kind": kind, "status": "no_route"}


def test_a_standby_is_shown_and_never_converted(world: World) -> None:
    world.executors.route("text_analysis", C1, standby=C2)
    shown = world.preview()
    assert shown.items[0].standby_connection_id == C2 and shown.items[0].status == "ready"
    changed = world.set_mode("rules", mapping=world.mapping(shown, "text_analysis"))
    (group,) = changed.groups
    assert [member.connection_id for member in group.current_revision.members] == [C1]
    assert all(C2 not in [m.connection_id for m in revision.members] for revision in world.groups.revisions.values())


@pytest.mark.parametrize(("setup", "reason"), [
    ("archived", "connection_archived"), ("no_revision", "no_revision"), ("not_served", "kind_not_served")])
def test_a_route_that_cannot_become_a_group_is_incompatible_with_its_reason(
    setup: str, reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World()
    target = {"archived": C3, "no_revision": C4, "not_served": C1}[setup]
    world.executors.route("text_analysis", target, standby=C2)
    if setup == "not_served":
        monkeypatch.setattr(routing_mode, "is_served", lambda connection, revision: False)
    item = world.preview().items[0]
    assert (item.status, item.incompatible_reason) == ("incompatible", reason)
    assert item.primary_connection_id == target and item.standby_connection_id == C2
    assert item.proposed_group_name is None, "an incompatible route gets no proposal"


def test_the_reason_is_the_first_that_applies_archived_then_no_revision_then_not_served() -> None:
    route = RouteRecord("exre_1", "text_analysis", 1, C1, None, T0, ADMIN)
    archived = ConnectionRecord(C1, "pull", "A", T0, ADMIN, archived_at=T0, archived_by=ADMIN)
    live = replace(archived, archived_at=None, archived_by=None)
    revision = RevisionRecord(R1, C1, 1, T0, ADMIN, pull_settings())
    assert classify_route("text_analysis", route, archived, None, served=False).incompatible_reason == (
        "connection_archived")
    assert classify_route("text_analysis", route, live, None, served=False).incompatible_reason == "no_revision"
    assert classify_route("text_analysis", route, live, revision, served=False).incompatible_reason == (
        "kind_not_served")
    assert classify_route("text_analysis", route, live, revision, served=True).status == "ready"
    assert classify_route("text_analysis", None, None, None, served=False).status == "no_route"


def test_a_route_to_a_connection_that_does_not_exist_is_an_internal_error_and_not_a_flag() -> None:
    route = RouteRecord("exre_1", "text_analysis", 1, C1, None, T0, ADMIN)
    assert refusal(lambda: classify_route("text_analysis", route, None, None, served=False)).code is (
        ErrorCode.INTERNAL_ERROR)


def test_the_proposed_names_are_unique_among_the_proposals_and_the_active_groups(world: World) -> None:
    names = [item.proposed_group_name for item in world.preview().items]
    assert len({name.lower() for name in names}) == 6
    assert names[0] == "Gateway A / text_analysis" and names[1] == "Gateway A / comparison_pair_check"
    world.set_mode("rules")                                   # the six names are now held by active groups
    again = [item.proposed_group_name for item in world.preview().items]
    assert again == [f"{name} (2)" for name in names], "a taken name gets a number, the rest is the same"


def test_a_proposed_name_fits_a_label_and_a_name_that_is_not_one_is_not_echoed() -> None:
    long = "x" * 300
    name = propose_name(long, "comparison_sheet_changes", set())
    assert len(name) <= 120 and name.endswith(" / comparison_sheet_changes")
    taken = {name.lower()}
    second = propose_name(long, "comparison_sheet_changes", taken)
    assert len(second) <= 120 and second.endswith(" (2)") and second.lower() not in taken
    assert propose_name("a\x00b", "text_analysis", set()) == "text_analysis", "a name that is not a label is not echoed"


def test_the_digest_is_over_exactly_what_is_shown(world: World) -> None:
    shown = world.preview()
    body = json.dumps([item.as_wire() for item in shown.items], sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    assert shown.preview_digest == hashlib.sha256((DIGEST_DOMAIN + body).encode("utf-8")).hexdigest()
    assert shown.preview_digest == preview_digest_of(shown.items) == world.preview().preview_digest
    assert len(shown.preview_digest) == 64 and shown.preview_digest == shown.preview_digest.lower()
    wire = shown.items[0].as_wire()
    assert set(wire) == {"work_kind", "status", "primary_connection_id", "connection_revision_id", "pin_id",
                         "gateway_model", "billing", "proposed_group_name"}, "an absent field is absent, not null"


def test_the_digest_changes_with_every_thing_the_preview_shows(world: World) -> None:
    base = world.preview().preview_digest
    seen = {base}

    def digest_after(change) -> str:
        fresh = World()
        fresh.route_all()
        change(fresh)
        return fresh.preview().preview_digest

    for change in (
        lambda w: w.executors.revise(C1, R1B),                                     # a new revision of a primary
        lambda w: w.executors.route("comparison_report", C1),                      # another primary
        lambda w: w.executors.route("text_analysis", C1, standby=C2),              # a standby
        lambda w: w.executors.routes.pop("comparison_spec"),                       # a route removed
        lambda w: w.executors.connect(C2, None, name="Renamed"),                   # a name that is proposed
        lambda w: w.groups.groups.update({"exg_x": GroupRecord(                    # a name an active group holds
            "exg_x", "Gateway A / text_analysis", 0, T0, ADMIN)}),
    ):
        digest = digest_after(change)
        assert digest not in seen, "a change the preview shows must change the digest"
        seen.add(digest)
    assert len(seen) == 7


def test_the_digest_does_not_cover_the_routing_mode(world: World) -> None:
    before = world.preview().preview_digest
    world.groups.mode = ModeState("rules", "exrm_01M2545JSD15ETSNNV904X991K", T0, ADMIN)
    shown = world.preview()
    assert shown.preview_digest == before and shown.routing_mode.mode == "rules"


def test_the_preview_writes_nothing_and_takes_no_lock_of_the_journal(world: World) -> None:
    world.preview()
    assert world.groups.written() == (0, 0, 0, 0)
    assert world.journal.events == [] and world.ledger.began == [] and world.executors.route_writes == []
    assert not any(call.startswith(("insert", "lock")) for call in world.groups.calls), world.groups.calls


def test_only_an_administrator_previews(world: World) -> None:
    error = refusal(lambda: world.preview(roles=("expert",)))
    assert detail(error) == ("permission_denied", {"required_capability": "role:admin"})
    assert world.groups.calls == []


# --- the request ------------------------------------------------------------------------------------------------


DIGEST = "a" * 64
ENTRY = [MappingEntry("text_analysis", "Pool")]


@pytest.mark.parametrize(("mode", "digest", "mapping", "field", "constraint"), [
    ("sideways", None, None, "mode", "enum"),
    ("rules", None, ENTRY, "preview_digest", "preview_digest_required"),
    ("rules", "A" * 64, ENTRY, "preview_digest", "format"),
    ("rules", "a" * 63, ENTRY, "preview_digest", "format"),
    ("rules", DIGEST, None, "mapping", "mapping_required"),
    ("rules", DIGEST, [], "mapping", "mapping_required"),
    ("rules", DIGEST, [MappingEntry("text_analysis", "A"), MappingEntry("text_analysis", "B")], "mapping",
     "mapping_work_kind_repeated"),
    ("rules", DIGEST, [MappingEntry("not_a_kind", "A")], "work_kind", "enum"),
    ("rules", DIGEST, [MappingEntry("text_analysis", "  ")], "display_name", "required"),
    ("rules", DIGEST, [MappingEntry("text_analysis", "a\x00b")], "display_name", "printable"),
    ("rules", DIGEST, [MappingEntry("text_analysis", "x" * 121)], "display_name", "max_length"),
    ("legacy", DIGEST, None, "mapping", "mapping_not_accepted"),
    ("legacy", None, ENTRY, "mapping", "mapping_not_accepted"),
    ("legacy", None, [], "mapping", "mapping_not_accepted"),
])
def test_a_request_that_is_wrong_is_refused_before_a_key_is_claimed_or_a_row_read(
    world: World, mode, digest, mapping, field, constraint
) -> None:
    error = refusal(lambda: world.set_mode(mode, digest=digest, mapping=mapping))
    assert detail(error) == ("validation_failed", {"field": field, "constraint": constraint}), error
    assert world.ledger.began == [] and world.groups.calls == [] and world.groups.written() == (0, 0, 0, 0)


def test_one_name_for_two_work_kinds_is_a_conflict_without_regard_to_case(world: World) -> None:
    both = [MappingEntry("text_analysis", "Pool"), MappingEntry("comparison_spec", "POOL")]
    error = refusal(lambda: world.set_mode("rules", digest=DIGEST, mapping=both))
    assert detail(error) == ("conflict", {"conflict_reason": "group_name_in_use", "aggregate_type": "ExecutorGroup"})
    assert world.ledger.began == [] and world.groups.calls == []


def test_only_an_administrator_changes_the_mode_and_the_key_is_not_claimed_for_anybody_else(world: World) -> None:
    error = refusal(lambda: world.set_mode("rules", roles=("expert",)))
    assert detail(error) == ("permission_denied", {"required_capability": "role:admin"})
    assert world.ledger.began == [] and world.groups.calls == [] and world.groups.written() == (0, 0, 0, 0)


# --- item 16: the confirmed cut-over -------------------------------------------------------------------------------


def test_the_confirmed_cut_over_makes_a_one_member_group_and_a_rule_per_work_kind_and_the_rules_event(
    world: World,
) -> None:
    shown = world.preview()
    changed = world.set_mode("rules")

    assert changed.routing_mode.mode == "rules" and changed.routing_mode.changed_by == ADMIN
    assert [g.group.display_name for g in changed.groups] == [i.proposed_group_name for i in shown.items]
    assert world.groups.member_counts == [1] * 6, "every group is declared with one member"
    for item, summary in zip(shown.items, changed.groups, strict=True):
        revision = summary.current_revision
        assert (revision.revision_no, revision.strategy) == (1, "least_loaded")
        assert [(m.connection_id, m.connection_revision_id) for m in revision.members] == [
            (item.primary_connection_id, item.connection_revision_id)], "the primary's current revision, snapshotted"
        assert (revision.pin_id, revision.gateway_model, revision.billing) == (
            item.pin_id, item.gateway_model, item.billing)
        assert (revision.input_per_mtok_usd, revision.output_per_mtok_usd) == (3.0, 15.0), "the provider lock's rates"
        assert summary.routed_work_kinds == (item.work_kind,)
    assert [rule.work_kind for rule in changed.rules] == sorted(WORK_KINDS)
    assert {rule.group_revision_id for rule in changed.rules} == {
        g.current_revision.group_revision_id for g in changed.groups}
    assert world.groups.mode == changed.routing_mode


def test_the_rules_event_carries_the_digest_that_was_confirmed_and_what_the_change_created(world: World) -> None:
    shown = world.preview()
    changed = world.set_mode("rules", mapping=world.mapping(shown, "text_analysis", "comparison_report"))
    (event,) = world.groups.events
    assert (event["event_no"], event["mode"], event["preview_digest"], event["changed_by"]) == (
        1, "rules", shown.preview_digest, ADMIN)
    assert [entry["work_kind"] for entry in event["mapping"]] == ["text_analysis", "comparison_report"]
    created = {rule.work_kind: rule for rule in changed.rules}
    for entry in event["mapping"]:
        rule = created[entry["work_kind"]]
        assert set(entry) == {"work_kind", "group_id", "group_revision_id", "rule_revision_id"}
        assert (entry["group_id"], entry["group_revision_id"], entry["rule_revision_id"]) == (
            rule.group_id, rule.group_revision_id, rule.rule_revision_id)
    assert event["mode_event_id"] == changed.routing_mode.mode_event_id


def test_the_journals_lock_comes_first_the_connections_are_locked_ascending_and_the_mode_event_comes_last(
    world: World,
) -> None:
    world.executors.route("comparison_report", C2)           # two primaries, so the order is observable
    world.set_mode("rules", mapping=world.mapping(None, "text_analysis", "comparison_report"))
    calls = world.groups.calls
    first_lock_connections = calls.index("lock_connections")
    assert calls.index("lock_mode") == 0 < first_lock_connections < calls.index("insert_group")
    assert calls.count("lock_mode") == 1 and calls[-1] == "insert_mode_event" and calls.count("insert_mode_event") == 1
    assert world.groups.locked[0] == sorted(world.groups.locked[0]) == [C1, C2], (
        "the preview is recomputed under the lock of the primaries, ascending")
    assert all(ids == sorted(ids) for ids in world.groups.locked)
    # A group's rows come before its rule, and the rule of one work kind is made right after its group.
    order = [call for call in calls if call.startswith(("insert_", "lock_rule"))]
    assert order == ["insert_group", "insert_revision", "lock_rule:text_analysis", "insert_rule:text_analysis",
                     "insert_group", "insert_revision", "lock_rule:comparison_report", "insert_rule:comparison_report",
                     "insert_mode_event"]


def test_a_work_kind_left_out_of_the_mapping_gets_no_group_and_no_rule(world: World) -> None:
    changed = world.set_mode("rules", mapping=world.mapping(None, "text_analysis"))
    assert [rule.work_kind for rule in changed.rules] == ["text_analysis"] and len(changed.groups) == 1
    assert len(world.groups.groups) == 1
    for kind in WORK_KINDS[1:]:
        assert world.groups.current_rule(SESSION, kind) is None, "refused under rules, never routed by the legacy primary"
        assert world.executors.routes[kind].primary_connection_id in (C1, C2), "the legacy route is still there"


def test_the_cut_over_journals_each_group_each_rule_and_the_change_with_identities_and_classifiers_only(
    world: World,
) -> None:
    world.set_mode("rules", mapping=world.mapping(None, "text_analysis", "comparison_spec"))
    assert world.journal.types() == [
        "executor.group_created", "executor.routing_rule_set", "executor.group_created",
        "executor.routing_rule_set", "executor.routing_mode_changed"]
    for event in world.journal.events:
        assert event["event_type"].startswith("executor.")
        assert set(event["payload"]) <= _SAFE_KEYS, event
        assert all(isinstance(value, (str, int, bool, type(None))) for value in event["payload"].values())
        assert event["payload"]["actor_uid"] == ADMIN
    changed = world.journal.events[-1]
    assert changed["aggregate_type"] == "ExecutorRoutingModeEvent"
    assert changed["aggregate_id"] == world.groups.mode.mode_event_id
    assert changed["payload"] == {"from_state": "legacy", "to_state": "rules", "revision_no": 1, "actor_uid": ADMIN}


def test_the_command_is_recorded_under_the_type_the_product_purge_keeps(world: World) -> None:
    from scripts.recovery.product_purge import KEEP_COMMAND_TYPES

    world.set_mode("rules")
    world.set_mode("legacy", key="k2")
    assert {kind for kind, _ in world.ledger.began} == {"set_executor_routing_mode"} <= set(KEEP_COMMAND_TYPES)


def test_a_digest_that_is_not_the_one_now_computed_is_stale_and_nothing_is_made(world: World) -> None:
    shown = world.preview()
    world.executors.revise(C1, R1B)                           # the world moved after the proposal was shown
    error = refusal(lambda: world.set_mode("rules", digest=shown.preview_digest, mapping=world.mapping(shown)))
    assert detail(error) == ("conflict", {"conflict_reason": "preview_stale", "aggregate_type": "ExecutorRoutingModeEvent"})
    assert world.groups.written() == (0, 0, 0, 0) and world.journal.events == []
    assert "insert_group" not in world.groups.calls and "insert_mode_event" not in world.groups.calls


def test_a_route_set_after_the_proposal_makes_the_digest_stale(world: World) -> None:
    shown = world.preview()
    world.executors.route("text_analysis", C2)
    error = refusal(lambda: world.set_mode("rules", digest=shown.preview_digest, mapping=world.mapping(shown)))
    assert error.detail_fields["conflict_reason"] == "preview_stale"


def test_the_digest_is_held_before_the_mapping_so_a_stale_confirmation_is_a_conflict_whatever_it_names(
    world: World,
) -> None:
    shown = world.preview()
    world.executors.routes.pop("comparison_spec")
    stale = refusal(lambda: world.set_mode("rules", digest=shown.preview_digest, mapping=world.mapping(shown)))
    assert stale.code is ErrorCode.CONFLICT


@pytest.mark.parametrize("kind", ["comparison_spec", "comparison_report"])
def test_an_entry_for_a_work_kind_that_is_not_ready_is_refused(kind: str) -> None:
    world = World()
    world.executors.route("text_analysis", C1)
    world.executors.route("comparison_report", C3)            # archived primary: incompatible; comparison_spec: no route
    mapping = [MappingEntry("text_analysis", "One"), MappingEntry(kind, "Two")]
    error = refusal(lambda: world.set_mode("rules", mapping=mapping))
    assert detail(error) == ("validation_failed", {"field": "mapping", "constraint": "mapping_entry_not_ready"})
    assert world.groups.written() == (0, 0, 0, 0), "refused before the first group"


def test_when_no_work_kind_is_ready_there_is_nothing_to_confirm() -> None:
    world = World()
    world.executors.route("text_analysis", C3)
    error = refusal(lambda: world.set_mode("rules", mapping=[]))
    assert detail(error) == ("validation_failed", {"field": "mapping", "constraint": "mapping_required"})


def test_a_pin_the_provider_lock_no_longer_holds_is_refused_before_the_first_group(world: World) -> None:
    mapping = world.mapping()
    error = refusal(lambda: set_routing_mode(
        SESSION, mode="rules", preview_digest=world.preview().preview_digest, mapping=mapping,
        pins=[ModelPin("claude-opus-5", 15.0, 75.0)], roles=("admin",), idempotency_key="k1", actor_uid=ADMIN,
        repository=world.executors, groups=world.groups, commands=world.ledger, journal=world.journal))
    assert detail(error) == ("validation_failed", {"field": "pin_id", "constraint": "model_not_pinned"})
    assert world.groups.written() == (0, 0, 0, 0)


def test_a_name_an_active_group_holds_is_a_conflict_and_the_database_transaction_is_what_takes_back_the_earlier_groups(
    world: World,
) -> None:
    world.groups.groups["exg_held"] = GroupRecord("exg_held", "Taken", 0, T0, ADMIN)
    mapping = [MappingEntry("text_analysis", "Fresh"), MappingEntry("comparison_report", "taken")]
    error = refusal(lambda: world.set_mode("rules", mapping=mapping))
    assert detail(error) == ("conflict", {"conflict_reason": "group_name_in_use", "aggregate_type": "ExecutorGroup"})
    assert world.groups.events == [], "no mode event is written once a group was refused"


def test_the_mode_it_already_is_is_a_conflict(world: World) -> None:
    unchanged = refusal(lambda: world.set_mode("legacy", key="k0"))
    assert detail(unchanged) == (
        "conflict", {"conflict_reason": "routing_mode_unchanged", "aggregate_type": "ExecutorRoutingModeEvent"})
    world.set_mode("rules")
    written = world.groups.written()
    again = refusal(lambda: world.set_mode("rules", key="k2"))
    assert again.detail_fields["conflict_reason"] == "routing_mode_unchanged"
    assert world.groups.written() == written, "the second cut-over made nothing"


def test_a_repeat_under_the_same_key_replays_the_first_answer_and_writes_nothing_more(world: World) -> None:
    shown = world.preview()
    mapping = world.mapping(shown)
    first = world.set_mode("rules", digest=shown.preview_digest, mapping=mapping)
    written, events = world.groups.written(), list(world.journal.events)
    again = world.set_mode("rules", digest=shown.preview_digest, mapping=mapping)
    assert [g.group.group_id for g in again.groups] == [g.group.group_id for g in first.groups]
    assert again.routing_mode == first.routing_mode and again.rules == first.rules
    assert world.groups.written() == written and world.journal.events == events
    assert world.groups.calls == [], "a replay takes no lock and writes nothing"


def test_the_same_key_with_another_payload_is_not_a_replay(world: World) -> None:
    world.set_mode("rules", mapping=world.mapping(None, "text_analysis"))
    other = refusal(lambda: world.set_mode("rules", mapping=world.mapping(None, "comparison_spec"), key="k1"))
    assert other.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_the_ledger_compares_the_mapping_by_work_kind_the_digest_and_the_actor_who_spent_the_key() -> None:
    def fingerprint(**kwargs: Any) -> str:
        fresh = World()
        fresh.route_all()
        fresh.set_mode("rules", **kwargs)
        return fresh.ledger.fingerprints()[0]

    mapping = [MappingEntry("text_analysis", "One"), MappingEntry("comparison_spec", "Two")]
    assert fingerprint(mapping=mapping) == fingerprint(mapping=list(reversed(mapping))), (
        "the order the mapping was listed in is not a difference")
    assert fingerprint(mapping=mapping) != fingerprint(mapping=[MappingEntry("text_analysis", "One"),
                                                                 MappingEntry("comparison_spec", "Three")])
    assert fingerprint(mapping=mapping) != fingerprint(mapping=mapping, actor=OTHER)


def test_a_second_cut_over_after_the_first_one_won_is_refused_whatever_its_key(world: World) -> None:
    """Two administrators confirm the same preview: the journal's lock serialises them, the first commits, and the
    second -- which waited for the lock and then read the mode -- is ``routing_mode_unchanged``. Here the two run one
    after the other against the same stand-in, which is the only order the lock allows."""
    first = world.set_mode("rules", key="admin-one")
    second = refusal(lambda: world.set_mode("rules", key="admin-two", actor=OTHER))
    assert second.detail_fields["conflict_reason"] == "routing_mode_unchanged"
    assert len(world.groups.events) == 1 and len(first.groups) == 6 and len(world.groups.groups) == 6


# --- the legacy routes are read-only under rules --------------------------------------------------------------------


def test_the_guard_takes_the_journals_lock_before_it_reads_the_mode_and_passes_while_the_mode_is_legacy(
    world: World,
) -> None:
    assert ensure_legacy_routing(SESSION, world.groups) is None
    assert world.groups.calls == ["lock_mode"]


def test_under_rules_set_route_is_a_conflict_before_a_key_is_claimed_and_nothing_is_written(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.set_mode("rules")
    monkeypatch.setattr(routing_mode, "GroupRepository", lambda: world.groups)
    before = (world.groups.written(), list(world.ledger.began), list(world.journal.events))
    error = refusal(lambda: commands.set_route(
        SESSION, work_kind="text_analysis", primary_connection_id=C2, standby_connection_id=None, roles=("admin",),
        idempotency_key="route-1", actor_uid=ADMIN, repository=world.executors, commands=world.ledger))
    assert detail(error) == (
        "conflict", {"conflict_reason": "routing_mode_rules", "aggregate_type": "ExecutorRouteEvent"})
    assert (world.groups.written(), list(world.ledger.began), list(world.journal.events)) == before
    assert world.executors.route_writes == [], "no route lock, no route row"
    assert world.executors.routes["text_analysis"].primary_connection_id == C1, "the history is as it was"


def test_while_the_mode_is_legacy_set_route_gets_past_the_guard_to_its_own_checks(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(routing_mode, "GroupRepository", lambda: world.groups)
    error = refusal(lambda: commands.set_route(
        SESSION, work_kind="text_analysis", primary_connection_id=C1, standby_connection_id=C1, roles=("admin",),
        idempotency_key="route-1", actor_uid=ADMIN, repository=world.executors, commands=world.ledger))
    assert detail(error) == ("validation_failed", {"field": "standby_connection_id", "constraint": "standby_equals_primary"})
    assert world.ledger.began == [("set_executor_route", "route-1")], "the guard let it through to the ledger"


def test_the_role_is_checked_before_the_mode_so_a_non_administrator_learns_nothing_of_it(world: World) -> None:
    error = refusal(lambda: commands.set_route(
        SESSION, work_kind="text_analysis", primary_connection_id=C1, standby_connection_id=None, roles=("expert",),
        idempotency_key="route-1", actor_uid=ADMIN, repository=world.executors, commands=world.ledger))
    assert error.code is ErrorCode.PERMISSION_DENIED and world.groups.calls == []


# --- item 22: the rollback ------------------------------------------------------------------------------------------------


def test_the_rollback_writes_one_legacy_event_and_touches_no_group_revision_or_rule(world: World) -> None:
    cut = world.set_mode("rules")
    groups_before = dict(world.groups.groups)
    revisions_before = dict(world.groups.revisions)
    rules_before = list(world.groups.rules)
    world.groups.calls.clear()

    back = world.set_mode("legacy", key="k2")

    assert back.routing_mode.mode == "legacy" and back.groups == ()
    assert world.groups.groups == groups_before and world.groups.revisions == revisions_before
    assert world.groups.rules == rules_before and back.rules == cut.rules, "the rules stay current and readable"
    assert [e["mode"] for e in world.groups.events] == ["rules", "legacy"] and [e["event_no"] for e in world.groups.events] == [1, 2]
    assert world.groups.events[1]["preview_digest"] is None and world.groups.events[1]["mapping"] == []
    assert world.groups.calls == ["lock_mode", "insert_mode_event"], "the lock, then the one event; no group, no rule"
    assert world.journal.events[-1]["payload"] == {
        "from_state": "rules", "to_state": "legacy", "revision_no": 2, "actor_uid": ADMIN}


def test_work_admitted_by_a_rule_keeps_the_group_revision_it_was_admitted_on(world: World) -> None:
    cut = world.set_mode("rules")
    admitted = {rule.work_kind: rule.group_revision_id for rule in cut.rules}
    world.set_mode("legacy", key="k2")
    for kind, revision_id in admitted.items():
        rule = world.groups.current_rule(SESSION, kind)
        assert rule is not None and rule.group_revision_id == revision_id
        revision = world.groups.get_revision(SESSION, revision_id)
        assert revision is not None and len(revision.members) == 1, "the revision a Run froze is still there, unchanged"


def test_the_rollback_takes_neither_a_digest_nor_a_mapping_and_the_legacy_route_serves_new_starts_again(
    world: World,
) -> None:
    world.set_mode("rules")
    refused = refusal(lambda: world.set_mode("legacy", digest=DIGEST, key="k2"))
    assert refused.detail_fields == {"field": "mapping", "constraint": "mapping_not_accepted"}
    assert world.groups.mode.mode == "rules", "a refused rollback changed nothing"
    world.set_mode("legacy", key="k3")
    assert world.groups.mode.mode == "legacy" and world.executors.routes["text_analysis"].primary_connection_id == C1


def test_a_second_cut_over_after_a_rollback_appends_new_rules_and_proposes_new_names(world: World) -> None:
    first = world.set_mode("rules", key="k1")
    world.set_mode("legacy", key="k2")
    shown = world.preview()
    assert [item.proposed_group_name for item in shown.items] == [f"{g.group.display_name} (2)" for g in first.groups]
    second = world.set_mode("rules", key="k3")
    assert [rule.rule_no for rule in second.rules] == [2] * 6, "rules are append-only: the second cut-over is rule 2"
    assert {rule.group_id for rule in second.rules}.isdisjoint({g.group.group_id for g in first.groups})
    assert [e["event_no"] for e in world.groups.events] == [1, 2, 3]
    assert len(world.groups.groups) == 12, "the first cut-over's groups were not deleted or reused"


# --- the grant classification --------------------------------------------------------------------------------------------


def test_the_code_writes_the_routing_mode_journal_so_the_table_leaves_the_sealed_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.recovery import grant_classification as grants

    seen = grants.observed_statements(ROOT / "src/auditmanager", frozenset({"executor_routing_mode_event"}))
    assert seen["executor_routing_mode_event"].verbs == {"INSERT"}, "append-only: an insert and nothing else"
    assert "executor_routing_mode_event" not in grants.SEALED_NOT_YET_WRITTEN
    assert "executor_routing_mode_event" in grants.APPEND_ONLY
    # The check can fail: a set that still named the table is red against the same scan.
    monkeypatch.setattr(grants, "SEALED_NOT_YET_WRITTEN", frozenset({"executor_routing_mode_event"}))
    assert sorted(set(seen) & grants.SEALED_NOT_YET_WRITTEN) == ["executor_routing_mode_event"]
