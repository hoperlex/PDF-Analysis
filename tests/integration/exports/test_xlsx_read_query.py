"""The XLSX read boundary must not invent absent labels or norm citations."""

from __future__ import annotations

from copy import deepcopy

import pytest

from auditmanager.exports.xlsx.projection import CitationRead, project_workbook
from auditmanager.exports.xlsx.query import read_xlsx_projection


HEADER = {
    "run_id": "run_1", "project_uid": "prj_1", "version_uid": "ver_1",
    "analysis_profile_id": "ap_1", "norms_snapshot_id": "ns_1",
    "snapshot_key": "corpus-key",
}


def _row(observation_id: str, ordinal: int, page: int, *, canonical: str = "obs_2") -> dict:
    return {
        "finding_uid": "fnd_1", "project_uid": "prj_1", "version_uid": "ver_1",
        "allocated_by_run_id": "run_1", "category": "layout",
        "canonical_observation_id": canonical,
        "finding_observation_id": observation_id,
        "observation_run_id": "run_1", "observation_finding_uid": "fnd_1",
        "observation_category": "layout", "finding_text": f"Текст {observation_id}",
        "recommendation_text": "Исправить", "proposed_severity": "operational",
        "evidence_ordinal": ordinal, "page_number": page,
        "current_verdict": "accepted", "decided_severity": "critical",
        "latest_comment": "Проверено", "verdict_finding_uid": "fnd_1",
    }


class _MappingResult:
    def __init__(self, values):
        self.values = values

    def mappings(self):
        return self

    def first(self):
        return self.values

    def all(self):
        return self.values


class _Session:
    def __init__(self, header=HEADER, rows=None):
        self.header = deepcopy(header)
        self.rows = deepcopy(rows if rows is not None else [
            _row("obs_1", 0, 3), _row("obs_2", 0, 4), _row("obs_2", 1, 5),
        ])
        self.calls = []

    def execute(self, statement, parameters):
        sql = str(statement)
        assert sql.lstrip().upper().startswith("SELECT")
        assert parameters == {"run_id": "run_1"}
        self.calls.append(sql)
        return _MappingResult(self.header if len(self.calls) == 1 else self.rows)


def _read(session, *, labels=None, citations=None):
    return read_xlsx_projection(
        session, "run_1", page_labels=labels if labels is not None else {
            3: "АР-3", 4: "АР-4", 5: "АР-5",
        },
        citations_by_finding=citations if citations is not None else {
            "fnd_1": (CitationRead("СП 1", "2.1", "Цитата"),),
        },
        attribution="consultant_plus",
    )


def test_reads_complete_canonical_members_evidence_verdict_and_snapshot() -> None:
    session = _Session()
    run, findings = _read(session)
    assert len(session.calls) == 2
    assert "LEFT JOIN finding_observation" in session.calls[1]
    assert "WHERE f.allocated_by_run_id = :run_id" in session.calls[1]
    assert run.snapshot_key == "corpus-key"
    assert findings[0].canonical_observation_id == "obs_2"
    assert findings[0].member_observation_ids == ("obs_1",)
    assert [(e.evidence_ordinal, e.page_label) for e in findings[0].observations[1].evidence] == [
        (0, "АР-4"), (1, "АР-5"),
    ]
    row = project_workbook(run, findings).findings[0]
    assert row.finding_text == "Текст obs_2"
    assert row.sheet_page == "АР-4\nАР-5"
    assert row.decided_severity == "critical"
    assert row.citations[0].quote == "Цитата"


def test_missing_run_issues_no_finding_read_and_empty_run_is_explicit() -> None:
    session = _Session(header=None)
    assert _read(session) is None
    assert len(session.calls) == 1
    run, findings = _read(_Session(rows=[]), citations={})
    assert run.run_id == "run_1" and findings == ()


def test_no_snapshot_is_explicit_blank_and_missing_join_refuses() -> None:
    header = dict(HEADER, norms_snapshot_id=None, snapshot_key=None)
    assert _read(_Session(header=header))[0].snapshot_key == ""
    with pytest.raises(ValueError, match="xlsx_read_snapshot_missing"):
        _read(_Session(header=dict(HEADER, snapshot_key=None)))


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (lambda rows: rows[0].update(observation_run_id="run_2"), "incomplete_finding"),
        (lambda rows: rows[0].update(observation_finding_uid=None), "incomplete_finding"),
        (lambda rows: rows[0].update(verdict_finding_uid=None), "incomplete_finding"),
        (lambda rows: rows[0].update(evidence_ordinal=None), "incomplete_finding"),
        (lambda rows: [row.update(canonical_observation_id="obs_missing") for row in rows], "canonical_missing"),
        (lambda rows: rows[2].update(evidence_ordinal=2), "evidence_order_invalid"),
        (lambda rows: rows[2].update(current_verdict="rejected"), "verdict_changed"),
        (lambda rows: [row.update(decided_severity="invalid") for row in rows], "verdict_invalid"),
    ],
)
def test_inconsistent_rows_refuse(change, error) -> None:
    session = _Session()
    change(session.rows)
    with pytest.raises(ValueError, match=f"xlsx_(read|projection)_{error}"):
        _read(session)


def test_display_labels_and_citation_partition_are_required() -> None:
    with pytest.raises(ValueError, match="xlsx_read_page_label_missing"):
        _read(_Session(), labels={3: "АР-3", 4: "АР-4"})
    with pytest.raises(ValueError, match="xlsx_read_citation_partition_invalid"):
        _read(_Session(), citations={})
    with pytest.raises(ValueError, match="xlsx_read_citation_partition_invalid"):
        _read(_Session(), citations={"fnd_1": (), "fnd_other": ()})
    run, findings = _read(_Session(), citations={"fnd_1": ()})
    assert project_workbook(run, findings).findings[0].citations == ()


def test_missing_observation_and_evidence_cannot_be_silently_dropped() -> None:
    for rows in ([dict(_row("obs_1", 0, 3), finding_observation_id=None)],
                 [dict(_row("obs_1", 0, 3), evidence_ordinal=None)]):
        with pytest.raises(ValueError, match="xlsx_read_incomplete_finding"):
            _read(_Session(rows=rows))


def test_a_v1_finding_is_its_single_observation() -> None:
    """`W57B-NORMS-CATALOGUE-XLSX-01`: a v1 finding has no canonical identity (only the v2
    publication writes one) and exactly one observation, which is the row the CSV exports;
    its absent recommendation is an empty cell, never ``None``."""
    rows = [
        dict(_row("obs_1", 0, 3, canonical=None), recommendation_text=None,
             proposed_severity=None, current_verdict="pending", decided_severity=None),
        dict(_row("obs_1", 1, 4, canonical=None), recommendation_text=None,
             proposed_severity=None, current_verdict="pending", decided_severity=None),
    ]
    run, findings = _read(_Session(rows=rows), citations={"fnd_1": ()})
    (finding,) = findings
    assert finding.canonical_observation_id == "obs_1"
    assert finding.member_observation_ids == ()
    workbook = project_workbook(run, findings)
    row = workbook.findings[0]
    assert (row.sheet_page, row.recommendation, row.proposed_severity) == ("АР-3\nАР-4", "", None)


def test_no_canonical_identity_with_two_observations_still_refuses() -> None:
    rows = [_row("obs_1", 0, 3, canonical=None), _row("obs_2", 0, 4, canonical=None)]
    with pytest.raises(ValueError, match="xlsx_read_canonical_missing"):
        _read(_Session(rows=rows))
