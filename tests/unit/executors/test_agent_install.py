"""`EXEC2-ENROLL-SSH-01`: the worker's half of path A (B2 section 11 item 1) -- an agent installed over SSH from
the UI, against a scripted SSH host.

No database, no network, no real SSH: the repository, the command ledger, the grant and the journal are
stand-ins, and the SSH host is :class:`ScriptedHost`. The one part that is real is the **remote bootstrap**: the
tests at the bottom run the very text the worker sends (``REMOTE_COMMAND``) with ``bash`` on this machine, against
a stand-in ``sudo`` and a package whose ``install.sh`` records what it was given. What is shown:

* the claim is durable and exclusive: ``requested -> scanning`` is stored, an install is claimed by the grant's
  ledger key (``agent-install:<install_id>``), and a second worker (or a restarted one) leaves a claimed session
  alone -- including a worker that read the session at the same moment and reached the grant second. A worker that
  fails *before* it won the grant (a host key that changed, a missing package, a refused grant, an unexpected error)
  ends the session only after locking its row and finding no grant in the ledger, and the grant is issued under the
  same row lock; the model the payload names is read in the grant's own transaction;
* the destination rules run **before any connection**, on the scan and again on the install; a refused target never
  reaches the transport. A private range is refused unless the stand sets ``AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE=1``
  (`R-149g`; anything but ``1`` is not a yes), which asks the rules about the ``vpn`` transport for the scan and the
  install alike -- loopback, link-local, the compose network and service names stay refused, and the log names only
  the refusal's closed category;
* no trust on first use: the host key is stored write-once by the scan; an install runs only when the key seen now
  equals the key the administrator confirmed, and the connection is pinned to it (``host_key_changed`` otherwise,
  with no grant issued and nothing sent);
* the grant is the administrator's issue, attributed to the session's creator, and a retry is a new session with a
  fresh grant on the same connection; an absent or malformed public origin ends the session (``enrollment_failed``)
  and is never guessed;
* the secret is on no argument vector, local or remote: the remote command is constant text, the secret is a line
  of stdin, and in the remote shell it reaches ``install.sh`` as an environment variable only; and it is in no
  event, log line, ledger entry or error;
* the package the host receives is the image's archive byte for byte, verified on the host by the digest path B's
  command carries; ``sudo`` that asks for a password, an ``install.sh`` that exits non-zero and a grant that was
  never redeemed all end the session ``failed`` with a sanitised reason;
* at the end the sealed key is replaced and no longer named by the session, and the stand's ``authorized_keys``
  line is removed on the host.

Unexecuted in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import ipaddress
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from auditmanager.executors import agent_install_runner as runner_module
from auditmanager.executors.agent_install import (
    INSTALL_MARKER_PREFIX,
    INSTALL_SESSION_SECONDS,
    authorized_keys_line,
    install_destination,
    install_marker,
)
from auditmanager.executors.agent_install_repository import (
    STALE_SCAN_SECONDS,
    AgentInstallRepository,
    InstallRecord,
)
from auditmanager.executors.agent_install_runner import (
    ALLOW_PRIVATE_ENV,
    EXIT_FAILURES,
    FAILURES,
    GRANT_COMMAND_TYPE,
    PRIVATE_INSTALL_TRANSPORT,
    REMOTE_COMMAND,
    AgentInstallRunner,
    RemoteResult,
    SshInstallTransport,
    allow_private_targets,
    build_payload,
    failure_for,
    grant_key,
    key_line_state,
)
from auditmanager.executors.agent_package import AgentPackage
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.model import (
    AGENT_INSTALL_FAILURES,
    GENERIC_PURPOSES,
    ConnectionRecord,
    host_key_fingerprint,
)
from auditmanager.executors.public import SecretUnreadableError
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.ssh_transport import SshFailure
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[3]
T0 = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
NOW = T0 + timedelta(minutes=5)
CREATOR = "usr_01M2545JSD15ETSNNV904X991K"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
INSTALL = "exai_01M2545JSD15ETSNNV904X991K"
SECOND = "exai_01M2545JSD15ETSNNV904X991M"
KEY_SECRET = "exs_01M2545JSD15ETSNNV904X991K"
ARCHIVE = b"\x1f\x8b the agent package, as the image holds it"
PACKAGE = AgentPackage(
    version="0.9.0", sha256=hashlib.sha256(ARCHIVE).hexdigest(), size_bytes=len(ARCHIVE),
    path=Path("/nonexistent/auditmanager-agent-0.9.0.tar.gz"))
PUBLIC = "93.184.216.34"
HOST, PORT, USER = "agent-host.example", 22, "ubuntu"
ORIGIN = "https://stand.example"
MODEL = "claude-opus-5"
PEM_BODY = "PASTED-KEY-BODY-THAT-MUST-NEVER-BE-LOGGED-OR-SENT-IN-AN-ARGUMENT"
PEM = f"-----BEGIN OPENSSH PRIVATE KEY-----\n{PEM_BODY}\n-----END OPENSSH PRIVATE KEY-----\n"
SUCCESS = RemoteResult(
    "completed", exit_status=0, stdout=b"am-install: installed\nam-install: key-line removed\n")


def host_key_line() -> str:
    return Ed25519PrivateKey.generate().public_key().public_bytes(
        Encoding.OpenSSH, PublicFormat.OpenSSH).decode("ascii")


# -- stand-ins -----------------------------------------------------------------------------------


class FakeSession:
    """What the runner asks of a session: to be committed. Anything else is a bug in the runner. A commit makes what
    the ledger staged durable; a transaction that ends without one drops it (:meth:`World.transaction`)."""

    def __init__(self, ledger: FakeLedger | None = None) -> None:
        self.commits = 0
        self.ledger = ledger

    def commit(self) -> None:
        self.commits += 1
        if self.ledger is not None:
            self.ledger.commit()


class FakeInstalls:
    """The worker's half of ``AgentInstallRepository`` in memory, with the same guards on the state."""

    def __init__(self) -> None:
        self.rows: dict[str, InstallRecord] = {}
        self.now = NOW
        self.replaced: list[str] = []
        self.finish_calls: list[dict[str, Any]] = []
        self.locked: list[str] = []   # the sessions whose row was read ``FOR UPDATE``, in order

    def add(self, install_id: str = INSTALL, *, state: str = "requested", access: str = "generated_key",
            host: str = HOST, port: int = PORT, user: str = USER, created_at: datetime = T0,
            observed: str | None = None, confirmed: str | None = None,
            key_secret: str | None = KEY_SECRET, package: AgentPackage | None = PACKAGE,
            updated_at: datetime | None = None) -> InstallRecord:
        record = InstallRecord(
            install_id=install_id, connection_id=CONNECTION, state=state, access=access, ssh_host=host,
            ssh_port=port, ssh_user=user, key_secret_id=key_secret, public_key=None,
            observed_host_key=observed, confirmed_host_key_fingerprint=confirmed,
            host_key_confirmed_at=None if confirmed is None else NOW, host_key_confirmed_by=None
            if confirmed is None else CREATOR, package_version=None if package is None else package.version,
            package_sha256=None if package is None else package.sha256, failure_reason=None,
            key_removed_at=None, created_at=created_at, created_by=CREATOR,
            updated_at=updated_at or created_at, finished_at=None)
        self.rows[install_id] = record
        return record

    def _age(self, record: InstallRecord) -> float:
        return (self.now - record.created_at).total_seconds()

    def get_install(self, session, install_id, *, lock=False):
        if lock:
            self.locked.append(install_id)
        return self.rows.get(install_id)

    def claim_requested(self, session, *, seconds, stale_scan_seconds=STALE_SCAN_SECONDS):
        for record in sorted(self.rows.values(), key=lambda row: (row.created_at, row.install_id)):
            stale = (record.state == "scanning" and record.observed_host_key is None
                     and (self.now - record.updated_at).total_seconds() > stale_scan_seconds)
            if (record.state == "requested" or stale) and self._age(record) < seconds:
                self.rows[record.install_id] = dataclasses.replace(record, state="scanning", updated_at=self.now)
                return self.rows[record.install_id]
        return None

    def installing(self, session, *, seconds, limit):
        found = [row for row in sorted(self.rows.values(), key=lambda row: (row.created_at, row.install_id))
                 if row.state == "installing" and self._age(row) < seconds]
        return found[:limit]

    def record_observed_host_key(self, session, install_id, *, host_key):
        row = self.rows[install_id]
        if row.state != "scanning" or row.observed_host_key is not None:
            return False
        self.rows[install_id] = dataclasses.replace(
            row, state="awaiting_host_key", observed_host_key=host_key, updated_at=self.now)
        return True

    def finish_install(self, session, *, install_id, connection_id, from_state, state, reason):
        self.finish_calls.append({"install_id": install_id, "from": from_state, "state": state, "reason": reason})
        row = self.rows[install_id]
        if row.state != from_state:
            return False
        assert (state == "failed") == (reason is not None), "ck_executor_agent_install_failure_shape"
        if row.key_secret_id is not None:
            self.replaced.append(row.key_secret_id)
        self.rows[install_id] = dataclasses.replace(
            row, state=state, failure_reason=reason, key_secret_id=None, key_removed_at=row.key_removed_at or self.now,
            finished_at=self.now, updated_at=self.now)
        return True

    # What the API does between the worker's two halves (``confirm_agent_install_host_key``).
    def confirm(self, install_id: str, fingerprint: str | None = None) -> None:
        row = self.rows[install_id]
        assert row.state == "awaiting_host_key" and row.observed_host_key is not None
        self.rows[install_id] = dataclasses.replace(
            row, state="installing", confirmed_host_key_fingerprint=fingerprint or host_key_fingerprint(
                row.observed_host_key), host_key_confirmed_at=self.now, host_key_confirmed_by=CREATOR,
            updated_at=self.now)


