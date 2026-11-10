"""The measurement scenarios of the second witness CAN produce a wrong link, and say which guard stops it (D-649).

`tests/support/witness_scenarios.py` builds five PDFs with portal blocks and readings authored the way a portal fails and calls the
shipped rule once per subset of its guards removed. A scenario whose every variant links 0 wrongly proves nothing, so this module
pins, per kind of case: the shipped rule's links / wrong / missed, and the smallest sets of guards whose removal links wrongly. Nothing
here needs a database: the PDF alone gives the text layer, the line boxes and the glyphs the links are held against; the stand run
(`python -m tests.support.measure_finding_blocks`) reads the same counts from the stored documents and says whether they agree.

The shipped rule links wrongly in the kinds that this module pins as ``SHIPPED`` -- the residual of the judge's A1 (`D-629`) -- and
nowhere else: when the rule is hardened against them, those expectations are to change with it, in the same commit.
"""

from __future__ import annotations

from functools import lru_cache

import pytest

from auditmanager.analysis.geometry import finding_blocks as rule_module
from auditmanager.analysis.geometry.finding_blocks import Readings, fold_text
from auditmanager.analysis.recognised.artifact import recognised_entries
from auditmanager.analysis.recognised.portal import read_portal
from tests.support import witness_scenarios as w
from tests.support.finding_block_proof import PdfOracle
from tests.support.xy_cut_blocks import block_text

JUDGE_CLASSES = ("skipped_line", "word_swapped_of_3", "two_words_of_5")      # what the near-copy veto does not see and no flag names
FLAGGED_CAUGHT = ("latin_in_word",)                                            # a flag names it, and so does the near-copy veto
FLAG_ONLY = ("garbled_mixed_script",)                                          # only a flag names it
NEAR_COPY_ONLY = ("latin_designation", "letter_o_for_zero", "digit_for_letter", "lost_space", "sign_dropped", "two_short_words")


@lru_cache(maxsize=None)
def sheet(name: str) -> w.Sheet:
    return w.SCENARIOS[name]()


@lru_cache(maxsize=None)
def table(name: str) -> dict:
    return w.evaluate(sheet(name))


def shipped(name: str, kind: str) -> dict:
    return table(name)[w.SHIPPED]["by_kind"][kind]


def minimal(name: str, kind: str) -> list[tuple[str, ...]]:
    return w.minimal_failing_sets(table(name), kind)


# -- the sheets are what they say ---------------------------------------------------------------------


@pytest.mark.parametrize("name", list(w.SCENARIOS))
def test_every_sheet_is_a_pdf_whose_quotations_blocks_and_lines_lie_on_their_pages(name):
    inputs = w.inputs_of(sheet(name))
    try:
        assert inputs.evidence and inputs.blocks and inputs.lines
        for line in inputs.lines:
            width, height = inputs.sizes[line.page_number]
            assert 0 <= line.x0 and line.x1 <= width - 10 and 0 <= line.y0 and line.y1 <= height, "a line outside the page"
        for block in inputs.blocks:
            assert all(0.0 <= value <= 1.0 for value in block.bbox_norm), block
        # every quotation is placed by the glyph oracle: an unplaced one would hide a wrong link from the proof
        figures = w.run_variant(inputs)
        assert figures["links_by_geometry"].get("unplaced", 0) == 0
        for facts in inputs.evidence.values():
            assert inputs.oracle.quote_boxes(facts[0].page_number, facts[0].char_start, facts[0].quote), facts[0].quote
    finally:
        inputs.pdf_oracle.close()


@pytest.mark.parametrize("name", list(w.SCENARIOS))
def test_every_quotation_stands_inside_the_blocks_row_span_of_its_own_page(name):
    inputs = w.inputs_of(sheet(name))
    try:
        for uid, facts in inputs.evidence.items():
            line = next(l for l in inputs.lines if l.page_number == facts[0].page_number and l.char_start <= facts[0].char_start < l.char_end)
            page_blocks = [b for b in inputs.blocks if b.page_number == facts[0].page_number]
            height = inputs.sizes[line.page_number][1]
            assert any(b.bbox_norm[1] * height <= line.y0 and line.y1 <= b.bbox_norm[3] * height for b in page_blocks), uid
    finally:
        inputs.pdf_oracle.close()


def occurrences(name: str) -> dict[str, set[int]]:
    inputs = w.inputs_of(sheet(name))
    try:
        readings = Readings({"x": "x"}, (), inputs.layer)
        found: dict[str, set[int]] = {}
        for uid, facts in inputs.evidence.items():
            kind = w.label_of(inputs.labels[uid])
            found.setdefault(kind, set()).add(readings.occurrences(facts[0].page_number, fold_text(facts[0].quote)))
        return found
    finally:
        inputs.pdf_oracle.close()


