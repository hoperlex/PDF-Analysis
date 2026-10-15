"""The XLSX package seam composes the complete read without policy defaults."""

from __future__ import annotations

import io
import zipfile
from dataclasses import replace
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx.package import (
    ExportAuthorization,
    ExportSources,
    prepare_xlsx_package,
)
from auditmanager.exports.xlsx.projection import CitationRead
from auditmanager.exports.xlsx.writer import CONTENT_TYPE


_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_HEADER = {
    "run_id": "run_1", "project_uid": "prj_1", "version_uid": "ver_1",
    "analysis_profile_id": "ar_v3", "norms_snapshot_id": "ns_1",
    "snapshot_key": "pinned-key",
}


def _row(observation_id: str, page: int, *, canonical: str = "obs_2") -> dict:
    return {
        "finding_uid": "fnd_1", "project_uid": "prj_1", "version_uid": "ver_1",
        "allocated_by_run_id": "run_1", "category": "fire_safety",
        "canonical_observation_id": canonical,
        "finding_observation_id": observation_id, "observation_run_id": "run_1",
        "observation_finding_uid": "fnd_1", "observation_category": "fire_safety",
        "finding_text": "=literal" if observation_id == "obs_2" else "Повтор",
        "recommendation_text": "Исправить", "proposed_severity": "operational",
        "evidence_ordinal": 0, "page_number": page,
        "current_verdict": "accepted", "decided_severity": "critical",
        "latest_comment": "Проверено", "verdict_finding_uid": "fnd_1",
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
    def __init__(self, header=_HEADER, rows=None):
        self.header = header
        self.rows = [_row("obs_1", 2), _row("obs_2", 3)] if rows is None else rows
        self.queries: list[str] = []

    def execute(self, statement, parameters):
        sql = str(statement)
        assert sql.lstrip().upper().startswith("SELECT")
        assert parameters == {"run_id": "run_1"}
        self.queries.append(sql)
        return _Rows(self.header if len(self.queries) == 1 else self.rows)


def _authorization() -> ExportAuthorization:
    return ExportAuthorization("run_1", "usr_1", "exportRunXlsx", "allow", "policy-decision-1")


def _sources() -> ExportSources:
    return ExportSources(
        page_labels={2: "АР-2", 3: "АР-3"},
        page_label_source_ref="page-map-1",
        citations_by_finding={"fnd_1": (CitationRead("СП 1", "2.1", "Норма"),)},
        citation_source_ref="citation-set-1",
        attribution="recorded",
    )


def _cells(content: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        assert all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist())
        root = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    values = {}
    for cell in root.findall(f".//{_NS}c"):
        text = cell.find(f"{_NS}is/{_NS}t")
        if text is None:
            text = cell.find(f"{_NS}v")
        values[cell.attrib["r"]] = text.text or "" if text is not None else ""
    return values


def test_package_reads_projects_and_writes_repeatable_zip() -> None:
    first_session = _Session()
    first = prepare_xlsx_package(
        first_session, authorization=_authorization(), sources=_sources(),
    )
    second = prepare_xlsx_package(
        _Session(), authorization=_authorization(), sources=_sources(),
    )
    assert first == second
    assert first is not None
    assert first.content_type == CONTENT_TYPE
    assert first.replacement_count == 0
    assert (
        first.decision_ref, first.page_label_source_ref, first.citation_source_ref,
    ) == ("policy-decision-1", "page-map-1", "citation-set-1")
    assert len(first_session.queries) == 2
    cells = _cells(first.content)
    assert cells["B2"] == "АР-3"
    assert cells["D2"] == "=literal"
    assert cells["H2"] == "СП 1, 2.1"
    assert cells["I2"] == "Норма"
    assert cells["B3"] == "АР-2" and cells["D3"] == "также найдено"
    with zipfile.ZipFile(io.BytesIO(first.content)) as archive:
        assert b"<f>" not in archive.read("xl/worksheets/sheet2.xml")


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        replace(_authorization(), run_id=""),
        replace(_authorization(), principal_id=""),
        replace(_authorization(), operation="exportRunCsv"),
        replace(_authorization(), decision="deny"),
        replace(_authorization(), decision_ref=""),
    ],
)
def test_missing_or_denied_policy_fails_before_sql(authorization) -> None:
    session = _Session()
    with pytest.raises(ValueError, match="xlsx_package_authorization_invalid"):
        prepare_xlsx_package(session, authorization=authorization, sources=_sources())
    assert session.queries == []


@pytest.mark.parametrize(
    "sources",
    [
        None,
        replace(_sources(), page_label_source_ref=""),
        replace(_sources(), citation_source_ref=""),
        replace(_sources(), attribution=""),
        replace(_sources(), page_labels={2: " "}),
        replace(_sources(), page_labels={True: "АР-1"}),
        replace(_sources(), citations_by_finding={"fnd_1": None}),
    ],
)
def test_missing_source_provenance_or_invalid_material_fails_before_sql(sources) -> None:
    session = _Session()
    with pytest.raises(ValueError, match="xlsx_package_(sources|page_label|citations)_invalid"):
        prepare_xlsx_package(session, authorization=_authorization(), sources=sources)
    assert session.queries == []


def test_missing_page_label_or_citation_partition_fails_without_package() -> None:
    with pytest.raises(ValueError, match="xlsx_read_page_label_missing"):
        prepare_xlsx_package(
            _Session(), authorization=_authorization(),
            sources=replace(_sources(), page_labels={2: "АР-2"}),
        )
    with pytest.raises(ValueError, match="xlsx_read_citation_partition_invalid"):
        prepare_xlsx_package(
            _Session(), authorization=_authorization(),
            sources=replace(_sources(), citations_by_finding={}),
        )


def test_absent_run_and_explicit_empty_run() -> None:
    assert prepare_xlsx_package(
        _Session(header=None), authorization=_authorization(), sources=_sources(),
    ) is None
    empty = prepare_xlsx_package(
        _Session(rows=[]), authorization=_authorization(),
        sources=replace(_sources(), citations_by_finding={}),
    )
    assert empty is not None
    assert _cells(empty.content) == {
        f"{column}1": value for column, value in zip(
            "ABCDEFGHIJK",
            (
                "№", "Лист/стр.", "Категория", "Замечание", "Рекомендация",
                "Серьёзность (решение эксперта)", "Серьёзность (предложение модели)",
                "Норма (документ, пункт)", "Цитата нормы", "Решение эксперта",
                "Комментарий",
            ),
        )
    }