class FakeLedger:
    """``CommandRepository``, as far as the worker reads it: ``UNIQUE (command_type, idempotency_key)``. The
    only writer is :class:`FakeGrants`, as ``issue_executor_enrollment`` is the only writer in production."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict[str, Any]] = {}
        self.staged: dict[tuple[str, str], dict[str, Any]] = {}   # written by a transaction that has not committed

    def find(self, session, *, command_type, idempotency_key):
        return self.rows.get((command_type, str(idempotency_key)))

    def commit(self) -> None:
        self.rows.update(self.staged)
        self.staged.clear()

    def rollback(self) -> None:
        self.staged.clear()

    def claim(self, install_id: str) -> None:
        """What a worker that issued the grant and then died left behind."""
        self.rows[(GRANT_COMMAND_TYPE, grant_key(install_id))] = {"state": "succeeded", "outcome": {}}


class FakeExecutors:
    def __init__(self) -> None:
        self.kind, self.archived, self.revision, self.model = "pull", False, True, MODEL

    def get_connection(self, session, connection_id, *, lock=False):
        return ConnectionRecord(
            connection_id=connection_id, kind=self.kind, display_name="Claude", created_at=T0, created_by=CREATOR,
            archived_at=T0 if self.archived else None, archived_by=CREATOR if self.archived else None)

    def current_revisions(self, session, connection_ids):
        revision = SimpleNamespace(settings=SimpleNamespace(gateway_model=self.model))
        return {connection_id: revision for connection_id in connection_ids} if self.revision else {}


class FakeEnrollments:
    """The grants the worker issued, and which of them an agent has redeemed."""

    def __init__(self) -> None:
        self.redeemed: set[str] = set()
        self.by_secret: dict[str, str] = {}

    def get_enrollment(self, session, enrollment_id, *, lock=False):
        return SimpleNamespace(enrollment_id=enrollment_id,
                               redeemed_at=NOW if enrollment_id in self.redeemed else None)


class FakeGrants:
    """``issue_executor_enrollment``: records how it was called, returns a fresh secret each time, and takes the
    ledger key it was given -- a second call under the same key is ``conflict`` / ``enrollment_shown_once``."""

    def __init__(self, enrollments: FakeEnrollments, ledger: FakeLedger) -> None:
        self.enrollments, self.ledger, self.calls = enrollments, ledger, []
        self.refuse: DomainError | None = None

    def __call__(self, session, **kwargs):
        if self.refuse is not None:
            raise self.refuse
        key = (GRANT_COMMAND_TYPE, kwargs["idempotency_key"])
        if key in self.ledger.rows or key in self.ledger.staged:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="enrollment_shown_once")
        number = len(self.calls) + 1
        secret, enrollment_id = f"ame_{number:08d}_" + "A" * 43, f"exen_01M2545JSD15ETSNNV904X99{number:02d}"
        self.ledger.staged[key] = {"state": "succeeded", "outcome": {"enrollment_id": enrollment_id}}
        self.calls.append({**kwargs, "secret_digest": hashlib.sha256(secret.encode()).hexdigest()})
        self.enrollments.by_secret[secret] = enrollment_id
        kwargs["journal"](session, event_type="executor.enrollment_issued", aggregate_type="ExecutorEnrollment",
                          aggregate_id=enrollment_id,
                          payload={"connection_id": kwargs["connection_id"], "actor_uid": kwargs["actor_uid"]})
        return SimpleNamespace(secret=secret, record=SimpleNamespace(enrollment_id=enrollment_id),
                               package=kwargs["package_source"]())


class Journal:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def __call__(self, session, *, event_type, aggregate_type, aggregate_id, payload=None, **_) -> None:
        self.events.append({"event_type": event_type, "aggregate_type": aggregate_type,
                            "aggregate_id": aggregate_id, "payload": dict(payload or {})})

    def of(self, event_type: str) -> list[dict[str, Any]]:
        return [event for event in self.events if event["event_type"] == event_type]


class ScriptedHost:
    """The SSH host: ``scan`` shows a host key, ``execute`` records the call and answers as scripted.

    ``redeem`` makes the agent on the host enroll the way ``install.sh`` does: it reads the secret from the first
    lines of the payload and redeems the grant that secret belongs to."""

    def __init__(self, key_line: str, enrollments: FakeEnrollments) -> None:
        self.key_line, self.enrollments = key_line, enrollments
        self.scan_failure: Exception | None = None
        self.scans: list[Any] = []
        self.calls: list[dict[str, Any]] = []
        self.answer = SUCCESS
        self.redeem = True

    def scan(self, endpoint):
        self.scans.append(endpoint)
        if self.scan_failure is not None:
            raise self.scan_failure
        return self.key_line

    def execute(self, endpoint, private_key, host_key, payload, *, timeout_s):
        self.calls.append({"endpoint": endpoint, "private_key": private_key, "host_key": host_key,
                           "payload": payload, "timeout_s": timeout_s})
        if self.redeem and self.answer.exit_status == 0:
            self.enrollments.redeemed.add(self.enrollments.by_secret[payload.split(b"\n")[1].decode()])
        return self.answer


class World:
    """One worker with every collaborator a stand-in. ``pump`` is one pass of the worker's loop, waited for."""

    def __init__(self) -> None:
        self.installs, self.ledger, self.executors = FakeInstalls(), FakeLedger(), FakeExecutors()
        self.session = FakeSession(self.ledger)
        self.enrollments = FakeEnrollments()
        self.grants = FakeGrants(self.enrollments, self.ledger)
        self.journal = Journal()
        self.host = ScriptedHost(host_key_line(), self.enrollments)
        self.opened: list[tuple[str, str]] = []
        self.unreadable = False
        self.package_error: DomainError | None = None
        self.package = (PACKAGE, ARCHIVE)
        self.now = NOW
        self.environ = {"AUDITMANAGER_PUBLIC_ORIGIN": ORIGIN}
        self.resolves = [PUBLIC]
        self.runner = self.build()

    def build(self, **changes: Any) -> AgentInstallRunner:
        options: dict[str, Any] = dict(
            ring=object(), policy=DestinationPolicy(resolver=lambda host, port: self.resolves, networks=lambda: ()),
            environ=self.environ, transport=self.host, installs=self.installs, executors=self.executors,
            enrollments=self.enrollments, commands=self.ledger, journal=self.journal, issue_grant=self.grants,
            open_key=self.open_key, load=self.load, clock=lambda: self.now)
        options.update(changes)
        self.installs.now = self.now
        return AgentInstallRunner(self.transaction, **options)  # type: ignore[arg-type]

    @contextmanager
    def transaction(self):
        """One short transaction: what it staged in the ledger is durable only if it committed."""
        try:
            yield self.session
        finally:
            self.ledger.rollback()

    def open_key(self, session, ring, *, secret_id, destination, repository=None):
        self.opened.append((secret_id, destination))
        if self.unreadable:
            raise SecretUnreadableError()
        return PEM

    def load(self, version, *, directory):
        if self.package_error is not None:
            raise self.package_error
        assert version == PACKAGE.version
        return self.package

    def pump(self) -> int:
        taken = self.runner.run_pending()
        self.runner.join(10)
        return taken

    def to_awaiting(self, install_id: str = INSTALL, **row: Any) -> InstallRecord:
        self.installs.add(install_id, **row)
        assert self.pump() == 1
        record = self.installs.rows[install_id]
        assert record.state == "awaiting_host_key", record.state
        return record

    def to_installing(self, install_id: str = INSTALL, **row: Any) -> InstallRecord:
        self.to_awaiting(install_id, **row)
        self.installs.confirm(install_id)
        return self.installs.rows[install_id]

    def installed(self, install_id: str = INSTALL, **row: Any) -> InstallRecord:
        self.to_installing(install_id, **row)
        assert self.pump() == 1
        return self.installs.rows[install_id]

    @property
    def everything_recorded(self) -> str:
        """All that the worker wrote down besides the session's own row (which holds the target by design): the
        journal's events and the ledger's rows, as text."""
        return json.dumps({"events": self.journal.events, "ledger": {str(k): v for k, v in self.ledger.rows.items()}},
                          default=str)


@pytest.fixture
def world() -> World:
    return World()


# -- the scan: requested -> scanning -> awaiting_host_key --------------------------------------------


def test_a_requested_session_is_scanned_and_waits_for_the_administrators_confirmation(world: World) -> None:
    world.installs.add()
    assert world.pump() == 1
    record = world.installs.rows[INSTALL]
    assert (record.state, record.observed_host_key) == ("awaiting_host_key", world.host.key_line)
    (endpoint,) = world.host.scans
    assert (endpoint.host, endpoint.port, endpoint.user) == (PUBLIC, PORT, USER), "the validated address, not the name"
    assert world.host.calls == [], "nothing is installed before the key is confirmed"
    (event,) = world.journal.of("executor.agent_install_host_key_observed")
    assert event["aggregate_id"] == INSTALL and event["payload"] == {
        "connection_id": CONNECTION, "state": "awaiting_host_key"}
    assert world.pump() == 0, "an awaiting session is not taken again"


def test_a_session_is_claimed_as_scanning_before_the_host_is_touched(world: World) -> None:
    """``scanning`` is the durable claim: it is stored by the claim, before the network."""
    states: list[str] = []
    original = world.host.scan

    def watch(endpoint):
        states.append(world.installs.rows[INSTALL].state)
        return original(endpoint)

    world.host.scan = watch  # type: ignore[method-assign]
    world.installs.add()
    world.pump()
    assert states == ["scanning"]


def test_a_scan_a_dead_worker_left_is_taken_again_after_a_while_and_a_fresh_one_is_not(world: World) -> None:
    world.installs.add(state="scanning", updated_at=NOW - timedelta(seconds=STALE_SCAN_SECONDS - 5))
    assert world.pump() == 0 and world.host.scans == [], "another worker may be scanning it right now"
    world.installs.add(SECOND, state="scanning", updated_at=NOW - timedelta(seconds=STALE_SCAN_SECONDS + 5))
    assert world.pump() == 1
    assert world.installs.rows[SECOND].state == "awaiting_host_key" and world.installs.rows[INSTALL].state == "scanning"
    assert len(world.host.scans) == 1


def test_a_session_older_than_its_lifetime_is_not_taken(world: World) -> None:
    world.installs.add(created_at=NOW - timedelta(seconds=INSTALL_SESSION_SECONDS + 1))
    assert world.pump() == 0 and world.host.scans == []


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "169.254.169.254", "postgres", "[::1]"])
def test_a_target_the_destination_rules_refuse_is_never_connected_to(world: World, host: str) -> None:
    """Before any connection: not even the host-key scan reaches a refused target."""
    world.resolves = [PUBLIC]
    world.installs.add(host=host)
    assert world.pump() == 1
    assert world.installs.rows[INSTALL].state == "failed"
    assert world.installs.rows[INSTALL].failure_reason == "host_unreachable"
    assert world.host.scans == [] and world.host.calls == []


