"""`HOSTS-BACKEND-01` (ADR-0028 decisions 2 and 3): the stand keeps the system connections and groups; nobody changes them by hand.

Revising or archiving a system connection or group is refused with ``conflict`` / ``system_managed``, and so is every other act a user could aim at one --
keying, probing, routing, enrolling, a token, the integration mark, a rule, a membership. The lists, the cut-over preview and the rule-target pickers do not show
them. Each refusal comes **before** anything is written. A connection a user made is revised, archived and listed as it always was (the contrast is in
every test: the same call on a user's connection goes through).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin
from auditmanager.executors import commands, enrollment, group_commands, integration_mark, runner
from auditmanager.executors.group_repository import GroupRepository
from auditmanager.executors.groups import GroupRecord, GroupSettings, MemberRequest
from auditmanager.executors.model import ConnectionRecord, RevisionSettings
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.ingest.public import CommandStarted
from auditmanager.shared.errors import DomainError, ErrorCode

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
HOST = "exh_01M2545JSD15ETSNNV904X991M"
SYSTEM = "exc_01M2545JSD15ETSNNV904X991K"
USER = "exc_01M2545JSD15ETSNNV904X991M"
GROUP = "exg_01M2545JSD15ETSNNV904X991K"
OPUS = "claude-opus-5-5"
KEY = "k" * 16


class Ledger:
    def __init__(self) -> None:
        self.succeeded: list[Any] = []

    def begin(self, session, *, command_type, idempotency_key, fingerprint):
        return CommandStarted(command_id="cmd_1")  # type: ignore[arg-type]

    def succeed(self, session, command_id, outcome) -> None:
        self.succeeded.append(outcome)


class Store:
    """The executor repository, for one system connection and one the user made. Records every write it is asked for."""

    def __init__(self) -> None:
        self.writes: list[str] = []

    def _record(self, connection_id: str) -> ConnectionRecord:
        system = connection_id == SYSTEM
        return ConnectionRecord(
            connection_id, "pull", "adm1.hlab.kz · claude_code" if system else "kzSonnet", T0, ADMIN, None, None,
            system_managed=system, host_id=HOST if system else None, capacity_pool=f"{HOST}:claude_code" if system else None)

    def get_connection(self, session, connection_id, *, lock=False):
        return self._record(connection_id) if connection_id in (SYSTEM, USER) else None

    def current_revisions(self, session, ids):
        return {}

    def insert_revision(self, *a, **k):
        self.writes.append("revision")
        raise AssertionError("a system connection took a revision")

    def archive_connection(self, *a, **k):
        self.writes.append("archive")
        raise AssertionError("a system connection was archived")

    def current_routes(self, session):
        return []

    def lock_route(self, session, work_kind):
        pass

    def append_route(self, *a, **k):
        self.writes.append("route")
        raise AssertionError("a route named a system connection")

    def sweep_probes(self, session):
        return 0

    def current_secrets(self, session, ids):
        return {}

    def insert_probe(self, *a, **k):
        self.writes.append("probe")
        raise AssertionError("a probe was requested for a system connection")


def _refused(call: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def _is_system_refusal(error: DomainError) -> bool:
    return error.code is ErrorCode.CONFLICT and error.detail_fields.get("conflict_reason") == "system_managed"


SETTINGS = RevisionSettings(pin_id=OPUS, gateway_model=OPUS, billing="not_metered", allow_client_documents=False, timeout_seconds=60,
                            pull_client="agent", answer_deadline_seconds=600, max_claimed_tasks=1)


def test_a_system_connection_is_not_revised_by_hand() -> None:
    store = Store()
    error = _refused(lambda: commands.revise_connection(
        None, connection_id=SYSTEM, settings=SETTINGS, pinned_model_ids=[OPUS], roles=("admin",),  # type: ignore[arg-type]
        idempotency_key=KEY, actor_uid=ADMIN, repository=store, commands=Ledger()))  # type: ignore[arg-type]
    assert _is_system_refusal(error) and store.writes == []


def test_a_system_connection_is_not_archived_by_hand() -> None:
    store = Store()
    error = _refused(lambda: commands.archive_connection(
        None, connection_id=SYSTEM, roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN, repository=store, commands=Ledger()))  # type: ignore[arg-type]
    assert _is_system_refusal(error) and store.writes == []


def test_a_system_connection_is_not_probed_and_not_a_route() -> None:
    store = Store()
    assert _is_system_refusal(_refused(lambda: commands.request_probe(
        None, connection_id=SYSTEM, roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN, repository=store, commands=Ledger())))  # type: ignore[arg-type]
    assert store.writes == []


def test_the_connection_a_user_made_is_still_a_connection_the_same_commands_reach() -> None:
    """The contrast: the same revise on the user's connection passes the guard (it then reaches the write the fake store forbids)."""
    store = Store()
    with pytest.raises(AssertionError, match="took a revision"):
        commands.revise_connection(
            None, connection_id=USER, settings=SETTINGS, pinned_model_ids=[OPUS], roles=("admin",),  # type: ignore[arg-type]
            idempotency_key=KEY, actor_uid=ADMIN, repository=store, commands=Ledger())  # type: ignore[arg-type]


