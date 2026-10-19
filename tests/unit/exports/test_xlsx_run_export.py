"""`W57B-NORMS-CATALOGUE-XLSX-01`: the run's Excel export use case, without a database.

A fake session answers the use case's own statements and the certified package's two reads;
the run/page preflight and the certified chain are replaced where a case says so, exactly as
``tests/integration/exports/test_xlsx_certified_package.py`` replaces them. The workbook is
opened as the ZIP it is and its sheet XML read cell by cell (no spreadsheet application runs
on this host). The database- and S3-backed case is
``tests/integration/exports/test_xlsx_run_export.py``.
"""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports import ExportAuthorization, XlsxExport, export_run_xlsx
from auditmanager.exports.xlsx import run_export
from auditmanager.exports.xlsx.certified_package import CertifiedXlsxPackageRefused
from auditmanager.exports.xlsx.package import PreparedXlsx
from auditmanager.exports.xlsx.preflight import VerifiedXlsxRunSource
from auditmanager.exports.xlsx.source_labels import VerifiedPageLabels
from auditmanager.exports.xlsx.writer import CONTENT_TYPE, FINDING_COLUMNS
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity.errors import IdentifierFormatError

RUN = "run_01M5B0000000000000000000R1"
VERSION = "ver_01M5B0000000000000000000V1"
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _facts(**changes: object) -> dict:
    values = {
        "run_id": RUN, "state": "published", "provider_mode": "recorded",
        "analysis_profile_id": "ap_01M5B00000000000000000AP01",
        "norms_snapshot_id": None, "norm_retrieval_set_id": None,
        "has_partitions": False, "has_citations": False,
    }
    values.update(changes)
    return values


def _finding_row(uid: str, observation: str, page: int, **changes: object) -> dict:
    values = {
        "finding_uid": uid, "project_uid": "prj_1", "version_uid": VERSION,
        "allocated_by_run_id": RUN, "category": "documentation",
        "canonical_observation_id": None,
        "finding_observation_id": observation, "observation_run_id": RUN,
        "observation_finding_uid": uid, "observation_category": "documentation",
        "finding_text": f"Замечание {uid}", "recommendation_text": None,
        "proposed_severity": None, "evidence_ordinal": 0, "page_number": page,
        "current_verdict": "pending", "decided_severity": None, "latest_comment": None,
        "verdict_finding_uid": uid,
    }
    values.update(changes)
    return values


class _Result:
    def __init__(self, values: object) -> None:
        self.values = values

    def mappings(self) -> "_Result":
        return self

    def scalars(self) -> "_Result":
        return _Result([row["finding_uid"] for row in self.values])  # type: ignore[union-attr]

    def first(self) -> object:
        return self.values

    def all(self) -> object:
        return self.values


class _Session:
    """Answers by statement shape; refuses anything it was not told about."""

    def __init__(self, facts: dict | None, findings: list[dict] | None = None) -> None:
        self.facts = facts
        self.findings = findings if findings is not None else [
            _finding_row("fnd_1", "obs_1", 2), _finding_row("fnd_2", "obs_2", 3),
        ]
        self.statements: list[str] = []

    def execute(self, statement, parameters):
        sql = " ".join(str(statement).split())
        assert sql.upper().startswith("SELECT")
        assert parameters == {"run_id": RUN}
        if "AS has_partitions" in sql:
            self.statements.append("facts")
            return _Result(self.facts)
        if sql.startswith("SELECT f.finding_uid FROM finding f"):
            self.statements.append("finding_uids")
            unique = {row["finding_uid"]: row for row in self.findings}
            return _Result(list(unique.values()))
        if "LEFT JOIN norms_snapshot s" in sql:
            self.statements.append("package_run")
            return _Result({
                "run_id": RUN, "project_uid": "prj_1", "version_uid": VERSION,
                "analysis_profile_id": self.facts["analysis_profile_id"],
                "norms_snapshot_id": None, "snapshot_key": None,
            })
        if "LEFT JOIN finding_observation o" in sql:
            self.statements.append("package_findings")
            return _Result(self.findings)
        pytest.fail(f"unexpected SQL: {sql}")