@pytest.mark.parametrize("address", ["10.0.0.5", "192.168.1.9", "172.16.0.4", "127.0.0.2", "169.254.10.10"])
def test_a_name_that_resolves_to_an_unpermitted_address_is_refused(world: World, address: str) -> None:
    world.resolves = [PUBLIC, address]
    world.installs.add()
    world.pump()
    assert world.installs.rows[INSTALL].failure_reason == "host_unreachable"
    assert world.host.scans == []


def test_an_address_outside_the_allowed_hosts_is_refused(world: World) -> None:
    world.runner = world.build(policy=DestinationPolicy(
        allowed_hosts=("other.example",), resolver=lambda host, port: [PUBLIC], networks=lambda: ()))
    world.installs.add()
    world.pump()
    assert world.installs.rows[INSTALL].failure_reason == "host_unreachable" and world.host.scans == []


def test_a_host_that_gives_no_key_ends_the_session_as_unreachable(world: World) -> None:
    world.host.scan_failure = SshFailure("unreachable", "no host key observed", sent=False)
    world.installs.add()
    world.pump()
    row = world.installs.rows[INSTALL]
    assert (row.state, row.failure_reason, row.key_secret_id) == ("failed", "host_unreachable", None)
    assert world.installs.replaced == [KEY_SECRET], "the sealed key is replaced when the session ends"


def test_the_destination_policy_is_the_one_every_executor_destination_passes(world: World) -> None:
    seen: list[tuple[str, int, str]] = []

    class Spy(DestinationPolicy):
        def check(self, host, port, *, transport):
            seen.append((host, port, transport))
            return super().check(host, port, transport=transport)

    world.runner = world.build(policy=Spy(resolver=lambda host, port: [PUBLIC], networks=lambda: ()))
    world.installs.add()
    world.pump()
    assert seen == [(HOST, PORT, runner_module.INSTALL_TRANSPORT)] and runner_module.INSTALL_TRANSPORT == "ssh_command"


# -- private-range targets: one stand setting, `R-149g` ---------------------------------------------------------

PRIVATE_ADDRESSES = ["10.0.0.5", "192.168.1.9", "172.16.0.4", "100.64.0.7", "fd00::5"]


def with_setting(world: World, value: str | None) -> None:
    """The worker as the stand starts it with ``AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE`` set to ``value``
    (``None``: not set at all). The setting is read once, when the runner is built."""
    world.environ.pop(ALLOW_PRIVATE_ENV, None)
    if value is not None:
        world.environ[ALLOW_PRIVATE_ENV] = value
    world.runner = world.build()


def refused_before_any_connection(world: World) -> None:
    assert world.pump() == 1
    row = world.installs.rows[INSTALL]
    assert (row.state, row.failure_reason) == ("failed", "host_unreachable")
    assert world.host.scans == [] and world.host.calls == []


def test_the_setting_is_one_or_zero_and_anything_else_is_not_a_yes() -> None:
    assert ALLOW_PRIVATE_ENV == "AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE" and PRIVATE_INSTALL_TRANSPORT == "vpn"
    assert allow_private_targets({ALLOW_PRIVATE_ENV: "1"}) is True
    assert allow_private_targets({ALLOW_PRIVATE_ENV: " 1 "}) is True, "the whitespace of an env file is not a value"
    for off in ({}, {ALLOW_PRIVATE_ENV: "0"}, {ALLOW_PRIVATE_ENV: ""}, {ALLOW_PRIVATE_ENV: "  "}):
        assert allow_private_targets(off) is False, off
    for invalid in ("true", "True", "yes", "on", "2", "01", "-1", "1.0", "enabled", "1,0"):
        assert allow_private_targets({ALLOW_PRIVATE_ENV: invalid}) is False, invalid


@pytest.mark.parametrize("address", PRIVATE_ADDRESSES)
def test_with_the_setting_on_a_private_target_is_scanned_and_installed(world: World, address: str) -> None:
    with_setting(world, "1")
    world.resolves = [address]
    row = world.installed()
    assert (row.state, row.failure_reason) == ("succeeded", None)
    assert {endpoint.host for endpoint in world.host.scans} == {address}, "the scan and the rescan went to the address"
    (call,) = world.host.calls
    assert call["endpoint"].host == address


@pytest.mark.parametrize("value", [None, "0", "", " 0 "])
@pytest.mark.parametrize("address", PRIVATE_ADDRESSES)
def test_with_the_setting_off_or_absent_a_private_target_is_refused_as_before(
    world: World, address: str, value: str | None,
) -> None:
    with_setting(world, value)
    world.resolves = [address]
    world.installs.add()
    refused_before_any_connection(world)


@pytest.mark.parametrize("value", ["true", "yes", "on", "2", "01", "-1", "1.0", "enabled"])
def test_a_value_that_is_neither_one_nor_zero_leaves_private_targets_refused_and_says_so_by_name(
    world: World, caplog, value: str,
) -> None:
    with caplog.at_level(logging.WARNING):
        with_setting(world, value)
    assert ALLOW_PRIVATE_ENV in caplog.text, "the stand is not silently different from what the operator wrote"
    world.resolves = ["10.0.0.5"]
    world.installs.add()
    refused_before_any_connection(world)


def test_the_log_names_the_variable_of_an_invalid_value_and_never_the_value(world: World, caplog) -> None:
    with caplog.at_level(logging.WARNING):
        with_setting(world, "PLEASE-9317")
    assert ALLOW_PRIVATE_ENV in caplog.text and "PLEASE-9317" not in caplog.text


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "169.254.169.254", "0.0.0.0", "postgres", "[::1]", "api"])
def test_with_the_setting_on_loopback_link_local_and_service_names_stay_refused(world: World, host: str) -> None:
    with_setting(world, "1")
    world.resolves = ["10.0.0.5"]
    world.installs.add(host=host)
    refused_before_any_connection(world)


@pytest.mark.parametrize("answers", [
    ["127.0.0.2"], ["169.254.10.10"], ["10.0.0.5", "169.254.10.10"], [PUBLIC, "127.0.0.2"], ["::1"], ["fe80::1"],
])
def test_with_the_setting_on_a_name_that_resolves_to_a_forbidden_address_is_refused(
    world: World, answers: list[str],
) -> None:
    with_setting(world, "1")
    world.resolves = answers
    world.installs.add()
    refused_before_any_connection(world)


def test_with_the_setting_on_the_compose_network_stays_refused_and_another_private_range_is_not(world: World) -> None:
    with_setting(world, "1")
    answers = ["10.0.0.5"]
    world.runner = world.build(policy=DestinationPolicy(
        resolver=lambda host, port: answers, networks=lambda: [ipaddress.ip_network("10.0.0.0/24")]))
    world.installs.add()
    refused_before_any_connection(world)
    answers[:] = ["10.1.0.5"]                                  # the same policy, a private address outside it
    assert world.installed(SECOND, key_secret="exs_01M2545JSD15ETSNNV904X991M").state == "succeeded"


def test_with_the_setting_on_the_allowed_hosts_still_narrow(world: World) -> None:
    with_setting(world, "1")
    world.runner = world.build(policy=DestinationPolicy(
        allowed_hosts=("other.example",), resolver=lambda host, port: ["10.0.0.5"], networks=lambda: ()))
    world.installs.add()
    refused_before_any_connection(world)


@pytest.mark.parametrize(("value", "transport"), [(None, "ssh_command"), ("0", "ssh_command"), ("1", "vpn")])
def test_the_scan_and_the_install_ask_the_destination_rules_the_same_question(
    world: World, value: str | None, transport: str,
) -> None:
    seen: list[tuple[str, int, str]] = []

    class Spy(DestinationPolicy):
        def check(self, host, port, *, transport):
            seen.append((host, port, transport))
            return super().check(host, port, transport=transport)

    with_setting(world, value)
    world.runner = world.build(policy=Spy(resolver=lambda host, port: [PUBLIC], networks=lambda: ()))
    assert world.installed().state == "succeeded"
    assert seen == [(HOST, PORT, transport)] * 2, "once for the scan, once for the install, one transport"


@pytest.mark.parametrize(("value", "host", "category"), [
    ("0", "10.0.0.5", "private_range"),
    ("1", "169.254.10.10", "link_local"),
    ("1", "127.0.0.1", "loopback"),
    ("1", "postgres", "service_name"),
])
def test_a_refusal_is_logged_as_its_closed_category_and_nothing_else(
    world: World, caplog, value: str, host: str, category: str,
) -> None:
    with_setting(world, value)
    world.installs.add(host=host)
    with caplog.at_level(logging.DEBUG):
        refused_before_any_connection(world)
    assert category in caplog.text
    assert host not in caplog.text, "never the address or the name"


def test_the_composition_roots_runner_reads_the_setting_from_the_environment_it_is_given() -> None:
    from auditmanager.executors.public import install_runner_for

    def built(environ: dict[str, str]) -> AgentInstallRunner:
        return install_runner_for(lambda: nullcontext(FakeSession()), ring=None, environ=environ)  # type: ignore[arg-type]

    assert built({})._destination_transport == runner_module.INSTALL_TRANSPORT == "ssh_command"
    assert built({ALLOW_PRIVATE_ENV: "1"})._destination_transport == PRIVATE_INSTALL_TRANSPORT == "vpn"
    assert built({ALLOW_PRIVATE_ENV: "yes"})._destination_transport == "ssh_command"


def test_only_the_worker_service_forwards_the_setting_and_it_defaults_to_off_and_is_explained() -> None:
    compose = (ROOT / "infra" / "deploy" / "compose.server.yml").read_text()
    api, worker = _service_block(compose, "api"), _service_block(compose, "worker")
    line = f"      {ALLOW_PRIVATE_ENV}: ${{{ALLOW_PRIVATE_ENV}:-0}}"
    assert worker.splitlines().count(line) == 1, "the worker forwards it, default 0"
    assert ALLOW_PRIVATE_ENV not in api, "the api never reads it"
    readme = (ROOT / "infra" / "deploy" / "README.md").read_text()
    assert ALLOW_PRIVATE_ENV in readme and "hosting's internal networks" in readme and "`1` or `0`" in readme


# -- the claim of an install -------------------------------------------------------------------------


def test_the_claim_of_an_install_is_the_grants_ledger_key_and_it_is_made_before_the_connection(world: World) -> None:
    world.to_installing()
    seen: list[bool] = []
    original = world.host.execute

    def watch(endpoint, private_key, host_key, payload, *, timeout_s):
        seen.append((GRANT_COMMAND_TYPE, grant_key(INSTALL)) in world.ledger.rows)
        return original(endpoint, private_key, host_key, payload, timeout_s=timeout_s)

    world.host.execute = watch  # type: ignore[method-assign]
    assert (GRANT_COMMAND_TYPE, grant_key(INSTALL)) not in world.ledger.rows, "nothing is claimed by looking"
    world.pump()
    assert seen == [True], "the claim was in the ledger when the install connection was made"
    assert world.ledger.rows[(GRANT_COMMAND_TYPE, grant_key(INSTALL))]["outcome"] == {
        "enrollment_id": "exen_01M2545JSD15ETSNNV904X9901"}


