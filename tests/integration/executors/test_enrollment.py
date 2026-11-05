"""`EXEC2-ENROLL-01`: the universal agent over the served application (B2 section 11 items 2, 7 and 8, the
server half).

Two halves in one file, told apart by what a test asks for:

* **the edge, with a stand-in port** -- no fixture of the database harness. What is under test is the
  authorization seam and the eight routes: an enrollment secret is a principal of its own that reaches the
  exchange and nothing else, a runner token reaches the health report and not the exchange, the package
  route needs no credential and is the same ``422`` for every version the image does not hold, and a
  stand-in that raises a typed refusal is what a caller sees;
* **real rows** -- every test below the second banner requests ``session`` (and the fixtures built on it),
  the suite's database harness, which **fails hard without ``DATABASE_URL`` and never skips**
  (``tests/integration/README.md``): this suite has no pytest marker for it, the fixture is the marker.
  They drive ``ExecutorEnrollmentAdapter`` with the real modules and the real rows: the secret is shown once
  and stored as a hash, the exchange is single-use and idempotent for the agent that lost the response, the
  health report reaches the connection's detail, a new grant revokes the old one, a move is journaled, and an
  install session seals its key and stays out of the connection's secrets.

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
from auditmanager.api.schemas import models
from auditmanager.api.security import (
    ENROLLMENT_OPERATIONS,
    RUNNER_OPERATIONS,
    UNAUTHENTICATED_OPERATIONS,
    EnrollmentIdentity,
    RunnerIdentity,
)
from auditmanager.executors.agent_package import PACKAGE_DIRECTORY_ENV, load_package
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.executors.conftest import driver

Request, dispatch = driver.Request, driver.dispatch
ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "contracts" / "api" / "v1" / "openapi.json"

CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
INSTALL = "exai_01M2545JSD15ETSNNV904X991K"
SECRET = "ame_abcd1234_" + "A" * 43
TOKEN = "amr_abcd1234_" + "B" * 43
INSTANCE = "agent-instance-0001"
ENROLLMENT = "exen_01M2545JSD15ETSNNV904X991K"
NOW = "2026-11-02T12:00:00Z"
AGENT_OPERATIONS = {
    "issueExecutorEnrollment": ("POST", "/executor-connections/{connection_id}/enrollments"),
    "redeemExecutorEnrollment": ("POST", "/runner/enroll"),
    "reportRunnerHealth": ("POST", "/runner/health"),
    "downloadAgentPackage": ("GET", "/runner/agent-package/{version}"),
    "createExecutorAgentInstall": ("POST", "/executor-connections/{connection_id}/agent-installs"),
    "getExecutorAgentInstall": ("GET", "/executor-connections/{connection_id}/agent-installs/{install_id}"),
    "confirmExecutorAgentInstallHostKey": (
        "POST", "/executor-connections/{connection_id}/agent-installs/{install_id}/confirm-host-key"),
    "setExecutorIntegrationAuthorisation": (
        "POST", "/executor-connections/{connection_id}/integration-authorisation"),
}
HEALTH = {
    "agent_version": "0.9.0", "concurrency": 1, "execution_profile": "command", "features": ["images"],
    "clis": [{"cli": "claude", "installed": True, "version": "2.1.3", "auth_state": "valid"},
             {"cli": "codex", "installed": False, "auth_state": "unknown"}],
}


# =================================================================================================
# the edge, with a stand-in port (no database)
# =================================================================================================


def _install_view(state: str = "requested") -> models.ExecutorAgentInstall:
    return models.ExecutorAgentInstall.model_validate({
        "install_id": INSTALL, "connection_id": CONNECTION, "state": state, "access": "generated_key",
        "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu", "created_at": NOW,
        "created_by": "usr_01M2545JSD15ETSNNV904X991K", "updated_at": NOW,
    })


class StubEnrollment:
    """The ``EnrollmentPort``: it records what reached it, and answers a fixed secret."""

    def __init__(self, package_directory: Path | None = None) -> None:
        self.calls: list[tuple] = []
        self.refuse: DomainError | None = None
        self.package_directory = package_directory

    def authenticate_enrollment(self, presented: str):
        self.calls.append(("authenticate", presented))
        return EnrollmentIdentity(ENROLLMENT, CONNECTION, b"k" * 32) if presented == SECRET else None

    def _maybe_refuse(self) -> None:
        if self.refuse is not None:
            raise self.refuse

    def redeem_enrollment(self, *, enrollment, runner_instance_id):
        self.calls.append(("redeem", enrollment, runner_instance_id))
        self._maybe_refuse()
        return models.IssuedRunnerToken.model_validate({"token": TOKEN, "runner_token": {
            "token_id": "ern_01M2545JSD15ETSNNV904X991K", "connection_id": CONNECTION,
            "token_prefix": TOKEN[:12], "created_at": NOW, "created_by": "usr_01M2545JSD15ETSNNV904X991K",
            "expires_at": "2026-12-02T12:00:00Z"}})

    def report_health(self, *, runner, body):
        self.calls.append(("health", runner, body.concurrency))
        self._maybe_refuse()
        return models.RunnerHealthAck.model_validate({"recorded_at": NOW})

    def read_package(self, *, version):
        self.calls.append(("package", version))
        self._maybe_refuse()
        package, content = load_package(version, directory=self.package_directory)
        return package.file_name, content

    def issue_enrollment(self, *, connection_id, user_uid, idempotency_key):
        self.calls.append(("issue", connection_id))
        self._maybe_refuse()
        return models.IssuedExecutorEnrollment.model_validate({
            "secret": SECRET, "package_version": "0.9.0", "package_sha256": "a" * 64,
            "command": "echo install", "enrollment": {
                "enrollment_id": ENROLLMENT, "connection_id": connection_id, "secret_prefix": SECRET[:12],
                "state": "pending", "created_at": NOW, "created_by": user_uid,
                "expires_at": "2026-11-02T12:15:00Z"}})

    def create_agent_install(self, *, connection_id, body, user_uid, idempotency_key):
        self.calls.append(("create_install", connection_id, body.access.value))
        return _install_view()

    def get_agent_install(self, *, connection_id, install_id):
        self.calls.append(("get_install", connection_id, install_id))
        return _install_view()

    def confirm_agent_install_host_key(self, *, connection_id, install_id, host_key_fingerprint, user_uid,
                                       idempotency_key):
        self.calls.append(("confirm", install_id, host_key_fingerprint))
        return _install_view("installing")

    def set_integration_authorisation(self, *, connection_id, authorised, user_uid, idempotency_key):
        self.calls.append(("mark", connection_id, authorised))
        return models.ExecutorConnection.model_validate({
            "connection_id": connection_id, "kind": "pull", "display_name": "Claude", "created_at": NOW,
            "created_by": user_uid, "secrets": [], "routed_work_kinds": []})


class TokenOnlyRunner:
    """The ``RunnerPort`` as far as the seam asks it: a runner token and nothing else.

    Not called ``StubRunner``: ``test_runner_seam.StubRunner`` is the whole port and ``DeliveringRunner`` extends it, and
    the port-wholeness guard resolves a base class by name, so a second class of that name makes the base unreadable.

    Any other method of the port is an ``AttributeError`` that names it -- the form
    ``test_every_port_implementation_is_whole`` reads as "answers to nothing it was not given"; this suite drives
    only the authentication of a runner token."""

    def __init__(self) -> None:
        self.presented: list[str] = []

    def authenticate_runner(self, presented: str, *, address: str | None):
        self.presented.append(presented)
        return RunnerIdentity("ern_T", CONNECTION) if presented == TOKEN else None

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"this suite drives only authenticate_runner of the RunnerPort, not {name}")


class _Wired:
    """``StubEnrollment`` as ``build_router`` is given it: every call forwarded, so the stub still records it.

    A class constructed in the call is what ``test_every_port_implementation_is_whole`` can read; a parameter
    handed through is not, and the guard reports what it cannot read."""

    def __init__(self, port: "StubEnrollment") -> None:
        self._port = port

    def __getattr__(self, name: str) -> Any:
        return getattr(self._port, name)


def _surface(port: StubEnrollment | None, *, roles: frozenset[str] = frozenset({"admin"})):
    if port is None:
        router = build_router(
            projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
            exports=None,  # type: ignore[arg-type]
            credentials=driver.SuiteCredentialAdapter(roles=roles),
            accounts=driver.SuiteAccountAdapter(),
            registrations=driver.SuiteRegistrationAdapter(),
            runner=TokenOnlyRunner(),  # type: ignore[arg-type]
            enrollment=None,
        )
    else:
        router = build_router(
            projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
            exports=None,  # type: ignore[arg-type]
            credentials=driver.SuiteCredentialAdapter(roles=roles),
            accounts=driver.SuiteAccountAdapter(),
            registrations=driver.SuiteRegistrationAdapter(),
            runner=TokenOnlyRunner(),  # type: ignore[arg-type]
            enrollment=_Wired(port),  # type: ignore[arg-type]
        )
    return driver.Surface(router)


@pytest.fixture
def stub(tmp_path: Path) -> StubEnrollment:
    return StubEnrollment(tmp_path)


@pytest.fixture
def edge(stub: StubEnrollment):
    return _surface(stub)


def post(surface, path: str, body: Any = None, *, bearer: str | None = None, credential: str | None = None,
         **headers: str):
    sent = {"Content-Type": "application/json", **headers}
    if bearer is not None:
        sent["Authorization"] = f"Bearer {bearer}"
    return dispatch(
        surface, Request.build("POST", path, headers=sent, body=json.dumps({} if body is None else body).encode()),
        credential=credential)


def exchange(surface, bearer: str | None, instance: str = INSTANCE):
    return post(surface, "/runner/enroll", {"runner_instance_id": instance}, bearer=bearer)


def publish(directory: Path, version: str = "0.9.0", content: bytes = b"\x1f\x8b the agent package") -> bytes:
    name = f"auditmanager-agent-{version}.tar.gz"
    (directory / name).write_bytes(content)
    (directory / (name + ".sha256")).write_text(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
    return content


def test_the_eight_operations_are_served_where_the_contract_puts_them(edge) -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))["paths"]
    served = edge.app.openapi()["paths"]
    for operation_id, (method, path) in AGENT_OPERATIONS.items():
        assert contract[path][method.lower()]["operationId"] == operation_id
        assert served[path][method.lower()]["operationId"] == operation_id, operation_id
        assert (served[path][method.lower()].get("security") == []) == (operation_id == "downloadAgentPackage")


def test_the_registers_name_each_operation_once() -> None:
    assert ENROLLMENT_OPERATIONS == {"redeemExecutorEnrollment"}
    assert "reportRunnerHealth" in RUNNER_OPERATIONS and "downloadAgentPackage" in UNAUTHENTICATED_OPERATIONS
    assert not ENROLLMENT_OPERATIONS & (RUNNER_OPERATIONS | UNAUTHENTICATED_OPERATIONS)


def test_an_enrollment_secret_reaches_the_exchange_and_the_port_sees_the_grant_not_the_secret(edge, stub) -> None:
    answer = exchange(edge, SECRET)
    assert answer.status == 201, answer.body
    assert answer.json()["token"] == TOKEN and answer.header("X-Correlation-Id")
    identity = next(call for call in stub.calls if call[0] == "redeem")[1]
    assert identity == EnrollmentIdentity(ENROLLMENT, CONNECTION, b"k" * 32)
    assert SECRET not in repr(identity) and "kkkk" not in repr(identity)


@pytest.mark.parametrize("presented", [
    "amr_abcd1234_" + "B" * 43, "ame_zzzzzzzz_" + "A" * 43, "ame_abcd1234_" + "A" * 42, "garbage", "am2.payload.tag", "",
])
def test_a_runner_token_a_wrong_secret_and_garbage_are_the_same_401_at_the_exchange(edge, stub, presented: str) -> None:
    answer = exchange(edge, presented or None)
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"
    assert not any(call[0] == "redeem" for call in stub.calls)


def test_a_users_credential_and_no_credential_cannot_exchange(edge, stub) -> None:
    for answer in (dispatch(edge, Request.build("POST", "/runner/enroll", headers={"Content-Type": "application/json"},
                                                body=json.dumps({"runner_instance_id": INSTANCE}).encode())),
                   exchange(edge, None)):
        assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"
    assert not any(call[0] == "redeem" for call in stub.calls)


def test_the_exchange_is_closed_when_no_port_authenticates_a_secret() -> None:
    bare = _surface(None)
    answer = exchange(bare, SECRET)
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"


@pytest.mark.parametrize("path", ["/runner/tasks/claim", "/runner/health", "/executor-connections"])
def test_an_enrollment_secret_reaches_no_other_operation(edge, stub, path: str) -> None:
    if path == "/executor-connections":
        answer = dispatch(edge, Request.build("GET", path, headers={"Authorization": f"Bearer {SECRET}"}),
                          credential=None)
    else:
        answer = post(edge, path, {"wait_seconds": 0} if "claim" in path else HEALTH, bearer=SECRET)
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"
    assert not any(call[0] in ("health", "redeem") for call in stub.calls)


def test_a_typed_refusal_of_the_exchange_is_what_the_caller_reads(edge, stub) -> None:
    stub.refuse = DomainError(ErrorCode.CONFLICT, conflict_reason="enrollment_redeemed")
    answer = exchange(edge, SECRET)
    assert answer.status == 409
    assert answer.json()["error_code"] == "conflict"
    assert answer.json()["details"] == {"conflict_reason": "enrollment_redeemed"}
    assert SECRET not in answer.body.decode()


def test_the_exchange_refuses_an_instance_id_outside_the_declared_form(edge, stub) -> None:
    for bad in ("short", "has space 1", "x" * 65):
        answer = exchange(edge, SECRET, bad)
        assert answer.status == 422 and answer.json()["details"]["field"] == "runner_instance_id"
    answer = post(edge, "/runner/enroll", {"runner_instance_id": INSTANCE, "extra": 1}, bearer=SECRET)
    assert answer.status == 422 and answer.json()["details"]["constraint"] == "additionalProperties"
    assert not any(call[0] == "redeem" for call in stub.calls)


def test_a_runner_token_reports_health_and_the_port_sees_its_identity(edge, stub) -> None:
    answer = post(edge, "/runner/health", HEALTH, bearer=TOKEN)
    assert answer.status == 200 and answer.json() == {"recorded_at": NOW}
    assert stub.calls[-1] == ("health", RunnerIdentity("ern_T", CONNECTION), 1)


@pytest.mark.parametrize("bearer", [SECRET, "amr_zzzzzzzz_" + "B" * 43, None])
def test_only_a_runner_token_reports_health(edge, stub, bearer: str | None) -> None:
    answer = post(edge, "/runner/health", HEALTH, bearer=bearer)
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"
    assert not any(call[0] == "health" for call in stub.calls)


@pytest.mark.parametrize(("change", "field"), [
    ({"concurrency": 0}, "concurrency"), ({"concurrency": 17}, "concurrency"),
    ({"execution_profile": "shell"}, "execution_profile"), ({"features": ["gpu"]}, "features"),
    ({"agent_version": "../x"}, "agent_version"),
    ({"clis": [{"cli": "gemini", "installed": True, "auth_state": "valid"}]}, "cli"),
])
def test_a_report_outside_the_closed_vocabulary_is_a_422_before_the_port_is_reached(
    edge, stub, change: dict[str, Any], field: str,
) -> None:
    answer = post(edge, "/runner/health", {**HEALTH, **change}, bearer=TOKEN)
    assert answer.status == 422 and answer.json()["details"]["field"] == field
    assert not any(call[0] == "health" for call in stub.calls)


def test_a_report_with_a_property_the_schema_does_not_declare_is_refused(edge, stub) -> None:
    answer = post(edge, "/runner/health", {**HEALTH, "credential_path": "/root/.claude/.credentials.json"},
                  bearer=TOKEN)
    assert answer.status == 422 and answer.json()["details"]["constraint"] == "additionalProperties"
    assert "credentials" not in answer.body.decode()


def test_the_package_needs_no_credential_and_is_served_with_the_digest_the_command_carries(
    edge, stub, tmp_path: Path,
) -> None:
    content = publish(tmp_path)
    for credential, headers in ((None, {}), (driver.TEST_TOKEN, {}), (None, {"Authorization": "Bearer garbage"})):
        answer = dispatch(edge, Request.build("GET", "/runner/agent-package/0.9.0", headers=headers),
                          credential=credential)
        assert answer.status == 200, answer.body
        assert answer.body == content and hashlib.sha256(answer.body).hexdigest() == hashlib.sha256(content).hexdigest()
        assert answer.header("Content-Type") == "application/gzip"
        assert answer.header("Content-Length") == str(len(content)) and answer.header("X-Correlation-Id")
        assert "auditmanager-agent-0.9.0.tar.gz" in (answer.header("Content-Disposition") or "")


@pytest.mark.parametrize("version", ["9.9.9", "latest", "1.2", "0.9.0.0", "0.9.x", "..", "%2e%2e", "0.9.0%00"])
def test_a_version_the_image_does_not_hold_is_the_same_422_and_never_a_listing(
    edge, stub, tmp_path: Path, version: str,
) -> None:
    publish(tmp_path)
    answer = dispatch(edge, Request.build("GET", f"/runner/agent-package/{version}"), credential=None)
    if answer.status == 404:  # a path the router cannot match is no route; it still lists nothing
        assert "0.9.0" not in answer.body.decode()
        return
    assert answer.status == 422, answer.body
    assert answer.json()["error_code"] == "validation_failed"
    assert answer.json()["details"] == {"field": "version", "constraint": "package_version_unknown"}
    assert "0.9.0" not in answer.body.decode()


def test_a_path_that_climbs_out_of_the_package_directory_serves_no_file(edge, stub, tmp_path: Path) -> None:
    publish(tmp_path)
    (tmp_path / "notes.txt").write_text("private-file-content")
    for target in ("/runner/agent-package/../../etc/passwd", "/runner/agent-package/..%2f..%2fetc%2fpasswd",
                   "/runner/agent-package/%2e%2e%2fnotes.txt", "/runner/agent-package//etc/passwd",
                   "/runner/agent-package/notes.txt", "/runner/agent-package/auditmanager-agent-0.9.0.tar.gz"):
        answer = dispatch(edge, Request.build("GET", target), credential=None)
        assert answer.status in (404, 422), (target, answer.status)
        assert b"root:" not in answer.body and b"private-file-content" not in answer.body


def test_an_image_without_a_package_is_a_503_that_names_the_dependency(edge, stub) -> None:
    answer = dispatch(edge, Request.build("GET", "/runner/agent-package/0.9.0"), credential=None)
    assert answer.status == 503 and answer.json()["error_code"] == "dependency_unavailable"
    assert answer.json()["details"] == {"dependency": "agent_package"}


def test_the_administrators_operations_are_for_an_administrator_and_a_keyed_write_needs_its_key(stub) -> None:
    expert = _surface(stub, roles=frozenset({"expert"}))
    admin = _surface(stub)
    path = f"/executor-connections/{CONNECTION}/enrollments"
    keyed = {"Idempotency-Key": f"enroll-{uuid4().hex}"}
    denied = dispatch(expert, Request.build("POST", path, headers=keyed))
    assert denied.status == 403 and denied.json()["details"] == {"required_capability": "role:admin"}
    missing = dispatch(admin, Request.build("POST", path))
    assert missing.status == 422 and missing.json()["details"]["field"] == "Idempotency-Key"
    done = dispatch(admin, Request.build("POST", path, headers=keyed))
    assert done.status == 201 and done.json()["secret"] == SECRET
    assert [call[0] for call in stub.calls].count("issue") == 1


def test_the_install_operations_reach_the_port_with_the_ids_of_the_path(stub) -> None:
    admin = _surface(stub)
    base = f"/executor-connections/{CONNECTION}"
    keyed = {"Content-Type": "application/json", "Idempotency-Key": f"k-{uuid4().hex}"}
    created = dispatch(admin, Request.build("POST", f"{base}/agent-installs", headers=keyed, body=json.dumps(
        {"access": "generated_key", "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu"}).encode()))
    assert created.status == 201 and created.json()["state"] == "requested"
    read = dispatch(admin, Request.build("GET", f"{base}/agent-installs/{INSTALL}"))
    assert read.status == 200 and read.json()["install_id"] == INSTALL
    fingerprint = "SHA256:" + "A" * 43
    confirmed = dispatch(admin, Request.build(
        "POST", f"{base}/agent-installs/{INSTALL}/confirm-host-key",
        headers={**keyed, "Idempotency-Key": f"k-{uuid4().hex}"},
        body=json.dumps({"host_key_fingerprint": fingerprint}).encode()))
    assert confirmed.status == 200 and confirmed.json()["state"] == "installing"
    mark = dispatch(admin, Request.build("POST", f"{base}/integration-authorisation",
                                         headers={**keyed, "Idempotency-Key": f"k-{uuid4().hex}"},
                                         body=json.dumps({"authorised": True}).encode()))
    assert mark.status == 200 and mark.json()["connection_id"] == CONNECTION
    assert [call[0] for call in stub.calls] == ["create_install", "get_install", "confirm", "mark"]
    assert ("confirm", INSTALL, fingerprint) in stub.calls


def test_a_malformed_install_identity_is_a_404_and_reaches_no_port(stub) -> None:
    admin = _surface(stub)
    answer = dispatch(admin, Request.build("GET", f"/executor-connections/{CONNECTION}/agent-installs/not-an-id"))
    assert answer.status == 404 and stub.calls == []


def test_the_issue_operation_hands_the_port_no_origin_taken_from_the_request(stub) -> None:
    """The origin of the install command is the stand's configured one; the request's ``Host`` and forwarded
    scheme never reach the port (behind the web tier they are the API's own internal name)."""
    admin = _surface(stub)
    path = f"/executor-connections/{CONNECTION}/enrollments"
    done = dispatch(admin, Request.build(
        "POST", path, headers={"Idempotency-Key": f"enroll-{uuid4().hex}", "Host": "api:8000",
                               "X-Forwarded-Proto": "http"}))
    assert done.status == 201
    assert stub.calls[-1] == ("issue", CONNECTION)


# =================================================================================================
# real rows (needs PostgreSQL: every test below requests `session`, the harness that fails without it)
# =================================================================================================

MODEL = "claude-opus-5"
PULL_SETTINGS = {
    "pin_id": MODEL, "gateway_model": MODEL, "billing": "not_metered", "allow_client_documents": False,
    "timeout_seconds": 60, "pull_client": "agent", "answer_deadline_seconds": 60, "max_claimed_tasks": 1,
}


@pytest.fixture
def package_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> bytes:
    monkeypatch.setenv(PACKAGE_DIRECTORY_ENV, str(tmp_path))
    return publish(tmp_path)


def build_stand(session: Session, rings, *, public_origin: str | None):
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
            sessions, ring=rings.public, public_origin=public_origin),
    )
    return driver.Surface(router)


