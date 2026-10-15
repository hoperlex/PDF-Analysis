"""One typed response must pass every AR v2 filter before merge."""

from __future__ import annotations

import json

import pytest

from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v2.response import V2ResponseError
from auditmanager.analysis.profiles.ar_v2.response_pipeline import finish_response
from auditmanager.analysis.text.adapter import ModelResponse
from auditmanager.analysis.text.textlayer import Page, TextLayer


def _layer() -> TextLayer:
    text = "Стена А имеет толщину 200 мм. Окно Б имеет ширину 1200 мм."
    return TextLayer(
        version_uid="ver_pipeline",
        normalization_id="NFC",
        pages=(Page(1, 0, len(text), text),),
        document_text=text,
    )


def _proposal(*quotes: str) -> dict[str, object]:
    return {
        "category": "dimensions",
        "finding_text": "Указанные размеры требуют сверки",
        "recommendation_text": "Уточнить размер в проекте",
        "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": quote} for quote in quotes],
    }


def _response(output_text: str, *, stop_reason: str = "end_turn") -> ModelResponse:
    return ModelResponse(
        output_text=output_text,
        stop_reason=stop_reason,
        input_tokens=100,
        output_tokens=50,
        latency_ms=10,
    )


def test_filters_failed_proposal_before_dense_merge_numbering() -> None:
    raw = json.dumps(
        {
            "observations": [
                _proposal("Стена А имеет толщину 200 мм"),
                _proposal("Стена А имеет толщину 200 мм", "Невидимый размер 300 мм"),
                {"invalid": True},
                _proposal("Стена А имеет толщину 200 мм"),
                _proposal("Окно Б имеет ширину 1200 мм"),
            ]
        },
        ensure_ascii=False,
    )
    result = finish_response(_response(raw), _layer())
    assert result.response_sha256 == _response(raw).response_sha256
    assert result.truncated is False
    assert result.grounding.malformed_count == 1
    assert [item.proposal_ordinal for item in result.grounding.rejected] == [1]
    assert result.grounding.rejected[0].failures[0].reason == "quotation_absent"
    assert result.merge.source_proposal_ordinals == (0, 2, 3)
    assert result.merge.artifact["groups"] == [
        {
            "observation_ordinals": [0, 1],
            "canonical_ordinal": 0,
            "merge_rule_version": "1.0.0",
        },
        {
            "observation_ordinals": [2],
            "canonical_ordinal": 2,
            "merge_rule_version": "1.0.0",
        },
    ]
    for item in result.grounding.accepted:
        for evidence in item.evidence:
            assert _layer().slice(evidence.char_start, evidence.char_end) == evidence.quote


def test_max_token_signal_salvages_only_complete_elements() -> None:
    full = json.dumps(_proposal("Стена А имеет толщину 200 мм"), ensure_ascii=False)
    cut = '{"observations":[' + full + ',{"category":"dimensions"'
    result = finish_response(_response(cut, stop_reason="max_tokens"), _layer())
    assert result.truncated
    assert result.grounding.salvaged
    assert result.merge.source_proposal_ordinals == (0,)


def test_malformed_untruncated_response_is_refused() -> None:
    with pytest.raises(V2ResponseError, match="malformed_untruncated_response"):
        finish_response(_response('{"observations":['), _layer())


def test_recognised_only_quote_remains_diagnostic_and_unmerged() -> None:
    raw = json.dumps(
        {"observations": [_proposal("Только в OCR: толщина 250 мм")]},
        ensure_ascii=False,
    )
    result = finish_response(
        _response(raw),
        _layer(),
        recognised_context=(RecognisedContext(1, "Только в OCR: толщина 250 мм", ()),),
    )
    assert result.grounding.rejected[0].failures[0].reason == "quote_in_recognised_text"
    assert result.merge.source_proposal_ordinals == ()
    assert result.merge.artifact["groups"] == []
