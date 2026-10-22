"""`EXEC-CANDIDATE-2` (`EXEC-AGENT-01` on the lane): the shipped ``agent.py`` answers a real run.

``tools/executor-runner/agent.py`` runs as a **subprocess**, with a stub local command, against the
real application over HTTP (uvicorn on a loopback port, the proxy's ``/api/v1`` prefix mounted in
front, the real seam, envelope, runner adapter and real rows). It never sees the database, the
object store or a shell on the stand: it calls the four runner operations with its token and
nothing else. A ``pull`` connection with client ``agent`` is probed by the worker's probe loop
(the agent answers the echo task), routed, and a real run's ``text_analysis`` call is answered by
the agent through the command.

Nothing calls a model: the "model" is a stub script. One rolled-back session is shared by the
server threads, the worker's adapter and the test, serialised by a lock; the agent process is
started only once the run's worker is waiting, so the test thread never touches the session while a
server thread does.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.analysis.text import ProviderConfig, ProviderMode
from auditmanager.bootstrap.providers import DatabaseProviders, UnboundAdapter
from auditmanager.executors import pull
from auditmanager.executors.public import current_revision
from auditmanager.executors.probe_runner import ProbeRunner
from auditmanager.executors.runtime import DestinationPolicy, KindRuntime
from auditmanager.runs import RunRepository, execute_run, start_audit_run
from tests.integration.executors.test_runner_bridge_e2e import Serialised, stand  # noqa: F401  (stand is a fixture)
from tests.integration.executors.test_runner_channel import admin_call, issue, make_connection

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)
engine = harness.engine
session = harness.session
blob_store = harness.blob_store
seeded = harness.seeded
new_key = harness.new_key

_NAME = "executor_runner_support"
_SUPPORT = Path(__file__).resolve().parents[2] / "unit" / "executor_runner" / "_support.py"
if _NAME in sys.modules:
    S = sys.modules[_NAME]
else:
    _s = importlib.util.spec_from_file_location(_NAME, _SUPPORT)
    assert _s is not None and _s.loader is not None
    S = importlib.util.module_from_spec(_s)
    sys.modules[_NAME] = S
    _s.loader.exec_module(S)

_HTTP_SUPPORT = "am_exec_http_support"
if _HTTP_SUPPORT in sys.modules:
    support = sys.modules[_HTTP_SUPPORT]
else:
    _h = importlib.util.spec_from_file_location(_HTTP_SUPPORT, Path(__file__).resolve().parent / "http_support.py")
    assert _h is not None and _h.loader is not None
    support = importlib.util.module_from_spec(_h)
    sys.modules[_HTTP_SUPPORT] = support
    _h.loader.exec_module(support)

RECORDINGS = Path(__file__).resolve().parents[3] / "fixtures/recorded/text_analysis"
RECORDING_PATH = next(RECORDINGS.glob("*.json"))
RECORDING = json.loads(RECORDING_PATH.read_text("utf-8"))
MODEL = support.PIN.model_id
LIVE = ProviderConfig(
    mode=ProviderMode.LIVE, model_id=MODEL, run_cost_ceiling_usd=1.0, api_key=None,
    ceiling_is_explicit=True,
)

#: The "local command": reads the task document on stdin and prints ONE JSON document. The echo
#: task of a probe is answered with its nonce; a run's task with the recorded analysis.
STUB = r'''
import json, sys
task = json.load(sys.stdin)
mode = sys.argv[2] if len(sys.argv) > 2 else "answer"
if mode == "garbage":
    print("this is not json")
elif "echo" in task["output_schema"].get("properties", {}):
    print(json.dumps({"echo": task["user_text"]}))
else:
    print(json.load(open(sys.argv[1]))["output_text"])
'''


def _settings(**over: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "pin_id": MODEL, "gateway_model": MODEL, "billing": "not_metered",
        "allow_client_documents": False, "timeout_seconds": 60, "pull_client": "agent",
        "answer_deadline_seconds": 30, "max_claimed_tasks": 1,
    }
    values.update(over)
    return values


def _agent(tmp_path: Path, origin: str, token: str, *, mode: str = "answer", declared: str = MODEL) -> Any:
    stub = S.write_stub(tmp_path / f"stub-{mode}.py", STUB)
    config = S.agent_config(
        tmp_path / f"agent-{mode}.toml", origin,
        argv=[sys.executable, str(stub), str(RECORDING_PATH), mode], declared=declared,
        command_timeout=60.0,
    )
    return S.AgentProcess(config, "--max-tasks", "1", token=token)


def _probe_by_the_agent(tmp_path: Path, sessions: Serialised, origin: str, token: str, connection_id: str) -> None:
    """«Проверить»: the worker's probe loop posts the echo task and the agent answers it."""
    with sessions() as session:
        from auditmanager.executors.public import request_probe

        request_probe(
            session, connection_id=connection_id, roles=support.ADMIN_ROLES,
            idempotency_key=support.unique(), actor_uid=support.ACTOR)
        session.commit()
    runner = ProbeRunner(
        sessions, ring=None, policy=DestinationPolicy.from_environment({}), engine=None)  # type: ignore[arg-type]
    with _agent(tmp_path, origin, token) as agent:
        assert runner.run_pending() == 1
        runner.join_pull_probes(60)
        code = agent.wait(timeout=30)
        assert code == 0, agent.stderr
    with sessions() as session:
        row = session.execute(text(
            "SELECT state, outcome, reported_model, identity_basis FROM executor_probe "
            "WHERE connection_id = :c"), {"c": connection_id}).mappings().one()
    assert dict(row) == {"state": "finished", "outcome": "ok", "reported_model": MODEL,
                         "identity_basis": "declared"}


