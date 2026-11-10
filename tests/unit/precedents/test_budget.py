"""`plan-v5` 3.5: the selection rule of the executor context: window order, 3 cases per candidate, 12 000 characters, then «не уместилось: N»."""

from __future__ import annotations

import pytest

from auditmanager.precedents.budget import BudgetCase, BudgetEntry, not_fitted_line, select_within_budget


def _entry(input_id: str, *sizes: int) -> BudgetEntry:
    return BudgetEntry(input_id, tuple(BudgetCase(f"{input_id}-{index}", "x" * size) for index, size in enumerate(sizes)))


def _shape(selection):
    return [(entry.input_id, [case.case_id for case in entry.cases]) for entry in selection.entries]


def test_everything_that_fits_is_selected_in_window_order_with_no_line():
    selection = select_within_budget([_entry("a", 100, 200), _entry("b", 300)])
    assert _shape(selection) == [("a", ["a-0", "a-1"]), ("b", ["b-0"])]
    assert (selection.characters_used, selection.not_fitted, selection.over_cap, selection.line) == (600, 0, 0, None)


def test_at_most_three_cases_per_candidate_and_the_rest_are_not_counted_in_the_line():
    selection = select_within_budget([_entry("a", 10, 10, 10, 10, 10)])
    assert _shape(selection) == [("a", ["a-0", "a-1", "a-2"])]
    assert (selection.over_cap, selection.not_fitted, selection.line) == (2, 0, None)


def test_over_12000_characters_the_line_says_how_many_did_not_fit():
    entries = [_entry(f"c{index}", 1000, 1000, 1000) for index in range(5)]  # 15 000 characters of cases
    selection = select_within_budget(entries)
    assert _shape(selection) == [
        ("c0", ["c0-0", "c0-1", "c0-2"]),
        ("c1", ["c1-0", "c1-1", "c1-2"]),
        ("c2", ["c2-0", "c2-1", "c2-2"]),
        ("c3", ["c3-0", "c3-1"]),
        ("c4", []),
    ]
    assert selection.not_fitted == 4 and selection.line == "не уместилось: 4" == not_fitted_line(4)
    assert selection.characters_used == 11_000 and selection.characters_total <= 12_000


def test_the_line_is_paid_for_out_of_the_budget():
    selection = select_within_budget([_entry("a", 50, 50, 10)], max_characters=100)
    assert _shape(selection) == [("a", ["a-0"])]
    assert (selection.not_fitted, selection.line) == (2, "не уместилось: 2")
    assert selection.characters_total == 50 + len("не уместилось: 2") <= 100


def test_a_selection_that_fills_the_budget_exactly_needs_no_line():
    selection = select_within_budget([_entry("a", 50, 50)], max_characters=100)
    assert selection.not_fitted == 0 and selection.line is None and selection.characters_total == 100


def test_the_first_case_that_does_not_fit_ends_the_selection_a_smaller_later_one_does_not_jump_ahead():
    selection = select_within_budget([_entry("a", 11_000, 2_000), _entry("b", 100)])
    assert _shape(selection) == [("a", ["a-0"]), ("b", [])]
    assert selection.not_fitted == 2 and selection.line == "не уместилось: 2"


def test_a_candidate_with_no_cases_stays_in_the_list():
    assert _shape(select_within_budget([_entry("a"), _entry("b", 5)])) == [("a", []), ("b", ["b-0"])]


def test_the_budget_counts_characters_not_bytes():
    selection = select_within_budget([_entry("a", 10)], max_characters=10)
    assert selection.not_fitted == 0
    cyrillic = BudgetEntry("a", (BudgetCase("c", "я" * 10),))
    assert select_within_budget([cyrillic], max_characters=10).not_fitted == 0


@pytest.mark.parametrize("kwargs", [{"max_cases_per_entry": 0}, {"max_characters": -1}])
def test_impossible_limits_are_refused(kwargs):
    with pytest.raises(ValueError):
        select_within_budget([_entry("a", 1)], **kwargs)
