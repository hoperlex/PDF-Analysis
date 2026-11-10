"""`UI-PARITY-C6`: the finding to portal block relation, as a pure function over three saved documents.

Every case states the geometry in points on a 600 x 800 page (so 0.1 of the width is 60 points and 0.1 of the
height 80) and the blocks as fractions of the page; the expected ids are literals, never read back from the
function under test.

The rule claims containment and nothing more (module docstring): a block holds the evidence of a line only when it extends over
the line's whole width, because where along a line the evidence stands is not in the data. The cases that fail on the
proportional cut this rule had before are marked ``F1`` / ``F2`` (`D-353`, judge J3 2026-11-09). The cases of the second witness
(a line that no block holds, a choice among the blocks it touches by their recognised text, `D-450`) are marked ``W``. After the
independent judge's findings (`JUDGE-N2` H1, M2, M3, L1 to L3; `D-590`) the witness is asked only under the conditions of step 5 of the
rule, and the cases that had pinned the old behaviour (a block without a reading neither matches nor vetoes) say the reverse; the
judge's reproductions are the ``P1`` to ``P5`` cases.
"""

from __future__ import annotations

import pytest

import auditmanager.analysis.geometry.finding_blocks as rule_module
from auditmanager.analysis.geometry import (
    EvidenceSpan,
    PortalBox,
    Readings,
    TextLine,
    link_evidence,
    linkable_pages,
)
from auditmanager.analysis.geometry.finding_blocks import (
    EDGE_TOLERANCE,
    TOUCH_COVERAGE,
    WITNESS_MAX_GAP_LINE_HEIGHTS,
    WITNESS_MIN_CHARACTERS,
    _close,
    _near_copy,
    fold_text,
    skeleton,
)

PAGE = {1: (600.0, 800.0), 2: (600.0, 800.0)}

# One line of 20 characters, 100 pt wide, 12 pt tall: x 100..200, y 90..102 -> 0.1667..0.3333 by 0.1125..0.1275.
LINE = TextLine(1, 0, 20, 100.0, 90.0, 200.0, 102.0)
# A line of 40 characters across two columns of one page: x 50..550, y 200..212 -> 0.0833..0.9167 by 0.25..0.265.
WIDE = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 212.0)


def box(identifier: str, x0: float, y0: float, x1: float, y1: float, page: int = 1) -> PortalBox:
    return PortalBox(identifier, page, x0, y0, x1, y1)


AROUND_LINE = box("blk_a", 0.1, 0.1, 0.4, 0.2)


def link(spans, lines, blocks, pages=PAGE):
    return link_evidence(spans, lines={1: lines, 2: []}, pages=pages, blocks=blocks)


def test_an_evidence_inside_one_block_is_linked_to_it_and_to_no_other():
    other = box("blk_b", 0.5, 0.5, 0.9, 0.9)
    assert link([EvidenceSpan(1, 3, 9)], [LINE], [AROUND_LINE, other]) == ("blk_a",)


def test_a_block_that_stops_short_of_the_line_does_not_hold_the_evidence_though_it_covers_most_of_the_line():
    # F1. The block ends at x = 0.3: of the line's 0.1667..0.3333 it covers 0.8, but the evidence is somewhere on the whole line.
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [box("blk_a", 0.0, 0.0, 0.3, 1.0)]) == ()
    assert link([EvidenceSpan(1, 3, 9)], [LINE], [box("blk_a", 0.0, 0.0, 0.3, 1.0)]) == ()


def test_a_block_covering_less_than_half_of_the_line_does_not_hold_the_evidence():
    # The block ends at x = 0.24: it covers 0.0733 / 0.1667 = 0.44.
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [box("blk_a", 0.0, 0.0, 0.24, 1.0)]) == ()


def test_a_block_may_fall_short_of_the_line_by_the_edge_tolerance_and_no_more():
    # F1. A 1024 pt wide page makes the arithmetic exact: the line is x 128..256 = 0.125..0.25; the tolerance is 0.005 of the width.
    line = TextLine(1, 0, 20, 128.0, 90.0, 256.0, 102.0)
    pages = {1: (1024.0, 800.0)}
    within = box("blk_a", 0.0, 0.0, 0.25 - 0.004, 1.0)
    beyond = box("blk_a", 0.0, 0.0, 0.25 - 0.006, 1.0)
    assert link([EvidenceSpan(1, 0, 20)], [line], [within], pages=pages) == ("blk_a",)
    assert link([EvidenceSpan(1, 0, 20)], [line], [beyond], pages=pages) == ()
    same_at_the_left = box("blk_a", 0.125 + 0.006, 0.0, 1.0, 1.0)
    assert link([EvidenceSpan(1, 0, 20)], [line], [same_at_the_left], pages=pages) == ()


def test_the_block_must_cover_at_least_half_of_the_lines_height_exactly_half_holds_it():
    # A 1024 pt high page: the line is y 128..256 = 0.125..0.25; the block ends at 0.1875, half of the line's height.
    line = TextLine(1, 0, 20, 100.0, 128.0, 200.0, 256.0)
    pages = {1: (600.0, 1024.0)}
    assert link([EvidenceSpan(1, 0, 20)], [line], [box("blk_a", 0.0, 0.0, 1.0, 0.1875)], pages=pages) == ("blk_a",)
    assert link([EvidenceSpan(1, 0, 20)], [line], [box("blk_a", 0.0, 0.0, 1.0, 0.1874)], pages=pages) == ()
    assert link([EvidenceSpan(1, 0, 20)], [line], [box("blk_a", 0.0, 0.2501, 1.0, 1.0)], pages=pages) == ()


def test_a_line_across_two_columns_holds_its_evidence_in_neither_column_the_cut_is_not_a_place():
    # F1. The line crosses both columns; the characters say nothing of where the gap is, so neither half is "the left column".
    left, right = box("blk_l", 0.0, 0.2, 0.5, 0.3), box("blk_r", 0.5, 0.2, 1.0, 0.3)
    assert link([EvidenceSpan(1, 100, 120)], [WIDE], [left, right]) == ()
    assert link([EvidenceSpan(1, 125, 140)], [WIDE], [left, right]) == ()
    assert link([EvidenceSpan(1, 100, 140)], [WIDE], [left, right]) == ()


def test_a_label_and_its_value_on_one_line_do_not_move_the_value_to_the_labels_block():
    # F1, the judge's reproducer. "Итого" at x 20, a 300 pt gap carrying one space, then a phrase at x 330: one line of 36
    # characters over x 20..520. The first ten characters of the phrase (6..16) stand in the right column, and the proportional
    # cut put them at x 93..242, in the left one.
    line = TextLine(1, 0, 36, 20.0, 200.0, 520.0, 212.0)
    left, right = box("blk_left", 0.0, 0.2, 0.5, 0.3), box("blk_right", 0.5, 0.2, 1.0, 0.3)
    assert link([EvidenceSpan(1, 6, 16)], [line], [left, right]) == ()
    assert link([EvidenceSpan(1, 0, 5)], [line], [left, right]) == ()