@pytest.fixture
def stand(session: Session, admin_account: str, rings, package_content: bytes):
    return build_stand(session, rings, public_origin="https://stand.example")


def admin_call(surface, method: str, path: str, body: Any = None, *, key: str | None = None):
    headers = {"Content-Type": "application/json", "Idempotency-Key": key or f"enroll-{uuid4().hex}"}
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def read_connection(surface, connection_id: str) -> dict[str, Any]:
    answer = dispatch(surface, Request.build("GET", f"/executor-connections/{connection_id}"))
    assert answer.status == 200, answer.body
    return answer.json()


def make_connection(surface, *, kind: str = "pull") -> str:
    created = admin_call(surface, "POST", "/executor-connections", {"kind": kind, "display_name": "Claude Code"})
    assert created.status == 201, created.body
    connection_id = created.json()["connection_id"]
    if kind == "pull":
        revised = admin_call(surface, "POST", f"/executor-connections/{connection_id}/revisions", PULL_SETTINGS)
        assert revised.status == 201, revised.body
    return connection_id


def issue(surface, connection_id: str, *, key: str | None = None):
    return admin_call(surface, "POST", f"/executor-connections/{connection_id}/enrollments", key=key)


def agent_call(surface, bearer: str, path: str, body: Any = None):
    return post(surface, path, body, bearer=bearer)


