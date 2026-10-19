"""The served version comparison over fake ports (`W59-VERSION-COMPARE-01`).

The version rows go through the real ``read_ordered_version_pair`` against a fake
session that answers its one SELECT; classifications, runs, page text and findings
come from in-memory port fakes. ``tests/integration/comparison/test_service_db.py``
repeats the version half against PostgreSQL.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.comparison.public import (
    MAX_DIFF_LIMIT,
    OUTCOME_COMPARED,
    OUTCOME_REFUSED,
    ComparisonIntegrityError,
    ComparisonRequest,
    ComparisonRequestInvalid,
    FindingEvidenceSnapshot,
    FindingSnapshot,
    RunCandidate,
    SavedPageText,
    SuppliedVersionClassification,
    VersionComparisonService,
)
from auditmanager.comparison.raw_text import MAX_LINES_PER_PAGE
from auditmanager.comparison import service as service_module

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
OTHER_PROJECT = "prj_01M2545JSD15ETSNNV904X991K"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
OTHER_DOCUMENT = "doc_01M2545JSD15ETSNNV904X991K"
V1 = "ver_01M2545JSD15ETSNNV904X9911"
V2 = "ver_01M2545JSD15ETSNNV904X9912"
V3 = "ver_01M2545JSD15ETSNNV904X9913"
FOREIGN = "ver_01M2545JSD15ETSNNV904X9914"
R1 = "run_01M2545JSD15ETSNNV904X9911"
R2 = "run_01M2545JSD15ETSNNV904X9912"
R2_OLD = "run_01M2545JSD15ETSNNV904X9919"
SECTIONS = frozenset({"AR", "KJ", "PS", "PB"})


def _row(version_uid, ordinal, pages, *, document=DOCUMENT, project=PROJECT):
    return {
        "version_uid": version_uid, "version_document_uid": document,
        "set_document_uid": document, "project_uid": project, "version_ordinal": ordinal,
        "state": "published", "sha256": f"{ordinal:x}" * 64, "byte_size": 100,
        "page_count": pages, "media_type": "application/pdf",
    }


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _Session:
    """Answers ``read_ordered_version_pair``'s one SELECT from a dict of rows."""

    def __init__(self, rows):
        self.rows = {row["version_uid"]: row for row in rows}
        self.statements = 0

    def execute(self, statement, parameters):
        self.statements += 1
        wanted = {parameters["source_version_uid"], parameters["target_version_uid"]}
        return _Result(sorted(
            (row for uid, row in self.rows.items() if uid in wanted),
            key=lambda row: row["version_uid"],
        ))


class _Classifications:
    def __init__(self, stored):
        self.stored = stored

    def read_classification(self, session, *, version_uid):
        value = self.stored.get(version_uid)
        return None if value is None else SuppliedVersionClassification(version_uid, *value)


class _Analyses:
    def __init__(self, runs, texts, findings):
        self.runs, self.texts, self.findings = runs, texts, findings

    def runs_newest_first(self, session, *, version_uid):
        return tuple(RunCandidate(run_id, state) for run_id, state in self.runs.get(version_uid, ()))

    def saved_page_text(self, session, *, run_id, version):
        pages = self.texts.get(run_id)
        return None if pages is None else SavedPageText(run_id, "c" * 64, pages)

    def published_findings(self, session, *, run_id):
        return self.findings.get(run_id, ())


def _sheet(title, *notes):
    return "\n".join(("ООО Проект", "Лист", title, *notes)) + "\n"


SOURCE_PAGES = {
    1: _sheet("Общие данные", "Ведомость листов", "Примечание 1"),
    2: _sheet("План 1 этажа", "Ось А-Г", "Стена 200", "Дверь Д1", "Окно ОК-1"),
    3: _sheet("Разрез 1-1", "Отм. +3.000", "Перекрытие П1"),
    4: "",
    5: _sheet("Узлы старые", "Узел 7", "Узел 8", "Узел 9"),
}
TARGET_PAGES = {
    1: _sheet("Общие данные", "Ведомость листов", "Примечание 1"),
    2: _sheet("Разрез 1-1", "Отм. +3.000", "Перекрытие П1"),
    3: _sheet("План 1 этажа", "Ось А-Г", "Стена 250", "Дверь Д1", "Окно ОК-1"),
    4: "",
    5: _sheet("Фасад", "Цвет RAL 9003", "Облицовка"),
}