def _providers(sessions: Serialised) -> DatabaseProviders:
    return DatabaseProviders(
        ring=None, policy=DestinationPolicy.from_environment({}), base_config=LIVE, ceiling_usd=1.0,
        runtime=KindRuntime(session_factory=sessions, engine=None),  # type: ignore[arg-type]
    )


def _start_run(session: Any, seeded: Any, new_key: Any, label: str, providers: DatabaseProviders) -> Any:
    return start_audit_run(
        session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="live",
        idempotency_key=new_key(label), connection_route=providers.freeze,
    )


def _execute_with_agent_started_at_the_first_wait(
    session: Any, blob_store: Any, run_id: str, providers: Any, monkeypatch: pytest.MonkeyPatch,
    start_agent: Any,
) -> tuple[Any, Any]:
    """Run to a terminal state; the agent process is started the first time the worker waits, so
    until then no server thread has anything to read."""
    started: list[Any] = []
    real = pull.TaskWaiter.wait

    def wait(self: Any, seconds: float) -> None:
        if not started:
            started.append(start_agent())
        real(self, min(seconds, 0.05))

    monkeypatch.setattr(pull.TaskWaiter, "wait", wait)
    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=UnboundAdapter(), provider_config=LIVE,
        providers=providers.resolve,
    )
    return result, started[0]


def _rows(session: Any, run_id: str) -> dict[str, Any]:
    one = lambda sql: [dict(r) for r in session.execute(text(sql), {"r": run_id}).mappings()]  # noqa: E731
    return {
        "run": one("SELECT * FROM audit_run WHERE run_id = :r")[0],
        "calls": one("SELECT * FROM model_call WHERE run_id = :r"),
        "effects": one("SELECT * FROM provider_call_effect WHERE run_id = :r"),
        "stage": one("SELECT * FROM stage_result WHERE run_id = :r AND stage_id = 'text_analysis'")[0],
        "tasks": one("SELECT * FROM executor_task WHERE run_id = :r"),
    }


