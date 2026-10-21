"""`W60-OPT-MATCH-01` phase A: specification rows from a saved text layer, container-free.

The pages are written the way ``source_preparation`` saves them: pdfplumber's lines joined by
``\\n``, the cells of a row joined by single spaces, words sometimes glued together. The
``REAL_AR_PAGE`` excerpt is verbatim from page 14 (sheet 10) of the local real AR set
``13АВ-РД-АР-ТП1-ТП2`` extracted by ``analysis.stages.extraction``; the whole 30-page set
gives exactly the one table and the two rows asserted below.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from auditmanager.optimisation import specification
from auditmanager.optimisation.specification import (
    EXTRACTION_ALGORITHM,
    FORM7_COLUMNS,
    QUANTITY_AMBIGUOUS,
    QUANTITY_NOT_NUMERIC,
    SKIP_REASONS,
    TABLE_HEADER_AMBIGUOUS,
    TABLE_PARSED,
    UNIT_SOURCE_COLUMN,
    UNIT_SOURCE_HEADER,
    UNITS,
    SpecificationExtraction,
    canonical_unit,
    extract_specification,
)

VERSION = "ver_01M2545JSD15ETSNNV904XA001"
OTHER_VERSION = "ver_01M2545JSD15ETSNNV904XA002"

FORM7_PAGE = """Спецификация оборудования, изделий и материалов
Поз. Наименование и техническая характеристика Тип, марка оборудования. Код Завод- Ед. Кол. Масса Примечание
Обозначение документа, опросного листа изделия, изготовитель изм. 1 ед.,
материала кг
1 2 3 4 5 6 7 8 9
Изделия
1 Дверь противопожарная металлическая ДПМ-01/60 EI60 ООО «Промет» шт. 4 45,5
однопольная, левая
2 Окно ПВХ двухкамерное ОП В2 1460х1460 ГОСТ 30674-99 шт 12
3 Кирпич керамический полнотелый КР-р-по 250х120х65/1НФ/150/2,0/50 ГОСТ 530-2012 шт 1 250 3,5
Материалы
4 Утеплитель минераловатный ВЕНТИ БАТТС м3 12,5 по месту
плотностью 90 кг/м³, толщ. 100 мм
5 Гидроизоляционная мембрана Техноэласт ЭПП м² 340,8
6 Профиль направляющий ПН 50х40 п. м 120
7 Монтажная пена компл. - по месту
8 Плита м 2 шт 4
Изм. Кол.уч. Лист №док. Подпись Дата
Разработал Иванов 01.26 Стадия Лист Листов
Р 7 12
"""

REAL_AR_PAGE = """4.Т.10 ГРЩ-1 ВП-Б 1,3
4.Т.11 ГРЩ-1 ВП-А 1,3
114,7
Ведомость металлических изделий
Поз. Наименование Кол-во, шт. Примечание
1 Металлический щит МЩ-1 12
План наотм. +0,400 2 Металлический щит МЩ-2 12
3 Рифленая сталь 690х395 t=4 мм 7
1. СпецификациюэлементовметаллическихщитовМЩ-1 иМЩ-2 см. л. 17 и18
13АВ-РД-АР-ТП1/ТП2
Изм. Кол.уч. Лист №док. Подпись Дата
Стадия Лист Листов
АрхитектурныерешенияТП; ТП2
10
ФорматА2
Экспликация помещений на отм. +0,400
Кат.
Наименование № пом. Площадь, м2 пом.
4.Т.1 Камера силового трансформатора ТП-13А Луч А 11,1 В4
"""


def _extract(*pages: str, version: str = VERSION) -> SpecificationExtraction:
    return extract_specification(
        version_uid=version, pages={number: text for number, text in enumerate(pages, start=1)}
    )


def _by_position(result: SpecificationExtraction) -> dict[str | None, specification.SpecificationRow]:
    return {row.position: row for row in result.rows}


# -- Form 7 ------------------------------------------------------------------------------


def test_a_split_form7_header_is_read_as_one_with_all_nine_columns() -> None:
    result = _extract(FORM7_PAGE)
    assert result.algorithm == EXTRACTION_ALGORITHM
    assert result.table_count == 1
    (table,) = result.tables
    assert (table.page_number, table.header_line_start, table.header_line_end) == (1, 2, 4)
    assert table.columns == FORM7_COLUMNS
    assert (table.status, table.implicit_unit, table.row_count) == (TABLE_PARSED, None, 7)


def test_form7_rows_keep_position_name_unit_quantity_mass_and_note() -> None:
    rows = _by_position(_extract(FORM7_PAGE))
    door = rows["1"]
    assert door.name == (
        "Дверь противопожарная металлическая ДПМ-01/60 EI60 ООО «Промет» однопольная, левая"
    )
    assert (door.unit_text, door.unit, door.unit_source) == ("шт.", "шт", UNIT_SOURCE_COLUMN)
    assert (door.quantity_text, door.quantity, door.quantity_issue) == ("4", Decimal("4"), None)
    assert (door.mass_text, door.note, door.group) == ("45,5", None, "Изделия")
    assert (door.page_number, door.sheet_label, door.line_start, door.line_end) == (1, "7", 7, 8)

    window = rows["2"]
    assert window.name == "Окно ПВХ двухкамерное ОП В2 1460х1460 ГОСТ 30674-99"
    assert (window.quantity, window.mass_text, window.note) == (Decimal("12"), None, None)

    wool = rows["4"]
    assert wool.name == (
        "Утеплитель минераловатный ВЕНТИ БАТТС плотностью 90 кг/м³, толщ. 100 мм"
    )
    assert (wool.unit, wool.quantity, wool.note, wool.group) == (
        "м3", Decimal("12.5"), "по месту", "Материалы",
    )
    assert (rows["5"].unit_text, rows["5"].unit, rows["5"].quantity) == (
        "м²", "м2", Decimal("340.8"),
    )
    assert (rows["6"].unit_text, rows["6"].unit, rows["6"].quantity) == (
        "п. м", "п.м", Decimal("120"),
    )


def test_a_quantity_that_is_not_one_plain_number_is_never_a_number() -> None:
    rows = _by_position(_extract(FORM7_PAGE))
    foam = rows["7"]
    assert (foam.unit, foam.quantity_text, foam.quantity, foam.quantity_issue) == (
        "компл", "-", None, QUANTITY_NOT_NUMERIC,
    )
    # «1 250» before a mass column: 1250 pieces, or 1 piece of 250 kg? Not decided here.
    brick = rows["3"]
    assert (brick.quantity_text, brick.quantity, brick.quantity_issue) == (
        "1 250", None, QUANTITY_AMBIGUOUS,
    )


def test_a_row_with_two_unit_and_quantity_places_is_skipped_not_guessed() -> None:
    result = _extract(FORM7_PAGE)
    assert "8" not in _by_position(result)
    assert dict(result.skipped_by_reason) == {"anchor_ambiguous": 1, "column_numbering": 1}
    assert [(s.line, s.reason, s.excerpt) for s in result.skipped] == [
        (5, "column_numbering", "1 2 3 4 5 6 7 8 9"),
        (17, "anchor_ambiguous", "8 Плита м 2 шт 4"),
    ]


def test_digit_grouping_is_read_only_when_no_column_can_follow_the_quantity() -> None:
    page = (
        "Поз. Наименование Ед. изм. Кол.\n"
        "1 Кирпич керамический шт 1 250\n"
        "2 Раствор кладочный м3 12,75\n"
    )
    rows = _by_position(_extract(page))
    assert (rows["1"].quantity_text, rows["1"].quantity) == ("1 250", Decimal("1250"))
    assert rows["2"].quantity == Decimal("12.75")


# -- the real AR set ---------------------------------------------------------------------


def test_the_real_ar_schedule_reads_two_rows_with_the_header_unit() -> None:
    result = _extract(REAL_AR_PAGE)
    assert result.table_count == 1
    (table,) = result.tables
    assert table.columns == ("position", "name", "quantity", "note")
    assert (table.implicit_unit, table.header_line_start, table.header_line_end) == ("шт", 5, 5)
    assert [
        (row.position, row.name, row.unit, row.unit_source, row.quantity, row.sheet_label)
        for row in result.rows
    ] == [
        ("1", "Металлический щит МЩ-1", "шт", UNIT_SOURCE_HEADER, Decimal("12"), "10"),
        ("3", "Рифленая сталь 690х395 t=4 мм", "шт", UNIT_SOURCE_HEADER, Decimal("7"), "10"),
    ]


def test_interleaved_drawing_text_and_the_first_note_are_not_rows() -> None:
    result = _extract(REAL_AR_PAGE)
    # «План наотм. +0,400» sits on the second row's baseline: reported, not repaired.
    assert [(s.line, s.reason) for s in result.skipped] == [(7, "position_missing")]
    # «… см. л. 17 и18» ends the table; 17 is never a quantity of a third row.
    assert all(row.quantity != Decimal("17") for row in result.rows)
    # The room schedule (Наименование, № пом., Площадь) is no specification.
    assert all(table.page_number == 1 and table.header_line_start == 5 for table in result.tables)


# -- what is not a table, and where a table ends -----------------------------------------


def test_a_drawing_stamp_is_never_a_header() -> None:
    page = (
        "Изм. Кол.уч. Лист №док. Подпись Дата Наименование Примечание\n"
        "1 Кабель шт 4\n"
    )
    result = _extract(page)
    assert (result.table_count, result.rows) == (0, ())


def test_room_and_finishing_schedules_are_not_specifications() -> None:
    page = (
        "Ведомость отделки стен\n"
        "Тип Наименование помещения Состав стены Кол-во, м2 Примечание\n"
        "Отп-1 Коридор - Грунтовка глубокого проникновения 117,4\n"
    )
    assert _extract(page).table_count == 0


def test_a_header_naming_two_quantity_columns_is_reported_and_not_read() -> None:
    page = (
        "Поз. Наименование Кол-во, м3 Кол-во, м2 Примечание\n"
        "1 Стена из газобетонных блоков 4,58 30,5\n"
        "2 Перегородка кирпичная 2,60 21,7\n"
    )
    result = _extract(page)
    (table,) = result.tables
    assert (table.status, table.row_count) == (TABLE_HEADER_AMBIGUOUS, 0)
    assert result.rows == ()
    assert dict(result.skipped_by_reason) == {"table_header_ambiguous": 2}


def test_a_table_ends_at_the_stamp_and_never_continues_onto_the_next_page() -> None:
    first = "Поз. Наименование Ед. изм. Кол.\n1 Кабель ВВГнг 3х2,5 м 120\nИзм. Кол.уч. Лист №док. Подпись Дата\n2 Кабель ВВГнг 3х1,5 м 80\n"
    second = "3 Кабель ВВГнг 5х4 м 40\n"
    result = _extract(first, second)
    assert [(row.page_number, row.position) for row in result.rows] == [(1, "1")]


def test_continuation_lines_are_bounded_and_text_before_the_first_row_reported() -> None:
    page = (
        "Поз. Наименование Ед. изм. Кол. Примечание\n"
        "строка до первой позиции\n"
        "1 Панель сэндвич м2 50\n"
        "продолжение 1\n"
        "продолжение 2\n"
        "продолжение 3\n"
        "продолжение 4\n"
    )
    result = _extract(page)
    (row,) = result.rows
    assert row.name == "Панель сэндвич продолжение 1 продолжение 2 продолжение 3"
    assert (row.line_start, row.line_end) == (3, 6)
    assert dict(result.skipped_by_reason) == {
        "text_before_first_row": 1, "continuation_limit": 1,
    }


def test_too_many_lines_without_an_anchor_end_the_table() -> None:
    filler = "\n".join(f"Пояснение номер {word}" for word in "абвгдежз")
    page = f"Поз. Наименование Ед. изм. Кол.\n{filler}\n1 Кабель м 10\n"
    result = _extract(page)
    assert result.rows == ()
    assert dict(result.skipped_by_reason) == {"text_before_first_row": 6}


def test_an_implicit_unit_table_with_a_mass_column_reads_the_trailing_pair() -> None:
    page = (
        "Наименование Тип Кол-во, шт. Масса, кг\n"
        "Анкер химический HIT 8 0,25\n"
        "Уголок стальной 50х5 4\n"
    )
    result = _extract(page)
    first, second = result.rows
    assert (first.name, first.quantity, first.mass_text) == (
        "Анкер химический HIT", Decimal("8"), "0,25",
    )
    assert (second.name, second.quantity, second.quantity_issue) == (
        "Уголок стальной 50х5", None, QUANTITY_AMBIGUOUS,
    )


def test_a_header_without_any_unit_leaves_rows_without_a_unit() -> None:
    page = "Поз. Наименование Кол. Примечание\n1 Решётка вентиляционная 6\n"
    (row,) = _extract(page).rows
    assert (row.unit, row.unit_text, row.unit_source, row.quantity) == (
        None, None, None, Decimal("6"),
    )


# -- provenance, bounds, determinism -----------------------------------------------------


def test_row_ids_are_digests_of_version_page_and_span() -> None:
    once = _extract(FORM7_PAGE)
    again = _extract(FORM7_PAGE)
    other = _extract(FORM7_PAGE, version=OTHER_VERSION)
    moved = _extract("", FORM7_PAGE)
    assert once == again
    ids = [row.row_id for row in once.rows]
    assert all(re.fullmatch(r"sr-[0-9a-f]{32}", value) for value in ids)
    assert len(set(ids)) == len(ids)
    assert not set(ids) & {row.row_id for row in other.rows}
    assert not set(ids) & {row.row_id for row in moved.rows}
    assert [row.name for row in moved.rows] == [row.name for row in once.rows]


def test_rows_beyond_the_bound_make_the_extraction_over_limit(monkeypatch) -> None:
    monkeypatch.setattr(specification, "MAX_SPECIFICATION_ROWS", 3)
    result = _extract(FORM7_PAGE)
    assert result.over_limit is True
    assert len(result.rows) == 3
    assert result.skipped_by_reason["rows_over_limit"] == 4


def test_the_skipped_listing_is_capped_while_its_counts_stay_complete(monkeypatch) -> None:
    monkeypatch.setattr(specification, "MAX_LISTED_SKIPS", 1)
    result = _extract(FORM7_PAGE)
    assert len(result.skipped) == 1
    assert result.skipped_count == 2


def test_every_reported_reason_is_a_declared_one() -> None:
    result = _extract(FORM7_PAGE, REAL_AR_PAGE)
    assert set(result.skipped_by_reason) <= set(SKIP_REASONS)
    assert result.page_count == 2
    assert [row.page_number for row in result.rows] == sorted(row.page_number for row in result.rows)


@pytest.mark.parametrize(
    ("spelling", "canonical"),
    [
        ("шт", "шт"), ("шт.", "шт"), ("ШТ", "шт"), ("штук", "шт"),
        ("м", "м"), ("м.", "м"),
        ("м2", "м2"), ("м²", "м2"), ("кв. м", "м2"), ("кв.м", "м2"),
        ("м3", "м3"), ("м³", "м3"), ("куб. м", "м3"),
        ("кг", "кг"), ("т", "т"), ("тн", "т"),
        ("компл.", "компл"), ("комплект", "компл"), ("к-т", "компл"),
        ("п.м.", "п.м"), ("п. м", "п.м"), ("пог. м", "п.м"), ("м.п.", "п.м"),
        ("мм", None), ("упак.", None), ("", None), (None, None),
    ],
)
def test_unit_spellings(spelling: str | None, canonical: str | None) -> None:
    assert canonical_unit(spelling) == canonical
    if canonical is not None:
        assert canonical in UNITS
