"""``match_published_findings``: the findings of an AR v3 beta Run are none, or exactly the review's proposals.

Pure: no database. The review document is the part of the sealed artifact the matcher reads
(``provisional_citations``); the findings are the certified partitions the citation reader returns.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.findings.public import (
    VerifiedCitation, VerifiedFindingPartitions, VerifiedObservationPartition,
)
from auditmanager.runs.v3_published_findings import match_published_findings
from auditmanager.shared.errors import DomainError, ErrorCode

DOC, PAR, OTHER_PAR = "ndoc_" + "A" * 26, "npar_" + "B" * 26, "npar_" + "C" * 26
NORM_QUOTE = "Минимальная ширина эвакуационных путей составляет 1,4 м."
PDF_QUOTE = "Ширина эвакуационных путей принята не менее 1,2 м"


def _proposal(ordinal: int = 0, *, paragraph: str = PAR, quote: str = PDF_QUOTE, page: int = 7) -> dict:
    return {
        "proposal_ordinal": ordinal,
        "evidence": [{"page_number": page, "quote": quote, "char_start": 10, "char_end": 10 + len(quote), "block_id": None}],
        "citations": [{
            "item_id": "C01", "label": "N1", "document_id": DOC, "paragraph_id": paragraph,
            "raw_offset": 0, "raw_quote": NORM_QUOTE, "state": "verified",
        }],
    }


def _finding(n: int, *, paragraph: str = PAR, state: str = "verified", merged: bool = False):
    observation = "fobs_" + str(n) * 26
    citation = VerifiedCitation(
        citation_ordinal=1, norms_snapshot_id="ns_" + "D" * 26, norm_document_id=DOC,
        norm_paragraph_id=paragraph, designation="СП 1.13130", title="t", clause_number=None,
        page_label=1, quote=NORM_QUOTE, state=state, source_attribution="unattributed",
    )
    partition = VerifiedObservationPartition(observation, 1, (citation,), "1,4 м", "1,2 м")
    return VerifiedFindingPartitions(
        "fnd_" + str(n) * 26, partition, (partition,) if merged else (),
    )


def _evidence(n: int, *, quote: str = PDF_QUOTE, page: int = 7, start: int = 10):
    return SimpleNamespace(
        finding_observation_id="fobs_" + str(n) * 26, evidence_ordinal=0, page_number=page,
        quote=quote, char_start=start, char_end=start + len(quote), block_id=None,
    )


def _doc(*proposals: dict) -> dict:
    return {"provisional_citations": list(proposals)}


def _refused(reason: str, *args) -> None:
    with pytest.raises(DomainError) as caught:
        match_published_findings(*args)
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert caught.value.detail_fields["reason"] == reason


def test_no_finding_is_a_legitimate_state_even_when_the_review_has_proposals() -> None:
    match_published_findings((), (), _doc(_proposal()))
    match_published_findings((), (), _doc())


def test_one_finding_per_proposal_matches() -> None:
    match_published_findings(
        (_finding(1),), (_evidence(1),), _doc(_proposal()),
    )


def test_the_match_is_by_content_not_by_order() -> None:
    first, second = _proposal(0, paragraph=PAR), _proposal(1, paragraph=OTHER_PAR)
    match_published_findings(
        (_finding(2, paragraph=OTHER_PAR), _finding(1, paragraph=PAR)),
        (_evidence(1), _evidence(2)), _doc(first, second),
    )


def test_a_finding_the_review_does_not_explain_is_refused() -> None:
    _refused("published_finding_count_differs_from_review", (_finding(1),), (_evidence(1),), _doc())


def test_a_finding_missing_for_a_proposal_is_refused() -> None:
    _refused(
        "published_finding_count_differs_from_review",
        (_finding(1),), (_evidence(1),), _doc(_proposal(0), _proposal(1)),
    )


def test_the_same_count_with_other_norm_content_is_refused() -> None:
    _refused(
        "published_finding_not_in_review",
        (_finding(1, paragraph=OTHER_PAR),), (_evidence(1),), _doc(_proposal(paragraph=PAR)),
    )


def test_the_same_count_with_other_pdf_evidence_is_refused() -> None:
    _refused(
        "published_finding_not_in_review",
        (_finding(1),), (_evidence(1, quote="Ширина принята не менее 9,9 м"),), _doc(_proposal()),
    )


def test_the_same_count_with_another_page_or_offset_is_refused() -> None:
    _refused("published_finding_not_in_review", (_finding(1),), (_evidence(1, page=8),), _doc(_proposal()))
    _refused("published_finding_not_in_review", (_finding(1),), (_evidence(1, start=11),), _doc(_proposal()))


def test_a_changed_citation_state_is_refused() -> None:
    _refused(
        "published_finding_not_in_review",
        (_finding(1, state="rebound"),), (_evidence(1),), _doc(_proposal()),
    )


def test_two_findings_cannot_both_stand_for_one_proposal() -> None:
    _refused(
        "published_finding_not_in_review",
        (_finding(1), _finding(2)), (_evidence(1), _evidence(2)),
        _doc(_proposal(0), _proposal(1, paragraph=OTHER_PAR)),
    )


def test_a_merged_observation_is_refused() -> None:
    _refused(
        "published_finding_merged_unexpected",
        (_finding(1, merged=True),), (_evidence(1),), _doc(_proposal()),
    )


def test_a_review_proposal_that_cannot_be_read_is_refused() -> None:
    _refused("review_proposal_unreadable", (_finding(1),), (_evidence(1),), _doc({"proposal_ordinal": 0}))
