"""`EXEC2-ENROLL-01`: the API side of path A, an install session of the agent over SSH (B2 section 11 item 1
is the worker's half, `EXEC2-ENROLL-SSH-01`; this is what the API does before and around it).

No database: the repository, the command ledger and the journal are stand-ins, the key ring is a real
X25519 ring so that what is sealed can be opened again. What is shown: a request that could become an option
of ``ssh`` is refused before anything is read; a key is sealed to the session's endpoint and to no other, is
never returned, and is in no event or ledger entry; a generated key returns its public half and the
``authorized_keys`` line; one session per connection is unfinished at a time; the host-key fingerprint is
confirmed by value against the observed one -- no trust on first use -- and an identical repeat answers the
session as it stands; and until the worker lands a session stays ``requested`` -- but not for ever: a session
older than ``INSTALL_SESSION_SECONDS`` is finished as ``failed`` (``no_worker`` while still ``requested``,
``timed_out`` otherwise) with its key replaced, by the next create and by a read of it, with one journal event.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_ssh_private_key,
)

from auditmanager.executors.agent_install import (
    FAILURE_NO_WORKER,
    FAILURE_TIMED_OUT,
    INSTALL_SESSION_SECONDS,
    OverdueInstall,
    authorized_keys_line,
    confirm_agent_install_host_key,
    create_agent_install,
    get_agent_install,
    install_destination,
    observed_fingerprint,
)
from auditmanager.executors.agent_install_repository import UNFINISHED_STATES, InstallRecord
from auditmanager.executors.agent_package import AgentPackage
from auditmanager.executors.model import AGENT_INSTALL_FAILURES, ConnectionRecord, host_key_fingerprint
from auditmanager.executors.sealing import (
    PrivateRing,
    PublicRing,
    SecretUnreadable,
    associated_data,
)
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.jobs.events import _SAFE_KEYS
from auditmanager.shared.errors import DomainError, ErrorCode

T0 = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
OTHER_CONNECTION = "exc_01M2545JSD15ETSNNV904X991M"
PACKAGE = AgentPackage(version="0.9.0", sha256="b" * 64, size_bytes=1, path=None)  # type: ignore[arg-type]
HOST, PORT, USER = "agent-host.example", 22, "ubuntu"


# -- stand-ins --------------------------------------------------------------------------------


class FakeLedger:
    def __init__(self) -> None:
        self.replay: dict[str, Any] | None = None
        self.began: list[dict[str, Any]] = []
        self.succeeded: list[dict[str, Any]] = []

    def begin(self, session, *, command_type, idempotency_key, fingerprint):
        self.began.append({"type": command_type, "key": str(idempotency_key), "fingerprint": str(fingerprint)})
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


class FakeExecutors:
    def __init__(self, *, kind: str = "pull", archived: bool = False, revision: bool = True,
                 exists: bool = True) -> None:
        self.has_revision, self.exists = revision, exists
        self.connection = ConnectionRecord(
            connection_id=CONNECTION, kind=kind, display_name="Claude", created_at=T0, created_by=ADMIN,
            archived_at=T0 if archived else None, archived_by=ADMIN if archived else None)

    def get_connection(self, session, connection_id, *, lock=False):
        return self.connection if self.exists and connection_id == CONNECTION else None

    def current_revisions(self, session, connection_ids):
        return {connection_id: object() for connection_id in connection_ids} if self.has_revision else {}


class FakeInstalls:
    """``AgentInstallRepository`` in memory."""

    def __init__(self) -> None:
        self.rows: dict[str, InstallRecord] = {}
        self.keys: dict[str, dict[str, Any]] = {}
        self.current: dict[str, str] = {}
        self.replaced: set[str] = set()
        self.confirmed_calls = 0
        #: The database's clock. A session is created at this moment and is overdue by it.
        self.now = T0
        #: Every ask for the sessions whose time is up: ``(connection_id, install_id or None)``.
        self.overdue_asked: list[tuple[str, str | None]] = []

    def unfinished_install(self, session, connection_id):
        for row in self.rows.values():
            if row.connection_id == connection_id and row.state not in ("succeeded", "failed"):
                return row.install_id
        return None

    def insert_key(self, session, *, secret_id, connection_id, kid, destination, ciphertext,
                   public_material, actor_uid):
        previous = self.current.get(connection_id)
        if previous is not None:  # ux_executor_secret_current: one current agent_install_key per connection
            self.replaced.add(previous)
        self.current[connection_id] = secret_id
        self.keys[secret_id] = {"connection_id": connection_id, "kid": kid, "destination": destination,
                                "ciphertext": ciphertext, "public_material": public_material}

    def insert_install(self, session, *, install_id, connection_id, access, ssh_host, ssh_port, ssh_user,
                       key_secret_id, package_version, package_sha256, actor_uid):
        assert key_secret_id in self.keys, "the key row is written before the session that names it"
        assert self.unfinished_install(session, connection_id) is None, "ux_executor_agent_install_open"
        record = InstallRecord(
            install_id=str(install_id), connection_id=connection_id, state="requested", access=access,
            ssh_host=ssh_host, ssh_port=ssh_port, ssh_user=ssh_user, key_secret_id=key_secret_id,
            public_key=self.keys[key_secret_id]["public_material"], observed_host_key=None,
            confirmed_host_key_fingerprint=None, host_key_confirmed_at=None, host_key_confirmed_by=None,
            package_version=package_version, package_sha256=package_sha256, failure_reason=None,
            key_removed_at=None, created_at=self.now, created_by=actor_uid, updated_at=self.now,
            finished_at=None)
        self.rows[record.install_id] = record
        return record

    def get_install(self, session, install_id, *, lock=False):
        return self.rows.get(install_id)

    def confirm_host_key(self, session, install_id, *, fingerprint, actor_uid):
        self.confirmed_calls += 1
        row = self.rows[install_id]
        if row.state != "awaiting_host_key" or row.confirmed_host_key_fingerprint is not None:
            return False
        self.rows[install_id] = dataclasses.replace(
            row, state="installing", confirmed_host_key_fingerprint=fingerprint,
            host_key_confirmed_at=T0 + timedelta(minutes=1), host_key_confirmed_by=actor_uid,
            updated_at=T0 + timedelta(minutes=1))
        return True

    def overdue_installs(self, session, *, connection_id, install_id=None, seconds=INSTALL_SESSION_SECONDS):
        """``InstallLifetimeRepository.overdue_installs``: unfinished, created at least ``seconds`` ago."""
        self.overdue_asked.append((connection_id, install_id))
        return [
            OverdueInstall(install_id=row.install_id, state=row.state, key_secret_id=row.key_secret_id)
            for row in sorted(self.rows.values(), key=lambda row: (row.created_at, row.install_id))
            if row.connection_id == connection_id and row.state in UNFINISHED_STATES
            and (install_id is None or row.install_id == install_id)
            and row.created_at <= self.now - timedelta(seconds=seconds)
        ]

    def fail_install(self, session, *, install_id, connection_id, from_state, reason):
        """``InstallLifetimeRepository.fail_install``: the shape the table's CHECKs demand of a failure."""
        row = self.rows[install_id]
        if row.state != from_state:
            return False
        self.rows[install_id] = dataclasses.replace(
            row, state="failed", failure_reason=reason, finished_at=self.now, updated_at=self.now,
            key_secret_id=None, public_key=None, key_removed_at=row.key_removed_at or self.now)
        replaced = self.current.pop(connection_id, None)  # no current agent_install_key remains
        if replaced is not None:
            self.replaced.add(replaced)
        return True

    def worker_observes(self, install_id: str, host_key: str) -> None:
        """What `EXEC2-ENROLL-SSH-01` does: scan, record the key it saw, wait for the confirmation."""
        self.rows[install_id] = dataclasses.replace(
            self.rows[install_id], state="awaiting_host_key", observed_host_key=host_key)

    def worker_ends(self, install_id: str, state: str, reason: str | None = None) -> None:
        self.rows[install_id] = dataclasses.replace(
            self.rows[install_id], state=state, failure_reason=reason, finished_at=T0, key_removed_at=T0,
            key_secret_id=None, public_key=None)


