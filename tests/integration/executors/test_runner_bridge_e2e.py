"""`EXEC-PULL-01`: one run's model call, end to end, through the shipped stdio bridge.

A test client speaks MCP JSON-RPC to ``tools/executor-runner/mcp_bridge.py`` (a child process),
which calls the real application over HTTP (uvicorn on a loopback port, the proxy's ``/api/v1``
prefix mounted in front, the real seam and routes over the real runner adapter and real rows),
while the worker's :class:`~auditmanager.executors.pull.PullAdapter` waits for the answer in its
own thread. Nothing calls a model: the "model" is this test, answering as a Claude Code session
would. All database access shares one rolled-back session, serialised by a lock, so the threads
cannot interleave inside a statement.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import ProxyDispatchError
from auditmanager.executors.public import PullAdapter, current_revision
from auditmanager.jobs.lease import AttemptContext
from tests.integration.executors.conftest import ADMIN, driver
from tests.integration.executors.test_runner_channel import (
    GOOD, MODEL, PULL_SETTINGS, REQUEST, SCHEMA, admin_call, live_attempt, make_connection,
)

_SUPPORT = Path(__file__).resolve().parents[2] / "unit" / "executor_runner" / "_support.py"
_NAME = "am_runner_bridge_support"
if _NAME in sys.modules:
    support = sys.modules[_NAME]
else:
    import importlib.util

    _spec = importlib.util.spec_from_file_location(_NAME, _SUPPORT)
    assert _spec is not None and _spec.loader is not None
    support = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = support
    _spec.loader.exec_module(support)


class Serialised:
    """The one session, handed to one thread at a time for the length of a ``with`` block."""

    def __init__(self, session: Session) -> None:
        self.session, self.lock = session, threading.RLock()

    @contextmanager
    def __call__(self):
        with self.lock:
            yield self.session


@pytest.fixture
def stand(session: Session, admin_account: str, rings):
    from auditmanager.api.routers import build_router
    from auditmanager.bootstrap.adapters import ExecutorAdapter
    from auditmanager.bootstrap.runner import RunnerAdapter

    sessions = Serialised(session)
    surface = driver.Surface(build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=frozenset({"admin"})),
        accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(),
        executors=ExecutorAdapter(sessions, ring=rings.public),  # type: ignore[arg-type]
        runner=RunnerAdapter(sessions),  # type: ignore[arg-type]
    ))
    outer = FastAPI()
    outer.mount("/api/v1", surface.app)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(outer, host="127.0.0.1", port=port,
                                           log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started
    try:
        yield surface, sessions, f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _worker(sessions: Serialised, connection_id: str, attempt: dict, outcome: dict) -> threading.Thread:
    def run() -> None:
        with sessions() as session:
            revision = current_revision(session, connection_id)
        assert revision is not None
        context = AttemptContext(run_id=attempt["run_id"], attempt_id=attempt["attempt_id"],
                                 started_monotonic=time.monotonic())
        adapter = PullAdapter(session_factory=sessions, revision=revision, context=context,
                              poll_seconds=0.1)
        try:
            outcome["response"] = adapter.complete(REQUEST)
        except ProxyDispatchError as error:
            outcome["error"] = error

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def test_a_session_through_the_bridge_answers_a_runs_model_call(stand, session) -> None:
    surface, sessions, origin = stand
    # Setup runs before any other thread touches the session; the requests it makes are served
    # on the test client's own thread, so the lock must not be held across them.
    connection_id = make_connection(surface)
    issued = admin_call(surface, "POST", f"/executor-connections/{connection_id}/runner-tokens", {})
    token = issued.json()["token"]
    attempt = live_attempt(session)
    outcome: dict = {}
    worker = _worker(sessions, connection_id, attempt, outcome)

    with support.McpSession(origin, token=token) as mcp:
        mcp.initialize()
        tools = mcp.request("tools/list")["result"]["tools"]
        assert {tool["name"] for tool in tools} == {"claim_task", "submit_answer", "report_failure"}
        claimed = mcp.payload(mcp.call("claim_task", {"wait_seconds": 20}, timeout=40))
        assert claimed["status"] == "task" and claimed["model"] == MODEL
        assert claimed["system"] == "SYSTEM-PROMPT" and claimed["user_text"] == "USER-TEXT"
        assert claimed["output_schema"] == SCHEMA
        # The session answers: a document that validates, declaring exactly the pinned model.
        accepted = mcp.payload(mcp.call("submit_answer", {
            "task_id": claimed["task_id"], "model": claimed["model"], "output_text": GOOD,
            "input_tokens": 120, "output_tokens": 30}))
        assert accepted["status"] == "accepted" and accepted["state"] == "answered"
        assert token not in mcp.stderr()

    worker.join(timeout=30)
    assert not worker.is_alive() and "error" not in outcome, outcome
    response = outcome["response"]
    assert response.output_text == GOOD and (response.input_tokens, response.output_tokens) == (120, 30)
    assert response.reported_cost_usd is None
    with sessions():
        row = dict(session.execute(text(
            "SELECT state, declared_model, claim_count, run_id FROM executor_task "
            "ORDER BY created_at DESC LIMIT 1")).mappings().one())
    assert row == {"state": "answered", "declared_model": MODEL, "claim_count": 1,
                   "run_id": attempt["run_id"]}


def test_a_session_that_declares_another_model_is_refused_and_can_fail_the_task(stand, session) -> None:
    surface, sessions, origin = stand
    connection_id = make_connection(surface)
    token = admin_call(surface, "POST",
                       f"/executor-connections/{connection_id}/runner-tokens", {}).json()["token"]
    attempt = live_attempt(session)
    outcome: dict = {}
    worker = _worker(sessions, connection_id, attempt, outcome)
    with support.McpSession(origin, token=token) as mcp:
        mcp.initialize()
        claimed = mcp.payload(mcp.call("claim_task", {"wait_seconds": 20}, timeout=40))
        refused = mcp.call("submit_answer", {"task_id": claimed["task_id"], "model": "claude-sonnet-5",
                                             "output_text": GOOD})
        assert refused.get("isError") is True
        failed = mcp.payload(mcp.call("report_failure", {
            "task_id": claimed["task_id"],
            "reason": "model_mismatch: running claude-sonnet-5, task pins claude-opus-5"}))
        assert failed["status"] == "failed"
    worker.join(timeout=30)
    error = outcome["error"]
    assert (error.dispatch_class, error.retry_safe) == ("outcome_unknown", False)