def test_a_line_inside_one_column_is_linked_to_that_column_wherever_the_evidence_stands_in_it():
    line = TextLine(1, 0, 36, 330.0, 200.0, 520.0, 212.0)
    left, right = box("blk_left", 0.0, 0.2, 0.5, 0.3), box("blk_right", 0.5, 0.2, 1.0, 0.3)
    for span in (EvidenceSpan(1, 0, 5), EvidenceSpan(1, 12, 20), EvidenceSpan(1, 30, 36), EvidenceSpan(1, 0, 36)):
        assert link([span], [line], [left, right]) == ("blk_right",)


def test_an_evidence_over_a_line_is_held_by_every_block_that_extends_over_the_whole_of_it():
    # The line is x 0.0833..0.9167; both blocks cover all of it (the portal's rectangles may overlap).
    left, right = box("blk_l", 0.0, 0.2, 0.95, 0.3), box("blk_r", 0.05, 0.2, 1.0, 0.3)
    assert link([EvidenceSpan(1, 100, 140)], [WIDE], [left, right]) == ("blk_l", "blk_r")
    assert link([EvidenceSpan(1, 100, 110)], [WIDE], [left, right]) == ("blk_l", "blk_r")


def test_a_block_inside_another_block_holds_the_evidence_with_it():
    drawing, table = box("blk_d", 0.0, 0.0, 1.0, 1.0), box("blk_t", 0.1, 0.1, 0.4, 0.2)
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [drawing, table]) == ("blk_d", "blk_t")


def test_an_evidence_on_a_page_with_a_line_outside_it_has_no_block_even_if_the_caller_listed_the_page():
    # F2. The text layer's coordinates are not the page's (the extractor's boxes are shifted by a MediaBox origin): the evidence
    # line is above the page, the block that happens to sit under the shifted box would be a wrong one.
    shifted = [TextLine(1, 0, 20, 100.0, -31.7, 200.0, -19.7), TextLine(1, 21, 41, 100.0, 90.0, 200.0, 102.0)]
    assert link([EvidenceSpan(1, 21, 41)], shifted, [AROUND_LINE]) == ()
    assert link([EvidenceSpan(1, 21, 41)], shifted[1:], [AROUND_LINE]) == ("blk_a",)


def test_the_blocks_come_in_the_portal_order_not_the_order_of_the_evidence():
    first, second = box("blk_1", 0.0, 0.0, 1.0, 0.5), box("blk_2", 0.0, 0.5, 1.0, 1.0)
    lines = [LINE, TextLine(1, 21, 41, 100.0, 500.0, 200.0, 512.0)]
    spans = [EvidenceSpan(1, 21, 41), EvidenceSpan(1, 0, 20)]
    assert link(spans, lines, [first, second]) == ("blk_1", "blk_2")


def test_an_evidence_over_two_lines_is_linked_to_the_blocks_of_both():
    below = TextLine(1, 21, 41, 100.0, 500.0, 200.0, 512.0)
    upper, lower = box("blk_1", 0.0, 0.0, 1.0, 0.2), box("blk_2", 0.0, 0.5, 1.0, 0.7)
    assert link([EvidenceSpan(1, 10, 30)], [LINE, below], [upper, lower]) == ("blk_1", "blk_2")


def test_an_evidence_that_no_block_covers_has_no_block_and_is_not_moved_to_the_nearest():
    far = box("blk_a", 0.6, 0.6, 0.9, 0.9)
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [far]) == ()


def test_a_block_of_another_page_never_holds_the_evidence_even_at_the_same_place():
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [box("blk_p2", 0.1, 0.1, 0.4, 0.2, page=2)]) == ()


def test_an_evidence_on_a_page_where_no_link_can_be_derived_has_no_block():
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [AROUND_LINE], pages={2: (600.0, 800.0)}) == ()


def test_a_span_that_covers_only_the_separator_between_two_lines_holds_nothing():
    # The "\n" at offset 20 belongs to neither line (the lines span 0..20 and 21..41).
    below = TextLine(1, 21, 41, 100.0, 500.0, 200.0, 512.0)
    assert link([EvidenceSpan(1, 20, 21)], [LINE, below], [AROUND_LINE, box("blk_b", 0.0, 0.5, 1.0, 0.7)]) == ()


def test_a_finding_with_no_evidence_is_linked_to_nothing():
    assert link([], [LINE], [AROUND_LINE]) == ()


def test_two_items_naming_one_block_name_it_once():
    spans = [EvidenceSpan(1, 0, 5), EvidenceSpan(1, 10, 20)]
    assert link(spans, [LINE], [AROUND_LINE]) == ("blk_a",)


# --- the pages a link can be derived on -------------------------------------------------------------------------


def portal_page(number: int = 1, *, width: int = 1200, height: int = 1600, rotation: int = 0, geometry: str = "ok") -> dict:
    return {"page_number": number, "width_px": width, "height_px": height, "rotation_deg": rotation, "geometry": geometry}


def inventory_page(width: float = 600.0, height: float = 800.0, rotation: int = 0) -> dict:
    return {"page_number": 1, "width_pt": width, "height_pt": height, "rotation_deg": rotation}


def test_a_page_whose_raster_describes_the_text_layers_page_is_linkable_with_its_size():
    assert linkable_pages([portal_page()], {1: inventory_page()}) == {1: (600.0, 800.0)}


def test_a_page_the_portal_itself_marked_a_mismatch_is_not_linkable():
    assert linkable_pages([portal_page(geometry="geometry_mismatch")], {1: inventory_page()}) == {}


def test_a_page_whose_aspect_differs_from_the_text_layers_page_is_not_linkable():
    # A CropBox narrower than the MediaBox: the portal rasterised 600 x 400 of the 600 x 800 the extractor measured.
    assert linkable_pages([portal_page(width=1200, height=800)], {1: inventory_page()}) == {}


def test_a_page_with_a_different_rotation_is_not_linkable():
    assert linkable_pages([portal_page(width=1600, height=1200, rotation=90)], {1: inventory_page(800.0, 600.0)}) == {}


def test_a_quarter_turn_both_sides_agree_on_is_linkable():
    page = portal_page(width=1600, height=1200, rotation=90)
    assert linkable_pages([page], {1: inventory_page(800.0, 600.0, 90)}) == {1: (800.0, 600.0)}


def test_a_page_the_inventory_does_not_hold_is_not_linkable():
    assert linkable_pages([portal_page(2)], {1: inventory_page()}) == {}


