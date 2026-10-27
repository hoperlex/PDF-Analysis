"""`EXEC-PULL-01`: the authorization seam and the runner routes, with a stand-in port.

No database: ``StubRunner`` is the ``RunnerPort`` and records what reached it. What is under
test is the edge -- a runner token is a principal of its own that reaches four operations and
nothing else, a user's credential reaches none of them, and the one status that is the runner
contract's rather than the catalog's (``422`` for ``model_identity_mismatch``) is what a caller
sees. The behaviour behind the port is ``test_runner_channel.py`` on real rows.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.api.routers import build_router
from auditmanager.api.routers.runner import ModelNotTheTasks
from auditmanager.api.schemas import models
from auditmanager.api.security import RUNNER_OPERATIONS, RunnerIdentity
from tests.integration.executors.conftest import driver

Request, dispatch = driver.Request, driver.dispatch
TOKEN = "amr_abcd1234_" + "A" * 43
TASK = "ext_01M2545JSD15ETSNNV904X991K"
BLOB = "blob_01M2545JSD15ETSNNV904X991K"
PNG = b"\x89PNG\r\n\x1a\nthe bytes the port returns"


class StubRunner:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.addresses: list[str | None] = []
        self.claimed_max_images: list[int | None] = []

    def authenticate_runner(self, presented: str, *, address: str | None):
        self.addresses.append(address)
        return RunnerIdentity("ern_T", "exc_C") if presented == TOKEN else None

    def claim_task(self, *, runner, wait_seconds, max_images=None):
        self.calls.append(("claim", runner, wait_seconds))
        self.claimed_max_images.append(max_images)
        return None

    def extend_claim(self, *, runner, task_id):
        self.calls.append(("extend", runner, task_id))
        return models.ExtendedExecutorTaskClaim.model_validate({"claim_expires_at": "2026-10-22T07:32:15Z"})

    def submit_answer(self, *, runner, task_id, body):
        self.calls.append(("answer", runner, task_id))
        if body.model == "wrong-model":
            raise ModelNotTheTasks
        return models.ExecutorTaskAck.model_validate({"task_id": task_id, "state": "answered"})

    def fail_task(self, *, runner, task_id, reason):
        self.calls.append(("fail", runner, task_id, reason))
        return models.ExecutorTaskAck.model_validate({"task_id": task_id, "state": "failed"})

    def issue_token(self, **_):  # pragma: no cover - not reached here
        raise AssertionError

    def revoke_token(self, **_):  # pragma: no cover - not reached here
        raise AssertionError

    def read_image(self, *, runner, task_id, blob_id):
        self.calls.append(("image", runner, task_id, blob_id))
        return PNG


@pytest.fixture
def stub(surface) -> StubRunner:
    """The stand-in the surface was built with (the router carries its runner port)."""
    return surface.router.runner_tokens


@pytest.fixture
def surface():
    return driver.Surface(build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})),
        accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(),
        runner=StubRunner(),  # type: ignore[arg-type]
    ))


def post(surface, path: str, body=None, *, token: str | None = TOKEN, **headers):
    sent = {"Content-Type": "application/json", **headers}
    if token is not None:
        sent["Authorization"] = f"Bearer {token}"
    return dispatch(surface, Request.build("POST", path, headers=sent,
                                           body=b"{}" if body is None else json.dumps(body).encode()),
                    credential=None)


PATHS = {
    "claimExecutorTask": "/runner/tasks/claim",
    "extendExecutorTaskClaim": f"/runner/tasks/{TASK}/extend",
    "submitExecutorTaskAnswer": f"/runner/tasks/{TASK}/answer",
    "failExecutorTask": f"/runner/tasks/{TASK}/fail",
}
#: The fifth runner operation (`EXEC-IMAGE-DELIVERY-01`) is a GET, so it is not in ``PATHS``,
#: which the POST-driven cases below iterate.
IMAGE_OPERATION = "getExecutorTaskImage"
IMAGE_PATH = f"/runner/tasks/{TASK}/images/{BLOB}"
BODIES = {"submitExecutorTaskAnswer": {"output_text": "{}", "model": "m"},
          "failExecutorTask": {"reason": "model_mismatch: x"}}


def test_the_runner_operations_are_exactly_the_four_posts_and_the_image_read_under_runner_tasks() -> None:
    assert set(PATHS) | {IMAGE_OPERATION} == RUNNER_OPERATIONS
    assert IMAGE_OPERATION not in PATHS


def test_a_runner_token_reaches_the_image_read_and_the_port_sees_its_identity(surface, stub) -> None:
    answer = dispatch(surface, Request.build(
        "GET", IMAGE_PATH, headers={"Authorization": f"Bearer {TOKEN}"}), credential=None)
    assert answer.status == 200 and answer.body == PNG
    assert answer.header("Content-Type") == "image/png" and answer.header("X-Correlation-Id")
    assert stub.calls == [("image", RunnerIdentity("ern_T", "exc_C"), TASK, BLOB)]


def test_a_wrong_token_no_token_and_a_users_credential_cannot_read_an_image(surface, stub) -> None:
    for headers in ({"Authorization": "Bearer amr_zzzzzzzz_" + "B" * 43},
                    {"Authorization": "Bearer garbage"}, {}):
        answer = dispatch(surface, Request.build("GET", IMAGE_PATH, headers=headers), credential=None)
        assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"
    # A user's credential (the suite's default one) is not a runner token.
    answer = dispatch(surface, Request.build("GET", IMAGE_PATH))
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"
    assert stub.calls == []


@pytest.mark.parametrize("operation", sorted(PATHS))
def test_a_runner_token_reaches_the_operation_and_the_port_sees_its_identity(
    surface, stub, operation: str,
) -> None:
    answer = post(surface, PATHS[operation], BODIES.get(operation))
    assert answer.status in (200, 204), answer.body
    assert answer.header("X-Correlation-Id")
    assert stub.calls and stub.calls[0][1] == RunnerIdentity("ern_T", "exc_C")


@pytest.mark.parametrize("operation", sorted(PATHS))
def test_a_wrong_token_and_no_token_are_authentication_required_and_reach_no_port(
    surface, stub, operation: str,
) -> None:
    for token in ("amr_zzzzzzzz_" + "B" * 43, "garbage", None):
        answer = post(surface, PATHS[operation], BODIES.get(operation), token=token)
        body = answer.json()
        assert answer.status == 401 and body["error_code"] == "authentication_required", token
        assert body["retryable"] is False and "details" not in body
    assert stub.calls == []


@pytest.mark.parametrize("operation", sorted(PATHS))
def test_a_users_credential_is_not_a_runner_token(surface, stub, operation: str) -> None:
    answer = dispatch(surface, Request.build(
        "POST", PATHS[operation], headers={"Content-Type": "application/json"},
        body=json.dumps(BODIES.get(operation, {})).encode()))
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required"
    assert stub.calls == []


@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/executor-connections"), ("GET", "/executor-routes"), ("GET", "/projects"),
    ("POST", "/executor-connections"), ("GET", "/me"),
])
def test_a_runner_token_is_refused_on_every_other_operation(surface, stub, method, path) -> None:
    answer = dispatch(surface, Request.build(
        method, path, headers={"Authorization": f"Bearer {TOKEN}", "Idempotency-Key": "k-1",
                               "Content-Type": "application/json"},
        body=b"{}" if method == "POST" else b""), credential=None)
    assert answer.status == 401 and answer.json()["error_code"] == "authentication_required", path


def test_the_claim_defaults_to_the_long_poll_and_refuses_a_wait_outside_the_range(surface, stub) -> None:
    assert post(surface, "/runner/tasks/claim", {}).status == 204
    assert post(surface, "/runner/tasks/claim", {"wait_seconds": 3}).status == 204
    assert [call[2] for call in stub.calls] == [25, 3]
    for bad in (26, -1, "x", 1.5):
        refused = post(surface, "/runner/tasks/claim", {"wait_seconds": bad})
        assert refused.status == 422 and refused.json()["error_code"] == "validation_failed", bad
    assert len(stub.calls) == 2
    assert post(surface, "/runner/tasks/claim", {"wait_seconds": 1, "extra": 1}).status == 422


def test_the_declared_max_images_reaches_the_port_and_an_absent_one_reaches_it_as_none(surface, stub) -> None:
    """`CMP-EXEC-IMAGES-01`: the router passes the claim's own value, and never invents one."""
    assert post(surface, "/runner/tasks/claim", {}).status == 204
    assert post(surface, "/runner/tasks/claim", {"wait_seconds": 0}).status == 204
    assert post(surface, "/runner/tasks/claim", {"wait_seconds": 0, "max_images": 1}).status == 204
    assert post(surface, "/runner/tasks/claim", {"max_images": 8}).status == 204
    assert stub.claimed_max_images == [None, None, 1, 8]
    before = len(stub.claimed_max_images)
    for bad in (0, 9):
        assert post(surface, "/runner/tasks/claim", {"max_images": bad}).status == 422
    assert len(stub.claimed_max_images) == before, "a refused claim reaches no port"