def test_a_session_whose_grant_exists_is_not_picked_up_again_by_this_worker_or_another(world: World) -> None:
    """A worker that issued the grant and died, or one that is installing now, holds the claim."""
    world.to_installing()
    world.ledger.claim(INSTALL)
    other = world.build()  # another worker (or this one after a restart) sharing the database
    assert world.runner._claim() is None and other._claim() is None
    assert world.pump() == 0 and world.host.calls == [] and world.grants.calls == []
    assert world.installs.rows[INSTALL].state == "installing", "left alone: the grant may have been spent"


def test_a_claim_that_was_made_and_never_finished_leaves_a_session_that_times_out(world: World) -> None:
    """A worker that dies after its claim leaves ``installing``; nobody installs again, and the session ends by its
    lifetime (the API's sweep) -- from then on it is not even a candidate."""
    world.to_installing()
    world.ledger.claim(INSTALL)
    assert world.pump() == 0 and world.host.calls == []
    world.now = T0 + timedelta(seconds=INSTALL_SESSION_SECONDS + 1)
    world.installs.now = world.now
    assert world.runner._claim() is None


def test_a_session_this_process_is_working_on_is_not_picked_up_a_second_time(world: World) -> None:
    world.to_installing()
    first = world.runner._claim()
    assert first is not None and first.kind == "install"
    world.runner._working.add(INSTALL)  # what ``_start`` does before the thread runs
    assert world.runner._claim() is None


def test_two_workers_that_read_one_session_together_install_it_once(world: World) -> None:
    """Both pass the reads and the host-key comparison; the ledger lets one issue the grant. The other finds the
    key taken, sends nothing and leaves the session as it is."""
    world.to_installing()
    other = world.build()
    work = other._claim()
    assert work is not None
    original = other._verify_host

    def meanwhile_the_first_worker_claims(ready):
        world.ledger.claim(INSTALL)
        return original(ready)

    other._verify_host = meanwhile_the_first_worker_claims  # type: ignore[method-assign]
    other._install(work)
    assert world.host.calls == [] and world.grants.calls == []
    assert world.installs.rows[INSTALL].state == "installing" and world.installs.finish_calls == []
    assert world.journal.of("executor.agent_install_started") == []


@pytest.mark.parametrize("claimed", [True, False])
@pytest.mark.parametrize("how", ["host_key_changed", "package_unavailable", "grant_refused", "unexpected_error"])
def test_a_worker_that_fails_before_it_won_the_grant_ends_the_session_only_if_nobody_holds_it(
    world: World, how: str, claimed: bool,
) -> None:
    """Worker B read the session; worker A then won the grant (``claimed``) and is installing. B's failure comes before
    its own grant, in any of the ways that precede it: B must leave A's session alone. Unclaimed, the same failure
    ends the session -- the guard can fail, and what it guards is only the claimed case."""
    world.to_installing()
    other = world.build()
    work = other._claim()
    assert work is not None
    if claimed:
        world.ledger.claim(INSTALL)
    if how == "host_key_changed":
        world.host.key_line = host_key_line()
        expected = "host_key_changed"
    elif how == "package_unavailable":
        world.package_error = DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="agent_package")
        expected = "package_unavailable"
    elif how == "grant_refused":
        world.grants.refuse = DomainError(ErrorCode.CONFLICT, conflict_reason="connection_archived")
        expected = "enrollment_failed"
    else:
        def explode(ready):
            raise RuntimeError("boom")

        other._verify_host = explode  # type: ignore[method-assign]
        expected = "install_failed"
    other._guarded(work)

    row = world.installs.rows[INSTALL]
    assert world.host.calls == [] and world.grants.calls == []
    if claimed:
        assert row.state == "installing" and row.failure_reason is None
        assert world.installs.finish_calls == [] and world.installs.replaced == [], "the holder's key is not replaced"
        assert world.journal.of("executor.agent_install_failed") == []
    else:
        assert (row.state, row.failure_reason) == ("failed", expected)


def test_the_session_row_is_locked_before_the_ledger_is_read_by_a_worker_that_gives_up(world: World) -> None:
    """The grant is issued with the same row locked (next test), so reading the ledger under the lock sees every grant
    that was begun: a grant in flight is waited for and then seen."""
    world.to_installing()
    other = world.build()
    work = other._claim()
    assert work is not None
    seen: list[list[str]] = []
    find = world.ledger.find

    def watching(session, *, command_type, idempotency_key):
        seen.append(list(world.installs.locked))
        return find(session, command_type=command_type, idempotency_key=idempotency_key)

    world.ledger.find = watching  # type: ignore[method-assign]
    world.host.key_line = host_key_line()
    other._install(work)
    assert seen == [[INSTALL]], "the row was locked when the ledger was read"
    assert world.installs.rows[INSTALL].failure_reason == "host_key_changed"


def test_the_grant_is_issued_with_the_session_row_locked(world: World) -> None:
    world.to_installing()
    at_issue: list[list[str]] = []
    issue = world.grants

    def watching(session, **kwargs):
        at_issue.append(list(world.installs.locked))
        return issue(session, **kwargs)

    world.runner._issue_grant = watching  # type: ignore[assignment]
    world.pump()
    assert at_issue == [[INSTALL]]
    assert world.installs.rows[INSTALL].state == "succeeded", "the worker that won the grant ends its own session"


def test_the_payload_names_the_model_read_in_the_grants_transaction_not_the_one_read_before_the_network(
    world: World,
) -> None:
    world.to_installing()
    trail: list[str] = []
    revisions = world.executors.current_revisions

    def current(session, connection_ids):
        trail.append("revision")
        return revisions(session, connection_ids)

    world.executors.current_revisions = current  # type: ignore[method-assign]
    issue = world.runner._issue_grant

    def granting(session, **kwargs):
        trail.append("grant")
        return issue(session, **kwargs)

    world.runner._issue_grant = granting  # type: ignore[assignment]
    verify = world.runner._verify_host

    def revised_meanwhile(ready):
        world.executors.model = "claude-sonnet-5"   # the connection got a new revision while the host was scanned
        return verify(ready)

    world.runner._verify_host = revised_meanwhile  # type: ignore[method-assign]
    world.pump()
    (call,) = world.host.calls
    assert call["payload"].split(b"\n")[3] == b"claude-sonnet-5", "never the model of the revision read before the grant"
    assert trail == ["revision", "grant", "revision"], "read again after the grant, in the transaction that commits it"


@pytest.mark.parametrize("change", ["invalid_model", "no_revision"])
def test_a_connection_that_cannot_name_a_model_when_the_grant_is_issued_gets_no_grant(world: World, change: str) -> None:
    world.to_installing()
    verify = world.runner._verify_host

    def changed_meanwhile(ready):
        if change == "invalid_model":
            world.executors.model = "claude opus"      # not a name install.sh accepts
        else:
            world.executors.revision = False
        return verify(ready)

    world.runner._verify_host = changed_meanwhile  # type: ignore[method-assign]
    world.pump()
    row = world.installs.rows[INSTALL]
    assert (row.state, row.failure_reason) == ("failed", "enrollment_failed")
    assert world.host.calls == []
    assert (GRANT_COMMAND_TYPE, grant_key(INSTALL)) not in world.ledger.rows, "the grant rolled back with the payload"


def test_two_workers_racing_for_one_requested_session_scan_it_once(world: World) -> None:
    world.installs.add()
    other = world.build()
    assert world.runner._claim() is not None
    assert other._claim() is None, "scanning is stored: the second claim finds nothing requested"


def test_the_grant_command_is_one_the_product_purge_already_classifies_and_the_lane_adds_none() -> None:
    from auditmanager.executors import enrollment

    assert f'"{GRANT_COMMAND_TYPE}"' in Path(enrollment.__file__).read_text(), (
        "the claim is made under the command type ``issue_executor_enrollment`` begins")
    purge = (ROOT / "scripts" / "recovery" / "product_purge.py").read_text()
    assert f'"{GRANT_COMMAND_TYPE}"' in purge, "a command type the purge has not classified stops the purge"
    runner_source = Path(runner_module.__file__).read_text()
    assert "command_type=" not in runner_source.replace("command_type=GRANT_COMMAND_TYPE", ""), (
        "the worker begins no command of its own")


# -- the install --------------------------------------------------------------------------------------


def test_a_confirmed_session_is_installed_and_its_key_is_replaced(world: World) -> None:
    record = world.installed()
    assert (record.state, record.failure_reason, record.key_secret_id) == ("succeeded", None, None)
    assert record.finished_at is not None and record.key_removed_at is not None
    assert world.installs.replaced == [KEY_SECRET]
    ((secret_id, destination),) = world.opened
    assert secret_id == KEY_SECRET and destination == install_destination(
        ssh_host=HOST, ssh_port=PORT, ssh_user=USER), "the key is opened for the endpoint it was sealed for"
    (call,) = world.host.calls
    stored = world.installs.rows[INSTALL].observed_host_key
    assert call["host_key"] == stored == world.host.key_line, "pinned to the stored key"
    assert call["private_key"] == PEM and (call["endpoint"].host, call["endpoint"].port) == (PUBLIC, PORT)
    assert 0 < call["timeout_s"] <= runner_module.INSTALL_CALL_SECONDS
    assert world.installs.finish_calls == [
        {"install_id": INSTALL, "from": "installing", "state": "succeeded", "reason": None}]


def test_the_payload_is_the_stands_grant_and_the_images_archive_byte_for_byte(world: World) -> None:
    """Path A's agent is byte-identical to path B's: the same archive, verified by the digest B's command carries."""
    world.installed()
    (call,) = world.host.calls
    lines = call["payload"].split(b"\n", 7)
    secret = lines[1].decode()
    assert lines[0] == b"AM-INSTALL/1" and lines[2:5] == [ORIGIN.encode(), MODEL.encode(), PACKAGE.sha256.encode()]
    assert int(lines[5]) == len(ARCHIVE) == PACKAGE.size_bytes
    assert lines[6].decode() == install_marker(INSTALL)
    assert lines[7] == ARCHIVE, "nothing but the archive follows the seven header lines"
    assert hashlib.sha256(lines[7]).hexdigest() == PACKAGE.sha256
    assert secret == "ame_00000001_" + "A" * 43 and world.enrollments.by_secret[secret] in world.enrollments.redeemed


