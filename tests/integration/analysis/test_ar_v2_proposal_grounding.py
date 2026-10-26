"""A single unresolved quote rejects the complete AR v2 proposal."""

from __future__ import annotations

import pytest

from auditmanager.analysis.profiles.ar_v2.proposal_grounding import ground_proposals
from auditmanager.analysis.profiles.ar_shared.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v2.response import (
    ParsedResponse,
    ProposedEvidence,
    ProposedObservation,
)
from auditmanager.analysis.text.textlayer import Page, TextLayer


def _layer() -> TextLayer:
    first = "АР: отметка верха 3,00 м. Толщина стены 200 мм."
    second = "АР: отметка верха 3,20 м. Толщина стены 250 мм."
    return TextLayer(
        version_uid="ver_grounding",
        normalization_id="NFC",
        pages=(
            Page(1, 0, len(first), first),
            Page(2, len(first), len(first) + len(second), second),
        ),
        document_text=first + second,
    )


def _proposal(*items: tuple[int, str]) -> ProposedObservation:
    return ProposedObservation(
        category="internal_contradiction",
        finding_text="Отметки противоречат друг другу",
        recommendation_text="Сверить отметки",
        proposed_severity="operational",
        evidence=tuple(ProposedEvidence(page, quote) for page, quote in items),
    )


def test_whole_proposal_rejected_but_all_failures_retained() -> None:
    parsed = ParsedResponse(
        observations=(
            _proposal((1, "отметка верха 3,00 м")),
            _proposal(
                (1, "Толщина стены 200 мм"),
                (1, "Кровля плоская"),
                (2, "Стена отсутствует"),
            ),
            _proposal((2, "отметка верха 3,20 м")),
        ),
        salvaged=True,
        malformed_count=2,
    )
    result = ground_proposals(
        parsed,
        _layer(),
        recognised_context=(RecognisedContext(1, "Кровля плоская", ("mixed_script",)),),
    )

    assert [item.proposal_ordinal for item in result.accepted] == [0, 2]
    assert [item.proposal.proposed_severity for item in result.accepted] == [
        "operational", "operational"
    ]
    assert len(result.rejected) == 1
    assert result.rejected[0].proposal_ordinal == 1
    assert [(item.evidence_ordinal, item.reason) for item in result.rejected[0].failures] == [
        (1, "quote_in_recognised_text"),
        (2, "quotation_absent"),
    ]
    assert result.malformed_count == 2
    assert result.salvaged is True
    for item in result.accepted:
        for anchor in item.evidence:
            assert _layer().slice(anchor.char_start, anchor.char_end) == anchor.quote


def test_wrong_page_is_not_repaired_and_other_valid_proposal_survives() -> None:
    result = ground_proposals(
        ParsedResponse(
            observations=(
                _proposal((1, "отметка верха 3,20 м")),
                _proposal((2, " отметка верха 3,20 м ")),
            ),
            salvaged=False,
            malformed_count=0,
        ),
        _layer(),
    )
    assert [item.proposal_ordinal for item in result.accepted] == [1]
    assert result.accepted[0].evidence[0].quote == "отметка верха 3,20 м"
    assert result.rejected[0].failures[0].reason == "quotation_on_different_page"


def test_unknown_ocr_page_fails_before_any_result_is_returned() -> None:
    with pytest.raises(ValueError, match="recognised_page_absent_from_text_layer"):
        ground_proposals(
            ParsedResponse((_proposal((1, "отметка верха 3,00 м")),), False, 0),
            _layer(),
            recognised_context=(RecognisedContext(3, "отметка верха 3,00 м", ()),),
        )
    with pytest.raises(ValueError, match="recognised_page_absent_from_text_layer"):
        ground_proposals(
            ParsedResponse((), False, 0),
            _layer(),
            recognised_context=(RecognisedContext(3, "вне PDF", ()),),
        )
