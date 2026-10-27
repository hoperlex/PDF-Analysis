"""The finding views of an AR v3 beta Run carry the certified citations and never a number.

``_v3_beta_citations`` reads through the certified-partition reader; any other profile is read exactly
as before (no database access, ``norm_citations`` absent). Pure: the reader is stood in.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import AR_V3_BETA_PROFILE_ID
from auditmanager.api.schemas.findings import observation_body
from auditmanager.bootstrap import adapters
from auditmanager.findings.public import (
    CitationReadRefused, VerifiedCitation, VerifiedCitationRead, VerifiedFindingPartitions,
    VerifiedObservationPartition,
)
from auditmanager.shared.errors import DomainError, ErrorCode

BETA = str(AR_V3_BETA_PROFILE_ID)
OBSERVATION = "fobs_" + "O" * 26
RUN, VERSION = "run_" + "R" * 26, "ver_" + "V" * 26


def _row(profile: str = BETA, observation: str = OBSERVATION) -> SimpleNamespace:
    return SimpleNamespace(
        analysis_profile_id=profile, run_id=RUN, version_uid=VERSION, finding_observation_id=observation,
        finding_uid="fnd_" + "F" * 26, project_uid="prj_" + "P" * 26, category="evacuation",
        finding_text="t", recommendation_text="r", stage_id="text_analysis",
        prompt_bundle_id="pb_" + "B" * 26, provider_mode="recorded", model_call_id=None,
        proposed_severity="operational",
    )


def _read() -> VerifiedCitationRead:
    citation = VerifiedCitation(
        citation_ordinal=1, norms_snapshot_id="ns_" + "S" * 26, norm_document_id="ndoc_" + "A" * 26,
        norm_paragraph_id="npar_" + "B" * 26, designation="СП 1.13130", title="Эвакуационные пути",
        clause_number="4.2.5", page_label=3, quote="Минимальная ширина эвакуационных путей составляет 1,4 м.",
        state="verified", source_attribution="unattributed",
    )
    partition = VerifiedObservationPartition(OBSERVATION, 1, (citation,), "1,4 м", "1,2 м")
    return VerifiedCitationRead(
        RUN, "prj_" + "P" * 26, VERSION, "ns_" + "S" * 26, "nrs_" + "N" * 26, "published",
        (VerifiedFindingPartitions("fnd_" + "F" * 26, partition, ()),),
    )


def test_a_beta_run_reads_its_certified_partitions_through_the_v3_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def read(session: object, **kwargs: object) -> VerifiedCitationRead:
        seen.update(kwargs)
        return _read()

    monkeypatch.setattr("auditmanager.findings.public.read_verified_citations", read)
    views = adapters._v3_beta_citations(object(), [_row()])  # type: ignore[arg-type]
    assert seen == {"run_id": RUN, "version_uid": VERSION, "profile_id": BETA,
                    "cite_stage_id": "ar_v3_citation_review"}
    (citation,) = views[OBSERVATION]
    assert citation.quote.startswith("Минимальная") and citation.designation == "СП 1.13130"
    assert citation.clause_number == "4.2.5" and citation.state == "verified"


def test_a_run_of_another_profile_is_read_as_before_with_no_database_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "auditmanager.findings.public.read_verified_citations",
        lambda *a, **k: pytest.fail("a legacy run must not be read as a v3 run"),
    )
    assert adapters._v3_beta_citations(object(), [_row(profile="ap_" + "L" * 26)]) == {}  # type: ignore[arg-type]
    assert adapters._v3_beta_citations(object(), []) == {}  # type: ignore[arg-type]
    legacy = adapters._observation_view(_row(profile="ap_" + "L" * 26), [], {})
    assert legacy.norm_citations is None and "norm_citations" not in observation_body(legacy)


def test_an_inconsistent_partition_is_a_storage_integrity_error_never_a_finding_without_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(session: object, **kwargs: object) -> None:
        raise CitationReadRefused("citation_partition_invalid")

    monkeypatch.setattr("auditmanager.findings.public.read_verified_citations", refuse)
    with pytest.raises(DomainError) as caught:
        adapters._v3_beta_citations(object(), [_row()])  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR


def test_the_observation_view_serves_the_citations_and_never_a_claimed_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("auditmanager.findings.public.read_verified_citations", lambda s, **k: _read())
    row = _row()
    views = adapters._v3_beta_citations(object(), [row])  # type: ignore[arg-type]
    observation = adapters._observation_view(row, [], views)
    body = observation_body(observation)
    assert [c["quote"] for c in body["norm_citations"]] == [views[OBSERVATION][0].quote]
    assert "required_value" not in body and "stated_value" not in body
    assert body["proposed_severity"] == "operational"