def audit_mentions(session: Session, needle: str) -> int:
    return int(session.execute(text(
        "SELECT count(*) FROM audit_event WHERE payload::text LIKE :needle"), {"needle": f"%{needle}%"}).scalar_one())


def test_a_grant_is_shown_once_stored_only_as_a_hash_and_listed_without_its_secret(
    session, stand, package_content: bytes,
) -> None:
    connection_id = make_connection(stand)
    key = f"enroll-{uuid4().hex}"
    first = issue(stand, connection_id, key=key)
    assert first.status == 201, first.body
    body = first.json()
    secret, meta = body["secret"], body["enrollment"]
    assert len(secret) == 56 and secret.startswith(meta["secret_prefix"] + "_") and meta["state"] == "pending"
    assert body["package_version"] == "0.9.0"
    assert body["package_sha256"] == hashlib.sha256(package_content).hexdigest()
    command = body["command"]
    assert command.count(secret) == 1 and f"{body['package_sha256']}  agent.tar.gz" in command
    assert "sha256sum -c -" in command and "https://stand.example/api/v1/runner/agent-package/0.9.0" in command
    stored = session.execute(text(
        "SELECT secret_prefix, secret_hash FROM executor_enrollment WHERE enrollment_id = :id"),
        {"id": meta["enrollment_id"]}).one()
    assert stored[0] == meta["secret_prefix"] and bytes(stored[1]) == hashlib.sha256(secret.encode()).digest()
    assert audit_mentions(session, secret[4:]) == 0 and audit_mentions(session, secret[:12]) == 0

    again = issue(stand, connection_id, key=key)
    assert again.status == 409 and again.json()["details"] == {"conflict_reason": "enrollment_shown_once"}
    assert secret not in again.body.decode()

    detail = read_connection(stand, connection_id)
    assert [item["enrollment_id"] for item in detail["enrollments"]] == [meta["enrollment_id"]]
    assert secret not in json.dumps(detail) and "secret_hash" not in json.dumps(detail)
    assert detail["enrollments"][0]["state"] == "pending"


