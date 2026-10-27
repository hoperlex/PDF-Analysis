"""`CMP-INGEST-01`: the title block's text into facts, and the facts into a grouping proposal.

Pure text and pure rules (no PDF, no database). Each rule is a function with a test that shows it failing on the
value that would break it; none of the values is an identity and none is decided here: the proposal is what an
expert confirms (ADR-0025 decisions 10, 11 and 16).
"""

from __future__ import annotations

from datetime import date

import pytest

from auditmanager.ingest.comparison_pdf.names import name_hint
from auditmanager.ingest.comparison_pdf.proposal import (
    FileEntry,
    fold_designation,
    grouping_key,
    propose_set,
    suggest_label,
)
from auditmanager.ingest.comparison_pdf.stamp import (
    SECTION_MARKS,
    FileStamp,
    PageStamp,
    parse_page_stamp,
    read_file_stamp,
    section_from_designation,
)
from auditmanager.sections.public import SECTION_CODES

#: A title block as PDFium reads it from the synthetic corpus (label, then value, one per line).
LABELLED = (
    "Обозначение\r\nСИНТ-01-ЭМ\r\nНаименование листа\r\nПлан освещения. Корпус 1, этаж 1\r\n"
    "Стадия\r\nР\r\nЛист\r\n2\r\nИзм.\r\nИзм.2\r\nДата\r\n10.03.2026\r\nОрганизация\r\nСИНТЕТИКПРОЕКТ"
)


class TestOnePage:
    def test_a_labelled_block_is_read(self) -> None:
        stamp = parse_page_stamp(LABELLED)
        assert stamp.designation == "СИНТ-01-ЭМ"
        assert stamp.revision_number == 2
        assert stamp.release_date == date(2026, 3, 10)
        assert stamp.project_stage == "R"
        assert stamp.has_text and not stamp.is_empty

    def test_a_page_with_no_text_in_the_zone_has_no_stamp_and_says_so(self) -> None:
        stamp = parse_page_stamp("   \r\n ")
        assert not stamp.has_text and stamp.is_empty and stamp.designation is None

    def test_the_label_is_never_mistaken_for_a_value(self) -> None:
        stamp = parse_page_stamp("Обозначение\r\nНаименование листа\r\nПлан")
        assert stamp.designation is None

    @pytest.mark.parametrize("text", ["Изм.4", "Изм. 4", "Изм 4", "изм.4", "Изм.№4"])
    def test_the_revision_is_read_in_its_spellings(self, text: str) -> None:
        assert parse_page_stamp(text).revision_number == 4

    def test_a_bare_label_without_a_number_states_no_revision(self) -> None:
        assert parse_page_stamp("Изм.\r\n2\r\nДата").revision_number is None  # the 2 is a sheet number, not a revision

    def test_the_highest_revision_of_a_page_wins(self) -> None:
        assert parse_page_stamp("Изм.1 Изм.3 Изм.2").revision_number == 3

    @pytest.mark.parametrize(
        ("text", "expected"),
        [("Дата\r\n05.05.2026", date(2026, 5, 5)), ("Дата: 5.5.26", date(2026, 5, 5)), ("текст 31.12.2025", date(2025, 12, 31))],
    )
    def test_the_date_is_read_and_validated(self, text: str, expected: date) -> None:
        assert parse_page_stamp(text).release_date == expected

    @pytest.mark.parametrize("text", ["Дата\r\n31.02.2026", "Дата\r\n01.01.1850", "Дата\r\n1.2.3.4"])
    def test_an_impossible_date_is_not_read(self, text: str) -> None:
        assert parse_page_stamp(text).release_date is None

    def test_a_stage_is_read_only_in_cyrillic(self) -> None:
        assert parse_page_stamp("Стадия\r\nП").project_stage == "P"
        assert parse_page_stamp("Стадия\r\nРД").project_stage == "R"
        # A Latin letter that looks like the Cyrillic one is a reason to ask, not to guess.
        assert parse_page_stamp("Стадия\r\nP").project_stage is None
        assert parse_page_stamp("Стадия\r\nR").project_stage is None

    def test_an_unlabelled_designation_is_found_by_its_shape(self) -> None:
        assert parse_page_stamp("13AV-RD-EM2-PA\r\nЛист 1").designation == "13AV-RD-EM2-PA"

    def test_a_date_or_a_revision_is_not_a_designation(self) -> None:
        assert parse_page_stamp("10.03.2026\r\nИзм.2").designation is None
        assert parse_page_stamp("1.2.3").designation is None


