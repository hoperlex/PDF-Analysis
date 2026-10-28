"""The thresholds and the match rules `v1.2` on hand-made pages (`CMP-MATRIX-01`).

Each rule is crossed on purpose: the pages are built so that one condition holds or fails. The numbers asserted are
the original's (``settings.py:92-94`` for the thresholds); the scores asserted are what the formula gives for the
words the pages share, written next to the page that makes them."""

from __future__ import annotations

import pytest

from auditmanager.comparison.matrix import resolve, settings
from auditmanager.comparison.matrix.lineage import assign, build_rows, find_duplicates, find_splits
from auditmanager.comparison.matrix.scoring import score

from .pages import features, page, tokens, versions_features, words

RULES = settings.RULES
V1, V2, V3 = "ver_A", "ver_B", "ver_C"


def _cells(result: dict) -> list[list[dict]]:
    return [row["cells"] for row in result["rows"]]


def test_the_thresholds_are_the_originals() -> None:
    assert (settings.MATCH_HIGH, settings.MATCH_MEDIUM, settings.MATCH_CANDIDATE_FLOOR) == (0.55, 0.35, 0.20)
    assert settings.RULES_VERSION == "v1.2"
    assert settings.RULES == {"order", "text", "kind", "margin", "resolve", "package", "direct", "permit", "pageno", "group"}


@pytest.mark.parametrize(
    ("shared", "expected_score", "state", "confidence", "reason"),
    [
        (15, 15 / 25, "matched", "high", None),  # 0.60 >= 0.55
        (14, 14 / 26, "matched", "medium", None),  # 0.538: just under the high threshold
        (12, 12 / 28, "matched", "medium", None),  # 0.35 <= 0.4286 < 0.55
        (11, 11 / 29, "matched", "medium", None),  # 0.379: just over the medium threshold
        (10, 10 / 30, "unmatched", None, "below_pair"),  # 0.333: just under it, a candidate and no pair
        (9, 9 / 31, "unmatched", None, "below_pair"),  # 0.20 <= 0.29 < 0.35: a candidate, not a pair
        (8, 8 / 32, "unmatched", None, "below_pair"),  # 0.25
        (7, 7 / 33, "unmatched", None, "below_pair"),  # 0.212: just over the candidate floor
        (6, 6 / 34, "absent", None, "no_candidates"),  # 0.176: just under it, not even a candidate
        (5, 5 / 35, "absent", None, "no_candidates"),  # 0.14 < 0.20: not even a candidate
    ],
)
def test_a_pair_is_high_medium_a_candidate_or_nothing_by_the_three_thresholds(
    shared: int, expected_score: float, state: str, confidence: str | None, reason: str | None
) -> None:
    common, own_a, own_b = tokens("о", shared), tokens("а", 20 - shared), tokens("б", 20 - shared)
    a = page(V1, 1, common + own_a)
    b = page(V2, 1, common + own_b)
    fa, fb = features([a])[0], features([b])[0]
    value, _parts = score(fa, fb, 0.0, 0.0, RULES)
    assert value == pytest.approx(expected_score)
    result = build_rows([V1, V2], versions_features({V1: [a], V2: [b]}))
    first = next(row for row in result["rows"] if row["cells"][0]["state"] == "matched")
    cell = first["cells"][1]
    assert cell["state"] == state and cell.get("confidence") == confidence
    if state == "matched":
        assert len(result["rows"]) == 1
    else:
        assert len(result["rows"]) == 2, "an unlinked page opens a row of its own"
    if reason is not None:
        assert cell["reason"] == reason
    if state == "unmatched":
        assert [c["page_number"] for c in cell["candidates"]] == [1]


def test_a_pair_with_nothing_to_compare_scores_zero_and_has_no_candidate() -> None:
    a, b = page(V1, 1, tokens("о", 3)), page(V2, 1, tokens("о", 3))
    value, parts = score(*features([a, b]), 0.0, 0.0, RULES)
    assert value == 0.0 or parts.get("text_unknown") == 1.0 or "no_content_evidence" in parts


def test_a_title_and_a_designation_count_and_a_different_kind_is_penalised() -> None:
    same = ("СИНТ-01", "5", "План освещения")
    a = page(V1, 1, tokens("о", 20), designation=same[0], sheet_number=same[1], title=same[2])
    b = page(V2, 1, tokens("о", 20), designation=same[0], sheet_number=same[1], title=same[2])
    fa, fb = features([a, b])
    value, parts = score(fa, fb, 0.0, 0.0, RULES)
    assert parts["title"] == 1.0 and parts["identity"] == 1.0 and value == pytest.approx(1.0)
    spec = page(V2, 2, tokens("о", 20), designation="СИНТ-01.СО", sheet_number="5", title="План освещения")
    _fa, fs = features([a, spec])
    penalised, parts = score(fa, fs, 0.0, 0.0, RULES)
    assert parts["kind_mismatch"] == 1.0 and penalised < value * 0.7


