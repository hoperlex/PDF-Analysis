"""`HOSTS-BACKEND-01`: what ``HostsService`` hands the adapter is a shape the contract's own models accept.

The adapter validates every answer with ``model_validate`` and fails loudly on a shape that is not the contract's, so a mapping slip here would be a 500 at the first
real call. This module builds the facts of a host by hand, runs the service's mapping over them and validates the result with the **generated models of contract 1.45.0**:
the list with its summary line, the details (slots, providers, reasons, cooldown, tasks), the host that is off line, the issued enrollment, the install session, the token and
the catalogue of a redeemed host grant, and the answer to a health report. The two promises of the plan are asserted on the way: a list never shows a reason or an unavailable
model (reasons are for the administrator's details), and no view carries a secret.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.bootstrap.hosts_adapter import ExecutorHostAdapter
from auditmanager.bootstrap.hosts_service import HostsService
from auditmanager.executors import public as ex
from auditmanager.executors.agent_install_repository import InstallRecord
from auditmanager.executors.enrollment_repository import EnrollmentRecord
from auditmanager.executors.host_commands import HostDetails, HostFacts, SlotUse
from auditmanager.executors.host_repository import ActiveTask, HostRecord, StoredReport
from auditmanager.executors.hosts import normalise_host_report
from auditmanager.shared.identity import ExecutorHostId

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"


def _host_id() -> str:
    return str(ExecutorHostId.new())


def _report(*, auth: str = "valid", sonnet: str = "not_verified") -> StoredReport:
    report = normalise_host_report(agent_version="0.21.0", slots={"claude_code": 1}, providers=[{
        "provider": "claude_code", "access": "subscription", "auth_state": auth, "cli_version": "2.1.310", "models": [
            {"model_id": OPUS, "state": "verified" if auth == "valid" else "not_verified", "checked_at": "2026-11-10T11:59:00Z"},
            {"model_id": SONNET, "state": sonnet, "checked_at": "2026-11-10T11:59:00Z"}]}])
    return StoredReport(host_id="x", token_id="ern_X", report=report, report_sha256="a" * 64, reported_at=NOW)


def _facts(*, enabled: bool = True, age: float | None = 5.0, in_use: int = 0, auth: str = "valid", cooldown: bool = False) -> HostFacts:
    host_id = _host_id()
    return HostFacts(
        record=HostRecord(host_id, "adm1.hlab.kz", NOW - timedelta(days=1), ADMIN), enabled=enabled, pulse_age_seconds=age, report=_report(auth=auth),
        slots=(SlotUse("claude_code", "subscription", 1, in_use),),
        cooldowns={("claude_code", OPUS): NOW + timedelta(minutes=9)} if cooldown else {}, connections=(), now=NOW)


class Sessions:
    @contextmanager
    def __call__(self):
        class S:
            def commit(self) -> None: ...
        yield S()


def _service(monkeypatch: pytest.MonkeyPatch, facts: list[HostFacts], *, tasks: tuple[ActiveTask, ...] = ()) -> HostsService:
    monkeypatch.setattr(ex, "read_hosts", lambda session, host_ids=None, **kw: [f for f in facts if host_ids is None or f.record.host_id in host_ids])
    monkeypatch.setattr(ex, "host_details", lambda session, host_id: HostDetails(
        facts=facts[0], models=tuple(ex.model_availability(facts[0])), tasks=tasks))
    return HostsService(session_factory=Sessions())  # type: ignore[arg-type]


def test_the_list_is_valid_and_shows_only_models_that_can_be_used_and_no_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    online, busy, off = _facts(), _facts(in_use=1), _facts(age=None)
    view = _service(monkeypatch, [online, busy, off]).list_hosts()
    parsed = models.ExecutorHostList.model_validate(view)
    assert (parsed.online, parsed.total, parsed.slots_total, parsed.slots_free) == (2, 3, 3, 1), "on line of all; slots free of all"
    by_id = {item.host_id: item for item in parsed.items}
    first = by_id[online.record.host_id]
    assert [(m.model_id, m.state.value if hasattr(m.state, "value") else m.state) for m in first.models] == [(OPUS, "available")], (
        "Sonnet is not verified: it is not listed at all, and no reason is given in a list")
    assert [m.state for m in by_id[busy.record.host_id].models] == ["busy"]
    assert by_id[off.record.host_id].state.value == "offline" and by_id[off.record.host_id].models == []
    assert "reason" not in repr(view) and "model_not_verified" not in repr(view)


def test_a_host_that_is_switched_off_lists_no_model_and_says_so_by_its_switch_only(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts(enabled=False)
    parsed = models.ExecutorHost.model_validate(_service(monkeypatch, [facts]).get_host(host_id=facts.record.host_id))
    assert parsed.enabled is False and parsed.models == [] and parsed.last_seen_at is not None


def test_the_details_carry_the_reasons_the_slots_the_cooldown_and_the_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts(enabled=False, cooldown=True, in_use=1)
    task = ActiveTask("ext_01M2545JSD15ETSNNV904X991K", "run_01M2545JSD15ETSNNV904X991K", "claude_code", OPUS, "blocks", NOW - timedelta(minutes=3))
    view = _service(monkeypatch, [facts], tasks=(task,)).get_host_details(host_id=facts.record.host_id)
    parsed = models.ExecutorHostDetails.model_validate(view)
    (slot,) = parsed.slots
    assert (slot.provider.value, slot.access.value, slot.slots, slot.in_use) == ("claude_code", "subscription", 1, 1)
    (provider,) = parsed.providers
    assert (provider.provider.value, provider.auth_state.value, provider.cli_version) == ("claude_code", "valid", "2.1.310")
    states = {m.model_id: (m.state, [r.value for r in m.reasons], m.cooldown_until) for m in provider.models}
    assert states[OPUS][0] == "unavailable" and states[OPUS][1] == ["host_disabled", "model_cooling_down"] and states[OPUS][2] is not None
    assert states[SONNET][1] == ["host_disabled", "model_not_verified"]
    (running,) = parsed.tasks
    assert (running.provider.value, running.model_id, running.stage_key) == ("claude_code", OPUS, "blocks")


def test_the_details_of_a_login_that_is_gone_name_it(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts(auth="login_required")
    parsed = models.ExecutorHostDetails.model_validate(_service(monkeypatch, [facts]).get_host_details(host_id=facts.record.host_id))
    (provider,) = parsed.providers
    assert provider.auth_state.value == "login_required"
    assert [r.value for r in provider.models[0].reasons] == ["login_required", "model_not_verified"]


def test_a_host_that_never_reported_is_a_valid_host_with_nothing_to_list(monkeypatch: pytest.MonkeyPatch) -> None:
    bare = HostFacts(record=HostRecord(_host_id(), "new", NOW, ADMIN), enabled=True, pulse_age_seconds=None, report=None, slots=(), cooldowns={},
                     connections=(), now=NOW)
    parsed = models.ExecutorHostList.model_validate(_service(monkeypatch, [bare]).list_hosts())
    (item,) = parsed.items
    assert (item.state.value, item.models, item.slots_total, item.last_seen_at, item.agent_version) == ("offline", [], 0, None, None)
    details = models.ExecutorHostDetails.model_validate(_service(monkeypatch, [bare]).get_host_details(host_id=bare.record.host_id))
    assert details.providers == [] and details.slots == []


# --- the writes' answers --------------------------------------------------------------------------------------------


def test_the_issued_enrollment_is_the_contracts_and_carries_the_secret_once(monkeypatch: pytest.MonkeyPatch) -> None:
    host_id = _host_id()
    record = EnrollmentRecord(
        enrollment_id="exen_01M2545JSD15ETSNNV904X991K", connection_id=None, secret_prefix="ame_abcd1234", created_at=NOW, created_by=ADMIN,
        expires_at=NOW + timedelta(minutes=15), redeemed_at=None, runner_token_id=None, revoked_at=None, revoked_by=None, read_at=NOW, host_id=host_id)
    secret = "ame_abcd1234_" + "S" * 43
    issued = SimpleNamespace(record=record, secret=secret, package=SimpleNamespace(version="0.21.0", sha256="a" * 64), command="curl x | sudo bash")
    monkeypatch.setattr(ex, "issue_host_enrollment", lambda session, **kw: issued)
    monkeypatch.setattr(HostsService, "_roles", staticmethod(lambda session, uid: ("admin",)))
    parsed = models.IssuedExecutorEnrollment.model_validate(
        HostsService(session_factory=Sessions()).issue_enrollment(display_name="adm1.hlab.kz", user_uid=ADMIN, idempotency_key="k" * 16))  # type: ignore[arg-type]
    assert parsed.enrollment.host_id == host_id and parsed.enrollment.connection_id is None and parsed.enrollment.state.value == "pending"
    assert parsed.secret == secret and "AUDITMANAGER_AGENT_MODEL" not in parsed.command


def test_the_install_session_of_a_host_is_the_contracts_and_never_carries_a_private_key(monkeypatch: pytest.MonkeyPatch) -> None:
    host_id = _host_id()
    record = InstallRecord(
        install_id="exai_01M2545JSD15ETSNNV904X991K", connection_id=None, state="requested", access="generated_key", ssh_host="agent-host.example",
        ssh_port=22, ssh_user="ubuntu", key_secret_id="exs_X", public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLE1 s",
        observed_host_key=None, confirmed_host_key_fingerprint=None, host_key_confirmed_at=None, host_key_confirmed_by=None, package_version="0.21.0",
        package_sha256="a" * 64, failure_reason=None, key_removed_at=None, created_at=NOW, created_by=ADMIN, updated_at=NOW, finished_at=None, host_id=host_id)
    monkeypatch.setattr(ex, "create_host_agent_install", lambda session, **kw: record)
    monkeypatch.setattr(HostsService, "_roles", staticmethod(lambda session, uid: ("admin",)))
    body = models.CreateExecutorHostAgentInstallRequest.model_validate(
        {"display_name": "adm1.hlab.kz", "access": "generated_key", "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu"})
    parsed = models.ExecutorAgentInstall.model_validate(
        HostsService(session_factory=Sessions()).create_agent_install(body=body, user_uid=ADMIN, idempotency_key="k" * 16))  # type: ignore[arg-type]
    assert parsed.host_id == host_id and parsed.connection_id is None and parsed.state.value == "requested"
    assert parsed.authorized_keys_line is not None and parsed.authorized_keys_line.startswith("restrict ssh-ed25519 ")
    assert "PRIVATE" not in parsed.model_dump_json()


def test_a_redeemed_host_grant_answers_the_token_the_host_and_the_catalogue(monkeypatch: pytest.MonkeyPatch) -> None:
    host_id = _host_id()
    token = "amr_abcd1234_" + "T" * 43
    redeemed = SimpleNamespace(value=token, record=SimpleNamespace(host_id=host_id))
    monkeypatch.setattr(ex, "redeem_enrollment", lambda session, principal, **kw: redeemed)
    answer = HostsService(session_factory=Sessions()).redeem_host_enrollment(  # type: ignore[arg-type]
        enrollment=SimpleNamespace(enrollment_id="exen_X", connection_id=None, host_id=host_id, exchange_key=b"k"), runner_instance_id="agent-instance-0001")
    parsed = models.IssuedRunnerToken.model_validate(answer)
    assert parsed.token == token and parsed.host_id == host_id and parsed.runner_token is None
    assert {(e.provider.value, e.model_id) for e in parsed.catalogue} >= {("claude_code", OPUS), ("codex", "gpt-6.1-sol")}
    for entry in parsed.catalogue:
        assert entry.model_id in entry.accepted_reported or entry.accepted_reported, "an exact list of reported strings, never a rule"


def test_the_answer_to_a_health_report_is_the_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.executors.host_commands import HostHealthAck

    monkeypatch.setattr(ex, "report_host_runner_health", lambda session, **kw: HostHealthAck(NOW, ex.catalogue().for_agent(), True, True))
    adapter = ExecutorHostAdapter(Sessions(), service=HostsService(session_factory=Sessions()))  # type: ignore[arg-type]
    body = models.ReportRunnerHealthRequest.model_validate({
        "agent_version": "0.21.0", "clis": [{"cli": "claude", "installed": True, "auth_state": "valid", "version": "2.1.310"}], "concurrency": 1,
        "execution_profile": "command", "features": [], "providers": [{"provider": "claude_code", "access": "subscription", "auth_state": "valid", "models": [
            {"model_id": OPUS, "state": "verified", "checked_at": "2026-11-10T11:59:00Z"}]}], "slots": {"claude_code": 1}, "key_file": {"state": "absent"}})
    ack = adapter.report_host_health(runner=SimpleNamespace(token_id="ern_X", host_id=_host_id(), connection_id=None), body=body)
    assert ack.enabled is True and ack.catalogue and ack.recorded_at == NOW