def line_at(x0: float, y0: float, x1: float, y1: float) -> TextLine:
    return TextLine(1, 0, 10, x0, y0, x1, y1)


def test_a_page_with_a_line_above_the_page_is_not_linkable_the_origin_of_the_mediabox_is_not_zero():
    # F2, the judge's row B: MediaBox [100 50 700 850], text 50 pt from the top; the extractor reports top -31.7.
    lines = {1: [line_at(150.0, -31.7, 441.2, 8.3)]}
    assert linkable_pages([portal_page()], {1: inventory_page()}) == {1: (600.0, 800.0)}
    assert linkable_pages([portal_page()], {1: inventory_page()}, lines) == {}


def test_a_page_with_a_line_past_its_right_or_bottom_edge_is_not_linkable():
    # F2, the judge's row G: a rotated page whose line reaches x 831.7 on an 800 pt wide page.
    assert linkable_pages([portal_page(width=1600, height=1200, rotation=90)], {1: inventory_page(800.0, 600.0, 90)},
                          {1: [line_at(791.7, 0.0, 831.7, 81.2)]}) == {}
    assert linkable_pages([portal_page()], {1: inventory_page()}, {1: [line_at(100.0, 790.0, 200.0, 801.5)]}) == {1: (600.0, 800.0)}, (
        "a hair past the edge is the glyph box of a font, not a shift"
    )
    assert linkable_pages([portal_page()], {1: inventory_page()}, {1: [line_at(100.0, 790.0, 200.0, 808.0)]}) == {}


def test_a_page_whose_lines_all_lie_inside_it_stays_linkable_and_other_pages_lines_do_not_count():
    lines = {1: [line_at(50.0, 68.3, 341.2, 108.3)], 2: [line_at(0.0, -99.0, 10.0, 10.0)]}
    assert linkable_pages([portal_page()], {1: inventory_page()}, lines) == {1: (600.0, 800.0)}


# --- the second witness (`D-450`, `D-590`) --------------------------------------------------------------------------------
#
# The line is WIDE: x 50..550 on the 600 pt page, 0.0833..0.9167 across, y 0.25..0.265 down, 40 characters. It is 12 pt tall, so the widest
# gap the witness tolerates (two heights, `D-626`) is 24 pt, 0.04 of the page's width, whatever the number of its characters. Two column
# blocks stand at either side of x = 0.5; neither holds the line (the evidence is somewhere on it), both of them touch and cross it.

LEFT = box("blk_l", 0.0, 0.2, 0.5, 0.3)
RIGHT = box("blk_r", 0.5, 0.2, 1.0, 0.3)
QUOTE = "Огнестойкость узла не менее R30"
RIGHT_TEXT = "Огнестойкость узла не менее R30."
LEFT_TEXT = "Итого по разделу"
#: The text layer's page: the quotation occurs in it once (the evidence is that occurrence).
PAGE_TEXT = "Итого по разделу\n" + RIGHT_TEXT + "\nКонец страницы"
TEXTS = {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}


def witness(quote, texts, blocks=(LEFT, RIGHT), *, span=(100, 140), line=WIDE, page_text=PAGE_TEXT, **options):
    spans = [EvidenceSpan(1, span[0], span[1], quote)]
    page_texts = None if page_text is None else {1: page_text}
    return link_evidence(
        spans, lines={1: [line], 2: []}, pages=PAGE, blocks=list(blocks), block_texts=texts, page_texts=page_texts, **options,
    )


def test_w_a_line_across_two_blocks_is_linked_to_the_one_whose_text_contains_the_quotation():
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}) == ("blk_r",)
    assert witness(QUOTE, {"blk_l": RIGHT_TEXT, "blk_r": LEFT_TEXT}) == ("blk_l",)


def test_w_without_the_recognised_text_or_the_quotation_or_the_pages_text_the_geometry_decides_alone_as_before():
    assert witness(QUOTE, None) == ()
    assert witness(QUOTE, {}) == ()
    assert witness(None, TEXTS) == ()
    assert witness("", TEXTS) == ()
    assert witness(QUOTE, TEXTS, page_text=None) == (), "the witness is asked only when the page's text says the quotation is unique"
    # And the call that names none of them is the call of before the witness: the same answer on every geometry case above.
    assert link_evidence([EvidenceSpan(1, 100, 140)], lines={1: [WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT]) == ()
    assert link_evidence([EvidenceSpan(1, 100, 140, QUOTE)], lines={1: [WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT]) == ()


def test_w_two_blocks_that_both_contain_the_quotation_make_it_ambiguous_and_no_link_is_made():
    assert witness(QUOTE, {"blk_l": RIGHT_TEXT, "blk_r": "Здесь " + RIGHT_TEXT}) == ()


def test_w_no_block_that_contains_the_quotation_means_no_link_not_the_nearest_or_the_most_similar():
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": "Огнестойкость узла не менее R45"}) == ()
    # Most of the words are in the right block (all but the last), and the quotation is still not in it.
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": "Огнестойкость узла не менее"}) == ()


def test_w_h1_a_touching_block_with_no_reading_makes_the_witness_abstain_it_neither_matches_nor_is_passed_over():
    # Reversed by `JUDGE-N2` H1 (the cases of the first witness pinned "a block without text neither matches nor vetoes", which is how
    # a text block that repeated the quotation won over an image block the evidence stood in).
    assert witness(QUOTE, {"blk_r": RIGHT_TEXT}) == (), "the left block has no entry at all"
    assert witness(QUOTE, {"blk_l": "", "blk_r": RIGHT_TEXT}) == (), "the left block's body is empty"
    assert witness(QUOTE, {"blk_l": " ,. ", "blk_r": RIGHT_TEXT}) == (), "a body with no word in it reads nothing"
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}) == ("blk_r",), "and with both read the link is made"


def test_w_a_block_without_a_reading_that_the_line_does_not_touch_changes_nothing():
    far, other_page = box("blk_far", 0.0, 0.6, 1.0, 0.7), box("blk_p2", 0.0, 0.2, 1.0, 0.3, page=2)
    assert witness(QUOTE, TEXTS, blocks=(LEFT, RIGHT, far, other_page)) == ("blk_r",)


def test_w_the_comparison_folds_case_yo_whitespace_hyphenation_and_punctuation():
    quote = "Ёлка у ПОДЪЕЗДА, строительство-дома не менее R30"
    text = "елка   у\nподъезда  строи-\nтельство дома  не менее r30!"
    assert witness(quote, {"blk_l": LEFT_TEXT, "blk_r": text}, page_text=text) == ("blk_r",)
    page = "строи\u00adтельство дома"
    assert witness("Строительство дома", {"blk_l": LEFT_TEXT, "blk_r": page}, page_text=page) == ("blk_r",)
    page = "строи‐\nтельство дома"
    assert witness("Строительство дома", {"blk_l": LEFT_TEXT, "blk_r": page}, page_text=page) == ("blk_r",)
    page = "строи‑ \n  тельство дома"
    assert witness("Строительство дома", {"blk_l": LEFT_TEXT, "blk_r": page}, page_text=page) == ("blk_r",)


