"""`UI-PARITY-C6`: the finding to portal block relation, as a pure function over three saved documents.

Every case states the geometry in points on a 600 x 800 page (so 0.1 of the width is 60 points and 0.1 of the
height 80) and the blocks as fractions of the page; the expected ids are literals, never read back from the
function under test.
"""

from __future__ import annotations

from auditmanager.analysis.geometry import (
    EvidenceSpan,
    PortalBox,
    TextLine,
    link_evidence,
    linkable_pages,
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


def test_a_block_covering_most_of_the_evidence_holds_it():
    # The block ends at x = 0.3: of the line's 0.1667..0.3333 it covers 0.1333 / 0.1667 = 0.8.
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [box("blk_a", 0.0, 0.0, 0.3, 1.0)]) == ("blk_a",)


def test_a_block_covering_less_than_half_of_the_evidence_does_not_hold_it():
    # The block ends at x = 0.24: it covers 0.0733 / 0.1667 = 0.44.
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [box("blk_a", 0.0, 0.0, 0.24, 1.0)]) == ()


def test_exactly_half_holds_it_the_threshold_is_at_least_half():
    # A 1024 pt wide page makes the arithmetic exact: the line is x 128..256 = 0.125..0.25, the block ends at 0.1875.
    line = TextLine(1, 0, 20, 128.0, 90.0, 256.0, 102.0)
    block = box("blk_a", 0.0, 0.0, 0.1875, 1.0)
    assert link([EvidenceSpan(1, 0, 20)], [line], [block], pages={1: (1024.0, 800.0)}) == ("blk_a",)
    just_less = box("blk_a", 0.0, 0.0, 0.1874, 1.0)
    assert link([EvidenceSpan(1, 0, 20)], [line], [just_less], pages={1: (1024.0, 800.0)}) == ()


def test_a_line_across_two_columns_is_cut_at_the_evidence_not_taken_whole():
    left, right = box("blk_l", 0.0, 0.2, 0.5, 0.3), box("blk_r", 0.5, 0.2, 1.0, 0.3)
    # Characters 100..120 are the first half of the line: x 50..300 = 0.0833..0.5, the left column.
    assert link([EvidenceSpan(1, 100, 120)], [WIDE], [left, right]) == ("blk_l",)
    # Characters 125..140 are the last of it: x 362.5..550 = 0.6042..0.9167, the right column.
    assert link([EvidenceSpan(1, 125, 140)], [WIDE], [left, right]) == ("blk_r",)


def test_an_evidence_over_the_whole_of_a_line_is_held_by_every_block_covering_half_of_it():
    # The line is x 0.0833..0.9167; the left block covers up to 0.6 (0.62 of it), the right one from 0.4 (0.62 of it).
    left, right = box("blk_l", 0.0, 0.2, 0.6, 0.3), box("blk_r", 0.4, 0.2, 1.0, 0.3)
    assert link([EvidenceSpan(1, 100, 140)], [WIDE], [left, right]) == ("blk_l", "blk_r")


def test_a_block_inside_another_block_holds_the_evidence_with_it():
    drawing, table = box("blk_d", 0.0, 0.0, 1.0, 1.0), box("blk_t", 0.1, 0.1, 0.4, 0.2)
    assert link([EvidenceSpan(1, 0, 20)], [LINE], [drawing, table]) == ("blk_d", "blk_t")


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
