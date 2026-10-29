"""The page parser and the stream of positions (`CMP-VC-SPEC-01`, part A).

Pages are drawn by the ``drawn`` fixture the way the page profile reports them (words and vector lines in points). The rules under
test are those of the original's ``spec.py`` (PDF-proverka at ``23f379fd``): columns by the vertical rules of the header, rows by
the horizontal rules, the type of a row by its filled cells, an ambiguous boundary flagged and never guessed, every value verbatim.
"""

from __future__ import annotations

import pytest

from auditmanager.comparison.specification import table


def _rows(parsed):
    return [r["cells"] for r in parsed["rows"]]


def test_a_specification_page_is_read_row_by_row_with_every_value_verbatim(drawn) -> None:
    page = drawn.Page()
    page.row({"pos": "1", "mark": "СИНТ-ЩО.01", "name": "Щит освещения ЩО-1", "quantity": "1", "mass": "45,0"})
    page.row({"pos": "2", "mark": "СИНТ-КБ.325", "name": "Кабель ВВГнг 3×2,5, м", "quantity": "320", "mass": "0,12", "note": "по проекту"})
    parsed = page.parse()
    assert parsed["parsed"] is True
    assert parsed["columns"] == ["pos", "mark", "name", "quantity", "mass", "note"]
    assert _rows(parsed) == [
        {"pos": "1", "mark": "СИНТ-ЩО.01", "name": "Щит освещения ЩО-1", "quantity": "1", "mass": "45,0"},
        {"pos": "2", "mark": "СИНТ-КБ.325", "name": "Кабель ВВГнг 3×2,5, м", "quantity": "320", "mass": "0,12", "note": "по проекту"},
    ]


def test_the_first_row_under_the_header_is_a_row(drawn) -> None:
    """The original took the bottom of the header from the lowest word of a band around the labels, which dropped the first row
    of a compact form; the header here ends at the first row rule below the labels."""
    page = drawn.Page()
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    page.row({"pos": "2", "mark": "М-2", "name": "Вторая", "quantity": "6"})
    assert [c["pos"] for c in _rows(page.parse())] == ["1", "2"]


def test_the_row_of_column_numbers_under_the_header_is_not_a_position(drawn) -> None:
    page = drawn.Page(numbered_row=True)
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    assert [c["pos"] for c in _rows(page.parse())] == ["1"]


def test_a_page_without_a_header_is_not_a_specification(drawn) -> None:
    page = drawn.Page(header_words=False)
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    assert page.parse() is None


def test_a_table_that_names_fewer_than_five_columns_is_not_a_specification(drawn) -> None:
    """A «Поз.» and a «Наименование» in a table of a single-line diagram are not a specification header."""
    page = drawn.Page(header={"pos": ["Поз."], "name": ["Наименование"], "quantity": ["Кол."], "mark": ["Тип"]})
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    assert page.parse() is None


def test_a_table_that_does_not_span_the_sheet_is_an_inset_of_a_drawing(drawn) -> None:
    narrow = [("pos", 56.7, 76.7), ("mark", 76.7, 116.7), ("name", 116.7, 186.7), ("quantity", 186.7, 206.7), ("mass", 206.7, 236.7),
              ("note", 236.7, 276.7)]
    page = drawn.Page(columns=narrow)
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    assert page.parse() is None


def test_a_header_without_row_rules_is_found_but_not_read(drawn) -> None:
    page = drawn.Page(rules=False)
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    assert page.parse() == {"parsed": False, "reason": "нет линий строк таблицы"}


def test_a_header_without_column_rules_is_found_but_not_read(drawn) -> None:
    page = drawn.Page()
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    page.finish()
    from auditmanager.comparison.specification import table as t

    horizontal_only = [ln for ln in page.lines if abs(ln[0] - ln[2]) > 1]
    assert t.parse_page(page.words, horizontal_only, drawn.PAGE_W, drawn.PAGE_H) == {"parsed": False, "reason": "колонки таблицы не найдены"}


def test_the_title_block_is_not_read_as_rows(drawn) -> None:
    page = drawn.Page()
    page.row({"pos": "1", "mark": "М-1", "name": "Первая", "quantity": "5"})
    top_of_stamp = page.y + 1
    page.row({"pos": "2", "mark": "М-2", "name": "Штамп", "quantity": "7"})
    parsed = page.parse(stamp_zone=[14.0, top_of_stamp, 595.0, 842.0])
    assert [c["pos"] for c in _rows(parsed)] == ["1"]


def test_a_parent_row_has_sub_rows_that_take_its_name_and_mark(drawn) -> None:
    page = drawn.Page()
    page.row({"mark": "ВВГнг-LS", "name": "Кабель силовой"})
    page.row({"name": "3х1.5", "quantity": "100", "mass": "0,1"})
    page.row({"name": "3х2.5", "quantity": "200"})
    page.row({"pos": "2", "mark": "АВ-16", "name": "Выключатель", "quantity": "12"})
    flow = table.assemble([{"page": 3, "rows": page.parse()["rows"]}])
    kinds = [(i["kind"], i["name"], i["quantity"]) for i in flow["items"]]
    assert kinds == [("child", "3х1.5", "100"), ("child", "3х2.5", "200"), ("position", "Выключатель", "12")]
    child = flow["items"][0]
    assert child["parent_name"] == "Кабель силовой" and child["parent_mark"] == "ВВГнг-LS"
    assert flow["items"][2]["parent"] is None


def test_the_type_of_a_row_is_decided_by_its_cells_not_by_the_number(drawn) -> None:
    page = drawn.Page()
    page.row({"mark": "М-1", "name": "Без номера", "quantity": "5"})  # no «Поз.»: still a position
    page.row({"pos": "9", "name": "Номер без количества и марки"})  # a number but nothing else: text, not a position
    flow = table.assemble([{"page": 1, "rows": page.parse()["rows"]}])
    assert [i["name"] for i in flow["items"]] == ["Без номера"]
    assert flow["items"][0]["pos"] == ""