def rings() -> tuple[PublicRing, PrivateRing]:
    private = X25519PrivateKey.generate()
    return (PublicRing(keys={"k1": private.public_key()}, active_kid="k1"),
            PrivateRing(keys={"k1": private}, active_kid="k1"))


def host_key_line() -> str:
    return Ed25519PrivateKey.generate().public_key().public_bytes(
        Encoding.OpenSSH, PublicFormat.OpenSSH).decode("ascii")


def fingerprint_of(line: str) -> str:
    blob = base64.b64decode(line.split()[1])
    return "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")


PASTED_KEY = (
    "-----BEGIN OPENSSH PRIVATE KEY-----\n"
    "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZWQyNTUxOQAAACD\n"
    "PASTED-KEY-BODY-THAT-MUST-NEVER-BE-RETURNED-OR-LOGGED\n"
    "-----END OPENSSH PRIVATE KEY-----\n"
)


class World:
    def __init__(self, **connection: Any) -> None:
        self.executors = FakeExecutors(**connection)
        self.installs = FakeInstalls()
        self.ledger = FakeLedger()
        self.journal = Journal()
        self.public, self.private = rings()

    def create(self, key: str = "install-1", *, access: str = "generated_key", host: str = HOST,
               port: Any = PORT, user: str = USER, private_key: str | None = None,
               roles=("admin",), ring: Any = "default", package=lambda: PACKAGE):
        return create_agent_install(
            None, connection_id=CONNECTION, access=access, ssh_host=host, ssh_port=port,  # type: ignore[arg-type]
            ssh_user=user, private_key=private_key, ring=self.public if ring == "default" else ring,
            roles=roles, idempotency_key=key, actor_uid=ADMIN, executors=self.executors,  # type: ignore[arg-type]
            repository=self.installs, commands=self.ledger, package_source=package,  # type: ignore[arg-type]
            journal=self.journal)

    def confirm(self, install_id: str, fingerprint: str, key: str = "confirm-1", *,
                connection_id: str = CONNECTION, roles=("admin",)):
        return confirm_agent_install_host_key(
            None, connection_id=connection_id, install_id=install_id, fingerprint=fingerprint,  # type: ignore[arg-type]
            roles=roles, idempotency_key=key, actor_uid=ADMIN, repository=self.installs,  # type: ignore[arg-type]
            commands=self.ledger, journal=self.journal)  # type: ignore[arg-type]

    def awaiting(self) -> tuple[InstallRecord, str]:
        record = self.create()
        line = host_key_line()
        self.installs.worker_observes(record.install_id, line)
        return self.installs.rows[record.install_id], fingerprint_of(line)