@pytest.mark.parametrize("configured", [None, "", "not an origin", "https://stand.example/path"])
def test_a_stand_without_a_valid_public_origin_issues_nothing_and_never_guesses_one(
    session, admin_account: str, rings, package_content: bytes, configured: str | None,
) -> None:
    """The origin of the install command is the configured one alone: the request's ``Host`` is never a
    fallback (behind the web tier it is the API's internal name). No grant is written, and the idempotency key
    is not spent: the same key issues once the stand is configured."""
    unconfigured = build_stand(session, rings, public_origin=configured)
    configured_stand = build_stand(session, rings, public_origin="https://stand.example")
    connection_id = make_connection(configured_stand)
    key = f"enroll-{uuid4().hex}"
    refused = issue(unconfigured, connection_id, key=key)
    assert refused.status == 503 and refused.json()["error_code"] == "dependency_unavailable"
    assert refused.json()["details"] == {"dependency": "public_origin"}
    assert read_connection(configured_stand, connection_id)["enrollments"] == []
    assert session.execute(text("SELECT count(*) FROM executor_enrollment WHERE connection_id = :id"),
                           {"id": connection_id}).scalar_one() == 0
    done = issue(configured_stand, connection_id, key=key)
    assert done.status == 201, done.body
    assert "https://stand.example/api/v1/runner/agent-package/0.9.0" in done.json()["command"]


def test_the_exchange_registers_the_agent_once_and_the_token_it_yields_claims_like_any_runner_token(
    session, stand,
) -> None:
    connection_id = make_connection(stand)
    secret = issue(stand, connection_id).json()["secret"]
    first = exchange(stand, secret)
    assert first.status == 201, first.body
    token, meta = first.json()["token"], first.json()["runner_token"]
    assert len(token) == 56 and token.startswith(meta["token_prefix"] + "_") and meta["connection_id"] == connection_id
    stored = session.execute(text("SELECT token_hash FROM executor_runner_token WHERE token_id = :id"),
                             {"id": meta["token_id"]}).scalar_one()
    assert bytes(stored) == hashlib.sha256(token.encode()).digest()
    assert audit_mentions(session, token[4:]) == 0 and audit_mentions(session, secret[4:]) == 0

    claim = agent_call(stand, token, "/runner/tasks/claim", {"wait_seconds": 0})
    assert claim.status == 204, "the token of an exchange is a runner token of its connection"

    detail = read_connection(stand, connection_id)
    (grant,) = detail["enrollments"]
    assert grant["state"] == "redeemed" and grant["runner_token_id"] == meta["token_id"]
    assert [item["token_id"] for item in detail["runner_tokens"]] == [meta["token_id"]]


