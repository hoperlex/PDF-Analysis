"""`CTX-STAND`: the pull adapter writes ``context_request`` into the task of a `review:main` call, and into no other.

The descriptor is the claim's (RUNNER_API 11): ``{input_id, text_sha256, section}`` per observation of the critic's request, only for the call of
the cell ``review:main`` of a run whose consent holds the stand's own ``executor_context_policy`` under plan v3 on the stage layout. Every other
call is written byte for byte as it was: the payload has the members it always had and no more. No database and no sleeping (the scripted task
table of ``test_pull_adapter``).
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy.exc import OperationalError

from auditmanager.analysis.public import ModelRequest
from auditmanager.executors import pull, task_context
from auditmanager.executors.pull import HostCall, PullAdapter
from auditmanager.executors.task_context import RunContextFacts
from auditmanager.jobs.lease import AttemptContext
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.executors.test_pull_adapter import MODEL, SCHEMA, Clock, FakeStore, Sessions, revision

CRITIC = ModelRequest(model_id=MODEL, body={
    "model": MODEL, "max_tokens": 16, "system": "SYSTEM",
    "messages": [{"role": "user", "content": json.dumps({"observations": [
        {"input_id": "xri_1", "title": "Размер", "description": "Размер не сходится"},
        {"input_id": "xri_2", "title": "Узел", "description": "Узел не показан"}]}, ensure_ascii=False)}],
    "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
})
ELIGIBLE = RunContextFacts(True, "extended-review-v3", "AR", task_context.executor_context_policy())


def call(cell: str) -> HostCall:
    return HostCall(provider="claude_code", access="subscription", model_id=MODEL, effort="medium", timeout_seconds=900, cell_key=cell)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(pull.time, "sleep", fake.sleep)
    return fake


def answer(clock: Clock, store: FakeStore) -> None:
    if store.task is not None and store.task.state == "open":
        store.claim()
        store.answered('{"observations": []}', MODEL)


def written(clock: Clock, monkeypatch: pytest.MonkeyPatch, *, cell: str = "review:main", facts: Any = ELIGIBLE, request: ModelRequest = CRITIC,
            context: Any = "attempt", host: bool = True) -> dict[str, Any]:
    reads: list[str] = []

    def read(session: Any, run_id: str) -> Any:
        reads.append(run_id)
        if isinstance(facts, BaseException):
            raise facts
        return facts

    monkeypatch.setattr(pull, "read_run_context_facts", read)
    store = FakeStore(clock, answer)
    attempt = AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic(), call_id="mc_1") if context == "attempt" else context
    PullAdapter(session_factory=Sessions(), revision=revision(deadline=3600), context=attempt, repository=store,  # type: ignore[arg-type]
                poll_seconds=2.0, monotonic=clock.monotonic, host_call=call(cell) if host else None).complete(request)
    assert store.payload is not None
    store.payload["__reads"] = reads  # type: ignore[assignment]
    return store.payload


def test_the_critic_call_of_an_eligible_run_carries_one_entry_per_observation_in_order(clock: Clock, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = written(clock, monkeypatch)
    request = payload["context_request"]
    assert [entry["input_id"] for entry in request] == ["xri_1", "xri_2"] and {entry["section"] for entry in request} == {"AR"}
    assert all(len(entry["text_sha256"]) == 64 for entry in request) and payload["__reads"] == ["run_1"]
    assert payload["host"]["cell_key"] == "review:main"


@pytest.mark.parametrize("name, facts", [
    ("a legacy run", replace(ELIGIBLE, stage_plan=False)),
    ("a run that asks for plan v2", replace(ELIGIBLE, plan_version="extended-review-v2")),
    ("a consent without the policy", replace(ELIGIBLE, policy=None)),
    ("a consent with another digest", replace(ELIGIBLE, policy={**task_context.executor_context_policy(), "bundle_sha256": "3" * 64})),
    ("a consent that cannot be read", task_context.NO_FACTS),
])
def test_a_run_that_is_not_eligible_gets_a_task_exactly_as_before(clock: Clock, monkeypatch: pytest.MonkeyPatch, name: str, facts: Any) -> None:
    payload = written(clock, monkeypatch, facts=facts)
    assert "context_request" not in payload and set(payload) == {"system", "user_text", "output_schema", "host", "__reads"}, name


@pytest.mark.parametrize("cell", ["text:main", "blocks:main", "blocks:leg1", "cross_check:main", "norms:main", "correction:main"])
def test_no_other_cell_is_offered_reference_data_and_its_consent_is_not_even_read(clock: Clock, monkeypatch: pytest.MonkeyPatch, cell: str) -> None:
    payload = written(clock, monkeypatch, cell=cell)
    assert "context_request" not in payload and payload["__reads"] == []


def test_a_call_that_is_not_a_cells_is_written_as_it_was(clock: Clock, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = written(clock, monkeypatch, host=False)
    assert set(payload) == {"system", "user_text", "output_schema", "__reads"} and payload["__reads"] == []


def test_a_call_with_no_run_or_of_a_comparison_is_not_offered_any(clock: Clock, monkeypatch: pytest.MonkeyPatch) -> None:
    class Comparison:
        run_id = None
        comparison_attempt_id = "cwa_1"
        attempt_id = None
        call_id = None

        def remaining_seconds(self) -> float:
            return 3000.0

        def call_started(self) -> None: ...

    payload = written(clock, monkeypatch, context=Comparison())
    assert "context_request" not in payload and payload["__reads"] == []


def test_a_request_that_is_not_a_critics_is_offered_nothing(clock: Clock, monkeypatch: pytest.MonkeyPatch) -> None:
    repair = ModelRequest(model_id=MODEL, body={**CRITIC.body, "messages": [{"role": "user", "content": "the reply was refused: repair it"}]})
    assert "context_request" not in written(clock, monkeypatch, request=repair)


@pytest.mark.parametrize("failure", [DomainError(ErrorCode.INTERNAL_ERROR), OperationalError("s", {}, Exception("x"))])
def test_a_consent_that_cannot_be_read_costs_the_call_only_its_data(clock: Clock, monkeypatch: pytest.MonkeyPatch, failure: BaseException) -> None:
    payload = written(clock, monkeypatch, facts=failure)
    assert "context_request" not in payload and payload["system"] == "SYSTEM", "the task is written; reference data is optional by contract"