def refusal(call, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    return caught.value


def details(error: DomainError) -> dict[str, Any]:
    return dict(error.detail_fields)


# -- the values ---------------------------------------------------------------------------------


def test_a_session_key_is_bound_to_the_endpoint_it_was_sealed_for() -> None:
    assert install_destination(ssh_host=HOST, ssh_port=PORT, ssh_user=USER) == "agent_install|ubuntu@agent-host.example:22|"
    assert install_destination(ssh_host=HOST, ssh_port=2222, ssh_user=USER) != install_destination(
        ssh_host=HOST, ssh_port=PORT, ssh_user=USER)


def test_the_authorized_keys_line_restricts_the_key_and_names_the_session() -> None:
    line = authorized_keys_line("ssh-ed25519 AAAAC3Nza", "exai_01M2545JSD15ETSNNV904X991K")
    assert line == "restrict ssh-ed25519 AAAAC3Nza auditmanager-install:exai_01M2545JSD15ETSNNV904X991K"
    assert len(line) <= 2200


def test_the_observed_fingerprint_is_derived_from_the_stored_line_as_a_revisions_is() -> None:
    world = World()
    record = world.create()
    assert observed_fingerprint(record) is None
    line = host_key_line()
    world.installs.worker_observes(record.install_id, line)
    assert observed_fingerprint(world.installs.rows[record.install_id]) == fingerprint_of(line) == host_key_fingerprint(line)
    garbled = dataclasses.replace(record, observed_host_key="not a key")
    assert observed_fingerprint(garbled) is None


# -- creating a session -------------------------------------------------------------------------


@pytest.mark.parametrize("host", [
    "", "-oProxyCommand=id", "-host", "a b", "host;rm -rf /", "host`id`", "host$(id)", ".host", "host.",
    "a" * 254, "host\n", "[::1", "ho/st", "user@host", "host:22", "ünicode.example", "[zzzz]",
])
def test_a_host_that_could_become_an_option_or_a_command_is_refused_before_anything_is_read(host: str) -> None:
    world = World()
    error = refusal(world.create, host=host)
    assert error.code is ErrorCode.VALIDATION_FAILED and details(error) == {"field": "ssh_host", "constraint": "format"}
    assert world.ledger.began == [] and world.installs.rows == {} and world.installs.keys == {}


@pytest.mark.parametrize("host", ["host.example", "10.0.0.5", "[fe80::1]", "a", "A-b.c-1"])
def test_a_plain_host_name_or_address_is_accepted(host: str) -> None:
    assert World().create(host=host).ssh_host == host


@pytest.mark.parametrize("user", ["", "-x", "a b", "1abc", "x" * 65, "root;id", "a'b", "a\n", "us$er"])
def test_a_user_outside_the_portable_set_is_refused(user: str) -> None:
    error = refusal(World().create, user=user)
    assert details(error) == {"field": "ssh_user", "constraint": "format"}


@pytest.mark.parametrize("user", ["ubuntu", "_svc", "deploy.user-1", "a", "x" * 64])
def test_a_portable_user_name_is_accepted(user: str) -> None:
    assert World().create(user=user).ssh_user == user


@pytest.mark.parametrize("port", [0, -1, 65536, True, "22", None, 22.0])
def test_a_port_outside_one_to_65535_is_refused(port: Any) -> None:
    assert details(refusal(World().create, port=port)) == {"field": "ssh_port", "constraint": "range"}


@pytest.mark.parametrize(("access", "key", "constraint"), [
    ("pasted_key", None, "private_key_required"),
    ("generated_key", PASTED_KEY, "private_key_not_accepted"),
])
def test_a_key_is_required_for_a_pasted_one_and_refused_for_a_generated_one(
    access: str, key: str | None, constraint: str,
) -> None:
    world = World()
    error = refusal(world.create, access=access, private_key=key)
    assert error.code is ErrorCode.VALIDATION_FAILED and details(error) == {
        "field": "private_key", "constraint": constraint}
    assert world.ledger.began == [] and "PASTED-KEY-BODY" not in str(error)


@pytest.mark.parametrize("key", [
    "password123", "ssh-ed25519 AAAAC3Nza public-not-private", "", "-----BEGIN CERTIFICATE-----\nx\n-----END CERTIFICATE-----",
    "-----BEGIN ENCRYPTED PRIVATE KEY-----\nx\n-----END ENCRYPTED PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\nDEK-Info: AES-128-CBC,AB\n\nx\n-----END RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----\n" + "A" * 9000 + "\n-----END OPENSSH PRIVATE KEY-----",
])
def test_a_pasted_value_that_is_not_an_unencrypted_private_key_is_refused_without_echoing_it(key: str) -> None:
    error = refusal(World().create, access="pasted_key", private_key=key)
    assert details(error) == {"field": "private_key", "constraint": "format"}
    assert key[:40] not in str(error) or key == ""


def test_an_access_the_contract_does_not_name_is_refused_and_a_password_is_not_one() -> None:
    for access in ("password", "agent", ""):
        error = refusal(World().create, access=access)
        assert details(error) == {"field": "access", "constraint": "enum"}


def test_a_generated_key_session_is_recorded_requested_and_returns_the_public_half_only() -> None:
    world = World()
    record = world.create()
    assert record.state == "requested" and record.access == "generated_key"
    assert (record.ssh_host, record.ssh_port, record.ssh_user) == (HOST, PORT, USER)
    assert record.package_version == "0.9.0" and record.package_sha256 == "b" * 64
    assert record.public_key and record.public_key.startswith("ssh-ed25519 ")
    assert record.observed_host_key is None and record.confirmed_host_key_fingerprint is None
    assert world.ledger.succeeded == [{"install_id": record.install_id}]
    assert not hasattr(record, "private_key") and not hasattr(record, "ciphertext")


def test_the_sealed_key_opens_for_its_endpoint_only_and_is_the_pair_of_the_public_half() -> None:
    world = World()
    record = world.create()
    row = world.installs.keys[record.key_secret_id]  # type: ignore[index]
    assert row["destination"] == install_destination(ssh_host=HOST, ssh_port=PORT, ssh_user=USER)
    fields = dict(secret_id=record.key_secret_id, connection_id=CONNECTION, purpose="agent_install_key",
                  kid=row["kid"])
    opened = world.private.open(
        row["kid"], row["ciphertext"], associated_data(destination=row["destination"], **fields))  # type: ignore[arg-type]
    assert opened.startswith(b"-----BEGIN OPENSSH PRIVATE KEY-----")
    pair = load_ssh_private_key(opened, password=None).public_key().public_bytes(  # type: ignore[union-attr]
        Encoding.OpenSSH, PublicFormat.OpenSSH).decode()
    assert pair == record.public_key
    for other in (install_destination(ssh_host=HOST, ssh_port=2222, ssh_user=USER),
                  install_destination(ssh_host="elsewhere.example", ssh_port=PORT, ssh_user=USER),
                  install_destination(ssh_host=HOST, ssh_port=PORT, ssh_user="root")):
        with pytest.raises(SecretUnreadable):
            world.private.open(row["kid"], row["ciphertext"], associated_data(destination=other, **fields))  # type: ignore[arg-type]
    assert opened not in row["ciphertext"]


def test_a_pasted_key_is_sealed_and_never_returned_stored_in_the_clear_or_journaled() -> None:
    world = World()
    record = world.create(access="pasted_key", private_key=PASTED_KEY)
    assert record.access == "pasted_key" and record.public_key is None
    row = world.installs.keys[record.key_secret_id]  # type: ignore[index]
    assert row["public_material"] is None
    assert b"PASTED-KEY-BODY" not in row["ciphertext"]
    opened = world.private.open(row["kid"], row["ciphertext"], associated_data(
        secret_id=record.key_secret_id, connection_id=CONNECTION, purpose="agent_install_key",
        kid=row["kid"], destination=row["destination"]))  # type: ignore[arg-type]
    assert opened.decode() == PASTED_KEY
    said = repr([world.journal.events, world.ledger.began, world.ledger.succeeded, record])
    assert "PASTED-KEY-BODY" not in said and "BEGIN OPENSSH" not in said


def test_the_ledger_fingerprint_is_of_the_request_without_key_material() -> None:
    first, second = World(), World()
    first.create("same-key", access="pasted_key", private_key=PASTED_KEY)
    second.create("same-key", access="pasted_key", private_key=PASTED_KEY.replace("PASTED", "OTHER"))
    assert first.ledger.began[0]["fingerprint"] == second.ledger.began[0]["fingerprint"]


def test_the_journal_names_the_session_by_identity_and_carries_no_key_or_host() -> None:
    world = World()
    record = world.create()
    assert len(world.journal.events) == 1
    event = world.journal.events[0]
    assert event["event_type"] == "executor.agent_install_requested"
    assert event["aggregate_type"] == "ExecutorAgentInstall" and event["aggregate_id"] == record.install_id
    assert event["payload"] == {"connection_id": CONNECTION, "secret_id": record.key_secret_id,
                                "purpose": "agent_install_key", "state": "requested", "actor_uid": ADMIN}
    assert HOST not in repr(world.journal.events) and USER not in repr(world.journal.events)


def test_only_an_administrator_creates_a_session() -> None:
    world = World()
    for roles in ((), ("expert",)):
        assert refusal(world.create, roles=roles).code is ErrorCode.PERMISSION_DENIED
    assert world.ledger.began == [] and world.installs.rows == {}


@pytest.mark.parametrize(("connection", "code", "detail"), [
    ({"exists": False}, ErrorCode.NOT_FOUND, {"aggregate_type": "ExecutorConnection"}),
    ({"archived": True}, ErrorCode.CONFLICT, {"conflict_reason": "connection_archived"}),
    ({"kind": "ssh_command"}, ErrorCode.VALIDATION_FAILED, {"field": "kind", "constraint": "kind_not_pull"}),
    ({"revision": False}, ErrorCode.CONFLICT, {"conflict_reason": "no_revision"}),
])
def test_a_connection_that_cannot_take_an_agent_takes_no_session(
    connection: dict[str, Any], code: ErrorCode, detail: dict[str, str],
) -> None:
    world = World(**connection)
    error = refusal(world.create)
    assert error.code is code and details(error) == detail
    assert world.installs.rows == {} and world.installs.keys == {} and world.journal.events == []


def test_one_session_per_connection_is_unfinished_at_a_time_and_a_finished_one_makes_room() -> None:
    world = World()
    first = world.create("install-1")
    error = refusal(world.create, "install-2")
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "install_in_progress"}
    assert len(world.installs.rows) == 1 and len(world.installs.keys) == 1 and world.installs.replaced == set()
    world.installs.worker_ends(first.install_id, "failed", "host_unreachable")
    second = world.create("install-3")
    assert second.install_id != first.install_id and second.state == "requested"
    assert second.key_secret_id != first.key_secret_id
    assert world.installs.current == {CONNECTION: second.key_secret_id}, "the new session's key is the current one"
    assert world.installs.replaced == {first.key_secret_id}, "and the previous session's key is replaced"