def test_the_grant_is_an_administrators_issue_attributed_to_the_sessions_creator(world: World) -> None:
    world.installed()
    (grant,) = world.grants.calls
    assert grant["actor_uid"] == CREATOR and tuple(grant["roles"]) == ("admin",)
    assert grant["connection_id"] == CONNECTION and grant["idempotency_key"] == f"agent-install:{INSTALL}"
    assert grant["configured_origin"] == ORIGIN
    assert grant["package_source"]() == PACKAGE, "the session's own package, not whatever is latest"
    (issued,) = world.journal.of("executor.enrollment_issued")
    assert issued["payload"]["actor_uid"] == CREATOR
    (started,) = world.journal.of("executor.agent_install_started")
    assert started["aggregate_id"] == INSTALL and started["payload"] == {
        "connection_id": CONNECTION, "state": "installing", "actor_uid": CREATOR}


def test_a_pasted_key_has_no_line_of_the_stands_to_remove(world: World) -> None:
    world.installed(access="pasted_key")
    (call,) = world.host.calls
    assert call["payload"].split(b"\n")[6] == b"-"
    (removed,) = world.journal.of("executor.agent_install_key_removed")
    assert removed["payload"]["reason"] == "not_applicable"


def test_the_stands_key_line_is_reported_removed_or_remaining_in_the_journal(world: World) -> None:
    world.installed()
    (removed,) = world.journal.of("executor.agent_install_key_removed")
    assert removed["payload"] == {"connection_id": CONNECTION, "secret_id": KEY_SECRET,
                                  "purpose": "agent_install_key", "reason": "host_line_removed"}
    other = World()
    other.host.answer = RemoteResult("completed", exit_status=0, stdout=b"am-install: installed\n")
    other.installed()
    (said_nothing,) = other.journal.of("executor.agent_install_key_removed")
    assert said_nothing["payload"]["reason"] == "host_line_remains", "no word that it is gone is not a yes"


def test_a_host_key_that_changed_since_the_confirmation_is_refused_before_anything_is_sent(world: World) -> None:
    world.to_installing()
    world.host.key_line = host_key_line()  # the host now shows another key
    assert world.pump() == 1
    row = world.installs.rows[INSTALL]
    assert (row.state, row.failure_reason) == ("failed", "host_key_changed")
    assert world.host.calls == [], "no key, no secret and no package left the stand"
    assert world.grants.calls == [], "a host that is not contacted gets no grant"
    assert world.installs.replaced == [KEY_SECRET]


def test_the_connection_is_pinned_to_the_stored_key_and_ssh_is_the_backstop(world: World) -> None:
    """The rescan matched, but ssh (``StrictHostKeyChecking=yes`` against the stored key) says it changed."""
    world.host.answer = RemoteResult("host_key_changed")
    assert world.installed().failure_reason == "host_key_changed"


def test_a_confirmed_fingerprint_that_is_not_the_stored_keys_is_not_a_confirmation(world: World) -> None:
    world.to_awaiting()
    world.installs.confirm(INSTALL, fingerprint="SHA256:" + "B" * 43)
    world.pump()
    assert world.installs.rows[INSTALL].failure_reason == "host_key_not_confirmed"
    assert world.host.scans[1:] == [] and world.host.calls == [] and world.opened == []


def test_sudo_that_asks_for_a_password_fails_the_session_with_a_clear_reason_and_no_partial_agent(
    world: World,
) -> None:
    world.host.answer = RemoteResult("completed", exit_status=86, stdout=b"am-install: key-line removed\n")
    row = world.installed()
    assert (row.state, row.failure_reason) == ("failed", "sudo_password_required")
    assert world.enrollments.redeemed == set(), "install.sh never ran: the grant is unspent"
    (removed,) = world.journal.of("executor.agent_install_key_removed")
    assert removed["payload"]["reason"] == "host_line_removed", "the stand's line goes whatever the outcome"


@pytest.mark.parametrize(("status", "reason"), sorted({
    64: "install_failed", 65: "package_unavailable", 66: "unsupported_platform", 69: "enrollment_failed",
    77: "install_failed", 78: "enrollment_failed", 81: "install_failed", 82: "install_failed",
    83: "package_unavailable", 84: "package_unavailable", 85: "unsupported_platform",
    86: "sudo_password_required", 87: "install_failed", 1: "install_failed", 2: "install_failed",
    129: "install_failed", 255: "install_failed",
}.items()))
def test_a_remote_exit_status_ends_the_session_with_a_sanitised_reason(world: World, status: int, reason: str) -> None:
    world.host.answer = RemoteResult("completed", exit_status=status, stdout=b"")
    row = world.installed()
    assert (row.state, row.failure_reason) == ("failed", reason)
    assert failure_for(status) == reason


@pytest.mark.parametrize(("outcome", "reason"), [
    ("refused", "ssh_refused"), ("unreachable", "host_unreachable"), ("timed_out", "timed_out"),
    ("broken", "install_failed"), ("host_key_changed", "host_key_changed"), ("anything else", "install_failed"),
])
def test_an_ssh_failure_ends_the_session_with_a_sanitised_reason(world: World, outcome: str, reason: str) -> None:
    world.host.answer = RemoteResult(outcome)
    assert world.installed().failure_reason == reason


def test_a_success_is_not_believed_unless_the_grant_was_redeemed(world: World) -> None:
    """``install.sh`` exits 0 on a host that already holds a token while it refuses the new secret."""
    world.host.redeem = False
    row = world.installed()
    assert (row.state, row.failure_reason) == ("failed", "enrollment_failed")


def test_every_reason_the_worker_can_give_is_one_the_contract_names() -> None:
    assert set(FAILURES) <= set(AGENT_INSTALL_FAILURES) and "no_worker" not in FAILURES
    assert set(EXIT_FAILURES.values()) <= set(FAILURES)
    assert failure_for(None) == "install_failed" and failure_for(0) == "install_failed", "0 is not a failure here"


@pytest.mark.parametrize("environ", [{}, {"AUDITMANAGER_PUBLIC_ORIGIN": ""}, {"AUDITMANAGER_PUBLIC_ORIGIN": "https://"},
                                     {"AUDITMANAGER_PUBLIC_ORIGIN": "not an origin"},
                                     {"AUDITMANAGER_PUBLIC_ORIGIN": "https://stand.example/path"},
                                     {"AUDITMANAGER_PUBLIC_ORIGIN": "https://[::1]"}])
def test_an_absent_or_unusable_public_origin_ends_the_session_and_is_never_guessed(
    world: World, environ: dict[str, str],
) -> None:
    world.environ.clear()
    world.environ.update(environ)
    world.runner = world.build(environ=dict(environ))
    row = world.installed()
    assert (row.state, row.failure_reason) == ("failed", "enrollment_failed")
    assert world.grants.calls == [] and world.host.calls == [] and world.opened == []


def test_a_package_the_image_no_longer_holds_ends_the_session(world: World) -> None:
    world.package_error = DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="agent_package")
    assert world.installed().failure_reason == "package_unavailable"
    assert world.host.calls == [] and world.opened == []


def test_a_package_that_is_not_the_one_the_session_recorded_is_refused(world: World) -> None:
    world.package = (dataclasses.replace(PACKAGE, sha256="c" * 64), ARCHIVE)
    assert world.installed().failure_reason == "package_unavailable"
    assert world.host.calls == []


def test_a_key_that_cannot_be_opened_here_ends_the_session(world: World) -> None:
    world.unreadable = True
    assert world.installed().failure_reason == "secret_unreadable"
    assert world.host.calls == [] and world.grants.calls == []


def test_a_session_whose_key_reference_is_gone_cannot_be_installed(world: World) -> None:
    assert world.installed(key_secret=None).failure_reason == "secret_unreadable"


@pytest.mark.parametrize("change", ["archived", "not_pull", "no_revision"])
def test_a_connection_that_cannot_take_an_agent_ends_the_session(world: World, change: str) -> None:
    if change == "archived":
        world.executors.archived = True
    elif change == "not_pull":
        world.executors.kind = "http_api"
    else:
        world.executors.revision = False
    assert world.installed().failure_reason == "enrollment_failed" and world.host.calls == []


def test_a_grant_the_stand_refuses_ends_the_session(world: World) -> None:
    world.grants.refuse = DomainError(ErrorCode.CONFLICT, conflict_reason="connection_archived")
    assert world.installed().failure_reason == "enrollment_failed" and world.host.calls == []


def test_a_target_that_stops_passing_the_rules_before_the_install_is_not_connected_to(world: World) -> None:
    world.to_installing()
    world.resolves = ["169.254.169.254"]
    world.pump()
    assert world.installs.rows[INSTALL].failure_reason == "host_unreachable"
    assert len(world.host.scans) == 1 and world.host.calls == [] and world.opened == []


def test_an_install_with_too_little_life_left_is_not_started(world: World) -> None:
    world.to_installing()
    world.now = T0 + timedelta(seconds=INSTALL_SESSION_SECONDS - 30)
    world.installs.now = world.now
    world.pump()
    assert world.installs.rows[INSTALL].failure_reason == "timed_out" and world.host.calls == []


def test_the_call_is_bounded_by_the_sessions_remaining_life(world: World) -> None:
    world.to_installing()
    world.now = T0 + timedelta(seconds=INSTALL_SESSION_SECONDS - 200)
    world.installs.now = world.now
    world.pump()
    (call,) = world.host.calls
    assert call["timeout_s"] == pytest.approx(195.0)


def test_a_session_the_api_already_ended_is_left_as_it_was_written(world: World) -> None:
    """The API's sweep ended the session while the install ran: the late write changes nothing."""
    world.to_installing()

    def sweep_then_answer(endpoint, private_key, host_key, payload, *, timeout_s):
        row = world.installs.rows[INSTALL]
        world.installs.rows[INSTALL] = dataclasses.replace(
            row, state="failed", failure_reason="timed_out", key_secret_id=None, finished_at=NOW, key_removed_at=NOW)
        return SUCCESS

    world.host.execute = sweep_then_answer  # type: ignore[method-assign]
    world.enrollments.redeemed.add("exen_01M2545JSD15ETSNNV904X9901")
    world.pump()
    row = world.installs.rows[INSTALL]
    assert (row.state, row.failure_reason) == ("failed", "timed_out")
    assert world.journal.of("executor.agent_install_succeeded") == [] and world.journal.of(
        "executor.agent_install_key_removed") == []
    assert world.installs.replaced == [], "the key the sweep replaced is not replaced a second time"


