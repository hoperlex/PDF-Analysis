"""Text «было → стало» and the word comparison (ports of ``textdiff.py`` and ``engine._compare_words``)."""

from __future__ import annotations

import pytest

from auditmanager.comparison.engine.child import textdiff
from auditmanager.comparison.engine.child import words as w


def word(text: str, x: float, y: float, width: float | None = None, height: float = 8.0) -> dict:
    width = width if width is not None else 5.0 * len(text)
    return {"text": text, "pt": [x, y, x + width, y + height], "dir": None}


def test_numbers_changed_in_order_are_listed_in_pairs() -> None:
    assert textdiff.numbers("Рр=323.55кВт", "Рр=324.26кВт") == [{"before": "323.55", "after": "324.26"}]
    assert textdiff.numbers("3,0 и 5", "3.0 и 6") == [{"before": "5", "after": "6"}]


def test_numbers_that_differ_in_count_are_listed_without_pairs() -> None:
    assert textdiff.numbers("1 2 3", "1 3") == [{"before": "2", "after": ""}]
    assert textdiff.numbers("1", "1 4") == [{"before": "", "after": "4"}]


@pytest.mark.parametrize("before,after,norm", [
    ("кВт 5", "кВт5", "spaces"), ("ABC", "АВС", "symbol"), ("3,5", "3.5", "number_format"), ("кВт", "кВт", "spaces"),
    ("5", "6", None),
])
def test_a_normalisation_is_classified_not_hidden(before: str, after: str, norm: str | None) -> None:
    assert textdiff.classify(before, after) == norm


def test_changed_words_at_one_place_are_one_change_with_their_numbers() -> None:
    changes = textdiff.build([word("323.55кВт", 10, 10)], [word("324.26кВт", 10, 10)], [])
    assert len(changes) == 1
    c = changes[0]
    assert (c["kind"], c["before"], c["after"]) == ("changed", "323.55кВт", "324.26кВт")
    assert c["numbers"] == [{"before": "323.55", "after": "324.26"}] and c["norm"] is None


def test_a_word_only_in_one_version_is_added_or_removed() -> None:
    changes = textdiff.build([word("старое", 10, 10)], [word("новое", 200, 100)], [])
    assert sorted(c["kind"] for c in changes) == ["added", "removed"]


def test_a_change_of_spaces_alone_is_not_significant() -> None:
    changes = textdiff.build([word("кВт 5", 10, 10)], [word("кВт5", 10, 10)], [])
    assert changes[0]["norm"] == "spaces" and textdiff.significant(changes) == 0


def test_a_moved_inscription_is_not_a_difference_of_the_text_channel() -> None:
    moved = [{"text": "ЩО-1", "a_pt": [10, 10, 30, 18], "b_in_a_pt": [40, 10, 60, 18], "shift_pt": 30.0, "dir": None}]
    changes = textdiff.build([], [], moved)
    assert [c["kind"] for c in changes] == ["moved"] and textdiff.significant(changes) == 0


def test_changes_get_identities_in_reading_order() -> None:
    changes = textdiff.build([word("б", 10, 100)], [word("а", 10, 10)], [])
    assert [c["id"] for c in changes] == ["t1", "t2"]
    assert changes[0]["after"] == "а"


# -- compare_words ------------------------------------------------------------------------------------------------

def test_a_word_within_the_tolerance_is_the_same() -> None:
    result = w.compare_words([word("QF1", 10, 10)], [word("QF1", 10.2, 10.1)], 0.5)
    assert result["same"] == 1 and not result["only_a"] and not result["only_b"] and not result["moved"]


def test_a_word_beyond_the_tolerance_and_within_twenty_points_is_a_moved_inscription() -> None:
    result = w.compare_words([word("QF1", 10, 10)], [word("QF1", 25, 10)], 0.5)
    assert len(result["moved"]) == 1 and result["moved"][0]["shift_pt"] == pytest.approx(15.0, abs=0.01)


def test_a_word_more_than_twenty_points_away_is_removed_and_added() -> None:
    """``WORD_MOVE_PT`` is 20 (``settings.py:90``): a label moved by 120 pt is a removal and an addition."""
    result = w.compare_words([word("ЩО-1", 10, 10)], [word("ЩО-1", 130, 40)], 0.5)
    assert len(result["only_a"]) == 1 and len(result["only_b"]) == 1 and not result["moved"]


def test_the_nearest_pairs_are_taken_first() -> None:
    a = [word("X", 0, 0), word("X", 100, 0)]
    b = [word("X", 101, 0), word("X", 1, 0)]
    result = w.compare_words(a, b, 0.5)
    assert len(result["moved"]) == 2 and sorted(m["shift_pt"] for m in result["moved"]) == [1.0, 1.0]


# -- warnings, release marks, the frame, the kind of a sheet ------------------------------------------------------

def test_a_short_row_that_says_not_agreed_is_a_warning() -> None:
    found = w.warning_lines([word("НЕ", 10, 10, 12), word("СОГЛАСОВАНО", 30, 10, 60), word("текст", 10, 200)])
    assert [f["text"] for f in found] == ["НЕ СОГЛАСОВАНО"]


def test_the_word_copy_in_a_long_ordinary_row_is_not_a_warning() -> None:
    row = [word(t, 10 + 30 * i, 10) for i, t in enumerate(["Сети", "освещения", "копия", "1", "этаж", "план"])]
    assert w.warning_lines(row) == []


def test_a_release_mark_is_found_with_its_date_and_the_blocks_next_to_it() -> None:
    page = [word("В", 100, 100, 6), word("производство", 110, 100, 70), word("работ", 185, 100, 30),
            word("Иванов", 100, 112, 40), word("12.03.2026", 150, 112, 50), word("прочее", 100, 400)]
    marks = w.release_blocks(page)
    assert len(marks) == 1 and marks[0]["date"] == "12.03.2026"
    assert marks[0]["bbox"][1] <= 100 and marks[0]["bbox"][3] >= 120


def test_a_frame_is_found_from_long_lines_near_the_edges_and_not_from_short_ones() -> None:
    mm = w.MM
    segments = [(20 * mm, 5 * mm, 20 * mm, 800), (590, 5 * mm, 590, 800), (20 * mm, 5 * mm, 590, 5 * mm), (20 * mm, 836, 590, 836)]
    frame = w.detect_frame(595.0, 842.0, segments)
    assert frame is not None and frame[0] == pytest.approx(20 * mm, abs=0.1)
    assert w.detect_frame(595.0, 842.0, [(100, 100, 100, 150)]) is None


def test_a_specification_sheet_is_recognised_by_its_head_or_its_designation() -> None:
    head = [word("Поз.", 20, 20), word("Наименование", 60, 20), word("Кол.", 200, 20)]
    assert w.classify_kind(head, None, 842.0) == "spec"
    assert w.classify_kind([word("План", 20, 20)], "СИНТ-01-ЭМ.СО", 842.0) == "spec"
    assert w.classify_kind([word("План", 20, 20)], "СИНТ-01-ЭМ", 842.0) == "other"
