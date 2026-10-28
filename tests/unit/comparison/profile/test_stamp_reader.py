"""The stamp reader (`CMP-PROFILE-01`): the title block's designation, sheet number, title, «Изм.» and date.

Two kinds of test. Synthetic words pin the rule's edges (the zone, the labels, the shape of each field, the
refusal to guess). The answer key of VS-1 pins the rule to the corpus: every page of every version, read from
the PDF by pdfplumber, must give the key's fields; the scan pages give nothing.
"""

from __future__ import annotations

import pdfplumber
import pytest

from auditmanager.comparison.profile.stamp import read_stamp, stamp_zone

W, H = 1190.55, 841.89


def _words(*items: tuple[float, float, str]) -> list[list]:
    """``(x0, top, text)`` to ``[x0, top, x1, bottom, text]`` with a nominal size."""
    return [[x, t, x + 6 * len(text), t + 6, text] for x, t, text in items]


def test_a_stamp_is_read_label_above_value() -> None:
    zone_x, zone_top, *_ = stamp_zone(W, H)
    words = _words(
        (zone_x + 40, zone_top + 10, "Обозначение"),
        (zone_x + 48, zone_top + 24, "АБВ-01-ЭМ"),
        (zone_x + 40, zone_top + 50, "Наименование"),
        (zone_x + 130, zone_top + 50, "листа"),
        (zone_x + 48, zone_top + 64, "План"),
        (zone_x + 80, zone_top + 64, "этажа"),
        (zone_x + 400, zone_top + 50, "Лист"),
        (zone_x + 408, zone_top + 64, "17"),
        (zone_x + 300, zone_top + 80, "Изм."),
        (zone_x + 308, zone_top + 94, "Изм.3"),
        (zone_x + 400, zone_top + 80, "Дата"),
        (zone_x + 408, zone_top + 94, "01.02.2026"),
    )
    got = read_stamp(words, W, H)
    assert (got.designation, got.sheet_number, got.sheet_title) == ("АБВ-01-ЭМ", "17", "План этажа")
    assert (got.revision_number, got.release_date) == ("3", "2026-02-01")
    assert got.labels == ("designation", "title", "sheet", "revision", "date")


def test_words_outside_the_zone_are_not_the_stamp() -> None:
    words = _words((20, 20, "Обозначение"), (28, 34, "АБВ"), (20, 60, "Лист"), (28, 74, "9"))
    got = read_stamp(words, W, H)
    assert not got.found and got.labels == ()


def test_nothing_is_guessed_without_a_label_or_with_the_wrong_shape() -> None:
    zone_x, zone_top, *_ = stamp_zone(W, H)
    # A number and a title with no labels: absent.
    assert not read_stamp(_words((zone_x + 50, zone_top + 30, "12"), (zone_x + 50, zone_top + 50, "План")), W, H).found
    # «Лист» over a word that is not a number: the sheet number is absent, not the word.
    words = _words((zone_x + 40, zone_top + 10, "Лист"), (zone_x + 48, zone_top + 24, "три"))
    assert read_stamp(words, W, H).sheet_number is None
    # A date that does not exist, and a revision with no digit.
    words = _words(
        (zone_x + 40, zone_top + 10, "Дата"), (zone_x + 48, zone_top + 24, "31.02.2026"),
        (zone_x + 200, zone_top + 10, "Изм."), (zone_x + 208, zone_top + 24, "—"),
    )
    got = read_stamp(words, W, H)
    assert got.release_date is None and got.revision_number is None


def test_a_sheet_number_may_be_a_part_number() -> None:
    zone_x, zone_top, *_ = stamp_zone(W, H)
    for shown in ("5.1", "5-2", "12", "П3"):
        words = _words((zone_x + 40, zone_top + 10, "Лист"), (zone_x + 48, zone_top + 24, shown))
        assert read_stamp(words, W, H).sheet_number == shown


def test_the_value_stops_at_the_next_label_below_and_at_a_gap() -> None:
    zone_x, zone_top, *_ = stamp_zone(W, H)
    words = _words(
        (zone_x + 40, zone_top + 10, "Наименование"),
        (zone_x + 48, zone_top + 24, "Первая"),
        (zone_x + 48, zone_top + 32, "строка"),
        (zone_x + 48, zone_top + 80, "Далеко"),  # a gap of 40 pt: another cell
    )
    assert read_stamp(words, W, H).sheet_title == "Первая строка"


def test_a_small_page_clips_the_zone_to_the_page() -> None:
    x0, top, x1, bottom = stamp_zone(595.28, 841.89)
    assert x0 == pytest.approx(595.28 - 581.1, abs=0.1) and (x1, bottom) == (595.28, 841.89)
    assert top == pytest.approx(841.89 - 198.4, abs=0.1)
    assert stamp_zone(300, 100)[:2] == (0.0, 0.0)


def test_every_vs1_page_reads_as_the_answer_key_says(vs1_key: dict, fixtures_dir) -> None:
    mismatches = []
    for version in vs1_key["versions"]:
        pdf = pdfplumber.open(fixtures_dir / version["file"])
        for index, page_key in enumerate(version["pages"]):
            page = pdf.pages[index]
            words = [[w["x0"], w["top"], w["x1"], w["bottom"], w["text"]] for w in page.extract_words()]
            got = read_stamp(words, float(page.width), float(page.height))
            if not page_key["text_layer"]:
                if got.found:
                    mismatches.append((version["id"], index + 1, "a scan has no text to read", got))
                continue
            stamp = page_key["stamp"]
            day, month, year = stamp["date"].split(".")
            expected = (
                stamp["designation"], page_key["sheet_no"], page_key["title"],
                stamp["revision"].removeprefix("Изм."), f"{year}-{month}-{day}",
            )
            actual = (got.designation, got.sheet_number, got.sheet_title, got.revision_number, got.release_date)
            if expected != actual:
                mismatches.append((version["id"], index + 1, expected, actual))
    assert mismatches == []