def test_a_session_that_ended_before_its_install_began_is_left_alone(world: World) -> None:
    world.to_installing()
    work = world.runner._claim()
    assert work is not None
    world.installs.rows[INSTALL] = dataclasses.replace(
        world.installs.rows[INSTALL], state="failed", failure_reason="timed_out", key_secret_id=None,
        finished_at=NOW, key_removed_at=NOW)
    world.runner._install(work)
    assert len(world.host.scans) == 1 and world.host.calls == [] and world.opened == []
    assert world.grants.calls == [] and world.installs.finish_calls == []


def test_an_unexpected_error_is_recorded_as_a_failed_session_and_never_raised(world: World, caplog) -> None:
    world.to_installing()

    def explode(endpoint, private_key, host_key, payload, *, timeout_s):
        raise RuntimeError(f"boom {PEM_BODY} ame_00000001_{'A' * 43}")

    world.host.execute = explode  # type: ignore[method-assign]
    with caplog.at_level(logging.DEBUG):
        world.pump()
    row = world.installs.rows[INSTALL]
    assert (row.state, row.failure_reason) == ("failed", "install_failed")
    assert "RuntimeError" in caplog.text and PEM_BODY not in caplog.text, "the class name, never the message"


def test_a_retry_is_a_new_session_of_the_same_connection_with_a_fresh_enrollment(world: World) -> None:
    world.host.answer = RemoteResult("completed", exit_status=86, stdout=b"")
    first = world.installed()
    assert first.failure_reason == "sudo_password_required"
    world.host.answer = SUCCESS
    second = world.installed(SECOND, key_secret="exs_01M2545JSD15ETSNNV904X991M")
    assert (second.state, second.connection_id) == ("succeeded", first.connection_id) == ("succeeded", CONNECTION)
    one, two = world.grants.calls
    assert one["connection_id"] == two["connection_id"] == CONNECTION
    assert one["idempotency_key"] != two["idempotency_key"] and one["secret_digest"] != two["secret_digest"]
    assert {(GRANT_COMMAND_TYPE, grant_key(INSTALL)), (GRANT_COMMAND_TYPE, grant_key(SECOND))} <= set(
        world.ledger.rows)


# -- no secret anywhere it should not be -------------------------------------------------------------------