def test_w_the_quotation_must_be_a_run_of_whole_words_of_the_text_not_a_piece_of_a_word():
    for quote in ("узла не менее R3", "гнестойкость узла не", "узла менее R30 не"):
        # The page holds the quotation once (after the block's text), so the page asks and the block's words decide.
        assert witness(quote, TEXTS, page_text=RIGHT_TEXT + " | " + quote) == (), quote


def test_w_a_quotation_shorter_than_the_minimum_is_not_asked_about_the_witness():
    assert fold_text("R30 шт.") == "r30 шт" and len(fold_text("R30 шт.")) < WITNESS_MIN_CHARACTERS
    texts, page = {"blk_l": LEFT_TEXT, "blk_r": "Огнестойкость R30 шт."}, "Огнестойкость R30 шт."
    assert witness("R30 шт.", texts, page_text=page) == ()
    assert witness("R30 шт.", texts, page_text=page, witness_min_characters=1) == ("blk_r",)
    assert len(fold_text(QUOTE)) >= WITNESS_MIN_CHARACTERS
    # The minimum counts the folded text, spaces included: "a b c d e f g h" is 15 characters.
    spelled = {"blk_l": LEFT_TEXT, "blk_r": "a b c d e f g h"}
    assert witness("a.b.c.d.e.f.g.h", spelled, page_text="a b c d e f g h", witness_min_characters=15) == ("blk_r",)
    assert witness("a.b.c.d.e.f.g.h", spelled, page_text="a b c d e f g h", witness_min_characters=16) == ()


def test_w_a_block_the_line_does_not_touch_is_never_a_candidate_whatever_its_text_says():
    above = box("blk_up", 0.0, 0.0, 1.0, 0.1)
    other_page = box("blk_p2", 0.0, 0.2, 1.0, 0.3, page=2)
    texts = {"blk_up": RIGHT_TEXT, "blk_p2": RIGHT_TEXT, "blk_l": LEFT_TEXT, "blk_r": "Другой текст"}
    assert witness(QUOTE, texts, blocks=(above, other_page, LEFT, RIGHT)) == ()


def test_w_p3_a_block_that_covers_less_than_half_of_the_lines_height_touches_it_and_cannot_be_linked_or_passed_over():
    # The line is y 0.25..0.265; this block ends at 0.2575, half of the height (to the rounding) short of it.
    short = box("blk_short", 0.5, 0.2, 1.0, 0.2575 - 0.0001)
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_short": RIGHT_TEXT}, blocks=(LEFT, short)) == (), "it holds the quotation, is not crossed"
    enough = box("blk_enough", 0.5, 0.2, 1.0, 0.2575 + 0.0001)
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_enough": RIGHT_TEXT}, blocks=(LEFT, enough)) == ("blk_enough",)
    # The judge's P3: the true block (49 % of the height, the quotation read right in it) is not crossed, a neighbour repeats the quotation.
    assert witness(QUOTE, {"blk_l": RIGHT_TEXT, "blk_r": RIGHT_TEXT}, blocks=(box("blk_l", 0.0, 0.2, 0.5, 0.2575 - 0.0001), RIGHT)) == ()
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT, "blk_low": RIGHT_TEXT}, blocks=(
        LEFT, RIGHT, box("blk_low", 0.0, 0.2, 0.5, 0.2575 - 0.0001))) == (), "touching is not crossing: it counts"


def test_w_a_block_touches_the_line_from_a_tenth_of_its_height_and_from_more_than_the_edge_tolerance_across():
    assert TOUCH_COVERAGE == 0.1 and EDGE_TOLERANCE == 0.005
    height = 0.015                                  # the line's height, y 0.25..0.265
    # A block that starts 11 % of the line's height above its bottom edge touches it; one that starts 9 % above does not.
    touching = box("blk_x", 0.0, 0.25 + height * 0.89, 1.0, 0.4)
    assert witness(QUOTE, TEXTS, blocks=(LEFT, RIGHT, touching)) == (), "11 % of the height: touching, and nothing reads it"
    assert witness(QUOTE, TEXTS, blocks=(LEFT, RIGHT, box("blk_x", 0.0, 0.25 + height * 0.91, 1.0, 0.4))) == ("blk_r",), "9 %: not touching"
    # Across: the line ends at 0.9167; a block that reaches 0.0052 in touches it, one that reaches 0.0048 in does not.
    end = 50.0 / 600 + 500.0 / 600
    assert witness(QUOTE, TEXTS, blocks=(LEFT, RIGHT, box("blk_x", end - 0.0052, 0.2, 1.0, 0.3))) == ()
    assert witness(QUOTE, TEXTS, blocks=(LEFT, RIGHT, box("blk_x", end - 0.0048, 0.2, 1.0, 0.3))) == ("blk_r",)


def test_w_a_block_that_only_grazes_the_end_of_the_line_does_not_touch_it_and_one_that_reaches_in_does():
    base = (box("blk_a", 0.0, 0.2, 0.5, 0.3), box("blk_b", 0.5, 0.2, 0.9166, 0.3))
    texts = {"blk_a": LEFT_TEXT, "blk_b": RIGHT_TEXT}
    assert witness(QUOTE, texts, blocks=base) == ("blk_b",), "the line ends at 0.9167: the block stops 0.0001 short, inside the tolerance"
    assert witness(QUOTE, texts, blocks=(*base, box("blk_g", 0.915, 0.2, 1.0, 0.3))) == ("blk_b",), "a graze of 0.0017 reaches the line not at all"
    assert witness(QUOTE, texts, blocks=(*base, box("blk_g", 0.9, 0.2, 1.0, 0.3))) == (), "a block from 0.9 reaches 0.0167 in and nothing reads it"


