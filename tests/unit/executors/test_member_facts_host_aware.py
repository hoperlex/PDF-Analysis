"""`D-676`: ``executors.member_facts`` reads a server's system member by its server's facts; comparisons no longer carry a workaround.

A system group's members are the system connections of the servers (ADR-0028 decisions 3 and 16). They have no probe and no runner token of
their own -- the server reports -- so the generic reading (a probe, a runner) finds none of them eligible. The tests run ``member_facts`` over
fakes of the rows (the store, the occupancies, the probe, the servers) and say, member by member:

* a system member is read by its server: eligible when the server has no reason against the model, with the server's slots as capacity and use;
  each reason, a missing server and an archived one keep it from being chosen; the access asked of the server is the group's billing;
* a member that is not a system connection is read as it always was -- from its probe, its runner and its occupancy -- and the servers are not
  even read for it;
* the order of the members is the revision's, mixed members included.

Break-it-once (``_facts`` back to the probe-only reading, in a scratch copy of ``src``): five of the eight tests fail -- the eligible system member
(``probe_not_ok``), the full server, the missing and the archived server, the access asked of the server and the mixed group; the reason test
cannot tell the two readings apart (both leave the member unprobed), the plain-member tests hold what must not move.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.executors import group_commands, host_commands
from auditmanager.executors.group_selection import (
    ISSUE_AT_CAPACITY, ISSUE_CONNECTION_ARCHIVED, ISSUE_PROBE_NOT_OK, ISSUE_REVISION_CHANGED, member_issue,
)
from auditmanager.executors.model import ConnectionRecord
from auditmanager.executors.queries import Occupancy

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
PIN = "gpt-6-sol"
HOST = "exh_01M2545JSD15ETSNNV904X991M"
SYSTEM_POOL = f"{HOST}:codex"


def _connection(connection_id: str, *, pool: str | None, kind: str = "pull", archived: bool = False) -> ConnectionRecord:
    return ConnectionRecord(
        connection_id=connection_id, kind=kind, display_name=connection_id, created_at=NOW, created_by="u",
        archived_at=NOW if archived else None, system_managed=pool is not None, host_id=None if pool is None else pool.split(":")[0],
        capacity_pool=pool,
    )


def _member(connection_id: str, order: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(connection_id=connection_id, connection_revision_id=f"rev-{connection_id}", tie_break_order=order)


def _revision(*members: SimpleNamespace, billing: str = "not_metered") -> SimpleNamespace:
    return SimpleNamespace(members=tuple(members), billing=billing, pin_id=PIN)


def _host(host_id: str = HOST, *, slots: int = 3, in_use: int = 1, archived: bool = False, provider: str = "codex") -> SimpleNamespace:
    slot = SimpleNamespace(provider=provider, slots=slots, in_use=in_use)
    return SimpleNamespace(
        record=SimpleNamespace(host_id=host_id, archived_at=NOW if archived else None),
        slot_of=lambda wanted: slot if wanted == provider else None,
    )


class World:
    """The rows, faked: connections by id, their current revisions, the probe's answer, the occupancies and the servers."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, connections: list[ConnectionRecord], *, hosts: list[Any] | None = None,
                 reasons: list[str] | None = None, probe_ok: bool = False, runner_online: bool = False) -> None:
        self.connections = {item.connection_id: item for item in connections}
        self.hosts_read: list[list[str]] = []
        self.reasons_asked: list[dict[str, str]] = []
        found_hosts = hosts if hosts is not None else [_host()]
        reasons = reasons if reasons is not None else []

        class Store:
            def current_revisions(_self, session: Any, ids: Any) -> dict[str, Any]:
                return {cid: SimpleNamespace(revision_id=f"rev-{cid}") for cid in ids}

            def get_connection(_self, session: Any, connection_id: str) -> ConnectionRecord | None:
                return self.connections.get(connection_id)

            def runner_online(_self, session: Any, connection_id: str) -> bool:
                return runner_online

        self.store = Store()
        monkeypatch.setattr(group_commands, "occupancies", lambda session, ids, store: {
            cid: Occupancy(capacity=2, active_runs=1, active_calls=0) for cid in ids})
        monkeypatch.setattr(group_commands, "is_served", lambda connection, current: True)
        monkeypatch.setattr(group_commands, "is_probed_ok", lambda session, store, connection, current: probe_ok)

        def read_hosts(session: Any, host_ids: Any = None, *, include_archived: bool = False, **_: Any) -> list[Any]:
            self.hosts_read.append(list(host_ids))
            assert include_archived, "an archived server is read too: its members are reported archived, not missing"
            return [item for item in found_hosts if item.record.host_id in host_ids]

        def member_reasons(host: Any, *, provider: str, access: str, model_id: str) -> tuple[list[str], bool]:
            self.reasons_asked.append({"provider": provider, "access": access, "model_id": model_id})
            return list(reasons), False

        monkeypatch.setattr(host_commands, "read_hosts", read_hosts)
        monkeypatch.setattr(host_commands, "member_reasons", member_reasons)

    def facts(self, revision: SimpleNamespace) -> list[Any]:
        return group_commands.member_facts(None, revision, self.store)  # type: ignore[arg-type]


