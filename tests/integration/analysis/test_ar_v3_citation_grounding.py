"""PDF evidence precedes norm grounding; neither yields persisted authority."""

from __future__ import annotations

import json

from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.citation_grounding import ground_v3_proposals
from auditmanager.analysis.profiles.ar_v3.response import parse_response
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.norms.public import NormLabelBinding, NormParagraph


PDF_QUOTE = "Ширина прохода 1,2 м"
NORM_QUOTE = "Минимальная ширина прохода составляет 1,4 м"


def _layer() -> TextLayer:
    body = "АР. " + PDF_QUOTE + "."
    return TextLayer("ver_fixture", "NFC", (Page(1, 0, len(body), body),), body)


def _norm(*, label: str = "N2", pdf_quote: str = PDF_QUOTE,
          required: str = "1,4 м", stated: str = "1,2 м") -> dict[str, object]:
    return {
        "category": "evacuation",
        "finding_text": "Проход уже требования нормы.",
        "recommendation_text": "Проверить ширину.",
        "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": pdf_quote}],
        "norm_citations": [{"label": label, "quote": NORM_QUOTE}],
        "required_value": required,
        "stated_value": stated,
    }


def _parsed(*items: object):
    return parse_response(json.dumps({"observations": items}, ensure_ascii=False), truncated=False)


def _source():
    return (
        (NormParagraph("p1", "d1", NORM_QUOTE),),
        (NormLabelBinding("N1", "p1"), NormLabelBinding("N2", "p1")),
    )


def test_two_labels_share_one_paragraph_and_pdf_offsets_are_exact() -> None:
    paragraphs, bindings = _source()
    result = ground_v3_proposals(
        _parsed(_norm()), _layer(), paragraphs=paragraphs, label_bindings=bindings,
    )
    assert result.rejected == ()
    assert len(result.accepted) == 1
    candidate = result.accepted[0]
    assert candidate.proposal_ordinal == 0
    assert candidate.evidence[0].quote == PDF_QUOTE
    assert _layer().slice(candidate.evidence[0].char_start, candidate.evidence[0].char_end) == PDF_QUOTE
    assert [(item.label, item.paragraph_id, item.state, item.raw_quote)
            for item in candidate.norm_citations] == [
        ("N2", "p1", "verified", NORM_QUOTE),
    ]
    assert not hasattr(candidate, "finding_uid")
    assert not hasattr(candidate, "norm_citation_count")


def test_pdf_failure_withholds_before_norm_failure_and_drops_all_anchors() -> None:
    paragraphs, bindings = _source()
    result = ground_v3_proposals(
        _parsed(_norm(label="N9", pdf_quote="Проход шириной 9 м")),
        _layer(), paragraphs=paragraphs, label_bindings=bindings,
    )
    assert result.accepted == ()
    assert [(item.proposal_ordinal, item.reason) for item in result.rejected] == [
        (0, "quotation_absent"),
    ]


def test_norm_quote_and_both_value_failures_withhold_whole_proposal() -> None:
    paragraphs, bindings = _source()
    proposals = (_norm(label="N9"), _norm(required="11,4 м"), _norm(stated="11,2 м"))
    result = ground_v3_proposals(
        _parsed(*proposals), _layer(), paragraphs=paragraphs, label_bindings=bindings,
    )
    assert result.accepted == ()
    assert [item.reason for item in result.rejected] == [
        "norm_label_unknown", "norm_value_not_in_quote", "stated_value_not_in_evidence",
    ]


def test_ordinary_proposal_has_only_candidate_empty_citation_list() -> None:
    ordinary = _norm()
    ordinary["category"] = "dimensions"
    for key in ("norm_citations", "required_value", "stated_value"):
        del ordinary[key]
    paragraphs, bindings = _source()
    result = ground_v3_proposals(
        _parsed(ordinary), _layer(), paragraphs=paragraphs, label_bindings=bindings,
    )
    assert len(result.accepted) == 1
    assert result.accepted[0].norm_citations == ()


def test_ocr_only_quote_remains_unpublishable() -> None:
    paragraphs, bindings = _source()
    result = ground_v3_proposals(
        _parsed(_norm(pdf_quote="Только OCR распознал эту строку")),
        _layer(), paragraphs=paragraphs, label_bindings=bindings,
        recognised_context=(RecognisedContext(
            1, "Только OCR распознал эту строку", ("mixed_script",),
        ),),
    )
    assert result.accepted == ()
    assert result.rejected[0].reason == "quote_in_recognised_text"