def test_equal_candidates_are_not_chosen_arbitrarily() -> None:
    """Rule ``margin``: two look-alike pages in the next version are not told apart by the score alone."""
    body = tokens("о", 20)
    a = page(V1, 1, body)
    twins = [page(V2, 1, body), page(V2, 2, body)]
    links, _matrix = assign(features([a]), features(twins), RULES)
    assert links == {}, "no pair is guessed between two equal candidates"
    result = build_rows([V1, V2], versions_features({V1: [a], V2: twins}))
    assert all(c["state"] != "matched" or "confidence" not in c or c["version_uid"] == V1 for cells in _cells(result) for c in cells)


def test_a_permit_is_a_document_of_its_own_and_is_never_linked_to_another_permit_or_a_sheet() -> None:
    def permit(version: str, number_text: str, body: list[str]):
        label = words(["Разрешение"], x0=250, y0=60)
        return page(version, 1, body, extra_words=label + words([number_text], x0=250, y0=80), y0=300.0)

    body = tokens("о", 20)
    one, two = permit(V1, "№1/2025", body), permit(V2, "№2/2025", body)
    fa, fb = features([one])[0], features([two])[0]
    assert (fa.kind, fb.kind) == ("permit", "permit") and fa.permit_no != fb.permit_no
    assert resolve.permit_conflict(fa, fb) is True
    ordinary = page(V2, 1, body, y0=300.0)
    assert resolve.permit_conflict(fa, features([ordinary])[0]) is True
    same_permit = permit(V2, "№1/2025", body)
    assert resolve.permit_conflict(fa, features([same_permit])[0]) is False
    different = build_rows([V1, V2], versions_features({V1: [one], V2: [two]}))
    assert len(different["rows"]) == 2
    assert all(len([c for c in cells if c["state"] == "matched"]) == 1 for cells in _cells(different))
    # no candidate is offered across permits (the other permit is not a candidate): the cells are ``absent``
    assert all(c["state"] == "absent" for cells in _cells(different) for c in cells if c["state"] != "matched")
    same = build_rows([V1, V2], versions_features({V1: [one], V2: [same_permit]}))
    assert len(same["rows"]) == 1


def test_the_package_rule_reads_the_designation_correspondence_of_the_confident_pairs() -> None:
    from types import SimpleNamespace as NS

    prev = [NS(designation="A-1"), NS(designation="A-1"), NS(designation="B-1"), NS(designation="B-1"), NS(designation="")]
    cur = [NS(designation="A-1.1"), NS(designation="A-1.1"), NS(designation="B-1.1"), NS(designation="B-1.1"), NS(designation="")]
    links = {i: (i, 0.9, {}) for i in range(5)}
    forward, reverse = resolve.package_map(prev, cur, links)
    assert forward == {"A-1": "A-1.1", "B-1": "B-1.1"} and reverse == {"A-1.1": "A-1", "B-1.1": "B-1"}
    maps = (forward, reverse)
    # a page of package A against a page of package B contradicts the correspondence from both sides
    assert resolve.package_conflict(NS(designation="A-1"), NS(designation="B-1.1"), maps) is True
    assert resolve.package_conflict(NS(designation="A-1"), NS(designation="A-1.1"), maps) is False
    assert resolve.package_conflict(NS(designation="A-1"), NS(designation=""), maps) is False
    assert resolve.package_conflict(NS(designation="Z-9"), NS(designation="B-1.1"), maps) is False  # A unknown on one side
    # one pair is not a correspondence (RESOLVE_PACKAGE_MIN = 2)
    one = resolve.package_map([NS(designation="C")], [NS(designation="D")], {0: (0, 0.9, {})})
    assert one == ({}, {})


def test_the_page_number_of_an_unstamped_report_decides_when_the_text_does_not() -> None:
    """Rule ``pageno``: three pages of a built-in report with the same text and different footer numbers."""
    body = tokens("о", 80)  # so many shared words that the footer number alone is under the margin of the score

    def numbered(version: str, number: int, footer: str):
        return page(version, number, body, extra_words=words([footer], x0=280, y0=800))

    older = [numbered(V1, 1, "1"), numbered(V1, 2, "2"), numbered(V1, 3, "3")]
    newer = [numbered(V2, 1, "3"), numbered(V2, 2, "1"), numbered(V2, 3, "2")]  # shuffled in the file
    result = build_rows([V1, V2], versions_features({V1: older, V2: newer}))
    pairs = sorted(
        (cells[0]["page_number"], cells[1]["page_number"]) for cells in _cells(result)
        if cells[0]["state"] == "matched" and cells[1]["state"] == "matched"
    )
    assert pairs == [(1, 2), (2, 3), (3, 1)], "linked by the footer number, not by position"