def test_a_stand_without_a_public_key_or_an_image_without_a_package_creates_nothing() -> None:
    world = World()
    error = refusal(world.create, ring=None)
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE and details(error) == {
        "dependency": "secrets_public_key_missing"}

    def no_package() -> AgentPackage:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="agent_package")

    error = refusal(world.create, package=no_package)
    assert details(error) == {"dependency": "agent_package"}
    assert world.installs.rows == {} and world.installs.keys == {} and world.journal.events == []


def test_a_repeat_of_the_key_answers_the_first_session_and_creates_nothing() -> None:
    world = World()
    first = world.create("install-1")
    world.ledger.replay = {"install_id": first.install_id}
    again = world.create("install-1")
    assert again == first and len(world.installs.rows) == 1 and len(world.installs.keys) == 1
    assert len(world.journal.events) == 1


def test_until_the_worker_lands_a_session_stays_visibly_requested() -> None:
    world = World()
    record = world.create()
    assert get_agent_install(None, connection_id=CONNECTION, install_id=record.install_id,  # type: ignore[arg-type]
                             repository=world.installs).state == "requested"


# -- the end of a session -------------------------------------------------------------------------


def read(world: World, install_id: str) -> InstallRecord:
    return get_agent_install(None, connection_id=CONNECTION, install_id=install_id,  # type: ignore[arg-type]
                             repository=world.installs, journal=world.journal)  # type: ignore[arg-type]


