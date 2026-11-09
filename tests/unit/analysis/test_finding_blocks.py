"""`UI-PARITY-C6`: the finding to portal block relation, as a pure function over three saved documents.

Every case states the geometry in points on a 600 x 800 page (so 0.1 of the width is 60 points and 0.1 of the
height 80) and the blocks as fractions of the page; the expected ids are literals, never read back from the
function under test.

The rule claims containment and nothing more (module docstring): a block holds the evidence of a line only when it extends over
the line's whole width, because where along a line the evidence stands is not in the data. The cases that fail on the
proportional cut this rule had before are marked ``F1`` / ``F2`` (`D-353`, judge J3 2026-11-09). The cases of the second witness
(a line that no block holds, a choice among the blocks it crosses by their recognised text, `D-450`) are marked ``W``.
"""

from __future__ import annotations

from auditmanager.analysis.geometry import (
    EvidenceSpan,
    PortalBox,
    TextLine,
    link_evidence,
    linkable_pages,
)
from auditmanager.analysis.geometry.finding_blocks import WITNESS_MIN_CHARACTERS, fold_text

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


# --- the second witness (`D-450`) --------------------------------------------------------------------------------------
#
# The line is WIDE: x 50..550 on the 600 pt page, 0.0833..0.9167 across, y 0.25..0.265 down. Two column blocks stand at either side
# of x = 0.5; neither holds the line (the evidence is somewhere on it), both of them cross it.

LEFT = box("blk_l", 0.0, 0.2, 0.5, 0.3)
RIGHT = box("blk_r", 0.5, 0.2, 1.0, 0.3)
QUOTE = "Огнестойкость узла не менее R30"
RIGHT_TEXT = "Огнестойкость узла не менее R30."
LEFT_TEXT = "Итого по разделу"


def witness(quote, texts, blocks=(LEFT, RIGHT), *, span=(100, 140), line=WIDE, **options):
    spans = [EvidenceSpan(1, span[0], span[1], quote)]
    return link_evidence(spans, lines={1: [line], 2: []}, pages=PAGE, blocks=list(blocks), block_texts=texts, **options)


def test_w_a_line_across_two_blocks_is_linked_to_the_one_whose_text_contains_the_quotation():
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}) == ("blk_r",)
    assert witness(QUOTE, {"blk_l": RIGHT_TEXT, "blk_r": LEFT_TEXT}) == ("blk_l",)