def _finding(number, quotes, text="Нет дверного проёма", category="layout"):
    return FindingSnapshot(
        f"fnd_{number:026d}", f"fobs_{number:026d}", category, text,
        tuple(FindingEvidenceSnapshot(page, quote) for page, quote in quotes),
    )


SOURCE_FINDINGS = (
    _finding(1, [(2, "Дверь Д1")]),                         # still reported on moved page 3
    _finding(2, [(2, "Стена 200")], text="Толщина стены"),  # quote changed -> probably fixed
    _finding(3, [(5, "Узел 7")], text="Нет узла"),           # sheet removed -> undetermined
    _finding(4, [(1, "Примечание 1")], text="Примечание"),   # quote still present -> undetermined
)
TARGET_FINDINGS = (
    _finding(11, [(3, "Дверь Д1")]),
    _finding(12, [(5, "Цвет RAL 9003")], text="Цвет не согласован", category="facade"),
)


def _service(classifications=None, runs=None, texts=None, findings=None):
    return VersionComparisonService(
        classifications=_Classifications(
            {V1: ("P", "AR"), V2: ("P", "AR")} if classifications is None else classifications
        ),
        analyses=_Analyses(
            {V1: ((R1, "published"),), V2: ((R2, "published"), (R2_OLD, "published"))}
            if runs is None else runs,
            {R1: SOURCE_PAGES, R2: TARGET_PAGES} if texts is None else texts,
            {R1: SOURCE_FINDINGS, R2: TARGET_FINDINGS} if findings is None else findings,
        ),
        section_codes=SECTIONS,
    )


def _session(*extra):
    return _Session([_row(V1, 1, 5), _row(V2, 2, 5), *extra])


def _compare(service=None, session=None, **request):
    arguments = {
        "project_uid": PROJECT, "document_uid": DOCUMENT,
        "source_version_uid": V1, "target_version_uid": V2,
    } | request
    return (service or _service()).compare(session or _session(), ComparisonRequest(**arguments))


def test_compared_pair_carries_both_sides_and_its_digest() -> None:
    result = _compare()
    assert result.outcome == OUTCOME_COMPARED and result.refusal is None
    assert (result.source.run_id, result.target.run_id) == (R1, R2)  # newest published
    assert (result.source.project_stage, result.source.section_code) == ("P", "AR")
    assert result.target.text_layer_sha256 == "c" * 64
    assert len(result.comparison_sha256) == 64
    assert _compare().comparison_sha256 == result.comparison_sha256


def test_sheet_list_covers_every_page_once_in_target_order() -> None:
    rows = [
        (row.status, row.source_page_number, row.target_page_number, row.pairing_basis, row.textless)
        for row in _compare().sheets
    ]
    # Removed source pages 4 and 5 follow target page 3, the furthest one their paired
    # predecessors (source 2 -> target 3, source 3 -> target 2) reached.
    assert rows == [
        ("unchanged", 1, 1, "exact_text", False),
        ("unchanged", 3, 2, "exact_text", False),
        ("changed", 2, 3, "similar_text", False),
        ("removed", 4, None, None, True),
        ("removed", 5, None, None, False),
        ("added", None, 4, None, True),
        ("added", None, 5, None, False),
    ]


def test_diff_page_covers_changed_added_and_removed_text_with_anchors() -> None:
    page = _compare().sheet_diffs
    assert (page.offset, page.total, page.next_offset) == (0, 3, None)
    changed, removed, added = page.items
    assert (changed.status, changed.source_page_number, changed.target_page_number) == (
        "changed", 2, 3,
    )
    assert changed.outcome == "computed"
    assert (changed.added_line_count, changed.removed_line_count) == (1, 1)
    replaced = [hunk for hunk in changed.hunks if hunk.tag != "equal"]
    assert [(h.tag, h.source_lines, h.target_lines) for h in replaced] == [
        ("replace", ("Стена 200\n",), ("Стена 250\n",)),
    ]
    assert all(h.source_lines == () and h.target_lines == () for h in changed.hunks if h.tag == "equal")
    assert (added.status, added.target_page_number, added.added_line_count) == ("added", 5, 5)
    assert (removed.status, removed.source_page_number, removed.removed_line_count) == (
        "removed", 5, 6,
    )
    assert len({changed.evidence_sha256, added.evidence_sha256, removed.evidence_sha256}) == 3