def expired_events(world: World) -> list[dict[str, Any]]:
    return [event for event in world.journal.events if event["event_type"] == "executor.agent_install_expired"]


def test_a_session_lives_thirty_minutes_and_ends_with_a_reason_the_table_allows() -> None:
    assert INSTALL_SESSION_SECONDS == 1800
    assert {FAILURE_NO_WORKER, FAILURE_TIMED_OUT} == {"no_worker", "timed_out"} <= set(AGENT_INSTALL_FAILURES)


def test_a_session_is_not_ended_a_moment_before_its_time_is_up() -> None:
    world = World()
    first = world.create("install-1")
    world.installs.now = T0 + timedelta(seconds=INSTALL_SESSION_SECONDS - 1)
    error = refusal(world.create, "install-2")
    assert details(error) == {"conflict_reason": "install_in_progress"}
    assert read(world, first.install_id).state == "requested"
    assert expired_events(world) == [] and world.installs.replaced == set()
    assert world.installs.current == {CONNECTION: first.key_secret_id}


def test_the_next_create_ends_a_requested_session_nobody_took_as_no_worker_and_goes_ahead() -> None:
    world = World()
    first = world.create("install-1", access="pasted_key", private_key=PASTED_KEY)
    world.installs.now = T0 + timedelta(seconds=INSTALL_SESSION_SECONDS)
    second = world.create("install-2")
    assert second.install_id != first.install_id and second.state == "requested"
    ended = world.installs.rows[first.install_id]
    assert (ended.state, ended.failure_reason) == ("failed", "no_worker")
    assert ended.finished_at == world.installs.now and ended.updated_at == world.installs.now
    assert ended.key_secret_id is None and ended.key_removed_at == world.installs.now
    assert ended.public_key is None, "the reference to the key is gone with the key"
    assert world.installs.replaced == {first.key_secret_id}
    assert world.installs.current == {CONNECTION: second.key_secret_id}
    assert [event["event_type"] for event in world.journal.events] == [
        "executor.agent_install_requested", "executor.agent_install_expired",
        "executor.agent_install_requested"], "the expiry is journaled before the new session it makes room for"
    assert world.installs.overdue_asked == [(CONNECTION, None)] * 2, "the connection's, not one session's"