class TestSectionFromTheMark:
    @pytest.mark.parametrize(
        ("designation", "code"),
        [("СИНТ-01-ЭМ", "EOM"), ("СИНТ-02-АР.1", "AR"), ("13AV-RD-EM2-PA", None), ("X-01-КЖ", "KJ"), ("Y-ОВ", "OV"), ("1-2-СОУЭ", "SS")],
    )
    def test_the_mark_that_ends_a_designation_names_the_section_or_nothing(self, designation: str, code: str | None) -> None:
        assert section_from_designation(designation) == code

    def test_no_designation_no_section(self) -> None:
        assert section_from_designation(None) is None and section_from_designation("") is None

    def test_every_mark_names_a_section_of_the_catalogue(self) -> None:
        assert set(SECTION_MARKS.values()) <= SECTION_CODES


def _page(designation: str | None = "ABC-1-ЭМ", revision: int | None = None, released: date | None = None,
          stage: str | None = None, text: bool = True) -> PageStamp:
    return PageStamp(designation, revision, released, stage, has_text=text)


class TestOneFile:
    def test_the_revision_is_the_highest_and_the_date_is_that_sheets(self) -> None:
        pages = [
            _page(revision=0, released=date(2026, 1, 15)),
            _page(revision=2, released=date(2026, 3, 10)),
            _page(revision=1, released=date(2026, 2, 12)),
            _page(revision=2, released=date(2026, 3, 9)),
        ]
        stamp = read_file_stamp(pages)
        assert stamp.revision_number == 2 and stamp.release_date == date(2026, 3, 10)

    def test_with_no_revision_the_latest_date_is_the_date(self) -> None:
        stamp = read_file_stamp([_page(released=date(2026, 1, 1)), _page(released=date(2026, 6, 1))])
        assert stamp.revision_number is None and stamp.release_date == date(2026, 6, 1)

    def test_the_designation_is_the_one_most_sheets_carry(self) -> None:
        pages = [_page("A-1-ЭМ")] * 9 + [_page("B-2-ЭМ")] * 1
        stamp = read_file_stamp(pages)
        assert stamp.designation == "A-1-ЭМ" and not stamp.designations_differ

    def test_a_second_designation_on_a_fifth_of_the_sheets_is_reported(self) -> None:
        pages = [_page("A-1-ЭМ")] * 4 + [_page("B-2-ЭМ")] * 1
        assert read_file_stamp(pages).designations_differ

    def test_a_subdocument_joins_its_parent_when_the_parent_is_on_a_fifth_of_the_sheets(self) -> None:
        pages = [_page("ИТП-1")] * 2 + [_page("ИТП-1.ТМ")] * 8
        stamp = read_file_stamp(pages)
        assert stamp.designation == "ИТП-1" and stamp.designation_votes == (("ИТП-1", 10),)

    def test_a_subdocument_stays_apart_when_the_parent_is_rare(self) -> None:
        pages = [_page("ИТП-1")] * 1 + [_page("ИТП-1.ТМ")] * 9
        stamp = read_file_stamp(pages)
        assert stamp.designation == "ИТП-1.ТМ"

    def test_the_stage_is_the_one_most_sheets_state_and_a_tie_states_none(self) -> None:
        assert read_file_stamp([_page(stage="R")] * 2 + [_page(stage="P")]).project_stage == "R"
        assert read_file_stamp([_page(stage="R"), _page(stage="P")]).project_stage is None

    def test_a_page_without_a_text_layer_is_listed_as_textless(self) -> None:
        pages = [_page(), _page(text=False), _page()]
        assert read_file_stamp(pages).textless_pages == (2,)
        # The envelope's own count of layers wins over the zone: outlined letters in a page that has text elsewhere.
        assert read_file_stamp(pages, has_layer=[True, True, False]).textless_pages == (3,)

    def test_the_facts_survive_the_set_record(self) -> None:
        stamp = read_file_stamp([_page(revision=3, released=date(2026, 4, 7), stage="R", text=True), _page(text=False)])
        assert FileStamp.from_json(stamp.to_json()) == stamp


def _entry(file_id: str, name: str, *, revision: int | None = None, released: date | None = None,
           designation: str | None = "ABC-1-ЭМ", differs: bool = False, textless: tuple[int, ...] = (),
           stage: str | None = None) -> FileEntry:
    stamp = FileStamp(
        page_count=3, designation=designation,
        designation_votes=() if designation is None else ((designation, 3),),
        designations_differ=differs, revision_number=revision, release_date=released, project_stage=stage,
        section_code=section_from_designation(designation), stamped_pages=3, textless_pages=textless,
    )
    return FileEntry(file_id, name, stamp, name_hint(name))


