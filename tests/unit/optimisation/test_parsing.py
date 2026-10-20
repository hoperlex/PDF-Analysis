"""`W60-PRICE-LIST-01` phase A: the price-list parser, container-free.

CSV in UTF-8 with and without a byte-order mark, UTF-16 and Windows-1251; ``;``, tab and ``,``
delimiters; the decimal comma; XLSX shared strings, inline strings, rich and phonetic runs,
stored numbers and the first sheet by workbook order; the header rules; malformed rows
**reported, never guessed**; every whole-file refusal; determinism.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from auditmanager.optimisation.parsing import (
    SKIP_REASONS,
    ParseOutcome,
    parse_price_list,
)
from auditmanager.optimisation.parsing import xlsx_source
from auditmanager.optimisation.parsing.limits import MAX_BYTES, MAX_DATA_ROWS, MAX_LISTED_ROWS
from auditmanager.optimisation.parsing.values import read_price
from auditmanager.sections.public import section_names
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.optimisation.xlsx_builder import (  # type: ignore[import-not-found]
    Inline,
    Num,
    Raw,
    Rich,
    build_xlsx,
    simple_xlsx,
)

NAMES = section_names()
HEADER = "Код;Наименование;Ед. изм.;Цена, руб.;Поставщик;Раздел"


def _parse(data: bytes, *, currency: str | None = None) -> ParseOutcome:
    return parse_price_list(data, default_currency=currency, section_names=NAMES)


def _refused(data: bytes, constraint: str, *, currency: str | None = None) -> DomainError:
    with pytest.raises(DomainError) as caught:
        _parse(data, currency=currency)
    error = caught.value
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert dict(error.detail_fields) == {
        "field": "content",
        "constraint": constraint,
        "aggregate_type": "PriceList",
    }
    return error


def _csv(*lines: str, encoding: str = "utf-8") -> bytes:
    return ("\n".join(lines) + "\n").encode(encoding)


def _rows(outcome: ParseOutcome) -> list[tuple[Any, ...]]:
    return [
        (p.row_number, p.code, p.name, p.unit, p.unit_price, p.currency, p.vendor, p.section_code)
        for p in outcome.positions
    ]


# -- CSV: encodings and delimiters ------------------------------------------------------------


def test_utf8_with_bom_semicolons_and_a_decimal_comma() -> None:
    data = b"\xef\xbb\xbf" + _csv(HEADER, "К-1;Кабель ВВГнг-LS 3х2,5;м;125,50;Кабельный завод;ЭОМ")
    outcome = _parse(data)
    assert _rows(outcome) == [
        (2, "К-1", "Кабель ВВГнг-LS 3х2,5", "м", Decimal("125.5"), "RUB", "Кабельный завод", "EOM")
    ]
    assert outcome.source_format == "csv" and outcome.media_type == "text/csv"
    assert outcome.report["encoding"] == "utf-8-sig"
    assert outcome.report["delimiter"] == ";"
    assert outcome.report["currency_sources"] == {"price_header": 1}


def test_utf8_without_bom_comma_delimited_with_a_quoted_decimal_comma() -> None:
    data = _csv(
        "Name,Unit,Unit price,Currency",
        'Cable,m,"125,50",RUB',
        "Pipe,m,99.9,usd",
    )
    outcome = _parse(data)
    assert [(p.name, p.unit_price, p.currency) for p in outcome.positions] == [
        ("Cable", Decimal("125.5"), "RUB"),
        ("Pipe", Decimal("99.9"), "USD"),
    ]
    assert outcome.report["encoding"] == "utf-8" and outcome.report["delimiter"] == ","
    assert outcome.report["currency_sources"] == {"column": 2}


def test_windows_1251_is_detected_and_cyrillic_survives() -> None:
    data = _csv(HEADER, "1;Щит распределительный;шт;12 345,67;ООО «Щит»;ЭОМ", encoding="cp1251")
    with pytest.raises(UnicodeDecodeError):
        data.decode("utf-8")
    outcome = _parse(data)
    assert outcome.report["encoding"] == "cp1251"
    assert _rows(outcome)[0][2:6] == ("Щит распределительный", "шт", Decimal("12345.67"), "RUB")
    assert outcome.positions[0].vendor == "ООО «Щит»"


def test_utf16_tab_separated_text_is_read() -> None:
    data = ("Наименование\tЕд. изм.\tЦена\tВалюта\nЛампа\tшт\t150\tRUB\n").encode("utf-16")
    outcome = _parse(data)
    assert outcome.report["encoding"] == "utf-16" and outcome.report["delimiter"] == "\t"
    assert _rows(outcome)[0][2:6] == ("Лампа", "шт", Decimal("150"), "RUB")


def test_bytes_that_are_neither_utf8_nor_windows_1251_are_refused() -> None:
    _refused(b"\x98\x98\x98;\x98\n", "price_list_encoding")


def test_a_nul_byte_is_binary_content_and_refused() -> None:
    _refused(_csv(HEADER) + b"\x00\x01", "price_list_unreadable")


# -- the header -------------------------------------------------------------------------------


def test_the_header_is_found_below_a_preamble_and_blank_rows_are_ignored() -> None:
    data = _csv(
        "Прайс-лист ООО «Ромашка»",
        "",
        "Действует с 01.10.2026",
        HEADER,
        "1;Кабель;м;10;;",
        ";;;;;",
        "2;Труба;м;20;;",
    )
    outcome = _parse(data)
    assert outcome.report["header_row"] == 4
    assert outcome.report["preamble_rows"] == 2
    assert outcome.report["blank_rows"] == 1
    assert [p.row_number for p in outcome.positions] == [5, 7]


def test_no_header_in_the_first_twenty_non_blank_rows_is_refused() -> None:
    _refused(_csv(*[f"строка {n}" for n in range(20)], HEADER, "1;Кабель;м;10;;"), "price_list_header")
    assert _parse(_csv(*[f"строка {n}" for n in range(19)], HEADER, "1;Кабель;м;10;;")).positions


def test_a_total_is_never_read_as_a_unit_price() -> None:
    _refused(_csv("Наименование;Ед. изм.;Стоимость", "Кабель;м;100"), "price_list_header")
    _refused(_csv("Наименование;Ед. изм.;Сумма", "Кабель;м;100"), "price_list_header")


def test_two_candidate_price_columns_refuse_the_file() -> None:
    error = _refused(
        _csv("Наименование;Ед. изм.;Цена без НДС;Цена с НДС", "Кабель;м;100;120"),
        "price_list_header_ambiguous",
    )
    assert "unit_price" in str(error)


def test_a_weaker_name_column_yields_and_an_ambiguous_optional_column_is_not_read() -> None:
    data = _csv(
        "Код;Код ОКПД2;Наименование;Описание;Ед. изм.;Цена, руб.",
        "К-1;27.32;Кабель;Медный;м;10",
    )
    outcome = _parse(data)
    assert outcome.positions[0].name == "Кабель" and outcome.positions[0].code is None
    assert outcome.report["ambiguous_columns"] == {"code": ["Код", "Код ОКПД2"]}
    assert "Описание" in outcome.report["ignored_columns"]
    assert set(outcome.report["columns"]) == {"name", "unit", "unit_price"}


def test_vendor_and_code_headers_win_over_name_and_vendor() -> None:
    data = _csv(
        "Наименование;Наименование производителя;Код поставщика;Ед.изм.;Price",
        "Кабель;Завод;A-1;м;10",
    )
    outcome = _parse(data, currency="RUB")
    position = outcome.positions[0]
    assert (position.name, position.vendor, position.code) == ("Кабель", "Завод", "A-1")
    assert outcome.report["currency_sources"] == {"default": 1}


def test_english_headers_and_the_mark_column() -> None:
    data = _csv("Item name;Model;UoM;Unit price;Manufacturer", "Lamp;LED-12;pcs;7.5;Acme")
    position = _parse(data, currency="EUR").positions[0]
    assert (position.name, position.mark, position.unit, position.vendor) == ("Lamp", "LED-12", "pcs", "Acme")
    assert (position.unit_price, position.currency) == (Decimal("7.5"), "EUR")


# -- values: prices are read, never guessed ---------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("125,50", "125.5"),
        ("125.50", "125.5"),
        ("12 345,67", "12345.67"),
        ("12 345,67", "12345.67"),
        ("1 234 567", "1234567"),
        ("1.234,56", "1234.56"),
        ("1,234.56", "1234.56"),
        ("1.234.567", "1234567"),
        ("1,234,567", "1234567"),
        ("1,234", "1.234"),
        ("1.234", "1.234"),
        ("+7", "7"),
        ("0,000001", "0.000001"),
        ("99999999999999,999999", "99999999999999.999999"),
    ],
)
def test_plain_numbers_are_prices(text: str, expected: str) -> None:
    reading = read_price(text)
    assert reading.reason is None and reading.value == Decimal(expected)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", "price_missing"),
        ("   ", "price_missing"),
        ("по запросу", "price_not_a_number"),
        ("договорная", "price_not_a_number"),
        ("500 руб.", "price_not_a_number"),
        ("от 100", "price_not_a_number"),
        ("100-200", "price_not_a_number"),
        ("12 34", "price_not_a_number"),
        ("1e3", "price_not_a_number"),
        ("1,2,3", "price_not_a_number"),
        (",5", "price_not_a_number"),
        ("5.", "price_not_a_number"),
        ("≈100", "price_not_a_number"),
        ("0", "price_not_positive"),
        ("0,00", "price_not_positive"),
        ("-5", "price_not_positive"),
        ("0,0000001", "price_precision"),
        ("100000000000000", "price_too_large"),
    ],
)
def test_anything_else_is_not_a_price_and_says_why(text: str, reason: str) -> None:
    reading = read_price(text)
    assert reading.value is None and reading.reason == reason


def test_malformed_rows_are_skipped_with_reasons_and_never_repaired() -> None:
    data = _csv(
        "Наименование;Ед. изм.;Цена;Валюта;Раздел",
        "Кабель;м;125,5;RUB;АР",
        ";м;10;RUB;",
        "Труба;;10;RUB;",
        "Щит;шт;по запросу;RUB;",
        "Лампа;шт;0;RUB;",
        "Кнопка;шт;10;грн;",
        "Реле;шт;10;;",
        "Датчик;шт;" + "1" * 15 + ";RUB;",
        "Провод;м;1,5;RUB;Неизвестный раздел",
        "Я" * 2001 + ";шт;1;RUB;",
    )
    outcome = _parse(data)
    assert [(p.row_number, p.name, p.section_code) for p in outcome.positions] == [
        (2, "Кабель", "AR"),
        (10, "Провод", None),
    ]
    assert outcome.report["skipped"] == [
        {"row": 3, "reason": "name_missing"},
        {"row": 4, "reason": "unit_missing"},
        {"row": 5, "reason": "price_not_a_number"},
        {"row": 6, "reason": "price_not_positive"},
        {"row": 7, "reason": "currency_unrecognised"},
        {"row": 8, "reason": "currency_missing"},
        {"row": 9, "reason": "price_too_large"},
        {"row": 11, "reason": "value_too_long"},
    ]
    assert outcome.report["warnings"] == [{"row": 10, "reason": "section_unrecognised"}]
    assert (outcome.data_row_count, outcome.accepted_row_count, outcome.skipped_row_count) == (10, 2, 8)
    assert list(outcome.report["skipped_by_reason"]) == [
        reason for reason in SKIP_REASONS if reason in outcome.report["skipped_by_reason"]
    ]


def test_currency_comes_from_the_cell_then_the_price_header_then_the_default() -> None:
    with_header = _csv("Наименование;Ед. изм.;Цена, $;Валюта", "A;шт;1;EUR", "B;шт;2;")
    outcome = _parse(with_header, currency="RUB")
    assert [p.currency for p in outcome.positions] == ["EUR", "USD"]
    assert outcome.report["price_header_currency"] == "USD"
    assert outcome.report["currency_sources"] == {"column": 1, "price_header": 1}

    plain = _csv("Наименование;Ед. изм.;Цена", "A;шт;1")
    assert _parse(plain, currency="KZT").positions[0].currency == "KZT"
    _refused(plain, "price_list_no_positions")


@pytest.mark.parametrize(
    ("cell", "code"),
    [
        ("АР", "AR"),
        ("эом", "EOM"),
        ("EOM", "EOM"),
        ("ov", "OV"),
        ("ОВиК", "OV"),
        ("ПЗ", "PS"),
        ("Пожарная безопасность", "PB"),
        ("электроснабжение и электрооборудование", "EOM"),
    ],
)
def test_sections_are_read_by_code_abbreviation_or_catalogue_name(cell: str, code: str) -> None:
    data = _csv("Наименование;Ед. изм.;Цена;Раздел", f"A;шт;1;{cell}")
    outcome = _parse(data, currency="RUB")
    assert outcome.positions[0].section_code == code
    assert outcome.report["warnings"] == []


# -- whole-file refusals and bounds -----------------------------------------------------------


def test_an_empty_file_and_an_oversized_file_are_refused() -> None:
    _refused(b"", "non_empty")
    _refused(b"x" * (MAX_BYTES + 1), f"byte_size <= {MAX_BYTES}")


def test_an_excel_97_workbook_is_refused_with_its_own_reason() -> None:
    error = _refused(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 512, "price_list_format")
    assert "XLSX or CSV" in str(error)


def test_more_than_twenty_thousand_data_rows_are_refused_and_exactly_that_many_pass() -> None:
    body = [f"Позиция {n};шт;{n + 1}" for n in range(MAX_DATA_ROWS)]
    outcome = _parse(_csv("Наименование;Ед. изм.;Цена, руб.", *body))
    assert outcome.accepted_row_count == MAX_DATA_ROWS
    _refused(_csv("Наименование;Ед. изм.;Цена, руб.", *body, "Лишняя;шт;1"), f"data_rows <= {MAX_DATA_ROWS}")


def test_only_the_first_thousand_skipped_rows_are_listed_but_every_one_is_counted() -> None:
    body = [f"Позиция {n};шт;по запросу" for n in range(MAX_LISTED_ROWS + 5)]
    outcome = _parse(_csv("Наименование;Ед. изм.;Цена, руб.", *body, "Кабель;м;1"))
    assert len(outcome.report["skipped"]) == MAX_LISTED_ROWS
    assert outcome.report["skipped_by_reason"] == {"price_not_a_number": MAX_LISTED_ROWS + 5}
    assert outcome.report["skipped_listed_in_full"] is False


def test_a_file_with_no_acceptable_row_is_refused_with_the_counts() -> None:
    error = _refused(
        _csv("Наименование;Ед. изм.;Цена, руб.", "Кабель;м;по запросу", "Труба;;5"),
        "price_list_no_positions",
    )
    assert "2 data row(s)" in str(error)
    assert "unit_missing 1" in str(error) and "price_not_a_number 1" in str(error)
    _refused(_csv("Наименование;Ед. изм.;Цена, руб."), "price_list_no_positions")


# -- XLSX -------------------------------------------------------------------------------------


def test_xlsx_shared_inline_rich_strings_and_stored_numbers() -> None:
    data = build_xlsx(
        [
            (
                "Прайс",
                [
                    (1, ["Прайс-лист"]),
                    (3, ["Код", "Наименование", "Ед. изм.", Inline("Цена, руб."), "Раздел"]),
                    (4, [Num("101"), Rich(("Кабель ", "ВВГнг"), phonetic="カ"), "м", Num("12.300000000000001"), "ЭОМ"]),
                    (5, [None, Inline("Щит_x000D_ЩР-1"), "шт", Num("1.5E+3"), None]),
                    (6, ["К-3", "Лампа", "шт", Raw('<c r="{ref}" t="str"><f>1+1</f><v>2,5</v></c>'), None]),
                    (8, ["К-4", "Реле", "шт", Raw('<c r="{ref}" t="e"><v>#N/A</v></c>'), None]),
                ],
            )
        ]
    )
    outcome = _parse(data)
    assert outcome.source_format == "xlsx"
    assert outcome.report["sheet"] == "Прайс" and outcome.report["header_row"] == 3
    assert _rows(outcome) == [
        (4, "101", "Кабель ВВГнг", "м", Decimal("12.3"), "RUB", None, "EOM"),
        (5, None, "Щит ЩР-1", "шт", Decimal("1500"), "RUB", None, None),
        (6, "К-3", "Лампа", "шт", Decimal("2.5"), "RUB", None, None),
    ]
    assert outcome.report["skipped"] == [{"row": 8, "reason": "price_not_a_number"}]


def test_xlsx_reads_the_first_sheet_in_workbook_order_not_by_part_name() -> None:
    first = [(1, ["Наименование", "Ед. изм.", "Цена", "Валюта"]), (2, ["Первый", "шт", Num("1"), "RUB"])]
    second = [(1, ["Наименование", "Ед. изм.", "Цена", "Валюта"]), (2, ["Второй", "шт", Num("2"), "RUB"])]
    outcome = _parse(build_xlsx([("Главный", first), ("Архив", second)]))
    assert [p.name for p in outcome.positions] == ["Первый"]
    assert outcome.report["sheet"] == "Главный"


def test_xlsx_numeric_codes_and_sparse_cells() -> None:
    data = simple_xlsx(
        [
            ["Наименование", None, "Ед. изм.", None, "Цена", "Код"],
            ["Кабель", None, "м", None, Num("10"), Num("123456789012")],
        ]
    )
    position = _parse(data, currency="RUB").positions[0]
    assert (position.name, position.unit, position.code) == ("Кабель", "м", "123456789012")


def test_an_xlsx_declaring_a_document_type_is_refused_before_it_is_parsed() -> None:
    data = build_xlsx(
        [("Прайс", [(1, ["Наименование", "Ед. изм.", "Цена"]), (2, ["A", "шт", Num("1")])])],
        sheet_prolog='<!DOCTYPE lol [<!ENTITY lol "lol">]>',
    )
    _refused(data, "price_list_unreadable", currency="RUB")


def test_a_zip_that_is_not_a_workbook_and_a_broken_zip_are_refused() -> None:
    no_rels = build_xlsx([("Прайс", [(1, ["Наименование"])])], with_package_rels=False)
    _refused(no_rels, "price_list_unreadable")
    _refused(b"PK\x03\x04" + b"\x00" * 64, "price_list_unreadable")


def test_a_decompressed_part_over_the_bound_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    data = simple_xlsx(
        [["Наименование", "Ед. изм.", "Цена"]] + [[f"Позиция {n}", "шт", Num("1")] for n in range(500)]
    )
    assert _parse(data, currency="RUB").accepted_row_count == 500
    monkeypatch.setattr(xlsx_source, "MAX_XLSX_PART_BYTES", 4096)
    _refused(data, "xlsx_part_size <= 67108864", currency="RUB")


# -- determinism ------------------------------------------------------------------------------


def test_the_same_bytes_parse_to_the_same_positions_and_report() -> None:
    data = _csv(HEADER, "1;Кабель;м;10;;АР", "2;Труба;м;по запросу;;", "3;Щит;шт;1 000;;ЖЖ")
    first, second = _parse(data), _parse(data)
    assert first.positions == second.positions
    assert json.dumps(first.report, sort_keys=True, ensure_ascii=False) == json.dumps(
        second.report, sort_keys=True, ensure_ascii=False
    )
    assert first.report["report_version"] == 1
