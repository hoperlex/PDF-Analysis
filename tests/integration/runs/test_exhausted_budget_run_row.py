"""What the **run row** says after the attempt budget is spent, and by which route.

`W5-ADV` was dispatched on the premise that this was a seam nobody had covered: that
`test_retry_policy.py`'s `test_the_budget_is_finite_and_its_exhaustion_reaches_a_terminal`
asserts the *stage* row's `dependency_unavailable` while
`test_terminal_reason_names_the_cause.py` "reaches the unreachable-provider case by a
different route", leaving `audit_run.terminal_reason` on the exhausted path unasserted.

**The premise was false when `W5-ADV` wrote this file, and `W29-RETRY` made it true.**
A `RecordedAdapter` over an empty directory used to raise `dependency_unavailable` on
every call, which is retryable, so the wave-3 fixture took *the* exhausted-budget route,
spending all three attempts and both pinned backoffs before it terminated. That is a local
file that is not there, dressed as a provider that could not be reached, and the ladder it
bought could not change the answer. The adapter now reports `analysis_input_invalid`, the
fixture is asked exactly once, and the wave-3 suite drives its unreachable-provider case
with a scripted provider instead.

That leaves two things worth writing down, and both are here rather than in a comment on a
closure record:

1. the route itself, so that a future reader is not told again that the wave-3 fixture is
   the long path. The first test below asserts one attempt and no wait. If someone gives
   the empty-recordings failure a retryable code again, it goes red there rather than
   costing every such run ten seconds in silence.
2. the run row's reason on an exhausted budget driven by the *scripted* provider, which is
   the adapter the retry suite uses. That is now the only route to the exhausted path in
   this file, and the wave-3 suite reaches the same reason through its own scripted
   provider, which is what makes the property a property of the executor rather than of
   one fixture.

Shown to fail
-------------
Mutations were applied to a copy of `src/` at `/root/w5adv-mut` with `contracts/`, `docs/`
and `fixtures/` symlinked, run with `pytest -o pythonpath=/root/w5adv-mut/src`, and
`auditmanager.__file__` was asserted to resolve under the copy first. No tracked file was
edited.

* `findings/terminal.py::_reason_for` returns `analysis_failed` unconditionally —
  `test_an_exhausted_budget_names_the_transport_failure_on_the_run_row` failed as
  `'analysis_failed' == 'dependency_unavailable'`. The route test stayed **green**, which
  is right: the loop is unchanged and only the reason is wrong.
* `runs/retry.py::RetryPolicy.has_budget_for` returns `attempt <= 1`, so nothing is ever
  retried — **both** tests failed. The route test failed on its claim, `1 == 3`. The
  run-row test failed on its *precondition*, also `1 == 3`, and not on its claim: with no
  retries the run never reaches the exhausted path, so the guard refuses to report a
  verdict about a journey the run did not take. That is the precondition working. I had
  predicted this one would stay green — it does not, and the prediction is recorded here
  wrong rather than quietly corrected, because the difference between a guard that fails
  on its claim and one that fails on its precondition is exactly what a mutation run is
  for.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import ProviderMode, RecordedAdapter
from auditmanager.runs import (
    ATTEMPT_BUDGET,
    BACKOFF_SECONDS,
    RunRepository,
    execute_run,
    start_audit_run,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

STAGE = "text_analysis"


class _CountingAdapter:
    """Wraps an adapter and counts how many times the provider was actually asked.

    The count is the only way to tell an exhausted budget from a single failed attempt
    from outside the executor: both end at the same terminal with the same code, and the
    whole point of the first test is that those two are different journeys.
    """

    def __init__(self, inner) -> None:
        self._inner = inner
        self.calls = 0

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request):
        self.calls += 1
        return self._inner.complete(request)


class _NeverReachable:
    """A provider that is unreachable for good, raising exactly as the real adapters do."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request):
        self.calls += 1
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="no model response is available for this request",
            dependency="model_provider",
        )


def _start(session: Session, seeded, label: str) -> str:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=IdempotencyKey(f"w5adv-{label}-{uuid.uuid4()}"),
    )
    assert started.replayed is False
    return str(started.run_id)


def _stage_row(session: Session, run_id: str):
    for row in RunRepository().stage_results(session, run_id):
        if row.stage_id == STAGE:
            return row
    raise AssertionError(f"no {STAGE} stage result was persisted for {run_id}")


def _run_row(session: Session, run_id: str) -> dict:
    return dict(
        session.execute(
            text(
                "SELECT state, terminal_reason, degradation_set "
                "FROM audit_run WHERE run_id = :r"
            ),
            {"r": run_id},
        )
        .mappings()
        .one()
    )