def test_w_without_the_recognised_text_or_the_quotation_the_geometry_decides_alone_as_before():
    texts = {"blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}
    assert witness(QUOTE, None) == ()
    assert witness(QUOTE, {}) == ()
    assert witness(None, texts) == ()
    assert witness("", texts) == ()
    # And the call that names neither is the call of before the witness: the same answer on every geometry case above.
    assert link_evidence([EvidenceSpan(1, 100, 140)], lines={1: [WIDE]}, pages=PAGE, blocks=[LEFT, RIGHT]) == ()


def test_w_two_blocks_that_both_contain_the_quotation_make_it_ambiguous_and_no_link_is_made():
    assert witness(QUOTE, {"blk_l": RIGHT_TEXT, "blk_r": "Здесь " + RIGHT_TEXT}) == ()


def test_w_no_block_that_contains_the_quotation_means_no_link_not_the_nearest_or_the_most_similar():
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": "Огнестойкость узла не менее R45"}) == ()
    # Most of the words are in the right block (all but the last), and the quotation is still not in it.
    assert witness(QUOTE, {"blk_l": LEFT_TEXT, "blk_r": "Огнестойкость узла не менее"}) == ()


def test_w_only_a_block_with_text_can_match_a_block_without_text_neither_matches_nor_vetoes():
    assert witness(QUOTE, {"blk_r": RIGHT_TEXT}) == ("blk_r",)
    assert witness(QUOTE, {"blk_r": ""}) == ()
    assert witness(QUOTE, {"blk_l": None, "blk_r": RIGHT_TEXT}) == ("blk_r",)


def test_w_the_comparison_folds_case_yo_whitespace_hyphenation_and_punctuation():
    quote = "Ёлка у ПОДЪЕЗДА, строительство-дома не менее R30"
    text = "елка   у\nподъезда  строи-\nтельство дома  не менее r30!"
    assert witness(quote, {"blk_l": LEFT_TEXT, "blk_r": text}) == ("blk_r",)
    assert witness("Строительство дома", {"blk_r": "строи\u00adтельство дома"}) == ("blk_r",)
    assert witness("Строительство дома", {"blk_r": "строи‐\nтельство дома"}) == ("blk_r",)


def test_w_the_quotation_must_be_a_run_of_whole_words_of_the_text_not_a_piece_of_a_word():
    assert witness("узла не менее R3", {"blk_r": RIGHT_TEXT}) == ()
    assert witness("гнестойкость узла не", {"blk_r": RIGHT_TEXT}) == ()
    assert witness("узла менее R30 не", {"blk_r": RIGHT_TEXT}) == (), "the words in another order are not the quotation"


def test_w_a_quotation_shorter_than_the_minimum_is_not_asked_about_the_witness():
    assert fold_text("R30 шт.") == "r30 шт" and len(fold_text("R30 шт.")) < WITNESS_MIN_CHARACTERS
    assert witness("R30 шт.", {"blk_r": "Огнестойкость R30 шт."}) == ()
    assert witness("R30 шт.", {"blk_r": "Огнестойкость R30 шт."}, witness_min_characters=1) == ("blk_r",)
    assert len(fold_text(QUOTE)) >= WITNESS_MIN_CHARACTERS
    # The minimum counts the folded text, spaces included: "a b c d e f g h" is 15 characters.
    assert witness("a.b.c.d.e.f.g.h", {"blk_r": "a b c d e f g h"}, witness_min_characters=15) == ("blk_r",)
    assert witness("a.b.c.d.e.f.g.h", {"blk_r": "a b c d e f g h"}, witness_min_characters=16) == ()


def test_w_a_block_the_line_does_not_cross_is_never_a_candidate_whatever_its_text_says():
    above = box("blk_up", 0.0, 0.0, 1.0, 0.1)
    other_page = box("blk_p2", 0.0, 0.2, 1.0, 0.3, page=2)
    texts = {"blk_up": RIGHT_TEXT, "blk_p2": RIGHT_TEXT, "blk_l": LEFT_TEXT, "blk_r": "Другой текст"}
    assert witness(QUOTE, texts, blocks=(above, other_page, LEFT, RIGHT)) == ()


def test_w_a_block_that_covers_less_than_half_of_the_lines_height_is_not_crossed():
    # The line is y 0.25..0.265; this block ends at 0.2575, a half of the height short of it.
    short = box("blk_short", 0.5, 0.2, 1.0, 0.2575 - 0.0001)
    assert witness(QUOTE, {"blk_short": RIGHT_TEXT}, blocks=(LEFT, short)) == ()
    enough = box("blk_enough", 0.5, 0.2, 1.0, 0.2575 + 0.0001)
    assert witness(QUOTE, {"blk_enough": RIGHT_TEXT}, blocks=(LEFT, enough)) == ("blk_enough",)


def test_w_a_block_that_only_grazes_the_end_of_the_line_is_not_crossed():
    # The line ends at x = 0.9167: a block from 0.9 reaches 0.0167 into it (more than the tolerance), one from 0.915 only 0.0017.
    assert witness(QUOTE, {"blk_g": RIGHT_TEXT}, blocks=(box("blk_g", 0.9, 0.2, 1.0, 0.3),)) == ("blk_g",)
    assert witness(QUOTE, {"blk_g": RIGHT_TEXT}, blocks=(box("blk_g", 0.915, 0.2, 1.0, 0.3),)) == ()


def test_w_a_line_a_block_holds_is_never_given_to_the_witness_geometry_is_not_second_guessed_by_a_reading():
    holder = box("blk_all", 0.0, 0.2, 1.0, 0.3)
    texts = {"blk_all": "Здесь нет цитаты", "blk_l": LEFT_TEXT, "blk_r": RIGHT_TEXT}
    assert witness(QUOTE, texts, blocks=(holder, LEFT, RIGHT)) == ("blk_all",)


def test_w_the_witness_does_not_change_what_a_block_that_holds_a_line_gives_the_other_lines_of_the_evidence():
    # Two lines, the evidence spans both: the first is held by the wide block, the second crosses the two columns.
    first = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 212.0)
    second = TextLine(1, 141, 181, 50.0, 400.0, 550.0, 412.0)
    holder = box("blk_top", 0.0, 0.2, 1.0, 0.3)
    left, right = box("blk_l2", 0.0, 0.45, 0.5, 0.55), box("blk_r2", 0.5, 0.45, 1.0, 0.55)
    spans = [EvidenceSpan(1, 100, 181, QUOTE + "\n" + QUOTE)]
    texts = {"blk_top": "x", "blk_l2": "y", "blk_r2": QUOTE + " " + QUOTE}
    found = link_evidence(spans, lines={1: [first, second]}, pages=PAGE, blocks=[holder, left, right], block_texts=texts)
    assert found == ("blk_top", "blk_r2")