def test_the_quotation_occurs_twice_where_the_cell_is_repeated_and_once_where_the_copy_is_hidden_or_absent():
    image = occurrences("witness_image")
    assert image == {"repeat": {2}, "wrapped": {1}, "bleed": {1}, "clean": {1}}
    assert all(counts == {2} for counts in occurrences("witness_schedule").values())
    assert all(counts == {2} for counts in occurrences("witness_damage").values())
    assert all(counts == {1} for counts in occurrences("witness_a1").values()), "scenario 4 is the layout where the text layer holds it once"
    assert all(counts == {1} for counts in occurrences("witness_gutter").values())


def test_the_readings_marked_exact_are_what_the_pdfs_own_characters_in_the_block_read():
    for name, page_number, kinds in (("witness_image", 4, {"text"}), ("witness_schedule", 1, {"text"}), ("witness_gutter", 1, {"text"})):
        built = sheet(name)
        oracle = PdfOracle(built.pdf)
        try:
            boxes = [[] for _ in oracle.layer]
            chosen = [b for b in built.blocks if b.page == page_number and b.kind in kinds]
            layout = oracle.layer[page_number - 1]
            boxes[page_number - 1] = [
                (b.box[0] / layout.width_pt, b.box[1] / layout.height_pt, b.box[2] / layout.width_pt, b.box[3] / layout.height_pt)
                for b in chosen
            ]
            read = block_text(built.pdf, boxes)[page_number - 1]
        finally:
            oracle.close()
        assert read == [b.reading for b in chosen], name


@pytest.mark.parametrize("name", list(w.SCENARIOS))
def test_the_portal_export_of_a_sheet_keeps_every_reading_as_authored_and_has_a_description_for_an_image(name):
    built = sheet(name)
    oracle = PdfOracle(built.pdf)
    try:
        markdown, block_list = w.portal_files(built, name, oracle.layer)
        pages = len(oracle.layer)
    finally:
        oracle.close()
    entries = recognised_entries(read_portal(markdown, block_list, page_count=pages))
    texts = sorted((e["page_number"], e["text"]) for e in entries if e["kind"] == "recognised_text")
    assert texts == sorted((b.page, b.reading) for b in built.blocks if b.kind == "text")
    assert sum(1 for e in entries if e["kind"] == "portal_description") == sum(1 for b in built.blocks if b.kind == "image")


# -- scenario 1: an image block over the line ------------------------------------------------------------


def test_scenario_1_the_shipped_rule_links_nothing_and_wrongly_nothing_and_misses_every_callout_of_the_image():
    for kind in ("repeat", "wrapped", "bleed", "clean"):
        assert shipped("witness_image", kind) == {"findings": 30, "with_a_block": 0, "links": 0, "wrong": 0, "marginal": 0, "missed": 30}


def test_scenario_1_an_image_block_that_cannot_be_read_is_what_keeps_a_repeated_phrase_out_and_a_repeated_phrase_is_what_a_removed_gate_lets_in():
    assert minimal("witness_image", "repeat") == [("unique", "reading")], "two guards stand between the repeat and a wrong link"
    assert minimal("witness_image", "wrapped") == [("reading",)], "the text layer's order hides the wrapped copy from the unique-quotation gate"
    assert minimal("witness_image", "bleed") == [("reading",)]
    assert minimal("witness_image", "clean") == [], "the control: nobody's reading holds the quotation"


# -- scenario 2: a schedule whose rows differ in two words of four -----------------------------------------


def test_scenario_2_the_shipped_rule_asks_nothing_of_a_phrase_the_schedule_repeats():
    for level in w.DEGRADE_LEVELS:
        assert shipped("witness_schedule", level) == {"findings": 30, "with_a_block": 0, "links": 0, "wrong": 0, "marginal": 0, "missed": 30}


def test_scenario_2_without_the_unique_quotation_gate_a_damaged_left_reading_hands_the_link_to_the_repeating_cell():
    assert minimal("witness_schedule", "d00") == [], "an exact reading: two cells hold the phrase, so there is no single match"
    for level in ("d10", "d30", "d50"):
        assert minimal("witness_schedule", level) == [("unique",)], level
    wrong = {level: table("witness_schedule")["unique"]["by_kind"][level]["wrong"] for level in ("d10", "d30", "d50")}
    assert wrong["d10"] >= 1 and wrong["d30"] >= wrong["d10"] and wrong["d50"] >= wrong["d30"], wrong
    # a flagged damage makes the whole block's reading doubtful, which the near-copy veto does not need to see
    assert minimal("witness_schedule", "f30") == [("unique", "flags", "near_copy"), ("unique", "reading", "near_copy")]


# -- scenario 3: the damage a portal makes -------------------------------------------------------------------