def test_an_empty_claim_answer_has_no_body(surface) -> None:
    answer = post(surface, "/runner/tasks/claim", {"wait_seconds": 0})
    assert answer.status == 204 and answer.body == b""


def test_a_malformed_task_identity_is_not_found_and_never_a_lookup(surface, stub) -> None:
    """The repository's own rule for a path identity that cannot exist: `not_found`."""
    refused = post(surface, "/runner/tasks/not-a-task/extend")
    assert refused.status == 404 and refused.json()["error_code"] == "not_found"
    assert stub.calls == []


def test_the_peer_address_is_what_the_proxy_set(surface, stub) -> None:
    post(surface, "/runner/tasks/claim", {"wait_seconds": 0}, **{"X-Real-IP": "203.0.113.7"})
    assert stub.addresses[-1] == "203.0.113.7"


def test_a_declared_model_that_is_not_the_tasks_is_422_with_the_mismatch_code(surface, stub) -> None:
    answer = post(surface, PATHS["submitExecutorTaskAnswer"], {"output_text": "{}", "model": "wrong-model"})
    body = answer.json()
    assert answer.status == 422 and body["error_code"] == "model_identity_mismatch"
    assert body["retryable"] is False and "wrong-model" not in answer.body.decode()
    assert answer.header("X-Correlation-Id")


def test_an_answer_body_is_closed_and_bounded(surface, stub) -> None:
    for body in ({"output_text": "{}"}, {"model": "m"}, {"output_text": "", "model": "m"},
                 {"output_text": "{}", "model": "m", "input_tokens": -1},
                 {"output_text": "{}", "model": "m", "surprise": 1},
                 {"output_text": "x" * 1_000_001, "model": "m"}):
        refused = post(surface, PATHS["submitExecutorTaskAnswer"], body)
        assert refused.status == 422, str(body)[:60]
    assert stub.calls == []
    for body in ({}, {"reason": ""}, {"reason": "x" * 513}):
        assert post(surface, PATHS["failExecutorTask"], body).status == 422
    assert post(surface, PATHS["failExecutorTask"], {"reason": "x" * 512}).status == 200


def test_the_token_is_in_no_response_header_or_body(surface) -> None:
    for operation in sorted(PATHS):
        for token in (TOKEN, "amr_zzzzzzzz_" + "B" * 43):
            answer = post(surface, PATHS[operation], BODIES.get(operation), token=token)
            assert token not in answer.body.decode() and token not in str(answer.headers)
