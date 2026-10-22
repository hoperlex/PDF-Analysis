"""`EXEC-CANDIDATE-2`: a real run through a ``pull`` connection (`EXEC-PULL-01` wired into `EXEC-HTTP-01`).

Real PostgreSQL and S3; no network and no model. The run is started with the provider source
``database``, so it freezes the route's revision and ``execute_run`` binds the adapter of that
revision at its Attempt: for a ``pull`` revision that is the task adapter, which writes an
``executor_task`` and waits. A runner is played through the real application (the seam, the
envelope, the runner adapter and real rows) *while the worker waits*, on the same thread and the
same rolled-back session, so every flow is deterministic and free of threads.

What this file shows that the PULL lane could not: the resolver and the worker's probe loop serve
the kind (they used to refuse it as ``kind_not_served``); a connection with no key is probed on the
worker, routed and started on; the run records the declared model, ``identity_basis: declared`` and
the unmetered cost; an unclaimed task ends the run as ``no_executor_online`` with nothing charged.
"""

from __future__ import annotations

import functools
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
from auditmanager.executors import probe_runner, pull
from auditmanager.executors.kinds import adapter_for, register_channel_kind
from auditmanager.executors.public import current_revision
from auditmanager.executors.runtime import DestinationPolicy, KindRuntime
from auditmanager.runs import RunRepository, execute_run, start_audit_run
from auditmanager.shared.errors import DomainError
from tests.integration.executors.test_runner_channel import (  # noqa: F401  (surface is a fixture)
    admin_call, claim, issue, make_connection, runner_call, surface,
)

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

_SUPPORT_NAME = "am_exec_http_support"
_SUPPORT_PATH = Path(__file__).resolve().parent / "http_support.py"
if _SUPPORT_NAME in sys.modules:
    support = sys.modules[_SUPPORT_NAME]
else:
    _s = importlib.util.spec_from_file_location(_SUPPORT_NAME, _SUPPORT_PATH)
    assert _s is not None and _s.loader is not None
    support = importlib.util.module_from_spec(_s)
    sys.modules[_SUPPORT_NAME] = support
    _s.loader.exec_module(support)

RECORDINGS = Path(__file__).resolve().parents[3] / "fixtures/recorded/text_analysis"
RECORDING = json.loads(next(RECORDINGS.glob("*.json")).read_text("utf-8"))
MODEL = support.PIN.model_id
LIVE = ProviderConfig(
    mode=ProviderMode.LIVE, model_id=MODEL, run_cost_ceiling_usd=1.0, api_key=None,
    ceiling_is_explicit=True,
)


def _settings(**over: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "pin_id": MODEL, "gateway_model": MODEL, "billing": "not_metered",
        "allow_client_documents": False, "timeout_seconds": 60,
        "pull_client": "claude_code_session", "answer_deadline_seconds": 10,
        "max_claimed_tasks": 1,
    }
    values.update(over)
    return values


def _providers(session: Any) -> DatabaseProviders:
    return DatabaseProviders(
        ring=None, policy=DestinationPolicy.from_environment({}), base_config=LIVE, ceiling_usd=1.0,
        runtime=KindRuntime(session_factory=lambda: nullcontext(session), engine=None),
    )


def _start(session: Any, seeded: Any, new_key: Any, label: str, providers: DatabaseProviders) -> Any:
    return start_audit_run(
        session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="live",
        idempotency_key=new_key(label), connection_route=providers.freeze,
    )


def _execute(session: Any, blob_store: Any, run_id: str, providers: Any) -> Any:
    return execute_run(
        session, run_id, blob_store=blob_store, adapter=UnboundAdapter(), provider_config=LIVE,
        providers=providers.resolve,
    )


def _rows(session: Any, run_id: str) -> dict[str, Any]:
    one = lambda sql: [dict(r) for r in session.execute(text(sql), {"r": run_id}).mappings()]  # noqa: E731
    return {
        "run": one("SELECT * FROM audit_run WHERE run_id = :r")[0],
        "calls": one("SELECT * FROM model_call WHERE run_id = :r"),
        "effects": one("SELECT * FROM provider_call_effect WHERE run_id = :r"),
        "stage": one("SELECT * FROM stage_result WHERE run_id = :r AND stage_id = 'text_analysis'")[0],
        "tasks": one("SELECT * FROM executor_task WHERE run_id = :r"),
    }


def _play_on_first_wait(monkeypatch: pytest.MonkeyPatch, moves: Any) -> None:
    """Run ``moves()`` once, the first time a worker waits for a runner."""
    done: list[bool] = []
    real = pull.TaskWaiter.wait

    def wait(self: Any, seconds: float) -> None:
        if not done:
            done.append(True)
            moves()
        real(self, min(seconds, 0.005))

    monkeypatch.setattr(pull.TaskWaiter, "wait", wait)


