"""`EXEC-PULL-01`: the shipped runner client (`tools/executor-runner/runner_client.py`) against
the real application over real HTTP.

The client is the binding wire spec's other half (`RUNNER_API.md`); its own tests run against a
fake server. This runs it against ``create_asgi_app`` served by uvicorn on a loopback port (the
proxy's ``/api/v1`` prefix mounted in front), with the seam, the envelope and the middlewares
real and the runner port a stand-in, so what is proved is that every status, body shape,
timestamp and error envelope the server writes is one the client reads -- including the ``Date``
header the client derives claim time from. No database, no container, no model.
"""

from __future__ import annotations

import importlib.util
import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI

from auditmanager.api.routers.runner import ModelNotTheTasks
from auditmanager.api.schemas import models
from auditmanager.api.security import RunnerIdentity
from tests.integration.executors.conftest import driver
from tests.integration.executors.test_runner_seam import TOKEN, StubRunner

_PATH = Path(__file__).resolve().parents[3] / "tools" / "executor-runner" / "runner_client.py"
_NAME = "am_runner_client_under_test"
if _NAME in sys.modules:
    client_module = sys.modules[_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_NAME, _PATH)
    assert _spec is not None and _spec.loader is not None
    client_module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = client_module
    _spec.loader.exec_module(client_module)

TASK = "ext_01M2545JSD15ETSNNV904X991K"


class DeliveringRunner(StubRunner):
    """The stand-in port, now with a task to hand out and the refusals a runner meets."""

    def __init__(self) -> None:
        super().__init__()
        self.waiting = True
        self.held = True

    def claim_task(self, *, runner, wait_seconds):
        self.calls.append(("claim", runner, wait_seconds))
        if not self.waiting:
            return None
        self.waiting = False
        now = time.time()
        return models.ClaimedExecutorTask.model_validate({
            "task_id": TASK,
            "claim_expires_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now + 120)) + "Z",
            "deadline_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now + 600)) + ".250000+00:00",
            "model": "claude-opus-5", "system": "SYSTEM", "user_text": "USER",
            "output_schema": {"type": "object"},
        })

    def extend_claim(self, *, runner, task_id):
        from auditmanager.shared.errors import DomainError, ErrorCode

        if not self.held:
            raise DomainError(ErrorCode.CONFLICT, message="the claim on the task is lost",
                              conflict_reason="claim_lost")
        return super().extend_claim(runner=runner, task_id=task_id)


@pytest.fixture
def server():
    inner_port = DeliveringRunner()
    from auditmanager.api.routers import build_router

    router = build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})),
        accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(),
        runner=inner_port,  # type: ignore[arg-type]
    )
    surface = driver.Surface(router)
    outer = FastAPI()
    outer.mount("/api/v1", surface.app)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = uvicorn.Config(outer, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    running = uvicorn.Server(config)
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not running.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert running.started, "the test server did not start"
    try:
        yield inner_port, f"http://127.0.0.1:{port}"
    finally:
        running.should_exit = True
        thread.join(timeout=10)


def test_the_client_reads_every_shape_the_server_writes(server) -> None:
    port, origin = server
    client = client_module.RunnerClient(origin, TOKEN)
    task = client.claim(0)
    assert task is not None and task["task_id"] == TASK and task["model"] == "claude-opus-5"
    assert task["output_schema"] == {"type": "object"}
    # The client derives claim time from the server's clock: the server sent a Date header.
    assert abs(client.clock_skew) < 5 and client.seconds_until(task["claim_expires_at"]) > 100
    assert client.seconds_until(task["deadline_at"]) > 550
    assert client.claim(0) is None, "204 with an empty body is None"
    extended = client.extend(TASK)
    assert "claim_expires_at" in extended
    assert client.answer(TASK, "{}", "claude-opus-5", 10, 5) == {"task_id": TASK, "state": "answered"}
    assert client.fail(TASK, "model_mismatch: x") == {"task_id": TASK, "state": "failed"}
    assert [call[0] for call in port.calls] == ["claim", "claim", "extend", "answer", "fail"]


def test_the_clients_error_classes_follow_the_servers_statuses(server) -> None:
    port, origin = server
    wrong = client_module.RunnerClient(origin, "amr_zzzzzzzz_" + "B" * 43)
    with pytest.raises(client_module.RunnerAuthError) as auth:
        wrong.claim(0)
    assert auth.value.status == 401 and auth.value.error_code == "authentication_required"

    client = client_module.RunnerClient(origin, TOKEN)
    port.held = False
    with pytest.raises(client_module.RunnerConflict) as lost:
        client.extend(TASK)
    assert lost.value.status == 409 and lost.value.error_code == "conflict"
    with pytest.raises(client_module.RunnerNotFound):
        client.extend("ext_not-a-real-shape-but-valid-chars")
    with pytest.raises(client_module.RunnerRejected) as mismatch:
        client.answer(TASK, "{}", "wrong-model")
    assert mismatch.value.status == 422 and mismatch.value.error_code == "model_identity_mismatch"


def test_the_token_never_comes_back_in_anything_the_client_raises(server) -> None:
    port, origin = server
    wrong = client_module.RunnerClient(origin, "amr_zzzzzzzz_" + "C" * 43)
    with pytest.raises(client_module.RunnerError) as raised:
        wrong.claim(0)
    assert "C" * 43 not in str(raised.value) and "C" * 43 not in repr(raised.value)