def _authorization(**changes: object) -> ExportAuthorization:
    values = {
        "run_id": RUN, "principal_id": "usr_1", "operation": "exportRunXlsx",
        "decision": "allow", "decision_ref": "role-register:exportRunXlsx",
    }
    values.update(changes)
    return ExportAuthorization(**values)


def _labels() -> VerifiedXlsxRunSource:
    return VerifiedXlsxRunSource(
        RUN, VERSION, "published",
        VerifiedPageLabels(VERSION, {1: "101", 2: "102", 3: "103"}, f"{VERSION}:blob:digest"),
    )


@pytest.fixture
def preflight(monkeypatch):
    calls: list[str] = []

    def fake(session, run_id, *, read_blob):
        assert run_id == RUN and callable(read_blob)
        calls.append("preflight")
        return _labels()

    monkeypatch.setattr(run_export, "read_xlsx_run_source_preflight", fake)
    return calls


def _export(session, **arguments):
    arguments.setdefault("authorization", _authorization())
    arguments.setdefault("read_blob", lambda blob_id: pytest.fail("no Blob read expected"))
    arguments.setdefault("read_citations", None)
    return export_run_xlsx(session, RUN, **arguments)


def _cells(content: bytes, part: str) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read(part))
    cells: dict[str, str] = {}
    for cell in root.findall(f".//{MAIN}c"):
        node = cell.find(f"{MAIN}is/{MAIN}t")
        if node is None:
            node = cell.find(f"{MAIN}v")
        cells[cell.attrib["r"]] = (node.text or "") if node is not None else ""
    return cells


# --- the refusals exportRunCsv makes, before anything else is read -------------------------


def test_an_unknown_run_is_not_found_after_one_read() -> None:
    session = _Session(None)
    with pytest.raises(DomainError) as caught:
        _export(session)
    assert caught.value.code is ErrorCode.NOT_FOUND
    assert dict(caught.value.detail_fields) == {"aggregate_type": "AuditRun"}
    assert session.statements == ["facts"]


@pytest.mark.parametrize("state", ["queued", "running", "failed", "cancelled"])
def test_a_run_that_publishes_no_result_is_refused_after_one_read(state: str) -> None:
    session = _Session(_facts(state=state))
    with pytest.raises(DomainError) as caught:
        _export(session, read_citations=lambda *a, **k: pytest.fail("citations read"))
    assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert dict(caught.value.detail_fields) == {"machine": "audit_run", "current_state": state}
    assert session.statements == ["facts"]


def test_a_malformed_run_identity_is_refused_before_any_read() -> None:
    session = _Session(_facts())
    with pytest.raises(IdentifierFormatError):
        export_run_xlsx(
            session, "run_not_an_identity", authorization=_authorization(),
            read_blob=lambda blob_id: b"", read_citations=None,
        )
    assert session.statements == []


@pytest.mark.parametrize(
    "authorization",
    [
        _authorization(run_id="run_01M5B0000000000000000000R2"),
        _authorization(operation="exportRunCsv"),
        _authorization(decision="deny"),
    ],
)
def test_an_authorization_for_anything_else_is_refused(preflight, authorization) -> None:
    with pytest.raises(ValueError, match="xlsx_export_authorization_invalid"):
        _export(_Session(_facts()), authorization=authorization)
    assert preflight == []


# --- a run without citation partitions -----------------------------------------------------