def test_a_repeat_by_the_agent_that_lost_the_response_gets_a_fresh_token_and_the_first_stops_working(
    session, stand,
) -> None:
    connection_id = make_connection(stand)
    secret = issue(stand, connection_id).json()["secret"]
    first = exchange(stand, secret)
    again = exchange(stand, secret)
    assert first.status == again.status == 201
    assert again.json()["token"] != first.json()["token"], "the repeat is a new random token, not the same one"
    old, new = first.json()["runner_token"], again.json()["runner_token"]
    assert old["token_id"] != new["token_id"] and old["token_prefix"] != new["token_prefix"]
    assert old["token_prefix"][4:11] == new["token_prefix"][4:11], "the instance tag is what the repeat is judged by"
    assert agent_call(stand, first.json()["token"], "/runner/tasks/claim", {"wait_seconds": 0}).status == 401
    assert agent_call(stand, again.json()["token"], "/runner/tasks/claim", {"wait_seconds": 0}).status == 204
    stored = session.execute(text(
        "SELECT runner_token_id, redeemed_at IS NOT NULL FROM executor_enrollment WHERE connection_id = :c"),
        {"c": connection_id}).one()
    assert stored[0] == new["token_id"] and stored[1] is True, "runner_token_id follows the latest token"
    revoked = session.execute(text(
        "SELECT revoked_at IS NOT NULL, revoked_by FROM executor_runner_token WHERE token_id = :id"),
        {"id": old["token_id"]}).one()
    assert revoked[0] is True and revoked[1] == driver.TEST_SUBJECT.user_uid
    assert audit_mentions(session, first.json()["token"][4:]) == 0 == audit_mentions(
        session, again.json()["token"][4:])
    kinds = [row[0] for row in session.execute(text(
        "SELECT event_type FROM audit_event WHERE payload ->> 'connection_id' = :c ORDER BY audit_event_id"),
        {"c": connection_id}).all()]
    assert kinds.count("executor.enrollment_redeemed") == 2 and "executor.runner_token_revoked" in kinds
    other = exchange(stand, secret, "agent-instance-0002")
    assert other.status == 409 and other.json()["details"] == {"conflict_reason": "enrollment_redeemed"}
    assert secret not in other.body.decode()
    assert agent_call(stand, again.json()["token"], "/runner/tasks/claim", {"wait_seconds": 0}).status == 204, (
        "a stranger's refused attempt revokes nothing")


def test_a_repeat_after_the_token_was_revoked_is_refused(session, stand) -> None:
    connection_id = make_connection(stand)
    secret = issue(stand, connection_id).json()["secret"]
    token = exchange(stand, secret).json()
    revoked = admin_call(stand, "POST", f"/executor-connections/{connection_id}/runner-tokens/"
                                        f"{token['runner_token']['token_id']}/revoke")
    assert revoked.status == 200
    again = exchange(stand, secret)
    assert again.status == 409 and again.json()["details"] == {"conflict_reason": "enrollment_redeemed"}


def _redeemed_grant(session: Session, connection_id: str, secret: str, *, minutes_to_expiry: int) -> None:
    """A grant already exchanged by ``INSTANCE``, with the runner token that exchange minted, whose window
    ends ``minutes_to_expiry`` from now (negative: it ended). Written directly because a grant's dates are
    frozen by a trigger, so the only way to see the window pass is to start from one that has."""
    from auditmanager.executors.enrollment import exchange_key, instance_tag, mint_runner_token
    from auditmanager.shared.identity import ExecutorEnrollmentId, ExecutorRunnerTokenId

    minted = mint_runner_token(instance_tag(exchange_key(secret), INSTANCE), set())
    assert minted is not None
    value, prefix = minted
    token_id = str(ExecutorRunnerTokenId.new())
    session.execute(text(
        "INSERT INTO executor_runner_token (token_id, connection_id, token_prefix, token_hash, created_by, "
        "expires_at) VALUES (:id, :c, :prefix, :hash, :actor, clock_timestamp() + interval '30 days')"
    ), {"id": token_id, "c": connection_id, "prefix": prefix,
        "hash": hashlib.sha256(value.encode()).digest(), "actor": driver.TEST_SUBJECT.user_uid})
    session.execute(text(
        "INSERT INTO executor_enrollment (enrollment_id, connection_id, secret_prefix, secret_hash, "
        "created_at, created_by, expires_at, redeemed_at, runner_token_id) VALUES (:id, :c, :prefix, :hash, "
        "clock_timestamp() - interval '30 minutes', :actor, "
        "clock_timestamp() + make_interval(mins => :ahead), clock_timestamp() - interval '29 minutes', :token)"
    ), {"id": str(ExecutorEnrollmentId.new()), "c": connection_id, "prefix": secret[:12],
        "hash": hashlib.sha256(secret.encode()).digest(), "actor": driver.TEST_SUBJECT.user_uid,
        "ahead": minutes_to_expiry, "token": token_id})


def test_the_window_of_a_repeat_is_the_grants_own_fifteen_minutes(session, stand) -> None:
    inside_connection, past_connection = make_connection(stand), make_connection(stand)
    inside_secret, past_secret = "ame_insidewn_" + "I" * 43, "ame_pastwndw_" + "P" * 43
    _redeemed_grant(session, inside_connection, inside_secret, minutes_to_expiry=5)
    _redeemed_grant(session, past_connection, past_secret, minutes_to_expiry=-5)
    inside = exchange(stand, inside_secret)
    assert inside.status == 201, "inside the window the same instance is given a fresh token"
    assert inside.json()["runner_token"]["connection_id"] == inside_connection
    past = exchange(stand, past_secret)
    assert past.status == 409 and past.json()["details"] == {"conflict_reason": "enrollment_redeemed"}
    assert exchange(stand, inside_secret, "agent-instance-0002").status == 409


def test_an_expired_grant_is_a_401_indistinguishable_from_a_wrong_secret(session, stand) -> None:
    from auditmanager.shared.identity import ExecutorEnrollmentId

    connection_id = make_connection(stand)
    secret = "ame_expired1_" + "E" * 43
    session.execute(text(
        "INSERT INTO executor_enrollment (enrollment_id, connection_id, secret_prefix, secret_hash, "
        "created_at, created_by, expires_at) VALUES (:id, :c, :prefix, :hash, "
        "clock_timestamp() - interval '20 minutes', :actor, clock_timestamp() - interval '5 minutes')"
    ), {"id": str(ExecutorEnrollmentId.new()), "c": connection_id, "prefix": secret[:12],
        "hash": hashlib.sha256(secret.encode()).digest(), "actor": driver.TEST_SUBJECT.user_uid})
    expired = exchange(stand, secret)
    wrong = exchange(stand, "ame_expired1_" + "W" * 43)
    assert expired.status == wrong.status == 401
    assert expired.json()["error_code"] == wrong.json()["error_code"] == "authentication_required"
    assert expired.json()["message"] == wrong.json()["message"]
    assert session.execute(text("SELECT count(*) FROM executor_runner_token WHERE connection_id = :c"),
                           {"c": connection_id}).scalar_one() == 0


