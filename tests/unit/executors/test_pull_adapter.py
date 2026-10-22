"""`EXEC-PULL-01`: the pull adapter and its probe, against a scripted task table.

No database and no sleeping: ``FakeStore`` is the task table, a ``Clock`` stands in for
``time.monotonic`` and ``time.sleep``, and a *script* plays the runner at chosen instants. The
same flows run against real rows in ``tests/integration/executors``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors import pull
from auditmanager.executors.model import RevisionRecord, RevisionSettings
from auditmanager.executors.pull import PullAdapter, answer_window, probe_pull
from auditmanager.executors.runner_repository import TaskRecord
from auditmanager.jobs.lease import AttemptContext
from auditmanager.shared.errors import ErrorCode

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
MODEL = "claude-opus-5"
SCHEMA = {"type": "object", "properties": {"observations": {"type": "array"}},
          "required": ["observations"], "additionalProperties": False}
REQUEST = ModelRequest(model_id=MODEL, body={
    "model": MODEL, "max_tokens": 16, "system": "SYSTEM",
    "messages": [{"role": "user", "content": "USER"}],
    "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
})


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeStore:
    """The task table. ``script(clock, store)`` runs on every read and plays the runner."""

    def __init__(self, clock: Clock, script: Callable[[Clock, "FakeStore"], None] | None = None) -> None:
        self.clock, self.script = clock, script
        self.task: TaskRecord | None = None
        self.payload: dict | None = None
        self.answer: tuple[str | None, str | None] = (None, None)
        self.events: list[str] = []

    def insert_task(self, session, **kwargs) -> TaskRecord:
        self.payload = dict(kwargs["payload"])
        self.events.append(f"insert:{kwargs['origin']}")
        self.inserted = kwargs
        self.task = TaskRecord(
            task_id="ext_T", connection_id=kwargs["connection_id"], revision_id=kwargs["revision_id"],
            origin=kwargs["origin"], run_id=kwargs["run_id"], attempt_id=kwargs["attempt_id"],
            model_call_id=kwargs["model_call_id"], probe_id=kwargs["probe_id"], state="open",
            expected_model=kwargs["expected_model"], created_at=NOW, deadline_at=NOW,
            claimed_by_token_id=None, claim_expires_at=None, first_claimed_at=None, claim_count=0,
            declared_model=None, declared_input_tokens=None, declared_output_tokens=None,
            fail_reason=None, terminal_at=None, payload_cleared_at=None, past_deadline=False,
        )
        return self.task

    def get_task(self, session, task_id: str, **_) -> TaskRecord | None:
        if self.script:
            self.script(self.clock, self)
        return self.task

    def answer_of(self, session, task_id: str):
        return self.answer

    def expire_task(self, session, task_id: str):
        assert self.task is not None
        if self.task.state not in ("open", "claimed"):
            return None
        self.events.append("expire")
        self.task = replace(self.task, state="expired", terminal_at=NOW)
        return self.task

    def cancel_task(self, session, task_id: str) -> bool:
        assert self.task is not None
        if self.task.state not in ("open", "claimed"):
            return False
        self.events.append("cancel")
        self.task = replace(self.task, state="cancelled", terminal_at=NOW)
        return True

    # -- the runner's moves ------------------------------------------------------------------
    def claim(self) -> None:
        assert self.task is not None
        self.task = replace(self.task, state="claimed", claim_count=self.task.claim_count + 1,
                            claimed_by_token_id="ern_R", claim_expires_at=NOW, first_claimed_at=NOW)

    def answered(self, text: str, model: str, tokens: tuple[int, int] | None = (11, 7)) -> None:
        assert self.task is not None
        self.answer = (text, model)
        self.task = replace(
            self.task, state="answered", declared_model=model, terminal_at=NOW,
            declared_input_tokens=None if tokens is None else tokens[0],
            declared_output_tokens=None if tokens is None else tokens[1])

    def failed(self) -> None:
        assert self.task is not None
        self.task = replace(self.task, state="failed", fail_reason="x", terminal_at=NOW)


class Sessions:
    @contextmanager
    def __call__(self):
        class Session:
            def commit(self) -> None: ...
        yield Session()


def revision(*, deadline: int = 600, billing: str = "not_metered") -> RevisionRecord:
    return RevisionRecord(
        revision_id="excr_R", connection_id="exc_C", revision_no=1, created_at=NOW,
        created_by="usr_A", settings=RevisionSettings(
            pin_id=MODEL, gateway_model=MODEL, billing=billing, allow_client_documents=False,
            timeout_seconds=60, pull_client="claude_code_session",
            answer_deadline_seconds=deadline, max_claimed_tasks=1),
    )


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(pull.time, "sleep", fake.sleep)
    return fake


def adapter(clock: Clock, store: FakeStore, *, deadline: int = 600, context=None) -> PullAdapter:
    return PullAdapter(
        session_factory=Sessions(), revision=revision(deadline=deadline), context=context,
        repository=store, poll_seconds=2.0, monotonic=clock.monotonic)  # type: ignore[arg-type]


def context(clock: Clock, *, used: float = 0.0) -> AttemptContext:
    # The watchdog counts on the real monotonic clock; only the waiting is simulated.
    return AttemptContext(run_id="run_1", attempt_id="att_1",
                          started_monotonic=time.monotonic() - used, call_id="mc_1")


def test_an_answered_task_completes_the_call_with_the_declared_model(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if c.now >= 1006 and store.task and store.task.state == "open":
            store.claim()
        if c.now >= 1010 and store.task and store.task.state == "claimed":
            store.answered('{"observations": []}', MODEL)

    store = FakeStore(clock, script)
    response = adapter(clock, store, context=context(clock)).complete(REQUEST)
    assert response.output_text == '{"observations": []}'
    assert (response.input_tokens, response.output_tokens) == (11, 7)
    assert response.reported_cost_usd is None and response.stop_reason == "end_turn"
    assert getattr(response, "model", MODEL) == MODEL
    assert store.events == ["insert:run_call"]
    assert store.inserted["run_id"] == "run_1" and store.inserted["attempt_id"] == "att_1"
    assert store.inserted["model_call_id"] == "mc_1" and store.inserted["expected_model"] == MODEL


def test_the_task_carries_the_two_halves_of_the_request_and_its_schema(clock: Clock) -> None:
    store = FakeStore(clock, lambda c, s: (s.claim(), s.answered("{}", MODEL)) if s.task else None)
    adapter(clock, store).complete(REQUEST)
    assert store.payload == {"system": "SYSTEM", "user_text": "USER", "output_schema": SCHEMA}


def test_the_call_is_recorded_as_declared_and_live() -> None:
    from auditmanager.analysis.public import ProviderMode
    from auditmanager.executors.model import IDENTITY_BASIS_BY_KIND

    built = PullAdapter(session_factory=Sessions(), revision=revision(), context=None,
                        repository=FakeStore(Clock()))  # type: ignore[arg-type]
    assert built.identity_basis == "declared" == IDENTITY_BASIS_BY_KIND["pull"]
    assert built.provider_mode is ProviderMode.LIVE


def test_a_task_nobody_claimed_is_not_sent_and_names_no_executor_online(clock: Clock) -> None:
    store = FakeStore(clock)
    with pytest.raises(ProxyDispatchError) as raised:
        adapter(clock, store, deadline=30).complete(REQUEST)
    error = raised.value
    assert (error.dispatch_class, error.retry_safe) == ("not_sent", False)
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert error.detail_fields == {"dependency": "no_executor_online"}
    assert store.task is not None and store.task.state == "expired"
    assert clock.now >= 1030, "it waited the whole window and not less"


def test_a_task_claimed_and_never_answered_is_outcome_unknown(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if c.now >= 1004 and store.task and store.task.state == "open":
            store.claim()

    store = FakeStore(clock, script)
    with pytest.raises(ProxyDispatchError) as raised:
        adapter(clock, store, deadline=30).complete(REQUEST)
    assert (raised.value.dispatch_class, raised.value.retry_safe) == ("outcome_unknown", False)
    assert raised.value.detail_fields == {"dependency": "executor_deadline"}
    assert store.task is not None and store.task.state == "expired"


def test_a_runner_that_reports_failure_after_a_claim_is_outcome_unknown(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if store.task and store.task.state == "open":
            store.claim()
        elif store.task and store.task.state == "claimed":
            store.failed()

    with pytest.raises(ProxyDispatchError) as raised:
        adapter(clock, FakeStore(clock, script)).complete(REQUEST)
    assert raised.value.dispatch_class == "outcome_unknown"
    assert raised.value.detail_fields == {"dependency": "executor_task_failed"}


def test_a_task_the_api_expired_or_cancelled_reads_as_its_claim_count_says(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if store.task and store.task.state == "open":
            store.task = replace(store.task, state="cancelled", terminal_at=NOW)

    with pytest.raises(ProxyDispatchError) as raised:
        adapter(clock, FakeStore(clock, script)).complete(REQUEST)
    assert (raised.value.dispatch_class, raised.value.detail_fields) == (
        "not_sent", {"dependency": "no_executor_online"})


def test_an_answer_in_the_last_instant_beats_the_deadline(clock: Clock) -> None:
    class Racing(FakeStore):
        def expire_task(self, session, task_id):  # the runner answers between read and expiry
            self.claim()
            self.answered("{}", MODEL)
            return None

    response = adapter(clock, Racing(clock), deadline=10).complete(REQUEST)
    assert response.output_text == "{}"


def test_the_wait_is_cut_to_what_the_watchdog_leaves_minus_the_margin(clock: Clock) -> None:
    # 900 s watchdog, 700 s used: 200 s left, 60 s margin -> 140 s, below the revision's 600.
    ctx = context(clock, used=700)
    assert answer_window(600, ctx) == pytest.approx(140.0)
    assert answer_window(600, None) == 600.0
    assert answer_window(100, ctx) == 100.0
    store = FakeStore(clock)
    with pytest.raises(ProxyDispatchError):
        adapter(clock, store, deadline=600, context=ctx).complete(REQUEST)
    assert 1139 <= clock.now - 0 <= 1150, clock.now


def test_with_too_little_time_left_nothing_is_written(clock: Clock) -> None:
    store = FakeStore(clock)
    with pytest.raises(ProxyDispatchError) as raised:
        adapter(clock, store, context=context(clock, used=845)).complete(REQUEST)
    assert (raised.value.dispatch_class, raised.value.detail_fields) == (
        "not_sent", {"dependency": "executor_deadline"})
    assert store.events == []


def test_a_schema_the_validator_cannot_judge_is_refused_before_a_task_exists(clock: Clock) -> None:
    store = FakeStore(clock)
    body = {**REQUEST.body, "output_config": {"format": {"schema": {"allOf": []}}}}
    with pytest.raises(ProxyDispatchError) as raised:
        adapter(clock, store).complete(ModelRequest(model_id=MODEL, body=body))
    assert raised.value.dispatch_class == "not_sent" and store.events == []


def test_a_request_without_a_prompt_is_refused_before_a_task_exists(clock: Clock) -> None:
    store = FakeStore(clock)
    with pytest.raises(ProxyDispatchError):
        adapter(clock, store).complete(ModelRequest(model_id=MODEL, body={"messages": []}))
    assert store.events == []


def test_a_waiter_that_is_interrupted_withdraws_the_task(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        raise KeyboardInterrupt

    store = FakeStore(clock, script)
    with pytest.raises(KeyboardInterrupt):
        adapter(clock, store).complete(REQUEST)
    assert store.events == ["insert:run_call", "cancel"]


# -- «Проверить» ------------------------------------------------------------------------------


def test_the_probe_with_no_runner_online_says_so_after_the_claim_window(clock: Clock) -> None:
    store = FakeStore(clock)
    result = probe_pull(Sessions(), revision(), "epb_P", repository=store,  # type: ignore[arg-type]
                        monotonic=clock.monotonic, poll_seconds=5.0, claim_seconds=120,
                        answer_seconds=120)
    assert result.outcome == "no_runner_online" and result.reported_model is None
    assert 1120 <= clock.now < 1130
    assert store.inserted["origin"] == "probe" and store.inserted["probe_id"] == "epb_P"
    assert store.inserted["run_id"] is None and store.inserted["attempt_id"] is None
    assert store.events == ["insert:probe", "expire"]


def test_the_probe_answered_declares_the_model_and_is_ok(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if c.now >= 1030 and store.task and store.task.state == "open":
            store.claim()
        if c.now >= 1040 and store.task and store.task.state == "claimed":
            store.answered('{"echo": "x"}', MODEL, tokens=None)

    result = probe_pull(Sessions(), revision(), "epb_P", repository=FakeStore(clock, script),  # type: ignore[arg-type]
                        monotonic=clock.monotonic, poll_seconds=5.0)
    assert (result.outcome, result.reported_model, result.identity_basis) == ("ok", MODEL, "declared")
    assert result.rate_check == "not_metered"


def test_the_probe_of_a_metered_revision_does_not_claim_a_checked_rate(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if store.task and store.task.state == "open":
            store.claim()
            store.answered("{}", MODEL)

    result = probe_pull(Sessions(), revision(billing="metered"), "epb_P",  # type: ignore[arg-type]
                        repository=FakeStore(clock, script), monotonic=clock.monotonic)
    assert result.outcome == "ok" and result.rate_check == "not_reported"


def test_the_probe_claimed_but_never_answered_times_out(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if store.task and store.task.state == "open":
            store.claim()

    result = probe_pull(Sessions(), revision(), "epb_P", repository=FakeStore(clock, script),  # type: ignore[arg-type]
                        monotonic=clock.monotonic, poll_seconds=5.0, claim_seconds=60,
                        answer_seconds=60)
    assert result.outcome == "timeout" and 1119 <= clock.now < 1135


def test_the_probe_a_runner_reports_failed_is_a_protocol_error(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if store.task and store.task.state == "open":
            store.claim()
        elif store.task and store.task.state == "claimed":
            store.failed()

    result = probe_pull(Sessions(), revision(), "epb_P", repository=FakeStore(clock, script),  # type: ignore[arg-type]
                        monotonic=clock.monotonic)
    assert result.outcome == "protocol_error"


def test_the_probe_task_asks_for_a_fixed_echo_a_runner_can_give(clock: Clock) -> None:
    store = FakeStore(clock)
    probe_pull(Sessions(), revision(), "epb_P", repository=store, monotonic=clock.monotonic,  # type: ignore[arg-type]
               claim_seconds=1, answer_seconds=1, poll_seconds=1, nonce="abc123")
    assert store.payload is not None
    from auditmanager.executors.answers import read_answer

    assert store.payload["user_text"] == "abc123"
    assert read_answer(store.payload["output_schema"], '{"echo": "abc123"}') is None
    assert read_answer(store.payload["output_schema"], '{"echo": "other"}') is not None
