"""The retry policy, driven through ``execute_run`` against the real chain.

``P4-RUN-01`` lost three of seventeen live attempts to ``dependency_unavailable`` at ~133 s
each and retried them by hand in its own harness. ``P4_CLOSURE.md`` §1 accepted that retry
because the failure is transport, not judgement; §6 then required the policy to live in the
run executor rather than in each caller. This module is the evidence that it does, and that
it does only what §1's reasoning licenses.

Each test drives the whole chain — B1's rows, B2's stages, B4's gate, real PostgreSQL and
real MinIO — and asserts on what the **executor** did: how many times the provider was
asked, what was waited, what the database now says. None of them asserts a property of a
fixture. The provider is a scripted adapter rather than a recording, because a recording
cannot be made to fail twice and answer on the third try, which is the behaviour under
test; every scripted response that is not an outage comes from the committed recording, so
what publishes here is the same artifact the rest of the suite publishes.

Shown to fail
-------------
Every guard below was mutated and watched go red, then reverted and watched go green. The
mutations were applied to a copy of ``src/`` outside the worktree and run with
``pytest -o pythonpath=<copy>/src``; no tracked file was edited to produce them. What each
one changed, and which assertion caught it:

* ``RetryPolicy.retries`` returns ``False`` (nothing is retried) — ``adapter.calls == 2``
  failed as ``1 == 2``.
* ``RetryPolicy.retries`` returns ``error is not None`` (everything is retried) —
  ``adapter.calls == 1`` failed as ``3 == 1``.
* the loop's budget check stops one attempt early — ``adapter.calls == ATTEMPT_BUDGET``
  failed as ``2 == 3``.
* the exhausted branch replaces the outcome with ``analysis_failed`` —
  ``stage.error["code"]`` failed as ``analysis_failed != dependency_unavailable``.
* a fresh ``CostMeter`` is built per attempt — ``terminal_state == "failed"`` failed as
  ``published``, the run buying its way past a spent ceiling.
* ``metrics.update(attempts.metrics())`` removed — ``attempts[clean_run] == 1`` failed as
  ``None == 1``.
* ``ATTEMPT_BUDGET`` 3 -> 4 with a matching ladder — ``ATTEMPT_BUDGET == 3`` failed as
  ``4 == 3``.
* the catalog check dropped from ``RetryPolicy.__post_init__`` — ``pytest.raises(ValueError)``
  failed as DID NOT RAISE.
* the backoff is computed and never slept — ``waits == [BACKOFF_SECONDS[0]]`` failed as
  ``[] == [2.0]``.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import (
    CostMeter,
    ModelRequest,
    ModelResponse,
    ProviderMode,
)
from auditmanager.runs import (
    ATTEMPT_BUDGET,
    BACKOFF_SECONDS,
    RETRYABLE_STAGE_ERRORS,
    RetryPolicy,
    RunRepository,
    execute_run,
    start_audit_run,
)
from auditmanager.shared.errors import DomainError, ErrorCode

STAGE = "text_analysis"


class _ScriptedProvider:
    """A provider that is unreachable for the first ``outages`` calls, then answers.

    The outage is raised exactly as ``RecordedAdapter`` and ``LiveAdapter`` raise it: a
    ``DomainError`` carrying ``dependency_unavailable`` and the stable dependency class
    name. Nothing about it is special-cased by the executor, which sees only the typed
    error the stage hands back.
    """

    def __init__(self, inner, *, outages: int, reported_cost_usd: float | None = None):
        self._inner = inner
        self._outages = outages
        self._reported_cost_usd = reported_cost_usd
        self.calls = 0

    @property
    def provider_mode(self) -> ProviderMode:
        # A class-level constant on the real adapters. Recorded here too, so `execute_run`
        # sees the mode the run declares and this suite stays offline.
        return ProviderMode.RECORDED

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        if self.calls <= self._outages:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE,
                message="no model response is available for this request",
                dependency="model_provider",
            )
        response = self._inner.complete(request)
        if self._reported_cost_usd is None:
            return response
        return replace(response, reported_cost_usd=self._reported_cost_usd)


class _ModelAnsweredBadly:
    """A provider that answers, and whose answer is unusable.

    A reply cut short at the output ceiling that yields no usable observation is the
    stage's ``analysis_failed`` path. The model was reached and it produced output; the
    output is worthless. Asking again would re-ask a question that was already answered.
    """

    def __init__(self) -> None:
        self.calls = 0

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(
            output_text='{"observations": []}',
            stop_reason="max_tokens",
            input_tokens=4096,
            output_tokens=10,
            latency_ms=1200,
        )


def _start(session: Session, seeded, new_key, label: str) -> str:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key(label),
    )
    assert started.replayed is False
    return str(started.run_id)


def _stage_row(session: Session, run_id: str, stage_id: str = STAGE):
    for row in RunRepository().stage_results(session, run_id):
        if row.stage_id == stage_id:
            return row
    raise AssertionError(f"no {stage_id} stage result was persisted for {run_id}")


def _run_state(session: Session, run_id: str) -> str:
    return session.execute(
        text("SELECT state FROM audit_run WHERE run_id = :run_id"), {"run_id": run_id}
    ).scalar_one()


# --- the pins ----------------------------------------------------------------


def test_the_attempt_budget_and_backoff_are_pinned_and_agree():
    """The pins themselves, asserted as values rather than read back from the code.

    A test that imported the budget and compared it to itself would pass under any
    number. These are the figures ``P4-RUN-01``'s measurement justifies — three attempts,
    because every one of its three outages cleared on the next attempt, and waits that are
    small beside the ~133 s an outage took to surface. Changing them is a decision, and a
    decision should have to edit a test that states the old value.
    """
    assert ATTEMPT_BUDGET == 3
    assert BACKOFF_SECONDS == (2.0, 8.0)
    assert len(BACKOFF_SECONDS) == ATTEMPT_BUDGET - 1, (
        "every retry needs exactly one wait; a budget and a ladder that disagree leave "
        "one attempt's wait undefined"
    )
    assert {code.value for code in RETRYABLE_STAGE_ERRORS} == {"dependency_unavailable"}


def test_a_policy_cannot_be_built_over_a_code_the_catalog_calls_final():
    """The structural half of "never retry ``analysis_failed``".

    The refusal is not a comment and not a branch in the executor: the frozen catalog
    pins ``retryable`` per code, and a policy over a code it marks ``false`` does not
    construct. Every code in the policy is checked, so this holds for the eighteen other
    non-retryable codes too, not just the one named here.
    """
    with pytest.raises(ValueError) as refusal:
        RetryPolicy(retryable_errors=frozenset({ErrorCode.ANALYSIS_FAILED}))
    assert "analysis_failed" in str(refusal.value)

    assert ErrorCode.ANALYSIS_FAILED.retryable is False
    assert ErrorCode.DEPENDENCY_UNAVAILABLE.retryable is True

    # Narrower than the catalog on purpose: idempotency_key_in_progress is retryable and
    # is a command concern no executing stage can raise.
    assert ErrorCode.IDEMPOTENCY_KEY_IN_PROGRESS.retryable is True
    assert ErrorCode.IDEMPOTENCY_KEY_IN_PROGRESS not in RETRYABLE_STAGE_ERRORS


# --- the retry ---------------------------------------------------------------


def test_an_unreachable_provider_is_retried_and_the_run_still_publishes(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """The behaviour ``P4_CLOSURE.md`` §6 asked for, now inside the executor.

    One outage, then the recorded answer. The run publishes, the provider was asked
    twice, and the pinned first wait was taken once — the caller wrote no retry loop and
    supplied no attempt-suffixed key.
    """
    adapter = _ScriptedProvider(recorded_adapter, outages=1)
    waits: list[float] = []
    run_id = _start(session, seeded, new_key, "retry-then-publish")
    before = session.execute(
        text("SELECT command_id, frozen_input_digest FROM audit_run WHERE run_id = :r"),
        {"r": run_id},
    ).one()

    result = execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        sleep=waits.append,
    )

    assert adapter.calls == 2, (
        "the executor asked the provider once; a transport failure must be re-asked"
    )
    assert result.attempts == 2
    assert result.terminal_state == "published"
    assert result.published_finding_count > 0
    assert waits == [BACKOFF_SECONDS[0]], (
        "the one retry must wait the pinned first backoff, and the attempt that "
        "succeeded must not wait after it"
    )

    stage = _stage_row(session, run_id)
    assert stage.status == "succeeded"
    assert stage.metrics.get("attempts") == 2
    assert stage.metrics.get("retried_on_error_code") == "dependency_unavailable", (
        "the row must say why a second attempt happened, not merely that one did"
    )
    assert stage.metrics.get("attempt_budget_exhausted") is False

    # The retry is a loop inside one execution. It issues no second command, so the run's
    # identity is the one the single command created - unlike P4-RUN-01's harness, which
    # had a second command to suffix.
    after = session.execute(
        text("SELECT command_id, frozen_input_digest FROM audit_run WHERE run_id = :r"),
        {"r": run_id},
    ).one()
    assert tuple(after) == tuple(before)
    assert (
        session.execute(
            text("SELECT count(*) FROM audit_run WHERE version_uid = :v"),
            {"v": seeded.version_uid},
        ).scalar_one()
        == 1
    )


def test_the_model_answering_badly_is_never_retried(
    session: Session, seeded, blob_store, provider_config, new_key
):
    """``analysis_failed`` is the model having answered. It is asked once.

    Retrying it would re-ask an answered question and, over enough attempts, launder a
    bad answer into a good one — which is the reasoning ``P4_CLOSURE.md`` §1 rests its
    acceptance of the transport retry on.
    """
    adapter = _ModelAnsweredBadly()
    waits: list[float] = []
    run_id = _start(session, seeded, new_key, "bad-answer-not-retried")

    result = execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        sleep=waits.append,
    )

    assert adapter.calls == 1, (
        "the model answered; asking again re-asks a question that was answered"
    )
    assert result.attempts == 1
    assert waits == []
    assert result.terminal_state == "failed"

    stage = _stage_row(session, run_id)
    assert stage.status == "failed"
    assert stage.error is not None
    assert stage.error["code"] == ErrorCode.ANALYSIS_FAILED.value
    assert stage.metrics.get("attempts") == 1
    assert stage.metrics.get("retried_on_error_code") is None
    assert stage.metrics.get("attempt_budget_exhausted") is False, (
        "one attempt of three was used. The run failed, but it did not run out of "
        "attempts - it was refused a second one because the catalog marks this code not "
        "retryable. A definition keyed only on 'the last attempt failed' would report "
        "True here and make every count of exhausted budgets meaningless in the other "
        "direction"
    )


def test_the_budget_is_finite_and_its_exhaustion_reaches_a_terminal(
    session: Session, seeded, blob_store, provider_config, new_key
):
    """A provider that never returns costs the run its whole budget and no more.

    The run ends: it reaches a declared terminal rather than spinning, the stage keeps the
    transport code it actually failed with rather than being flattened into a generic
    analysis failure, and the row says the budget was spent.
    """
    adapter = _ScriptedProvider(None, outages=ATTEMPT_BUDGET + 5)
    waits: list[float] = []
    run_id = _start(session, seeded, new_key, "budget-exhausted")

    result = execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        sleep=waits.append,
    )

    assert adapter.calls == ATTEMPT_BUDGET, (
        f"the provider was asked {adapter.calls} times against a budget of "
        f"{ATTEMPT_BUDGET}; the loop must use the budget and stop at it"
    )
    assert result.attempts == ATTEMPT_BUDGET
    assert waits == list(BACKOFF_SECONDS), (
        "each retry waits its own pinned backoff, in order, and the first attempt waits "
        "for nothing"
    )

    assert result.terminal_state == "failed"
    assert _run_state(session, run_id) == "failed", "the run must reach a terminal state"
    assert STAGE in result.degradation_set

    stage = _stage_row(session, run_id)
    assert stage.status == "failed"
    assert stage.error is not None
    assert stage.error["code"] == ErrorCode.DEPENDENCY_UNAVAILABLE.value, (
        "an exhausted budget must still report the transport failure it exhausted "
        "itself against; an operator reading analysis_failed has no reason to retry"
    )
    assert stage.metrics.get("attempts") == ATTEMPT_BUDGET
    assert stage.metrics.get("attempt_budget") == ATTEMPT_BUDGET
    assert stage.metrics.get("attempt_budget_exhausted") is True

    # No model_call row: `complete()` raised, so no response exists to record one from.
    # P4_CLOSURE section 1 cites exactly this - `model_call_rows: 0` per failed attempt -
    # as the evidence that the failures were preserved rather than swallowed.
    assert (
        session.execute(
            text("SELECT count(*) FROM model_call WHERE run_id = :r"), {"r": run_id}
        ).scalar_one()
        == 0
    )


# --- the money ---------------------------------------------------------------


def test_the_cost_ceiling_binds_across_attempts_not_per_attempt(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """``OD-03``'s per-run ceiling is a property of the run. A retry does not refill it.

    Both halves run the same script — one outage, then an answer the transport bills at
    USD 0.50 — against the same USD 1.00 ceiling. The only difference is what the run had
    already spent when the retry happened. A run that had spent 0.90 halts on
    ``cost_budget_exceeded``; a run that had spent nothing publishes. If each attempt were
    metered separately the first would publish too, because its second attempt would begin
    at zero.
    """
    spent_run = _start(session, seeded, new_key, "ceiling-across-attempts")
    spent_adapter = _ScriptedProvider(recorded_adapter, outages=1, reported_cost_usd=0.50)
    meter = CostMeter(ceiling_usd=1.00, spent_usd=0.90)

    spent_result = execute_run(
        session,
        spent_run,
        blob_store=blob_store,
        adapter=spent_adapter,
        provider_config=provider_config,
        cost_meter=meter,
        sleep=lambda _seconds: None,
    )

    assert spent_adapter.calls == 2
    assert spent_result.attempts == 2
    assert spent_result.terminal_state == "failed"
    stage = _stage_row(session, spent_run)
    assert stage.error is not None
    assert stage.error["code"] == ErrorCode.COST_BUDGET_EXCEEDED.value, (
        "the retried attempt spent against the run's budget, so the run must halt; a "
        "per-attempt budget would have let it through"
    )
    assert meter.spent_usd == pytest.approx(1.40), (
        "the meter carries the whole run's spend, earlier attempts included"
    )
    assert stage.metrics.get("cost_usd") == pytest.approx(1.40)

    # The control: the same script, the same ceiling, nothing spent beforehand.
    fresh_run = _start(session, seeded, new_key, "ceiling-with-room")
    fresh_adapter = _ScriptedProvider(recorded_adapter, outages=1, reported_cost_usd=0.50)
    fresh_result = execute_run(
        session,
        fresh_run,
        blob_store=blob_store,
        adapter=fresh_adapter,
        provider_config=provider_config,
        cost_meter=CostMeter(ceiling_usd=1.00),
        sleep=lambda _seconds: None,
    )
    assert fresh_adapter.calls == 2
    assert fresh_result.terminal_state == "published", (
        "0.50 against a 1.00 ceiling publishes; the halt above is the accumulated "
        "spend and not the cost of the call"
    )


# --- the provenance ----------------------------------------------------------


def test_a_later_reader_can_tell_a_first_try_success_from_a_retried_one(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """The alternative-headline property, recomputed from the database alone.

    ``P4_CLOSURE.md`` §1 kept its ruling falsifiable by leaving the failed attempts
    visible, so anyone who disagreed could recompute 12/14 instead of 14/14. The executor
    must not lose that when it takes the retry in-process: this recomputes the same
    quantity over two runs, from the persisted rows, with no help from this process's
    memory.
    """
    clean_run = _start(session, seeded, new_key, "headline-clean")
    execute_run(
        session,
        clean_run,
        blob_store=blob_store,
        adapter=_ScriptedProvider(recorded_adapter, outages=0),
        provider_config=provider_config,
        sleep=lambda _seconds: None,
    )
    retried_run = _start(session, seeded, new_key, "headline-retried")
    execute_run(
        session,
        retried_run,
        blob_store=blob_store,
        adapter=_ScriptedProvider(recorded_adapter, outages=1),
        provider_config=provider_config,
        sleep=lambda _seconds: None,
    )

    rows = session.execute(
        text(
            """
            SELECT r.run_id, r.state, (s.metrics ->> 'attempts')::int AS attempts
              FROM audit_run r
              JOIN stage_result s ON s.run_id = r.run_id AND s.stage_id = :stage
             WHERE r.run_id IN (:clean, :retried)
            """
        ),
        {"stage": STAGE, "clean": clean_run, "retried": retried_run},
    ).all()
    attempts = {row.run_id: row.attempts for row in rows}
    states = {row.run_id: row.state for row in rows}

    assert states == {clean_run: "published", retried_run: "published"}
    assert attempts[clean_run] == 1
    assert attempts[retried_run] == 2

    published = [run for run, state in states.items() if state == "published"]
    without_a_retry = [run for run in published if attempts[run] == 1]
    assert (len(without_a_retry), len(published)) == (1, 2), (
        "this is the 12/14-vs-14/14 computation in miniature: the published count and "
        "the published-without-a-retry count are both queries, not recollections"
    )


def test_a_success_on_the_last_allowed_attempt_did_not_exhaust_the_budget(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """Using every attempt is not the same as running out of them.

    ``W5-ADV`` found that ``attempt_budget_exhausted`` was ``attempts >= attempt_budget``
    and never asked whether the last attempt *failed*. A run that answered on its final
    allowed try therefore published **and** recorded the budget as exhausted, so any query
    counting exhausted budgets — the reason the field is persisted at all — silently
    included successful runs.

    The existing guards could not see it: the success case asserts ``False`` at
    ``attempts == 2``, one short of the budget, and the failure case asserts ``True`` at
    ``attempts == 3``. Both agree with the broken definition and the correct one. This is
    the case that separates them.
    """
    adapter = _ScriptedProvider(recorded_adapter, outages=ATTEMPT_BUDGET - 1)
    waits: list[float] = []
    run_id = _start(session, seeded, new_key, "succeeds-on-the-last-attempt")

    result = execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        sleep=waits.append,
    )

    # -- the precondition: this run really did use its whole budget and still publish.
    assert adapter.calls == ATTEMPT_BUDGET
    assert result.attempts == ATTEMPT_BUDGET
    assert waits == list(BACKOFF_SECONDS), "every pinned backoff was taken, in order"
    assert result.terminal_state == "published", (
        "the last allowed attempt answered, so the run must publish; without this the "
        "assertion below would be about a failed run and would prove nothing"
    )

    stage = _stage_row(session, run_id)
    assert stage.status == "succeeded"
    assert stage.metrics.get("attempts") == ATTEMPT_BUDGET

    # -- the claim.
    assert stage.metrics.get("attempt_budget_exhausted") is False, (
        "the run answered on its last allowed attempt, so the budget was spent but not "
        "exhausted: nothing was left undone for want of another try. Reporting True here "
        "puts published runs into every count of exhausted budgets"
    )