@pytest.mark.parametrize("state", ["scanning", "awaiting_host_key", "installing"])
def test_a_session_somebody_took_and_that_went_silent_ends_as_timed_out(state: str) -> None:
    world = World()
    first = world.create("install-1")
    world.installs.rows[first.install_id] = dataclasses.replace(
        first, state=state, observed_host_key=None if state == "scanning" else host_key_line())
    world.installs.now = T0 + timedelta(hours=2)
    world.create("install-2")
    ended = world.installs.rows[first.install_id]
    assert (ended.state, ended.failure_reason) == ("failed", "timed_out")
    (event,) = expired_events(world)
    assert event["payload"]["from_state"] == state and event["payload"]["reason"] == "timed_out"


def test_a_read_of_an_overdue_session_ends_it_and_answers_the_ended_one() -> None:
    world = World()
    first = world.create()
    asked = len(world.installs.overdue_asked)
    world.installs.now = T0 + timedelta(seconds=INSTALL_SESSION_SECONDS + 5)
    answer = read(world, first.install_id)
    assert (answer.state, answer.failure_reason) == ("failed", "no_worker")
    assert answer.finished_at is not None and answer.key_removed_at is not None
    assert answer.key_secret_id is None and answer.public_key is None
    assert world.installs.current == {} and world.installs.replaced == {first.key_secret_id}
    assert world.installs.overdue_asked[asked:] == [(CONNECTION, first.install_id)], "that session, no other"
    assert len(expired_events(world)) == 1


