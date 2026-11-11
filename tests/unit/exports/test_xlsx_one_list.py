"""`F8-COUNT-XLSX`: the workbook of a ``one_list`` run has the column «Источник»; the workbook of a ``text_only`` run is unchanged.

Pure checks (no database, no storage, no spreadsheet application) on the labels, the writer, the projection and the read adapter's choice of
statement. The expected words and the column lists are literals on purpose: a table or a layout edited on one side only is a red test.

**The control that can fail.** ``TEXT_ONLY_WORKBOOK_SHA256`` is the digest of the whole workbook of ``_corpus`` as the writer of base commit
``8dcf5a0aa`` (before this lane) produced it. A ``text_only`` workbook that gains a column, a width, a cell or a different byte fails that
equality; the one-list workbook of the same findings must differ from it. The corpus is built from a writer module passed in, so the same
function ran against the base writer to capture the digest.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import replace
from types import ModuleType
from typing import Any
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx import reader, writer
from auditmanager.exports.xlsx.labels import (
    CATEGORY_LABELS,
    GROUNDING_PORTAL_BLOCK,
    GROUNDING_TEXT_SPAN,
    SOURCE_LABELS,
    source_of,
)
from auditmanager.exports.xlsx.projection import (
    CitationRead,
    EvidenceLocationRead,
    FindingRead,
    ObservationRead,
    RunRead,
    VerdictRead,
    project_workbook,
)
from auditmanager.exports.xlsx.query import read_xlsx_projection

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

#: The columns of a ``text_only`` workbook: the twelve of ``8dcf5a0aa``, as literals.
TEXT_ONLY_COLUMNS = (
    "№", "Лист/стр.", "Категория", "Замечание", "Рекомендация", "Серьёзность (решение эксперта)",
    "Серьёзность (предложение модели)", "Норма (документ, пункт)", "Цитата нормы", "Решение эксперта", "Комментарий",
    "ID замечания",
)
#: The columns of a ``one_list`` workbook: the same, with «Источник» right after «Категория».
ONE_LIST_COLUMNS = (
    "№", "Лист/стр.", "Категория", "Источник", "Замечание", "Рекомендация", "Серьёзность (решение эксперта)",
    "Серьёзность (предложение модели)", "Норма (документ, пункт)", "Цитата нормы", "Решение эксперта", "Комментарий",
    "ID замечания",
)
#: SHA-256 of the whole workbook ``_corpus(<base writer>)`` renders, captured from the writer of ``8dcf5a0aa``.
TEXT_ONLY_WORKBOOK_SHA256 = "3d6c0027a4db9ec00b12d8e4553ea104523277a8328916074843137ee211a38e"


def _corpus(module: ModuleType) -> Any:
    """Four findings of a text-only run, drawn with the writer ``module`` (the current one, or the base one when the digest was captured)."""
    return module.WorkbookInput(
        project_uid="prj_01M5B0000000000000000000P1",
        version_uid="ver_01M5B0000000000000000000V1",
        run_id="run_01M5B0000000000000000000R1",
        profile_id="profile_1",
        snapshot_key="ns_1",
        attribution="ответы модели воспроизведены из записи (recorded)",
        findings=(
            module.FindingRow(
                finding_uid="fnd_1", sheet_page="АР-1 / 3", category="fire_safety", finding_text="Первое замечание",
                recommendation="Исправить", decided_severity="critical", proposed_severity="economic",
                citations=(module.Citation("СП 1", "2.1", "Цитата"),), expert_decision="accepted", comment="Проверено",
                members=(module.FindingMember("АР-2 / 4", "Вторая запись"),),
            ),
            module.FindingRow(finding_uid="fnd_2", sheet_page="АР-5", category="layout", finding_text="Второе замечание"),
            module.FindingRow(
                finding_uid="fnd_3", sheet_page="КЖ-1\nКЖ-2", category="documentation", finding_text="Третье замечание",
                proposed_severity="recommendation", expert_decision="rejected",
            ),
            module.FindingRow(
                finding_uid="fnd_4", sheet_page="ОВ-9", category="internal_contradiction", finding_text="= не формула",
                proposed_severity="operational", expert_decision="pending",
            ),
        ),
    )


def _cells(content: bytes, part: str = "xl/worksheets/sheet2.xml") -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read(part))
    cells: dict[str, str] = {}
    for cell in root.iter(f"{MAIN}c"):
        node = cell.find(f"{MAIN}is/{MAIN}t")
        if node is None:
            node = cell.find(f"{MAIN}v")
        cells[cell.attrib["r"]] = (node.text or "") if node is not None else ""
    return cells


def _one_list_source() -> Any:
    """Three findings of a one-list run: a text finding, a block finding (with a «также найдено» member) and a cross-check."""
    return writer.WorkbookInput(
        project_uid="prj_1", version_uid="ver_1", run_id="run_1", profile_id="profile_1", snapshot_key="ns_1",
        attribution="ответы модели получены живым вызовом (live)", publication_mode="one_list",
        findings=(
            writer.FindingRow(finding_uid="fnd_t", sheet_page="АР-1", category="layout", finding_text="Текстовое", source="text"),
            writer.FindingRow(
                finding_uid="fnd_d", sheet_page="АР-2", category="drawing_discrepancy", finding_text="На чертеже",
                recommendation="Требуется проверка эксперта по источнику", source="drawing", expert_decision="pending",
                members=(writer.FindingMember("АР-3", "Та же отметка"),),
            ),
            writer.FindingRow(finding_uid="fnd_c", sheet_page="АР-4", category="cross_source", finding_text="Не сходится", source="cross_check"),
        ),
    )


# --- the control: a text-only workbook is the one the base writer produced -----------------------------------------------------


def test_a_text_only_workbook_is_the_workbook_the_base_writer_produced() -> None:
    content = writer.render_xlsx(_corpus(writer)).content
    assert hashlib.sha256(content).hexdigest() == TEXT_ONLY_WORKBOOK_SHA256
    cells = _cells(content)
    assert tuple(cells[f"{column}1"] for column in "ABCDEFGHIJKL") == TEXT_ONLY_COLUMNS == writer.FINDING_COLUMNS
    assert "M1" not in cells
    # The mode is the default and says nothing else: stating it changes no byte.
    assert writer.render_xlsx(replace(_corpus(writer), publication_mode="text_only")).content == content


def test_the_same_findings_of_a_one_list_run_are_a_different_workbook_with_one_more_column() -> None:
    plain = _corpus(writer)
    one_list = replace(
        plain, publication_mode="one_list",
        findings=tuple(replace(row, source="text") for row in plain.findings),
    )
    content = writer.render_xlsx(one_list).content
    assert hashlib.sha256(content).hexdigest() != TEXT_ONLY_WORKBOOK_SHA256
    cells = _cells(content)
    assert tuple(cells[f"{column}1"] for column in "ABCDEFGHIJKLM") == ONE_LIST_COLUMNS == writer.ONE_LIST_FINDING_COLUMNS
    assert "N1" not in cells


# --- the column ---------------------------------------------------------------------------------------------------------------


def test_a_one_list_workbook_says_where_each_finding_stands_and_keeps_the_id_last() -> None:
    cells = _cells(writer.render_xlsx(_one_list_source()).content)
    assert [cells[f"{column}1"] for column in "ABCDEFGHIJKLM"] == list(ONE_LIST_COLUMNS)
    assert [cells[f"D{row}"] for row in (2, 3, 5)] == ["Текст", "Чертёж", "Сверка"]
    assert [cells[f"C{row}"] for row in (2, 3, 5)] == [
        "Планировочные решения", "Расхождение на чертеже", "Расхождение источников",
    ]
    assert [cells[f"M{row}"] for row in (2, 3, 5)] == ["fnd_t", "fnd_d", "fnd_c"]
    # The member row of the block finding: its page and note stay where they were, the new cell is empty, and it carries no ID.
    assert (cells["B4"], cells["D4"], cells["E4"], cells["L4"], cells["M4"]) == ("АР-3", "", "также найдено", "Та же отметка", "")
    assert cells["F3"] == "Требуется проверка эксперта по источнику"
    assert cells["K3"] == "не решено"


def test_the_summary_of_a_one_list_workbook_counts_the_new_categories_by_their_words() -> None:
    summary = _cells(writer.render_xlsx(_one_list_source()).content, "xl/worksheets/sheet1.xml")
    counted = {summary[f"A{row}"]: summary[f"B{row}"] for row in range(1, 40) if f"A{row}" in summary}
    assert counted["Расхождение на чертеже"] == "1" and counted["Расхождение источников"] == "1"


def test_the_import_reads_a_one_list_workbook_by_its_headers() -> None:
    """«ID замечания», «Решение эксперта» and «Комментарий» are found by name, so the new column moves none of them."""
    one_list = _one_list_source()
    source = replace(one_list, findings=(replace(one_list.findings[1], expert_decision="accepted", comment="Верно"),))
    rows = reader.read_findings_sheet(writer.render_xlsx(source).content)
    assert [(row.finding_uid, row.decision, row.comment) for row in rows if row.finding_uid] == [("fnd_d", "принято", "Верно")]


@pytest.mark.parametrize(
    ("category", "grounding", "expected"),
    [
        ("layout", GROUNDING_TEXT_SPAN, "text"),
        ("fire_safety", GROUNDING_TEXT_SPAN, "text"),
        ("drawing_discrepancy", GROUNDING_PORTAL_BLOCK, "drawing"),
        ("layout", GROUNDING_PORTAL_BLOCK, "drawing"),
        ("drawing_discrepancy", GROUNDING_TEXT_SPAN, "drawing"),
        ("cross_source", GROUNDING_PORTAL_BLOCK, "cross_check"),
        ("cross_source", GROUNDING_TEXT_SPAN, "cross_check"),
    ],
)
def test_the_source_comes_from_the_category_and_the_grounding(category: str, grounding: str, expected: str) -> None:
    assert source_of(category, grounding) == expected
    assert expected in SOURCE_LABELS and category in CATEGORY_LABELS


def test_a_grounding_nobody_named_is_refused_and_not_read_as_text() -> None:
    with pytest.raises(ValueError, match="xlsx_grounding_kind_invalid"):
        source_of("layout", "image")
    assert tuple(SOURCE_LABELS.values()) == ("Текст", "Чертёж", "Сверка")


# --- the refusals: a column that exists for one shape is never half-present in the other ---------------------------------------


def test_a_source_on_a_text_only_workbook_is_refused_and_not_dropped() -> None:
    plain = _corpus(writer)
    with pytest.raises(ValueError, match="xlsx_source_unexpected"):
        writer.render_xlsx(replace(plain, findings=(replace(plain.findings[0], source="text"), *plain.findings[1:])))


@pytest.mark.parametrize("source", [None, "", "drawing ", "Чертёж", "block"])
def test_a_one_list_finding_with_no_known_source_is_refused(source: object) -> None:
    one_list = _one_list_source()
    bad = replace(one_list, findings=(replace(one_list.findings[0], source=source),))
    with pytest.raises(ValueError, match="xlsx_source_invalid"):
        writer.render_xlsx(bad)


def test_an_unknown_publication_mode_is_refused() -> None:
    with pytest.raises(ValueError, match="xlsx_publication_mode_invalid"):
        writer.render_xlsx(replace(_one_list_source(), publication_mode="all_at_once"))


# --- the projection ----------------------------------------------------------------------------------------------------------


def _observation(oid: str, uid: str, category: str, grounding: str, page: int = 1) -> ObservationRead:
    return ObservationRead(
        finding_observation_id=oid, finding_uid=uid, category=category, finding_text=f"Текст {oid}", recommendation="",
        proposed_severity=None, evidence=(EvidenceLocationRead(0, page, f"АР-{page}"),), grounding_kind=grounding,
    )


def _finding(uid: str, category: str, grounding: str, *, members: tuple[str, ...] = ()) -> FindingRead:
    canonical = f"{uid}_o1"
    observations = (
        _observation(canonical, uid, category, grounding),
        *(_observation(f"{uid}_{name}", uid, category, grounding, page=2) for name in members),
    )
    return FindingRead(
        finding_uid=uid, run_id="run_1", category=category, canonical_observation_id=canonical,
        member_observation_ids=tuple(f"{uid}_{name}" for name in members), observations=observations,
        verdict=VerdictRead(uid, "pending", None, None), citations=(),
    )


def test_the_projection_gives_a_source_to_a_one_list_run_and_none_to_a_text_only_one() -> None:
    findings = (
        _finding("fnd_t", "layout", "text_span"),
        _finding("fnd_d", "drawing_discrepancy", "portal_block", members=("o2", "o3")),
        _finding("fnd_c", "cross_source", "portal_block"),
    )
    one_list = project_workbook(RunRead("prj_1", "ver_1", "run_1", "profile_1", "", "live", "one_list"), findings)
    assert one_list.publication_mode == "one_list"
    assert [row.source for row in one_list.findings] == ["text", "drawing", "cross_check"]
    assert len(one_list.findings[1].members) == 2

    text_only = project_workbook(
        RunRead("prj_1", "ver_1", "run_1", "profile_1", "", "live"), (_finding("fnd_t", "layout", "text_span"),)
    )
    assert text_only.publication_mode == "text_only" and [row.source for row in text_only.findings] == [None]


def test_the_projection_refuses_a_publication_mode_it_does_not_know() -> None:
    with pytest.raises(ValueError, match="xlsx_projection_run_invalid"):
        project_workbook(RunRead("prj_1", "ver_1", "run_1", "profile_1", "", "live", "everything"), ())


def test_a_one_list_finding_of_an_unnamed_grounding_is_refused_by_the_projection() -> None:
    with pytest.raises(ValueError, match="xlsx_grounding_kind_invalid"):
        project_workbook(
            RunRead("prj_1", "ver_1", "run_1", "profile_1", "", "live", "one_list"), (_finding("fnd_t", "layout", "image"),)
        )


# --- the read adapter: which statement reads which run ------------------------------------------------------------------------

HEADER = {
    "run_id": "run_1", "project_uid": "prj_1", "version_uid": "ver_1", "analysis_profile_id": "ap_1",
    "norms_snapshot_id": None, "snapshot_key": None,
}


def _row(oid: str, ordinal: int | None, page: int | None, *, uid: str = "fnd_1", category: str = "layout", **more: object) -> dict[str, object]:
    row: dict[str, object] = {
        "finding_uid": uid, "project_uid": "prj_1", "version_uid": "ver_1", "allocated_by_run_id": "run_1", "category": category,
        "canonical_observation_id": f"{uid}_o1", "finding_observation_id": oid, "observation_run_id": "run_1",
        "observation_finding_uid": uid, "observation_category": category, "finding_text": f"Текст {oid}",
        "recommendation_text": "Проверить", "proposed_severity": None, "evidence_ordinal": ordinal, "page_number": page,
        "current_verdict": "pending", "decided_severity": None, "latest_comment": None, "verdict_finding_uid": uid,
    }
    row.update(more)
    return row


class _Result:
    def __init__(self, values: Any) -> None:
        self.values = values

    def mappings(self) -> "_Result":
        return self

    def first(self) -> Any:
        return self.values

    def all(self) -> Any:
        return self.values


class _Session:
    """The first statement answers the run's header, the second its findings; every statement is kept as text."""

    def __init__(self, header: dict[str, object], rows: list[dict[str, object]]) -> None:
        self.header, self.rows, self.calls = header, rows, []

    def execute(self, statement: Any, parameters: dict[str, str]) -> _Result:
        assert parameters == {"run_id": "run_1"}
        self.calls.append(str(statement))
        return _Result(self.header if len(self.calls) == 1 else self.rows)