def test_diff_paging_continues_from_next_offset() -> None:
    first = _compare(diff_limit=2).sheet_diffs
    assert (len(first.items), first.next_offset) == (2, 2)
    second = _compare(diff_offset=2, diff_limit=2).sheet_diffs
    assert ([item.status for item in second.items], second.next_offset) == (["added"], None)
    beyond = _compare(diff_offset=9).sheet_diffs
    assert (beyond.items, beyond.total, beyond.next_offset) == ((), 3, None)


def test_character_budget_ends_a_page_early_without_truncating(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "MAX_DIFF_PAGE_CHARACTERS", 10)
    page = _compare(diff_limit=MAX_DIFF_LIMIT).sheet_diffs
    # The first sheet is always served whole; the next would cross the budget.
    assert (len(page.items), page.next_offset) == (1, 1)
    assert page.items[0].hunks


def test_oversized_page_is_marked_too_large_not_truncated() -> None:
    big = "\n".join(f"строка {n}" for n in range(MAX_LINES_PER_PAGE + 5))
    texts = {R1: SOURCE_PAGES, R2: TARGET_PAGES | {5: big}}
    page = _compare(_service(texts=texts)).sheet_diffs
    added = next(item for item in page.items if item.status == "added")
    assert (added.outcome, added.too_large_reason, added.hunks) == (
        "too_large", "target_text_too_many_lines", (),
    )


def test_finding_proposals_are_labelled_and_ordered() -> None:
    findings = _compare().findings
    assert (findings.status, findings.source_finding_count, findings.target_finding_count) == (
        "compared", 4, 2,
    )
    labels = [
        (p.kind, p.basis,
         p.source_finding.finding_uid[-2:] if p.source_finding else None,
         p.target_finding.finding_uid[-2:] if p.target_finding else None)
        for p in findings.proposals
    ]
    assert labels == [
        ("unchanged", "exact_issue_and_quotes", "01", "11"),
        ("probably_fixed", "quotes_absent_from_paired_sheets", "02", None),
        ("undetermined", "evidence_sheet_unpaired", "03", None),
        ("undetermined", "quote_still_on_paired_sheet", "04", None),
        ("new", "no_exact_source_match", None, "12"),
    ]
    assert len(findings.proposals[0].proposal_sha256) == 64
    assert all(p.proposal_sha256 is None for p in findings.proposals[1:])
    assert findings.proposals[0].target_finding.page_numbers == (3,)


def test_finding_with_evidence_over_the_cap_is_undetermined_not_dropped() -> None:
    many = _finding(5, [(1, f"Цитата {n}") for n in range(9)], text="Много цитат")
    repeated = _finding(6, [(2, "Дверь Д1"), (2, "Дверь  Д1")], text="Повтор")
    findings = {R1: (*SOURCE_FINDINGS, many, repeated), R2: TARGET_FINDINGS}
    proposals = _compare(_service(findings=findings)).findings.proposals
    by_uid = {p.source_finding.finding_uid[-2:]: p for p in proposals if p.source_finding}
    assert (by_uid["05"].kind, by_uid["05"].basis) == ("undetermined", "evidence_over_limit")
    # Two quotes repeated on one page are one coordinate; still under the cap.
    assert by_uid["06"].basis == "quote_still_on_paired_sheet"


def test_run_over_the_finding_limit_is_reported_unavailable() -> None:
    crowd = tuple(_finding(100 + n, [(1, "Примечание 1")], text=f"Замечание {n}") for n in range(201))
    findings = _compare(_service(findings={R1: crowd, R2: ()})).findings
    assert (findings.status, findings.unavailable_reason, findings.proposals) == (
        "unavailable", "findings_over_limit", (),
    )
    assert findings.source_finding_count == 201


