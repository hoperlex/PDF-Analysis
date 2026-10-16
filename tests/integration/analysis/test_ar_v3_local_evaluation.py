"""Offline AR v3 response replay keeps draft request and grounding paired."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.local_evaluation import (
    SuppliedV3Response,
    V3LocalEvaluationRefused,
    evaluate_v3_supplied_response,
)
from auditmanager.analysis.profiles.ar_v3.request_candidate import prepare_v3_request_candidate
from auditmanager.analysis.profiles.ar_v3.response import V3ResponseError
from auditmanager.analysis.text.textlayer import Page, TextLayer


DOCUMENT = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
SELECTED = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK"
HIDDEN = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QM"
SNAPSHOT = "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
MAP_SHA = "a" * 64
PDF_QUOTE = "Ширина прохода 1,2 м"
NORM_QUOTE = "Минимальная ширина прохода составляет 1,4 м"


def _json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _set(*, hidden: str = "Невыбранный нормативный абзац") -> bytes:
    rows = [dict(
        norm_document_id=DOCUMENT, norm_paragraph_id=paragraph,
        designation="СП 54", title="Жилые здания", ordinal=ordinal,
        clause_number="7.1.4", page_label="7", text=value,
        text_sha256=hashlib.sha256(value.encode()).hexdigest(),
    ) for ordinal, (paragraph, value) in enumerate((
        (SELECTED, NORM_QUOTE), (HIDDEN, hidden),
    ))]
    prompt = _json({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [dict(rows[0], item_id="item_a", label="N1")],
    }).decode("utf-8")
    return _json({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {
            "map_sha256": MAP_SHA, "reviewed_content_key": "reviewed-key",
            "norms_snapshot_id": SNAPSHOT, "embedding_build": "bge-m3-dense-v1",
        },
        "snapshot_content_digest": "b" * 64,
        "ranking_version": "norm-ranking-prep-v1",
        "norm_quote_version": "norm-quote-v1", "norm_value_version": "norm-value-v1",
        "prompt_part": prompt, "prompt_part_characters": len(prompt),
        "windows_per_item": 0, "inside_target_windows_dropped": True,
        "rebinding_paragraphs": rows,
    })


def _layer(*, body: str | None = None) -> TextLayer:
    text = body or "АР. " + PDF_QUOTE + "."
    return TextLayer("ver_fixture", "NFC", (Page(1, 0, len(text), text),), text)


def _inputs():
    raw = _set()
    layer = _layer()
    candidate = prepare_v3_request_candidate(
        layer, raw, expected_version_uid="ver_fixture",
        expected_set_sha256=hashlib.sha256(raw).hexdigest(),
        expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
    )
    return candidate, layer, raw


def _norm(*, pdf_quote: str = PDF_QUOTE, label: str = "N1") -> dict[str, object]:
    return {
        "category": "evacuation",
        "finding_text": "Проверить ширину прохода.",
        "recommendation_text": "Сверить проект и норму.",
        "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": pdf_quote}],
        "norm_citations": [{"label": label, "quote": NORM_QUOTE}],
        "required_value": "1,4 м", "stated_value": "1,2 м",
    }


def _response(request_sha256: str, *items: object, truncated: bool = False):
    return SuppliedV3Response(
        request_sha256, _json({"observations": list(items)}).decode("utf-8"), truncated,
    )


def test_replay_grounds_pdf_then_selected_norm_without_creating_finding():
    candidate, layer, raw = _inputs()
    response = _response(candidate.request_sha256, _norm())
    result = evaluate_v3_supplied_response(candidate, response, layer, raw)
    assert result.request_sha256 == candidate.request_sha256
    assert result.response_sha256 == hashlib.sha256(response.output_text.encode()).hexdigest()
    assert result.grounding.rejected == ()
    assert result.grounding.malformed_count == 0
    accepted = result.grounding.accepted[0]
    assert layer.slice(accepted.evidence[0].char_start, accepted.evidence[0].char_end) == PDF_QUOTE
    assert [(item.label, item.paragraph_id, item.state) for item in accepted.norm_citations] == [
        ("N1", SELECTED, "verified"),
    ]
    assert not hasattr(result, "finding_uid")
    assert not hasattr(accepted, "expert_verdict")


def test_pdf_failure_precedes_norm_failure_and_both_are_withheld():
    candidate, layer, raw = _inputs()
    response = _response(
        candidate.request_sha256,
        _norm(pdf_quote="Только отсутствующий текст", label="N9"),
        _norm(label="N9"),
    )
    result = evaluate_v3_supplied_response(candidate, response, layer, raw)
    assert result.grounding.accepted == ()
    assert [item.reason for item in result.grounding.rejected] == [
        "quotation_absent", "norm_label_unknown",
    ]


def test_changed_set_pdf_candidate_or_response_digest_refuses():
    candidate, layer, raw = _inputs()
    response = _response(candidate.request_sha256, _norm())
    attempts = (
        (candidate, response, layer, _set(hidden="Другой невыбранный абзац")),
        (candidate, response, _layer(body="АР. Ширина прохода 1,3 м."), raw),
        (replace(candidate, response_schema_json="{}"), response, layer, raw),
        (candidate, replace(response, request_sha256="c" * 64), layer, raw),
    )
    for supplied_candidate, supplied_response, supplied_layer, supplied_set in attempts:
        with pytest.raises(V3LocalEvaluationRefused):
            evaluate_v3_supplied_response(
                supplied_candidate, supplied_response, supplied_layer, supplied_set,
            )


def test_ocr_selection_is_part_of_request_identity_and_never_pdf_evidence():
    candidate, layer, raw = _inputs()
    response = _response(candidate.request_sha256, _norm(pdf_quote="Только OCR текст"))
    context = (RecognisedContext(1, "Только OCR текст", ("mixed_script",)),)
    with pytest.raises(V3LocalEvaluationRefused, match="request_candidate_mismatch"):
        evaluate_v3_supplied_response(
            candidate, response, layer, raw, recognised_context=context,
        )
    matching = prepare_v3_request_candidate(
        layer, raw, expected_version_uid=candidate.version_uid,
        expected_set_sha256=candidate.set_sha256,
        expected_snapshot_id=candidate.norms_snapshot_id,
        expected_map_sha256=candidate.map_sha256,
        recognised_context=context,
    )
    result = evaluate_v3_supplied_response(
        matching, replace(response, request_sha256=matching.request_sha256),
        layer, raw, recognised_context=context,
    )
    assert result.grounding.accepted == ()
    assert result.grounding.rejected[0].reason == "quote_in_recognised_text"


def test_malformed_untruncated_refuses_and_truncated_salvages_only_complete_prefix():
    candidate, layer, raw = _inputs()
    partial = '{"observations":[' + _json(_norm()).decode("utf-8") + ',{"category":"evacuation"'
    with pytest.raises(V3ResponseError, match="malformed_untruncated_response"):
        evaluate_v3_supplied_response(
            candidate, SuppliedV3Response(candidate.request_sha256, partial, False), layer, raw,
        )
    result = evaluate_v3_supplied_response(
        candidate, SuppliedV3Response(candidate.request_sha256, partial, True), layer, raw,
    )
    assert result.grounding.salvaged is True
    assert len(result.grounding.accepted) == 1
    assert result.grounding.rejected == ()