def test_redeeming_a_grant_past_its_expiry_is_a_clean_refusal_and_a_redemption_stays_inside_the_window(
    session, stand,
) -> None:
    """``mark_redeemed`` decides the window and stamps the redemption with one reading of the clock, so a
    late redemption is ``False`` (the caller's 401) and never ``ck_executor_enrollment_redeemed_in_window``
    (a 500). An already-expired grant is the deterministic face of that race."""
    from auditmanager.executors.enrollment_repository import EnrollmentRepository
    from auditmanager.shared.identity import ExecutorEnrollmentId

    connection_id = make_connection(stand)
    grants = EnrollmentRepository()
    late = str(ExecutorEnrollmentId.new())
    session.execute(text(
        "INSERT INTO executor_enrollment (enrollment_id, connection_id, secret_prefix, secret_hash, "
        "created_at, created_by, expires_at) VALUES (:id, :c, 'ame_latelate', :hash, "
        "clock_timestamp() - interval '20 minutes', :actor, clock_timestamp() - interval '1 second')"
    ), {"id": late, "c": connection_id, "hash": hashlib.sha256(b"late").digest(),
        "actor": driver.TEST_SUBJECT.user_uid})
    assert grants.mark_redeemed(session, late, "ern_" + "0" * 26) is False
    row = session.execute(text(
        "SELECT redeemed_at, runner_token_id FROM executor_enrollment WHERE enrollment_id = :id"),
        {"id": late}).one()
    assert tuple(row) == (None, None), "nothing changed"

    issued = issue(stand, connection_id).json()
    assert exchange(stand, issued["secret"]).status == 201
    redeemed = session.execute(text(
        "SELECT redeemed_at, expires_at, runner_token_id FROM executor_enrollment WHERE enrollment_id = :id"),
        {"id": issued["enrollment"]["enrollment_id"]}).one()
    assert redeemed[2] is not None and redeemed[0] <= redeemed[1]


def test_a_new_grant_revokes_the_previous_one_and_its_secret_stops_working(session, stand) -> None:
    connection_id = make_connection(stand)
    first = issue(stand, connection_id).json()
    second = issue(stand, connection_id).json()
    assert exchange(stand, first["secret"]).status == 401
    states = {item["enrollment_id"]: item["state"] for item in read_connection(stand, connection_id)["enrollments"]}
    assert states == {first["enrollment"]["enrollment_id"]: "revoked",
                      second["enrollment"]["enrollment_id"]: "pending"}
    assert exchange(stand, second["secret"]).status == 201
    pending = session.execute(text(
        "SELECT count(*) FROM executor_enrollment WHERE connection_id = :c AND redeemed_at IS NULL "
        "AND revoked_at IS NULL"), {"c": connection_id}).scalar_one()
    assert pending == 0


def test_a_grant_is_bound_to_a_pull_connection_with_a_revision_that_is_not_archived(session, stand) -> None:
    bare = admin_call(stand, "POST", "/executor-connections", {"kind": "pull", "display_name": "Bare"}).json()
    refused = issue(stand, bare["connection_id"])
    assert refused.status == 409 and refused.json()["details"] == {"conflict_reason": "no_revision"}
    http = admin_call(stand, "POST", "/executor-connections", {"kind": "http_api", "display_name": "API"}).json()
    kind = issue(stand, http["connection_id"])
    assert kind.status == 422 and kind.json()["details"] == {"field": "kind", "constraint": "kind_not_pull"}
    assert issue(stand, "exc_01M2545JSD15ETSNNV904X99ZZ").status == 404
    connection_id = make_connection(stand)
    assert admin_call(stand, "POST", f"/executor-connections/{connection_id}/archive").status == 200
    archived = issue(stand, connection_id)
    assert archived.status == 409 and archived.json()["details"] == {"conflict_reason": "connection_archived"}


def test_moving_an_agent_is_allowed_and_journaled(session, stand) -> None:
    connection_id = make_connection(stand)
    token = exchange(stand, issue(stand, connection_id).json()["secret"]).json()["token"]
    assert agent_call(stand, token, "/runner/tasks/claim", {"wait_seconds": 0}).status == 204
    moved = issue(stand, connection_id)
    assert moved.status == 201, "a connection with an online agent takes another grant"
    events = session.execute(text(
        "SELECT event_type, payload FROM audit_event WHERE aggregate_id = :c "
        "AND event_type = 'executor.agent_move_requested'"), {"c": connection_id}).all()
    assert len(events) == 1 and events[0][1]["connection_id"] == connection_id
    new_token = exchange(stand, moved.json()["secret"], "agent-instance-0002").json()["token"]
    assert new_token != token
    assert agent_call(stand, new_token, "/runner/tasks/claim", {"wait_seconds": 0}).status == 204
    old_id = read_connection(stand, connection_id)["runner_tokens"][-1]["token_id"]
    assert admin_call(stand, "POST", f"/executor-connections/{connection_id}/runner-tokens/{old_id}/revoke").status == 200
    assert agent_call(stand, token, "/runner/tasks/claim", {"wait_seconds": 0}).status == 401


def test_the_health_report_reaches_the_connection_detail_and_nothing_else_is_stored(session, stand) -> None:
    connection_id = make_connection(stand)
    token = exchange(stand, issue(stand, connection_id).json()["secret"]).json()["token"]
    before = read_connection(stand, connection_id)["runner_tokens"][0]
    assert "agent_version" not in before and "online" not in before, "a token that has not reported shows none"
    noisy = {**HEALTH, "clis": [{**HEALTH["clis"][0], "account": "a@b.c"}]}
    assert agent_call(stand, token, "/runner/health", noisy).status == 422
    assert agent_call(stand, token, "/runner/tasks/claim", {"wait_seconds": 0}).status == 204
    reported = agent_call(stand, token, "/runner/health", HEALTH)
    assert reported.status == 200 and "recorded_at" in reported.json()
    shown = read_connection(stand, connection_id)["runner_tokens"][0]
    assert shown["agent_version"] == "0.9.0" and shown["concurrency"] == 1
    assert shown["execution_profile"] == "command" and shown["features"] == ["images"]
    assert shown["online"] is True and shown["health_reported_at"]
    assert {(item["cli"], item["installed"], item["auth_state"]) for item in shown["clis"]} == {
        ("claude", True, "valid"), ("codex", False, "unknown")}
    row = session.execute(text(
        "SELECT cli_health::text, declared_features::text FROM executor_runner_token WHERE token_id = :id"),
        {"id": shown["token_id"]}).one()
    assert "a@b.c" not in row[0] + row[1] and "credentials" not in row[0] + row[1]
    assert audit_mentions(session, "claude") == 0, "telemetry is not journaled"


def test_a_token_that_has_not_been_seen_lately_is_not_online(session, stand) -> None:
    connection_id = make_connection(stand)
    token = exchange(stand, issue(stand, connection_id).json()["secret"]).json()
    agent_call(stand, token["token"], "/runner/health", HEALTH)
    session.execute(text(
        "UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - interval '10 minutes' "
        "WHERE token_id = :id"), {"id": token["runner_token"]["token_id"]})
    assert read_connection(stand, connection_id)["runner_tokens"][0]["online"] is False


