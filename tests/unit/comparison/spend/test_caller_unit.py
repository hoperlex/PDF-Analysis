"""The protocol of a comparison model call (`CMP-SPEND-01`), against a recording stand-in for the database.

Container-free: a fake session factory and a fake journal write every step into one log, so the order the
ADR demands is an assertion on a list -- the ``prepared`` row is **committed before the adapter is called**,
the adapter is called **once**, a refusal that needs no database touches none. The journal's own rules (the
states, the edges, the SQL) are proved on a real PostgreSQL in ``tests/integration/comparison/spend``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin, ModelRequest, ModelResponse, ProviderMode, ProxyDispatchError
from auditmanager.comparison.spend import errors
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.model import CallEstimate, CallRoute, Consent, Spend
from auditmanager.comparison.spend.repository import ComparisonSpendRepository
from auditmanager.shared.errors import DomainError, ErrorCode

DIGEST = "ef" * 32
REVISION = "excr_01"
MODEL = "claude-opus-5"
GATEWAY = "anthropic/claude-opus-5"
#: USD 1 per million input tokens and USD 5 per million output tokens: a 1 000 000-token reply costs USD 5.
PIN = ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=5.0)
ESTIMATE = CallEstimate(input_tokens=1_000_000, output_tokens=200_000)       # USD 2.00


class Log(list):  # type: ignore[type-arg]
    def at(self, name: str) -> list[int]:
        return [i for i, entry in enumerate(self) if (entry[0] if isinstance(entry, tuple) else entry) == name]


class FakeSession:
    def __init__(self, log: Log) -> None:
        self.log = log

    def __enter__(self) -> "FakeSession":
        self.log.append("open")
        return self

    def __exit__(self, *exc: object) -> bool:
        self.log.append("close")
        return False

    def commit(self) -> None:
        self.log.append("commit")


class FakeRepository(ComparisonSpendRepository):
    """Records every journal operation; answers what the scenario says."""

    def __init__(
        self, log: Log, *, job: Spend | tuple[Spend, ...] = Spend(0, 0), day: Spend = Spend(0, 0),
        active_run: bool = False,
        active_call: bool = False, other_open: int = 0, changed: bool = True, sent: bool = True,
        connection: str | None = "exc_01",
    ) -> None:
        # ``job`` may be a sequence: each read of the job's spend takes the next one (the last repeats), so a
        # test can say what the journal holds before the call and what it holds after.
        self.log, self.jobs, self.day = log, list(job) if isinstance(job, tuple) else [job], day
        self.active_run, self.active_call, self.other_open = active_run, active_call, other_open
        self.changed, self.sent, self.connection = changed, sent, connection

    def open_calls_of_other_attempts(self, session: Any, **kw: Any) -> int:
        self.log.append("other_attempts")
        return self.other_open

    def connection_of(self, session: Any, revision_id: str) -> str | None:
        self.log.append("connection_of")
        return self.connection

    def lock_connection(self, session: Any, connection_id: str) -> None:
        self.log.append("lock_connection")

    def lock_day(self, session: Any) -> None:
        self.log.append("lock_day")

    def connection_has_active_run(self, session: Any, connection_id: str) -> bool:
        self.log.append("active_run?")
        return self.active_run

    def connection_has_active_call(self, session: Any, connection_id: str) -> bool:
        self.log.append("active_call?")
        return self.active_call

    def job_spend(self, session: Any, **kw: Any) -> Spend:
        self.log.append(("job_spend", kw["job_id"]))
        return self.jobs.pop(0) if len(self.jobs) > 1 else self.jobs[0]

    def day_spend(self, session: Any) -> Spend:
        self.log.append("day_spend")
        return self.day

    def settle_abandoned(self, session: Any, **kw: Any) -> int:
        self.log.append("settle_abandoned")
        return 0

    def prepare(self, session: Any, **kw: Any) -> str:
        self.log.append(("prepare", kw))
        return "cmc_01"

    def mark_sent(self, session: Any, call_id: str) -> bool:
        self.log.append("mark_sent")
        return self.sent

    def complete(self, session: Any, call_id: str, **kw: Any) -> bool:
        self.log.append(("complete", kw))
        return self.changed

    def fail(self, session: Any, call_id: str, **kw: Any) -> bool:
        self.log.append(("fail", kw))
        return self.changed

    def mark_unknown(self, session: Any, call_id: str, **kw: Any) -> bool:
        self.log.append(("unknown", kw))
        return self.changed


class FakeItem:
    """What the caller reads of a ``WorkItem``."""

    def __init__(self, log: Log, *, payload: dict[str, Any] | None = None, stale: bool = False) -> None:
        self.log, self.stale = log, stale
        self.work_id, self.attempt_id, self.project_uid = "cq_01", "cqa_01", "prj_01"
        self.kind, self.payload = "comparison_pair_check", payload or {}

    def require_current(self, session: Any) -> None:
        self.log.append("require_current")
        if self.stale:
            raise DomainError(ErrorCode.STALE_ATTEMPT)


class Adapter:
    """The model seam: ``provider_mode`` is a property, ``complete`` writes ``adapter`` into the log."""

    def __init__(
        self, log: Log, *, mode: ProviderMode = ProviderMode.LIVE, reply: ModelResponse | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.log, self._mode, self.reply, self.error, self.calls = log, mode, reply, error, 0

    @property
    def provider_mode(self) -> ProviderMode:
        return self._mode

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        self.log.append("adapter")
        if self.error is not None:
            raise self.error
        assert self.reply is not None
        return self.reply


def _reply(*, model: str | None = GATEWAY, cost: float | None = None, tokens: tuple[int, int] = (500_000, 100_000)) -> ModelResponse:
    return ModelResponse(
        output_text="{}", stop_reason="end_turn", input_tokens=tokens[0], output_tokens=tokens[1],
        latency_ms=1200, reported_cost_usd=cost, model=model,
    )


def _consent(**over: object) -> Consent:
    values: dict[str, Any] = {
        "estimate_digest": DIGEST, "estimate_usd": 5.0, "ceiling_usd": 10.0,
        "connection_revision_id": REVISION, "pinned_model": MODEL,
    }
    values.update(over)
    return Consent(**values)


def _request() -> ModelRequest:
    return ModelRequest(model_id=MODEL, body={"model": MODEL, "messages": [{"role": "user", "content": "x"}]})


def _route(adapter: Adapter, **over: Any) -> CallRoute:
    values: dict[str, Any] = {
        "adapter": adapter, "model_identity": MODEL, "connection_revision_id": REVISION,
        "expected_model": GATEWAY, "check_identity": True, "unmetered": False, "pin": PIN,
    }
    values.update(over)
    return CallRoute(**values)


def _make(log: Log, **repo: Any) -> ComparisonModelCaller:
    return ComparisonModelCaller(lambda: FakeSession(log), repository=FakeRepository(log, **repo))  # type: ignore[arg-type]


def _call(caller: ComparisonModelCaller, item: FakeItem, route: CallRoute, consent: Consent | None = None) -> Any:
    return caller.call(item, route, _request(), estimate=ESTIMATE, consent=consent or _consent())  # type: ignore[arg-type]


def _prepare_kwargs(log: Log) -> dict[str, Any]:
    return next(entry[1] for entry in log if isinstance(entry, tuple) and entry[0] == "prepare")


def _journal(log: Log, name: str) -> dict[str, Any]:
    return next(entry[1] for entry in log if isinstance(entry, tuple) and entry[0] == name)


# --- the order: prepared is committed before the adapter is called ----------------------------------------


def test_the_prepared_row_is_committed_before_the_adapter_is_called_and_the_adapter_once() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    _call(_make(log), FakeItem(log), _route(adapter))
    assert adapter.calls == 1
    first_prepare, first_sent, call = log.at("prepare")[0], log.at("mark_sent")[0], log.at("adapter")[0]
    commit_after_prepare = next(i for i in log.at("commit") if i > first_prepare)
    commit_after_sent = next(i for i in log.at("commit") if i > first_sent)
    assert first_prepare < commit_after_prepare < first_sent < commit_after_sent < call
    # And what ends the call is written after it, in a transaction of its own.
    assert log.at("complete")[0] > call and any(i > log.at("complete")[0] for i in log.at("commit"))


def test_a_stale_attempt_is_refused_before_anything_is_prepared() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallLost):
        _call(_make(log), FakeItem(log, stale=True), _route(adapter))
    assert adapter.calls == 0 and not log.at("prepare") and not log.at("commit")


def test_a_call_whose_row_is_no_longer_prepared_is_not_sent() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallLost):
        _call(_make(log, sent=False), FakeItem(log), _route(adapter))
    assert adapter.calls == 0
    # The unsent row is ended ``failed``: the wrapper knows nothing was sent.
    assert _journal(log, "fail")["error_code"] == errors.REASON_LEASE_LOST


# --- what needs no database ---------------------------------------------------------------------------------


def _assert_refused_before_any_database(log: Log, adapter: Adapter, reason: str) -> None:
    assert adapter.calls == 0
    assert not [entry for entry in log if entry not in ("open", "close")], log
    assert reason


def test_a_live_call_without_a_consent_is_refused_before_the_database() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    caller = _make(log)
    with pytest.raises(errors.CallRefused) as refusal:
        caller.call(FakeItem(log), _route(adapter), _request(), estimate=ESTIMATE, consent=None)  # type: ignore[arg-type]
    assert refusal.value.reason == errors.REASON_CONSENT_REQUIRED and refusal.value.pauses_job
    _assert_refused_before_any_database(log, adapter, refusal.value.reason)


@pytest.mark.parametrize("change", [{"connection_revision_id": "excr_OTHER"}, {"pinned_model": "claude-sonnet-5"}])
def test_a_consent_given_for_another_revision_or_model_pauses_the_job(change: dict[str, str]) -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallRefused) as refusal:
        _call(_make(log), FakeItem(log), _route(adapter), _consent(**change))
    assert refusal.value.reason == errors.REASON_CONSENT_STALE and refusal.value.pauses_job
    _assert_refused_before_any_database(log, adapter, refusal.value.reason)


@pytest.mark.parametrize("expected", [None, "", "  ", "proxy", "default", "auto", "AUTO"])
def test_a_reply_that_cannot_be_held_to_a_model_fails_closed_before_the_call(expected: str | None) -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallRefused) as refusal:
        _call(_make(log), FakeItem(log), _route(adapter, expected_model=expected))
    assert refusal.value.reason == errors.REASON_MODEL_NOT_SELECTED
    _assert_refused_before_any_database(log, adapter, refusal.value.reason)


def test_a_route_that_does_not_check_identity_is_not_held_to_a_name() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply(model=None))
    _call(_make(log), FakeItem(log), _route(adapter, check_identity=False, expected_model=None))
    assert adapter.calls == 1


def test_the_mode_is_read_from_the_adapter_not_from_the_route() -> None:
    log = Log()
    recorded = Adapter(log, mode=ProviderMode.RECORDED, reply=_reply(model=None))
    # The route claims it is metered and carries a pin; the adapter says it is a replay.
    result = _call(_make(log), FakeItem(log), _route(recorded, unmetered=False), consent=None)
    prepared = _prepare_kwargs(log)
    assert prepared["provider_mode"] == "recorded" and prepared["model_identity"] == "recorded"
    assert prepared["estimate_micros"] == 0
    assert result.cost_basis == "unmetered" and result.cost_micros == 0
    assert "lock_day" not in log and "day_spend" not in log


def test_a_mode_that_is_neither_live_nor_recorded_is_refused() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    adapter._mode = SimpleNamespace(value="hybrid")  # type: ignore[assignment]
    with pytest.raises(ValueError):
        _call(_make(log), FakeItem(log), _route(adapter))
    assert adapter.calls == 0


def test_a_live_metered_route_must_carry_the_rates_to_price_the_call() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(ValueError):
        _call(_make(log), FakeItem(log), _route(adapter, pin=None))
    assert adapter.calls == 0 and not log.at("prepare")


# --- the connection's single user ------------------------------------------------------------------------------


def test_the_connection_lock_is_taken_before_the_connection_is_asked_and_before_the_row_is_prepared() -> None:
    log = Log()
    _call(_make(log), FakeItem(log), _route(Adapter(log, reply=_reply())))
    lock, run, call, prepare = (log.at(n)[0] for n in ("lock_connection", "active_run?", "active_call?", "prepare"))
    assert lock < run < call < prepare


@pytest.mark.parametrize("busy", [{"active_run": True}, {"active_call": True}])
def test_a_busy_connection_is_a_wait_and_sends_nothing(busy: dict[str, bool]) -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallRefused) as refusal:
        _call(_make(log, **busy), FakeItem(log), _route(adapter))
    assert refusal.value.reason == errors.REASON_CONNECTION_BUSY and refusal.value.pauses_job is False
    assert adapter.calls == 0 and not log.at("prepare")
    outcome = refusal.value.as_outcome()
    assert type(outcome).__name__ == "Yielded"


def test_a_replay_has_no_connection_and_takes_no_connection_lock() -> None:
    log = Log()
    replay = Adapter(log, mode=ProviderMode.RECORDED, reply=_reply(model=None))
    _call(_make(log), FakeItem(log), _route(replay, connection_revision_id=None), consent=None)  # type: ignore[arg-type]
    assert "lock_connection" not in log and "connection_of" not in log


def test_a_live_call_over_a_route_with_no_connection_does_not_match_any_consent() -> None:
    """Comparison model work goes through the executor connections only (decision 17)."""
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallRefused) as refusal:
        _call(_make(log), FakeItem(log), _route(adapter, connection_revision_id=None))
    assert refusal.value.reason == errors.REASON_CONSENT_STALE and adapter.calls == 0


def test_a_revision_that_does_not_exist_is_refused_loudly() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(ValueError):
        _call(_make(log, connection=None), FakeItem(log), _route(adapter))
    assert adapter.calls == 0


def test_an_earlier_attempts_open_call_blocks_every_new_send_of_the_item() -> None:
    """The belt of decision 5: if the settler did not run, the next attempt still sends nothing."""
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallRefused) as refusal:
        _call(_make(log, other_open=1), FakeItem(log), _route(adapter))
    assert refusal.value.reason == errors.REASON_UNSETTLED_CALL
    assert adapter.calls == 0 and not log.at("prepare") and "lock_connection" not in log


# --- the ceilings are decided before the call --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spend", "estimate_usd", "reason"),
    [
        ({"job": Spend(9_000_001, 0)}, 9.0, errors.REASON_JOB_CEILING),             # 9.000001 + 2.00 > 10
        ({"day": Spend(48_000_001, 0)}, 5.0, errors.REASON_DAY_CEILING),            # 48.000001 + 2.00 > 50
        ({"job": Spend(6_000_001, 0)}, 5.0, errors.REASON_OVERRUN),                 # > 1.2 x 5.00
    ],
)
def test_a_ceiling_refuses_before_the_row_is_prepared_and_before_the_adapter_is_called(
    spend: dict[str, Spend], estimate_usd: float, reason: str,
) -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallRefused) as refusal:
        _call(_make(log, **spend), FakeItem(log), _route(adapter), consent=_consent(estimate_usd=estimate_usd))
    assert refusal.value.reason == reason and refusal.value.pauses_job
    assert adapter.calls == 0 and not log.at("prepare") and "mark_sent" not in log


def test_the_ceilings_are_decided_under_the_installation_lock_and_before_the_insert() -> None:
    log = Log()
    _call(_make(log), FakeItem(log), _route(Adapter(log, reply=_reply())))
    assert log.at("lock_day")[0] < log.at("day_spend")[0] < log.at("prepare")[0]


def test_a_call_exactly_at_a_ceiling_is_allowed() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    _call(_make(log, job=Spend(8_000_000, 0), day=Spend(48_000_000, 0)), FakeItem(log), _route(adapter),
          consent=_consent(estimate_usd=8.0))
    assert adapter.calls == 1


def test_the_estimate_is_priced_from_the_pinned_rates_not_chosen_by_the_caller() -> None:
    log = Log()
    _call(_make(log), FakeItem(log), _route(Adapter(log, reply=_reply())))
    # 1 000 000 input tokens at USD 1/M plus 200 000 output tokens at USD 5/M.
    assert _prepare_kwargs(log)["estimate_micros"] == 2_000_000


def test_the_job_is_the_ai_job_of_the_payload_or_the_item_itself() -> None:
    for payload, expected in (({"ai_job_id": "job-7"}, "job-7"), ({}, None)):
        log = Log()
        _call(_make(log), FakeItem(log, payload=payload), _route(Adapter(log, reply=_reply())))
        assert log.at("job_spend") and next(e for e in log if isinstance(e, tuple) and e[0] == "job_spend")[1] == expected


@pytest.mark.parametrize("bad", [7, "", "x" * 129, ["a"]])
def test_a_malformed_job_key_is_refused_not_ignored(bad: object) -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(ValueError):
        _call(_make(log), FakeItem(log, payload={"ai_job_id": bad}), _route(adapter))
    assert adapter.calls == 0


# --- not_metered is not limited by money -----------------------------------------------------------------------


def test_a_not_metered_connection_is_not_limited_by_money() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply(cost=3.0))
    rich = {"job": Spend(99_000_000, 99_000_000), "day": Spend(999_000_000, 999_000_000)}
    result = _call(_make(log, **rich), FakeItem(log), _route(adapter, unmetered=True, pin=None))
    assert adapter.calls == 1
    assert _prepare_kwargs(log)["estimate_micros"] == 0
    assert (result.cost_basis, result.cost_micros) == ("unmetered", 0)
    assert result.pause is None
    for step in ("lock_day", "day_spend"):
        assert step not in log, step
    assert not [e for e in log if isinstance(e, tuple) and e[0] == "job_spend"]


def test_a_not_metered_call_still_needs_a_consent_for_its_route() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallRefused) as refusal:
        _call(_make(log), FakeItem(log), _route(adapter, unmetered=True, pin=None),
              consent=_consent(pinned_model="other"))
    assert refusal.value.reason == errors.REASON_CONSENT_STALE


# --- the cost of a completed call and the pause after it ---------------------------------------------------------


def test_a_reported_cost_is_measured_and_a_missing_one_is_estimated_from_the_pin() -> None:
    log = Log()
    result = _call(_make(log), FakeItem(log), _route(Adapter(log, reply=_reply(cost=0.4321))))
    assert (result.cost_basis, result.cost_micros) == ("measured", 432_100)
    log = Log()
    result = _call(_make(log), FakeItem(log), _route(Adapter(log, reply=_reply(cost=None))))
    # 500 000 input at USD 1/M + 100 000 output at USD 5/M = 1.00
    assert (result.cost_basis, result.cost_micros) == ("estimated", 1_000_000)
    done = _journal(log, "complete")
    assert (done["cost_basis"], done["cost_micros"], done["input_tokens"], done["output_tokens"]) == (
        "estimated", 1_000_000, 500_000, 100_000)


@pytest.mark.parametrize("unusable", [float("nan"), float("inf"), -0.5])
def test_an_unusable_reported_cost_is_not_trusted_and_the_call_is_priced_from_the_pin(unusable: float) -> None:
    log = Log()
    result = _call(_make(log), FakeItem(log), _route(Adapter(log, reply=_reply(cost=unusable))))
    assert (result.cost_basis, result.cost_micros) == ("estimated", 1_000_000)


def test_a_call_that_takes_the_job_over_one_point_two_times_its_estimate_returns_its_reply_and_a_pause() -> None:
    log = Log()
    reply = _reply(cost=1.0)
    # Before the call the job has spent 5.50 (inside 1.2 x 5.00); the journal read after it says 6.50.
    result = _call(_make(log, job=(Spend(5_500_000, 0), Spend(6_500_000, 0))), FakeItem(log),
                   _route(Adapter(log, reply=reply)), consent=_consent(estimate_usd=5.0))
    assert result.response is reply
    assert result.pause is not None and result.pause.reason == errors.REASON_OVERRUN


def test_a_call_inside_its_budget_has_no_pause() -> None:
    log = Log()
    result = _call(_make(log, job=Spend(1_000_000, 0)), FakeItem(log), _route(Adapter(log, reply=_reply(cost=1.0))))
    assert result.pause is None


# --- failures: what the transport proves decides the row -------------------------------------------------------


def _dispatch_error(dispatch_class: str, *, retry_safe: bool = False, received: Any = None,
                    code: ErrorCode = ErrorCode.DEPENDENCY_UNAVAILABLE, **details: Any) -> ProxyDispatchError:
    return ProxyDispatchError(code, dispatch_class=dispatch_class, retry_safe=retry_safe, received=received,
                              details=details or None)


@pytest.mark.parametrize("dispatch_class", ["not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"])
def test_an_error_proven_to_precede_processing_ends_failed_without_a_cost(dispatch_class: str) -> None:
    log = Log()
    adapter = Adapter(log, error=_dispatch_error(dispatch_class, retry_safe=True))
    with pytest.raises(errors.CallFailed) as failure:
        _call(_make(log), FakeItem(log), _route(adapter))
    failed = _journal(log, "fail")
    assert failed["error_code"] == "dependency_unavailable"
    assert failed.get("cost_micros") is None and failed.get("cost_basis") is None
    assert failure.value.retry_safe is True and failure.value.call_id == "cmc_01"
    assert adapter.calls == 1


def test_an_unproven_outcome_is_unknown_and_is_never_sent_again_here() -> None:
    log = Log()
    adapter = Adapter(log, error=_dispatch_error("outcome_unknown"))
    caller = _make(log)
    with pytest.raises(errors.OutcomeUnknown) as unknown:
        _call(caller, FakeItem(log), _route(adapter))
    assert _journal(log, "unknown")["error_code"] == "dependency_unavailable"
    assert adapter.calls == 1, "the wrapper must never retry"
    assert unknown.value.as_outcome().reason == errors.REASON_SPEND_UNKNOWN


def test_an_answer_that_arrived_but_could_not_be_used_is_failed_with_the_cost_it_may_have_charged() -> None:
    log = Log()
    received = SimpleNamespace(response_sha256="aa" * 32, input_tokens=500_000, output_tokens=100_000, latency_ms=900)
    adapter = Adapter(log, error=_dispatch_error("outcome_unknown", received=received, code=ErrorCode.ANALYSIS_FAILED))
    with pytest.raises(errors.CallFailed) as failure:
        _call(_make(log), FakeItem(log), _route(adapter))
    failed = _journal(log, "fail")
    assert failed["error_code"] == "analysis_failed" and failed["response_sha256"] == "aa" * 32
    assert (failed["cost_basis"], failed["cost_micros"]) == ("estimated", 1_000_000)
    assert failure.value.retry_safe is False


def test_an_unusable_answer_through_a_not_metered_route_is_failed_with_an_unmetered_zero() -> None:
    log = Log()
    received = SimpleNamespace(response_sha256="aa" * 32, input_tokens=5, output_tokens=5, latency_ms=1)
    adapter = Adapter(log, error=_dispatch_error("outcome_unknown", received=received, code=ErrorCode.ANALYSIS_FAILED))
    with pytest.raises(errors.CallFailed):
        _call(_make(log), FakeItem(log), _route(adapter, unmetered=True, pin=None))
    failed = _journal(log, "fail")
    assert (failed["cost_basis"], failed["cost_micros"]) == ("unmetered", 0)


def test_an_unexpected_fault_of_a_live_adapter_is_unknown_not_a_crash_that_leaves_the_row_sent() -> None:
    log = Log()
    adapter = Adapter(log, error=RuntimeError("socket exploded"))
    with pytest.raises(errors.OutcomeUnknown):
        _call(_make(log), FakeItem(log), _route(adapter))
    assert _journal(log, "unknown")["error_code"] == "adapter_fault"
    assert adapter.calls == 1


def test_an_error_of_a_recorded_adapter_is_failed_never_unknown() -> None:
    log = Log()
    adapter = Adapter(log, mode=ProviderMode.RECORDED, error=_dispatch_error("outcome_unknown"))
    with pytest.raises(errors.CallFailed):
        _call(_make(log), FakeItem(log), _route(adapter), consent=None)  # type: ignore[arg-type]
    assert not log.at("unknown")


def test_a_process_killed_mid_call_leaves_the_row_sent_for_the_reclaim_and_records_nothing() -> None:
    class Killed(BaseException):
        """What a kill is to the call: not an ``Exception``."""

    log = Log()
    adapter = Adapter(log, error=Killed())
    with pytest.raises(Killed):
        _call(_make(log), FakeItem(log), _route(adapter))
    assert log.at("mark_sent") and not log.at("complete") and not log.at("unknown") and not log.at("fail")


def test_a_runner_that_refused_the_images_is_unknown_on_a_metered_route_and_failed_on_a_free_one() -> None:
    refusal = _dispatch_error("outcome_unknown", dependency="executor_image_input_unsupported")
    log = Log()
    with pytest.raises(errors.OutcomeUnknown):
        _call(_make(log), FakeItem(log), _route(Adapter(log, error=refusal)))
    assert _journal(log, "unknown")["error_code"] == errors.REASON_IMAGES_UNSUPPORTED
    log = Log()
    with pytest.raises(errors.CallFailed) as failure:
        _call(_make(log), FakeItem(log), _route(Adapter(log, error=refusal), unmetered=True, pin=None))
    assert failure.value.reason == errors.REASON_IMAGES_UNSUPPORTED
    assert _journal(log, "fail")["error_code"] == errors.REASON_IMAGES_UNSUPPORTED and not log.at("unknown")


# --- R-133: a reply from another model is a typed refusal ---------------------------------------------------------


@pytest.mark.parametrize("reported", ["anthropic/claude-sonnet-5", None, "", "Anthropic/claude-opus-5", GATEWAY + " "])
def test_a_reply_from_another_model_or_none_is_refused_recorded_with_its_cost_and_not_returned(
    reported: str | None,
) -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply(model=reported, cost=0.25))
    with pytest.raises(errors.CallFailed) as failure:
        _call(_make(log), FakeItem(log), _route(adapter))
    assert failure.value.reason == errors.REASON_MODEL_IDENTITY
    failed = _journal(log, "fail")
    assert failed["error_code"] == "model_identity_mismatch"
    # The answer was paid for: its cost stays in the books.
    assert (failed["cost_basis"], failed["cost_micros"]) == ("measured", 250_000)
    assert not log.at("complete")


def test_the_gateway_name_may_carry_surrounding_blanks_in_the_configuration_only() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply(model=GATEWAY))
    _call(_make(log), FakeItem(log), _route(adapter, expected_model=f"  {GATEWAY}  "))
    assert adapter.calls == 1 and log.at("complete")


# --- a settled row is not overwritten ---------------------------------------------------------------------------


def test_a_reply_that_arrives_after_the_reclaim_settled_the_row_is_lost_not_published() -> None:
    log = Log()
    adapter = Adapter(log, reply=_reply())
    with pytest.raises(errors.CallLost) as lost:
        _call(_make(log, changed=False), FakeItem(log), _route(adapter))
    assert lost.value.call_id == "cmc_01" and adapter.calls == 1


def test_every_error_names_the_outcome_a_handler_returns() -> None:
    from auditmanager.comparison.work.model import Failed, Yielded

    assert errors.CallRefused(errors.REASON_JOB_CEILING, pauses_job=True).as_outcome() == Failed("job_ceiling")
    assert errors.CallRefused(errors.REASON_CONNECTION_BUSY, pauses_job=False).as_outcome() == Yielded(
        errors.BUSY_RETRY_SECONDS)
    assert errors.CallFailed("dependency_unavailable", call_id="c", retry_safe=True).as_outcome() == Failed(
        "dependency_unavailable", retry=True)
    assert errors.CallFailed("analysis_failed", call_id="c").as_outcome() == Failed("analysis_failed", retry=False)
    assert errors.OutcomeUnknown(call_id="c").as_outcome() == Failed("spend_unknown")
    assert errors.CallLost(call_id=None).as_outcome() == Failed("lease_lost")


def test_a_reason_is_a_code_a_work_item_can_store() -> None:
    from auditmanager.comparison.work.model import REASON_PATTERN

    for name in dir(errors):
        if name.startswith("REASON_"):
            assert REASON_PATTERN.match(getattr(errors, name)), name
