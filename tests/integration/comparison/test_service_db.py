"""The served comparison against PostgreSQL rows (`W59-VERSION-COMPARE-01`).

The version half is real: ``project``, ``document`` and ``document_version`` rows are
inserted in a rolled-back transaction and read by ``read_ordered_version_pair``'s one
SELECT, under the schema's own triggers and CHECKs (including the 500-page ceiling of
``0021``). Classifications, runs, page text and findings come from port fakes here;
the composition root's adapters for them are wired with the API.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import (
    OUTCOME_COMPARED,
    OUTCOME_REFUSED,
    ComparisonRequest,
    FindingEvidenceSnapshot,
    FindingSnapshot,
    RunCandidate,
    SavedPageText,
    SuppliedVersionClassification,
    VersionComparisonService,
)

PROJECT = "prj_01M2545JSD15ETSNNV904XA001"
OTHER_PROJECT = "prj_01M2545JSD15ETSNNV904XA002"
DOCUMENT = "doc_01M2545JSD15ETSNNV904XA001"
OTHER_DOCUMENT = "doc_01M2545JSD15ETSNNV904XA002"
FOREIGN_DOCUMENT = "doc_01M2545JSD15ETSNNV904XA003"
V1 = "ver_01M2545JSD15ETSNNV904XA001"
V2 = "ver_01M2545JSD15ETSNNV904XA002"
V_OTHER_SET = "ver_01M2545JSD15ETSNNV904XA003"
V_FOREIGN = "ver_01M2545JSD15ETSNNV904XA004"
V_MISSING = "ver_01M2545JSD15ETSNNV904XA005"
R1 = "run_01M2545JSD15ETSNNV904XA001"
R2 = "run_01M2545JSD15ETSNNV904XA002"
PAGES = 500


def _seed(session) -> None:
    rows = [
        ("INSERT INTO project (project_uid, name) VALUES (:p, 'Сравнение')", {"p": PROJECT}),
        ("INSERT INTO project (project_uid, name) VALUES (:p, 'Чужой')", {"p": OTHER_PROJECT}),
    ]
    for document, project in (
        (DOCUMENT, PROJECT), (OTHER_DOCUMENT, PROJECT), (FOREIGN_DOCUMENT, OTHER_PROJECT),
    ):
        rows.append((
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:d, :p, 'Комплект')", {"d": document, "p": project},
        ))
    for version, document, ordinal, digest in (
        (V1, DOCUMENT, 1, "a" * 64), (V2, DOCUMENT, 2, "b" * 64),
        (V_OTHER_SET, OTHER_DOCUMENT, 1, "c" * 64), (V_FOREIGN, FOREIGN_DOCUMENT, 1, "d" * 64),
    ):
        rows.append((
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "media_type, byte_size, sha256, page_count) "
            "VALUES (:v, :d, :o, 'application/pdf', 4096, :s, :n)",
            {"v": version, "d": document, "o": ordinal, "s": digest, "n": PAGES},
        ))
    for statement, parameters in rows:
        session.execute(text(statement), parameters)


def _page(number: int, revision: str) -> str:
    frame = "\n".join(f"Штамп строка {k}" for k in range(12))
    body = "\n".join(f"Лист {number} позиция {k} размер {k * 10}" for k in range(40))
    return f"{frame}\nЛист {number} изм. {revision}\n{body}\n"


SOURCE_PAGES = {n: _page(n, "1") for n in range(1, PAGES + 1)}
# Page 7 is redrawn in the newer set; every other sheet changes only its revision mark.
TARGET_PAGES = {n: _page(n, "2") for n in range(1, PAGES + 1)} | {
    7: _page(7, "2").replace("позиция 3 размер 30", "позиция 3 размер 35"),
}


class _Classifications:
    def __init__(self, stored):
        self._stored = stored

    def read_classification(self, session, *, version_uid):
        value = self._stored.get(version_uid)
        return None if value is None else SuppliedVersionClassification(version_uid, *value)


class _Analyses:
    def runs_newest_first(self, session, *, version_uid):
        return {V1: (RunCandidate(R1, "published"),), V2: (RunCandidate(R2, "published"),)}.get(
            version_uid, (),
        )

    def saved_page_text(self, session, *, run_id, version):
        return SavedPageText(run_id, "e" * 64, {R1: SOURCE_PAGES, R2: TARGET_PAGES}[run_id])

    def published_findings(self, session, *, run_id):
        page = 7
        quote = "Лист 7 позиция 3 размер 30" if run_id == R1 else "Лист 7 позиция 3 размер 35"
        uid = "fnd_01M2545JSD15ETSNNV904XA001" if run_id == R1 else "fnd_01M2545JSD15ETSNNV904XA002"
        observation = uid.replace("fnd_", "fobs_")
        return (FindingSnapshot(
            uid, observation, "dimensions", "Размер не совпадает со спецификацией",
            (FindingEvidenceSnapshot(page, quote),),
        ),)


def _service(stored=None):
    return VersionComparisonService(
        classifications=_Classifications(
            {V1: ("R", "KJ"), V2: ("R", "KJ")} if stored is None else stored
        ),
        analyses=_Analyses(),
        section_codes=frozenset({"AR", "KJ", "PS"}),
    )


def _request(**changes):
    return ComparisonRequest(**({
        "project_uid": PROJECT, "document_uid": DOCUMENT,
        "source_version_uid": V1, "target_version_uid": V2,
    } | changes))


def test_two_500_page_versions_compare_with_bounded_pages(comparison_session) -> None:
    _seed(comparison_session)
    result = _service().compare(comparison_session, _request())
    assert result.outcome == OUTCOME_COMPARED
    assert (result.source.page_count, result.target.page_count) == (PAGES, PAGES)
    assert (result.source.sha256, result.target.sha256) == ("a" * 64, "b" * 64)
    # Every sheet changed its revision mark, so every pair is a similar-text proposal.
    assert len(result.sheets) == PAGES
    assert {row.status for row in result.sheets} == {"changed"}
    assert all(row.source_page_number == row.target_page_number for row in result.sheets)
    page = result.sheet_diffs
    assert (page.total, len(page.items), page.next_offset) == (PAGES, 10, 10)
    last = _service().compare(comparison_session, _request(diff_offset=495, diff_limit=25))
    assert (len(last.sheet_diffs.items), last.sheet_diffs.next_offset) == (5, None)
    redrawn = _service().compare(comparison_session, _request(diff_offset=6, diff_limit=1))
    (sheet,) = redrawn.sheet_diffs.items
    assert (sheet.source_page_number, sheet.added_line_count, sheet.removed_line_count) == (7, 2, 2)
    (proposal,) = [p for p in result.findings.proposals if p.source_finding]
    assert (proposal.kind, proposal.basis) == ("probably_fixed", "quotes_absent_from_paired_sheets")
    (new,) = [p for p in result.findings.proposals if p.target_finding]
    assert new.kind == "new"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"target_version_uid": V1}, "same_version"),
        ({"target_version_uid": V_MISSING}, "version_not_found"),
        ({"target_version_uid": V_OTHER_SET}, "different_set"),
        # A version of another project is necessarily a version of another set.
        ({"target_version_uid": V_FOREIGN}, "different_set"),
        ({"source_version_uid": V2, "target_version_uid": V1}, "version_order_invalid"),
        ({"project_uid": OTHER_PROJECT}, "foreign_project"),
    ],
)
def test_stored_rows_drive_the_version_refusals(comparison_session, changes, reason) -> None:
    _seed(comparison_session)
    result = _service().compare(comparison_session, _request(**changes))
    assert (result.outcome, result.refusal.reason) == (OUTCOME_REFUSED, reason)


def test_unclassified_stored_version_is_refused_not_compared(comparison_session) -> None:
    _seed(comparison_session)
    result = _service({V2: ("R", "KJ")}).compare(comparison_session, _request())
    assert (result.refusal.reason, result.refusal.side) == ("stage_unclassified", "source")
    assert result.source.page_count == PAGES and result.source.run_id is None