class TestTheProposal:
    def test_the_order_is_revision_then_date_then_file_number_then_name(self) -> None:
        proposal = propose_set([
            _entry("c", "z.pdf", revision=2, released=date(2026, 3, 1)),
            _entry("a", "b.pdf", revision=0, released=date(2026, 1, 1)),
            _entry("b", "a.pdf", revision=1, released=date(2026, 2, 1)),
            _entry("d", "n (2).pdf", revision=2, released=date(2026, 3, 1)),
            _entry("e", "n (1).pdf", revision=2, released=date(2026, 3, 1)),
        ])
        # "z.pdf" has no number in its name and sorts before the numbered files of the same revision and date.
        assert [f.file_id for f in proposal.files] == ["a", "b", "c", "e", "d"]
        assert [f.position for f in proposal.files] == [1, 2, 3, 4, 5]

    def test_a_file_with_no_revision_comes_first(self) -> None:
        proposal = propose_set([_entry("a", "a.pdf", revision=0), _entry("b", "b.pdf", revision=None)])
        assert [f.file_id for f in proposal.files] == ["b", "a"]

    def test_the_proposal_is_a_function_of_its_input_not_of_its_order(self) -> None:
        entries = [_entry(str(i), f"f{i % 2}.pdf", revision=i % 3) for i in range(6)]
        assert propose_set(entries) == propose_set(list(reversed(entries)))

    def test_the_label_is_the_originals_suggestion(self) -> None:
        proposal = propose_set([_entry("a", "a.pdf", revision=3, released=date(2026, 4, 7))])
        assert proposal.files[0].version_label == "V1 Изм.3 07.04.2026"
        assert suggest_label(2, _entry("x", "x.pdf").stamp) == "V2"

    def test_the_stage_and_section_are_proposed_from_the_files_never_invented(self) -> None:
        both = propose_set([_entry("a", "a.pdf", stage="R"), _entry("b", "b.pdf", stage="R")])
        assert (both.project_stage, both.section_code) == ("R", "EOM")
        none = propose_set([_entry("a", "a.pdf", designation="13AV-RD-EM2-PA")])
        assert (none.project_stage, none.section_code) == (None, None)

    def test_each_warning_is_raised_by_its_own_input_only(self) -> None:
        plain = propose_set([_entry("a", "a.pdf", revision=0), _entry("b", "b.pdf", revision=1)])
        assert plain.warnings == ()
        assert propose_set([_entry("a", "a.pdf", differs=True)]).warnings == ("designations_differ",)
        assert propose_set([_entry("a", "a.pdf", revision=1), _entry("b", "b.pdf", revision=1)]).warnings == (
            "duplicate_revision_number",
        )
        assert propose_set([_entry("a", "a.pdf", designation=None)]).warnings == ("no_stamp_found",)
        assert propose_set([_entry("a", "a.pdf", textless=(2,))]).warnings == ("scan_without_text",)

    def test_the_order_that_disagrees_with_the_file_numbers_is_said(self) -> None:
        agreeing = propose_set([_entry("a", "p (1).pdf", revision=0), _entry("b", "p (2).pdf", revision=1)])
        assert agreeing.warnings == ()
        clashing = propose_set([_entry("a", "p (2).pdf", revision=0), _entry("b", "p (1).pdf", revision=1)])
        assert clashing.warnings == ("order_disagrees_with_file_numbers",)
        # One number is no ordering to disagree with.
        assert propose_set([_entry("a", "p (2).pdf", revision=0), _entry("b", "p.pdf", revision=1)]).warnings == ()

    def test_warnings_come_in_the_contracts_order(self) -> None:
        proposal = propose_set([
            _entry("a", "p (3).pdf", revision=1, designation=None, textless=(1,), differs=True),
            _entry("b", "p (2).pdf", revision=1, designation=None),
            _entry("c", "p (1).pdf", revision=2, designation=None),
        ])
        assert proposal.warnings == (
            "designations_differ", "order_disagrees_with_file_numbers", "duplicate_revision_number",
            "no_stamp_found", "scan_without_text",
        )

    def test_an_empty_set_is_a_fault(self) -> None:
        with pytest.raises(ValueError):
            propose_set([])


class TestGrouping:
    def test_files_with_one_designation_are_one_set_whatever_they_are_called(self) -> None:
        a = _entry("a", "Раздел 1/план.pdf")
        b = _entry("b", "другая папка/b.pdf")
        assert grouping_key(a.stamp, a.hint) == grouping_key(b.stamp, b.hint)

    def test_the_designation_is_compared_folded(self) -> None:
        a = _entry("a", "a.pdf", designation="синт-01-эм")
        b = _entry("b", "b.pdf", designation="СИНТ-01-ЭМ")
        assert grouping_key(a.stamp, a.hint) == grouping_key(b.stamp, b.hint)
        assert fold_designation(" СИНТ-01  ЭМ ") == "СИНТ-01 ЭМ"

    def test_a_name_never_overrides_a_designation(self) -> None:
        a = _entry("a", "same.pdf", designation="A-1-ЭМ")
        b = _entry("b", "same.pdf", designation="B-2-ЭМ")
        assert grouping_key(a.stamp, a.hint) != grouping_key(b.stamp, b.hint)

    def test_without_a_designation_the_name_groups(self) -> None:
        a = _entry("a", "Чертежи (1).pdf", designation=None)
        b = _entry("b", "Чертежи (2).pdf", designation=None)
        assert grouping_key(a.stamp, a.hint) == grouping_key(b.stamp, b.hint) == "name:чертежи"
