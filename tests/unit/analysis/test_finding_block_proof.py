"""The oracles `tests/support/finding_block_proof.py` holds the finding to block relation against can themselves fail (D-353).

A measurement that cannot report a wrong link reports none. Each verdict the proof can give (holds, marginal, WRONG, unplaced,
missed) is produced here from hand-made geometry, with a stand-in for the PDF oracle that answers from a table.
"""

from __future__ import annotations

import pytest

from auditmanager.analysis.geometry import TextLine
from tests.support.finding_block_proof import (
    BlockFact,
    EvidenceFact,
    MemoOracle,
    analyse,
    covered_share,
    degrade,
    doubtful_blocks,
    figures,
    normalise_text,
    require_same_links,
    rule_links,
    text_verdict,
)

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


# --- the second witness's reproduction (D-450) -------------------------------------------------------------------------------

TEXT = "Огнестойкость узла не менее R30 при пожаре в помещении класса Ф1"


def test_degrade_is_deterministic_keeps_the_layout_and_damages_none_at_zero_and_every_word_at_one():
    assert degrade("blk", TEXT, 0.0) == TEXT
    assert degrade("blk", TEXT, 0.3) == degrade("blk", TEXT, 0.3)
    assert degrade("blk", "a   b\nc", 0.0) == "a   b\nc" and degrade("blk", "a   b\nc", 1.0).count("\n") == 1
    everything = degrade("blk", TEXT, 1.0).split()
    assert len(everything) == len(TEXT.split()) and all(a != b for a, b in zip(everything, TEXT.split()))


def test_degrade_at_a_rate_damages_some_of_the_words_and_never_adds_one():
    some = degrade("blk", TEXT, 0.3).split()
    changed = sum(1 for a, b in zip(some, TEXT.split()) if a != b)
    assert len(some) == len(TEXT.split()) and 0 < changed < len(some)


def test_a_damaged_reading_stops_matching_the_quotation_and_an_unlinked_page_links_to_nothing():
    line = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 212.0)
    blocks = [BlockFact("blk_l", 1, "text", (0.0, 0.2, 0.5, 0.3), "Итого"), BlockFact("blk_r", 1, "text", (0.5, 0.2, 1.0, 0.3), None)]
    quote = "Огнестойкость узла не менее R30"
    fact, sizes, layer = EvidenceFact(1, 100, 140, quote), {1: (600.0, 800.0)}, {1: quote}
    texts = {"blk_l": "Итого", "blk_r": quote}
    assert rule_links([fact], [line], sizes, blocks, set(), texts, page_texts=layer) == ["blk_r"]
    assert rule_links([fact], [line], sizes, blocks, set(), {**texts, "blk_r": degrade("blk_r", quote, 1.0)}, page_texts=layer) == []
    assert rule_links([fact], [line], sizes, blocks, set(), None, page_texts=layer) == []
    assert rule_links([fact], [line], sizes, blocks, set(), texts) == [], "without the text layer's pages the witness is not asked"
    assert rule_links([fact], [line], sizes, blocks, {1}, texts, page_texts=layer) == []


def test_the_reproduction_guard_passes_on_the_same_answers():
    require_same_links({"a": ["blk_1"], "b": []}, {"a": ["blk_1"], "b": []})


@pytest.mark.parametrize(
    ("reproduced", "shipped"),
    [
        ({"a": ["blk_1"], "b": []}, {"a": ["blk_1"], "b": ["blk_2"]}),
        ({"a": ["blk_1"]}, {"a": ["blk_1"], "b": ["blk_2"]}),
        ({"a": ["blk_1"], "b": ["blk_9"]}, {"a": ["blk_1"]}),
        ({"a": ["blk_1", "blk_2"]}, {"a": ["blk_2", "blk_1"]}),
    ],
    ids=["a link missing", "a finding not answered", "a finding the adapter does not know", "another order"],
)
def test_the_reproduction_guard_fails_on_a_difference(reproduced, shipped):
    with pytest.raises(AssertionError, match="differs for"):
        require_same_links(reproduced, shipped)


def test_the_memo_oracle_asks_the_pdf_once_per_placement():
    class Counting:
        calls = 0

        def quote_boxes(self, page, start, quote):
            Counting.calls += 1
            return [(0.0, 0.0, 1.0, 1.0)]

    memo = MemoOracle(Counting())
    assert memo.quote_boxes(1, 5, "x") == memo.quote_boxes(1, 5, "x") and Counting.calls == 1
    memo.quote_boxes(1, 6, "x")
    assert Counting.calls == 2


def test_degrade_without_the_look_alikes_damages_what_no_quality_flag_names():
    from auditmanager.analysis.recognised.flags import flags_for

    seen = degrade("blk", TEXT, 1.0)
    unseen = degrade("blk", TEXT, 1.0, flaggable=False)
    assert flags_for(seen), "the look-alike damage is one a flag names (mixed script, homoglyph)"
    assert not flags_for(unseen) and unseen != TEXT, "the letter-short damage is not"


def test_a_block_is_doubtful_when_its_reading_is_flagged_or_empty_and_an_image_or_a_stamp_has_none():
    blocks = [
        BlockFact("blk_ok", 1, "text", (0.0, 0.0, 0.5, 0.5), "Огнестойкость узла"),
        BlockFact("blk_flag", 1, "text", (0.5, 0.0, 1.0, 0.5), "Огнестойкоcть узла"),  # a Latin c in a Cyrillic word
        BlockFact("blk_empty", 1, "text", (0.0, 0.5, 0.5, 1.0), None),
        BlockFact("blk_image", 1, "image", (0.5, 0.5, 1.0, 1.0), None),
        BlockFact("blk_stamp", 1, "stamp", (0.5, 0.5, 1.0, 1.0), None),
    ]
    texts = {b.portal_block_id: b.text for b in blocks if b.text}
    # `JUDGE-N2` H1/M3: an image never was doubtful here ("it is not read"), which is how it came to be passed over.
    assert doubtful_blocks(blocks, texts) == {"blk_flag", "blk_empty", "blk_image", "blk_stamp"}


def test_rule_links_passes_the_doubtful_blocks_to_the_rule():
    line = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 212.0)
    blocks = [BlockFact("blk_l", 1, "text", (0.0, 0.2, 0.5, 0.3), "Итого"), BlockFact("blk_r", 1, "text", (0.5, 0.2, 1.0, 0.3), None)]
    quote = "Огнестойкость узла не менее R30"
    fact, sizes, texts, layer = EvidenceFact(1, 100, 140, quote), {1: (600.0, 800.0)}, {"blk_l": "Итого", "blk_r": quote}, {1: quote}
    assert rule_links([fact], [line], sizes, blocks, set(), texts, doubtful={"blk_l"}, page_texts=layer) == []
    assert rule_links([fact], [line], sizes, blocks, set(), texts, doubtful=set(), page_texts=layer) == ["blk_r"]
    assert rule_links([fact], [line], sizes, blocks, set(), texts, page_texts=layer, max_gap_characters=None) == ["blk_r"]