def test_ending_a_session_is_idempotent_a_second_read_and_a_second_create_write_nothing_more() -> None:
    world = World()
    first = world.create()
    world.installs.now = T0 + timedelta(minutes=45)
    once = read(world, first.install_id)
    events, asked = len(world.journal.events), len(world.installs.overdue_asked)
    assert read(world, first.install_id) == once
    assert len(world.journal.events) == events, "a finished session is not looked at again"
    assert len(world.installs.overdue_asked) == asked
    world.create("install-2")
    assert len(expired_events(world)) == 1, "and the create finds nothing left to end"
    assert world.installs.rows[first.install_id] == once


@pytest.mark.parametrize(("state", "reason"), [("succeeded", None), ("failed", "host_unreachable")])
def test_a_session_that_has_ended_is_never_touched_however_old(state: str, reason: str | None) -> None:
    world = World()
    first = world.create()
    world.installs.worker_ends(first.install_id, state, reason)
    before = world.installs.rows[first.install_id]
    world.installs.now = T0 + timedelta(days=30)
    assert read(world, first.install_id) == before
    world.create("install-2")
    assert world.installs.rows[first.install_id] == before
    assert expired_events(world) == []
    assert world.installs.overdue_asked == [(CONNECTION, None)] * 2, "a read of a finished session asks nothing"


def test_a_session_of_another_connection_is_not_ended_by_this_ones_create() -> None:
    world = World()
    first = world.create()
    other = dataclasses.replace(first, install_id="exai_01M2545JSD15ETSNNV904X991M", connection_id=OTHER_CONNECTION)
    world.installs.rows[other.install_id] = other
    world.installs.now = T0 + timedelta(hours=1)
    world.create("install-2")
    assert world.installs.rows[other.install_id] == other
    assert world.installs.rows[first.install_id].state == "failed"


def test_the_expiry_event_names_the_session_by_identity_and_carries_no_key_host_or_user() -> None:
    world = World()
    first = world.create("install-1", access="pasted_key", private_key=PASTED_KEY)
    world.installs.now = T0 + timedelta(hours=1)
    read(world, first.install_id)
    (event,) = expired_events(world)
    assert event["aggregate_type"] == "ExecutorAgentInstall" and event["aggregate_id"] == first.install_id
    assert event["payload"] == {
        "connection_id": CONNECTION, "secret_id": first.key_secret_id, "purpose": "agent_install_key",
        "from_state": "requested", "to_state": "failed", "reason": "no_worker"}
    assert set(event["payload"]) <= _SAFE_KEYS, "the journal refuses any other key"
    said = repr(world.journal.events)
    assert HOST not in said and USER not in said and "PASTED-KEY-BODY" not in said and "BEGIN OPENSSH" not in said


def test_a_session_that_is_replayed_by_its_key_is_answered_without_ending_anything() -> None:
    world = World()
    first = world.create("install-1")
    asked = len(world.installs.overdue_asked)
    world.installs.now = T0 + timedelta(hours=1)
    world.ledger.replay = {"install_id": first.install_id}
    assert world.create("install-1") == first
    assert len(world.installs.overdue_asked) == asked and expired_events(world) == []
    assert world.installs.rows[first.install_id].state == "requested"


# -- reading a session ----------------------------------------------------------------------------


def test_a_session_of_another_connection_or_an_unknown_one_is_not_found() -> None:
    world = World()
    record = world.create()
    for connection_id, install_id in ((OTHER_CONNECTION, record.install_id), (CONNECTION, "exai_missing")):
        error = refusal(get_agent_install, None, connection_id=connection_id, install_id=install_id,  # type: ignore[arg-type]
                        repository=world.installs)
        assert error.code is ErrorCode.NOT_FOUND and details(error) == {"aggregate_type": "ExecutorAgentInstall"}


# -- confirming the host key ----------------------------------------------------------------------


