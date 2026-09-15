"""How much the model said, recorded beside how much it published.

``P4_CLOSURE.md`` §6 asked for this and gave the reason: on the PC-02 corpus precision
evidence is **saturated** — zero findings across nine controls — so a finding count of zero
has stopped discriminating between a model that read a clean document and found nothing and
a model that barely answered. ``PC02-C01`` and ``PC02-C07`` returned after 10 output tokens;
``PC02-C09`` produced 530 and published nothing. Three different outcomes, one finding
count, and nothing in the tree that could tell them apart.

The figure has to be the **provider's own**. A count recomputed from the response body would
measure what survived parsing rather than what was generated, and the two diverge precisely
where the figure earns its keep. The ``truncated`` variant makes that concrete: its
recording reports 16000 output tokens over 1199 characters of text, so the provider's answer
and any recomputation of it differ by a factor of fifty. Every assertion below is written
against that gap rather than against a number being merely present, because "``> 0``" would
pass on a recomputation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.analysis.text import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCEEDED,
    CostMeter,
    run_text_analysis,
)
from auditmanager.analysis.text.provenance import (
    CALL_STATUSES,
    CALL_SUCCEEDED,
    CALL_TRUNCATED,
)
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import RunId

RECORDINGS = Path(__file__).resolve().parents[3] / "fixtures/recorded/text_analysis"
RECORDING_NAME = "6c208358cfa9ae3a7591223084f87250084c9c6f8070f211d8e2fd9e278dbd1d.json"


def _recording(variant: str | None = None) -> dict:
    base = RECORDINGS if variant is None else RECORDINGS / "variants" / variant
    return json.loads((base / RECORDING_NAME).read_text(encoding="utf-8"))


def _recomputations(body: str) -> dict[str, int]:
    """Every plausible way someone would recompute a token count from the text.

    Named and asserted against as a set, rather than testing one of them, because the
    substitution this guards against is "somebody swapped the provider's figure for a
    cheap local estimate" and the estimate they would reach for is not knowable in
    advance.
    """
    return {
        "characters": len(body),
        "characters_over_three": len(body) // 3,
        "characters_over_four": len(body) // 4,
        "whitespace_words": len(body.split()),
    }


@pytest.mark.parametrize(
    "variant, expected_call_status, expected_stage_status",
    [
        (None, CALL_SUCCEEDED, STATUS_SUCCEEDED),
        ("truncated", CALL_TRUNCATED, STATUS_PARTIAL),
    ],
)
def test_the_stage_reports_the_providers_output_token_figure(
    text_layer_document,
    recorded_adapter,
    variant_adapter,
    variant,
    expected_call_status,
    expected_stage_status,
):
    """Both paths, because only asserting the happy one would miss the case that matters."""
    recording = _recording(variant)
    adapter = recorded_adapter if variant is None else variant_adapter(variant)

    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=adapter
    )
    assert outcome.status == expected_stage_status

    reported = recording["usage"]["output_tokens"]
    assert outcome.metrics["output_tokens"] == reported
    assert outcome.metrics["input_tokens"] == recording["usage"]["input_tokens"]
    assert outcome.metrics["output_tokens_source"] == "provider"
    assert outcome.metrics["call_status"] == expected_call_status
    assert outcome.metrics["call_status"] in CALL_STATUSES

    for how, figure in _recomputations(recording["output_text"]).items():
        assert reported != figure, (
            f"the fixture cannot discriminate: the provider's figure equals the "
            f"{how} recomputation of its own response text"
        )
        assert outcome.metrics["output_tokens"] != figure, (
            f"the emitted count equals the {how} recomputation of the response text; "
            "only the provider's usage block may supply this figure"
        )

    # The record that becomes the model_call row carries the same figure, unmodified.
    (call,) = outcome.model_calls
    assert call.output_tokens == reported
    assert call.status == expected_call_status


def test_the_output_token_count_sits_beside_the_finding_count(
    text_layer_document, variant_adapter
):
    """Both figures, in one metrics block, from one truncated call.

    16000 output tokens and two emitted observations. Either number alone says something
    false about this run: the count alone suggests a model that barely answered, and the
    token figure alone suggests one that answered at length and usefully.
    """
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("truncated"),
    )
    metrics = outcome.metrics

    assert metrics["output_tokens"] == 16000
    assert metrics["observations_emitted"] == 2
    assert metrics["observations_proposed"] == 2
    # A reply that was cut short covers a strict subset, and the pair is what shows why.
    assert metrics["pages_analysed"] < metrics["pages_total"]


def test_a_budget_overrun_still_reports_what_the_call_produced(
    text_layer_document, variant_adapter
):
    """The reply was paid for and never parsed. Both halves of that are recorded.

    The spend was already reported here; what it bought was not. A cost figure with no
    token figure beside it is the shape that makes a budget overrun unreadable afterwards
    — there is no way to tell an expensive short answer from a cheap long one.
    """
    recording = _recording("over_budget")
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("over_budget"),
        meter=CostMeter(ceiling_usd=0.01),
    )

    assert outcome.status == STATUS_FAILED
    assert outcome.error is not None
    assert outcome.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert outcome.artifact is None

    assert outcome.metrics["output_tokens"] == recording["usage"]["output_tokens"]
    assert outcome.metrics["input_tokens"] == recording["usage"]["input_tokens"]
    assert outcome.metrics["output_tokens_source"] == "provider"
    # Nothing was published, and that is reported next to what was generated rather than
    # instead of it.
    assert outcome.metrics["observations_emitted"] == 0
    assert outcome.metrics["cost_usd"] > 0