def test_the_recorded_adapter_over_an_empty_directory_is_asked_exactly_once(
    session: Session, seeded, blob_store, provider_config, tmp_path
):
    """A local miss is not laddered, and the ladder is not merely shortened.

    This test asserted the opposite until `W29-RETRY`: that a `RecordedAdapter` over an
    empty directory spends the whole budget and both pinned backoffs, because the code it
    raised was `dependency_unavailable`, which the catalog marks retryable. That was true
    and it was the defect. The file is not on this disk and will not be on this disk in
    ten seconds, so those three attempts and those ten seconds bought an answer that could
    not change. `W28-LIVE` measured the cost through a browser: 10.0 s of a 16.1 s run.

    The wave-3 guard it used to protect is repaired rather than deleted:
    `test_terminal_reason_names_the_cause.py` now drives its unreachable-provider case
    with a provider that is really unreachable, so the exhausted path keeps its run-row
    assertion. The scripted-provider test below is the other half of that.

    `waits` and `adapter.calls` are both asserted, and they are different claims: one
    attempt with a wait before it would be a policy that still believed this was
    retryable and merely had nowhere to go.
    """
    empty = tmp_path / "no-recordings"
    empty.mkdir()
    adapter = _CountingAdapter(RecordedAdapter(empty))
    waits: list[float] = []
    run_id = _start(session, seeded, "empty-recordings-route")

    result = execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        sleep=waits.append,
    )

    assert adapter.calls == 1, (
        f"the empty-recordings adapter was asked {adapter.calls} times. Re-asking a "
        "local directory for a file that is not in it cannot answer differently, and "
        f"the budget of {ATTEMPT_BUDGET} is for a provider that may come back"
    )
    assert result.attempts == 1
    assert waits == [], (
        f"the run waited {waits} before an attempt that could not go differently; the "
        f"pinned ladder {list(BACKOFF_SECONDS)} belongs to the transport failure"
    )

    stage = _stage_row(session, run_id)
    assert stage.error is not None
    assert stage.error["code"] == ErrorCode.ANALYSIS_INPUT_INVALID.value
    assert stage.metrics.get("attempts") == 1
    assert stage.metrics.get("retry_waited_seconds") == 0.0
    assert stage.metrics.get("attempt_budget_exhausted") is False, (
        "a stage that was never going to get a second attempt did not run out of "
        "budget; it never needed one"
    )

    # The user-visible half. `audit_run.terminal_reason` is CHECK-constrained to the
    # frozen catalog, so this also proves the new code is one the column admits, and
    # it is the string the run screen prints verbatim.
    row = _run_row(session, run_id)
    assert row["state"] == "failed"
    assert row["terminal_reason"] == ErrorCode.ANALYSIS_INPUT_INVALID.value, (
        f"the run row reports {row['terminal_reason']!r}. A retryable reason on a run "
        "that cannot succeed tells an operator to start it again"
    )


def test_an_exhausted_budget_names_the_transport_failure_on_the_run_row(
    session: Session, seeded, blob_store, provider_config
):
    """The run row, on the exhausted path, under a provider that is never reachable.

    The stage row's code is already guarded by `test_retry_policy.py`. This is the run
    row, which is the surface an operator reads first and the one `W3_CLOSURE.md` §2
    widened: `dependency_unavailable` is retryable and `analysis_failed` is not, so a run
    that spent its budget against an outage must not be filed as a model that answered
    badly.

    Driven by a scripted provider rather than by empty recordings, so that this and the
    wave-3 guard reach the same reason through two different adapters.
    """
    adapter = _NeverReachable()
    waits: list[float] = []
    run_id = _start(session, seeded, "exhausted-run-row")

    result = execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        sleep=waits.append,
    )

    # The precondition. Without it the assertion below could pass on a run that failed
    # once, or failed for some other reason entirely.
    assert adapter.calls == ATTEMPT_BUDGET
    assert result.attempts == ATTEMPT_BUDGET
    stage = _stage_row(session, run_id)
    assert stage.status == "failed"
    assert stage.error is not None
    assert stage.error["code"] == ErrorCode.DEPENDENCY_UNAVAILABLE.value, (
        "this run did not end on the transport failure; the assertion below would prove "
        "nothing about the exhausted path"
    )

    row = _run_row(session, run_id)
    assert row["state"] == "failed"
    assert row["terminal_reason"] == ErrorCode.DEPENDENCY_UNAVAILABLE.value, (
        "the run row reports "
        f"{row['terminal_reason']!r} after the budget was spent against an unreachable "
        "provider. analysis_failed is not retryable and dependency_unavailable is, so an "
        "operator reading this run row has no reason to retry a run that is entirely "
        "worth retrying"
    )
    assert list(row["degradation_set"]) == [STAGE], (
        "the run must name the stage it lost, not an empty or wider set"
    )