def test_a_v1_run_renders_with_labels_and_empty_norm_columns(preflight) -> None:
    session = _Session(_facts(state="partial"))
    export = _export(session)
    assert isinstance(export, XlsxExport)
    assert (export.run_id, export.run_state, export.content_type) == (RUN, "partial", CONTENT_TYPE)
    assert export.citation_source_ref == f"{RUN}:no-citation-partitions"
    assert export.page_label_source_ref == f"{VERSION}:blob:digest"
    assert export.replacement_count == 0 and export.byte_size == len(export.content)
    assert preflight == ["preflight"]
    assert session.statements == ["facts", "finding_uids", "package_run", "package_findings"]

    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        assert archive.namelist() == [
            "[Content_Types].xml", "_rels/.rels", "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels", "xl/styles.xml",
            "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml",
        ]
        assert all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist())
        workbook = archive.read("xl/workbook.xml").decode("utf-8")
        assert '<sheet name="Сводка"' in workbook and '<sheet name="Замечания"' in workbook
        assert b"<f>" not in archive.read("xl/worksheets/sheet2.xml")

    findings = _cells(export.content, "xl/worksheets/sheet2.xml")
    header = tuple(findings[f"{column}1"] for column in "ABCDEFGHIJK")
    assert header == FINDING_COLUMNS
    assert [findings["A2"], findings["B2"], findings["D2"]] == ["1", "102", "Замечание fnd_1"]
    assert [findings["A3"], findings["B3"], findings["D3"]] == ["2", "103", "Замечание fnd_2"]
    for row in ("2", "3"):
        assert findings[f"E{row}"] == ""  # no recommendation: an empty cell
        assert findings[f"H{row}"] == "" and findings[f"I{row}"] == ""  # no citations
        assert findings[f"J{row}"] == "pending"
    assert "A4" not in findings

    summary = _cells(export.content, "xl/worksheets/sheet1.xml")
    assert (summary["A4"], summary["B4"]) == ("Прогон", RUN)
    assert (summary["A6"], summary["B6"]) == ("Ключ снимка", "")
    assert (summary["A7"], summary["B7"]) == (
        "Атрибуция", "ответы модели воспроизведены из записи (recorded)"
    )


def test_the_same_run_state_gives_the_same_bytes(preflight) -> None:
    first = _export(_Session(_facts()))
    second = _export(_Session(_facts()))
    assert first.content == second.content


def test_a_run_with_no_findings_is_a_header_only_workbook(preflight) -> None:
    export = _export(_Session(_facts(), findings=[]))
    findings = _cells(export.content, "xl/worksheets/sheet2.xml")
    assert set(findings) == {f"{column}1" for column in "ABCDEFGHIJK"}


def test_the_live_attribution(preflight) -> None:
    export = _export(_Session(_facts(provider_mode="live")))
    summary = _cells(export.content, "xl/worksheets/sheet1.xml")
    assert summary["B7"] == "ответы модели получены живым вызовом (live)"


# --- the page-label source -----------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "xlsx_page_source_binding_invalid",
        "xlsx_page_source_bytes_invalid",
        "xlsx_page_source_layout_invalid",
        "xlsx_page_source_label_missing",
        "xlsx_run_page_source_missing",
    ],
)
def test_an_unverifiable_page_source_is_storage_integrity_error(monkeypatch, code) -> None:
    def refuse(session, run_id, *, read_blob):
        raise ValueError(code)

    monkeypatch.setattr(run_export, "read_xlsx_run_source_preflight", refuse)
    session = _Session(_facts())
    with pytest.raises(DomainError) as caught:
        _export(session)
    assert caught.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert dict(caught.value.detail_fields) == {"role": "source.structured_companion"}
    assert session.statements == ["facts"]


def test_a_storage_failure_behind_the_page_source_is_answered_as_itself(monkeypatch) -> None:
    unavailable = DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="object_storage")

    def refuse(session, run_id, *, read_blob):
        try:
            raise unavailable
        except DomainError as exc:
            raise ValueError("xlsx_page_source_unreadable") from exc

    monkeypatch.setattr(run_export, "read_xlsx_run_source_preflight", refuse)
    with pytest.raises(DomainError) as caught:
        _export(_Session(_facts()))
    assert caught.value is unavailable


def test_a_rendering_failure_is_not_disguised_as_a_refusal(preflight) -> None:
    broken = [_finding_row("fnd_1", "obs_1", 2, verdict_finding_uid=None)]
    with pytest.raises(ValueError, match="xlsx_read_incomplete_finding"):
        _export(_Session(_facts(), findings=broken))