def _probed_connection(session: Any, surface: Any, monkeypatch: pytest.MonkeyPatch, **settings: Any) -> tuple[str, str]:
    """A ``pull`` connection with a token, probed ``ok`` by the worker's loop and routed."""
    connection_id = make_connection(surface, settings=_settings(**settings))
    token, _ = issue(surface, connection_id)
    requested = admin_call(surface, "POST", f"/executor-connections/{connection_id}/probes")
    assert requested.status == 202, requested.body

    def runner() -> None:
        claimed = claim(surface, token)
        assert claimed.status == 200, claimed.body
        task = claimed.json()
        answer = {"output_text": json.dumps({"echo": task["user_text"]}), "model": task["model"]}
        assert runner_call(surface, token, f"/runner/tasks/{task['task_id']}/answer", answer).status == 200

    _play_on_first_wait(monkeypatch, runner)
    worker = probe_runner.ProbeRunner(
        lambda: nullcontext(session), ring=None,  # type: ignore[arg-type,return-value]
        policy=DestinationPolicy.from_environment({}),
    )
    assert worker.run_pending() == 1
    worker.join_pull_probes(30)
    return connection_id, token


def freeze_route_connection(session: Any) -> str:
    from auditmanager.executors.runtime import freeze_connection

    return freeze_connection(session, "text_analysis").connection_id