def test_a_system_connection_takes_no_enrollment_no_runner_token_and_no_mark() -> None:
    store = Store()
    assert _is_system_refusal(_refused(lambda: enrollment.issue_executor_enrollment(
        None, connection_id=SYSTEM, roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN,  # type: ignore[arg-type]
        configured_origin="https://stand.example", executors=store, repository=object(), commands=Ledger())))  # type: ignore[arg-type]
    assert _is_system_refusal(_refused(lambda: runner.issue_runner_token(
        None, connection_id=SYSTEM, expires_in_days=None, roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN,  # type: ignore[arg-type]
        executors=store, repository=object(), commands=Ledger())))  # type: ignore[arg-type]
    assert _is_system_refusal(_refused(lambda: integration_mark.set_integration_authorisation(
        None, connection_id=SYSTEM, authorised=True, roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN,  # type: ignore[arg-type]
        executors=store, repository=object(), commands=Ledger())))  # type: ignore[arg-type]


# --- groups --------------------------------------------------------------------------------------------------------------


class Groups:
    def __init__(self, *, system: bool) -> None:
        self.system, self.writes = system, []

    def get_group(self, session, group_id, *, lock=False):
        return GroupRecord(GROUP, "claude-opus-5-5 · subscription", 0, T0, ADMIN, None, None, system_managed=self.system) if group_id == GROUP else None

    def insert_revision(self, *a, **k):
        self.writes.append("revision")
        raise AssertionError("a system group took a revision")

    def archive_group(self, *a, **k):
        self.writes.append("archive")
        raise AssertionError("a system group was archived")

    def get_revision(self, session, revision_id):
        return SimpleNamespace(group_id=GROUP, group_revision_id=revision_id)

    def lock_connections(self, session, ids):
        return set(ids)

    def current_rules(self, session):
        return []


_GROUP_SETTINGS = GroupSettings(pin_id=OPUS, gateway_model=OPUS, billing="not_metered", strategy="least_loaded")
_MEMBER = [MemberRequest(USER, "excr_01M2545JSD15ETSNNV904X991K")]
_PINS = [ModelPin(OPUS, 5.0, 25.0)]


def test_a_system_group_is_not_revised_archived_or_named_by_a_rule() -> None:
    groups = Groups(system=True)
    assert _is_system_refusal(_refused(lambda: group_commands.revise_group(
        None, group_id=GROUP, settings=_GROUP_SETTINGS, members=_MEMBER, pins=_PINS, roles=("admin",), idempotency_key=KEY,  # type: ignore[arg-type]
        actor_uid=ADMIN, repository=Store(), groups=groups, commands=Ledger())))  # type: ignore[arg-type]
    assert _is_system_refusal(_refused(lambda: group_commands.archive_group(
        None, group_id=GROUP, roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN, groups=groups, commands=Ledger())))  # type: ignore[arg-type]
    assert _is_system_refusal(_refused(lambda: group_commands.set_routing_rule(
        None, work_kind="text_analysis", group_revision_id="exgr_01M2545JSD15ETSNNV904X991K", roles=("admin",), idempotency_key=KEY,  # type: ignore[arg-type]
        actor_uid=ADMIN, groups=groups, commands=Ledger())))  # type: ignore[arg-type]
    assert groups.writes == []


def test_the_group_a_user_made_reaches_the_same_writes() -> None:
    groups = Groups(system=False)
    with pytest.raises(AssertionError):
        group_commands.archive_group(None, group_id=GROUP, roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN, groups=groups, commands=Ledger())  # type: ignore[arg-type]


def test_a_system_connection_is_not_a_member_of_a_group_made_by_hand() -> None:
    store = Store()
    error = _refused(lambda: group_commands._refuse_members(  # type: ignore[attr-defined]
        None, store, Groups(system=False), _GROUP_SETTINGS, [MemberRequest(SYSTEM, "excr_01M2545JSD15ETSNNV904X991K")]))  # type: ignore[arg-type]
    assert _is_system_refusal(error)


# --- the lists and the preview ------------------------------------------------------------------------------------------


class Recorder:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def execute(self, statement: Any, params: Any = None) -> Any:
        self.sql.append(str(statement))
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: [], first=lambda: None), all=lambda: [])


def test_the_connection_list_leaves_the_system_connections_out() -> None:
    session = Recorder()
    ExecutorRepository().list_connections(session)  # type: ignore[arg-type]
    assert "WHERE NOT system_managed" in session.sql[0]


def test_the_group_list_leaves_the_system_groups_out() -> None:
    session = Recorder()
    GroupRepository().list_groups(session)  # type: ignore[arg-type]
    assert "WHERE NOT system_managed" in session.sql[0]


def test_a_route_that_names_a_system_connection_is_read_as_no_route_by_the_preview() -> None:
    from auditmanager.executors import routing_mode
    from auditmanager.executors.model import RouteRecord

    class PreviewStore(Store):
        def current_routes(self, session):
            return [RouteRecord("exre_X", "text_analysis", 1, SYSTEM, None, T0, ADMIN)]

    class PreviewGroups:
        def lock_connections(self, session, ids):
            return set(ids)

        def active_group_names(self, session):
            return set()

    items = routing_mode._build_items(None, PreviewStore(), PreviewGroups(), lock=False)  # type: ignore[arg-type]
    by_kind = {item.work_kind: item for item in items}
    assert by_kind["text_analysis"].status == "no_route", "a system connection is never a cut-over candidate"
