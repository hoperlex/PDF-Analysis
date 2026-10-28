"""`CMP-C0-FIX-01` item 1: which origin a pull task is written with.

A call made for a comparison work attempt (`CMP-SPEND-01`, ADR-0025 decision 4) is an ``executor_task`` of origin
``comparison_call`` that names its ``comparison_attempt_id`` and no run; every other call is a Run's call, written as it
always was. No database and no sleeping: a task table that answers at once. The permanent pin of the bare
``_write_task`` call is ``tests/unit/comparison/spend/test_wiring_and_pins.py``; these tests go through ``complete``, so
they also show that the comparison context's ``remaining_seconds()`` cuts the window the task is written with.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors.model import RevisionRecord, RevisionSettings
from auditmanager.executors.pull import DEADLINE_MARGIN_SECONDS, PullAdapter
from auditmanager.executors.runner_repository import TaskRecord
from auditmanager.jobs.lease import AttemptContext

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
MODEL = "claude-opus-5"
SCHEMA = {"type": "object", "properties": {"observations": {"type": "array"}},
          "required": ["observations"], "additionalProperties": False}
REQUEST = ModelRequest(model_id=MODEL, body={
    "model": MODEL, "max_tokens": 16, "system": "SYSTEM",
    "messages": [{"role": "user", "content": "USER"}],
    "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
})


class AnsweringStore:
    """A task table whose runner answers the moment the task is written."""

    def __init__(self) -> None:
        self.inserted: list[dict[str, Any]] = []
        self.task: TaskRecord | None = None

    def insert_task(self, session: object, **kwargs: Any) -> TaskRecord:
        self.inserted.append(kwargs)
        self.task = TaskRecord(
            task_id="ext_T", connection_id=kwargs["connection_id"], revision_id=kwargs["revision_id"],
            origin=kwargs["origin"], run_id=kwargs["run_id"], attempt_id=kwargs["attempt_id"],
            model_call_id=kwargs["model_call_id"], probe_id=kwargs["probe_id"], state="answered",
            expected_model=kwargs["expected_model"], created_at=NOW, deadline_at=NOW,
            claimed_by_token_id="ern_R", claim_expires_at=NOW, first_claimed_at=NOW, claim_count=1,
            declared_model=MODEL, declared_input_tokens=3, declared_output_tokens=2,
            fail_reason=None, terminal_at=NOW, payload_cleared_at=None, past_deadline=False,
            comparison_attempt_id=kwargs.get("comparison_attempt_id"),
        )
        return self.task

    def get_task(self, session: object, task_id: str, **_: object) -> TaskRecord | None:
        return self.task

    def answer_of(self, session: object, task_id: str) -> tuple[str | None, str | None]:
        return '{"observations": []}', MODEL


class Sessions:
    @contextmanager
    def __call__(self):  # type: ignore[no-untyped-def]
        class Session:
            def commit(self) -> None: ...

        yield Session()


@dataclass(frozen=True)
class ComparisonContext:
    """What the lane that calls a model builds for a comparison call: the attempt it serves and the time it has left."""

    comparison_attempt_id: str
    left: float = 600.0

    def remaining_seconds(self) -> float:
        return self.left


def _revision(deadline: int = 600) -> RevisionRecord:
    return RevisionRecord(
        revision_id="excr_R", connection_id="exc_C", revision_no=1, created_at=NOW, created_by="usr_A",
        settings=RevisionSettings(
            pin_id=MODEL, gateway_model=MODEL, billing="not_metered", allow_client_documents=False,
            timeout_seconds=60, pull_client="claude_code_session", answer_deadline_seconds=deadline,
            max_claimed_tasks=1),
    )


def _call(context: object | None, *, deadline: int = 600) -> dict[str, Any]:
    store = AnsweringStore()
    adapter = PullAdapter(session_factory=Sessions(), revision=_revision(deadline), context=context,
                          repository=store)  # type: ignore[arg-type]
    assert adapter.complete(REQUEST).output_text == '{"observations": []}'
    assert len(store.inserted) == 1
    return store.inserted[0]


def test_a_comparison_call_writes_a_comparison_call_task_that_names_its_attempt_and_no_run() -> None:
    written = _call(ComparisonContext("cqa_01ARZ3NDEKTSV4RRFFQ69G5FAV"))
    assert written["origin"] == "comparison_call"
    assert written["comparison_attempt_id"] == "cqa_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    # The origin-shape CHECK of the table: a comparison call has no run, no run attempt, no model call, no probe.
    assert (written["run_id"], written["attempt_id"], written["model_call_id"], written["probe_id"]) == (None,) * 4
    assert written["connection_id"] == "exc_C" and written["revision_id"] == "excr_R"
    assert written["expected_model"] == MODEL


def test_the_comparison_contexts_remaining_time_cuts_the_window_the_task_is_written_with() -> None:
    cut = _call(ComparisonContext("cqa_X", left=200.0))
    assert cut["deadline_seconds"] == pytest.approx(200.0 - DEADLINE_MARGIN_SECONDS)
    uncut = _call(ComparisonContext("cqa_X", left=100000.0), deadline=300)
    assert uncut["deadline_seconds"] == 300.0


def test_a_comparison_call_with_too_little_time_left_writes_no_task() -> None:
    store = AnsweringStore()
    adapter = PullAdapter(session_factory=Sessions(), revision=_revision(),
                          context=ComparisonContext("cqa_X", left=DEADLINE_MARGIN_SECONDS + 0.5),
                          repository=store)  # type: ignore[arg-type]
    with pytest.raises(ProxyDispatchError):
        adapter.complete(REQUEST)
    assert store.inserted == []


def test_a_runs_call_is_written_exactly_as_before() -> None:
    context = AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic(), call_id="mc_1")
    written = _call(context)
    assert written["origin"] == "run_call"
    assert written["comparison_attempt_id"] is None
    assert (written["run_id"], written["attempt_id"], written["model_call_id"], written["probe_id"]) == (
        "run_1", "att_1", "mc_1", None)


def test_a_call_with_no_context_is_a_run_call_not_a_comparison_call() -> None:
    written = _call(None)
    assert written["origin"] == "run_call" and written["comparison_attempt_id"] is None


def test_the_run_contexts_have_no_attribute_that_could_make_a_run_call_a_comparison_call() -> None:
    """The discriminator is the attribute, and only the comparison context carries it: the run's context must not."""
    context = AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic())
    assert not hasattr(context, "comparison_attempt_id")