def test_a_system_member_is_eligible_by_its_servers_facts_with_the_servers_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)])  # no probe, no runner: the generic reading finds nothing

    [facts] = world.facts(_revision(_member("sys", 1)))

    assert (facts.connection_id, facts.tie_break_order) == ("sys", 1)
    assert (facts.revision_is_snapshot, facts.archived, facts.served, facts.probed_ok, facts.runner_online) == (True, False, True, True, True)
    assert (facts.capacity, facts.used) == (3, 1), "the server's slots of the provider, not the connection's own occupancy (2, 1)"
    assert member_issue(facts) is None
    assert world.hosts_read == [[HOST]]


def test_each_reason_of_the_server_keeps_a_system_member_from_being_chosen(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)], reasons=["model_cooling_down"])

    [facts] = world.facts(_revision(_member("sys")))

    assert (facts.probed_ok, facts.runner_online) == (False, False)
    assert member_issue(facts) == ISSUE_PROBE_NOT_OK


def test_a_full_server_is_eligible_but_at_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)], hosts=[_host(slots=2, in_use=2)])

    [facts] = world.facts(_revision(_member("sys")))

    assert member_issue(facts) == ISSUE_AT_CAPACITY


def test_a_server_that_is_gone_or_archived_leaves_its_member_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    gone = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)], hosts=[])
    [missing] = gone.facts(_revision(_member("sys")))
    assert (missing.archived, missing.probed_ok, missing.capacity, missing.used) == (True, False, 0, 0)
    assert member_issue(missing) == ISSUE_CONNECTION_ARCHIVED

    archived = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)], hosts=[_host(archived=True)])
    [facts] = archived.facts(_revision(_member("sys")))
    assert facts.archived is True and member_issue(facts) == ISSUE_CONNECTION_ARCHIVED


def test_the_access_asked_of_the_server_is_the_groups_billing(monkeypatch: pytest.MonkeyPatch) -> None:
    subscription = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)])
    subscription.facts(_revision(_member("sys"), billing="not_metered"))
    metered = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)])
    metered.facts(_revision(_member("sys"), billing="metered"))

    assert subscription.reasons_asked == [{"provider": "codex", "access": "subscription", "model_id": PIN}]
    assert metered.reasons_asked == [{"provider": "codex", "access": "api", "model_id": PIN}]


def test_a_member_that_is_not_a_system_connection_is_read_as_it_always_was(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, [_connection("plain", pool=None)], probe_ok=True, runner_online=True)

    [facts] = world.facts(_revision(_member("plain", 2)))

    assert (facts.probed_ok, facts.runner_online, facts.served, facts.capacity, facts.used) == (True, True, True, 2, 1)
    assert member_issue(facts) is None
    assert world.hosts_read == [] and world.reasons_asked == [], "no server is read for a member that is not a system connection"

    unprobed = World(monkeypatch, [_connection("plain", pool=None)], probe_ok=False, runner_online=False)
    [dark] = unprobed.facts(_revision(_member("plain")))
    assert (dark.probed_ok, dark.runner_online) == (False, False), "a plain member without a probe stays ineligible: the servers do not vouch for it"


def test_the_members_keep_the_revisions_order_when_system_and_plain_are_mixed(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, [
        _connection("plain-a", pool=None), _connection("sys", pool=SYSTEM_POOL), _connection("plain-b", pool=None, archived=True)],
        probe_ok=True, runner_online=True)

    found = world.facts(_revision(_member("plain-a", 1), _member("sys", 2), _member("plain-b", 3)))

    assert [item.connection_id for item in found] == ["plain-a", "sys", "plain-b"]
    assert [(item.capacity, item.used) for item in found] == [(2, 1), (3, 1), (2, 1)]
    assert [item.archived for item in found] == [False, False, True]
    assert world.hosts_read == [[HOST]], "one read of the servers for the whole group"


def test_a_member_whose_revision_moved_is_reported_changed_even_on_a_server(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, [_connection("sys", pool=SYSTEM_POOL)])
    stale = SimpleNamespace(connection_id="sys", connection_revision_id="rev-older", tie_break_order=None)

    [facts] = world.facts(_revision(stale))

    assert facts.revision_is_snapshot is False and member_issue(facts) == ISSUE_REVISION_CHANGED
