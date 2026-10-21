"""Certified 0023 partitions reach actual XLSX cells without a silent zero."""

from __future__ import annotations

import io
import zipfile
from dataclasses import replace
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx.certified_sources import (
    XlsxCertifiedSourcesRefused,
    sources_from_certified_reads,
)
from auditmanager.exports.xlsx.package import ExportAuthorization, prepare_xlsx_package
from auditmanager.exports.xlsx.preflight import VerifiedXlsxRunSource
from auditmanager.exports.xlsx.source_labels import VerifiedPageLabels
from auditmanager.findings.citation_reader import (
    VerifiedCitation,
    VerifiedCitationRead,
    VerifiedFindingPartitions,
    VerifiedObservationPartition,
)


_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_QUOTE_1 = "Минимальная ширина прохода составляет 1,4 м"
_QUOTE_2 = "Высота ограждения принимается не менее 1,2 м"


def _citation(ordinal: int, quote: str, clause: str) -> VerifiedCitation:
    return VerifiedCitation(
        citation_ordinal=ordinal, norms_snapshot_id="ns_1",
        norm_document_id="ndoc_1", norm_paragraph_id=f"npar_{ordinal}",
        designation="СП 54.13330.2022", title="Жилые здания",
        clause_number=clause, page_label=7, quote=quote,
        state="verified", source_attribution="consultant_plus",
    )


def _reads(*, certified_zero: bool = False):
    labels = VerifiedPageLabels("ver_1", {2: "АР-2", 3: "АР-3"}, "ver_1:blob_1:digest")
    run = VerifiedXlsxRunSource("run_1", "ver_1", "published", labels)
    canonical = VerifiedObservationPartition(
        "obs_2", 0 if certified_zero else 1,
        () if certified_zero else (_citation(1, _QUOTE_1, "7.1.4"),),
        None if certified_zero else "1,4 м",
        None if certified_zero else "1,2 м",
    )
    member = VerifiedObservationPartition(
        "obs_1", 0 if certified_zero else 1,
        () if certified_zero else (_citation(1, _QUOTE_2, "8.2"),),
        None if certified_zero else "1,2 м",
        None if certified_zero else "1,0 м",
    )
    certified = VerifiedCitationRead(
        run_id="run_1", project_uid="prj_1", version_uid="ver_1",
        norms_snapshot_id="ns_1", norm_retrieval_set_id="nset_1",
        run_state="published",
        findings=(VerifiedFindingPartitions("fnd_1", canonical, (member,)),),
    )
    return run, certified


def _row(observation_id: str, page: int, *, category: str = "fire_safety") -> dict:
    return {
        "finding_uid": "fnd_1", "project_uid": "prj_1", "version_uid": "ver_1",
        "allocated_by_run_id": "run_1", "category": category,
        "canonical_observation_id": "obs_2",
        "finding_observation_id": observation_id, "observation_run_id": "run_1",
        "observation_finding_uid": "fnd_1", "observation_category": category,
        "finding_text": "Проверить значение", "recommendation_text": "Исправить",
        "proposed_severity": "operational", "evidence_ordinal": 0,
        "page_number": page, "current_verdict": "accepted",
        "decided_severity": "critical", "latest_comment": "Проверено",
        "verdict_finding_uid": "fnd_1",
    }


class _Rows:
    def __init__(self, values):
        self.values = values

    def mappings(self):
        return self

    def first(self):
        return self.values

    def all(self):
        return self.values


class _Session:
    def __init__(self, *, category: str = "fire_safety"):
        self.queries = 0
        self.category = category

    def execute(self, statement, parameters):
        assert str(statement).lstrip().upper().startswith("SELECT")
        assert parameters == {"run_id": "run_1"}
        self.queries += 1
        if self.queries == 1:
            return _Rows({
                "run_id": "run_1", "project_uid": "prj_1", "version_uid": "ver_1",
                "analysis_profile_id": "ar_v3", "norms_snapshot_id": "ns_1",
                "snapshot_key": "pinned-key",
            })
        return _Rows([
            _row("obs_1", 2, category=self.category),
            _row("obs_2", 3, category=self.category),
        ])