def test_w_a_quotation_over_two_lines_is_looked_for_whole_in_the_blocks_one_line_of_it_crosses():
    first = TextLine(1, 100, 140, 50.0, 200.0, 550.0, 212.0)
    second = TextLine(1, 141, 181, 50.0, 214.0, 550.0, 226.0)
    both = box("blk_both", 0.5, 0.2, 1.0, 0.3)
    quote = "Огнестойкость узла\nне менее R30 при пожаре"
    spans = [EvidenceSpan(1, 100, 181, quote)]

    def found(texts):
        return link_evidence(spans, lines={1: [first, second]}, pages=PAGE, blocks=[LEFT, both], block_texts=texts)

    assert found({"blk_both": "Огнестойкость узла не менее R30 при пожаре"}) == ("blk_both",)
    assert found({"blk_both": "Огнестойкость узла"}) == (), "half of the quotation is not the quotation"


def test_w_an_evidence_on_a_page_that_is_not_linkable_or_is_shifted_is_not_given_to_the_witness_either():
    texts = {"blk_r": RIGHT_TEXT}
    assert link_evidence([EvidenceSpan(1, 100, 140, QUOTE)], lines={1: [WIDE]}, pages={2: (600.0, 800.0)},
                         blocks=[LEFT, RIGHT], block_texts=texts) == ()
    above = TextLine(1, 0, 20, 100.0, -31.7, 200.0, -19.7)
    assert link_evidence([EvidenceSpan(1, 100, 140, QUOTE)], lines={1: [above, WIDE]}, pages=PAGE,
                         blocks=[LEFT, RIGHT], block_texts=texts) == ()


def test_w_the_witness_links_come_in_the_portal_order_and_join_the_geometry_links_of_other_evidence():
    held_line = TextLine(1, 0, 20, 100.0, 90.0, 200.0, 102.0)  # inside AROUND_LINE
    spans = [EvidenceSpan(1, 100, 140, QUOTE), EvidenceSpan(1, 0, 20, "что угодно")]
    blocks = [LEFT, AROUND_LINE, RIGHT]
    found = link_evidence(spans, lines={1: [WIDE, held_line]}, pages=PAGE, blocks=blocks, block_texts={"blk_r": RIGHT_TEXT})
    assert found == ("blk_a", "blk_r"), "the order of the blocks list (blk_l, blk_a, blk_r), not the order of the evidence"


def test_w_fold_text_is_the_words_in_lower_case_with_single_spaces():
    assert fold_text("  Ёж,\tЁЛКА!\n№ 5 ") == "еж елка no 5"
    assert fold_text("строи-\n  тельство") == "строительство"
    assert fold_text("светло-серый") == "светло серый", "a hyphen inside a line is a separator, not a break"
    assert fold_text("") == fold_text(" ,.;") == ""