def test_the_integration_mark_is_set_cleared_journaled_and_implies_nothing_else(session, stand) -> None:
    connection_id = make_connection(stand)
    path = f"/executor-connections/{connection_id}/integration-authorisation"
    assert "integration_authorisation" not in read_connection(stand, connection_id)["connection"]
    on = admin_call(stand, "POST", path, {"authorised": True})
    assert on.status == 200 and on.json()["integration_authorisation"]["authorised_by"]
    assert read_connection(stand, connection_id)["connection"]["integration_authorisation"]
    listed = dispatch(stand, Request.build("GET", "/executor-connections")).json()["items"]
    assert [bool(item.get("integration_authorisation")) for item in listed
            if item["connection_id"] == connection_id] == [True], "the list shows the mark too"
    assert admin_call(stand, "POST", path, {"authorised": True}).status == 200
    off = admin_call(stand, "POST", path, {"authorised": False})
    assert off.status == 200 and "integration_authorisation" not in off.json()
    kinds = [row[0] for row in session.execute(text(
        "SELECT event_type FROM audit_event WHERE aggregate_id = :c AND event_type LIKE "
        "'executor.integration_%' ORDER BY audit_event_id"), {"c": connection_id}).all()]
    assert sorted(kinds) == ["executor.integration_authorisation_cleared", "executor.integration_authorised"]
    http = admin_call(stand, "POST", "/executor-connections", {"kind": "http_api", "display_name": "API"}).json()
    refused = admin_call(stand, "POST", f"/executor-connections/{http['connection_id']}/integration-authorisation",
                         {"authorised": True})
    assert refused.status == 422 and refused.json()["details"] == {"field": "kind", "constraint": "kind_not_pull"}


def test_an_install_session_seals_its_key_stays_out_of_the_connections_secrets_and_waits_for_the_worker(
    session, stand, rings,
) -> None:
    from auditmanager.executors.public import install_destination, open_secret

    connection_id = make_connection(stand)
    base = f"/executor-connections/{connection_id}"
    created = admin_call(stand, "POST", f"{base}/agent-installs", {
        "access": "generated_key", "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu"})
    assert created.status == 201, created.body
    install = created.json()
    assert install["state"] == "requested" and install["public_key"].startswith("ssh-ed25519 ")
    assert install["authorized_keys_line"].endswith(f"auditmanager-install:{install['install_id']}")
    assert "BEGIN" not in created.body.decode() and "private_key" not in install

    row = session.execute(text(
        "SELECT s.secret_id, s.purpose, s.replaced_at, s.public_material FROM executor_agent_install i "
        "JOIN executor_secret s ON s.secret_id = i.key_secret_id WHERE i.install_id = :id"),
        {"id": install["install_id"]}).one()
    assert row[1] == "agent_install_key" and row[2] is None and row[3] == install["public_key"], (
        "the key is the connection's current agent_install_key, as any sealed secret is")
    opened = open_secret(session, rings.private, secret_id=row[0], destination=install_destination(
        ssh_host="agent-host.example", ssh_port=22, ssh_user="ubuntu"))
    assert opened.startswith("-----BEGIN OPENSSH PRIVATE KEY-----")
    assert read_connection(stand, connection_id)["connection"]["secrets"] == [], "the key is not the connection's"
    listed = dispatch(stand, Request.build("GET", "/executor-connections")).json()["items"]
    assert [item["secrets"] for item in listed if item["connection_id"] == connection_id] == [[]]

    second = admin_call(stand, "POST", f"{base}/agent-installs", {
        "access": "generated_key", "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu"})
    assert second.status == 409 and second.json()["details"] == {"conflict_reason": "install_in_progress"}

    fingerprint = "SHA256:" + "A" * 43
    early = admin_call(stand, "POST", f"{base}/agent-installs/{install['install_id']}/confirm-host-key",
                       {"host_key_fingerprint": fingerprint})
    assert early.status == 409 and early.json()["details"] == {"conflict_reason": "install_not_awaiting_host_key"}
    assert dispatch(stand, Request.build("GET", f"{base}/agent-installs/{install['install_id']}")).json()["state"] == "requested"


def test_a_new_install_session_replaces_the_previous_sessions_key(session, stand) -> None:
    connection_id = make_connection(stand)
    base = f"/executor-connections/{connection_id}/agent-installs"
    body = {"access": "generated_key", "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu"}
    first = admin_call(stand, "POST", base, body).json()
    session.execute(text(
        "UPDATE executor_agent_install SET state = 'failed', failure_reason = 'host_unreachable', "
        "finished_at = clock_timestamp(), updated_at = clock_timestamp() WHERE install_id = :id"),
        {"id": first["install_id"]})
    second = admin_call(stand, "POST", base, body)
    assert second.status == 201, second.body
    keys = dict(session.execute(text(
        "SELECT i.install_id, s.replaced_at IS NULL FROM executor_agent_install i "
        "JOIN executor_secret s ON s.secret_id = i.key_secret_id WHERE i.connection_id = :c"),
        {"c": connection_id}).all())
    assert keys == {first["install_id"]: False, second.json()["install_id"]: True}
    assert second.json()["public_key"] != first["public_key"]


INSTALL_BODY = {"access": "generated_key", "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu"}


def age_install(session: Session, install_id: str, seconds: int) -> None:
    """Make a session ``seconds`` older. ``created_at`` is frozen by a trigger, so the guard is lifted for this
    one statement (inside the test's own transaction, which is rolled back)."""
    guard = "ALTER TABLE executor_agent_install {} TRIGGER trg_executor_agent_install_frozen_guard"
    session.execute(text(guard.format("DISABLE")))
    session.execute(text(
        "UPDATE executor_agent_install SET created_at = created_at - make_interval(secs => :s) "
        "WHERE install_id = :id"), {"s": seconds, "id": install_id})
    session.execute(text(guard.format("ENABLE")))


def current_install_keys(session: Session, connection_id: str) -> int:
    return int(session.execute(text(
        "SELECT count(*) FROM executor_secret WHERE connection_id = :c AND purpose = 'agent_install_key' "
        "AND replaced_at IS NULL"), {"c": connection_id}).scalar_one())


def expired_events(session: Session, install_id: str) -> list[dict[str, Any]]:
    return [row[0] for row in session.execute(text(
        "SELECT payload FROM audit_event WHERE aggregate_id = :id "
        "AND event_type = 'executor.agent_install_expired' ORDER BY audit_event_id"), {"id": install_id}).all()]


