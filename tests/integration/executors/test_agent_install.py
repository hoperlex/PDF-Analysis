"""`EXEC2-ENROLL-SSH-01`: path A over real rows (B2 section 11 item 1) -- the API records an install session, the
worker's ``AgentInstallRunner`` takes it, a scripted SSH host answers, and the agent registers through the real
enrollment.

Every test requests ``session`` (and the fixtures built on it), the suite's database harness, which **fails hard
without ``DATABASE_URL`` and never skips** (``tests/integration/README.md``): this suite has no pytest marker for
it, the fixture is the marker. The API is the served application (``ExecutorAdapter`` and
``ExecutorEnrollmentAdapter``); the worker is the real runner with the real repositories, the real command ledger,
the real key ring and the real package loader. The only stand-in is the SSH host (:class:`ScriptedHost`), which
records what the worker sent and, when it is told the install worked, redeems the grant in its payload the way
``install.sh`` does. What is shown, in rows:

* a generated key travels the whole way -- ``requested``, ``scanning``, ``awaiting_host_key``, the administrator's
  confirmation, ``installing``, ``succeeded`` -- and ends with the sealed key replaced and no longer named, the
  connection's secrets empty in every state, the agent's grant redeemed, and no secret, key or fingerprint in the
  audit trail;
* a host key that changed after the confirmation is refused with no grant issued and nothing sent;
* ``sudo`` that asks for a password fails the session, and the retry is a new session of the same connection with
  a fresh enrollment (the first, unspent, is revoked);
* a target the destination rules refuse is never connected to;
* an install is claimed once, by the grant's ledger key: a second worker leaves a claimed session alone, and a
  session whose worker died after its claim ends as ``timed_out`` by the API's own sweep.

Unexecuted in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import hashlib
import json
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.api.routers import build_router
from auditmanager.executors.agent_install import INSTALL_SESSION_SECONDS, install_marker
from auditmanager.executors.agent_install_runner import (
    GRANT_COMMAND_TYPE,
    AgentInstallRunner,
    RemoteResult,
    grant_key,
    key_line_state,
)
from auditmanager.executors.agent_package import PACKAGE_DIRECTORY_ENV
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.model import host_key_fingerprint
from auditmanager.executors.public import (
    authenticate_enrollment,
    issue_executor_enrollment,
    redeem_enrollment,
)
from tests.integration.executors.conftest import driver

Request, dispatch = driver.Request, driver.dispatch

MODEL = "claude-opus-5"
PULL_SETTINGS = {
    "pin_id": MODEL, "gateway_model": MODEL, "billing": "not_metered", "allow_client_documents": False,
    "timeout_seconds": 60, "pull_client": "agent", "answer_deadline_seconds": 60, "max_claimed_tasks": 1,
}
PUBLIC = "93.184.216.34"
HOST, USER = "agent-host.example", "ubuntu"
INSTALL_BODY = {"access": "generated_key", "ssh_host": HOST, "ssh_port": 22, "ssh_user": USER}
ARCHIVE = b"\x1f\x8b the agent package"
SUCCESS = RemoteResult("completed", exit_status=0,
                       stdout=b"am-install: installed\nam-install: key-line removed\n")


def host_key_line() -> str:
    return Ed25519PrivateKey.generate().public_key().public_bytes(
        Encoding.OpenSSH, PublicFormat.OpenSSH).decode("ascii")


def pasted_private_key() -> str:
    return Ed25519PrivateKey.generate().private_bytes(
        Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption()).decode("ascii")


# -- the API, as test_enrollment builds it ----------------------------------------------------------


def publish(directory: Path, version: str = "0.9.0", content: bytes = ARCHIVE) -> bytes:
    name = f"auditmanager-agent-{version}.tar.gz"
    (directory / name).write_bytes(content)
    (directory / (name + ".sha256")).write_text(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
    return content


@pytest.fixture
def package_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(PACKAGE_DIRECTORY_ENV, str(tmp_path))
    publish(tmp_path)
    return tmp_path


def build_stand(session: Session, rings):
    from auditmanager.bootstrap.adapters import ExecutorAdapter, ExecutorEnrollmentAdapter
    from auditmanager.bootstrap.runner import RunnerAdapter

    def sessions():
        return nullcontext(session)

    router = build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})),
        accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(),
        executors=ExecutorAdapter(sessions, ring=rings.public),  # type: ignore[arg-type]
        runner=RunnerAdapter(sessions),  # type: ignore[arg-type]
        enrollment=ExecutorEnrollmentAdapter(  # type: ignore[arg-type]
            sessions, ring=rings.public, public_origin="https://stand.example"),
    )
    return driver.Surface(router)


@pytest.fixture
def stand(session: Session, admin_account: str, rings, package_dir: Path):
    return build_stand(session, rings)


def admin_call(surface, method: str, path: str, body: Any = None):
    headers = {"Content-Type": "application/json", "Idempotency-Key": f"install-{uuid4().hex}"}
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def make_connection(surface) -> str:
    created = admin_call(surface, "POST", "/executor-connections", {"kind": "pull", "display_name": "Claude Code"})
    assert created.status == 201, created.body
    connection_id = created.json()["connection_id"]
    revised = admin_call(surface, "POST", f"/executor-connections/{connection_id}/revisions", PULL_SETTINGS)
    assert revised.status == 201, revised.body
    return connection_id


def start_install(surface, connection_id: str, **body: Any) -> dict[str, Any]:
    created = admin_call(surface, "POST", f"/executor-connections/{connection_id}/agent-installs",
                         {**INSTALL_BODY, **body})
    assert created.status == 201, created.body
    return created.json()


def read_install(surface, connection_id: str, install_id: str) -> dict[str, Any]:
    answer = dispatch(surface, Request.build("GET", f"/executor-connections/{connection_id}/agent-installs/{install_id}"))
    assert answer.status == 200, answer.body
    return answer.json()


def confirm(surface, connection_id: str, install: dict[str, Any]) -> dict[str, Any]:
    answer = admin_call(
        surface, "POST", f"/executor-connections/{connection_id}/agent-installs/{install['install_id']}/confirm-host-key",
        {"host_key_fingerprint": install["observed_host_key_fingerprint"]})
    assert answer.status == 200, answer.body
    return answer.json()


def connection_secrets(surface, connection_id: str) -> list[Any]:
    answer = dispatch(surface, Request.build("GET", f"/executor-connections/{connection_id}"))
    assert answer.status == 200, answer.body
    return answer.json()["connection"]["secrets"]


def audit_mentions(session: Session, needle: str) -> int:
    return int(session.execute(text(
        "SELECT count(*) FROM audit_event WHERE payload::text LIKE :needle OR aggregate_id LIKE :needle"),
        {"needle": f"%{needle}%"}).scalar_one())


def events(session: Session, install_id: str) -> list[tuple[str, dict[str, Any]]]:
    return [(row[0], row[1]) for row in session.execute(text(
        "SELECT event_type, payload FROM audit_event WHERE aggregate_id = :id ORDER BY audit_event_id"),
        {"id": install_id}).all()]


def age_install(session: Session, install_id: str, seconds: int) -> None:
    """Make a session ``seconds`` older. ``created_at`` is frozen by a trigger, so the guard is lifted for this
    one statement (inside the test's own transaction, which is rolled back)."""
    guard = "ALTER TABLE executor_agent_install {} TRIGGER trg_executor_agent_install_frozen_guard"
    session.execute(text(guard.format("DISABLE")))
    session.execute(text(
        "UPDATE executor_agent_install SET created_at = created_at - make_interval(secs => :s) "
        "WHERE install_id = :id"), {"s": seconds, "id": install_id})
    session.execute(text(guard.format("ENABLE")))


# -- the worker, with a scripted SSH host ---------------------------------------------------------------


class ScriptedHost:
    """The SSH host. ``scan`` shows a key; ``execute`` records the call and answers as scripted. When the answer
    is a success it redeems the grant whose secret is the payload's second line, as ``install.sh`` would."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.key_line = host_key_line()
        self.answer = SUCCESS
        self.scans: list[Any] = []
        self.calls: list[dict[str, Any]] = []

    def scan(self, endpoint):
        self.scans.append(endpoint)
        return self.key_line

    def execute(self, endpoint, private_key, host_key, payload, *, timeout_s):
        self.calls.append({"endpoint": endpoint, "private_key": private_key, "host_key": host_key,
                           "payload": payload, "timeout_s": timeout_s})
        if self.answer.exit_status == 0:
            principal = authenticate_enrollment(self.session, payload.split(b"\n")[1].decode())
            assert principal is not None, "the grant in the payload is a grant the stand issued"
            redeem_enrollment(self.session, principal, runner_instance_id="agent-instance-0001")
        return self.answer


@pytest.fixture
def host(session: Session) -> ScriptedHost:
    return ScriptedHost(session)


def make_runner(session: Session, rings, host: ScriptedHost, package_dir: Path, *,
                resolves: list[str] | None = None) -> AgentInstallRunner:
    return AgentInstallRunner(
        lambda: nullcontext(session),  # type: ignore[arg-type]
        ring=rings.private,
        policy=DestinationPolicy(resolver=lambda name, port: resolves or [PUBLIC], networks=lambda: ()),
        environ={"AUDITMANAGER_PUBLIC_ORIGIN": "https://stand.example", PACKAGE_DIRECTORY_ENV: str(package_dir)},
        transport=host,
    )


@pytest.fixture
def runner(session: Session, rings, host: ScriptedHost, package_dir: Path) -> AgentInstallRunner:
    return make_runner(session, rings, host, package_dir)


def pump(runner: AgentInstallRunner) -> int:
    taken = runner.run_pending()
    runner.join(30)
    return taken


def drive_to_installing(stand, runner, host, connection_id: str, **body: Any) -> dict[str, Any]:
    """Create a session, let the worker scan it, and confirm the fingerprint it shows."""
    created = start_install(stand, connection_id, **body)
    assert pump(runner) == 1
    shown = read_install(stand, connection_id, created["install_id"])
    assert shown["state"] == "awaiting_host_key"
    assert shown["observed_host_key_fingerprint"] == host_key_fingerprint(host.key_line)
    assert confirm(stand, connection_id, shown)["state"] == "installing"
    return shown


# -- the whole way ----------------------------------------------------------------------------------------


def test_a_generated_key_session_goes_from_requested_to_succeeded_and_its_key_is_replaced(
    session, stand, runner, host,
) -> None:
    connection_id = make_connection(stand)
    created = start_install(stand, connection_id)
    install_id = created["install_id"]
    assert created["state"] == "requested" and connection_secrets(stand, connection_id) == []

    assert pump(runner) == 1 and host.calls == []
    shown = read_install(stand, connection_id, install_id)
    assert shown["state"] == "awaiting_host_key" and connection_secrets(stand, connection_id) == []
    assert (host.scans[0].host, host.scans[0].port, host.scans[0].user) == (PUBLIC, 22, USER)
    stored = session.execute(text("SELECT observed_host_key FROM executor_agent_install WHERE install_id = :id"),
                             {"id": install_id}).scalar_one()
    assert stored == host.key_line

    assert confirm(stand, connection_id, shown)["state"] == "installing"
    assert pump(runner) == 1
    done = read_install(stand, connection_id, install_id)
    assert done["state"] == "succeeded" and done.get("failure_reason") is None
    assert done["key_removed_at"] and done["finished_at"]
    assert done.get("public_key") is None and done.get("authorized_keys_line") is None, (
        "the key is gone from the session")
    assert connection_secrets(stand, connection_id) == []

    (call,) = host.calls
    assert call["host_key"] == host.key_line and call["private_key"].startswith("-----BEGIN OPENSSH PRIVATE KEY-----")
    assert (call["endpoint"].host, call["endpoint"].user) == (PUBLIC, USER)
    header = call["payload"].split(b"\n", 7)
    secret = header[1].decode()
    assert header[0] == b"AM-INSTALL/1" and header[2].decode() == "https://stand.example" and header[3].decode() == MODEL
    assert header[4].decode() == hashlib.sha256(ARCHIVE).hexdigest() and int(header[5]) == len(ARCHIVE)
    assert header[6].decode() == install_marker(install_id) and header[7] == ARCHIVE, (
        "the image's archive, byte for byte, behind the seven lines")

    row = session.execute(text(
        "SELECT state, failure_reason, key_secret_id, key_removed_at FROM executor_agent_install "
        "WHERE install_id = :id"), {"id": install_id}).one()
    assert row[0] == "succeeded" and row[1] is None and row[2] is None and row[3] is not None
    assert session.execute(text(
        "SELECT count(*) FROM executor_secret WHERE connection_id = :c AND purpose = 'agent_install_key' "
        "AND replaced_at IS NULL"), {"c": connection_id}).scalar_one() == 0
    (grant,) = session.execute(text(
        "SELECT created_by, redeemed_at IS NOT NULL, runner_token_id IS NOT NULL FROM executor_enrollment "
        "WHERE connection_id = :c"), {"c": connection_id}).all()
    assert grant[0] == driver.TEST_SUBJECT.user_uid, "attributed to the administrator who created the session"
    assert grant[1] and grant[2], "the agent registered through the same enrollment path B uses"
    assert session.execute(text("SELECT count(*) FROM executor_runner_token WHERE connection_id = :c"),
                           {"c": connection_id}).scalar_one() == 1
    claim = session.execute(text(
        "SELECT state, outcome FROM command_record WHERE command_type = :t AND idempotency_key = :k"),
        {"t": GRANT_COMMAND_TYPE, "k": grant_key(install_id)}).one()
    assert claim[0] == "succeeded", "the grant is the claim of the install"

    names = sorted(name for name, _ in events(session, install_id))
    assert names == sorted([
        "executor.agent_install_requested", "executor.agent_install_host_key_observed",
        "executor.agent_install_host_key_confirmed", "executor.agent_install_started",
        "executor.agent_install_succeeded", "executor.agent_install_key_removed"]), "each step journaled once"
    removed = dict(events(session, install_id))["executor.agent_install_key_removed"]
    assert removed["reason"] == "host_line_removed" and removed["purpose"] == "agent_install_key"
    for needle in (secret[4:], "PRIVATE KEY", host.key_line.split()[1], host_key_fingerprint(host.key_line)[7:]):
        assert audit_mentions(session, needle) == 0, needle
    assert key_line_state(SUCCESS.stdout) == "host_line_removed"


def test_a_pasted_key_session_installs_and_has_no_line_of_the_stands_to_remove(session, stand, runner, host) -> None:
    connection_id = make_connection(stand)
    drive_to_installing(stand, runner, host, connection_id, access="pasted_key", private_key=pasted_private_key())
    assert pump(runner) == 1
    (call,) = host.calls
    assert call["payload"].split(b"\n")[6] == b"-"
    install_id = session.execute(text("SELECT install_id FROM executor_agent_install WHERE connection_id = :c"),
                                 {"c": connection_id}).scalar_one()
    assert read_install(stand, connection_id, install_id)["state"] == "succeeded"
    assert dict(events(session, install_id))["executor.agent_install_key_removed"]["reason"] == "not_applicable"


# -- refusals ----------------------------------------------------------------------------------------------


def test_a_host_key_that_changed_after_the_confirmation_is_refused_with_no_grant_and_nothing_sent(
    session, stand, runner, host,
) -> None:
    connection_id = make_connection(stand)
    shown = drive_to_installing(stand, runner, host, connection_id)
    host.key_line = host_key_line()
    assert pump(runner) == 1
    done = read_install(stand, connection_id, shown["install_id"])
    assert (done["state"], done["failure_reason"]) == ("failed", "host_key_changed")
    assert host.calls == [], "no key, no secret and no package left the stand"
    assert session.execute(text("SELECT count(*) FROM executor_enrollment WHERE connection_id = :c"),
                           {"c": connection_id}).scalar_one() == 0
    assert session.execute(text(
        "SELECT count(*) FROM executor_secret WHERE connection_id = :c AND purpose = 'agent_install_key' "
        "AND replaced_at IS NULL"), {"c": connection_id}).scalar_one() == 0
    assert connection_secrets(stand, connection_id) == []


def test_sudo_that_wants_a_password_fails_the_session_and_the_retry_is_a_fresh_enrollment_on_one_connection(
    session, stand, runner, host,
) -> None:
    connection_id = make_connection(stand)
    host.answer = RemoteResult("completed", exit_status=86, stdout=b"am-install: key-line removed\n")
    first = drive_to_installing(stand, runner, host, connection_id)
    assert pump(runner) == 1
    failed = read_install(stand, connection_id, first["install_id"])
    assert (failed["state"], failed["failure_reason"]) == ("failed", "sudo_password_required")
    assert failed.get("public_key") is None

    host.answer = SUCCESS
    second = drive_to_installing(stand, runner, host, connection_id)
    assert second["install_id"] != first["install_id"]
    assert pump(runner) == 1
    assert read_install(stand, connection_id, second["install_id"])["state"] == "succeeded"

    grants = session.execute(text(
        "SELECT redeemed_at IS NOT NULL, revoked_at IS NOT NULL FROM executor_enrollment "
        "WHERE connection_id = :c ORDER BY created_at"), {"c": connection_id}).all()
    assert [tuple(row) for row in grants] == [(False, True), (True, False)], (
        "the first, unspent grant was revoked by the second")
    assert session.execute(text("SELECT count(DISTINCT connection_id) FROM executor_agent_install "
                                "WHERE install_id IN (:a, :b)"),
                           {"a": first["install_id"], "b": second["install_id"]}).scalar_one() == 1
    secrets = [call["payload"].split(b"\n")[1] for call in host.calls]
    assert len(secrets) == 2 and secrets[0] != secrets[1]


def test_a_grant_that_was_never_redeemed_is_not_a_success(session, stand, runner, host) -> None:
    """``install.sh`` exits 0 on a host that already holds a token while it refuses the new secret."""
    connection_id = make_connection(stand)

    def say_ok_without_enrolling(endpoint, private_key, host_key, payload, *, timeout_s):
        host.calls.append({"payload": payload})
        return SUCCESS

    host.execute = say_ok_without_enrolling  # type: ignore[method-assign]
    shown = drive_to_installing(stand, runner, host, connection_id)
    assert pump(runner) == 1
    done = read_install(stand, connection_id, shown["install_id"])
    assert (done["state"], done["failure_reason"]) == ("failed", "enrollment_failed")


@pytest.mark.parametrize("target", ["localhost", "postgres"])
def test_a_target_the_destination_rules_refuse_is_never_connected_to(session, stand, runner, host, target: str) -> None:
    """The API accepts the name syntactically; the worker refuses it before any connection."""
    connection_id = make_connection(stand)
    created = start_install(stand, connection_id, ssh_host=target)
    assert pump(runner) == 1
    done = read_install(stand, connection_id, created["install_id"])
    assert (done["state"], done["failure_reason"]) == ("failed", "host_unreachable")
    assert host.scans == [] and host.calls == []


def test_a_name_that_resolves_to_a_private_address_is_refused(session, rings, stand, host, package_dir) -> None:
    runner = make_runner(session, rings, host, package_dir, resolves=["10.0.0.5"])
    connection_id = make_connection(stand)
    created = start_install(stand, connection_id)
    assert pump(runner) == 1
    assert read_install(stand, connection_id, created["install_id"])["failure_reason"] == "host_unreachable"
    assert host.scans == []


def test_without_a_public_origin_the_session_fails_and_the_origin_is_never_guessed(
    session, rings, stand, host, package_dir,
) -> None:
    runner = AgentInstallRunner(
        lambda: nullcontext(session), ring=rings.private,  # type: ignore[arg-type]
        policy=DestinationPolicy(resolver=lambda name, port: [PUBLIC], networks=lambda: ()),
        environ={"AUDITMANAGER_PUBLIC_ORIGIN": "https://", PACKAGE_DIRECTORY_ENV: str(package_dir)}, transport=host)
    connection_id = make_connection(stand)
    shown = drive_to_installing(stand, runner, host, connection_id)
    assert pump(runner) == 1
    done = read_install(stand, connection_id, shown["install_id"])
    assert (done["state"], done["failure_reason"]) == ("failed", "enrollment_failed")
    assert host.calls == []
    assert session.execute(text("SELECT count(*) FROM executor_enrollment WHERE connection_id = :c"),
                           {"c": connection_id}).scalar_one() == 0


def test_a_worker_without_the_private_ring_cannot_open_the_key_and_says_so(session, stand, host, package_dir) -> None:
    runner = AgentInstallRunner(
        lambda: nullcontext(session), ring=None,  # type: ignore[arg-type]
        policy=DestinationPolicy(resolver=lambda name, port: [PUBLIC], networks=lambda: ()),
        environ={"AUDITMANAGER_PUBLIC_ORIGIN": "https://stand.example", PACKAGE_DIRECTORY_ENV: str(package_dir)},
        transport=host)
    connection_id = make_connection(stand)
    shown = drive_to_installing(stand, runner, host, connection_id)
    assert pump(runner) == 1
    done = read_install(stand, connection_id, shown["install_id"])
    assert (done["state"], done["failure_reason"]) == ("failed", "secret_unreadable")
    assert host.calls == []


# -- the claim -------------------------------------------------------------------------------------------


def test_an_install_is_claimed_by_its_grant_and_a_dead_workers_session_ends_by_its_lifetime(
    session, rings, stand, runner, host, package_dir,
) -> None:
    connection_id = make_connection(stand)
    shown = drive_to_installing(stand, runner, host, connection_id)
    install_id = shown["install_id"]
    other = make_runner(session, rings, host, package_dir)  # a second worker on the same database
    work = runner._claim()
    assert work is not None and work.kind == "install", "looking at a session claims nothing"
    # ... the first worker issues the grant -- the claim -- and dies before the install
    issue_executor_enrollment(
        session, connection_id=connection_id, roles=("admin",), idempotency_key=grant_key(install_id),
        actor_uid=driver.TEST_SUBJECT.user_uid, configured_origin="https://stand.example")
    assert runner._claim() is None and other._claim() is None, "the ledger key is taken: nobody installs twice"
    assert pump(other) == 0 and host.calls == []
    assert read_install(stand, connection_id, install_id)["state"] == "installing"
    (grant,) = session.execute(text("SELECT redeemed_at FROM executor_enrollment WHERE connection_id = :c"),
                               {"c": connection_id}).all()
    assert grant[0] is None, "the grant was never spent"

    # a worker that read the session before the claim and reaches the grant second sends nothing
    late = make_runner(session, rings, host, package_dir)
    ready = late._ready(work)
    assert ready is not None and not isinstance(ready, str)
    endpoint, failure = late._verify_host(ready)
    assert failure is None and endpoint is not None
    assert late._grant(ready, endpoint) == "taken" and host.calls == []

    age_install(session, install_id, INSTALL_SESSION_SECONDS + 1)
    ended = read_install(stand, connection_id, install_id)
    assert (ended["state"], ended["failure_reason"]) == ("failed", "timed_out")
    assert pump(other) == 0, "an ended session is nobody's work"


def test_a_requested_session_is_taken_by_one_worker_only(session, rings, stand, runner, host, package_dir) -> None:
    connection_id = make_connection(stand)
    start_install(stand, connection_id)
    other = make_runner(session, rings, host, package_dir)
    first = runner._claim()
    assert first is not None and first.kind == "scan"
    assert other._claim() is None, "scanning is stored: the session is no longer requested"
    state = session.execute(text("SELECT state FROM executor_agent_install WHERE install_id = :id"),
                           {"id": first.record.install_id}).scalar_one()
    assert state == "scanning"


def test_a_session_the_api_ended_while_the_worker_scanned_is_left_as_the_sweep_wrote_it(
    session, stand, runner, host,
) -> None:
    connection_id = make_connection(stand)
    created = start_install(stand, connection_id)
    work = runner._claim()
    assert work is not None
    age_install(session, created["install_id"], INSTALL_SESSION_SECONDS + 1)
    swept = read_install(stand, connection_id, created["install_id"])
    assert (swept["state"], swept["failure_reason"]) == ("failed", "timed_out")
    runner._scan(work)  # the worker is late: its write finds the session ended
    after = read_install(stand, connection_id, created["install_id"])
    assert (after["state"], after["failure_reason"]) == ("failed", "timed_out")
    assert after.get("observed_host_key_fingerprint") is None