def test_explicit_run_must_be_a_published_run_of_that_version() -> None:
    texts = {R1: SOURCE_PAGES, R2: TARGET_PAGES, R2_OLD: TARGET_PAGES}
    chosen = _compare(_service(texts=texts), target_run_id=R2_OLD)
    assert chosen.target.run_id == R2_OLD
    refused = _compare(target_run_id=R1)
    assert (refused.refusal.reason, refused.refusal.side) == ("run_not_of_version", "target")
    runs = {V1: ((R1, "published"),), V2: ((R2, "running"),)}
    refused = _compare(_service(runs=runs), target_run_id=R2)
    assert (refused.refusal.reason, refused.refusal.side) == ("run_not_published", "target")


@pytest.mark.parametrize(
    ("request_changes", "session_rows", "reason"),
    [
        ({"target_version_uid": V1}, (), "same_version"),
        ({"target_version_uid": V3}, (), "version_not_found"),
        ({"target_version_uid": V3}, (_row(V3, 3, 5, document=OTHER_DOCUMENT),), "different_set"),
        ({"target_version_uid": FOREIGN}, (_row(FOREIGN, 3, 5, project=OTHER_PROJECT),),
         "foreign_project"),
        ({"source_version_uid": V2, "target_version_uid": V1}, (), "version_order_invalid"),
        ({"project_uid": OTHER_PROJECT}, (), "foreign_project"),
        ({"document_uid": OTHER_DOCUMENT}, (), "different_set"),
    ],
)
def test_version_refusals_are_explicit(request_changes, session_rows, reason) -> None:
    result = _compare(session=_session(*session_rows), **request_changes)
    assert result.outcome == OUTCOME_REFUSED
    assert (result.refusal.reason, result.refusal.side) == (reason, None)
    assert result.sheets == () and result.sheet_diffs is None and result.findings is None


@pytest.mark.parametrize(
    ("classifications", "reason", "side"),
    [
        ({V2: ("P", "AR")}, "stage_unclassified", "source"),
        ({V1: ("P", "AR")}, "stage_unclassified", "target"),
        ({V1: ("P", "AR"), V2: ("R", "AR")}, "project_stage_mismatch", None),
        ({V1: ("P", "PS"), V2: ("P", "PB")}, "confirmed_section_mismatch", None),
    ],
)
def test_classification_refusals_never_relabel_the_pair(classifications, reason, side) -> None:
    result = _compare(_service(classifications=classifications))
    assert (result.outcome, result.refusal.reason, result.refusal.side) == (
        OUTCOME_REFUSED, reason, side,
    )
    assert result.source.version_uid == V1 and result.source.run_id is None


@pytest.mark.parametrize(
    ("runs", "texts", "reason", "side"),
    [
        ({V1: (), V2: ((R2, "published"),)}, None, "analysis_missing", "source"),
        ({V1: ((R1, "failed"),), V2: ((R2, "published"),)}, None, "analysis_missing", "source"),
        (None, {R1: SOURCE_PAGES}, "text_unavailable", "target"),
    ],
)
def test_missing_analysis_or_text_refuses_per_side(runs, texts, reason, side) -> None:
    result = _compare(_service(runs=runs, texts=texts))
    assert (result.refusal.reason, result.refusal.side) == (reason, side)
    assert result.source.project_stage == "P"


def test_stage_and_section_are_checked_before_runs_are_read() -> None:
    class _NoRuns(_Analyses):
        def runs_newest_first(self, session, *, version_uid):
            raise AssertionError("runs read before the classification refusal")

    service = VersionComparisonService(
        classifications=_Classifications({V1: ("P", "AR")}),
        analyses=_NoRuns({}, {}, {}), section_codes=SECTIONS,
    )
    assert _compare(service).refusal.reason == "stage_unclassified"


@pytest.mark.parametrize(
    "classifications",
    [{V1: ("P", "XX"), V2: ("P", "XX")}, {V1: ("Q", "AR"), V2: ("Q", "AR")}],
)
def test_stored_classification_outside_the_catalogue_is_an_integrity_error(classifications) -> None:
    with pytest.raises(ComparisonIntegrityError, match="stored_classification_invalid"):
        _compare(_service(classifications=classifications))


