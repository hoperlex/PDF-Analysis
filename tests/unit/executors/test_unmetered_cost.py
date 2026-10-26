"""The unmetered cost basis and the run-level cost rule (`EXEC-HTTP-01`, plan section 5).

A call through a connection with no per-call cost is recorded as ``unmetered`` and charges the
meter nothing. The run-level rule keeps the three fields of a run's cost moving together because
the run did call a provider: all calls unmetered -> figure 0, basis ``unmetered``, the call count;
a mix -> the metered sum with basis ``estimated``. The SQL halves of the rule (the run summary and
the dashboard aggregate) are exercised in ``tests/integration/executors``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.text import (
    CallBinding,
    CostMeter,
    ModelRequest,
    ModelResponse,
    ProviderConfig,
    ProviderMode,
    provider_lock,
    run_text_analysis,
)
from auditmanager.shared.identity import ModelCallId, RunId
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

ROOT = Path(__file__).resolve().parents[3]
TEXT_LAYER = json.loads(
    (ROOT / "fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json").read_text("utf-8"))
PIN = provider_lock().model(provider_lock().primary_model_id)


def test_the_meters_basis_follows_the_run_level_rule() -> None:
    meter = CostMeter(ceiling_usd=1.0)
    assert meter.cost_basis == "estimated", "no call yet: nothing to claim"
    meter.record_unmetered()
    meter.record_unmetered()
    assert (meter.cost_basis, meter.spent_usd, meter.call_count) == ("unmetered", 0.0, 2)
    meter.charge(PIN, input_tokens=100, output_tokens=100, reported_cost_usd=0.01)
    assert (meter.cost_basis, meter.spent_usd, meter.call_count) == ("estimated", 0.01, 3), \
        "unmetered and metered mix: the metered sum, estimated"
    clean = CostMeter(ceiling_usd=1.0)
    clean.charge(PIN, input_tokens=100, output_tokens=100, reported_cost_usd=0.01)
    assert clean.cost_basis == "measured"


def test_an_unmetered_call_never_approaches_the_ceiling() -> None:
    meter = CostMeter(ceiling_usd=0.01)
    for _ in range(50):
        meter.check_before_call()
        meter.record_unmetered()
    assert meter.spent_usd == 0.0


class _LiveAdapter:
    provider_mode = ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            output_text=json.dumps({"observations": []}), stop_reason="end_turn",
            input_tokens=1000, output_tokens=200, latency_ms=5, reported_cost_usd=None,
        )


class _Journal:
    def __init__(self) -> None:
        self.completed: list[Any] = []

    def prepare(self, request: ModelRequest, *, mode: ProviderMode) -> ModelCallId:
        return ModelCallId.new()

    def response_received(self, call_id: Any, response: Any) -> None: ...

    def complete(self, call: Any) -> None:
        self.completed.append(call)

    def outcome_unknown(self, call_id: Any, error: Any) -> None: ...

    def not_processed(self, call_id: Any, error: Any, dispatch_class: str) -> None: ...


def _run(call: CallBinding | None) -> tuple[Any, _Journal, CostMeter]:
    journal, meter = _Journal(), CostMeter(ceiling_usd=1.0)
    config = ProviderConfig(
        mode=ProviderMode.LIVE, model_id=PIN.model_id, run_cost_ceiling_usd=1.0, api_key=None,
        ceiling_is_explicit=False,
    )
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=TEXT_LAYER, adapter=_LiveAdapter(), config=config,
        meter=meter, call_journal=journal, call=call,
        profile=V1_REFERENCE_PROFILE,
    )
    return outcome, journal, meter


def test_an_unmetered_connection_records_the_call_as_unmetered_with_no_estimate() -> None:
    outcome, journal, meter = _run(CallBinding(
        provider_label="openai_chat", unmetered=True, identity_basis="reported",
        connection_revision_id="excr_01J00000000000000000000000",
    ))
    assert outcome.status == "succeeded"
    (call,) = outcome.model_calls
    assert (call.cost_basis, call.cost_usd, call.provider) == ("unmetered", 0.0, "openai_chat")
    assert journal.completed[0].as_dict()["cost_basis"] == "unmetered"
    assert (outcome.metrics["cost_basis"], outcome.metrics["cost_usd"]) == ("unmetered", 0.0)
    assert meter.call_count == 1 and meter.spent_usd == 0.0


def test_a_metered_connection_still_charges_the_pin_estimate_and_the_default_is_unchanged() -> None:
    for binding in (None, CallBinding(provider_label="openai_chat", identity_basis="reported",
                                      connection_revision_id="excr_01J00000000000000000000000")):
        outcome, _journal, meter = _run(binding)
        (call,) = outcome.model_calls
        assert call.cost_basis == "estimated" and call.cost_usd > 0
        assert call.provider == ("anthropic" if binding is None else "openai_chat")
        assert outcome.metrics["cost_basis"] == "estimated" and meter.spent_usd > 0


def test_a_call_binding_names_a_revision_and_a_basis_together_or_neither() -> None:
    with pytest.raises(ValueError):
        CallBinding(connection_revision_id="excr_01J00000000000000000000000")
    with pytest.raises(ValueError):
        CallBinding(identity_basis="reported")
