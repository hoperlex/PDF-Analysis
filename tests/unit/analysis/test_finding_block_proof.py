"""The oracles `tests/support/finding_block_proof.py` holds the finding to block relation against can themselves fail (D-353).

A measurement that cannot report a wrong link reports none. Each verdict the proof can give (holds, marginal, WRONG, unplaced,
missed) is produced here from hand-made geometry, with a stand-in for the PDF oracle that answers from a table.
"""

from __future__ import annotations

from tests.support.finding_block_proof import BlockFact, EvidenceFact, analyse, covered_share, figures, normalise_text, text_verdict

LEFT = BlockFact("blk_left", 1, "text", (0.0, 0.2, 0.5, 0.3), "Итого")
RIGHT = BlockFact("blk_right", 1, "text", (0.5, 0.2, 1.0, 0.3), "Огнестойкость узла не менее R30")
OTHER_PAGE = BlockFact("blk_p2", 2, "text", (0.0, 0.0, 1.0, 1.0), "Огнестойкость узла")
FACT = EvidenceFact(1, 10, 20, "Огнестойкость")
IN_RIGHT = [(0.55, 0.21, 0.7, 0.29)]


class Oracle:
    """Answers where a quotation's glyphs are from a table ``{(page, char_start): boxes | None}``."""

    def __init__(self, boxes):
        self.boxes = boxes

    def quote_boxes(self, page, char_start, quote):
        return self.boxes.get((page, char_start))


def run(linked, *, boxes=None, unlinked=(), blocks=(LEFT, RIGHT, OTHER_PAGE), facts=(FACT,)):
    return analyse(
        items=[("fnd_1", linked, "label")], evidence={"fnd_1": list(facts)}, blocks=list(blocks),
        unlinked_pages=list(unlinked), oracle=Oracle({(1, 10): IN_RIGHT} if boxes is None else boxes),
    )


def test_a_link_to_the_block_the_glyphs_are_in_holds():
    report = run(["blk_right"])
    assert [p["geometry"] for p in report["pairs"]] == ["holds"]
    assert report["misses"] == []
    assert figures(report)["wrong"] == 0 and figures(report)["link_precision_by_glyphs"] == 1.0


def test_a_link_to_a_block_that_does_not_touch_the_glyphs_is_wrong_and_the_block_that_has_them_is_missed():
    # The F1 shape: the finding is linked to the label's block, its quotation stands in the other one.
    report = run(["blk_left"])
    assert [p["geometry"] for p in report["pairs"]] == ["WRONG"]
    assert [m["portal_block_id"] for m in report["misses"]] == ["blk_right"]
    result = figures(report)
    assert (result["wrong"], result["missed_links"], result["link_precision_by_glyphs"], result["recall_by_glyphs"]) == (1, 1, 0.0, 0.0)


def test_a_block_that_only_touches_the_glyphs_is_marginal_not_wrong():
    edge = [(0.45, 0.21, 0.7, 0.29)]  # 0.05 of 0.25 of the width is in the left block: touching, far from half
    report = run(["blk_left"], boxes={(1, 10): edge})
    assert [p["geometry"] for p in report["pairs"]] == ["marginal"]


def test_a_quotation_the_oracle_cannot_place_is_unplaced_and_never_counted_for_or_against_the_rule():
    report = run(["blk_left"], boxes={(1, 10): None})
    assert [p["geometry"] for p in report["pairs"]] == ["unplaced"]
    result = figures(report)
    assert result["wrong"] == 0 and result["link_precision_by_glyphs"] is None


def test_a_finding_with_evidence_only_on_an_unlinked_page_is_left_out_of_the_coverage_it_could_not_have():
    fact = EvidenceFact(2, 40, 50, "Огнестойкость")
    report = run([], boxes={(2, 40): [(0.1, 0.1, 0.2, 0.2)]}, unlinked=[2], facts=(fact,))
    result = figures(report)
    assert (result["findings"], result["findings_on_unlinked_pages_only"], result["coverage"]) == (1, 1, None)


def test_coverage_counts_findings_with_a_block_among_the_findings_that_could_have_one():
    report = analyse(
        items=[("fnd_1", ["blk_right"], "a"), ("fnd_2", [], "b")], evidence={"fnd_1": [FACT], "fnd_2": [FACT]},
        blocks=[LEFT, RIGHT], unlinked_pages=[], oracle=Oracle({(1, 10): IN_RIGHT}),
    )
    result = figures(report)
    assert (result["findings"], result["findings_with_a_block"], result["coverage"], result["missed_links"]) == (2, 1, 0.5, 1)


def test_the_share_of_a_box_a_block_covers():
    assert abs(covered_share((0.4, 0.2, 0.6, 0.3), (0.5, 0.0, 1.0, 1.0)) - 0.5) < 1e-9
    assert covered_share((0.1, 0.2, 0.2, 0.3), (0.5, 0.0, 1.0, 1.0)) == 0.0


def test_the_text_verdict_folds_case_yo_spaces_punctuation_and_line_end_hyphenation():
    assert text_verdict("Степень  огнестойкости — II.", "степень огнестойкости II") == ("contains", 1.0)
    assert text_verdict("проёмов заполнения", "Проемов   заполнения.") == ("contains", 1.0)
    assert text_verdict("огнестойкость здания", "огнестой-\nкость здания") == ("contains", 1.0)
    assert normalise_text("А-Б\nВ") == "а б в"


def test_the_text_verdict_tells_most_of_the_words_from_some_and_none():
    assert text_verdict("a b c d", "a b c x")[0] == "most"
    assert text_verdict("a b c d", "a x y z")[0] == "some"
    assert text_verdict("a b c d", "x y z")[0] == "none"
