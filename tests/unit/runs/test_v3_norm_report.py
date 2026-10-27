"""``read_v3_norm_verification`` and the wire body: what the report is made of, without a database.

The saved review, the certified partitions and the evidence rows are the three inputs; each is
stood in by a small fake so that every refusal is reached on purpose. The database-backed
behaviour is ``tests/integration/runs/test_v3_decisions_over_http.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.bootstrap.adapters import _norm_verification_body
from auditmanager.findings.public import (
    CitationReadRefused, CitationReportRefused, VerifiedCitation, VerifiedCitationReport,
    VerifiedFindingPartitions, VerifiedObservationPartition,
)
from auditmanager.runs import v3_norm_report as module
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_" + "R" * 26
NDOC, NPAR = "ndoc_" + "A" * 26, "npar_" + "B" * 26
QUOTE = "Минимальная ширина эвакуационных путей составляет 1,4 м."
PDF = "Ширина эвакуационных путей принята не менее 1,2 м"


def _citation() -> VerifiedCitation:
    return VerifiedCitation(
        citation_ordinal=1, norms_snapshot_id="ns_" + "S" * 26, norm_document_id=NDOC,
        norm_paragraph_id=NPAR, designation="СП 1.13130", title="Эвакуационные пути",
        clause_number=None, page_label=3, quote=QUOTE, state="verified",
        source_attribution="unattributed",
    )


def _finding() -> VerifiedFindingPartitions:
    partition = VerifiedObservationPartition("fobs_" + "O" * 26, 1, (_citation(),), "1,4 м", "1,2 м")
    return VerifiedFindingPartitions("fnd_" + "F" * 26, partition, ())


def _proposal() -> dict[str, Any]:
    return {
        "proposal_ordinal": 0,
        "evidence": [{"page_number": 7, "quote": PDF, "char_start": 10, "char_end": 10 + len(PDF), "block_id": None}],
        "citations": [{"document_id": NDOC, "paragraph_id": NPAR, "raw_quote": QUOTE, "state": "verified"}],
    }


def _evidence() -> Any:
    return SimpleNamespace(
        finding_observation_id="fobs_" + "O" * 26, evidence_ordinal=0, page_number=7,
        quote=PDF, char_start=10, char_end=10 + len(PDF), block_id=None,
    )


class _Runs:
    def get(self, session: object, run_id: str) -> Any:
        return SimpleNamespace(version_uid="ver_" + "V" * 26)


def _arrange(monkeypatch: pytest.MonkeyPatch, *, document: dict[str, Any], findings: tuple = (),
             evidence: tuple = (), failure: Exception | None = None) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(module, "read_v3_saved_review", lambda *a, **k: SimpleNamespace(document=document))

    def report(session: object, **kwargs: Any) -> VerifiedCitationReport:
        seen.update(kwargs)
        if failure is not None:
            raise failure
        return VerifiedCitationReport(
            run_id=RUN, norms_snapshot_id="ns_" + "S" * 26, norm_retrieval_set_id="nrs_" + "N" * 26,
            status="complete", findings=findings, withheld_by_reason=(), textless_pages=(2, 5),
            error_code=None,
        )

    monkeypatch.setattr(module, "read_verified_citation_report", report)
    monkeypatch.setattr(module, "published_finding_evidence", lambda session, run_id: evidence)
    return seen


def _read() -> Any:
    return module.read_v3_norm_verification(object(), RUN, blob_store=object(), runs=_Runs())  # type: ignore[arg-type]


def _document(*, provisional: list | None = None, rejected: list | None = None, withheld: list | None = None) -> dict[str, Any]:
    return {
        "provisional_citations": [] if provisional is None else provisional,
        "withheld_proposals": [] if withheld is None else withheld,
        "rejected_proposals": [] if rejected is None else rejected,
    }


def test_the_report_asks_for_the_ar_v3_stage_not_the_v1_v2_one(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _arrange(monkeypatch, document=_document())
    _read()
    assert seen["cite_stage_id"] == "ar_v3_citation_review"


def test_the_report_counts_rejected_proposals_by_their_grounding_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    rejected = [{"proposal_ordinal": 1, "reason": "stated_value_not_in_evidence"},
                {"proposal_ordinal": 2, "reason": "quotation_absent"},
                {"proposal_ordinal": 3, "reason": "stated_value_not_in_evidence"}]
    _arrange(monkeypatch, document=_document(rejected=rejected))
    assert _read().withheld_by_reason == (("quotation_absent", 1), ("stated_value_not_in_evidence", 2))


def test_a_rejected_reason_outside_the_closed_enum_refuses_the_whole_report(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(monkeypatch, document=_document(rejected=[{"proposal_ordinal": 1, "reason": "context_only_or_mixed_source"}]))
    with pytest.raises(DomainError) as caught:
        _read()
    assert caught.value.detail_fields["reason"] == "review_rejected_reason_unknown"


def test_withheld_context_only_proposals_are_not_counted_as_a_reason_and_not_a_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(monkeypatch, document=_document(withheld=[{"proposal_ordinal": 0, "reason": "context_only_or_mixed_source"}]))
    report = _read()
    assert report.withheld_by_reason == () and report.findings == ()


def test_a_finding_for_a_withheld_proposal_is_refused_the_report_never_makes_one(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(
        monkeypatch,
        document=_document(withheld=[{"proposal_ordinal": 0, "reason": "context_only_or_mixed_source"}]),
        findings=(_finding(),), evidence=(_evidence(),),
    )
    with pytest.raises(DomainError) as caught:
        _read()
    assert caught.value.detail_fields["reason"] == "published_finding_count_differs_from_review"


def test_a_finding_that_the_review_explains_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(monkeypatch, document=_document(provisional=[_proposal()]), findings=(_finding(),), evidence=(_evidence(),))
    report = _read()
    assert [f.finding_uid for f in report.findings] == ["fnd_" + "F" * 26]
    assert report.textless_pages == (2, 5) and report.status == "complete"


@pytest.mark.parametrize("failure", [CitationReadRefused("citation_partition_invalid"), CitationReportRefused("report_stage_status_invalid")])
def test_an_unverifiable_partition_is_a_refusal_never_a_partial_report(monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    _arrange(monkeypatch, document=_document(), failure=failure)
    with pytest.raises(DomainError) as caught:
        _read()
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert str(failure) in caught.value.detail_fields["reason"]


def test_the_wire_body_carries_the_citations_and_never_a_number_or_a_severity(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(monkeypatch, document=_document(provisional=[_proposal()]), findings=(_finding(),), evidence=(_evidence(),))
    body = _norm_verification_body(_read())
    canonical = body["findings"][0]["canonical"]
    assert canonical["finding_observation_id"] == "fobs_" + "O" * 26
    assert canonical["norm_citations"][0]["quote"] == QUOTE
    assert canonical["norm_citations"][0]["clause_number"] is None  # required-nullable: present, null
    flat = repr(body)
    assert "required_value" not in flat and "stated_value" not in flat and "1,4 м" not in flat.replace(QUOTE, "")
    assert "error_code" not in body  # not set: absent, never null
