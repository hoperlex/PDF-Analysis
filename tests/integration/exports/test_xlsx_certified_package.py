"""One unserved W57b source chain yields cells or refuses a foreign Run pin."""

from __future__ import annotations

import io
import zipfile
from dataclasses import replace
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx import certified_package
from auditmanager.exports.xlsx.certified_package import (
    CertifiedXlsxPackageRefused,
    prepare_certified_xlsx_package,
)
from auditmanager.exports.xlsx.package import ExportAuthorization
from auditmanager.exports.xlsx.preflight import VerifiedXlsxRunSource
from auditmanager.exports.xlsx.source_labels import VerifiedPageLabels
from auditmanager.findings.citation_reader import (
    VerifiedCitation,
    VerifiedCitationRead,
    VerifiedFindingPartitions,
    VerifiedObservationPartition,
)


QUOTE = "Минимальная ширина прохода составляет 1,4 м"
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


class _Rows:
    def __init__(self, values: object):
        self.values = values

    def mappings(self) -> _Rows:
        return self

    def one_or_none(self):
        return self.values

    def first(self):
        return self.values

    def all(self):
        return self.values


class _Session:
    def __init__(self, *, change_pin_after_render: bool = False):
        self.pin_reads = 0
        self.package_reads = 0
        self.change_pin_after_render = change_pin_after_render

    def execute(self, statement, parameters):
        sql = str(statement)
        assert sql.lstrip().upper().startswith("SELECT")
        assert parameters == {"run_id": "run_1"}
        if "SELECT run_id, project_uid, version_uid, state" in sql:
            self.pin_reads += 1
            set_id = "nrs_changed" if self.change_pin_after_render and self.pin_reads == 2 else "nrs_1"
            return _Rows({
                "run_id": "run_1", "project_uid": "prj_1", "version_uid": "ver_1",
                "state": "published", "analysis_profile_id": "ar_v3",
                "norms_snapshot_id": "ns_1", "norm_retrieval_set_id": set_id,
            })
        if "FROM audit_run r" in sql:
            self.package_reads += 1
            return _Rows({
                "run_id": "run_1", "project_uid": "prj_1", "version_uid": "ver_1",
                "analysis_profile_id": "ar_v3", "norms_snapshot_id": "ns_1",
                "snapshot_key": "pinned-key",
            })
        if "FROM finding f" in sql:
            self.package_reads += 1
            return _Rows([{
                "finding_uid": "fnd_1", "project_uid": "prj_1",
                "version_uid": "ver_1", "allocated_by_run_id": "run_1",
                "category": "fire_safety", "canonical_observation_id": "obs_1",
                "finding_observation_id": "obs_1", "observation_run_id": "run_1",
                "observation_finding_uid": "fnd_1", "observation_category": "fire_safety",
                "finding_text": "Проверить проход", "recommendation_text": "Исправить",
                "proposed_severity": "operational", "evidence_ordinal": 0,
                "page_number": 2, "current_verdict": "accepted",
                "decided_severity": "critical", "latest_comment": "Проверено",
                "verdict_finding_uid": "fnd_1",
            }])
        pytest.fail(f"unexpected SQL: {sql}")


def _source() -> VerifiedXlsxRunSource:
    return VerifiedXlsxRunSource(
        "run_1", "ver_1", "published",
        VerifiedPageLabels("ver_1", {2: "АР-2"}, "ver_1:blob_1:digest"),
    )


def _citations() -> VerifiedCitationRead:
    citation = VerifiedCitation(
        citation_ordinal=1, norms_snapshot_id="ns_1",
        norm_document_id="ndoc_1", norm_paragraph_id="npar_1",
        designation="СП 54.13330.2022", title="Жилые здания",
        clause_number="7.1.4", page_label=7, quote=QUOTE,
        state="verified", source_attribution="consultant_plus",
    )
    return VerifiedCitationRead(
        run_id="run_1", project_uid="prj_1", version_uid="ver_1",
        norms_snapshot_id="ns_1", norm_retrieval_set_id="nrs_1",
        run_state="published", findings=(VerifiedFindingPartitions(
            "fnd_1", VerifiedObservationPartition(
                "obs_1", 1, (citation,), "1,4 м", "1,2 м",
            ), (),
        ),),
    )