def test_scenario_3_the_shipped_rule_links_nothing_on_repeated_cells_whatever_the_damage():
    for kind in (*w.PORTAL_DAMAGE, w.SPARSE_FLAGGED.name):
        assert shipped("witness_damage", kind) == {"findings": 24, "with_a_block": 0, "links": 0, "wrong": 0, "marginal": 0, "missed": 24}


def test_scenario_3_every_damage_class_has_a_set_of_guards_the_next_line_of_defence_it_meets():
    for kind in NEAR_COPY_ONLY:
        assert minimal("witness_damage", kind) == [("unique", "near_copy")], kind
    for kind in (*FLAGGED_CAUGHT, w.SPARSE_FLAGGED.name):
        assert minimal("witness_damage", kind) == [("unique", "flags", "near_copy"), ("unique", "reading", "near_copy")], kind
    for kind in FLAG_ONLY:
        assert minimal("witness_damage", kind) == [("unique", "flags"), ("unique", "reading")], kind


# -- scenario 4: the judge's A1 ------------------------------------------------------------------------------


def test_scenario_4_the_shipped_rule_links_wrongly_exactly_where_the_reading_error_is_one_nothing_names_and_the_quotation_is_held_by_the_neighbour():
    expected_wrong = {f"{c}/DB" for c in JUDGE_CLASSES} | {f"wrapped:{c}/D-" for c in JUDGE_CLASSES}
    found = {k for k, row in table("witness_a1")[w.SHIPPED]["by_kind"].items() if row["wrong"]}
    assert found == expected_wrong
    for kind in expected_wrong:
        assert shipped("witness_a1", kind)["wrong"] == shipped("witness_a1", kind)["findings"] == 10, "every row, not some of them"
        assert minimal("witness_a1", kind) == [()], kind


def test_scenario_4_it_takes_both_faults_or_a_copy_the_text_layer_hides_and_a_reading_error_alone_or_the_neighbour_alone_gives_no_link():
    for cls in w.DAMAGE_CLASSES:
        assert shipped("witness_a1", f"{cls}/D-")["links"] == 0, "a damaged left reading and nobody holding the quotation"
        assert shipped("witness_a1", f"{cls}/-B")["links"] == 0, "the exact left reading and the bled one: two matches"
        assert shipped("witness_a1", f"{cls}/--")["wrong"] == 0
    # control: an exact reading with nothing else holding the quotation is linked, and linked right
    for cls in ("lost_space", "sign_dropped", "skipped_line", "word_swapped_of_3"):
        assert shipped("witness_a1", f"{cls}/--") == {"findings": 10, "with_a_block": 10, "links": 10, "wrong": 0, "marginal": 0, "missed": 0}


def test_scenario_4_a_damage_the_near_copy_veto_sees_or_a_flag_names_is_stopped_and_the_guard_that_stops_it_is_the_one_that_sees_it():
    for cls in NEAR_COPY_ONLY:
        for kind in (f"{cls}/DB", f"wrapped:{cls}/D-"):
            assert minimal("witness_a1", kind) == [("near_copy",)], kind
    for kind in ("latin_in_word/DB", "wrapped:latin_in_word/D-"):
        assert minimal("witness_a1", kind) == [("flags", "near_copy"), ("reading", "near_copy")], kind
    for kind in ("garbled_mixed_script/DB", "wrapped:garbled_mixed_script/D-"):
        assert minimal("witness_a1", kind) == [("flags",), ("reading",)], kind


def test_scenario_4_a_copy_the_text_layers_order_hides_costs_the_link_even_when_the_reading_is_exact():
    for cls in ("lost_space", "skipped_line"):
        assert shipped("witness_a1", f"wrapped:{cls}/--")["links"] == 0 and shipped("witness_a1", f"wrapped:{cls}/--")["missed"] == 10


# -- scenario 5: gutters, after D-626 --------------------------------------------------------------------------


def test_scenario_5_the_shipped_rule_links_a_label_across_a_gutter_of_up_to_two_line_heights_and_abstains_beyond_it():
    for width, links in ((1.0, 24), (1.9, 24), (2.1, 0), (3.0, 0), (6.0, 0)):
        row = shipped("witness_gutter", f"inside-g{width:g}")
        assert (row["links"], row["wrong"]) == (links, 0), width
        assert row["missed"] == 24 - links
        assert minimal("witness_gutter", f"inside-g{width:g}") == [], "a label inside its own block is never linked wrongly"


def test_scenario_5_a_cell_the_portal_did_not_box_is_linked_to_its_neighbour_only_when_the_unboxed_stretch_guard_is_removed():
    for shape in ("short", "medium", "long"):
        assert shipped("witness_gutter", f"unboxed-{shape}")["links"] == 0
        assert minimal("witness_gutter", f"unboxed-{shape}") == [("gap",)]
    assert table("witness_gutter")["gap"]["by_kind"]["unboxed-long"]["wrong"] == 24