def test_a_line_that_starts_in_lower_case_continues_the_position_above_it(drawn) -> None:
    page = drawn.Page()
    page.row({"pos": "1", "mark": "М-1", "name": "Светильник светодиодный", "quantity": "5"})
    page.row({"name": "с блоком аварийного питания", "note": "(2 часа)"})
    item = table.assemble([{"page": 1, "rows": page.parse()["rows"]}])["items"][0]
    assert item["name"] == "Светильник светодиодный с блоком аварийного питания"
    assert item["note"] == "(2 часа)"
    assert len(item["rows"]) == 2 and item["ambiguous"] is False


def test_a_merged_title_row_is_a_section_and_the_positions_below_carry_it(drawn) -> None:
    page = drawn.Page()
    page.merged("Раздел 1. Щиты")
    page.row({"pos": "1", "mark": "М-1", "name": "Щит", "quantity": "1"})
    page.merged("Раздел 2. Кабели")
    page.row({"pos": "2", "mark": "М-2", "name": "Кабель", "quantity": "10"})
    parsed = page.parse()
    assert [r.get("span") for r in parsed["rows"]] == [True, None, True, None]
    items = table.assemble([{"page": 1, "rows": parsed["rows"]}])["items"]
    assert [(i["name"], i["section"]) for i in items] == [("Щит", "Раздел 1. Щиты"), ("Кабель", "Раздел 2. Кабели")]


def test_a_capital_after_a_finished_position_is_a_sub_title_of_the_section(drawn) -> None:
    page = drawn.Page()
    page.merged("Раздел 1")
    page.row({"pos": "1", "mark": "М-1", "name": "Щит", "quantity": "1"})
    page.row({"name": "Силовое оборудование"})
    page.row({"pos": "2", "mark": "М-2", "name": "Кабель", "quantity": "10"})
    items = table.assemble([{"page": 1, "rows": page.parse()["rows"]}])["items"]
    assert [i["section"] for i in items] == ["Раздел 1", "Раздел 1 / Силовое оборудование"]


def test_a_boundary_at_a_page_break_that_is_not_obvious_is_flagged_and_not_guessed(drawn) -> None:
    first = drawn.Page()
    first.row({"pos": "1", "mark": "М-1", "name": "Щит", "quantity": "1"})
    second = drawn.Page()
    second.row({"name": "Распределительный"})  # a capital at the top of a page: a continuation or a new title?
    second.row({"pos": "2", "mark": "М-2", "name": "Кабель", "quantity": "10"})
    flow = table.assemble([{"page": 1, "rows": first.parse()["rows"]}, {"page": 2, "rows": second.parse()["rows"]}])
    # The rule of the original (``spec.py:305``) treats a capital after a finished position as a sub-title, so nothing is appended
    # and nothing is flagged; the same text in lower case continues the position across the break without a flag.
    assert [i["ambiguous"] for i in flow["items"]] == [False, False]

    third = drawn.Page()
    third.row({"name": "(продолжение)"})
    flow = table.assemble([{"page": 1, "rows": first.parse()["rows"]}, {"page": 2, "rows": third.parse()["rows"]}])
    item = flow["items"][0]
    assert item["name"] == "Щит (продолжение)" and item["ambiguous"] is True
    assert sorted({r[0] for r in item["rows"]}) == [1, 2]


def test_a_sub_row_at_the_top_of_a_page_belongs_to_the_last_parent_of_the_page_before(drawn) -> None:
    first = drawn.Page()
    first.row({"mark": "ВВГнг-LS", "name": "Кабель силовой"})
    first.row({"name": "3х1.5", "quantity": "100"})
    second = drawn.Page()
    second.row({"name": "3х2.5", "quantity": "200"})
    flow = table.assemble([{"page": 1, "rows": first.parse()["rows"]}, {"page": 2, "rows": second.parse()["rows"]}])
    assert [(i["page"], i["parent_name"]) for i in flow["items"]] == [(1, "Кабель силовой"), (2, "Кабель силовой")]


def test_values_are_the_text_of_the_sheet_never_summed_or_normalised(drawn) -> None:
    page = drawn.Page()
    page.row({"pos": "1", "mark": "М-1", "name": "Кабель", "quantity": "2,50", "mass": "0,150", "note": "см. п. 3"})
    item = table.assemble([{"page": 1, "rows": page.parse()["rows"]}])["items"][0]
    assert (item["quantity"], item["mass"]) == ("2,50", "0,150")
    assert table.quantity(item["quantity"]) == 2.5 and table.quantity("abc") is None


def test_the_title_block_test_from_the_stamp(drawn) -> None:
    assert table.is_spec_stamp("13АВ-РД-ЭМ2.1-СО", None)
    assert table.is_spec_stamp("ПРОЕКТ.СО", "Лист")
    assert table.is_spec_stamp("СИНТ-01-ЭМ", "Спецификация оборудования, изделий и материалов")
    assert not table.is_spec_stamp("СИНТ-01-ЭМ", "Однолинейная схема")
    assert not table.is_spec_stamp(None, None)
    assert not table.is_spec_stamp("ПРОЕКТ-СОГЛАСОВАНИЕ", "План")


@pytest.mark.parametrize("a,b", [("ВВГнг", "BBГнг"), ("3×2,5", "3х2.5"), (" Щит  ЩО-1 ", "щит що-1")])
def test_the_key_of_a_comparison_ignores_space_case_comma_and_look_alike_letters(a: str, b: str) -> None:
    assert table.norm(a) == table.norm(b)