def _authorization(*, decision: str = "allow") -> ExportAuthorization:
    return ExportAuthorization(
        "run_1", "usr_1", "exportRunXlsx", decision, "decision_1",
    )


def _prepare(monkeypatch, session: _Session, *, citation_read=None, run_source=None):
    source = run_source or _source()
    observed = []

    def preflight(own_session, run_id, *, read_blob):
        assert own_session is session and run_id == "run_1" and callable(read_blob)
        observed.append("preflight")
        return source

    def read_citations(own_session, *, run_id, version_uid, profile_id):
        assert own_session is session
        assert (run_id, version_uid, profile_id) == ("run_1", "ver_1", "ar_v3")
        observed.append("citations")
        return citation_read or _citations()

    monkeypatch.setattr(certified_package, "read_xlsx_run_source_preflight", preflight)
    package = prepare_certified_xlsx_package(
        session, run_id="run_1", authorization=_authorization(),
        read_blob=lambda _id: b"unused-after-monkeypatch",
        read_citations=read_citations, profile_id="ar_v3",
        attribution="recorded",
    )
    return package, observed


def test_certified_chain_renders_actual_xlsx_with_pinned_citation(monkeypatch):
    session = _Session()
    package, observed = _prepare(monkeypatch, session)
    assert observed == ["preflight", "citations"]
    assert session.pin_reads == 2 and session.package_reads == 2
    assert package.citation_source_ref == "run_1:ns_1:nrs_1"
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    cells = {}
    for cell in root.findall(f".//{MAIN}c"):
        node = cell.find(f"{MAIN}is/{MAIN}t")
        if node is None:
            node = cell.find(f"{MAIN}v")
        cells[cell.attrib["r"]] = node.text or "" if node is not None else ""
    assert cells["B2"] == "АР-2"
    assert cells["H2"] == "СП 54.13330.2022, 7.1.4"
    assert cells["I2"] == QUOTE


def test_foreign_citation_snapshot_refuses_before_render(monkeypatch):
    session = _Session()
    foreign = replace(_citations(), norms_snapshot_id="ns_foreign")
    with pytest.raises(CertifiedXlsxPackageRefused, match="xlsx_citation_pin_mismatch"):
        _prepare(monkeypatch, session, citation_read=foreign)
    assert session.pin_reads == 1 and session.package_reads == 0


def test_foreign_preflight_run_refuses_before_citation_read(monkeypatch):
    session = _Session()
    foreign = replace(_source(), run_id="run_foreign")
    with pytest.raises(CertifiedXlsxPackageRefused, match="xlsx_run_pin_mismatch"):
        _prepare(monkeypatch, session, run_source=foreign)
    assert session.pin_reads == 1 and session.package_reads == 0


def test_changed_run_pin_after_render_refuses_result(monkeypatch):
    session = _Session(change_pin_after_render=True)
    with pytest.raises(CertifiedXlsxPackageRefused, match="xlsx_run_pin_changed"):
        _prepare(monkeypatch, session)
    assert session.pin_reads == 2 and session.package_reads == 2


def test_denied_decision_refuses_before_any_source_read(monkeypatch):
    monkeypatch.setattr(
        certified_package, "read_xlsx_run_source_preflight",
        lambda *args, **kwargs: pytest.fail("source read occurred"),
    )
    with pytest.raises(CertifiedXlsxPackageRefused, match="xlsx_export_inputs_invalid"):
        prepare_certified_xlsx_package(
            _Session(), run_id="run_1", authorization=_authorization(decision="deny"),
            read_blob=lambda _id: b"", read_citations=lambda *args, **kwargs: _citations(),
            profile_id="ar_v3", attribution="recorded",
        )