def test_scenario_5_the_judges_a2b_is_a_wrong_link_in_the_unit_of_four_mean_characters_and_none_in_two_heights():
    assert shipped("witness_gutter", "a2b")["wrong"] == 0
    assert table("witness_gutter")[w.OLD_UNIT]["by_kind"]["a2b"]["wrong"] == 24, "the limit before D-626 lets the label through"
    assert minimal("witness_gutter", "a2b") == [("gap",)]
    # and the unit that failed is not a change of the other kinds
    assert all(table("witness_gutter")[w.OLD_UNIT]["by_kind"][k]["wrong"] == 0 for k in w.kinds_of(table("witness_gutter")) if k != "a2b")


# -- the whole: every guard is, somewhere, the only thing between the rule and a wrong link ----------------------


def test_every_guard_of_the_rule_is_the_only_one_between_some_kind_of_case_and_a_wrong_link():
    alone: dict[str, list[str]] = {guard: [] for guard in w.GUARDS}
    for name in w.SCENARIOS:
        for kind in w.kinds_of(table(name)):
            for guard in w.GUARDS:
                if minimal(name, kind) == [(guard,)] or (guard,) in minimal(name, kind):
                    alone[guard].append(f"{name}:{kind}")
    assert all(alone.values()), alone


def test_the_shipped_rule_links_wrongly_nowhere_but_in_the_a1_residual():
    for name in w.SCENARIOS:
        wrong = {k: row["wrong"] for k, row in table(name)[w.SHIPPED]["by_kind"].items() if row["wrong"]}
        assert not wrong or name == "witness_a1", (name, wrong)


# -- the helpers ---------------------------------------------------------------------------------------------


def fake_row(wrong: int, kind: str = "k") -> dict:
    return {"all": {"wrong": wrong}, "by_kind": {kind: {"wrong": wrong}}}


def test_minimal_failing_sets_keeps_only_the_sets_without_a_failing_subset():
    failing = {w.SHIPPED: fake_row(0), "unique": fake_row(0), "gap": fake_row(0), "unique+gap": fake_row(1), "near_copy": fake_row(1), "near_copy+gap": fake_row(2), w.OLD_UNIT: fake_row(9)}
    assert w.minimal_failing_sets(failing, "k") == [("near_copy",), ("unique", "gap")]
    assert w.minimal_failing_sets({**failing, w.SHIPPED: fake_row(1)}, "k") == [()]
    assert w.minimal_failing_sets({w.SHIPPED: fake_row(0), w.OLD_UNIT: fake_row(9)}, "k") == []
    assert w.minimal_failing_sets(failing) == [("near_copy",), ("unique", "gap")], "all findings when no kind is named"


def test_without_patches_the_named_guards_for_the_block_only_and_refuses_a_name_it_does_not_know():
    near, occurrences_, trusted = rule_module._near_copy, Readings.occurrences, Readings.trusted
    with w.without(("near_copy", "unique", "reading")):
        assert rule_module._near_copy(("a",), ("a",)) is False
        assert Readings({"b": "x"}, ()).occurrences(1, "q") == 1
        assert Readings({"b": "x"}, {"b"}).trusted("b") is True
    assert (rule_module._near_copy, Readings.occurrences, Readings.trusted) == (near, occurrences_, trusted)
    with pytest.raises(ValueError, match="no such guard"):
        with w.without(("gate",)):
            pass


def test_variant_names_are_the_removed_guards_in_the_order_of_the_rule():
    assert w.variant_name(()) == w.SHIPPED
    assert w.variant_name(("near_copy", "unique")) == "unique+near_copy"
    assert w.variant_name(w.GUARDS) == "+".join(w.GUARDS)


def test_the_table_differences_name_the_variant_the_kind_and_both_counts():
    one = {"v": {"by_kind": {"k": {"links": 1, "wrong": 0, "missed": 2}}}}
    two = {"v": {"by_kind": {"k": {"links": 1, "wrong": 1, "missed": 2}}}, "u": {"by_kind": {}}}
    assert w.table_differences(one, one) == []
    assert w.table_differences(one, two) == [("u", "*", False, True), ("v", "k", (1, 0, 2), (1, 1, 2))]


def test_the_old_unit_limit_is_four_mean_characters_of_the_line_in_its_heights():
    line = w.TextLine(1, 0, 20, 50.0, 100.0, 450.0, 110.0)          # 400 pt over 20 characters: a mean character is 20 pt, the limit 80 pt = 8 heights
    fact = w.EvidenceFact(1, 0, 5, "x")
    assert w._old_unit_heights([fact], [line]) == pytest.approx(8.0)
    assert w._old_unit_heights([w.EvidenceFact(2, 0, 5, "x")], [line]) == w.WITNESS_MAX_GAP_LINE_HEIGHTS