def test_w_a_line_a_block_holds_is_never_given_to_the_witness_geometry_is_not_second_guessed_by_a_reading():
    holder = box("blk_all", 0.0, 0.2, 1.0, 0.3)
    texts = {"blk_all": "Здесь нет цитаты", "blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}
    assert witness(QUOTE, texts, blocks=(holder, LEFT, RIGHT)) == ("blk_all",)


def test_w_the_witness_does_not_change_what_a_block_that_holds_a_line_gives_the_other_lines_of_the_evidence():
    # Two lines: the first is held by the wide block, the second crosses the two columns; one evidence on each.
    first = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 212.0)
    second = TextLine(1, 141, 181, 50.0, 400.0, 550.0, 412.0)
    holder = box("blk_top", 0.0, 0.2, 1.0, 0.3)
    left, right = box("blk_l2", 0.0, 0.45, 0.5, 0.55), box("blk_r2", 0.5, 0.45, 1.0, 0.55)
    spans = [EvidenceSpan(1, 100, 140, "Заголовок раздела"), EvidenceSpan(1, 141, 181, QUOTE)]
    texts = {"blk_top": "x", "blk_l2": "y", "blk_r2": QUOTE}
    found = link_evidence(spans, lines={1: [first, second]}, pages=PAGE, blocks=[holder, left, right], block_texts=texts,
                          page_texts={1: "Заголовок раздела\n" + QUOTE})
    assert found == ("blk_top", "blk_r2")


def test_w_a_quotation_over_two_lines_is_looked_for_whole_in_the_blocks_one_line_of_it_touches():
    first = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 212.0)
    second = TextLine(1, 141, 181, 50.0, 214.0, 550.0, 226.0)
    both = box("blk_both", 0.5, 0.2, 1.0, 0.3)
    quote = "Огнестойкость узла\nне менее R30 при пожаре"
    spans = [EvidenceSpan(1, 100, 181, quote)]

    def found(texts, page="Огнестойкость узла не менее R30 при пожаре"):
        return link_evidence(spans, lines={1: [first, second]}, pages=PAGE, blocks=[LEFT, both], block_texts=texts, page_texts={1: page})

    assert found({"blk_l": LEFT_TEXT, "blk_both": "Огнестойкость узла не менее R30 при пожаре"}) == ("blk_both",)
    assert found({"blk_l": LEFT_TEXT, "blk_both": "Огнестойкость узла"}) == (), "half of the quotation is not the quotation"