def test_no_secret_key_or_host_detail_reaches_an_event_the_ledger_or_the_log(world: World, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        record = world.installed()
    assert record.state == "succeeded"
    (call,) = world.host.calls
    secret = call["payload"].split(b"\n")[1].decode()
    recorded = world.everything_recorded + caplog.text
    fingerprint = host_key_fingerprint(world.host.key_line)
    for needle in (secret, secret[4:], PEM_BODY, "PRIVATE KEY", world.host.key_line.split()[1], fingerprint,
                   HOST, PUBLIC, "bash", "install.sh", "sudo"):
        assert needle not in recorded, needle
    assert set().union(*(event["payload"].keys() for event in world.journal.events)) <= {
        "connection_id", "state", "from_state", "to_state", "reason", "secret_id", "purpose", "actor_uid"}


def test_the_prepared_install_and_the_ready_one_hide_the_key_and_the_payload(world: World) -> None:
    world.to_installing()
    ready = world.runner._ready(world.runner._claim())
    assert isinstance(ready, runner_module._Ready)
    assert PEM_BODY not in repr(ready) and PEM_BODY not in str(ready)
    prepared = runner_module._Prepared(
        record=ready.record, endpoint=SimpleNamespace(), enrollment_id="x", key=PEM, payload=b"ame_secret")  # type: ignore[arg-type]
    assert PEM_BODY not in repr(prepared) and "ame_secret" not in repr(prepared)
    assert "ame_secret" not in repr(RemoteResult("completed", 0, b"ame_secret"))


# -- the payload and the status lines ---------------------------------------------------------------


def test_the_payload_is_seven_lines_then_the_archive() -> None:
    secret = "ame_abcd1234_" + "B" * 43
    payload = build_payload(secret=secret, origin=ORIGIN, model=MODEL, sha256=PACKAGE.sha256, archive=ARCHIVE,
                            marker=install_marker(INSTALL))
    head, _, rest = payload.partition(ARCHIVE)
    assert head.decode().split("\n") == ["AM-INSTALL/1", secret, ORIGIN, MODEL, PACKAGE.sha256, str(len(ARCHIVE)),
                                         install_marker(INSTALL), ""]
    assert rest == b""


@pytest.mark.parametrize(("field", "value"), [
    ("secret", "ame_abcd1234_short"), ("secret", "x" + "ame_abcd1234_" + "B" * 43),
    ("secret", "ame_abcd1234_" + "B" * 43 + "\n"), ("origin", "https://stand.example/path"),
    ("origin", "https://[::1]"), ("origin", "https://stand.example\nAM"), ("model", "claude opus"),
    ("model", "a" * 65), ("sha256", "A" * 64), ("sha256", "a" * 63), ("marker", "auditmanager-install:exai_x"),
    ("marker", ""), ("marker", "--"),
])
def test_a_value_the_bootstrap_would_refuse_is_refused_before_it_leaves_the_stand(field: str, value: str) -> None:
    values = dict(secret="ame_abcd1234_" + "B" * 43, origin=ORIGIN, model=MODEL, sha256=PACKAGE.sha256,
                  archive=ARCHIVE, marker="-")
    values[field] = value
    with pytest.raises(ValueError) as refused:
        build_payload(**values)  # type: ignore[arg-type]
    assert value not in str(refused.value) or not value


@pytest.mark.parametrize("archive", [b"", b"x" * (32 * 1024 * 1024 + 1)])
def test_an_empty_or_oversized_archive_is_refused(archive: bytes) -> None:
    with pytest.raises(ValueError):
        build_payload(secret="ame_abcd1234_" + "B" * 43, origin=ORIGIN, model=MODEL, sha256=PACKAGE.sha256,
                      archive=archive, marker="-")


def test_only_the_three_fixed_status_lines_are_read_from_the_hosts_output() -> None:
    assert key_line_state(b"am-install: installed\nam-install: key-line removed\n") == "host_line_removed"
    assert key_line_state(b"am-install: key-line absent\n") == "host_line_remains"
    assert key_line_state(b"am-install: key-line not-removed\r\n") == "host_line_remains"
    assert key_line_state(b"") is None
    assert key_line_state(b"am-install: key-line removed but not really\nkey-line removed\n") is None
    assert key_line_state(b"PRIVATE KEY\nam-install: key-line removed extra\n") is None


def test_the_marker_is_the_last_field_of_the_line_the_administrator_adds() -> None:
    line = authorized_keys_line("ssh-ed25519 AAAA", INSTALL)
    assert line == f"restrict ssh-ed25519 AAAA {install_marker(INSTALL)}"
    assert line.split()[-1] == f"{INSTALL_MARKER_PREFIX}{INSTALL}" == install_marker(INSTALL)


# -- the remote command is constant ------------------------------------------------------------------------


def bootstrap_text() -> str:
    tokens = shlex.split(REMOTE_COMMAND)
    assert tokens[:4] == ["bash", "--noprofile", "--norc", "-c"] and len(tokens) == 5
    return tokens[4]


def test_the_remote_command_is_one_quoted_script_with_no_single_quote_inside() -> None:
    script = bootstrap_text()
    assert "'" not in script
    assert REMOTE_COMMAND == "bash --noprofile --norc -c '" + script + "'"


def test_the_remote_command_carries_no_value_and_no_secret_shape() -> None:
    assert re.search(r"ame_[0-9a-z]{8}_", REMOTE_COMMAND) is None
    for needle in (HOST, USER, MODEL, ORIGIN, INSTALL, "https://", "SHA256:", PACKAGE.sha256):
        assert needle not in REMOTE_COMMAND
    script = bootstrap_text()
    assert "$secret" in script and "set +x" in script, "the secret is a variable, and tracing is off"
    for line in script.splitlines():
        if "AUDITMANAGER_ENROLLMENT_SECRET" in line and "preserve-env" not in line:
            assert line.strip().startswith("AUDITMANAGER_ENROLLMENT_SECRET=$secret ")
    assert "--package agent.tar.gz --sha256" in script and "sudo -n" in script


def test_the_bootstrap_names_the_variables_install_sh_reads() -> None:
    from auditmanager.executors.agent_package import AGENT_MODEL_ENV, ENROLLMENT_SECRET_ENV, STAND_ORIGIN_ENV

    script = bootstrap_text()
    assert "--preserve-env=" in script
    for name in (ENROLLMENT_SECRET_ENV, STAND_ORIGIN_ENV, AGENT_MODEL_ENV):
        assert name in script
    reads = (ROOT / "tools" / "executor-runner" / "install.sh").read_text()
    for name in (ENROLLMENT_SECRET_ENV, STAND_ORIGIN_ENV, AGENT_MODEL_ENV):
        assert name in reads


def test_every_exit_the_bootstrap_makes_has_a_reason_and_none_meets_install_shs() -> None:
    script = bootstrap_text()
    made = {int(code) for code in re.findall(r"\bexit (\d+)\b", script)}
    bootstrap_codes = set(range(81, 88))
    assert made == bootstrap_codes | {129}, "81 to 87 are its own refusals, 129 a hang-up"
    assert bootstrap_codes <= set(EXIT_FAILURES)
    install_sh = (ROOT / "tools" / "executor-runner" / "install.sh").read_text()
    theirs = {int(code) for code in re.findall(r"\bdie (\d+)\b", install_sh)} | {1}
    assert theirs & bootstrap_codes == set(), "a status must mean one thing"
    assert theirs - {1} <= set(EXIT_FAILURES), "every install.sh status has a reason"


# -- the SSH call ----------------------------------------------------------------------------------------


def test_the_ssh_call_names_the_fixed_command_pins_the_key_and_puts_nothing_secret_on_an_argument_vector(
    monkeypatch,
) -> None:
    seen: dict[str, Any] = {}

    def fake_run(argv, stdin, timeout_s, environment):
        seen.update(argv=list(argv), stdin=stdin, timeout_s=timeout_s, environment=dict(environment))
        key = Path(argv[argv.index("-i") + 1])
        known = Path(next(item for item in argv if item.startswith("UserKnownHostsFile=")).split("=", 1)[1])
        seen.update(key=key.read_text(), key_mode=key.stat().st_mode & 0o777, known=known.read_text(),
                    known_mode=known.stat().st_mode & 0o777, key_path=key)
        return runner_module._Process(0, b"am-install: installed\n", b"", False)

    monkeypatch.setattr(runner_module, "_run_process", fake_run)
    line = host_key_line()
    payload = build_payload(secret="ame_abcd1234_" + "B" * 43, origin=ORIGIN, model=MODEL,
                            sha256=PACKAGE.sha256, archive=ARCHIVE, marker=install_marker(INSTALL))
    endpoint = runner_module.SshEndpoint(PUBLIC, 2222, USER)
    result = SshInstallTransport().execute(endpoint, PEM, line, payload, timeout_s=120)
    assert result == RemoteResult("completed", exit_status=0, stdout=b"am-install: installed\n")
    argv = seen["argv"]
    assert argv[0] == "ssh" and argv[-1] == REMOTE_COMMAND and argv[-2] == f"{USER}@{PUBLIC}"
    assert "StrictHostKeyChecking=yes" in argv and "BatchMode=yes" in argv and "PasswordAuthentication=no" in argv
    assert argv[argv.index("-p") + 1] == "2222" and "-T" in argv
    assert seen["stdin"] == payload and seen["timeout_s"] == 120
    joined = " ".join(argv)
    assert PEM_BODY not in joined and "ame_abcd1234" not in joined and PACKAGE.sha256 not in joined
    assert seen["known"] == f"[{PUBLIC}]:2222 {line}\n", "exactly the stored key, and no other, is trusted"
    assert seen["key"] == PEM and seen["key_mode"] == 0o600 and seen["known_mode"] == 0o600
    assert not seen["key_path"].exists(), "the key file is gone when the call returns"
    assert "ame_abcd1234" not in json.dumps(seen["environment"]) and PEM_BODY not in json.dumps(seen["environment"])


@pytest.mark.parametrize(("process", "expected"), [
    (runner_module._Process(0, b"x", b"", False), RemoteResult("completed", 0, b"x")),
    (runner_module._Process(86, b"x", b"", False), RemoteResult("completed", 86, b"x")),
    (runner_module._Process(1, b"", b"sudo: a password is required", False), RemoteResult("completed", 1, b"")),
    (runner_module._Process(255, b"", b"user@h: Permission denied (publickey).", False), RemoteResult("refused")),
    (runner_module._Process(255, b"", b"ssh: connect to host h port 22: Connection refused", False),
     RemoteResult("unreachable")),
    (runner_module._Process(255, b"", b"ssh: Could not resolve hostname h", False), RemoteResult("unreachable")),
    (runner_module._Process(255, b"", b"@@@ REMOTE HOST IDENTIFICATION HAS CHANGED! @@@", False),
     RemoteResult("host_key_changed")),
    (runner_module._Process(255, b"", b"Host key verification failed.", False), RemoteResult("host_key_changed")),
    (runner_module._Process(255, b"", b"Connection reset by peer", False), RemoteResult("broken")),
    (runner_module._Process(None, b"", b"", False), RemoteResult("broken")),
    (runner_module._Process(-9, b"", b"", True), RemoteResult("timed_out")),
])
def test_what_ssh_and_the_remote_command_say_is_told_apart(monkeypatch, process, expected) -> None:
    monkeypatch.setattr(runner_module, "_run_process", lambda *args, **kwargs: process)
    endpoint = runner_module.SshEndpoint(PUBLIC, 22, USER)
    assert SshInstallTransport().execute(endpoint, PEM, host_key_line(), b"payload", timeout_s=60) == expected


def test_a_key_ssh_cannot_use_is_a_refusal_and_a_stored_host_key_that_is_not_a_key_is_not_pinned(monkeypatch) -> None:
    monkeypatch.setattr(runner_module, "_run_process", lambda *args, **kwargs: pytest.fail("ssh must not run"))
    endpoint = runner_module.SshEndpoint(PUBLIC, 22, USER)
    assert SshInstallTransport().execute(endpoint, "  \n", host_key_line(), b"x", timeout_s=60) == RemoteResult(
        "refused")
    assert SshInstallTransport().execute(endpoint, PEM, "not a key", b"x", timeout_s=60) == RemoteResult("broken")


def test_the_bounded_runner_returns_what_a_process_said_and_stops_one_that_runs_too_long() -> None:
    quick = runner_module._run_process(
        [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read().upper()); sys.exit(3)"],
        b"payload", 30, {"PATH": os.environ.get("PATH", "")})
    assert (quick.status, quick.stdout, quick.timed_out) == (3, b"PAYLOAD", False)
    flood = runner_module._run_process(
        [sys.executable, "-c", "import sys; sys.stdout.write('x' * 100000)"], b"", 30, {})
    assert len(flood.stdout) == runner_module._OUTPUT_LIMIT, "the output is bounded"
    slow = runner_module._run_process([sys.executable, "-c", "import time; time.sleep(30)"], b"", 0.3, {})
    assert slow.timed_out
    assert runner_module._run_process(["/nonexistent/ssh"], b"", 5, {}).status is None


# -- the repository's statements, as text --------------------------------------------------------------------


class _Result:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount

    def first(self):
        return None

    def mappings(self):
        return self

    def all(self):
        return []


class RecordingSession:
    def __init__(self, *rowcounts: int) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []
        self._rowcounts = list(rowcounts)

    def execute(self, statement, params=None):
        self.statements.append((" ".join(str(statement).split()), dict(params or {})))
        return _Result(self._rowcounts.pop(0) if self._rowcounts else 1)


def test_the_worker_statements_name_the_state_they_move_a_session_from() -> None:
    repo = AgentInstallRepository()
    session = RecordingSession()
    assert repo.claim_requested(session, seconds=1800) is None  # type: ignore[arg-type]
    (sql, params), = session.statements
    assert "SET state = 'scanning'" in sql and "state = 'requested'" in sql and "FOR UPDATE SKIP LOCKED" in sql
    assert "created_at > clock_timestamp() - make_interval(secs => :seconds)" in sql
    assert "state = 'scanning' AND observed_host_key IS NULL AND updated_at < clock_timestamp()" in sql, (
        "a scan is taken again only while no key is stored and its worker has been silent")
    assert params == {"seconds": 1800, "stale": STALE_SCAN_SECONDS}

    session = RecordingSession()
    assert repo.installing(session, seconds=1800, limit=8) == []  # type: ignore[arg-type]
    (sql, params), = session.statements
    assert "i.state = 'installing'" in sql and "FOR UPDATE" not in sql and params == {
        "seconds": 1800, "limit": 8}, "nothing is locked or claimed by looking"

    session = RecordingSession(1)
    assert repo.record_observed_host_key(session, INSTALL, host_key="ssh-ed25519 AAAA")  # type: ignore[arg-type]
    (sql, params), = session.statements
    assert "state = 'awaiting_host_key'" in sql and "AND state = 'scanning'" in sql and (
        "observed_host_key IS NULL" in sql) and params == {"id": INSTALL, "key": "ssh-ed25519 AAAA"}
    assert not repo.record_observed_host_key(RecordingSession(0), INSTALL, host_key="k")  # type: ignore[arg-type]


def test_ending_a_session_replaces_its_key_only_when_it_ended_the_session() -> None:
    repo = AgentInstallRepository()
    session = RecordingSession(1)
    assert repo.finish_install(session, install_id=INSTALL, connection_id=CONNECTION, from_state="installing",  # type: ignore[arg-type]
                               state="succeeded", reason=None)
    update, replace = session.statements
    assert "key_secret_id = NULL" in update[0] and "finished_at = clock_timestamp()" in update[0]
    assert "AND state = :from_state" in update[0] and update[1] == {
        "id": INSTALL, "from_state": "installing", "state": "succeeded", "reason": None}
    assert "purpose = 'agent_install_key'" in replace[0] and "replaced_at IS NULL" in replace[0]
    assert replace[1] == {"c": CONNECTION}

    session = RecordingSession(0)
    assert not repo.finish_install(session, install_id=INSTALL, connection_id=CONNECTION, from_state="installing",  # type: ignore[arg-type]
                                   state="failed", reason="timed_out")
    assert len(session.statements) == 1, "a session somebody else ended keeps its key as that one left it"


def test_a_connections_secrets_never_include_an_install_key() -> None:
    session = RecordingSession()
    ExecutorRepository().current_secrets(session, [CONNECTION])  # type: ignore[arg-type]
    (sql, params), = session.statements
    assert params["purposes"] == list(GENERIC_PURPOSES) and "agent_install_key" not in params["purposes"]
    assert "purpose = ANY(:purposes)" in sql


# -- the worker's pass and the deployment -------------------------------------------------------------------------


def test_the_workers_pass_runs_every_runner_and_a_failing_one_starves_no_other(caplog) -> None:
    from auditmanager.bootstrap.composition import _passes

    calls: list[str] = []

    def probes() -> int:
        calls.append("probes")
        raise RuntimeError("the probe pass broke")

    def installs() -> int:
        calls.append("installs")
        return 2

    with caplog.at_level(logging.ERROR):
        assert _passes(probes, installs)() == 2
    assert calls == ["probes", "installs"] and "worker pass" in caplog.text
    assert _passes(lambda: 1, lambda: 2)() == 3 and _passes()() == 0


def test_the_install_runner_is_what_the_composition_root_builds_for_the_worker() -> None:
    from auditmanager.executors.public import AgentInstallRunner as exported, install_runner_for

    runner = install_runner_for(lambda: nullcontext(FakeSession()), ring=None,  # type: ignore[arg-type]
                                environ={"AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS": "a.example"})
    assert isinstance(runner, exported) and exported is AgentInstallRunner
    assert runner._policy.allowed_hosts == ("a.example",)
    assert callable(runner) and isinstance(runner._transport, SshInstallTransport)


def _service_block(compose: str, name: str) -> str:
    match = re.search(rf"^  {name}:\n(?P<body>(?:    .*\n|\n)+)", compose, re.MULTILINE)
    assert match is not None, name
    return match.group("body")


def test_the_worker_service_reads_the_same_origin_and_package_settings_as_the_api() -> None:
    compose = (ROOT / "infra" / "deploy" / "compose.server.yml").read_text()
    api, worker = _service_block(compose, "api"), _service_block(compose, "worker")
    for name in ("AUDITMANAGER_PUBLIC_ORIGIN", "AUDITMANAGER_AGENT_PACKAGE_DIR"):
        theirs = re.findall(rf"^      {name}: (.*)$", api, re.MULTILINE)
        ours = re.findall(rf"^      {name}: (.*)$", worker, re.MULTILINE)
        assert len(theirs) == 1 and ours == theirs, name
    assert "https://${ALPHA_CERT_NAME:-}" in worker
    readme = (ROOT / "infra" / "deploy" / "README.md").read_text()
    assert "Path A is run by the worker" in readme and "AUDITMANAGER_AGENT_PACKAGE_DIR" in readme


# -- the real bootstrap, on this machine ------------------------------------------------------------------------
#
# The text the worker sends is run with bash against a stand-in `sudo` and a package whose install.sh records
# what it received. This is the scripted SSH endpoint's remote half: nothing here is a copy of the logic.

_TOOLS = ("awk", "bash", "head", "mktemp", "readlink", "rm", "sha256sum", "tar", "wc", "chmod", "mv", "cat", "grep", "sort")
needs_bash = pytest.mark.skipif(
    sys.platform != "linux" or any(shutil.which(tool) is None for tool in _TOOLS),
    reason="the remote bootstrap is run with bash and GNU coreutils")

SECRET = "ame_abcd1234_" + "B" * 43
MARKER = install_marker(INSTALL)
OTHER_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOTHERKEY someone@laptop"
STANDS_LINE = f"restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISTANDSKEY {MARKER}"

_SUDO_STAND_IN = """#!/bin/sh
printf '%s\\n' "$@" >> "$FAKE_RECORD/sudo-argv"
echo '---' >> "$FAKE_RECORD/sudo-argv"
if [ "${FAKE_SUDO_MODE:-ok}" = password ]; then
  echo 'sudo: a password is required' >&2
  exit 1
fi
while [ $# -gt 0 ]; do
  case "$1" in
    -n | --preserve-env=*) shift ;;
    *) break ;;
  esac
done
exec "$@"
"""
_INSTALL_STAND_IN = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$FAKE_RECORD/install-argv"
env | grep '^AUDITMANAGER_' | sort > "$FAKE_RECORD/install-env"
exit "${FAKE_INSTALL_EXIT:-0}"
"""


def make_archive() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        data = _INSTALL_STAND_IN.encode()
        entry = tarfile.TarInfo("install.sh")
        entry.size, entry.mode = len(data), 0o755
        archive.addfile(entry, io.BytesIO(data))
    return buffer.getvalue()


class RemoteHost:
    """A directory standing in for the SSH user's machine: its HOME with an ``authorized_keys``, a TMPDIR, a PATH
    with a `sudo` that records its arguments, and a place the package's install.sh records what it received."""

    def __init__(self, root: Path, authorized: str | None) -> None:
        self.root = root
        self.bin, self.home, self.tmp, self.record = (root / name for name in ("bin", "home", "tmp", "record"))
        for directory in (self.bin, self.home / ".ssh", self.tmp, self.record):
            directory.mkdir(parents=True)
        (self.bin / "sudo").write_text(_SUDO_STAND_IN)
        (self.bin / "sudo").chmod(0o755)
        self.keys = self.home / ".ssh" / "authorized_keys"
        if authorized is not None:
            self.keys.write_text(authorized)
            self.keys.chmod(0o600)
        self.sudo_mode, self.install_exit = "ok", 0

    def run(self, payload: bytes) -> subprocess.CompletedProcess[bytes]:
        environment = {
            "PATH": f"{self.bin}:{os.environ.get('PATH', '/usr/bin:/bin')}", "HOME": str(self.home),
            "TMPDIR": str(self.tmp), "FAKE_RECORD": str(self.record), "FAKE_SUDO_MODE": self.sudo_mode,
            "FAKE_INSTALL_EXIT": str(self.install_exit),
        }
        return subprocess.run(shlex.split(REMOTE_COMMAND), input=payload, env=environment, capture_output=True,
                              timeout=120, check=False)

    def recorded(self, name: str) -> str:
        path = self.record / name
        return path.read_text() if path.exists() else ""


def payload_for(*, marker: str = MARKER, sha: str | None = None, archive: bytes | None = None,
                secret: str = SECRET) -> bytes:
    archive = make_archive() if archive is None else archive
    return build_payload(secret=secret, origin=ORIGIN, model=MODEL, sha256=sha or hashlib.sha256(archive).hexdigest(),
                         archive=archive, marker=marker)


@pytest.fixture
def remote(tmp_path: Path) -> RemoteHost:
    return RemoteHost(tmp_path, f"{OTHER_KEY}\n{STANDS_LINE}\n")


@needs_bash
def test_the_bootstrap_installs_with_the_secret_in_the_environment_and_in_no_argument(remote: RemoteHost) -> None:
    archive = make_archive()
    done = remote.run(payload_for(archive=archive))
    assert done.returncode == 0, done.stderr
    assert done.stdout.decode().splitlines() == ["am-install: installed", "am-install: key-line removed"]
    assert remote.recorded("install-argv").split() == [
        "--package", "agent.tar.gz", "--sha256", hashlib.sha256(archive).hexdigest()]
    environment = remote.recorded("install-env").splitlines()
    assert environment == sorted([f"AUDITMANAGER_AGENT_MODEL={MODEL}", f"AUDITMANAGER_ENROLLMENT_SECRET={SECRET}",
                                  f"AUDITMANAGER_STAND_ORIGIN={ORIGIN}"])
    arguments = remote.recorded("sudo-argv") + remote.recorded("install-argv")
    assert SECRET not in arguments and SECRET[4:] not in arguments, "no argument vector holds the secret"
    assert "--preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN,AUDITMANAGER_AGENT_MODEL" in arguments
    assert SECRET not in done.stdout.decode() + done.stderr.decode()


@needs_bash
def test_the_bootstrap_removes_the_stands_line_and_only_that_line_and_leaves_nothing_behind(remote: RemoteHost) -> None:
    mode = remote.keys.stat().st_mode & 0o777
    assert remote.run(payload_for()).returncode == 0
    assert remote.keys.read_text() == OTHER_KEY + "\n"
    assert remote.keys.stat().st_mode & 0o777 == mode
    assert sorted(path.name for path in (remote.home / ".ssh").iterdir()) == ["authorized_keys"]
    assert list(remote.tmp.iterdir()) == [], "the working directory and the archive are gone"


@needs_bash
def test_a_pasted_key_leaves_authorized_keys_alone_and_says_nothing_about_it(remote: RemoteHost) -> None:
    before = remote.keys.read_text()
    done = remote.run(payload_for(marker="-"))
    assert done.returncode == 0 and remote.keys.read_text() == before
    assert done.stdout.decode().splitlines() == ["am-install: installed"]


@needs_bash
def test_a_line_that_is_not_in_the_file_is_reported_absent_not_removed(tmp_path: Path) -> None:
    host = RemoteHost(tmp_path, OTHER_KEY + "\n")
    done = host.run(payload_for())
    assert done.returncode == 0 and "am-install: key-line absent" in done.stdout.decode().splitlines()
    assert host.keys.read_text() == OTHER_KEY + "\n"
    assert key_line_state(done.stdout) == "host_line_remains"


@needs_bash
def test_sudo_that_wants_a_password_stops_before_anything_is_installed_and_the_line_still_goes(
    remote: RemoteHost,
) -> None:
    remote.sudo_mode = "password"
    done = remote.run(payload_for())
    assert done.returncode == 86 and failure_for(done.returncode) == "sudo_password_required"
    assert remote.recorded("install-argv") == "", "install.sh never ran"
    assert MARKER not in remote.keys.read_text()
    assert "am-install: installed" not in done.stdout.decode()


@needs_bash
def test_an_install_sh_that_fails_fails_the_call_with_its_own_status_and_the_line_still_goes(remote: RemoteHost) -> None:
    remote.install_exit = 66
    done = remote.run(payload_for())
    assert done.returncode == 66 and failure_for(66) == "unsupported_platform"
    assert done.stdout.decode().splitlines() == ["am-install: key-line removed"]
    assert MARKER not in remote.keys.read_text()


@needs_bash
def test_a_package_whose_digest_is_not_the_declared_one_is_not_unpacked(remote: RemoteHost) -> None:
    done = remote.run(payload_for(sha="0" * 64))
    assert done.returncode == 83 and failure_for(83) == "package_unavailable"
    assert remote.recorded("install-argv") == ""


@needs_bash
def test_a_truncated_upload_is_refused(remote: RemoteHost) -> None:
    done = remote.run(payload_for()[:-20])
    assert done.returncode == 82
    assert remote.recorded("install-argv") == ""


@needs_bash
@pytest.mark.parametrize("damage", ["magic", "secret", "origin", "model", "sha", "size", "marker"])
def test_a_malformed_header_is_refused_before_anything_runs(remote: RemoteHost, damage: str) -> None:
    lines = payload_for().split(b"\n", 7)
    index = {"magic": 0, "secret": 1, "origin": 2, "model": 3, "sha": 4, "size": 5, "marker": 6}[damage]
    lines[index] = b"x y; echo pwned"
    done = remote.run(b"\n".join(lines))
    assert done.returncode == 81
    assert remote.recorded("sudo-argv") == "" and remote.recorded("install-argv") == ""
    assert b"pwned" not in done.stdout, "a field is data, never text for the shell"
    if damage in {"secret", "origin", "model", "sha", "size"}:
        assert MARKER not in remote.keys.read_text(), "a valid marker is honoured on the way out"
    else:
        assert MARKER in remote.keys.read_text(), "no marker was read, so there is no line to take away"


@needs_bash
def test_the_bootstrap_stands_on_the_tools_it_names(remote: RemoteHost) -> None:
    """A host without `sudo` on its PATH is `unsupported_platform` (85), reported before anything changes."""
    environment = {"PATH": str(remote.bin / "empty"), "HOME": str(remote.home), "TMPDIR": str(remote.tmp)}
    (remote.bin / "empty").mkdir()
    for tool in ("bash", "head", "mktemp", "readlink", "rm", "sha256sum", "tar", "wc", "awk", "mv", "chmod", "cat"):
        os.symlink(shutil.which(tool), remote.bin / "empty" / tool)
    done = subprocess.run([shutil.which("bash") or "bash", "--noprofile", "--norc", "-c", bootstrap_text()],
                          input=payload_for(), env=environment, capture_output=True, timeout=60, check=False)
    assert done.returncode == 85 and failure_for(85) == "unsupported_platform"