def test_the_workers_probe_loop_serves_a_pull_connection_and_a_route_to_it_is_allowed(
    session, surface, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    connection_id, _ = _probed_connection(session, surface, monkeypatch)
    probe = session.execute(text(
        "SELECT state, outcome, reported_model, identity_basis, secret_id FROM executor_probe "
        "WHERE connection_id = :c"), {"c": connection_id}).mappings().one()
    assert dict(probe) == {"state": "finished", "outcome": "ok", "reported_model": MODEL,
                           "identity_basis": "declared", "secret_id": None}
    # The kind is served, with no key and no address: a route is allowed on that probe alone.
    support.route(session, connection_id)
    assert freeze_route_connection(session) == connection_id


def test_a_probe_nobody_takes_ends_no_runner_online_and_the_connection_cannot_be_routed(
    session, surface, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    connection_id = make_connection(surface, settings=_settings())
    admin_call(surface, "POST", f"/executor-connections/{connection_id}/probes")
    monkeypatch.setattr(probe_runner, "probe_pull", functools.partial(
        pull.probe_pull, claim_seconds=0.2, answer_seconds=0.2, poll_seconds=0.02))
    worker = probe_runner.ProbeRunner(
        lambda: nullcontext(session), ring=None,  # type: ignore[arg-type,return-value]
        policy=DestinationPolicy.from_environment({}),
    )
    assert worker.run_pending() == 1
    worker.join_pull_probes(30)
    outcome = session.execute(text(
        "SELECT outcome FROM executor_probe WHERE connection_id = :c"), {"c": connection_id}).scalar_one()
    assert outcome == "no_runner_online"
    with pytest.raises(DomainError) as refused:
        support.route(session, connection_id)
    assert refused.value.code.value == "conflict"
    assert "connection_not_probed" in str(refused.value.detail_fields)


def test_a_run_is_answered_by_a_runner_and_records_the_declared_model_and_no_cost(
    session, seeded, blob_store, new_key, surface, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    connection_id, token = _probed_connection(session, surface, monkeypatch)
    support.route(session, connection_id)
    revision_id = current_revision(session, connection_id).revision_id
    providers = _providers(session)
    started = _start(session, seeded, new_key, "pull-ok", providers)
    seen: dict[str, Any] = {}

    def runner() -> None:
        claimed = claim(surface, token)
        assert claimed.status == 200, claimed.body
        task = claimed.json()
        seen.update(task)
        answered = runner_call(surface, token, f"/runner/tasks/{task['task_id']}/answer", {
            "output_text": RECORDING["output_text"], "model": task["model"],
            "input_tokens": RECORDING["usage"]["input_tokens"],
            "output_tokens": RECORDING["usage"]["output_tokens"]})
        assert answered.status == 200, answered.body

    _play_on_first_wait(monkeypatch, runner)
    result = _execute(session, blob_store, started.run_id, providers)
    rows = _rows(session, started.run_id)

    assert result.terminal_state == "published" and result.published_finding_count > 0
    assert rows["run"]["connection_revision_id"] == revision_id, "frozen at start"
    # What the runner was handed: the pinned model, the real prompt halves and the stage's schema.
    assert seen["model"] == MODEL and seen["system"] and seen["user_text"]
    assert seen["output_schema"]["type"] == "object"
    (call,), (effect,) = rows["calls"], rows["effects"]
    for row in (call, effect):
        assert row["connection_revision_id"] == revision_id
        assert (row["identity_basis"], row["provider"]) == ("declared", "claude_code_session")
    assert (call["cost_basis"], call["cost_micros"], effect["state"]) == ("unmetered", 0, "completed")
    cost = RunRepository().cost(session, started.run_id)
    assert (cost.model_call_count, cost.cost_micros, cost.basis) == (1, 0, "unmetered")
    # The task names the run, the Attempt and the call it served, and was answered once.
    (task,) = rows["tasks"]
    assert (task["state"], task["origin"], task["declared_model"], task["claim_count"]) == (
        "answered", "run_call", MODEL, 1)
    assert task["attempt_id"] is not None and task["model_call_id"] == call["model_call_id"]
    assert task["connection_id"] == connection_id


def test_a_run_nobody_serves_ends_no_executor_online_with_nothing_charged_and_no_other_connection(
    session, seeded, blob_store, new_key, surface, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    connection_id, _ = _probed_connection(session, surface, monkeypatch)
    support.route(session, connection_id)
    providers = _providers(session)
    started = _start(session, seeded, new_key, "pull-unserved", providers)

    # The deadline passes on a clock of the test's: three seconds a reading, against a ten second
    # window, so the wait ends after a few polls and nobody ever calls the claim endpoint.
    ticks = iter(range(0, 10_000, 3))
    original = adapter_for("pull")
    assert original is not None and original.channel is not None

    def quick(revision: Any, context: Any, runtime: Any) -> Any:
        return pull.PullAdapter(
            session_factory=runtime.session_factory, revision=revision, context=context,
            engine=None, poll_seconds=0.01, monotonic=lambda: float(next(ticks)))

    register_channel_kind("pull", quick, serves=original.serves, provider_label=original.provider_label)
    try:
        result = _execute(session, blob_store, started.run_id, providers)
    finally:
        register_channel_kind("pull", original.channel, serves=original.serves,
                              provider_label=original.provider_label)
    rows = _rows(session, started.run_id)

    assert result.terminal_state == "failed"
    (effect,) = rows["effects"]
    assert (effect["state"], effect["dispatch_class"]) == ("not_processed", "not_sent")
    error = rows["stage"]["error"]
    assert error["code"] == "dependency_unavailable"
    assert error["details"]["dependency"] == "no_executor_online"
    assert rows["calls"] == [] or all(call["cost_micros"] in (None, 0) for call in rows["calls"])
    cost = RunRepository().cost(session, started.run_id)
    assert cost.cost_micros == 0
    (task,) = rows["tasks"]
    assert (task["state"], task["claim_count"]) == ("expired", 0)
    # It never moved to another connection: the only task is this connection's.
    assert task["connection_id"] == connection_id


def test_a_revoked_token_cannot_answer_the_run_and_the_wait_ends_as_outcome_unknown(
    session, seeded, blob_store, new_key, surface, monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    """The runner takes the task, then its token is revoked: the answer is refused (401), the claim
    lapses nowhere before the deadline, and the call ends as outcome-unknown (the model may have run)."""
    connection_id, token = _probed_connection(session, surface, monkeypatch)
    support.route(session, connection_id)
    providers = _providers(session)
    started = _start(session, seeded, new_key, "pull-revoked", providers)
    token_id = session.execute(text(
        "SELECT token_id FROM executor_runner_token WHERE connection_id = :c"),
        {"c": connection_id}).scalar_one()

    def runner() -> None:
        claimed = claim(surface, token)
        assert claimed.status == 200
        revoked = admin_call(
            surface, "POST", f"/executor-connections/{connection_id}/runner-tokens/{token_id}/revoke")
        assert revoked.status == 200
        late = runner_call(surface, token, f"/runner/tasks/{claimed.json()['task_id']}/answer", {
            "output_text": RECORDING["output_text"], "model": claimed.json()["model"]})
        assert late.status == 401

    _play_on_first_wait(monkeypatch, runner)
    ticks = iter(range(0, 10_000, 3))
    original = adapter_for("pull")
    assert original is not None and original.channel is not None

    def quick(revision: Any, context: Any, runtime: Any) -> Any:
        return pull.PullAdapter(
            session_factory=runtime.session_factory, revision=revision, context=context,
            engine=None, poll_seconds=0.01, monotonic=lambda: float(next(ticks)))

    register_channel_kind("pull", quick, serves=original.serves, provider_label=original.provider_label)
    try:
        result = _execute(session, blob_store, started.run_id, providers)
    finally:
        register_channel_kind("pull", original.channel, serves=original.serves,
                              provider_label=original.provider_label)
    rows = _rows(session, started.run_id)
    assert result.terminal_state == "failed"
    (effect,) = rows["effects"]
    assert effect["dispatch_class"] == "outcome_unknown"
    assert rows["stage"]["error"]["details"]["dependency"] == "executor_deadline"