def test_w_an_evidence_on_a_page_that_is_not_linkable_or_is_shifted_is_not_given_to_the_witness_either():
    kept = dict(block_texts=TEXTS, page_texts={1: PAGE_TEXT})
    assert link_evidence([EvidenceSpan(1, 100, 140, QUOTE)], lines={1: [WIDE]}, pages={2: (600.0, 800.0)}, blocks=[LEFT, RIGHT], **kept) == ()
    above = TextLine(1, 0, 20, 100.0, -31.7, 200.0, -19.7)
    assert link_evidence([EvidenceSpan(1, 100, 140, QUOTE)], lines={1: [above, WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT], **kept) == ()
    assert link_evidence([EvidenceSpan(1, 100, 140, QUOTE)], lines={1: [WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT], **kept) == ("blk_r",)


def test_w_the_witness_links_come_in_the_portal_order_and_join_the_geometry_links_of_other_evidence():
    held_line = TextLine(1, 0, 20, 100.0, 90.0, 200.0, 102.0)  # inside AROUND_LINE
    spans = [EvidenceSpan(1, 100, 140, QUOTE), EvidenceSpan(1, 0, 20, "что угодно")]
    blocks = [LEFT, AROUND_LINE, RIGHT]
    found = link_evidence(spans, lines={1: [WIDE, held_line]}, pages=PAGE, blocks=blocks, block_texts=TEXTS, page_texts={1: PAGE_TEXT})
    assert found == ("blk_a", "blk_r"), "the order of the blocks list (blk_l, blk_a, blk_r), not the order of the evidence"


def test_w_fold_text_is_the_words_in_lower_case_with_single_spaces():
    assert fold_text("  Ёж,\tЁЛКА!\n№ 5 ") == "еж елка 5"
    assert fold_text("№5") == fold_text("№ 5") == "5", "the number sign is a separator (NFKC would have made it «No»)"
    assert fold_text("строи-\n  тельство") == "строительство"
    assert fold_text("светло-серый") == "светло серый", "a hyphen inside a line is a separator, not a break"
    assert fold_text("") == fold_text(" ,.;") == ""


def test_w_l2_a_number_keeps_its_sign_and_its_decimal_or_range_separator():
    assert fold_text("отм. +3.000 и -3.000") == "отм +3.000 и -3.000", "the sign is part of the number"
    assert fold_text("−3.000") == fold_text("–3.000") == fold_text("-3.000") == "-3.000", "a minus and an en dash are one sign"
    assert len({fold_text(text) for text in ("1,5", "1.5", "1-5", "1 5")}) == 4, "four different values"
    assert fold_text("п-19") == "п 19" and fold_text("КР-р-по 25") == "кр р по 25", "a hyphen inside a word is not a sign"
    assert fold_text("Ф1.3. Класс") == "ф1.3 класс", "the full stop that ends a sentence is not a separator"
    assert " табл 2 " in f" {fold_text('см. табл. 2.')} " and " табл 2 " not in f" {fold_text('табл. 2.5')} ", "a table 2 is not table 2.5"


def test_w_a_doubtful_reading_of_any_touching_block_makes_the_witness_abstain():
    # The quotation may stand in the block whose reading failed; the other block's match would then be a wrong link.
    assert witness(QUOTE, TEXTS) == ("blk_r",)
    assert witness(QUOTE, TEXTS, doubtful_blocks={"blk_l"}) == (), "the left block's reading is flagged; the right one's match is not trusted"
    assert witness(QUOTE, TEXTS, doubtful_blocks={"blk_r"}) == (), "the block that matches is itself flagged"


def test_w_a_doubtful_block_the_line_does_not_touch_changes_nothing():
    far, other_page = box("blk_far", 0.0, 0.6, 1.0, 0.7), box("blk_p2", 0.0, 0.2, 1.0, 0.3, page=2)
    texts = {**TEXTS, "blk_far": "x", "blk_p2": "y"}
    assert witness(QUOTE, texts, blocks=(LEFT, RIGHT, far, other_page), doubtful_blocks={"blk_far", "blk_p2"}) == ("blk_r",)


def test_w_a_doubtful_reading_does_not_touch_the_geometry_links():
    holder = box("blk_all", 0.0, 0.2, 1.0, 0.3)
    assert witness(QUOTE, TEXTS, blocks=(holder, LEFT, RIGHT), doubtful_blocks={"blk_l", "blk_r"}) == ("blk_all",)
    assert link_evidence([EvidenceSpan(1, 0, 20)], lines={1: [LINE]}, pages=PAGE, blocks=[AROUND_LINE], doubtful_blocks={"blk_a"}) == ("blk_a",)


def test_w_a_near_copy_of_the_quotation_in_another_touching_block_makes_the_witness_abstain():
    # The right block holds the quotation exactly; the left one holds the same phrase with a word read one letter short.
    # The quotation may stand in the left block, whose reading is damaged (no quality flag), so the right one is not trusted.
    damaged = "Огнестойкость узла не менее R3"
    assert witness(QUOTE, {"blk_l": damaged, "blk_r": RIGHT_TEXT}) == ()
    assert witness(QUOTE, {"blk_l": "Огнестойкость узла не менее R30 и", "blk_r": "Огнестойкость узла не менее R30"}) == (), "an exact copy too"
    assert witness(QUOTE, {"blk_l": "Огнестойкость узла", "blk_r": RIGHT_TEXT}) == ("blk_r",), "half of the words are not a near copy"


def sk(text):
    return tuple(skeleton(word) for word in fold_text(text).split())


def test_w_a_near_copy_is_an_alignment_of_the_words_at_a_cost_of_a_quarter_of_them_at_most():
    assert _near_copy(sk("не нормируется п 5"), sk("не нормируется п 6")) is True, "one of four: allowed"
    assert _near_copy(sk("не нормируется п 5"), sk("не нормируется р 6")) is False, "two of four"
    assert _near_copy(sk("огнестойкость узла"), sk("огнестойкость стен")) is False, "no miss is allowed in two words"
    assert _near_copy(sk("огнестойкость узла"), sk("огнестоикость узла")) is True, "one letter wrong in a long word is the same word"
    assert _near_copy(sk("a" * 8), sk("x " + "a" * 8 + " y")) is True and _near_copy(sk("a" * 8), sk("x y")) is False
    assert _near_copy(sk("aaaaaaaa bbbbbbbb"), sk("aaaaaaaa")) is False, "a text shorter than the quotation holds no alignment"
    assert _near_copy((), ("а",)) is False and _near_copy(("а",), ()) is False


def test_w_m2_a_missing_an_extra_and_a_merged_or_split_word_cost_one_each_and_the_budget_is_a_quarter_of_the_words():
    # 8 words: two misses are allowed, three are not.
    eight = "один два три четыре пять шесть семь восемь"
    assert _near_copy(sk(eight), sk("один два четыре пять шесть семь восемь")) is True, "one word missing"
    assert _near_copy(sk(eight), sk("один два три лишнее четыре пять шесть семь восемь")) is True, "one word extra"
    assert _near_copy(sk(eight), sk("один два три четыре пять шесть семьвосемь")) is True, "a space lost: two words are one"
    assert _near_copy(sk(eight), sk("один дватри четыре пять шесть семь восемь")) is True
    assert _near_copy(sk(eight), sk("один два три чет ыре пять шесть семь восемь")) is True, "a space added: one word is two"
    assert _near_copy(sk(eight), sk("один два пять шесть семь восемь")) is True, "two words missing: two misses"
    assert _near_copy(sk(eight), sk("один пять шесть семь восемь")) is False, "three words missing"
    assert _near_copy(sk(eight), sk("один дватри четыре пять шестьсемь восемь")) is True, "two merges"
    assert _near_copy(sk(eight), sk("один дватри четыре пять шестьсемь вос емь")) is False, "three"
    # 4 words allow one: a merge or a split alone is a near copy, a merge and a missing word are not.
    assert _near_copy(sk("один два три четыре"), sk("один дватри четыре")) is True, "two words written as one"
    assert _near_copy(sk("один два четыре пять"), sk("один два чет ыре пять")) is True, "one word written as two"
    assert _near_copy(sk("один два четыре пять"), sk("один два чет ыре")) is False, "a split and a word missing"
    assert _near_copy(sk("один два три четыре"), sk("один дватри")) is False, "a merge and a word missing"
    # 3 words: nothing is allowed, and a merged pair is no longer the quotation's words.
    assert _near_copy(sk("кладка из кирпича"), sk("кладка изкирпича")) is False


def test_w_m2_look_alikes_a_digit_for_a_letter_and_a_lost_sign_are_one_word_read_two_ways():
    assert skeleton("b25") == skeleton("в25"), "the Latin B of a class and the Cyrillic В"
    assert skeleton("200") == skeleton("2oo") == skeleton("2оо"), "a letter O for a zero"
    assert skeleton("-3.000") == skeleton("+3.000") == skeleton("3.000") == skeleton("з.ооо"), "a sign lost or flipped, a З for a 3"
    assert skeleton("i") == skeleton("1") == skeleton("l")
    assert skeleton("кладка") != skeleton("клад")


def test_w_l1_the_same_near_copy_question_is_asked_of_one_block_once():
    readings = Readings({"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}, (), {1: PAGE_TEXT})
    asked = []
    original = rule_module._near_copy

    def counting(quotation, words):
        asked.append((quotation, words))
        return original(quotation, words)

    rule_module._near_copy = counting
    try:
        words = sk(QUOTE)
        assert [readings.near_copy(words, "blk_l") for _ in range(3)] == [False] * 3
        assert [readings.near_copy(words, "blk_r") for _ in range(2)] == [True] * 2
    finally:
        rule_module._near_copy = original
    assert len(asked) == 2


def test_w_a_near_copy_in_a_block_the_line_does_not_touch_changes_nothing():
    damaged = "Огнестойкость узла не менее R3"
    far = box("blk_far", 0.0, 0.6, 1.0, 0.7)
    assert witness(QUOTE, {**TEXTS, "blk_far": damaged}, blocks=(LEFT, RIGHT, far)) == ("blk_r",)


def test_w_h1_p2_a_stretch_of_the_line_no_block_covers_makes_the_witness_abstain_unless_it_is_a_gutter():
    # The line is 12 pt tall on a 600 pt wide page: a height is 0.02 of the width and two of them (0.04, 24 pt) is the most a gap may be.
    assert WITNESS_MAX_GAP_LINE_HEIGHTS == 2.0
    right = box("blk_r", 0.5, 0.2, 1.0, 0.3)
    texts = {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}
    assert witness(QUOTE, texts, blocks=(box("blk_l", 0.0, 0.2, 0.5 - 0.03, 0.3), right)) == ("blk_r",), "a gutter of 0.03: 18 pt, 1.5 heights"
    assert witness(QUOTE, texts, blocks=(box("blk_l", 0.0, 0.2, 0.5 - 0.06, 0.3), right)) == (), "a gap of 0.06: 36 pt, 3 heights"
    # The judge's P2: the left half of the line is covered by no block at all (a stamp's text, a block the portal did not detect).
    assert witness(QUOTE, {"blk_r": RIGHT_TEXT}, blocks=(right,)) == ()
    assert witness(QUOTE, {"blk_r": RIGHT_TEXT}, blocks=(right,), witness_max_gap_line_heights=None) == ("blk_r",), "the ablation: no limit"
    # The ends of the line count: the right block stops before the line's end.
    assert witness(QUOTE, texts, blocks=(LEFT, box("blk_r", 0.5, 0.2, 0.9167 - 0.06, 0.3))) == ()
    assert witness(QUOTE, texts, blocks=(LEFT, box("blk_r", 0.5, 0.2, 0.9167 - 0.03, 0.3))) == ("blk_r",)


def test_w_d626_a2_the_limit_is_two_heights_of_the_line_to_the_point():
    # The judge's A2, in the unit of the rule: an unboxed stretch just under and just over two heights (24 pt), with a label of 13
    # characters standing in it and the right block's reading holding the label (a portal that read it in from the neighbour).
    quote = "Ось Б узел 12"
    texts = {"blk_l": "Итого по разделу", "blk_r": "Ось Б узел 12 см. лист 4"}
    page_text = f"{quote} прочее"
    for gap_pt, linked in ((22.8, True), (25.2, False)):
        left = box("blk_l", 50 / 600, 0.2, (300 - gap_pt) / 600, 0.3)
        right = box("blk_r", 300 / 600, 0.2, 560 / 600, 0.3)
        got = witness(quote, texts, blocks=(left, right), page_text=page_text)
        assert got == (("blk_r",) if linked else ()), f"{gap_pt} pt of a 12 pt line: {gap_pt / 12:.2f} heights"


def test_w_d626_a2b_a_wide_gap_in_the_line_does_not_widen_the_gap_that_is_tolerated():
    # The judge's A2b (`D-626`). Words that stand side by side at one height are one line however far apart (step 2), so a line of 25
    # characters across 500 pt has a "mean character" of 20 pt, and a limit of four of them was 80 pt: a 15-character label in a stretch
    # of 65 pt that no block boxes passed when the portal had read it into the neighbouring block. In heights of the line (12 pt, so 24 pt)
    # it abstains: the same stretch is five heights.
    line = TextLine(1, 0, 25, 50.0, 200.0, 550.0, 212.0)
    neighbour = box("blk_r", 115 / 600, 0.2, 560 / 600, 0.3)                      # starts 65 pt in; x 50..115 is boxed by nothing
    quote = "Ось Б-12 узел 3"
    texts = {"blk_r": "Ось Б-12 узел 3 по серии 2.240"}
    page_text = f"{quote} прочее"
    assert witness(quote, texts, blocks=(neighbour,), span=(0, 25), line=line, page_text=page_text) == ()
    assert witness(quote, texts, blocks=(neighbour,), span=(0, 25), line=line, page_text=page_text,
                   witness_max_gap_line_heights=None) == ("blk_r",), "the ablation: no limit, the case that passed"
    # The answer is the same whatever the number of characters the line holds: the stretch is the same 65 pt of the same 12 pt line.
    for characters in (5, 25, 400):
        counted = TextLine(1, 0, characters, 50.0, 200.0, 550.0, 212.0)
        assert witness(quote, texts, blocks=(neighbour,), span=(0, characters), line=counted, page_text=page_text) == (), characters
    # And a stretch of 20 pt (under two heights) of that line is a gutter whatever the line's characters are.
    gutter = box("blk_r", 70 / 600, 0.2, 560 / 600, 0.3)
    for characters in (5, 25, 400):
        counted = TextLine(1, 0, characters, 50.0, 200.0, 550.0, 212.0)
        assert witness(quote, texts, blocks=(gutter,), span=(0, characters), line=counted, page_text=page_text) == ("blk_r",), characters


def test_w_d626_the_unit_is_the_height_of_the_line_so_a_taller_line_tolerates_a_wider_gap():
    # The same 30 pt unboxed stretch: 2.5 heights of a 12 pt line, 1.25 heights of a 24 pt one.
    texts = {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}
    right = box("blk_r", 0.5, 0.2, 1.0, 0.3)
    left = box("blk_l", 0.0, 0.2, 0.5 - 0.05, 0.3)
    assert witness(QUOTE, texts, blocks=(left, right)) == ()
    tall = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 224.0)
    assert witness(QUOTE, texts, blocks=(left, right), line=tall) == ("blk_r",)


def test_w_h1_p1_an_image_block_that_holds_the_label_while_the_notes_repeat_it_gives_no_link_to_the_notes():
    # The judge's P1: a drawing's label is the evidence (the first occurrence on the page), the notes block repeats the phrase.
    quote = "Кладка из керамического кирпича"
    notes = "Примечания\n1. Кладка из керамического кирпича выполнять на растворе М100.\n2. Перемычки см. лист 5."
    # (a) The page's text holds the phrase twice (the label and the note): not unique, the witness is not asked.
    twice = "Кладка из керамического кирпича\n" + notes
    assert witness(quote, {"blk_r": notes}, page_text=twice) == ()
    # (b) Whatever the page says, a touching block without a reading (the image) makes the witness abstain.
    assert witness(quote, {"blk_r": notes}, page_text=notes) == ()
    assert witness(quote, {"blk_l": "", "blk_r": notes}, page_text=notes) == ()
    # (c) Control: with the left block read, and the quotation only in the notes, the link is made.
    assert witness(quote, {"blk_l": "План этажа", "blk_r": notes}, page_text=notes) == ("blk_r",)


def test_w_a_quotation_the_page_repeats_or_does_not_hold_is_not_asked_of_the_witness():
    assert witness(QUOTE, TEXTS, page_text=PAGE_TEXT + "\n" + QUOTE) == (), "twice on the page"
    assert witness(QUOTE, TEXTS, page_text="Итого по разделу") == (), "not on the page at all"
    assert witness(QUOTE, TEXTS, page_text=PAGE_TEXT + "\n" + QUOTE + "а") == ("blk_r",), "a longer word is not an occurrence"
    assert witness(QUOTE, TEXTS, page_text="Огнестойкость узла\nне менее R30") == ("blk_r",), "the break between two lines is no break"
    # Occurrences overlap: «а а а» holds «а а» twice.
    readings = Readings({"b": "x"}, (), {1: "а а а", 2: "у"})
    assert readings.occurrences(1, "а а") == 2 and readings.occurrences(2, "а а") == 0
    assert readings.occurrences(3, "а а") is None, "a page whose text is not known"


def test_w_the_page_of_the_evidence_decides_not_another_pages_text():
    spans = [EvidenceSpan(1, 100, 140, QUOTE)]
    assert link_evidence(spans, lines={1: [WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT], block_texts=TEXTS,
                         page_texts={1: PAGE_TEXT, 2: QUOTE + " " + QUOTE}) == ("blk_r",)
    assert link_evidence(spans, lines={1: [WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT], block_texts=TEXTS, page_texts={2: PAGE_TEXT}) == ()


@pytest.mark.parametrize(
    ("quote", "true_reading", "other", "page"),
    [
        pytest.param("Бетон класса B25", "Бетон класса В25", "Бетон класса B25 по прочности", "Бетон класса B25", id="p4-designation-lookalike"),
        pytest.param("шаг 200 мм", "шаг 2OO мм", "Арматура Ø12 А500С шаг 200 мм", "шаг 200 мм", id="p4-letter-o-for-zero"),
        pytest.param("Кладка из керамического кирпича марки", "Кладка изкерамического кирпича марки",
                     "Кладка из керамического кирпича марки КР-р-по", "Кладка из керамического кирпича марки", id="p4-space-lost"),
        pytest.param("отм. +3.000 пол 1 этажа", "отм. +3.ООО пол I этажа", "отм. +3.000 пол 1 этажа",
                     "отм. +3.000 пол 1 этажа", id="p4-two-short-words"),
        pytest.param("отм. -3.000 низ плиты", "отм. -З.ООО низ плиты", "отм. +3.000 низ плиты", "отм. -3.000 низ плиты",
                     id="p4-sign-lost-opposite-level"),
    ],
)
def test_w_m2_p4_a_true_block_read_with_an_error_no_flag_names_is_not_robbed_by_the_neighbour_that_holds_the_text_exactly(
    quote, true_reading, other, page
):
    # The evidence stands in blk_l (its reading is damaged); blk_r holds the same words exactly or with another sign. Whatever
    # else happens the answer is not the neighbour. (It is nothing: the damaged reading is a near copy of the quotation, and where
    # the neighbour holds the text exactly the quotation is not unique across the two readings -- the rule abstains.)
    got = witness(quote, {"blk_l": true_reading, "blk_r": other}, page_text=page)
    assert "blk_r" not in got
    assert got == ()


def test_w_p5_rows_that_differ_in_two_words_of_four_give_no_wrong_link_when_the_reading_is_damaged():
    # The judge's probe2 in miniature: a schedule of 12 rows, the row's phrase in two cells of it (the quotation is the first
    # occurrence, the left cell); the left column's reading is damaged by a letter short in a third of its words.
    from tests.support.finding_block_proof import degrade

    words = [f"{head}{tail}" for head, tail in zip(
        ["балеми", "нопуры", "самату", "фехица", "чешаю", "бадуго", "жизока", "лемино", "пурысат", "уфехиц", "цачеша", "юбавег"],
        ["ново", "тика", "мала", "жера", "быка", "шега", "реза", "сока", "дума", "лито", "фара", "зель"],
    )]
    lines, quotes, start = [], [], 0
    top, leading = 60.0, 13.0
    for n, word in enumerate(words, start=1):
        y = top + n * leading
        phrase = f"Не {word}, п. {n}"
        text = f"Поз. {n} {phrase} {phrase} {n} шт."
        lines.append(TextLine(1, start, start + len(text), 56.0, y, 540.0, y + 10.0))
        quotes.append((start + len(f"Поз. {n} "), phrase))
        start += len(text) + 1
    y0, y1 = (top + leading) / 800.0 - 0.01, (top + len(words) * leading + 10.0) / 800.0 + 0.01
    blocks = [box("pos", 56 / 600, y0, 140 / 600, y1), box("left", 148 / 600, y0, 322 / 600, y1),
              box("right", 328 / 600, y0, 495 / 600, y1), box("qty", 498 / 600, y0, 560 / 600, y1)]
    column = lambda make: "\n".join(make(n, w) for n, w in enumerate(words, start=1))  # noqa: E731
    page_text = column(lambda n, w: f"Поз. {n} Не {w}, п. {n} Не {w}, п. {n} {n} шт.")
    for rate in (0.0, 0.1, 0.3):
        texts = {"pos": column(lambda n, w: f"Поз. {n}"), "left": degrade("left", column(lambda n, w: f"Не {w}, п. {n}"), rate, flaggable=False),
                 "right": column(lambda n, w: f"Не {w}, п. {n}"), "qty": column(lambda n, w: f"{n} шт.")}
        for first, quote in quotes:
            got = link_evidence([EvidenceSpan(1, first, first + len(quote), quote)], lines={1: lines}, pages=PAGE, blocks=blocks,
                                block_texts=texts, page_texts={1: page_text})
            assert got == (), (rate, quote, got)


def test_w_the_witness_is_never_asked_when_the_caller_hands_over_readings_and_the_readings_cannot_speak():
    spans = [EvidenceSpan(1, 100, 140, QUOTE)]
    kwargs = dict(lines={1: [WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT])
    assert link_evidence(spans, readings=Readings(TEXTS, (), {1: PAGE_TEXT}), **kwargs) == ("blk_r",)
    assert link_evidence(spans, readings=Readings(TEXTS, (), None), **kwargs) == ()
    assert link_evidence(spans, readings=Readings({}, (), {1: PAGE_TEXT}), **kwargs) == ()
    assert link_evidence(spans, readings=Readings(None, (), {1: PAGE_TEXT}), **kwargs) == ()
    with pytest.raises(ValueError):
        link_evidence(spans, readings=Readings(TEXTS, (), {1: PAGE_TEXT}), block_texts=TEXTS, **kwargs)
    # One Readings serves many calls, and a call that builds its own from the three arguments gives the same answer.
    shared = Readings(TEXTS, (), {1: PAGE_TEXT})
    assert [link_evidence(spans, readings=shared, **kwargs) for _ in range(3)] == [("blk_r",)] * 3


def test_w_l3_the_thresholds_are_pinned_at_their_edges():
    # The near-copy budget: one miss in 4..7 words, two in 8..11 (a quarter, rounded down).
    base = "один два три четыре пять шесть семь восемь девять десять одиннадцать"
    for count, allowed in ((4, 1), (5, 1), (7, 1), (8, 2), (11, 2)):
        quotation = sk(" ".join(base.split()[:count]))
        for misses in range(0, allowed + 2):
            damaged = base.split()[:count]
            for at in range(misses):
                damaged[at] = f"х{at}"
            assert _near_copy(quotation, sk(" ".join(damaged))) is (misses <= allowed), (count, misses)
    # A word is the same word with one letter wrong only from four letters on both sides.
    assert _close("слов", "слав") and not _close("сло", "сла") and not _close("слов", "сло")
    # A block of exactly COVERAGE of the line's height crosses it (the boundary is inclusive).
    height = 0.015
    half = box("blk_half", 0.5, 0.2, 1.0, 0.25 + height * 0.5)
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_half": RIGHT_TEXT}, blocks=(LEFT, half)) == ("blk_half",)
    assert fold_text("а-\nб") == "аб" and fold_text("а‐\nб") == "аб" and fold_text("а‑\n  б") == "аб" and fold_text("а- \nб") == "аб"
