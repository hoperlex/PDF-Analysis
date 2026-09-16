"""``analysis.text.stage`` and ``analysis.text.cost``: the rules a scripted adapter reaches.

`W10-ANL` mutation sweep, rows ST-01, ST-04, ST-05, ST-08, ST-11, ST-12, ST-13, ST-14 and
CM-04 — all green across `tests/integration/analysis_engine`,
`tests/integration/analysis_text` and `tests/replay`.

The existing `test_partial_and_status.py` and `test_cost_ceiling.py` drive the stage through
the **recorded** adapter and its `variants/` directory. That covers whatever the recordings
happen to contain. The rules below need replies the recordings do not have — a truncated
reply that yields no usable observation at all, a truncated reply whose observations already
reach the last page, a document graph of the wrong version — so this file drives the stage
with a small scripted adapter built in the test.

A scripted adapter is legitimate here and is not a mock of the thing under test: the dispatch
says the surface is reachable with "recorded and scripted adapters", `ModelAdapter` is a
`runtime_checkable` `Protocol` on the public seam, and the stage reads `provider_mode` off
whatever object it was handed. Nothing is added to `fixtures/recorded/**`.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.analysis.text.adapter import ModelRequest, ModelResponse
from auditmanager.analysis.text.config import (
    ProviderConfig,
    ProviderMode,
    load_provider_config,
)
from auditmanager.analysis.text.cost import CostMeter, cost_budget_exceeded
from auditmanager.analysis.text.lock import ModelPin, provider_lock
from auditmanager.analysis.text.stage import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCEEDED,
    run_text_analysis,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId

#: Pinned literals. `claude-opus-5` and its rates are `docs/program/P02_LOCK.json`, checked
#: against that document in `test_provider_lock_refusals.py`.
MODEL_ID = "claude-opus-5"
CATEGORY = "internal_contradiction"
PAGE_ONE = "Отчёт за год. Выручка выросла.\n"
PAGE_TWO = "Выручка упала за тот же год.\n"
PAGE_THREE = "Прочие сведения приведены далее.\n"


def _text_layer_document() -> dict[str, Any]:
    pages = [PAGE_ONE, PAGE_TWO, PAGE_THREE]
    out, cursor = [], 0
    for number, text in enumerate(pages, start=1):
        out.append(
            {
                "page_number": number,
                "char_start": cursor,
                "char_end": cursor + len(text),
                "text": text,
            }
        )
        cursor += len(text)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": cursor,
        "pages": out,
    }


class _ScriptedAdapter:
    """Returns one prepared `ModelResponse`. Declares `recorded`, because it replayed."""

    def __init__(self, response: ModelResponse) -> None:
        self._response = response
        self.calls = 0

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return self._response


def _reply(*observations: dict[str, Any]) -> str:
    return json.dumps({"observations": list(observations)}, ensure_ascii=False)


def _observation(page: int, quote: str) -> dict[str, Any]:
    return {
        "category": CATEGORY,
        "finding_text": "Две суммы не сходятся.",
        "recommendation_text": "Сверить показатели.",
        "evidence": [{"page_number": page, "quote": quote}],
    }


def _response(
    output_text: str, *, stop_reason: str = "end_turn", reported_cost_usd: float | None = None
) -> ModelResponse:
    return ModelResponse(
        output_text=output_text,
        stop_reason=stop_reason,
        input_tokens=1000,
        output_tokens=200,
        latency_ms=1234,
        reported_cost_usd=reported_cost_usd,
    )


def _config(**overrides: Any) -> ProviderConfig:
    fields: dict[str, Any] = {
        "mode": ProviderMode.RECORDED,
        "model_id": MODEL_ID,
        "run_cost_ceiling_usd": 1.00,
        "api_key": None,
        "ceiling_is_explicit": False,
    }
    fields.update(overrides)
    return ProviderConfig(**fields)


def _run(response: ModelResponse, **overrides: Any) -> Any:
    kwargs: dict[str, Any] = {
        "run_id": RunId.new(),
        "text_layer_document": _text_layer_document(),
        "adapter": _ScriptedAdapter(response),
        "config": _config(),
    }
    kwargs.update(overrides)
    return run_text_analysis(**kwargs)


# --- the scripted adapter reproduces the ordinary outcomes ---------------------------


def test_a_complete_reply_succeeds_and_carries_no_error() -> None:
    outcome = _run(_response(_reply(_observation(1, "Выручка выросла"))))
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.error is None
    assert outcome.artifact["pages_analysed"] == [1, 2, 3]
    assert outcome.metrics["call_status"] == "succeeded"


# --- ST-01: a truncated reply that yields nothing usable is failed, never partial -----


def test_a_truncated_reply_with_no_usable_observation_is_failed() -> None:
    """ST-01. `partial` means usable observations over a subset; none is not a subset."""
    outcome = _run(_response('{"observations": [{"cat', stop_reason="max_tokens"))
    assert outcome.status == STATUS_FAILED
    assert outcome.status != STATUS_PARTIAL
    assert outcome.artifact is None
    assert outcome.error is not None
    assert outcome.error.code is ErrorCode.ANALYSIS_FAILED
    assert "cut short" in str(outcome.error)
    assert outcome.metrics["call_status"] == "truncated"


def test_a_truncated_reply_whose_observations_all_fail_to_ground_is_failed() -> None:
    """The same rule by the other route: proposals arrive but none resolves."""
    outcome = _run(
        _response(
            _reply(_observation(1, "Эта цитата отсутствует в документе")),
            stop_reason="max_tokens",
        )
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.artifact is None


# --- ST-04 and ST-05: pages_analysed is a strict subset whenever partial --------------


def test_a_truncated_reply_reports_only_the_pages_up_to_its_frontier() -> None:
    """ST-05. The frontier is the furthest page a complete observation cites."""
    outcome = _run(
        _response(_reply(_observation(1, "Выручка выросла")), stop_reason="max_tokens")
    )
    assert outcome.status == STATUS_PARTIAL
    assert outcome.artifact["pages_analysed"] == [1]


def test_a_truncated_reply_reaching_the_last_page_still_reports_a_strict_subset() -> None:
    """ST-04. The clamp: a cut-short report never proves full coverage.

    The observation cites page 3, the last page, so the frontier alone would admit all
    three. Section 4.7 requires a strict subset whenever the status is `partial`, so the
    last page is dropped. The expected value is the literal `[1, 2]`.
    """
    outcome = _run(
        _response(
            _reply(_observation(3, "Прочие сведения")),
            stop_reason="max_tokens",
        )
    )
    assert outcome.status == STATUS_PARTIAL
    assert outcome.artifact["pages_analysed"] == [1, 2]
    assert set(outcome.artifact["pages_analysed"]) < {1, 2, 3}


def test_a_complete_reply_reports_every_page() -> None:
    """The negative half: the clamp applies only to a truncated reply."""
    outcome = _run(_response(_reply(_observation(3, "Прочие сведения"))))
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.artifact["pages_analysed"] == [1, 2, 3]


# --- ST-11 and ST-12: the document graph fails closed --------------------------------


def _graph(**overrides: Any) -> dict[str, Any]:
    document = {
        "artifact_role": "context.document_graph",
        "artifact_version": "1.0.0",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
    }
    document.update(overrides)
    return document


@pytest.mark.parametrize(
    "role", ["prepared.text_layer", "geometry.block_index", "context.graph", ""]
)
def test_a_document_context_that_is_not_a_graph_is_refused(role: str) -> None:
    """ST-11."""
    outcome = _run(
        _response(_reply(_observation(1, "Выручка выросла"))),
        document_graph=_graph(artifact_role=role),
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert outcome.error.detail_fields["reason"] == "artifact_role_unexpected"


@pytest.mark.parametrize("version", ["1.1.0", "2.0.0", "0.9.0", ""])
def test_a_document_graph_of_an_unsupported_version_is_refused(version: str) -> None:
    """ST-12. A different `reason` from ST-11, so neither covers for the other."""
    outcome = _run(
        _response(_reply(_observation(1, "Выручка выросла"))),
        document_graph=_graph(artifact_version=version),
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.detail_fields["reason"] == "artifact_version_unsupported"


def test_a_well_formed_document_graph_is_accepted() -> None:
    outcome = _run(
        _response(_reply(_observation(1, "Выручка выросла"))), document_graph=_graph()
    )
    assert outcome.status == STATUS_SUCCEEDED


def test_an_absent_document_graph_is_permitted() -> None:
    assert _run(_response(_reply(_observation(1, "Выручка выросла")))).status == STATUS_SUCCEEDED


# --- ST-14: cost_basis on the record says which figure it is -------------------------


def test_cost_basis_is_measured_when_the_transport_reported_a_figure() -> None:
    """ST-14. The stage is the only layer that saw the response."""
    outcome = _run(
        _response(_reply(_observation(1, "Выручка выросла")), reported_cost_usd=0.02)
    )
    assert outcome.model_calls[0].cost_basis == "measured"


def test_cost_basis_reaches_the_record_but_not_the_success_path_metrics() -> None:
    """An asymmetry in the product, pinned as found rather than repaired.

    `run_text_analysis` puts `cost_basis` in the metrics dict it returns on the
    **budget-overrun** path, and does not put it in the metrics dict it returns on the
    success path — where it reaches the `ModelCallRecord` instead. This test records the
    behaviour as it is today so that changing it is a deliberate act. It is reported in
    the review record for the owner of `src/auditmanager/analysis/`; `W10-ANL` writes
    tests, not product code.
    """
    outcome = _run(
        _response(_reply(_observation(1, "Выручка выросла")), reported_cost_usd=0.02)
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.model_calls[0].cost_basis == "measured"
    assert "cost_basis" not in outcome.metrics

    overrun = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=_text_layer_document(),
        adapter=_ScriptedAdapter(
            _response(_reply(_observation(1, "Выручка выросла")), reported_cost_usd=5.0)
        ),
        config=_config(),
        meter=CostMeter(ceiling_usd=0.01),
    )
    assert overrun.status == STATUS_FAILED
    assert overrun.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert overrun.metrics["cost_basis"] == "measured"


def test_cost_basis_is_estimated_when_the_transport_reported_nothing() -> None:
    outcome = _run(_response(_reply(_observation(1, "Выручка выросла"))))
    assert outcome.model_calls[0].cost_basis == "estimated"


# --- ST-08 and CM-04: the two cost checks catch different failures --------------------


def test_a_meter_already_at_the_ceiling_issues_no_call() -> None:
    """ST-08. The check is before the call, so the adapter is never reached."""
    adapter = _ScriptedAdapter(_response(_reply(_observation(1, "Выручка выросла"))))
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=_text_layer_document(),
        adapter=adapter,
        config=_config(),
        meter=CostMeter(ceiling_usd=0.10, spent_usd=0.10),
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert adapter.calls == 0, "a run at the ceiling must issue no request at all"
    assert outcome.model_calls == ()


def test_spending_exactly_the_ceiling_does_not_halt_the_charge_that_reached_it() -> None:
    """CM-04. `charge` halts on `>`, not `>=`, and the boundary is load-bearing.

    A meter with a 0.01 ceiling charged exactly 0.01 has *not* passed the ceiling, so the
    call is recorded and the run continues. The next `check_before_call` halts it, because
    that one is `>=`. Collapsing the two comparisons to the same operator breaks one or
    the other, and both directions are asserted here.
    """
    pin = ModelPin(
        model_id=MODEL_ID, input_per_mtok_usd=5.0, output_per_mtok_usd=25.0
    )
    meter = CostMeter(ceiling_usd=0.01)
    assert meter.charge(pin, input_tokens=0, output_tokens=0, reported_cost_usd=0.01) == 0.01
    assert meter.spent_usd == 0.01
    with pytest.raises(DomainError) as raised:
        meter.check_before_call()
    assert raised.value.code is ErrorCode.COST_BUDGET_EXCEEDED


def test_spending_a_fraction_past_the_ceiling_halts_the_charge() -> None:
    pin = ModelPin(model_id=MODEL_ID, input_per_mtok_usd=5.0, output_per_mtok_usd=25.0)
    meter = CostMeter(ceiling_usd=0.01)
    with pytest.raises(DomainError) as raised:
        meter.charge(pin, input_tokens=0, output_tokens=0, reported_cost_usd=0.0100001)
    assert raised.value.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert meter.spent_usd == 0.0100001, "the call that broke the budget is still recorded"


def test_a_meter_below_the_ceiling_issues_the_call() -> None:
    """The negative half of `check_before_call`."""
    meter = CostMeter(ceiling_usd=0.01, spent_usd=0.0099999)
    meter.check_before_call()


def test_the_budget_envelope_carries_the_scope_and_no_amount() -> None:
    error = cost_budget_exceeded()
    assert error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert error.detail_fields["budget_scope"] == "run"
    assert set(error.detail_fields) == {"budget_scope"}


def test_the_default_ceiling_matches_the_figure_the_lock_records() -> None:
    """The lock carries a machine-readable ceiling; `config.py`'s comment says it does not.

    `docs/program/P02_LOCK.json` → `models.run_cost_ceiling_usd` is `1.0`, and
    `DEFAULT_RUN_COST_CEILING_USD` is `1.00`. They agree today. The module's comment claims
    `OD-03` "has not recorded a machine-readable number in either lock", which is false —
    see the review record. Pinning the agreement here means a future edit to either one
    without the other reddens.
    """
    from pathlib import Path

    lock = json.loads(
        (Path(__file__).resolve().parents[3] / "docs" / "program" / "P02_LOCK.json").read_text(
            encoding="utf-8"
        )
    )
    assert lock["models"]["run_cost_ceiling_usd"] == 1.0
    # The module's *default*, reached by supplying no ceiling — not the literal this
    # file's own `_config()` helper passes in.
    inherited = load_provider_config({"AUDITMANAGER_PROVIDER_MODE": "recorded"})
    assert inherited.run_cost_ceiling_usd == 1.00
    assert inherited.ceiling_is_explicit is False
    assert provider_lock().primary_model_id == MODEL_ID
