"""The one file wave 2 changed twice: ``runs/executor.py``.

``W2-PROV`` rewrote the body of ``_record_model_calls`` and removed the map that
collapsed ``truncated`` onto ``succeeded``. ``W2-RUN`` left that function alone and
started calling it **once per attempt**, from inside a retry loop. Git merged the two
with no conflict, and neither session's own suite crosses the seam: grep
``tests/integration/runs/test_retry_policy.py`` for ``output_tokens`` and you find one
fixture literal and no assertion; grep
``tests/integration/runs/test_call_status_and_output_tokens.py`` for ``attempts`` and you
find nothing at all. Textual mergeability is not semantic correctness. This file is the
first thing that runs both changes in one execution.

Four claims are under test, and each of them is a claim about the *composition* rather
than about either half:

1. ``stage_result.metrics`` is one dict that both sessions write into --
   ``_text_stage_result`` filters ``outcome.metrics`` (``W2-PROV``'s tokens and call
   status) and then calls ``metrics.update(attempts.metrics())`` (``W2-RUN``'s tally).
   ``update`` is last, so a key collision would silently drop a provenance figure and
   leave a green suite behind. The test asserts **both** key sets on **one** persisted
   row.
2. A reader with only the database can count attempts and tell a first-try success from
   a third-try one.
3. ``OD-03``'s ceiling is a property of the run, not of an attempt. The discriminating
   pair is a pre-spent meter against a fresh one over the *same* outage script: if the
   executor rebuilt the meter per attempt the caller's spend would be discarded and both
   runs would publish.
4. A ``partial`` outcome is not retried. This is a seam and not a restatement of
   ``W2-RUN``'s policy test: ``W2-PROV``'s truncated path is the one place that returns a
   non-``None`` ``error`` alongside a non-failed status, and the loop's break condition
   reads ``policy.retries(outcome.error)`` -- the *error*, never the status. A retryable
   code on that error would re-ask a provider that already answered.

Nothing here repairs anything. The adapters are local doubles over the shipped recorded
adapter, and every fact is read back out of PostgreSQL through SQL rather than off the
:class:`ExecutionResult` the call returned, because the object and the row are exactly
the two things that are allowed to disagree.
Mutation evidence
-----------------
Every guard below was shown to fail. Each mutation was applied to a copy of ``src/`` and
``tools/`` outside the worktree, run with ``-o pythonpath=<copy>/src`` after printing
``auditmanager.__file__`` to prove the copy was the imported tree, then reverted and
re-run green. No tracked file was edited to mutate anything.

==== =========================================================== ==========================
 id   mutation                                                    guards it reddened
==== =========================================================== ==========================
 M1   ``AttemptSummary.metrics()`` emits ``output_tokens``         both-authors, disjoint,
      instead of ``attempts`` -- the exact key collision the       first-vs-third, one-row,
      merge order makes silent                                     both ceiling guards
 M7   ``_run_text_analysis_stage`` builds a fresh ``CostMeter``    both ceiling guards
      per attempt instead of using the run's
 M8   ``AttemptSummary.metrics()`` always reports ``attempts: 1``  both-authors,
                                                                   first-vs-third, one-row
 M9   ``_record_model_calls`` writes each call twice               one-row
 M2   the pre-wave-2 map: ``truncated`` written as ``succeeded``   truncated-not-retried
 M6   ``RetryPolicy.retries`` returns ``True`` for any error       truncated-not-retried
==== =========================================================== ==========================

M1 reddens the both-authors guard with its named assertion -- "W2-RUN's attempt tally is
not on the persisted row: ['attempts']" -- and not with a ``KeyError``, which is the
difference between a guard that fired and a test that crashed. M7 likewise reddens with
"the meter this caller supplied recorded no spend after a run that published and charged".
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import CostMeter, ProviderMode
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode

#: The keys ``W2-PROV`` puts into the text stage's metrics, and the keys ``W2-RUN`` puts
#: there. Declared as data rather than spelled inline in each assertion so that a key
#: renamed on one side is caught once, by name, instead of slipping past a literal.
PROVENANCE_METRIC_KEYS = (
    "input_tokens",
    "output_tokens",
    "output_tokens_source",
    "call_status",
)
ATTEMPT_METRIC_KEYS = (
    "attempts",
    "attempt_budget",
    "attempt_budget_exhausted",
    "retried_on_error_code",
    "retry_waited_seconds",
)


class _OutageThenAnswer:
    """Unreachable for the first ``outages`` calls, then the shipped recorded adapter.

    The outage is raised the way ``RecordedAdapter`` and ``LiveAdapter`` raise it -- a
    typed ``DomainError`` carrying ``dependency_unavailable`` -- so the executor sees
    nothing special-cased. ``provider_mode`` is a property for the same reason it is a
    class constant on the real adapters: ``execute_run`` refuses an adapter whose mode
    disagrees with the run row, and this double must pass that guard honestly rather
    than be exempted from it.
    """

    def __init__(self, inner: Any, *, outages: int) -> None:
        self._inner = inner
        self._outages = outages
        self.calls = 0

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request: Any) -> Any:
        self.calls += 1
        if self.calls <= self._outages:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE,
                message="no model response is available for this request",
                dependency="model_provider",
            )
        return self._inner.complete(request)


def _no_wait(seconds: float) -> None:
    """Take the pinned backoff without spending it.

    The waits themselves are ``W2-RUN``'s to prove; what matters here is that the value
    reaches ``retry_waited_seconds`` on the persisted row, and a test that really slept
    ten seconds to establish that would be paying for nothing.
    """
    _no_wait.waited.append(seconds)


_no_wait.waited = []  # type: ignore[attr-defined]


def _run(
    session: Session,
    harness: Any,
    seed: Any,
    *,
    blob_store: Any,
    adapter: Any,
    provider_config: Any,
    label: str,
    cost_meter: CostMeter | None = None,
) -> str:
    """Start and execute one run over a seeded version, through the public surfaces."""
    started = start_audit_run(
        session,
        version_uid=seed["version_uid"],
        analysis_profile_id=str(harness.AR_TEXT_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(harness.AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
        provider_mode="recorded",
        idempotency_key=harness.new_key(label),
    )
    session.commit()
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        cost_meter=cost_meter,
        sleep=_no_wait,
    )
    session.commit()
    return str(started.run_id)


@pytest.fixture(scope="module")
def seed(journey_harness, session_factory, blob_store):
    """One contract-correct version every run in this module executes against."""
    h = journey_harness
    with session_factory() as session:
        return h.seed_version_with_contract_manifest(session, blob_store, h.new_key("seam"))


def _text_metrics(session: Session, run_id: str) -> dict[str, Any]:
    """The persisted ``text_analysis`` metrics, read back out of the database.

    Deliberately not the ``ExecutionResult``: the whole point of the attempt tally is
    that it survives the process, and asserting on the returned object would prove only
    that the object was built.
    """
    raw = session.execute(
        text(
            "SELECT metrics FROM stage_result "
            "WHERE run_id = :r AND stage_id = 'text_analysis'"
        ),
        {"r": run_id},
    ).scalar_one()
    return raw if isinstance(raw, dict) else json.loads(raw)


def _calls(session: Session, run_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in session.execute(
            text(
                "SELECT model_call_id, status, error_code, output_tokens, input_tokens, "
                "provider_mode, response_sha256, cost_micros, parameters "
                "FROM model_call WHERE run_id = :r ORDER BY model_call_id"
            ),
            {"r": run_id},
        )
        .mappings()
        .all()
    ]


def _terminal(session: Session, run_id: str) -> dict[str, Any]:
    return dict(
        session.execute(
            text(
                "SELECT state, degradation_set, terminal_reason "
                "FROM audit_run WHERE run_id = :r"
            ),
            {"r": run_id},
        )
        .mappings()
        .one()
    )


# ---------------------------------------------------------------------------
# 1. One metrics dict, two authors
# ---------------------------------------------------------------------------


def test_a_retried_run_persists_both_authors_metrics_on_one_row(
    journey_harness, session, seed, blob_store, recorded_adapter, provider_config
):
    """The seam itself: ``metrics.update(attempts.metrics())`` must not shadow tokens.

    Asserted on the row of a run that actually retried twice, because that is the only
    shape in which both halves are non-trivially present: the attempt keys are written
    on every run, but they only carry information once ``attempts > 1``, and the token
    keys only exist on an attempt that reached the provider.
    """
    adapter = _OutageThenAnswer(recorded_adapter, outages=2)
    run_id = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        label="both-authors",
    )
    metrics = _text_metrics(session, run_id)

    missing_attempt = [k for k in ATTEMPT_METRIC_KEYS if k not in metrics]
    missing_provenance = [k for k in PROVENANCE_METRIC_KEYS if k not in metrics]
    assert not missing_attempt, (
        f"W2-RUN's attempt tally is not on the persisted row: {missing_attempt}. "
        f"row carries {sorted(metrics)}"
    )
    assert not missing_provenance, (
        "W2-PROV's call provenance was dropped from the persisted row: "
        f"{missing_provenance}. `_text_stage_result` merges the attempt tally over the "
        f"outcome metrics, so a collision silently wins. Row carries {sorted(metrics)}"
    )

    # Both halves must be *informative*, not merely present.
    assert metrics["attempts"] == 3, metrics["attempts"]
    assert metrics["attempt_budget"] == 3
    assert metrics["attempt_budget_exhausted"] is True
    assert metrics["retried_on_error_code"] == ErrorCode.DEPENDENCY_UNAVAILABLE.value
    assert metrics["retry_waited_seconds"] > 0, (
        "two retries were taken, so the pinned backoff must have been recorded"
    )

    assert metrics["call_status"] == "succeeded"
    assert metrics["output_tokens_source"] == "provider"
    assert isinstance(metrics["output_tokens"], int) and metrics["output_tokens"] > 0
    assert isinstance(metrics["input_tokens"], int) and metrics["input_tokens"] > 0
    assert adapter.calls == 3, "the provider was asked once per attempt"


def test_the_two_key_sets_are_disjoint_so_neither_can_shadow_the_other(
    journey_harness, session, seed, blob_store, recorded_adapter, provider_config
):
    """A structural guard beside the behavioural one above.

    The behavioural test above fails if a collision drops a key today. This one fails if
    a *future* rename introduces a collision, before it has a chance to drop anything,
    and it reads the key sets off the real merge rather than off the two literals.
    """
    from auditmanager.runs.retry import AttemptSummary

    tally = AttemptSummary(
        attempts=2, attempt_budget=3, retried_on_error_code="x", waited_seconds_total=1.0
    ).metrics()
    assert set(tally) == set(ATTEMPT_METRIC_KEYS), (
        "the attempt tally's keys moved; this suite's expectation is stale"
    )

    run_id = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
        label="disjoint",
    )
    metrics = _text_metrics(session, run_id)
    stage_only = {k: v for k, v in metrics.items() if k not in tally}
    collisions = set(tally) & set(PROVENANCE_METRIC_KEYS)
    assert not collisions, (
        f"the attempt tally and the call provenance now share keys {sorted(collisions)}; "
        "the tally is merged last, so the provenance figure is the one that is lost"
    )
    for key in PROVENANCE_METRIC_KEYS:
        assert key in stage_only, f"{key} is not a stage-authored metric any more"


# ---------------------------------------------------------------------------
# 2. Countable after the process is gone
# ---------------------------------------------------------------------------


def test_a_first_try_and_a_third_try_success_are_distinguishable_from_the_row_alone(
    journey_harness, session, seed, blob_store, recorded_adapter, provider_config
):
    """``P4_CLOSURE.md`` §1's headline must stay a query rather than a recollection.

    The two runs publish the same findings from the same recording, so every figure a
    reader might mistake for the attempt count -- tokens, cost, response digest -- is
    identical between them. The attempt tally is the only thing that differs, which is
    what makes this a test of the tally and not of the fixture.
    """
    first = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=_OutageThenAnswer(recorded_adapter, outages=0),
        provider_config=provider_config,
        label="first-try",
    )
    third = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=_OutageThenAnswer(recorded_adapter, outages=2),
        provider_config=provider_config,
        label="third-try",
    )

    first_metrics = _text_metrics(session, first)
    third_metrics = _text_metrics(session, third)

    assert first_metrics["attempts"] == 1
    assert third_metrics["attempts"] == 3
    assert first_metrics["retried_on_error_code"] is None
    assert third_metrics["retried_on_error_code"] == "dependency_unavailable"
    assert first_metrics["attempt_budget_exhausted"] is False
    assert third_metrics["attempt_budget_exhausted"] is True

    for key in PROVENANCE_METRIC_KEYS + ("request_sha256", "cost_usd"):
        assert first_metrics[key] == third_metrics[key], (
            f"{key} differs between a first-try and a third-try run of the same "
            "recording; the retry changed what was recorded about the answer"
        )

    assert _terminal(session, first)["state"] == "published"
    assert _terminal(session, third)["state"] == "published", (
        "a run that lost the provider twice and then got an answer publishes; "
        "the retry is transport, not judgement"
    )


def test_the_retried_run_writes_provenance_only_for_the_attempt_that_answered(
    journey_harness, session, seed, blob_store, recorded_adapter, provider_config
):
    """``_record_model_calls`` is called once per attempt; two of the three have nothing.

    This is the half of the seam that could have gone wrong in the other direction -- a
    per-attempt call into a function that writes a row unconditionally would have
    produced three rows for one answer, inflating the ledger's call count and the PC-02
    report's spend. It writes one, and the attempt count lives on the stage row instead.
    """
    run_id = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=_OutageThenAnswer(recorded_adapter, outages=2),
        provider_config=provider_config,
        label="one-row",
    )
    calls = _calls(session, run_id)
    assert len(calls) == 1, (
        f"a three-attempt run wrote {len(calls)} model_call rows; two attempts never "
        "reached a response and have nothing to record"
    )
    call = calls[0]
    assert call["status"] == "succeeded"
    assert call["error_code"] is None
    assert call["provider_mode"] == "recorded"
    assert call["output_tokens"] > 0

    metrics = _text_metrics(session, run_id)
    assert metrics["attempts"] > len(calls), (
        "the row count and the attempt count are different facts; a reader that counted "
        "model_call rows alone would report this three-attempt run as a single attempt"
    )
    assert call["output_tokens"] == metrics["output_tokens"], (
        "the row and the stage metrics disagree about what the provider returned"
    )


# ---------------------------------------------------------------------------
# 3. OD-03 across the attempts
# ---------------------------------------------------------------------------


def test_a_retry_does_not_refill_the_run_cost_ceiling(
    journey_harness, session, seed, blob_store, recorded_adapter, provider_config
):
    """The meter is built once per run, so spend carried into it survives the attempts.

    The discriminating pair is the point. Both runs execute the identical outage script
    against the identical recording and differ only in the meter handed to
    ``execute_run``:

    * a fresh meter publishes;
    * a meter already carrying ``ceiling - half a call`` fails on ``cost_budget_exceeded``
      at the attempt that finally reached the provider.

    If the executor built a meter per attempt -- the reading of ``OD-03`` that a retry
    would be able to buy its way out of -- the caller's spend would be discarded and the
    second run would publish too. The pre-spend is computed from the *measured* cost of
    the control run rather than from a literal, so the test does not encode a rate card.
    """
    control_meter = CostMeter(ceiling_usd=provider_config.run_cost_ceiling_usd)
    control = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=_OutageThenAnswer(recorded_adapter, outages=2),
        provider_config=provider_config,
        label="ceiling-control",
        cost_meter=control_meter,
    )
    assert _terminal(session, control)["state"] == "published"
    one_call = control_meter.spent_usd
    # Named before the pre-spend is sized, because this is the first thing a per-attempt
    # meter breaks: the caller's object is handed to `execute_run` and, if the executor
    # builds its own inside the loop, comes back untouched. A test that only sized the
    # pre-spend from it would fail here as an arithmetic accident rather than as a finding.
    assert one_call > 0, (
        "the meter this caller supplied recorded no spend after a run that published and "
        "charged: execute_run is not spending through it, so OD-03's ceiling is a "
        "property of an attempt rather than of the run"
    )
    assert control_meter.call_count == 1, (
        f"the run's meter counted {control_meter.call_count} charged calls; a three-"
        "attempt run charges once, and a meter rebuilt per attempt counts zero"
    )

    ceiling = provider_config.run_cost_ceiling_usd
    pre_spent = CostMeter(ceiling_usd=ceiling, spent_usd=ceiling - one_call / 2)
    starved = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=_OutageThenAnswer(recorded_adapter, outages=2),
        provider_config=provider_config,
        label="ceiling-starved",
        cost_meter=pre_spent,
    )

    metrics = _text_metrics(session, starved)
    assert metrics["attempts"] == 3, (
        "the outage script is the control's; the budget must bite at the attempt that "
        f"reached the provider, not before it. attempts={metrics['attempts']}"
    )
    stage = session.execute(
        text(
            "SELECT status, error FROM stage_result "
            "WHERE run_id = :r AND stage_id = 'text_analysis'"
        ),
        {"r": starved},
    ).mappings().one()
    error = stage["error"] if isinstance(stage["error"], dict) else json.loads(stage["error"])
    assert stage["status"] == "failed", stage["status"]
    assert error["code"] == ErrorCode.COST_BUDGET_EXCEEDED.value, (
        "the retried attempt bought a fresh USD 1.00 budget: it answered and was "
        f"charged without the run's accumulated spend counting against it ({error})"
    )
    assert pre_spent.spent_usd > ceiling - one_call / 2, (
        "the caller's meter did not accumulate, so the executor was not using it"
    )
    assert _terminal(session, starved)["state"] != "published"


def test_the_ceiling_is_consulted_on_every_attempt_not_only_the_first(
    journey_harness, session, seed, blob_store, recorded_adapter, provider_config
):
    """A run that is already at the ceiling never reaches the provider at all.

    Beside the test above rather than inside it: that one proves the accumulated spend
    survives into a later attempt, this one proves the *before* check is what stops the
    call, so a meter exhausted before the run starts costs nothing and the adapter is
    never asked.
    """
    ceiling = provider_config.run_cost_ceiling_usd
    adapter = _OutageThenAnswer(recorded_adapter, outages=0)
    run_id = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        label="ceiling-exhausted",
        cost_meter=CostMeter(ceiling_usd=ceiling, spent_usd=ceiling),
    )
    assert adapter.calls == 0, (
        "a run already at the ceiling issued a request anyway; check_before_call is not "
        "reached on the attempt path"
    )
    metrics = _text_metrics(session, run_id)
    assert metrics["attempts"] == 1, (
        "a budget halt is not transport and must not be retried; "
        f"attempts={metrics['attempts']}"
    )
    assert _calls(session, run_id) == [], "nothing was called, so nothing may be recorded"


# ---------------------------------------------------------------------------
# 4. The truncated/partial outcome meets the retry classifier
# ---------------------------------------------------------------------------


def test_a_truncated_partial_carries_an_error_and_is_still_not_retried(
    journey_harness, session, seed, blob_store, variant_adapter, provider_config
):
    """``W2-PROV``'s partial path is the only non-failed outcome with a non-``None`` error.

    ``_run_text_analysis_stage`` breaks on ``policy.retries(outcome.error)`` and never
    looks at ``outcome.status``. That is deliberate -- it is what keeps a status
    comparison out of the executor -- and it means the truncated path's
    ``partial_result_not_publishable`` is load-bearing: were it ever restated as a
    transport code, a provider that answered and stopped at its output ceiling would be
    asked the same question twice more, at full price, and the second answer would
    overwrite the first one's stage row.

    The guard is the composition of two frozen facts, so both are asserted: the code the
    partial path raises, and that the catalog does not mark it retryable.
    """
    from auditmanager.runs.retry import RETRYABLE_STAGE_ERRORS

    assert ErrorCode.PARTIAL_RESULT_NOT_PUBLISHABLE.retryable is False
    assert ErrorCode.PARTIAL_RESULT_NOT_PUBLISHABLE not in RETRYABLE_STAGE_ERRORS

    adapter = variant_adapter("truncated")
    run_id = _run(
        session,
        journey_harness,
        seed,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        label="truncated-not-retried",
    )
    metrics = _text_metrics(session, run_id)
    assert metrics["attempts"] == 1, (
        "a reply cut short at the output ceiling was re-asked; the provider answered, "
        f"so there is nothing a second attempt could answer differently "
        f"(attempts={metrics['attempts']})"
    )
    assert metrics["call_status"] == "truncated"
    assert metrics["retried_on_error_code"] is None

    calls = _calls(session, run_id)
    assert len(calls) == 1, f"a truncated call was recorded {len(calls)} times"
    assert calls[0]["status"] == "truncated"