def test_the_agent_answers_the_probe_and_then_a_real_runs_text_analysis_task(
    stand, session, seeded, blob_store, new_key, tmp_path, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    surface, sessions, origin = stand
    connection_id = make_connection(surface, settings=_settings())
    token, token_meta = issue(surface, connection_id)

    # 1. «Проверить» is taken by the worker and answered by the agent: the connection is routable
    #    on a probe taken on no key.
    _probe_by_the_agent(tmp_path, sessions, origin, token, connection_id)
    support.route(session, connection_id)
    revision_id = current_revision(session, connection_id).revision_id

    # 2. A run: its text_analysis call becomes a task, the agent claims it, runs the command and
    #    submits the command's answer.
    providers = _providers(sessions)
    started = _start_run(session, seeded, new_key, "agent-e2e", providers)
    result, agent = _execute_with_agent_started_at_the_first_wait(
        session, blob_store, started.run_id, providers, monkeypatch,
        lambda: _agent(tmp_path, origin, token, mode="answer"),
    )
    code = agent.wait(timeout=60)
    stderr = agent.stderr
    rows = _rows(session, started.run_id)

    assert code == 0, stderr
    assert result.terminal_state == "published" and result.published_finding_count > 0
    assert rows["run"]["connection_revision_id"] == revision_id
    (call,), (effect,) = rows["calls"], rows["effects"]
    for row in (call, effect):
        assert (row["identity_basis"], row["provider"]) == ("declared", "agent")
    assert (call["cost_basis"], call["cost_micros"], effect["state"]) == ("unmetered", 0, "completed")
    cost = RunRepository().cost(session, started.run_id)
    assert (cost.model_call_count, cost.cost_micros, cost.basis) == (1, 0, "unmetered")
    (task,) = rows["tasks"]
    assert (task["state"], task["origin"], task["declared_model"], task["claim_count"]) == (
        "answered", "run_call", MODEL, 1)
    assert task["model_call_id"] == call["model_call_id"] and task["connection_id"] == connection_id
    # The token is seen from where it called, and appears nowhere the agent writes.
    seen = session.execute(text(
        "SELECT last_seen_at, last_seen_address FROM executor_runner_token WHERE token_id = :t"),
        {"t": token_meta["token_id"]}).one()
    assert seen[0] is not None and seen[1] == "127.0.0.1"
    for output in (stderr, agent.stdout):
        assert token not in output


def test_an_agent_whose_command_prints_no_json_fails_the_task_and_the_run_ends_outcome_unknown(
    stand, session, seeded, blob_store, new_key, tmp_path, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    surface, sessions, origin = stand
    connection_id = make_connection(surface, settings=_settings())
    token, _ = issue(surface, connection_id)
    _probe_by_the_agent(tmp_path, sessions, origin, token, connection_id)
    support.route(session, connection_id)
    providers = _providers(sessions)
    started = _start_run(session, seeded, new_key, "agent-garbage", providers)
    result, agent = _execute_with_agent_started_at_the_first_wait(
        session, blob_store, started.run_id, providers, monkeypatch,
        lambda: _agent(tmp_path, origin, token, mode="garbage"),
    )
    code = agent.wait(timeout=60)
    rows = _rows(session, started.run_id)
    assert code == 0, agent.stderr
    assert result.terminal_state == "failed"
    (effect,) = rows["effects"]
    assert effect["dispatch_class"] == "outcome_unknown", "a claimed task that fails may have run"
    (task,) = rows["tasks"]
    assert task["state"] == "failed" and task["claim_count"] == 1
    assert rows["stage"]["error"]["details"]["dependency"] == "executor_task_failed"


def test_an_agent_that_declares_another_model_than_the_connection_pins_never_runs_the_command(
    stand, session, seeded, blob_store, new_key, tmp_path, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    surface, sessions, origin = stand
    connection_id = make_connection(surface, settings=_settings())
    token, _ = issue(surface, connection_id)
    _probe_by_the_agent(tmp_path, sessions, origin, token, connection_id)
    support.route(session, connection_id)
    providers = _providers(sessions)
    started = _start_run(session, seeded, new_key, "agent-other-model", providers)
    result, agent = _execute_with_agent_started_at_the_first_wait(
        session, blob_store, started.run_id, providers, monkeypatch,
        lambda: _agent(tmp_path, origin, token, mode="answer", declared="not-the-pinned-model"),
    )
    code = agent.wait(timeout=60)
    rows = _rows(session, started.run_id)
    assert code == 0, agent.stderr
    assert result.terminal_state == "failed"
    (task,) = rows["tasks"]
    assert task["state"] == "failed" and "model_mismatch" in (task["fail_reason"] or "")
    assert rows["calls"] == [] or all(c["cost_micros"] in (None, 0) for c in rows["calls"])
