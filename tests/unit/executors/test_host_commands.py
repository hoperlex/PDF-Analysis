"""`HOSTS-BACKEND-01`: the host lifecycle commands, with the repositories, the ledger and the journal as stand-ins.

No database. What is proved: an agent's report is stored **only when it changed**, and a change clears the cooldowns, brings the system objects up to date and
reaches the journal; «Использовать» is admin-only, append-only with its author, and sets or clears the integration mark of the host's system connections;
slots are bounded and name only providers the host reports; a host in use cannot be archived; a refusal about access (and only that) starts the 15-minute
cooldown; a name that a used single-model agent holds blocks a host enrollment (``--upgrade``); the system connections and the groups of the pairs follow the
report, at most sixteen hosts to a pair. The same flows on real rows are ``tests/integration/executors/test_hosts_backend.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin
from auditmanager.executors import host_commands
from auditmanager.executors.catalogue import Catalogue, CatalogueEntry
from auditmanager.executors.host_commands import (
    archive_host,
    ensure_upgrade_allowed,
    issue_host_enrollment,
    record_task_failure,
    refuse_host_members_for_connection_token,
    report_host_health,
    set_host_enabled,
    set_host_slots,
    sync_system_objects,
)
from auditmanager.executors.host_repository import HostRecord
from auditmanager.executors.hosts import normalise_host_report
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.shared.errors import DomainError, ErrorCode

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
HOST = "exh_01M2545JSD15ETSNNV904X991M"
OTHER = "exh_01M2545JSD15ETSNNV904X991N"
TOKEN = "ern_01M2545JSD15ETSNNV904X991K"
OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
CATALOGUE = Catalogue(entries=(
    CatalogueEntry("claude_code", OPUS, ("subscription", "api"), ("medium",), (OPUS,)),
    CatalogueEntry("claude_code", SONNET, ("subscription", "api"), ("low",), (SONNET,)),
))
PINS = [ModelPin(OPUS, 5.0, 25.0), ModelPin(SONNET, 3.0, 15.0)]


class Journal:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def __call__(self, session, *, event_type, aggregate_type, aggregate_id, payload=None, **_) -> None:
        self.events.append({"event_type": event_type, "aggregate_id": aggregate_id, "payload": dict(payload or {})})

    def types(self) -> list[str]:
        return [event["event_type"] for event in self.events]


class Ledger:
    def __init__(self, replay: bool = False) -> None:
        self.replay, self.began, self.succeeded = replay, [], []

    def begin(self, session, *, command_type, idempotency_key, fingerprint):
        self.began.append(command_type)
        if self.replay:
            return CommandReplay(command_id="cmd_r", outcome={})  # type: ignore[arg-type]
        return CommandStarted(command_id="cmd_1")  # type: ignore[arg-type]

    def succeed(self, session, command_id, outcome) -> None:
        self.succeeded.append(dict(outcome))


@dataclass
class FakeHosts:
    """The host repository, in memory: one host, its switch, its slot journal, its snapshot and its cooldowns."""

    enabled: bool | None = True
    archived: bool = False
    report: Any = None
    pool_units: int = 0
    slot_events: list[tuple[str, int]] = field(default_factory=list)
    use_events: list[bool] = field(default_factory=list)
    marks: list[bool] = field(default_factory=list)
    cooldowns: list[tuple[str, str, int, str]] = field(default_factory=list)
    cleared: int = 0
    writes: int = 0
    locks: list[str] = field(default_factory=list)
    connections: list[Any] = field(default_factory=list)
    revoked: int = 0

    def get_host(self, session, host_id, *, lock=False):
        if host_id != HOST:
            return None
        return HostRecord(HOST, "adm1.hlab.kz", T0, ADMIN, T0 if self.archived else None, ADMIN if self.archived else None)

    def current_use(self, session, host_ids):
        return {} if self.enabled is None else {HOST: (self.enabled, T0, ADMIN)}

    def insert_use_event(self, session, host_id, *, enabled, actor_uid):
        self.use_events.append(enabled)
        self.enabled = enabled
        return len(self.use_events)

    def set_integration_marks(self, session, host_id, *, authorised, actor_uid):
        self.marks.append(authorised)
        return 1

    def slot_journal(self, session, host_ids):
        return {}

    def insert_slot_event(self, session, host_id, *, provider, slots, actor_uid):
        self.slot_events.append((provider, slots))
        return len(self.slot_events)

    def get_report(self, session, host_id, *, lock=False):
        return self.report

    def write_report(self, session, *, host_id, token_id, report, report_sha256):
        self.writes += 1
        self.report = SimpleNamespace(report=report, report_sha256=report_sha256)

    def clear_cooldowns(self, session, host_id):
        self.cleared += 1
        return 0

    def set_cooldown(self, session, *, host_id, provider, model_id, seconds, reason):
        self.cooldowns.append((provider, model_id, seconds, reason))
        return T0

    def system_connections(self, session, host_ids):
        return list(self.connections)

    def lock_pool(self, session, pool):
        self.locks.append(pool)

    def pool_units(self, session, pool, *, exclude_run_id=""):
        return self.pool_units_value(pool)

    def pool_units_value(self, pool):
        return self.pool_units

    def revoke_tokens_of(self, session, host_id, *, actor_uid):
        self.revoked += 1
        return []

    def revoke_pending_grants(self, session, host_id, *, actor_uid):
        return 0

    def archive_system_connections(self, session, host_id, *, actor_uid):
        return []

    def archive_host(self, session, host_id, *, actor_uid):
        self.archived = True
        return self.get_host(session, host_id)


def _report_args(**changes: Any) -> dict[str, Any]:
    base = {
        "agent_version": "0.21.0", "slots": {"claude_code": 1},
        "providers": [{"provider": "claude_code", "access": "subscription", "auth_state": "valid",
                       "models": [{"model_id": OPUS, "state": "verified", "checked_at": "2026-11-10T11:59:00Z"}]}],
    }
    return {**base, **changes}


@pytest.fixture
def synced(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    calls: list[Any] = []
    monkeypatch.setattr(host_commands, "sync_system_objects", lambda *args, **kwargs: calls.append(kwargs) or [])
    return calls


# --- the report: stored only on change ----------------------------------------------------------------------------


def test_the_first_report_is_stored_synced_and_journaled(synced: list[Any]) -> None:
    hosts, journal = FakeHosts(), Journal()
    changed, enabled = report_host_health(None, host_id=HOST, token_id=TOKEN, hosts=hosts, journal=journal, **_report_args())  # type: ignore[arg-type]
    assert (changed, enabled) == (True, True)
    assert hosts.writes == 1 and hosts.cleared == 1 and len(synced) == 1
    assert journal.types() == ["executor.host_report_changed"] and journal.events[0]["payload"]["state"] == "first"


def test_an_identical_report_writes_nothing_and_journals_nothing(synced: list[Any]) -> None:
    hosts, journal = FakeHosts(), Journal()
    report_host_health(None, host_id=HOST, token_id=TOKEN, hosts=hosts, journal=journal, **_report_args())  # type: ignore[arg-type]
    again = _report_args()
    again["providers"][0]["models"][0]["checked_at"] = "2026-11-10T13:00:00Z"  # a re-check at another time is not a change
    changed, _ = report_host_health(None, host_id=HOST, token_id=TOKEN, hosts=hosts, journal=journal, **again)  # type: ignore[arg-type]
    assert changed is False
    assert (hosts.writes, hosts.cleared, len(synced), len(journal.events)) == (1, 1, 1, 1), "the heartbeat is the token's pulse, not a row here"


def test_a_changed_report_is_stored_clears_the_cooldowns_and_says_changed(synced: list[Any]) -> None:
    hosts, journal = FakeHosts(), Journal()
    report_host_health(None, host_id=HOST, token_id=TOKEN, hosts=hosts, journal=journal, **_report_args())  # type: ignore[arg-type]
    failed = _report_args()
    failed["providers"][0]["models"] = [{"model_id": OPUS, "state": "failed", "checked_at": "2026-11-10T12:05:00Z",
                                         "failure_code": "quota_exceeded"}]
    changed, _ = report_host_health(None, host_id=HOST, token_id=TOKEN, hosts=hosts, journal=journal, **failed)  # type: ignore[arg-type]
    assert changed is True and hosts.writes == 2 and hosts.cleared == 2 and len(synced) == 2
    assert journal.events[-1]["payload"]["state"] == "changed"


def test_a_report_that_is_not_acceptable_stores_nothing(synced: list[Any]) -> None:
    hosts = FakeHosts()
    with pytest.raises(DomainError) as refused:
        report_host_health(None, host_id=HOST, token_id=TOKEN, hosts=hosts, journal=Journal(),  # type: ignore[arg-type]
                           **_report_args(providers=[{"provider": "gemini", "access": "api", "auth_state": "valid", "models": []}]))
    assert refused.value.code is ErrorCode.VALIDATION_FAILED and hosts.writes == 0 and not synced


@pytest.mark.parametrize("state", ["archived", "missing"])
def test_a_report_for_a_host_that_is_archived_or_gone_is_not_authenticated(state: str) -> None:
    hosts = FakeHosts(archived=state == "archived")
    host_id = HOST if state == "archived" else OTHER
    with pytest.raises(DomainError) as refused:
        report_host_health(None, host_id=host_id, token_id=TOKEN, hosts=hosts, journal=Journal(), **_report_args())  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.AUTHENTICATION_REQUIRED and hosts.writes == 0


def test_a_connection_token_sends_none_of_the_hosts_members() -> None:
    refuse_host_members_for_connection_token(providers=None, slots=None, key_file=None)
    for member in ({"providers": []}, {"slots": {"claude_code": 1}}, {"key_file": {"state": "ok"}}):
        with pytest.raises(DomainError) as refused:
            refuse_host_members_for_connection_token(**{"providers": None, "slots": None, "key_file": None, **member})
        assert refused.value.detail_fields["constraint"] == "host_token_only"


# --- «Использовать» -----------------------------------------------------------------------------------------------


def _use(hosts: FakeHosts, enabled: bool, *, roles: Any = ("admin",), ledger: Ledger | None = None, journal: Journal | None = None):
    return set_host_enabled(
        None, host_id=HOST, enabled=enabled, roles=roles, idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
        hosts=hosts, commands=ledger or Ledger(), journal=journal or Journal())


def test_only_an_administrator_switches_a_server() -> None:
    for roles in (("viewer",), ("expert",), ()):
        with pytest.raises(DomainError) as refused:
            _use(FakeHosts(), False, roles=roles)
        assert refused.value.code is ErrorCode.PERMISSION_DENIED


def test_switching_off_appends_an_event_with_its_author_and_clears_the_mark() -> None:
    hosts, journal = FakeHosts(enabled=True), Journal()
    _use(hosts, False, journal=journal)
    assert hosts.use_events == [False] and hosts.marks == [False]
    assert journal.events[0]["event_type"] == "executor.host_use_changed"
    assert journal.events[0]["payload"] == {"host_id": HOST, "enabled": False, "actor_uid": ADMIN}


def test_switching_on_sets_the_mark_of_its_system_connections() -> None:
    hosts = FakeHosts(enabled=False)
    _use(hosts, True)
    assert hosts.use_events == [True] and hosts.marks == [True]


def test_the_state_it_is_already_in_appends_nothing() -> None:
    hosts, journal = FakeHosts(enabled=True), Journal()
    _use(hosts, True, journal=journal)
    assert hosts.use_events == [] and hosts.marks == [] and journal.events == []


def test_an_archived_server_cannot_be_switched_and_a_replay_answers_it_as_it_stands() -> None:
    with pytest.raises(DomainError) as refused:
        _use(FakeHosts(archived=True), True)
    assert refused.value.detail_fields["conflict_reason"] == "host_archived"
    hosts = FakeHosts(enabled=True)
    _use(hosts, False, ledger=Ledger(replay=True))
    assert hosts.use_events == []


def test_a_server_that_does_not_exist_is_not_found() -> None:
    with pytest.raises(DomainError) as refused:
        set_host_enabled(None, host_id=OTHER, enabled=True, roles=("admin",), idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
                         hosts=FakeHosts(), commands=Ledger(), journal=Journal())
    assert refused.value.code is ErrorCode.NOT_FOUND


# --- slots ----------------------------------------------------------------------------------------------------------


def _slots(hosts: FakeHosts, slots: dict[str, int], *, roles: Any = ("admin",), journal: Journal | None = None):
    return set_host_slots(None, host_id=HOST, slots=slots, roles=roles, idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
                          hosts=hosts, commands=Ledger(), journal=journal or Journal())


def _reported(hosts: FakeHosts, *providers: tuple[str, str]) -> FakeHosts:
    report = normalise_host_report(
        agent_version="0.21.0", slots=None,
        providers=[{"provider": name, "access": access, "auth_state": "valid", "models": []} for name, access in providers])
    hosts.report = SimpleNamespace(report=report, report_sha256="a" * 64)
    return hosts


def test_slots_are_an_event_per_changed_provider_with_the_author() -> None:
    hosts, journal = _reported(FakeHosts(), ("claude_code", "subscription"), ("anthropic_api", "api")), Journal()
    _slots(hosts, {"claude_code": 3, "anthropic_api": 2}, journal=journal)
    assert hosts.slot_events == [("claude_code", 3)], "the API provider already has two by default: no event"
    assert journal.events[0]["payload"] == {"host_id": HOST, "provider": "claude_code", "slots": 3, "actor_uid": ADMIN}


@pytest.mark.parametrize(("slots", "constraint"), [({}, "required"), ({"claude_code": 0}, "range"), ({"claude_code": 17}, "range"),
                                                  ({"claude_code": True}, "range")])
def test_slots_are_one_to_sixteen_and_at_least_one_is_named(slots: dict[str, Any], constraint: str) -> None:
    with pytest.raises(DomainError) as refused:
        _slots(_reported(FakeHosts(), ("claude_code", "subscription")), slots)
    assert refused.value.detail_fields["constraint"] == constraint


def test_slots_of_a_provider_the_host_does_not_report_are_refused() -> None:
    hosts = _reported(FakeHosts(), ("claude_code", "subscription"))
    with pytest.raises(DomainError) as refused:
        _slots(hosts, {"codex": 2})
    assert refused.value.detail_fields["constraint"] == "provider_not_reported" and hosts.slot_events == []
    with pytest.raises(DomainError):
        _slots(FakeHosts(), {"claude_code": 2})  # a host that never reported has nothing to set


def test_only_an_administrator_changes_slots() -> None:
    with pytest.raises(DomainError) as refused:
        _slots(_reported(FakeHosts(), ("claude_code", "subscription")), {"claude_code": 2}, roles=("expert",))
    assert refused.value.code is ErrorCode.PERMISSION_DENIED


# --- archive ----------------------------------------------------------------------------------------------------------


def _row(pool: str, pin: str, billing: str, archived: bool = False):
    return SimpleNamespace(connection_id="exc_X", host_id=HOST, capacity_pool=pool, provider="claude_code", revision_id="excr_X",
                           pin_id=pin, billing=billing, archived_at=T0 if archived else None, integration_authorised_at=None)


def test_a_server_that_a_run_still_holds_is_not_archived() -> None:
    hosts = FakeHosts(pool_units=1)
    hosts.connections = [_row(f"{HOST}:claude_code", OPUS, "not_metered")]
    with pytest.raises(DomainError) as refused:
        archive_host(None, host_id=HOST, roles=("admin",), idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
                     hosts=hosts, groups=object(), commands=Ledger(), journal=Journal(), pins=PINS)  # type: ignore[arg-type]
    assert refused.value.detail_fields["conflict_reason"] == "host_in_use"
    assert hosts.locks == [f"{HOST}:claude_code"], "the pool was locked before its units were counted"
    assert hosts.revoked == 0 and not hosts.archived


def test_only_an_administrator_archives_a_server() -> None:
    with pytest.raises(DomainError) as refused:
        archive_host(None, host_id=HOST, roles=("expert",), idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
                     hosts=FakeHosts(), groups=object(), commands=Ledger(), journal=Journal())  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.PERMISSION_DENIED


# --- the passive cooldown ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("reason", ["quota_exceeded: monthly limit", "auth_failed", "model_not_found: no such model"])
def test_a_refusal_about_access_starts_the_fifteen_minute_cooldown(reason: str) -> None:
    hosts, journal = FakeHosts(), Journal()
    until = record_task_failure(None, host_id=HOST, provider="claude_code", model_id=OPUS, reason=reason, hosts=hosts, journal=journal)  # type: ignore[arg-type]
    assert until == T0 and hosts.cooldowns == [("claude_code", OPUS, 900, reason.split(":")[0].replace("auth_failed", "access_denied"))]
    assert journal.types() == ["executor.host_model_cooling_down"]


@pytest.mark.parametrize("reason", ["timeout", "answer_not_json: bad", "claude_turn_failed", "no reason given"])
def test_any_other_failure_starts_no_cooldown(reason: str) -> None:
    hosts, journal = FakeHosts(), Journal()
    assert record_task_failure(None, host_id=HOST, provider="claude_code", model_id=OPUS, reason=reason, hosts=hosts, journal=journal) is None  # type: ignore[arg-type]
    assert hosts.cooldowns == [] and journal.events == []


def test_a_failure_of_a_task_that_names_no_model_starts_no_cooldown() -> None:
    hosts = FakeHosts()
    assert record_task_failure(None, host_id=HOST, provider=None, model_id=None, reason="quota_exceeded", hosts=hosts) is None  # type: ignore[arg-type]
    assert hosts.cooldowns == []


# --- the guard on --upgrade ---------------------------------------------------------------------------------------------


class _Rows:
    def __init__(self, value: Any) -> None:
        self.value = value

    def all(self) -> Any:
        return self.value

    def scalar_one(self) -> Any:
        return self.value


class UpgradeSession:
    """Answers the two statements of the guard: the single-model connections of a name, and whether one is used."""

    def __init__(self, connections: list[str], used: set[str]) -> None:
        self.connections, self.used, self.asked = connections, used, []

    def execute(self, statement: Any, params: dict[str, Any]) -> _Rows:
        if "display_name" in str(statement):
            self.asked.append(params["name"])
            return _Rows([(cid,) for cid in self.connections])
        return _Rows(params["c"] in self.used)


def test_a_name_that_a_used_single_model_agent_holds_blocks_the_host_enrollment() -> None:
    with pytest.raises(DomainError) as refused:
        ensure_upgrade_allowed(UpgradeSession(["exc_USED"], {"exc_USED"}), "kzSonnet")  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.CONFLICT and refused.value.detail_fields["conflict_reason"] == "upgrade_blocked_by_use"
    assert "kzSonnet" not in str(refused.value.detail_fields) and "exc_USED" not in str(refused.value.detail_fields), "no name, no identity echoed"


def test_a_name_no_connection_holds_or_none_that_is_used_is_allowed() -> None:
    ensure_upgrade_allowed(UpgradeSession([], set()), "adm1.hlab.kz")  # type: ignore[arg-type]
    ensure_upgrade_allowed(UpgradeSession(["exc_IDLE"], set()), "adm1.hlab.kz")  # type: ignore[arg-type]


def test_the_guard_runs_before_a_host_is_made_or_a_grant_written() -> None:
    hosts, ledger = FakeHosts(), Ledger()
    with pytest.raises(DomainError) as refused:
        issue_host_enrollment(
            UpgradeSession(["exc_USED"], {"exc_USED"}), display_name="kzSonnet", roles=("admin",),  # type: ignore[arg-type]
            idempotency_key="k" * 16, actor_uid=ADMIN, configured_origin="https://stand.example", hosts=hosts,  # type: ignore[arg-type]
            grants=object(), commands=ledger, journal=Journal(), package_source=lambda: (_ for _ in ()).throw(AssertionError("package read")))  # type: ignore[arg-type]
    assert refused.value.detail_fields["conflict_reason"] == "upgrade_blocked_by_use"
    assert ledger.succeeded == [], "nothing succeeded: the refusal rolls the whole transaction back"


def test_only_an_administrator_enrolls_a_host_and_the_origin_comes_from_the_configuration() -> None:
    with pytest.raises(DomainError) as refused:
        issue_host_enrollment(None, display_name="h", roles=("expert",), idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
                              configured_origin="https://stand.example", commands=Ledger())
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    with pytest.raises(DomainError) as refused:
        issue_host_enrollment(None, display_name="h", roles=("admin",), idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
                              configured_origin=None, commands=Ledger())
    assert refused.value.detail_fields["dependency"] == "public_origin"


def test_a_repeat_of_the_enrollment_key_cannot_show_the_secret_again() -> None:
    with pytest.raises(DomainError) as refused:
        issue_host_enrollment(None, display_name="h", roles=("admin",), idempotency_key="k" * 16, actor_uid=ADMIN,  # type: ignore[arg-type]
                              configured_origin="https://stand.example", commands=Ledger(replay=True))
    assert refused.value.detail_fields["conflict_reason"] == "enrollment_shown_once"


# --- the system objects follow the report ---------------------------------------------------------------------------------


class FakeSystem:
    """The three stores the maintenance writes through, in memory: connections, groups and their member lists."""

    def __init__(self, live_per_pair: dict[tuple[str, str], int] | None = None) -> None:
        self.connections: list[dict[str, Any]] = []
        self.groups: dict[str, dict[str, Any]] = {}
        self.revisions: list[dict[str, Any]] = []
        self.live_per_pair = live_per_pair or {}
        self.marks = 0
        self.archived_groups: list[str] = []

    # HostRepository
    def system_connections(self, session, host_ids):
        return [SimpleNamespace(connection_id=c["id"], host_id=HOST, capacity_pool=f"{HOST}:{c['provider']}", provider=c["provider"],
                                revision_id="excr_" + c["id"], pin_id=c["model"], billing=c["billing"], archived_at=None,
                                integration_authorised_at=None) for c in self.connections]

    def insert_system_connection(self, session, *, host_id, provider, display_name, actor_uid):
        cid = f"exc_{len(self.connections):04d}"
        self.connections.append({"id": cid, "provider": provider, "name": display_name})
        return cid

    def set_integration_marks(self, session, host_id, *, authorised, actor_uid):
        self.marks += 1
        return 1

    def system_group_for(self, session, name):
        return next((gid for gid, g in self.groups.items() if g["name"] == name), None)

    def insert_system_group(self, session, *, display_name, actor_uid):
        gid = f"exg_{len(self.groups):04d}"
        self.groups[gid] = {"name": display_name, "members": None}
        return gid

    def lock_group(self, session, group_id):
        pass

    def live_members_of_pair(self, session, *, model_id, billing):
        count = self.live_per_pair.get((model_id, billing), len(self.connections))
        return [(f"exc_{n:04d}", f"excr_exc_{n:04d}") for n in range(count)]

    def current_group_members(self, session, group_id):
        return self.groups[group_id]["members"]

    # ExecutorRepository (the connection's revision; the group's is ``GroupRepo.insert_revision``)
    def insert_connection_revision(self, session, connection_id, settings, *, actor_uid):
        found = next(c for c in self.connections if c["id"] == connection_id)
        found["model"], found["billing"] = settings.pin_id, settings.billing
        found["settings"] = settings
        return SimpleNamespace(revision_id="excr_" + connection_id)

    # GroupRepository
    def lock_name(self, session, name):
        pass

    def next_revision_no(self, session, group_id):
        return len([r for r in self.revisions if r["group"] == group_id]) + 1

    def archive_group(self, session, group_id, *, actor_uid):
        self.archived_groups.append(group_id)


class GroupRepo(FakeSystem):
    def insert_revision(self, session, *, group_id, **kw):
        self.revisions.append({"group": group_id, "members": [m.connection_id for m in kw["members"]], "settings": kw["settings"]})
        self.groups[group_id]["members"] = sorted((m.connection_id, m.connection_revision_id) for m in kw["members"])
        return SimpleNamespace(group_revision_id=f"exgr_{len(self.revisions)}", revision_no=len(self.revisions))


class Execs:
    def __init__(self, system: FakeSystem) -> None:
        self.system = system

    def insert_revision(self, session, connection_id, settings, *, actor_uid):
        return self.system.insert_connection_revision(session, connection_id, settings, actor_uid=actor_uid)


def _sync(system: GroupRepo, report: Any, *, enabled: bool = True, journal: Journal | None = None):
    return sync_system_objects(
        None, host=HostRecord(HOST, "adm1.hlab.kz", T0, ADMIN), report=report, enabled=enabled, actor_uid=ADMIN,  # type: ignore[arg-type]
        book=CATALOGUE, hosts=system, executors=Execs(system), groups=system, pins=PINS, journal=journal or Journal())  # type: ignore[arg-type]


def _two_model_report():
    return normalise_host_report(agent_version="0.21.0", slots=None, providers=[{
        "provider": "claude_code", "access": "subscription", "auth_state": "valid",
        "models": [{"model_id": OPUS, "state": "verified", "checked_at": "2026-11-10T11:59:00Z"},
                   {"model_id": SONNET, "state": "not_verified", "checked_at": "2026-11-10T11:59:00Z"},
                   {"model_id": "gpt-6", "state": "not_verified", "checked_at": "2026-11-10T11:59:00Z"}]}])


def test_one_system_connection_per_catalogue_quadruple_and_one_group_per_pair() -> None:
    system, journal = GroupRepo(), Journal()
    created = _sync(system, _two_model_report(), journal=journal)
    assert [(q.provider, q.access, q.model_id) for q in created] == [
        ("claude_code", "subscription", OPUS), ("claude_code", "subscription", SONNET)], "a model outside the catalogue makes none"
    settings = {c["model"]: c["settings"] for c in system.connections}
    assert all(s.billing == "not_metered" and s.pin_id == s.gateway_model for s in settings.values()), "a subscription is not metered"
    assert settings[OPUS].pull_client == "agent" and settings[OPUS].allow_client_documents is False
    assert sorted(g["name"] for g in system.groups.values()) == [f"{OPUS} · subscription", f"{SONNET} · subscription"]
    assert system.marks == 1, "a connection made for a host that is on carries the mark"
    assert journal.types().count("executor.host_model_found") == 2 and journal.types().count("executor.group_created") == 2


def test_a_host_that_is_off_makes_connections_without_the_mark() -> None:
    system = GroupRepo()
    _sync(system, _two_model_report(), enabled=False)
    assert system.connections and system.marks == 0


def test_a_second_report_with_nothing_new_makes_nothing() -> None:
    system, journal = GroupRepo(), Journal()
    _sync(system, _two_model_report())
    before = (len(system.connections), len(system.revisions))
    assert _sync(system, _two_model_report(), journal=journal) == []
    assert (len(system.connections), len(system.revisions)) == before and journal.events == []


def test_a_group_is_revised_only_when_the_members_change() -> None:
    system = GroupRepo()
    _sync(system, _two_model_report())
    group = system.system_group_for(None, f"{OPUS} · subscription")
    assert len([r for r in system.revisions if r["group"] == group]) == 1
    system.live_per_pair[(OPUS, "not_metered")] = 2  # another host joined the pair
    system.connections.append({"id": "exc_0002", "provider": "claude_code", "model": OPUS, "billing": "not_metered", "settings": None})
    api = normalise_host_report(agent_version="0.21.0", slots=None, providers=[{
        "provider": "claude_code", "access": "api", "auth_state": "valid", "models": [
            {"model_id": OPUS, "state": "verified", "checked_at": "2026-11-10T11:59:00Z"}]}])
    _sync(system, api)  # the api pair is new; the subscription pair is untouched by it
    assert len([r for r in system.revisions if r["group"] == group]) == 1


def test_at_most_sixteen_hosts_take_part_in_a_pair_and_the_rest_are_journaled() -> None:
    system, journal = GroupRepo(live_per_pair={(OPUS, "not_metered"): 19}), Journal()
    _sync(system, _two_model_report(), journal=journal)
    group = system.system_group_for(None, f"{OPUS} · subscription")
    (revision,) = [r for r in system.revisions if r["group"] == group]
    assert len(revision["members"]) == 16, "GROUP_MEMBERS_MAX"
    assert journal.types().count("executor.host_over_group_limit") == 3


def test_an_empty_pair_archives_its_group_and_a_pair_that_never_had_one_makes_none() -> None:
    system = GroupRepo()
    _sync(system, _two_model_report())
    group = system.system_group_for(None, f"{OPUS} · subscription")
    system.live_per_pair[(OPUS, "not_metered")] = 0
    host_commands._refresh_pair_group(  # type: ignore[attr-defined]
        None, model_id=OPUS, access="subscription", pins={p.model_id: p for p in PINS}, hosts=system, groups=system, actor_uid=ADMIN,
        journal=Journal())
    assert system.archived_groups == [group]
    lonely = GroupRepo(live_per_pair={(OPUS, "metered"): 0})
    host_commands._refresh_pair_group(  # type: ignore[attr-defined]
        None, model_id=OPUS, access="api", pins={p.model_id: p for p in PINS}, hosts=lonely, groups=lonely, actor_uid=ADMIN,
        journal=Journal())
    assert lonely.groups == {}