# --- a run with citation partitions --------------------------------------------------------


@pytest.mark.parametrize(
    "facts",
    [
        _facts(norm_retrieval_set_id="nrs_01M5B000000000000000000NR1",
               norms_snapshot_id="ns_01M5B000000000000000000NS1"),
        _facts(has_partitions=True),
        _facts(has_citations=True),
    ],
)
def test_a_citing_run_goes_through_the_certified_chain(monkeypatch, facts) -> None:
    seen: dict[str, object] = {}

    def certified(session, *, run_id, authorization, read_blob, read_citations, profile_id,
                  attribution):
        seen.update(run_id=run_id, profile_id=profile_id, attribution=attribution,
                    citations=read_citations(session, run_id=run_id))
        return PreparedXlsx(
            content=b"PK-workbook", content_type=CONTENT_TYPE, replacement_count=0,
            decision_ref=authorization.decision_ref, page_label_source_ref="labels",
            citation_source_ref="run:ns:nrs",
        )

    monkeypatch.setattr(run_export, "prepare_certified_xlsx_package", certified)
    monkeypatch.setattr(
        run_export, "read_xlsx_run_source_preflight",
        lambda *a, **k: pytest.fail("the legacy branch ran"),
    )
    session = _Session(facts)
    export = _export(session, read_citations=lambda session, **arguments: "certified-read")
    assert seen == {
        "run_id": RUN, "profile_id": facts["analysis_profile_id"],
        "attribution": "ответы модели воспроизведены из записи (recorded)",
        "citations": "certified-read",
    }
    assert export.citation_source_ref == "run:ns:nrs" and export.content == b"PK-workbook"
    assert session.statements == ["facts"]


def _citing_facts() -> dict:
    return _facts(norm_retrieval_set_id="nrs_01M5B000000000000000000NR1",
                  norms_snapshot_id="ns_01M5B000000000000000000NS1")


def _assert_citation_unavailable(caught) -> None:
    assert caught.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
    assert dict(caught.value.detail_fields) == {
        "reference_kind": "norm_retrieval_set",
        "analysis_profile_id": "ap_01M5B00000000000000000AP01",
        "norms_snapshot_id": "ns_01M5B000000000000000000NS1",
    }


def test_a_citing_run_without_a_reader_is_refused_not_emptied() -> None:
    with pytest.raises(DomainError) as caught:
        _export(_Session(_citing_facts()), read_citations=None)
    _assert_citation_unavailable(caught)


def test_a_refusing_citation_reader_refuses_the_workbook(monkeypatch) -> None:
    def certified(session, *, read_citations, **arguments):
        return read_citations(session, run_id=RUN)

    monkeypatch.setattr(run_export, "prepare_certified_xlsx_package", certified)

    def reader(session, **arguments):
        raise ValueError("verified_run_authority_invalid")

    with pytest.raises(DomainError) as caught:
        _export(_Session(_citing_facts()), read_citations=reader)
    _assert_citation_unavailable(caught)


@pytest.mark.parametrize(
    "code",
    ["xlsx_citation_pin_mismatch", "xlsx_run_pin_mismatch", "xlsx_run_pin_changed"],
)
def test_a_certified_pin_refusal_refuses_the_workbook(monkeypatch, code) -> None:
    def certified(session, **arguments):
        raise CertifiedXlsxPackageRefused(code)

    monkeypatch.setattr(run_export, "prepare_certified_xlsx_package", certified)
    with pytest.raises(DomainError) as caught:
        _export(_Session(_citing_facts()), read_citations=lambda *a, **k: None)
    _assert_citation_unavailable(caught)


# --- no download name ----------------------------------------------------------------------


def test_the_export_value_names_no_file() -> None:
    for spelling in ("filename", "file_name", "download_name", "attachment_name"):
        assert not hasattr(XlsxExport, spelling)
