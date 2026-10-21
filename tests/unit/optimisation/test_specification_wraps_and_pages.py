"""`SPEC-TABLE-RECORDING-01` part 1 (debt `D-184`): what the saved text can say about a Form-7 table.

Container-free. The pages are written the way ``source_preparation`` saves them (pdfplumber's
lines joined by ``\\n``, a row's cells joined by single spaces, no column geometry). Three
rules are held, each only as far as plain text supports it and each with the boundary where it
stops and today's reading stays:

* a cell that wraps **above** its anchor line goes to its own row when the row's fragment
  cannot open a name and the lines above show where the cell begins;
* a table that ran to the end of its page is **continued** on the next page without a repeated
  header when the numbering goes on (or the page says «Продолжение») and nothing else comes
  before the first row;
* the **manufacturer** cell is the tail of a row's fragment from a legal form on, when the
  header has a manufacturer column.

The type/mark and the code are deliberately not split: no test here (and no rule) pretends the
text separates them from the name.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from auditmanager.optimisation import specification
from auditmanager.optimisation.specification import (
    LEGAL_FORMS,
    SpecificationExtraction,
    extract_specification,
    strip_legal_form,
)

VERSION = "ver_01M2545JSD15ETSNNV904XA001"

HEADER = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
)
HEADER_NO_MANUFACTURER = "Поз. Наименование Ед. изм. Кол. Примечание\n"


def _stamp(sheet: int) -> str:
    return (
        "Изм. Кол.уч. Лист №док. Подпись Дата\n"
        f"Разработал Иванов 01.26 Стадия Лист Листов\nР {sheet} 12\n"
    )


def _extract(*pages: str) -> SpecificationExtraction:
    return extract_specification(
        version_uid=VERSION, pages={number: text for number, text in enumerate(pages, start=1)}
    )


def _names(result: SpecificationExtraction) -> dict[str | None, str]:
    return {row.position: row.name for row in result.rows}


def _spans(result: SpecificationExtraction) -> dict[str | None, tuple[int, int]]:
    return {row.position: (row.line_start, row.line_end) for row in result.rows}


# -- cells that wrap above their anchor line ---------------------------------------------------

CENTRED_PAGE = (
    "Спецификация оборудования, изделий и материалов\n" + HEADER +
    "1 2 3 4 5 6 7 8 9\n"
    "Изделия\n"
    "Дверь противопожарная\n"
    "1 металлическая ДПМ-01/60 ООО «Промет» шт. 4 45,5\n"
    "однопольная, левая\n"
    "Анкер химический\n"
    "2 HIT-HY 200 Hilti шт 200 0,05\n"
    "Окно ПВХ двухкамерное\n"
    "3 ОП В2 1460х1460 шт 12\n" + _stamp(7)
)


def test_a_cell_wrapped_above_its_anchor_line_goes_to_its_own_row() -> None:
    result = _extract(CENTRED_PAGE)
    assert _names(result) == {
        "1": "Дверь противопожарная металлическая ДПМ-01/60 ООО «Промет» однопольная, левая",
        "2": "Анкер химический HIT-HY 200 Hilti",
        "3": "Окно ПВХ двухкамерное ОП В2 1460х1460",
    }
    # The span runs from the first line of the name to the last: provenance stays honest.
    assert _spans(result) == {"1": (6, 8), "2": (9, 10), "3": (11, 12)}
    assert dict(result.skipped_by_reason) == {"column_numbering": 1}
    row = result.rows[1]
    assert (row.unit, row.quantity, row.mass_text, row.group) == (
        "шт", Decimal("200"), "0,05", "Изделия",
    )


def test_a_fragment_that_can_open_a_name_takes_nothing_from_the_lines_above() -> None:
    page = (
        HEADER_NO_MANUFACTURER +
        "1 Дверь противопожарная ДПМ-01/60 шт. 4\n"
        "Анкер химический\n"
        "2 Окно ПВХ двухкамерное шт 12\n"
    )
    assert _names(_extract(page)) == {
        "1": "Дверь противопожарная ДПМ-01/60 Анкер химический",
        "2": "Окно ПВХ двухкамерное",
    }


def test_without_a_line_that_opens_a_name_above_nothing_moves() -> None:
    page = (
        HEADER_NO_MANUFACTURER +
        "1 Дверь противопожарная ДПМ-01/60 шт. 4\n"
        "однопольная, левая\n"
        "со сменным замком\n"
        "2 ДПМ-02/60 шт 3\n"
    )
    result = _extract(page)
    assert _names(result) == {
        "1": "Дверь противопожарная ДПМ-01/60 однопольная, левая со сменным замком",
        "2": "ДПМ-02/60",
    }
    assert result.skipped_count == 0


def test_the_cell_is_taken_up_to_the_nearest_line_that_opens_a_name() -> None:
    page = (
        HEADER_NO_MANUFACTURER +
        "1 Дверь противопожарная ДПМ-01/60 шт. 4\n"
        "Анкер химический\n"
        "для бетона и кирпича\n"
        "повышенной прочности\n"
        "2 HIT-HY 200 шт 200\n"
    )
    result = _extract(page)
    assert _names(result) == {
        "1": "Дверь противопожарная ДПМ-01/60",
        "2": "Анкер химический для бетона и кирпича повышенной прочности HIT-HY 200",
    }
    assert _spans(result) == {"1": (2, 2), "2": (3, 6)}


def test_a_name_that_opens_more_than_the_continuation_bound_above_is_not_taken() -> None:
    page = (
        HEADER_NO_MANUFACTURER +
        "Материалы\n"
        "Анкер химический\n"
        "для бетона и кирпича\n"
        "повышенной прочности\n"
        "в ампулах\n"
        "1 HIT-HY 200 шт 200\n"
    )
    result = _extract(page)
    assert _names(result) == {"1": "HIT-HY 200"}
    assert [skip.line for skip in result.skipped] == [3, 4, 5, 6]
    assert {skip.reason for skip in result.skipped} == {"text_before_first_row"}


def test_lines_before_the_first_row_join_it_and_the_rest_are_still_reported() -> None:
    page = (
        HEADER_NO_MANUFACTURER +
        "Наружные блоки\n"
        "Дверь противопожарная\n"
        "1 металлическая ДПМ-01/60 шт. 4\n"
    )
    result = _extract(page)
    assert _names(result) == {"1": "Дверь противопожарная металлическая ДПМ-01/60"}
    assert [(skip.line, skip.reason, skip.excerpt) for skip in result.skipped] == [
        (2, "text_before_first_row", "Наружные блоки"),
    ]


def test_a_skipped_line_between_the_rows_breaks_the_lines_that_touch_the_next_anchor() -> None:
    page = (
        HEADER_NO_MANUFACTURER +
        "1 Дверь противопожарная ДПМ-01/60 шт. 4\n"
        "Анкер химический\n"
        "для бетона\n"
        "и кирпича\n"
        "повышенной прочности\n"
        "2 HIT-HY 200 шт 200\n"
    )
    result = _extract(page)
    # Row 1 holds three continuation lines; the fourth is skipped, and the skipped line sits
    # between the first three and row 2's anchor: "Анкер химический" is not directly above it.
    assert _names(result) == {
        "1": "Дверь противопожарная ДПМ-01/60 Анкер химический для бетона и кирпича",
        "2": "HIT-HY 200",
    }
    assert dict(result.skipped_by_reason) == {"continuation_limit": 1}


# -- a table continued onto the next page -----------------------------------------------------

FIRST_PAGE = (
    "Спецификация оборудования, изделий и материалов\n" + HEADER +
    "1 2 3 4 5 6 7 8 9\n"
    "Изделия\n"
    "1 Дверь противопожарная ДПМ-01/60 ООО «Промет» шт. 4 45,5\n"
    "2 Анкер химический HIT-HY 200 шт 200 0,05\n" + _stamp(7)
)
SECOND_PAGE = (
    "3 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n"
    "Материалы\n"
    "4 Профиль направляющий ПН 50х40 п. м 120\n" + _stamp(8)
)
THIRD_PAGE = "5 Гидроизоляционная мембрана Техноэласт ЭПП м² 340,8\n" + _stamp(9)


def test_a_table_that_ran_to_the_end_of_its_page_continues_without_a_repeated_header() -> None:
    result = _extract(FIRST_PAGE, SECOND_PAGE, THIRD_PAGE)
    assert [(row.page_number, row.position, row.table_ordinal) for row in result.rows] == [
        (1, "1", 1), (1, "2", 1), (2, "3", 1), (2, "4", 1), (3, "5", 1),
    ]
    assert result.table_count == 1
    (table,) = result.tables
    assert (table.page_number, table.row_count, table.continued_on) == (1, 5, (2, 3))
    assert [row.sheet_label for row in result.rows] == ["7", "7", "8", "8", "9"]
    assert [row.group for row in result.rows] == ["Изделия", "Изделия", None, "Материалы", None]
    assert result.rows[3].unit == "п.м" and result.rows[4].quantity == Decimal("340.8")
    assert result.skipped_count == 1  # the «1 2 3 …» column numbering of the first page


def test_a_page_that_says_continuation_may_start_with_column_numbers_and_a_group() -> None:
    second = (
        "Продолжение таблицы\n"
        "1 2 3 4 5 6 7 8 9\n"
        "Материалы\n"
        "3 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n" + _stamp(8)
    )
    result = _extract(FIRST_PAGE, second)
    assert [(row.page_number, row.position, row.group) for row in result.rows[2:]] == [
        (2, "3", "Материалы"),
    ]
    assert [(s.page_number, s.line, s.reason) for s in result.skipped if s.page_number == 2] == [
        (2, 1, "text_before_first_row"), (2, 2, "column_numbering"),
    ]


def test_a_gap_in_the_numbering_ends_the_table_with_its_page() -> None:
    second = "7 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n" + _stamp(8)
    result = _extract(FIRST_PAGE, second)
    assert [row.position for row in result.rows] == ["1", "2"]
    assert result.tables[0].continued_on == ()


def test_a_page_that_says_continuation_is_continued_whatever_its_first_number() -> None:
    second = "Продолжение\n1 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n" + _stamp(8)
    result = _extract(FIRST_PAGE, second)
    assert [(row.page_number, row.position) for row in result.rows] == [(1, "1"), (1, "2"), (2, "1")]


def test_a_table_without_a_position_column_is_continued_only_when_the_page_says_so() -> None:
    first = "Наименование Тип Кол-во, шт. Масса, кг\nАнкер химический HIT 8 0,25\n" + _stamp(1)
    plain = "Уголок стальной 50х5 4 0,5\n" + _stamp(2)
    marked = "Продолжение\nУголок стальной 50х5 4 0,5\n" + _stamp(2)
    assert [row.page_number for row in _extract(first, plain).rows] == [1]
    assert [row.page_number for row in _extract(first, marked).rows] == [1, 2]


def test_a_title_block_is_not_a_row_of_the_next_page() -> None:
    # Without a position or a unit column, ``Разработал Иванов 01.26`` reads as a row; a page
    # that holds nothing but its stamp must not be "continued" with it.
    first = "Наименование Тип Кол-во, шт. Масса, кг\nАнкер химический HIT 8 0,25\n" + _stamp(1)
    second = "Продолжение\nРазработал Иванов 01.26 Стадия Лист Листов\nР 2 12\n"
    result = _extract(first, second)
    assert [row.page_number for row in result.rows] == [1]
    assert result.tables[0].continued_on == ()


def test_text_before_the_first_row_is_not_a_plain_continuation() -> None:
    second = (
        "Общие указания к спецификации\n"
        "3 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n" + _stamp(8)
    )
    assert [row.position for row in _extract(FIRST_PAGE, second).rows] == ["1", "2"]


def test_a_page_with_a_header_of_its_own_is_a_new_table_not_a_continuation() -> None:
    second = HEADER_NO_MANUFACTURER + "3 Окно ПВХ двухкамерное шт 12\n" + _stamp(8)
    result = _extract(FIRST_PAGE, second)
    assert result.table_count == 2
    assert [(row.position, row.table_ordinal) for row in result.rows] == [
        ("1", 1), ("2", 1), ("3", 2),
    ]
    assert [table.continued_on for table in result.tables] == [(), ()]


def test_the_next_page_must_be_the_next_page() -> None:
    result = extract_specification(
        version_uid=VERSION,
        pages={
            1: FIRST_PAGE,
            3: "3 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n" + _stamp(8),
        },
    )
    assert [row.position for row in result.rows] == ["1", "2"]


def test_a_page_that_does_not_continue_ends_the_chain() -> None:
    blank = "Общие данные\nЗдание жилое.\n"
    result = _extract(FIRST_PAGE, blank, "3 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n")
    assert [row.position for row in result.rows] == ["1", "2"]


def test_a_table_cut_by_a_note_is_not_continued() -> None:
    first = (
        "Поз. Наименование Ед. изм. Кол.\n"
        "1 Кабель ВВГнг 3х2,5 м 120\n"
        "Примечание: кабель поставляется барабанами.\n"
    )
    second = "2 Кабель ВВГнг 3х1,5 м 80\n"
    assert [row.position for row in _extract(first, second).rows] == ["1"]


def test_a_stamp_followed_by_rows_of_the_table_is_not_the_end_of_the_page() -> None:
    # The stamp sits in the middle of the reading order, so which lines are the table's
    # continuation is not known: the next page is left alone.
    first = (
        "Поз. Наименование Ед. изм. Кол.\n"
        "1 Кабель ВВГнг 3х2,5 м 120\n"
        "Изм. Кол.уч. Лист №док. Подпись Дата\n"
        "2 Кабель ВВГнг 3х1,5 м 80\n"
    )
    second = "2 Кабель ВВГнг 3х1,5 м 80\n"
    assert [row.position for row in _extract(first, second).rows] == ["1"]


def test_a_table_that_ends_at_the_page_without_a_stamp_is_continued() -> None:
    first = "Поз. Наименование Ед. изм. Кол.\n1 Кабель ВВГнг 3х2,5 м 120\n"
    second = "2 Кабель ВВГнг 3х1,5 м 80\n"
    assert [(row.page_number, row.position) for row in _extract(first, second).rows] == [
        (1, "1"), (2, "2"),
    ]


def test_dotted_positions_need_the_continuation_line() -> None:
    first = "Поз. Наименование Ед. изм. Кол.\n1.1 Кабель ВВГнг 3х2,5 м 120\n" + _stamp(1)
    plain = "1.2 Кабель ВВГнг 3х1,5 м 80\n"
    assert [row.page_number for row in _extract(first, plain).rows] == [1]
    assert [row.page_number for row in _extract(first, "Продолжение\n" + plain).rows] == [1, 2]


def test_the_row_bound_still_counts_the_rows_of_a_continued_page(monkeypatch) -> None:
    monkeypatch.setattr(specification, "MAX_SPECIFICATION_ROWS", 2)
    result = _extract(FIRST_PAGE, SECOND_PAGE)
    assert len(result.rows) == 2 and result.over_limit is True
    assert result.skipped_by_reason["rows_over_limit"] == 2


# -- the manufacturer cell ---------------------------------------------------------------------


def test_the_manufacturer_is_the_tail_of_the_fragment_from_a_legal_form_on() -> None:
    result = _extract(CENTRED_PAGE)
    door, anchor, window = result.rows
    assert door.manufacturer == "ООО «Промет»"
    # The name keeps it: nothing that reads the description changes.
    assert "ООО «Промет»" in door.name
    # «Hilti» is a manufacturer with no legal form: the text does not show it, so no split.
    assert (anchor.manufacturer, window.manufacturer) == (None, None)


@pytest.mark.parametrize(
    ("fragment", "manufacturer"),
    [
        ("Дверь ДПМ-01/60 ООО «Промет»", "ООО «Промет»"),
        ('Дверь ДПМ-01/60 ООО "Промет"', 'ООО "Промет"'),
        ("Дверь ДПМ-01/60 АО Промет Сервис", "АО Промет Сервис"),
        ("Дверь ДПМ-01/60 OOO «Промет»", "OOO «Промет»"),
        ("Дверь ДПМ-01/60 ИП Иванов", "ИП Иванов"),
        ("Дверь ДПМ-01/60 Промет", None),  # no legal form
        ("ООО «Промет»", None),  # nothing would remain of the name
        ("Дверь ДПМ-01/60 ООО", None),  # nothing after the legal form
        ("Дверь ООО-1 ДПМ-01/60", None),  # a mark that starts like a legal form
    ],
)
def test_manufacturer_forms(fragment: str, manufacturer: str | None) -> None:
    page = HEADER + f"1 {fragment} шт 4\n"
    (row,) = _extract(page).rows
    assert row.manufacturer == manufacturer


def test_without_a_manufacturer_column_the_text_is_not_split() -> None:
    page = HEADER_NO_MANUFACTURER + "1 Дверь ДПМ-01/60 ООО «Промет» шт 4\n"
    (row,) = _extract(page).rows
    assert row.manufacturer is None and row.name == "Дверь ДПМ-01/60 ООО «Промет»"


def test_the_legal_form_helpers() -> None:
    assert {"ООО", "АО", "ЗАО", "ПАО"} <= LEGAL_FORMS
    assert strip_legal_form("ООО «Промет»") == "«Промет»"
    assert strip_legal_form("Промет") == "Промет"
    assert strip_legal_form("ООО") == "ООО"