def test_incomplete_page_text_is_an_integrity_error_not_a_refusal() -> None:
    texts = {R1: {n: SOURCE_PAGES[n] for n in range(1, 5)}, R2: TARGET_PAGES}
    with pytest.raises(ComparisonIntegrityError, match="saved_page_text_invalid"):
        _compare(_service(texts=texts))


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"diff_offset": -1}, "diff_offset_invalid"),
        ({"diff_limit": 0}, "diff_limit_invalid"),
        ({"diff_limit": MAX_DIFF_LIMIT + 1}, "diff_limit_invalid"),
        ({"source_run_id": "run_x"}, "source_run_id_invalid"),
        ({"project_uid": "nonsense"}, "project_uid_invalid"),
    ],
)
def test_malformed_requests_are_rejected_before_any_read(changes, reason) -> None:
    with pytest.raises(ComparisonRequestInvalid, match=reason):
        _compare(**changes)


def test_the_service_reads_versions_once_and_writes_nothing() -> None:
    session = _session()
    result = _compare(session=session)
    assert session.statements == 1
    assert replace(result, sheet_diffs=None) == replace(_compare(), sheet_diffs=None)


# -- mode=stage: the W62 П/Р slice ----------------------------------------------------------


def test_stage_mode_compares_a_p_source_with_an_r_target_of_one_section() -> None:
    service = _service(classifications={V1: ("P", "AR"), V2: ("R", "AR")})
    result = _compare(service, mode="stage")
    assert (result.mode, result.outcome) == ("stage", OUTCOME_COMPARED)
    assert (result.source.project_stage, result.target.project_stage) == ("P", "R")
    assert result.source.section_code == result.target.section_code == "AR"
    assert result.sheets == _compare().sheets  # the raw comparison itself is unchanged
    assert result.comparison_sha256 != _compare().comparison_sha256  # the mode is bound


def test_the_same_p_r_pair_is_refused_in_version_mode_not_relabelled() -> None:
    service = _service(classifications={V1: ("P", "AR"), V2: ("R", "AR")})
    refused = _compare(service)
    assert (refused.mode, refused.refusal.reason) == ("version", "project_stage_mismatch")


@pytest.mark.parametrize(
    ("classifications", "reason", "side"),
    [
        ({V1: ("P", "AR"), V2: ("P", "AR")}, "stage_pair_invalid", None),
        ({V1: ("R", "AR"), V2: ("P", "AR")}, "stage_pair_invalid", None),
        ({V1: ("P", "AR"), V2: ("R", "KJ")}, "confirmed_section_mismatch", None),
        ({V2: ("R", "AR")}, "stage_unclassified", "source"),
    ],
)
def test_stage_mode_refusals(classifications, reason, side) -> None:
    result = _compare(_service(classifications=classifications), mode="stage")
    assert (result.mode, result.outcome) == ("stage", OUTCOME_REFUSED)
    assert (result.refusal.reason, result.refusal.side) == (reason, side)


def test_an_unknown_mode_is_rejected_before_any_read() -> None:
    with pytest.raises(ComparisonRequestInvalid, match="mode_invalid"):
        _compare(mode="object")


# -- the recomputation a command uses (`W59-DECISION-CARRYOVER-01`) -------------------------


def test_current_finding_proposals_are_the_comparison_without_its_diff_page() -> None:
    session = _session()
    current = _service().current_finding_proposals(session, ComparisonRequest(
        PROJECT, DOCUMENT, V1, V2, diff_offset=3, diff_limit=2,
    ))
    assert session.statements == 1
    assert current.comparison.sheet_diffs is None
    assert current.comparison == replace(_compare(), sheet_diffs=None)
    assert current.observations == {
        "source": {f.finding_uid: f.finding_observation_id for f in SOURCE_FINDINGS},
        "target": {f.finding_uid: f.finding_observation_id for f in TARGET_FINDINGS},
    }


def test_current_finding_proposals_of_a_refused_pair_are_that_refusal() -> None:
    unclassified = _service(classifications={V2: ("P", "AR")})
    current = unclassified.current_finding_proposals(
        _session(), ComparisonRequest(PROJECT, DOCUMENT, V1, V2),
    )
    assert current.comparison == _compare(service=unclassified)
    assert current.comparison.outcome == OUTCOME_REFUSED
    assert current.observations == {"source": {}, "target": {}}


def test_current_finding_proposals_refuse_a_malformed_request_like_compare() -> None:
    with pytest.raises(ComparisonRequestInvalid, match="mode_invalid"):
        _service().current_finding_proposals(
            _session(), ComparisonRequest(PROJECT, DOCUMENT, V1, V2, mode="object"),
        )