def _read(session: _Session) -> Any:
    return read_xlsx_projection(
        session, "run_1", page_labels={1: "АР-1", 2: "АР-2", 3: "АР-3"}, citations_by_finding={"fnd_1": ()},
        attribution="live",
    )


def test_a_text_only_run_is_read_by_the_statement_it_was_always_read_by() -> None:
    for header in (dict(HEADER), dict(HEADER, publication_mode="text_only")):  # a header with no marker is text_only
        session = _Session(header, [_row("fnd_1_o1", 0, 1)])
        run, findings = _read(session)
        assert run.publication_mode == "text_only" and len(session.calls) == 2
        assert "finding_block_evidence" not in session.calls[1] and "grounding_kind" not in session.calls[1]
        assert findings[0].observations[0].grounding_kind == "text_span"
        assert project_workbook(run, findings).findings[0].source is None


def test_a_one_list_run_is_read_with_the_evidence_of_a_block() -> None:
    """A block finding has no ``finding_evidence`` row: its location is the block's page."""
    rows = [
        _row("fnd_1_o1", 0, 1, category="drawing_discrepancy", grounding_kind="portal_block"),
        _row("fnd_1_o1", 1, 3, category="drawing_discrepancy", grounding_kind="portal_block"),
        _row("fnd_1_o2", 0, 2, category="drawing_discrepancy", grounding_kind="portal_block"),
    ]
    session = _Session(dict(HEADER, publication_mode="one_list"), rows)
    run, findings = _read(session)
    assert run.publication_mode == "one_list" and len(session.calls) == 2
    assert "finding_block_evidence" in session.calls[1]
    row = project_workbook(run, findings).findings[0]
    assert (row.source, row.sheet_page, row.members[0].sheet_page) == ("drawing", "АР-1\nАР-3", "АР-2")


