"""`HOSTS-BACKEND-01` (ADR-0028 decision 1): a host is installed over SSH with no model, and its key has a home of its own.

No database. The remote bootstrap is the real text run with bash against a stand-in ``sudo`` and package (the harness of ``test_agent_install``): a **host**
install sends ``-`` where a connection's sends its model, and then ``install.sh`` receives **no** ``AUDITMANAGER_AGENT_MODEL`` at all (and the variable is not in the
``--preserve-env`` list), so it installs host mode; a connection's install is exactly as it was. The API half is shown with stand-ins: the session of a host stores
its sealed key as a secret of the **host** (``host_id``, no connection), sealed to the host's identity, returns only the public half and the ``authorized_keys`` line, and
reads back only for its own host; one unfinished session per host; an overdue one ends; the host key is confirmed by exact fingerprint; a used single-model agent's
name blocks it (``--upgrade``); and the command of a host enrollment asks for no model.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.executors import host_commands
from auditmanager.executors.agent_install import observed_fingerprint
from auditmanager.executors.agent_install_repository import InstallRecord
from auditmanager.executors.agent_install_runner import build_payload, key_line_state
from auditmanager.executors.agent_package import AgentPackage, install_command
from auditmanager.executors.host_commands import (
    confirm_host_agent_install_host_key,
    create_host_agent_install,
    get_host_agent_install,
)
from auditmanager.executors.host_repository import HostRecord
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.executors.test_agent_install import (
    MARKER,
    ORIGIN,
    SECRET,
    RemoteHost,
    make_archive,
    needs_bash,
    payload_for,
)
from tests.unit.executors.test_host_commands import ADMIN, HOST, Journal, Ledger

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
INSTALL = "exai_01M2545JSD15ETSNNV904X991K"
PACKAGE = AgentPackage(version="0.21.0", sha256="a" * 64, size_bytes=1, path=None)  # type: ignore[arg-type]
KEY = "k" * 16


# --- the remote half --------------------------------------------------------------------------------------------------


def host_payload(archive: bytes) -> bytes:
    return build_payload(secret=SECRET, origin=ORIGIN, model="-", sha256=hashlib.sha256(archive).hexdigest(), archive=archive, marker=MARKER)


@needs_bash
def test_a_host_install_hands_install_sh_no_model_and_does_not_carry_the_variable(tmp_path) -> None:
    host = RemoteHost(tmp_path, f"ssh-ed25519 AAAA someone@laptop\nrestrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISTANDSKEY {MARKER}\n")
    archive = make_archive()
    done = host.run(host_payload(archive))
    assert done.returncode == 0, done.stderr
    assert done.stdout.decode().splitlines() == ["am-install: installed", "am-install: key-line removed"]
    assert host.recorded("install-env").splitlines() == sorted([f"AUDITMANAGER_ENROLLMENT_SECRET={SECRET}", f"AUDITMANAGER_STAND_ORIGIN={ORIGIN}"])
    sudo = host.recorded("sudo-argv")
    assert "--preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN\n" in sudo
    assert "AUDITMANAGER_AGENT_MODEL" not in sudo and SECRET not in sudo + host.recorded("install-argv")


@needs_bash
def test_a_connection_install_still_carries_its_model(tmp_path) -> None:
    host = RemoteHost(tmp_path, f"restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISTANDSKEY {MARKER}\n")
    assert host.run(payload_for()).returncode == 0
    assert any(line.startswith("AUDITMANAGER_AGENT_MODEL=") for line in host.recorded("install-env").splitlines())


def test_the_payload_of_a_host_names_no_model_and_the_command_of_a_host_asks_for_none() -> None:
    header = host_payload(make_archive()).split(b"\n")[:7]
    assert header[3] == b"-", "the fourth line of the payload is the model: a host's is ``-``"
    command = install_command(origin=ORIGIN, package=PACKAGE, secret=SECRET)
    assert "AUDITMANAGER_AGENT_MODEL" not in command and "preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN " in command
    with_model = install_command(origin=ORIGIN, package=PACKAGE, secret=SECRET, model="claude-opus-5")
    assert "AUDITMANAGER_AGENT_MODEL=claude-opus-5" in with_model


# --- the API half --------------------------------------------------------------------------------------------------------


class Ring:
    """The public ring: it seals to an opaque envelope and remembers the associated data it was given."""

    def __init__(self) -> None:
        self.sealed: list[tuple[bytes, dict[str, str]]] = []

    def seal(self, plaintext: bytes, associated: dict[str, str]) -> tuple[str, bytes]:
        self.sealed.append((plaintext, dict(associated)))
        return "kid-1", b"envelope"


class FakeHosts:
    def __init__(self, *, existing: bool = False) -> None:
        self.hosts: list[HostRecord] = [HostRecord(HOST, "adm1.hlab.kz", T0, ADMIN)] if existing else []
        self.use_events: list[bool] = []

    def lock_name(self, session, name):
        pass

    def list_hosts(self, session, **kw):
        return list(self.hosts)

    def insert_host(self, session, *, display_name, actor_uid):
        record = HostRecord(HOST, display_name, T0, actor_uid)
        self.hosts.append(record)
        return record

    def insert_use_event(self, session, host_id, *, enabled, actor_uid):
        self.use_events.append(enabled)
        return 1

    def get_host(self, session, host_id, *, lock=False):
        return next((h for h in self.hosts if h.host_id == host_id), None)


class FakeInstalls:
    def __init__(self, *, unfinished: bool = False) -> None:
        self.unfinished, self.keys, self.rows, self.overdue_calls = unfinished, [], {}, []

    def overdue_installs(self, session, **kw):
        self.overdue_calls.append(kw)
        return []

    def fail_install(self, *a, **k):
        return False

    def unfinished_install_of_host(self, session, host_id):
        return "exai_OLD" if self.unfinished else None

    def insert_key(self, session, **kw):
        self.keys.append(kw)

    def insert_install(self, session, **kw):
        record = InstallRecord(
            install_id=str(kw["install_id"]), connection_id=None, state="requested", access=kw["access"], ssh_host=kw["ssh_host"],
            ssh_port=kw["ssh_port"], ssh_user=kw["ssh_user"], key_secret_id=kw["key_secret_id"],
            public_key=self.keys[-1]["public_material"], observed_host_key=None, confirmed_host_key_fingerprint=None,
            host_key_confirmed_at=None, host_key_confirmed_by=None, package_version=kw["package_version"],
            package_sha256=kw["package_sha256"], failure_reason=None, key_removed_at=None, created_at=T0, created_by=kw["actor_uid"],
            updated_at=T0, finished_at=None, host_id=kw["host_id"])
        self.rows[record.install_id] = record
        return record

    def get_install(self, session, install_id, *, lock=False):
        return self.rows.get(install_id)


class NoUpgrade:
    """The session of the upgrade guard: no connection holds the name."""

    def execute(self, statement, params=None):
        return SimpleNamespace(all=lambda: [], scalar_one=lambda: False)


def _create(hosts: FakeHosts, installs: FakeInstalls, ring: Ring | None, *, access: str = "generated_key", private_key: str | None = None,
            ledger: Ledger | None = None, name: str = "adm1.hlab.kz", roles: Any = ("admin",)):
    return create_host_agent_install(
        NoUpgrade(), display_name=name, access=access, ssh_host="agent-host.example", ssh_port=22, ssh_user="ubuntu",  # type: ignore[arg-type]
        private_key=private_key, ring=ring, roles=roles, idempotency_key=KEY, actor_uid=ADMIN, hosts=hosts, installs=installs,  # type: ignore[arg-type]
        commands=ledger or Ledger(), package_source=lambda: PACKAGE, journal=Journal())


def test_a_generated_key_is_sealed_as_a_secret_of_the_host_and_only_its_public_half_comes_back() -> None:
    hosts, installs, ring = FakeHosts(), FakeInstalls(), Ring()
    record = _create(hosts, installs, ring)
    (key,) = installs.keys
    assert key["host_id"] == HOST and key.get("connection_id") is None, "the key is the host's: executor_secret.host_id, no connection"
    assert key["kid"] == "kid-1" and key["ciphertext"] == b"envelope" and key["public_material"].startswith("ssh-ed25519 ")
    plaintext, associated = ring.sealed[0]
    assert b"PRIVATE KEY" in plaintext and associated["connection_id"] == HOST and associated["purpose"] == "agent_install_key", (
        "sealed to the host's identity, so it opens for that host and no other")
    assert (record.host_id, record.connection_id, record.state, record.public_key) == (HOST, None, "requested", key["public_material"])
    assert hosts.use_events == [True], "a new server is on"
    assert b"PRIVATE KEY" not in repr(record).encode()


def test_a_pasted_key_is_sealed_and_comes_back_as_nothing() -> None:
    installs = FakeInstalls()
    record = _create(FakeHosts(), installs, Ring(), access="pasted_key", private_key="-----BEGIN OPENSSH PRIVATE KEY-----\nPASTED\n-----END OPENSSH PRIVATE KEY-----\n")
    assert installs.keys[0]["public_material"] is None and record.public_key is None


def test_the_existing_host_of_a_name_gets_the_session_and_no_second_host_is_made() -> None:
    hosts = FakeHosts(existing=True)
    record = _create(hosts, FakeInstalls(), Ring())
    assert record.host_id == HOST and len(hosts.hosts) == 1 and hosts.use_events == []


def test_one_session_per_host_may_be_unfinished() -> None:
    with pytest.raises(DomainError) as refused:
        _create(FakeHosts(existing=True), FakeInstalls(unfinished=True), Ring())
    assert refused.value.detail_fields["conflict_reason"] == "install_in_progress"


def test_an_overdue_session_of_the_host_is_looked_for_before_the_conflict_check() -> None:
    installs = FakeInstalls()
    _create(FakeHosts(existing=True), installs, Ring())
    assert installs.overdue_calls and installs.overdue_calls[0]["host_id"] == HOST and installs.overdue_calls[0]["connection_id"] is None


@pytest.mark.parametrize(("kwargs", "code"), [
    ({"roles": ("expert",)}, ErrorCode.PERMISSION_DENIED),
    ({"ring": None}, ErrorCode.DEPENDENCY_UNAVAILABLE),
    ({"access": "pasted_key"}, ErrorCode.VALIDATION_FAILED),
    ({"access": "generated_key", "private_key": "x" * 20}, ErrorCode.VALIDATION_FAILED),
])
def test_what_the_contract_refuses_is_refused_before_a_key_is_stored(kwargs: dict[str, Any], code: ErrorCode) -> None:
    installs = FakeInstalls()
    arguments = {"ring": Ring(), **kwargs}
    with pytest.raises(DomainError) as refused:
        _create(FakeHosts(), installs, arguments.pop("ring"), **arguments)
    assert refused.value.code is code and installs.keys == []


def test_a_repeat_of_the_key_answers_the_session_it_made() -> None:
    hosts, installs = FakeHosts(), FakeInstalls()
    first = _create(hosts, installs, Ring())

    class Replay(Ledger):
        def begin(self, session, **kw):
            return CommandReplay(command_id="cmd_r", outcome={"install_id": first.install_id})  # type: ignore[arg-type]

    again = _create(hosts, installs, Ring(), ledger=Replay())
    assert again is first and len(installs.keys) == 1


def test_a_session_is_read_only_through_its_own_host() -> None:
    installs = FakeInstalls()
    record = _create(FakeHosts(), installs, Ring())
    assert get_host_agent_install(None, host_id=HOST, install_id=record.install_id, repository=installs).install_id == record.install_id  # type: ignore[arg-type]
    for host_id, install_id in (("exh_01M2545JSD15ETSNNV904X991N", record.install_id), (HOST, "exai_01M2545JSD15ETSNNV904X991N")):
        with pytest.raises(DomainError) as refused:
            get_host_agent_install(None, host_id=host_id, install_id=install_id, repository=installs)  # type: ignore[arg-type]
        assert refused.value.code is ErrorCode.NOT_FOUND


def test_the_host_key_is_confirmed_by_the_exact_fingerprint_the_worker_observed() -> None:
    import dataclasses

    awaiting = InstallRecord(
        install_id=INSTALL, connection_id=None, state="awaiting_host_key", access="generated_key", ssh_host="h", ssh_port=22, ssh_user="u",
        key_secret_id="exs_X", public_key="ssh-ed25519 AAAA", observed_host_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEXAMPLE", confirmed_host_key_fingerprint=None,
        host_key_confirmed_at=None, host_key_confirmed_by=None, package_version="0.21.0", package_sha256="a" * 64, failure_reason=None,
        key_removed_at=None, created_at=T0, created_by=ADMIN, updated_at=T0, finished_at=None, host_id=HOST)

    class Installs:
        def __init__(self) -> None:
            self.record, self.confirmed = awaiting, []

        def get_install(self, session, install_id, *, lock=False):
            return self.record

        def confirm_host_key(self, session, install_id, *, fingerprint, actor_uid):
            self.confirmed.append(fingerprint)
            self.record = dataclasses.replace(self.record, state="installing", confirmed_host_key_fingerprint=fingerprint)
            return True

    installs = Installs()
    other = "SHA256:" + "B" * 43
    with pytest.raises(DomainError) as refused:
        confirm_host_agent_install_host_key(None, host_id=HOST, install_id=INSTALL, fingerprint=other, roles=("admin",), idempotency_key=KEY,  # type: ignore[arg-type]
                                            actor_uid=ADMIN, repository=installs, commands=Ledger(), journal=Journal())  # type: ignore[arg-type]
    assert refused.value.detail_fields["conflict_reason"] == "host_key_changed" and installs.confirmed == []
    with pytest.raises(DomainError) as unknown:
        confirm_host_agent_install_host_key(None, host_id="exh_01M2545JSD15ETSNNV904X991N", install_id=INSTALL, fingerprint=other,  # type: ignore[arg-type]
                                            roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN, repository=installs, commands=Ledger(), journal=Journal())  # type: ignore[arg-type]
    assert unknown.value.code is ErrorCode.NOT_FOUND
    exact = observed_fingerprint(awaiting)
    done = confirm_host_agent_install_host_key(None, host_id=HOST, install_id=INSTALL, fingerprint=exact, roles=("admin",), idempotency_key=KEY,  # type: ignore[arg-type]
                                               actor_uid=ADMIN, repository=installs, commands=Ledger(), journal=Journal())  # type: ignore[arg-type]
    assert done.state == "installing" and installs.confirmed == [exact]


def test_the_stand_keeps_no_secret_or_key_in_what_the_host_session_journals() -> None:
    journal = Journal()
    create_host_agent_install(
        NoUpgrade(), display_name="adm1.hlab.kz", access="generated_key", ssh_host="agent-host.example", ssh_port=22, ssh_user="ubuntu",  # type: ignore[arg-type]
        private_key=None, ring=Ring(), roles=("admin",), idempotency_key=KEY, actor_uid=ADMIN, hosts=FakeHosts(), installs=FakeInstalls(),  # type: ignore[arg-type]
        commands=Ledger(), package_source=lambda: PACKAGE, journal=journal)
    for event in journal.events:
        assert set(event["payload"]) <= {"host_id", "secret_id", "purpose", "state", "actor_uid", "enabled"}
        assert "PRIVATE" not in repr(event) and "ssh-ed25519" not in repr(event)
    assert "executor.agent_install_requested" in journal.types()


def test_the_remote_report_of_the_stands_line_is_still_read_as_before() -> None:
    assert key_line_state(b"am-install: key-line removed\n") == "host_line_removed"
    assert host_commands.INSTALL_PURPOSE == "agent_install_key"
