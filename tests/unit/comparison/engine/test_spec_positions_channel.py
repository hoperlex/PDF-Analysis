"""The channel ``spec_positions`` of a specification pair (`CMP-VC-SPEC-01`).

The oracle is the answer key of the synthetic corpus: V4 to V5, sheet E07, has position 7 added, position 6 removed and the
quantity of position 3 changed from 2 to 3 (three position differences). The real page children and the real engine child run on
the corpus; the unit tests of the rule drive :func:`~auditmanager.comparison.engine.child.job.spec_positions_channel` on the page
inputs the worker writes for the child (:func:`~auditmanager.comparison.engine.inputs.page_inputs`).

The rule: ``checked`` with the count when the pages of the pair yield positions on **both** sides, ``checked(0)`` when the graphics,
the colour and the text have no difference (the original's rule, ``engine.py:997``), and otherwise ``unchecked`` with the reason --
a page the parser could not read is never a page with no change.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from auditmanager.comparison.engine import inputs as inputs_module
from auditmanager.comparison.engine.child import job
from auditmanager.comparison.engine.limits import ALGO_VERSION

KEY_PAIR = ("vs1/v4.pdf", 6, "vs1/v5.pdf", 7)


def _page(corpus_page, rel: str, number: int, tmp_path: Path, name: str) -> dict:
    page = corpus_page(rel, number)
    return inputs_module.page_inputs(page.data, pdf_path=str(page.path), page_index=number - 1, work_dir=str(tmp_path), name=name)


@pytest.fixture
def pair(corpus_page, tmp_path):
    return _page(corpus_page, "vs1/v4.pdf", 6, tmp_path, "a"), _page(corpus_page, "vs1/v5.pdf", 7, tmp_path, "b")


def test_the_algorithm_version_names_the_channel_that_was_built() -> None:
    assert ALGO_VERSION == "cmp-engine/4"


def test_the_key_pair_reports_the_three_position_differences_of_the_answer_key(compare, vs1_key) -> None:
    sheet = next(
        s for t in vs1_key["transitions"] if (t.get("transition") or t.get("id")) == "V4->V5" for s in t["sheets"]
        if s["sheet_id"] == "E07"
    )
    expected = len(sheet["spec_positions"]["added"]) + len(sheet["spec_positions"]["removed"]) + len(sheet["spec_positions"]["changed"])
    outcome = compare(*KEY_PAIR).outcome
    assert expected == 3
    assert outcome["channels"]["spec_positions"] == {"state": "checked", "diffs": expected}
    assert "UNCHECKED_CHANNEL_SPEC_POSITIONS" not in outcome["reasons"]
    assert outcome["status"] == sheet["expected_status"]


def test_an_unchanged_specification_sheet_is_checked_with_no_difference(compare) -> None:
    outcome = compare("vs1/v3.pdf", 6, "vs1/v4.pdf", 6).outcome
    assert outcome["channels"]["spec_positions"] == {"state": "checked", "diffs": 0}


def test_a_sheet_that_is_not_a_specification_has_nothing_to_look_at(compare) -> None:
    outcome = compare("vs1/v1.pdf", 2, "vs1/v2.pdf", 2).outcome
    assert outcome["channels"]["spec_positions"]["state"] == "not_applicable"


def test_positions_are_counted_when_both_pages_yield_them(pair) -> None:
    a, b = pair
    assert job.spec_positions_channel(a, b, 5) == {"state": "checked", "diffs": 3}


def test_the_count_does_not_depend_on_the_order_of_the_words_in_the_profile(pair) -> None:
    """The order of the words in the profile is not the order of the sheet: reversed, they give the same count."""
    a, b = pair
    b = copy.deepcopy(b)
    b["words"] = list(reversed(b["words"]))
    assert job.spec_positions_channel(a, b, 5) == {"state": "checked", "diffs": 3}


def test_a_sheet_whose_graphics_text_and_colour_agree_needs_no_reading(pair) -> None:
    a, b = pair
    b = copy.deepcopy(b)
    b["words"] = []  # nothing could be read, yet nothing differs: the original's own rule
    assert job.spec_positions_channel(a, b, 0) == {"state": "checked", "diffs": 0}


def test_a_page_without_a_specification_header_leaves_the_channel_unchecked(pair) -> None:
    """The mutation proof of the rule: if the channel counted a side that has no positions as an empty side it would be
    ``checked`` with six removals, a claim the sheet does not support."""
    a, b = pair
    b = copy.deepcopy(b)
    b["words"] = [w for w in b["words"] if w[4] not in ("Поз.", "Наименование")]
    channel = job.spec_positions_channel(a, b, 5)
    assert channel["state"] == "unchecked"
    assert "лист B" in channel["reason"]
    channel_a = job.spec_positions_channel(b, a, 5)
    assert channel_a["state"] == "unchecked" and "лист A" in channel_a["reason"]


def test_a_table_with_a_header_and_no_row_rule_is_unchecked_with_the_reason(pair, tmp_path) -> None:
    import numpy

    a, b = pair
    b = copy.deepcopy(b)
    only_frame = numpy.array([[56.7, 14.2, 56.7, 827.7], [581.1, 14.2, 581.1, 827.7]], dtype=numpy.float32)
    path = tmp_path / "frame_only.f32"
    only_frame.tofile(path)
    b["lines"] = {"file": str(path), "count": 2}
    channel = job.spec_positions_channel(a, b, 5)
    assert channel["state"] == "unchecked" and "колонки" in channel["reason"]


def test_a_table_that_holds_no_position_is_unchecked_not_all_removed(pair) -> None:
    a, b = pair
    b = copy.deepcopy(b)
    header_only = {"Поз.", "Обозначение", "Наименование", "и", "тех.", "характеристика", "Кол.", "Масса", "ед.,", "кг", "Прим."}
    b["words"] = [w for w in b["words"] if w[4] in header_only and w[1] < 95]
    channel = job.spec_positions_channel(a, b, 5)
    assert channel["state"] == "unchecked" and "нет позиций" in channel["reason"]


def test_a_specification_against_a_drawing_is_unchecked(compare) -> None:
    outcome = compare("vs1/v4.pdf", 6, "vs1/v4.pdf", 1).outcome
    channel = outcome["channels"]["spec_positions"]
    assert channel["state"] == "unchecked" and "лист B" in channel["reason"]
    assert "UNCHECKED_CHANNEL_SPEC_POSITIONS" in outcome["reasons"]