def test_a_one_list_text_finding_is_a_text_source_and_a_cross_check_stays_one() -> None:
    session = _Session(
        dict(HEADER, publication_mode="one_list"),
        [_row("fnd_1_o1", 0, 1, grounding_kind="text_span")],
    )
    run, findings = _read(session)
    assert project_workbook(run, findings).findings[0].source == "text"
    mixed = _Session(
        dict(HEADER, publication_mode="one_list"),
        [_row("fnd_1_o1", 0, 1, category="cross_source", grounding_kind="portal_block")],
    )
    run, findings = _read(mixed)
    assert project_workbook(run, findings).findings[0].source == "cross_check"


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (lambda header, rows: header.update(publication_mode="all_at_once"), "xlsx_read_publication_mode_invalid"),
        # a block observation with no block evidence is not a finding with a location: refused, not exported with an empty cell
        (lambda header, rows: rows[0].update(evidence_ordinal=None, page_number=None), "xlsx_read_incomplete_finding"),
        # one observation read as two groundings
        (lambda header, rows: rows.append(_row("fnd_1_o1", 1, 1, grounding_kind="text_span")), "xlsx_read_observation_changed"),
    ],
)
def test_a_one_list_read_that_does_not_hold_together_is_refused(change: Any, error: str) -> None:
    header = dict(HEADER, publication_mode="one_list")
    rows = [_row("fnd_1_o1", 0, 1, grounding_kind="portal_block")]
    change(header, rows)
    with pytest.raises(ValueError, match=error):
        _read(_Session(header, rows))


def test_the_page_of_a_block_is_labelled_from_the_verified_labels_or_the_read_is_refused() -> None:
    session = _Session(dict(HEADER, publication_mode="one_list"), [_row("fnd_1_o1", 0, 9, grounding_kind="portal_block")])
    with pytest.raises(ValueError, match="xlsx_read_page_label_missing"):
        _read(session)


def test_the_citation_partition_is_still_required_of_a_one_list_run() -> None:
    session = _Session(dict(HEADER, publication_mode="one_list"), [_row("fnd_1_o1", 0, 1, grounding_kind="portal_block")])
    with pytest.raises(ValueError, match="xlsx_read_citation_partition_invalid"):
        read_xlsx_projection(
            session, "run_1", page_labels={1: "АР-1"}, citations_by_finding={}, attribution="live"
        )
    assert CitationRead  # the type the partition is made of stays the one of the text path