def _cells(content: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        root = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    cells = {}
    for cell in root.findall(f".//{_NS}c"):
        text = cell.find(f"{_NS}is/{_NS}t")
        if text is None:
            text = cell.find(f"{_NS}v")
        cells[cell.attrib["r"]] = text.text or "" if text is not None else ""
    return cells


def _package(
    run: VerifiedXlsxRunSource, certified: VerifiedCitationRead,
    *, category: str = "fire_safety",
):
    sources = sources_from_certified_reads(run, certified, attribution="recorded")
    session = _Session(category=category)
    result = prepare_xlsx_package(
        session,
        authorization=ExportAuthorization(
            "run_1", "usr_1", "exportRunXlsx", "allow", "policy-decision-1",
        ),
        sources=sources,
    )
    assert result is not None
    assert session.queries == 2
    return result


def test_canonical_and_member_certified_citations_reach_real_xlsx_cells():
    run, certified = _reads()
    first = _package(run, certified)
    assert first == _package(run, certified)
    cells = _cells(first.content)
    assert cells["B2"] == "АР-3"
    assert cells["H2"] == "СП 54.13330.2022, 7.1.4\nСП 54.13330.2022, 8.2"
    assert cells["I2"] == _QUOTE_1 + "\n" + _QUOTE_2
    assert cells["D3"] == "также найдено"
    assert first.citation_source_ref == "run_1:ns_1:nset_1"


def test_explicit_certified_zero_produces_blank_norm_cells():
    run, certified = _reads(certified_zero=True)
    sources = sources_from_certified_reads(run, certified, attribution="recorded")
    assert sources.citations_by_finding == {"fnd_1": ()}
    cells = _cells(_package(run, certified, category="dimensions").content)
    assert cells["H2"] == "" and cells["I2"] == ""


@pytest.mark.parametrize("mutation", [
    "run", "version", "state", "label_version", "count", "ordinal",
    "duplicate_member", "duplicate_finding", "missing_canonical",
])
def test_foreign_or_incomplete_partition_refuses_before_package(mutation: str):
    run, certified = _reads()
    finding = certified.findings[0]
    if mutation == "run":
        certified = replace(certified, run_id="run_other")
    elif mutation == "version":
        certified = replace(certified, version_uid="ver_other")
    elif mutation == "state":
        certified = replace(certified, run_state="partial")
    elif mutation == "label_version":
        run = replace(run, page_labels=replace(run.page_labels, version_uid="ver_other"))
    elif mutation == "count":
        canonical = replace(finding.canonical, citation_count=2)
        certified = replace(certified, findings=(replace(finding, canonical=canonical),))
    elif mutation == "ordinal":
        bad = replace(finding.canonical.citations[0], citation_ordinal=2)
        canonical = replace(finding.canonical, citations=(bad,))
        certified = replace(certified, findings=(replace(finding, canonical=canonical),))
    elif mutation == "duplicate_member":
        certified = replace(certified, findings=(replace(
            finding, merged_observations=(finding.canonical,)
        ),))
    elif mutation == "duplicate_finding":
        certified = replace(certified, findings=(finding, finding))
    elif mutation == "missing_canonical":
        certified = replace(certified, findings=(replace(finding, canonical=None),))
    with pytest.raises(XlsxCertifiedSourcesRefused):
        sources_from_certified_reads(run, certified, attribution="recorded")


def test_missing_finding_is_not_silently_interpreted_as_certified_zero():
    run, certified = _reads()
    incomplete = replace(certified, findings=())
    sources = sources_from_certified_reads(run, incomplete, attribution="recorded")
    assert sources.citations_by_finding == {}
    with pytest.raises(ValueError, match="xlsx_read_citation_partition_invalid"):
        prepare_xlsx_package(
            _Session(),
            authorization=ExportAuthorization(
                "run_1", "usr_1", "exportRunXlsx", "allow", "policy-decision-1",
            ),
            sources=sources,
        )