def test_the_observed_fingerprint_confirmed_by_value_moves_the_session_to_installing() -> None:
    world = World()
    record, fingerprint = world.awaiting()
    confirmed = world.confirm(record.install_id, fingerprint)
    assert confirmed.state == "installing" and confirmed.confirmed_host_key_fingerprint == fingerprint
    assert confirmed.host_key_confirmed_by == ADMIN and confirmed.host_key_confirmed_at is not None
    assert world.journal.events[-1] == {
        "event_type": "executor.agent_install_host_key_confirmed", "aggregate_type": "ExecutorAgentInstall",
        "aggregate_id": record.install_id,
        "payload": {"connection_id": CONNECTION, "state": "installing", "actor_uid": ADMIN}}
    assert fingerprint not in repr(world.journal.events), "the fingerprint is on the row and in no event"
    assert world.ledger.succeeded[-1] == {"install_id": record.install_id}


def test_a_fingerprint_that_is_not_the_observed_one_is_host_key_changed_and_confirms_nothing() -> None:
    world = World()
    record, _ = world.awaiting()
    error = refusal(world.confirm, record.install_id, fingerprint_of(host_key_line()))
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "host_key_changed"}
    stored = world.installs.rows[record.install_id]
    assert stored.state == "awaiting_host_key" and stored.confirmed_host_key_fingerprint is None
    assert world.installs.confirmed_calls == 0


@pytest.mark.parametrize("state", ["requested", "scanning", "succeeded", "failed"])
def test_a_session_that_is_not_waiting_for_a_host_key_cannot_be_confirmed(state: str) -> None:
    world = World()
    record = world.create()
    world.installs.rows[record.install_id] = dataclasses.replace(record, state=state)
    error = refusal(world.confirm, record.install_id, fingerprint_of(host_key_line()))
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "install_not_awaiting_host_key"}
    assert world.installs.confirmed_calls == 0


def test_an_identical_repeat_answers_the_session_as_it_stands_and_confirms_nothing_twice() -> None:
    world = World()
    record, fingerprint = world.awaiting()
    first = world.confirm(record.install_id, fingerprint, "confirm-1")
    events = len(world.journal.events)
    world.installs.rows[record.install_id] = dataclasses.replace(first, state="succeeded", finished_at=T0)
    again = world.confirm(record.install_id, fingerprint, "confirm-2")
    assert again.state == "succeeded" and again.confirmed_host_key_fingerprint == fingerprint
    assert len(world.journal.events) == events and world.installs.confirmed_calls == 1


def test_another_fingerprint_after_a_confirmation_is_host_key_changed() -> None:
    world = World()
    record, fingerprint = world.awaiting()
    world.confirm(record.install_id, fingerprint)
    error = refusal(world.confirm, record.install_id, fingerprint_of(host_key_line()), "confirm-2")
    assert details(error) == {"conflict_reason": "host_key_changed"}


def test_a_repeat_of_the_confirmation_key_answers_the_session_without_acting() -> None:
    world = World()
    record, fingerprint = world.awaiting()
    world.ledger.replay = {"install_id": record.install_id}
    answered = world.confirm(record.install_id, fingerprint)
    assert answered.state == "awaiting_host_key" and world.installs.confirmed_calls == 0
    assert world.journal.events[-1]["event_type"] == "executor.agent_install_requested"


@pytest.mark.parametrize("fingerprint", [
    "", "SHA256:short", "SHA256:" + "A" * 44, "MD5:" + "a" * 43, "sha256:" + "A" * 43, "SHA256:" + "A" * 42 + "!",
    "SHA256:" + "A" * 43 + "\n",
])
def test_a_fingerprint_outside_the_declared_form_is_refused_before_anything_is_read(fingerprint: str) -> None:
    world = World()
    record, _ = world.awaiting()
    began = len(world.ledger.began)
    error = refusal(world.confirm, record.install_id, fingerprint)
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert details(error) == {"field": "host_key_fingerprint", "constraint": "pattern"}
    assert len(world.ledger.began) == began


def test_a_session_of_another_connection_cannot_be_confirmed_and_only_an_administrator_confirms() -> None:
    world = World()
    record, fingerprint = world.awaiting()
    error = refusal(world.confirm, record.install_id, fingerprint, connection_id=OTHER_CONNECTION)
    assert error.code is ErrorCode.NOT_FOUND
    began = len(world.ledger.began)
    assert refusal(world.confirm, record.install_id, fingerprint, roles=("expert",)).code is ErrorCode.PERMISSION_DENIED
    assert len(world.ledger.began) == began and world.installs.confirmed_calls == 0