def test_a_footer_number_that_is_not_the_only_one_decides_nothing() -> None:
    body = tokens("о", 20)
    older = [page(V1, 1, body, extra_words=words(["1"], x0=280, y0=800)), page(V1, 2, body, extra_words=words(["1"], x0=280, y0=800))]
    newer = [page(V2, 1, body, extra_words=words(["1"], x0=280, y0=800))]
    result = build_rows([V1, V2], versions_features({V1: older, V2: newer}))
    assert not any(c["state"] == "matched" and c.get("confidence") for cells in _cells(result) for c in cells if c["version_uid"] == V2)


def test_copies_inside_a_version_are_duplicates_in_the_cell_of_their_primary() -> None:
    body = tokens("о", 30)
    stamped = [page(V1, 1, body, designation="Д-1", sheet_number="3"), page(V1, 2, tokens("б", 30)), page(V1, 3, body, designation="Д-1", sheet_number="3")]
    assert find_duplicates(features(stamped), RULES) == {3: 1}
    result = build_rows([V1], versions_features({V1: stamped}))
    assert len(result["rows"]) == 2
    first = result["rows"][0]["cells"][0]
    assert first["page_number"] == 1 and first["flags"] == ["duplicate"] and [d["page_number"] for d in first["dups"]] == [3]
    assert result["duplicates"] == {V1: {"3": 1}}


def test_two_unstamped_equal_pages_with_the_same_drawing_are_a_duplicate_too() -> None:
    body = tokens("о", 30)
    pages = [page(V1, 1, body, mask=True), page(V1, 2, body, mask=True)]
    assert find_duplicates(features(pages), RULES) == {2: 1}
    different = [page(V1, 1, body, mask=True), page(V1, 2, tokens("б", 30), mask=True)]
    assert find_duplicates(features(different), RULES) == {}


def test_a_sheet_missing_from_an_intermediate_version_is_bridged() -> None:
    sheet = tokens("о", 24)
    others_2 = [page(V2, 1, tokens("д", 24)), page(V2, 2, tokens("е", 24))]
    spec = {
        V1: [page(V1, 1, sheet), page(V1, 2, tokens("д", 24))],
        V2: others_2[:1],
        V3: [page(V3, 1, tokens("д", 24)), page(V3, 2, sheet)],
    }
    result = build_rows([V1, V2, V3], versions_features(spec))
    row = next(r for r in result["rows"] if r["cells"][0]["state"] == "matched" and r["cells"][0]["page_number"] == 1)
    assert [c["state"] for c in row["cells"]] == ["matched", "absent", "matched"]
    assert row["cells"][2]["flags"] == ["bridge"] and row["cells"][2]["confidence"] == "high" and row["cells"][2]["page_number"] == 2


def test_a_new_sheet_gets_a_row_after_the_row_of_the_previous_page_of_its_version() -> None:
    spec = {
        V1: [page(V1, 1, tokens("а", 24)), page(V1, 2, tokens("б", 24))],
        V2: [page(V2, 1, tokens("а", 24)), page(V2, 2, tokens("н", 24)), page(V2, 3, tokens("б", 24))],
    }
    result = build_rows([V1, V2], versions_features(spec))
    assert [(r["cells"][0].get("page_number"), r["cells"][1].get("page_number")) for r in result["rows"]] == [(1, 1), (None, 2), (2, 3)]


def test_a_floor_plan_repeated_per_floor_and_a_sheet_cut_in_parts_are_splits_by_the_stamps() -> None:
    old = [page(V1, 1, tokens("о", 20), designation="Д", sheet_number="1", title="Схема ВРУ-1"),
           page(V1, 2, tokens("п", 20), designation="Д", sheet_number="2", title="План 2-3 этажей. Сети")]
    new = [page(V2, 1, tokens("о", 10), designation="Д", sheet_number="1", title="Схема ВРУ-1. Начало"),
           page(V2, 2, tokens("о", 20)[10:] + tokens("о", 10)[:0], designation="Д", sheet_number="1.1", title="Схема ВРУ-1. Окончание"),
           page(V2, 3, tokens("п", 20), designation="Д", sheet_number="2", title="План 2 этажа. Сети"),
           page(V2, 4, tokens("п", 20), designation="Д", sheet_number="3", title="План 3 этажа. Сети")]
    found = find_splits(features(old), features(new))
    assert sorted((s["a_page"], s["b_page"], s["kind"]) for s in found) == [
        (1, 1, "split"), (1, 2, "split"), (2, 3, "floors"), (2, 4, "floors")]
    result = build_rows([V1, V2], versions_features({V1: old, V2: new}))
    by_source = {s["a"]["page_number"]: s for s in result["splits"]}
    assert (by_source[1]["kind"], by_source[1]["role"]) == ("split", "part") and by_source[1]["covered_percent"] == 100.0
    assert (by_source[2]["kind"], by_source[2]["role"]) == ("floors", "whole")
    flagged = {(c["version_uid"], c["page_number"]) for cells in _cells(result) for c in cells if c["state"] == "matched" and "split" in c["flags"]}
    assert {(V1, 1), (V2, 1), (V2, 2), (V1, 2), (V2, 3), (V2, 4)} == flagged


