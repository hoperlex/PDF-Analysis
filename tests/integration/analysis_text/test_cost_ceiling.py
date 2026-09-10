"""The ``OD-03`` per-run cost ceiling.

Exceeding it raises ``cost_budget_exceeded`` - the catalog code that exists for
exactly this case - and halts. The tests below check three things that are easy to get
wrong in a way no error message would reveal:

* the halt **publishes nothing**: no artifact, and no observation reaches a consumer;
* the halt **does not shorten the document**: ``pages_analysed`` never appears with a
  trimmed page set as a way of fitting the budget;
* the spend that broke the budget is still **recorded**, so a run report shows what was
  actually spent rather than the last figure under the line.

Rates come from ``docs/program/P02_LOCK.json``. No rate is written down here either:
the expected costs below are computed from the pin, so a rate change in the lock moves
the code and the test together.
"""

from __future__ import annotations

import pytest

from auditmanager.analysis.text import (
    DEFAULT_RUN_COST_CEILING_USD,
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    CostMeter,
    load_provider_config,
    provider_lock,
    run_text_analysis,
)
from auditmanager.analysis.text.config import ENV_COST_CEILING
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId


def _pin():
    lock = provider_lock()
    return lock.model(lock.primary_model_id)


def test_cost_is_computed_from_the_locked_rates():
    pin = _pin()
    expected = (
        2180 * pin.input_per_mtok_usd + 940 * pin.output_per_mtok_usd
    ) / 1_000_000.0
    assert pin.cost_usd(input_tokens=2180, output_tokens=940) == pytest.approx(expected)


def test_a_run_inside_the_ceiling_succeeds_and_records_its_spend(
    text_layer_document, recorded_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    assert outcome.status == STATUS_SUCCEEDED
    pin = _pin()
    call = outcome.model_calls[0]
    assert call.cost_usd == pytest.approx(
        pin.cost_usd(input_tokens=call.input_tokens, output_tokens=call.output_tokens)
    )
    assert 0 < outcome.metrics["cost_usd"] < DEFAULT_RUN_COST_CEILING_USD


def test_an_expensive_recording_halts_against_the_default_ceiling(
    text_layer_document, variant_adapter
):
    """The ``over_budget`` recording, run under the ceiling nobody configured."""
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("over_budget"),
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert outcome.artifact is None, "a halted run publishes no observation"
    assert outcome.metrics["observations_emitted"] == 0
    # The call that broke the budget is still on the record.
    assert len(outcome.model_calls) == 1
    assert outcome.model_calls[0].cost_usd > DEFAULT_RUN_COST_CEILING_USD


def test_an_explicit_low_ceiling_halts_the_ordinary_run(
    text_layer_document, recorded_adapter
):
    config = load_provider_config({ENV_COST_CEILING: "0.0001"})
    assert config.ceiling_is_explicit is True

    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=recorded_adapter,
        config=config,
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert outcome.artifact is None


def test_the_halt_never_shortens_the_document(text_layer_document, variant_adapter):
    """No trimmed page set, no partial status, no degraded success."""
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("over_budget"),
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.artifact is None
    assert "pages_analysed" not in outcome.metrics or outcome.metrics.get(
        "observations_emitted"
    ) == 0


def test_a_meter_already_at_the_ceiling_issues_no_call(
    text_layer_document, recorded_adapter
):
    """The pre-call guard: a run at the ceiling never asks the provider again."""
    spent = CostMeter(ceiling_usd=0.5, spent_usd=0.5, call_count=1)
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=recorded_adapter,
        meter=spent,
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert outcome.model_calls == (), "no second call was issued"
    assert spent.call_count == 1


def test_the_envelope_carries_only_the_declared_safe_detail():
    """``cost_budget_exceeded`` declares one safe key and it is not an amount."""
    meter = CostMeter(ceiling_usd=0.01)
    with pytest.raises(DomainError) as raised:
        meter.charge(_pin(), input_tokens=1_000_000, output_tokens=1_000_000)

    envelope = raised.value.envelope("corr-b3-cost").as_dict()
    assert envelope["error_code"] == "cost_budget_exceeded"
    assert envelope["retryable"] is False
    assert envelope["details"] == {"budget_scope": "run"}
    assert "$" not in envelope["message"]
    # The spend is still on the meter for the run report, just not in the envelope.
    assert meter.spent_usd > meter.ceiling_usd


def test_a_ceiling_that_is_not_a_positive_number_is_refused():
    for value in ("", "  ", "nonsense", "0", "-1"):
        if value.strip() == "":
            assert load_provider_config({ENV_COST_CEILING: value}).ceiling_is_explicit is False
            continue
        with pytest.raises(DomainError) as raised:
            load_provider_config({ENV_COST_CEILING: value})
        assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