def test_an_abandoned_session_ends_when_it_is_read_after_its_time_and_frees_the_connection(session, stand) -> None:
    """With no worker (`EXEC2-ENROLL-SSH-01`) nothing advances a session: it ends by its age, on a read."""
    from auditmanager.executors.agent_install import INSTALL_SESSION_SECONDS

    connection_id = make_connection(stand)
    base = f"/executor-connections/{connection_id}/agent-installs"
    install = admin_call(stand, "POST", base, INSTALL_BODY).json()
    install_id = install["install_id"]
    assert current_install_keys(session, connection_id) == 1

    age_install(session, install_id, INSTALL_SESSION_SECONDS - 10)
    early = dispatch(stand, Request.build("GET", f"{base}/{install_id}")).json()
    assert early["state"] == "requested" and "failure_reason" not in early and expired_events(session, install_id) == []
    assert admin_call(stand, "POST", base, INSTALL_BODY).status == 409, "still in progress"

    age_install(session, install_id, 20)
    ended = dispatch(stand, Request.build("GET", f"{base}/{install_id}"))
    assert ended.status == 200, ended.body
    body = ended.json()
    assert body["state"] == "failed" and body["failure_reason"] == "no_worker"
    assert body["finished_at"] and body["key_removed_at"], "finished, and the key is gone"
    assert "public_key" not in body and "authorized_keys_line" not in body, "nothing of the key is shown any more"
    row = session.execute(text(
        "SELECT key_secret_id, key_removed_at IS NOT NULL, finished_at IS NOT NULL, state, failure_reason "
        "FROM executor_agent_install WHERE install_id = :id"), {"id": install_id}).one()
    assert tuple(row) == (None, True, True, "failed", "no_worker")
    assert current_install_keys(session, connection_id) == 0, "no current agent_install_key remains"
    replaced = session.execute(text(
        "SELECT count(*) FROM executor_secret WHERE connection_id = :c AND purpose = 'agent_install_key' "
        "AND replaced_at IS NOT NULL"), {"c": connection_id}).scalar_one()
    assert replaced == 1

    (event,) = expired_events(session, install_id)
    assert set(event) == {"connection_id", "purpose", "from_state", "to_state", "reason", "secret_id"}
    assert (event["connection_id"], event["purpose"], event["from_state"], event["to_state"], event["reason"]) == (
        connection_id, "agent_install_key", "requested", "failed", "no_worker")
    assert "agent-host.example" not in json.dumps(event) and "ubuntu" not in json.dumps(event)

    again = dispatch(stand, Request.build("GET", f"{base}/{install_id}")).json()
    assert again == body and len(expired_events(session, install_id)) == 1, "idempotent: nothing more is written"
    fresh = admin_call(stand, "POST", base, INSTALL_BODY)
    assert fresh.status == 201 and fresh.json()["install_id"] != install_id
    assert current_install_keys(session, connection_id) == 1


@pytest.mark.parametrize("state", ["scanning", "awaiting_host_key", "installing"])
def test_a_session_somebody_took_ends_as_timed_out_when_the_next_create_finds_it_overdue(
    session, stand, state: str,
) -> None:
    connection_id = make_connection(stand)
    base = f"/executor-connections/{connection_id}/agent-installs"
    pasted = Ed25519PrivateKey.generate().private_bytes(
        Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption()).decode("ascii")
    taken = admin_call(stand, "POST", base, {**INSTALL_BODY, "access": "pasted_key", "private_key": pasted})
    assert taken.status == 201, taken.body
    install_id = taken.json()["install_id"]
    line = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode()
    steps = {
        "scanning": "state = 'scanning'",
        "awaiting_host_key": "state = 'awaiting_host_key', observed_host_key = :key",
        "installing": (
            "state = 'installing', observed_host_key = :key, confirmed_host_key_fingerprint = :fingerprint, "
            "host_key_confirmed_at = clock_timestamp(), host_key_confirmed_by = created_by"),
    }
    statement = (f"UPDATE executor_agent_install SET {steps[state]}, updated_at = clock_timestamp() "
                 "WHERE install_id = :id")
    values = {"id": install_id, "key": line, "fingerprint": "SHA256:" + "A" * 43}
    session.execute(text(statement), {name: value for name, value in values.items() if f":{name}" in statement})
    age_install(session, install_id, 1801)

    fresh = admin_call(stand, "POST", base, {**INSTALL_BODY, "ssh_host": "other-host.example"})
    assert fresh.status == 201, fresh.body
    row = session.execute(text(
        "SELECT state, failure_reason, key_secret_id, key_removed_at IS NOT NULL, finished_at IS NOT NULL, "
        "observed_host_key IS NOT NULL FROM executor_agent_install WHERE install_id = :id"),
        {"id": install_id}).one()
    assert tuple(row) == ("failed", "timed_out", None, True, True, state != "scanning"), (
        "ended, the key gone, and what the worker had recorded is left as it was")
    (event,) = expired_events(session, install_id)
    assert event["from_state"] == state and event["reason"] == "timed_out"
    assert current_install_keys(session, connection_id) == 1, "the new session's key is the only current one"
    assert "BEGIN" not in json.dumps(event) and pasted.splitlines()[1] not in json.dumps(event)


def test_ending_an_overdue_session_does_not_touch_another_connections_session(session, stand) -> None:
    mine, theirs = make_connection(stand), make_connection(stand)
    first = admin_call(stand, "POST", f"/executor-connections/{mine}/agent-installs", INSTALL_BODY).json()
    other = admin_call(stand, "POST", f"/executor-connections/{theirs}/agent-installs", INSTALL_BODY).json()
    for install in (first, other):
        age_install(session, install["install_id"], 3600)
    assert admin_call(stand, "POST", f"/executor-connections/{mine}/agent-installs", INSTALL_BODY).status == 201
    states = dict(session.execute(text(
        "SELECT install_id, state FROM executor_agent_install WHERE install_id = ANY(:ids)"),
        {"ids": [first["install_id"], other["install_id"]]}).all())
    assert states == {first["install_id"]: "failed", other["install_id"]: "requested"}
    assert current_install_keys(session, theirs) == 1


def test_the_host_key_is_confirmed_by_value_against_the_one_the_worker_observed(session, stand) -> None:
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    connection_id = make_connection(stand)
    base = f"/executor-connections/{connection_id}"
    install = admin_call(stand, "POST", f"{base}/agent-installs", {
        "access": "generated_key", "ssh_host": "agent-host.example", "ssh_port": 22, "ssh_user": "ubuntu"}).json()
    line = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode()
    observed = "SHA256:" + base64.b64encode(hashlib.sha256(base64.b64decode(line.split()[1])).digest()).decode().rstrip("=")
    session.execute(text(
        "UPDATE executor_agent_install SET state = 'awaiting_host_key', observed_host_key = :key, "
        "updated_at = clock_timestamp() WHERE install_id = :id"), {"id": install["install_id"], "key": line})
    shown = dispatch(stand, Request.build("GET", f"{base}/agent-installs/{install['install_id']}")).json()
    assert shown["state"] == "awaiting_host_key" and shown["observed_host_key_fingerprint"] == observed
    confirm = f"{base}/agent-installs/{install['install_id']}/confirm-host-key"

    wrong = admin_call(stand, "POST", confirm, {"host_key_fingerprint": "SHA256:" + "B" * 43})
    assert wrong.status == 409 and wrong.json()["details"] == {"conflict_reason": "host_key_changed"}
    done = admin_call(stand, "POST", confirm, {"host_key_fingerprint": observed})
    assert done.status == 200 and done.json()["state"] == "installing"
    assert done.json()["host_key_confirmed_by"] and done.json()["host_key_confirmed_at"]
    again = admin_call(stand, "POST", confirm, {"host_key_fingerprint": observed})
    assert again.status == 200 and again.json()["state"] == "installing"
    other = admin_call(stand, "POST", confirm, {"host_key_fingerprint": "SHA256:" + "B" * 43})
    assert other.status == 409 and other.json()["details"] == {"conflict_reason": "host_key_changed"}
    events = session.execute(text(
        "SELECT count(*) FROM audit_event WHERE aggregate_id = :id AND event_type = "
        "'executor.agent_install_host_key_confirmed'"), {"id": install["install_id"]}).scalar_one()
    assert events == 1


def test_the_package_route_serves_the_bytes_the_command_verifies(stand, package_content: bytes) -> None:
    connection_id = make_connection(stand)
    issued = issue(stand, connection_id).json()
    answer = dispatch(stand, Request.build("GET", f"/runner/agent-package/{issued['package_version']}"),
                      credential=None)
    assert answer.status == 200 and answer.body == package_content
    assert hashlib.sha256(answer.body).hexdigest() == issued["package_sha256"]