def test_the_text_coverage_of_the_parts_counts_the_old_words_that_stand_in_some_part() -> None:
    old = [page(V1, 1, tokens("о", 20) + tokens("м", 20), designation="Д", sheet_number="1", title="Схема ВРУ-1")]
    new = [page(V2, 1, tokens("о", 20), designation="Д", sheet_number="1", title="Схема ВРУ-1. Начало"),
           page(V2, 2, tokens("о", 10)[:0] + tokens("н", 5), designation="Д", sheet_number="2", title="Схема ВРУ-1. Окончание")]
    result = build_rows([V1, V2], versions_features({V1: old, V2: new}))
    assert result["splits"][0]["covered_percent"] == 50.0


def test_a_table_block_pairs_the_unresolved_sheets_of_a_group_in_order() -> None:
    """Rule ``group``: the rows of a specification moved over several sheets (each new sheet holds half of each old
    one, so the score cannot tell them apart) are a block; its sheets are linked in order with confidence ``group``
    (membership of a group, not "sheet for sheet")."""
    marks = [f"к{n}.{n}" for n in range(1, 41)]
    head = ["поз.", "наименование", "кол."]

    def sheet(version: str, number: int, slice_: list[str]):
        return page(version, number, head + slice_, designation="Д.СО", sheet_number=str(number))

    old = [sheet(V1, 1, marks[:20]), sheet(V1, 2, marks[20:])]
    new = [sheet(V2, 1, marks[:10] + marks[20:30]), sheet(V2, 2, marks[10:20] + marks[30:]), sheet(V2, 3, ["ф1.1"])]
    built = versions_features({V1: old, V2: new})
    assert {f.kind for f in built[V1] + built[V2]} == {"spec"}
    result = build_rows([V1, V2], built)
    pairs = [(c0["page_number"], c1["page_number"], c1.get("confidence"))
             for c0, c1 in (cells for cells in _cells(result)) if c0["state"] == c1["state"] == "matched"]
    assert pairs == [(1, 1, "group"), (2, 2, "group")]
    assert [c["page_number"] for cells in _cells(result) for c in cells[1:] if c["state"] == "matched"] == [1, 2, 3], "no page falls out"
    assert result["rows"][2]["cells"][0]["state"] == "absent", "the unrelated third sheet is a row of its own"


def test_group_pairs_follow_the_order_between_the_anchors() -> None:
    floor = __import__("numpy").ones((5, 5), dtype=bool)
    links = {1: (1, 0.9, {})}  # anchor: A1 <-> B1
    paired = resolve._group_pairs([0, 2], [0, 2, 3], [0, 1, 2], [0, 1, 2, 3], links, floor)
    assert paired == {0: 0, 2: 2}, "the sheets before the anchor pair with the sheets before it, after with after"
    assert resolve._increasing([(0, 2), (1, 0), (2, 1), (3, 3)]) == [(1, 0), (2, 1), (3, 3)]


def test_the_word_weight_depends_on_its_kind_and_rarity() -> None:
    assert resolve.token_class("в10") == 1.0 and resolve.token_class("щр-3") == 1.0
    assert resolve.token_class("кабель") == 0.5 and resolve.token_class("до") == 0.0
    assert resolve.token_class("125") == 0.15 and resolve.token_class("2025-10-13") == 0.15
    assert resolve.token_class("1.13.3") == 1.0, "a code of digits with separators is a designation"
    assert resolve._decisive(10.0, 1.0, 5, 1) is True
    assert resolve._decisive(2.0, 0.0, 2, 0) is False, "the lead is under RESOLVE_MIN_W"
    assert resolve._decisive(10.0, 3.0, 17, 2) is True, "robust: few words against, an overwhelming majority"
    assert resolve._decisive(10.0, 6.0, 9, 6) is False
    assert resolve._decisive(10.0, 3.0, 9, 2) is False, "the majority of the words is under 85 %"
