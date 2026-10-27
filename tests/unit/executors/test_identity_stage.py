"""`R-133` on the run path (`EXEC-HTTP-01`): the stage holds a live reply to the model asked for.

Container-free: the real stage with a fake live adapter and a journal double. The expected value
is the revision's gateway name (or `PROXY_LLM_MODEL` under the environment source); a reply that
names another model or none, and a configuration that selected nothing, are the typed failure
``model_identity_mismatch`` -- the answer may have been paid for, so it is never retried, its usage
is journaled, and nothing is published. A `recorded` response is a replayed fixture and is not held.
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
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

ROOT = Path(__file__).resolve().parents[3]
TEXT_LAYER = json.loads(
    (ROOT / "fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json").read_text("utf-8"))
PIN = provider_lock().model(provider_lock().primary_model_id)
EXPECTED = "anthropic/claude-opus-5"
OTHER = "openai/gpt-5-mini"


class _Adapter:
    def __init__(self, reported: str | None, mode: ProviderMode = ProviderMode.LIVE) -> None:
        self.provider_mode = mode
        self._reported = reported

    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            output_text=json.dumps({"observations": []}), stop_reason="end_turn",
            input_tokens=1000, output_tokens=200, latency_ms=5, model=self._reported,
        )


class _Journal:
    def __init__(self) -> None:
        self.received: list[Any] = []
        self.completed: list[Any] = []
        self.unknown: list[Any] = []

    def prepare(self, request: ModelRequest, *, mode: ProviderMode) -> ModelCallId:
        return ModelCallId.new()

    def response_received(self, call_id: Any, response: Any) -> None:
        self.received.append(response)

    def complete(self, call: Any) -> None:
        self.completed.append(call)

    def outcome_unknown(self, call_id: Any, error: Any) -> None:
        self.unknown.append(error)

    def not_processed(self, call_id: Any, error: Any, dispatch_class: str) -> None: ...


def _run(reported: str | None, call: CallBinding | None, mode: ProviderMode = ProviderMode.LIVE) -> Any:
    journal = _Journal()
    config = ProviderConfig(mode=mode, model_id=PIN.model_id, run_cost_ceiling_usd=1.0,
                            api_key=None, ceiling_is_explicit=False)
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=TEXT_LAYER, adapter=_Adapter(reported, mode),
        config=config, meter=CostMeter(ceiling_usd=1.0),
        call_journal=journal if mode is ProviderMode.LIVE else None, call=call,
        profile=V1_REFERENCE_PROFILE,
    )
    return outcome, journal


def _held(expected: str | None = EXPECTED) -> CallBinding:
    return CallBinding(expected_model=expected, check_identity=True)


def test_a_reply_naming_the_expected_model_passes() -> None:
    outcome, journal = _run(EXPECTED, _held())
    assert outcome.status == "succeeded" and len(journal.completed) == 1


@pytest.mark.parametrize("reported", [OTHER, None, "", EXPECTED.upper(), EXPECTED + "-20261001"])
def test_another_model_or_none_fails_closed_and_publishes_nothing(reported: str | None) -> None:
    outcome, journal = _run(reported, _held())
    assert outcome.status == "failed" and outcome.artifact is None and outcome.model_calls == ()
    assert outcome.error.code is ErrorCode.MODEL_IDENTITY_MISMATCH
    # The answer arrived and may have been paid for: unknown, never retried, usage kept.
    assert outcome.provider_effect_uncertain is True and outcome.provider_retry_allowed is False
    assert journal.completed == [] and len(journal.received) == 1
    assert (journal.received[0].input_tokens, journal.received[0].output_tokens) == (1000, 200)
    shown = str(outcome.error.custom_message)
    assert EXPECTED not in shown and OTHER not in shown and "model_not_selected" not in shown


@pytest.mark.parametrize("expected", ["proxy", "default", "auto", "", None])
def test_nothing_selected_fails_closed_and_the_message_names_model_not_selected(
    expected: str | None
) -> None:
    for reported in (EXPECTED, "proxy", None):
        outcome, journal = _run(reported, _held(expected))
        assert outcome.status == "failed"
        assert outcome.error.code is ErrorCode.MODEL_IDENTITY_MISMATCH
        assert "model_not_selected" in str(outcome.error.custom_message)
        assert journal.completed == [] and len(journal.received) == 1


def test_a_recorded_response_is_a_replayed_fixture_and_is_not_held() -> None:
    outcome, _ = _run(None, _held(), mode=ProviderMode.RECORDED)
    assert outcome.status == "succeeded"


def test_without_a_binding_asking_for_it_the_stage_behaves_as_it_always_did() -> None:
    for call in (None, CallBinding(), CallBinding(expected_model=EXPECTED, check_identity=False)):
        outcome, _ = _run(None, call)
        assert outcome.status == "succeeded"


def test_the_live_adapter_reports_the_model_the_sdk_reply_carries() -> None:
    from types import SimpleNamespace

    from auditmanager.analysis.text import LiveAdapter

    def create(**body: Any) -> Any:
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="{}")], stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=3, output_tokens=2), model="claude-opus-5")

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    response = LiveAdapter(api_key=None, client=client).complete(
        ModelRequest(model_id="claude-opus-5", body={"max_tokens": 1, "messages": []}))
    assert response.model == "claude-opus-5"
