"""The quality flags on recognised text (`W55B-RECOGNISED-01`, ``P02_SEAMS`` section 4.8).

Container-free. Two kinds of evidence:

* **recorded portal text**: the committed ``ar_baseline_ocr_defects.zip``, whose manifest lists
  every seeded flaw (page, block, kind, the original and the recognised spelling, and whether
  it must be flagged). Each flaggable one must raise its flag *on the recognised word*; the
  four engineering designations on page 6 must raise nothing; the clean ``ar_baseline.zip``
  must raise nothing on any block;
* **unit cases** for each flag, with the negatives that keep it honest.

Every expected flag name is a literal here, never imported from the module under test.
"""

from __future__ import annotations

import re

import pytest

from auditmanager.analysis.recognised import flags as flags_module
from auditmanager.analysis.recognised.flags import flags_for, inspect_recognised
from auditmanager.analysis.recognised.markdown import read_blocks
from tests.integration.analysis.recognised.recognised_support import (
    FLAG_FOR_KIND,
    manifest_entry,
    members,
)

VOCABULARY = (
    "mixed_script",
    "homoglyph",
    "cjk",
    "doubled_list_marker",
    "degenerate_instruction_echo",
    "degenerate_first_person_plan",
    "degenerate_page_narration",
    "degenerate_serialised_payload",
    "empty_text",
)


def _bodies(name: str) -> dict[str, str]:
    return {b.portal_block_id: b.body for b in read_blocks(members(name).markdown.decode("utf-8"))}


DEFECTS = manifest_entry("ar_baseline_ocr_defects.zip")["seeded_text_defects"]
DEFECT_BODIES = _bodies("ar_baseline_ocr_defects.zip")


# --- recorded portal text -------------------------------------------------------------


def test_the_recorded_bundle_seeds_every_flag_this_suite_must_see() -> None:
    kinds = {d["kind"] for d in DEFECTS if d["flaggable"]}
    assert kinds == set(FLAG_FOR_KIND)
    assert sum(1 for d in DEFECTS if d["flaggable"]) == 6
    assert sum(1 for d in DEFECTS if not d["flaggable"]) == 4


@pytest.mark.parametrize(
    "defect",
    [d for d in DEFECTS if d["flaggable"]],
    ids=lambda d: f"page{d['page']}-{d['kind']}-{d['recognised']}",
)
def test_each_seeded_flaw_raises_its_flag_on_the_recognised_word(defect: dict) -> None:
    report = inspect_recognised(DEFECT_BODIES[defect["block_id"]])
    flag = FLAG_FOR_KIND[defect["kind"]]

    assert flag in report.flags
    assert any(word and word in defect["recognised"] for word in report.evidence[flag]), (
        report.evidence[flag]
    )


@pytest.mark.parametrize(
    "defect",
    [d for d in DEFECTS if not d["flaggable"]],
    ids=lambda d: d["recognised"],
)
def test_each_seeded_designation_raises_nothing(defect: dict) -> None:
    report = inspect_recognised(DEFECT_BODIES[defect["block_id"]])
    for flag in ("mixed_script", "homoglyph"):
        assert not any(defect["recognised"] in word or word in defect["recognised"].split()
                       for word in report.evidence.get(flag, ()))
    assert report.flags == ()  # the whole page-6 block is clean


def test_the_designations_block_would_be_flagged_without_the_exemption(monkeypatch) -> None:
    """The exemption carries weight: the rules alone flag three of the four designations."""
    block = next(d["block_id"] for d in DEFECTS if not d["flaggable"])
    monkeypatch.setattr(flags_module, "DESIGNATION", re.compile(r"(?!x)x"))

    report = inspect_recognised(DEFECT_BODIES[block])
    assert set(report.evidence["homoglyph"]) == {"B25", "A500C", "A"}


@pytest.mark.parametrize("name", ["ar_baseline.zip", "ar_baseline_minimal.zip", "pages_31.zip"])
def test_clean_recorded_portal_text_raises_nothing(name: str) -> None:
    bodies = _bodies(name)
    assert bodies
    assert {identifier: flags_for(body) for identifier, body in bodies.items()} == {
        identifier: () for identifier in bodies
    }


# --- the vocabulary ---------------------------------------------------------------------


def test_the_vocabulary_and_its_order_are_pinned() -> None:
    assert flags_module.FLAG_ORDER == VOCABULARY
    assert flags_module.DEGENERACY_FLAGS == VOCABULARY[4:8]


def test_the_degeneracy_flags_are_the_norms_signals() -> None:
    from auditmanager.norms import DegeneracySignal

    assert {f"degenerate_{s.value}" for s in DegeneracySignal} == set(VOCABULARY[4:8])


def test_flags_are_deduplicated_and_in_the_pinned_order() -> None:
    text = "1. 1. кажд梯й\nУровeнь здaния\n- - пункт\nthe user wants it\nмелкоshтучных"
    assert flags_for(text) == (
        "mixed_script",
        "homoglyph",
        "cjk",
        "doubled_list_marker",
        "degenerate_first_person_plan",
    )


# --- mixed_script -----------------------------------------------------------------------


@pytest.mark.parametrize("text", ["мелкоshтучных блоков", "Уровeнь", "Systеm check"])
def test_a_word_mixing_cyrillic_and_latin_is_mixed_script(text: str) -> None:
    assert "mixed_script" in flags_for(text)


@pytest.mark.parametrize(
    "text",
    [
        "Наружные стены — трёхслойные, с эффективным утеплителем.",
        "Степень огнестойкости здания — II, класс С0, предел R 90.",
        "English words only here",
        "Revit 2024 и AutoCAD применяются для чертежей",
    ],
)
def test_text_whose_words_each_keep_to_one_script_is_not_mixed_script(text: str) -> None:
    assert "mixed_script" not in flags_for(text)


# --- homoglyph --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "word"),
    [
        ("Уровeнь ответственности", "Уровeнь"),  # a Latin e inside a Russian word
        ("здaния", "здaния"),
        ("Systеm check", "Systеm"),  # the reverse: a Cyrillic е inside a Latin word
        ("стена c утеплителем", "c"),  # a whole Latin word between Cyrillic ones
        ("в осях 36,0 x 18,0 м", "x"),
        ("класс C0 здания", "C0"),  # one capital and one digit is not a designation
    ],
)
def test_a_look_alike_letter_where_the_other_script_belongs_is_a_homoglyph(
    text: str, word: str
) -> None:
    report = inspect_recognised(text)
    assert word in report.evidence.get("homoglyph", ())


@pytest.mark.parametrize(
    "text",
    [
        "мелкоshтучных",  # mixed, but s and h have no Cyrillic twin
        "в трубах PVC и ПЭ",  # V has no Cyrillic twin
        "use the АР section here",  # a Cyrillic word among Latin ones: measured, left out
        "Revit и AutoCAD",
        "чистый русский текст без ошибок",
    ],
)
def test_no_homoglyph_without_a_look_alike_in_the_wrong_script(text: str) -> None:
    assert "homoglyph" not in flags_for(text)


# --- the designation exemption ----------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Бетон B25, арматура A500C, оси 1.A, предел REI 150.",
        "предел RЕI 150 принят",  # the R E I mixed: Cyrillic Е
        "шифр CП 7-AР лист",  # an СП 7-АР-style code with Latin C and A
        "шифр СП 7-АР лист",
        "оси 2.1.Б и 12.А",
        "марка M200, DN100, IP54, EI 60",
    ],
)
def test_engineering_designations_raise_neither_script_flag(text: str) -> None:
    flags = flags_for(text)
    assert "mixed_script" not in flags and "homoglyph" not in flags


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("предел RЕI 150 принят", {"mixed_script", "homoglyph"}),
        ("шифр CП 7-AР лист", {"mixed_script", "homoglyph"}),
        ("Бетон B25, арматура A500C", {"homoglyph"}),
        ("оси 1.A, предел", {"homoglyph"}),
    ],
)
def test_each_exempted_designation_is_flagged_by_the_rules_alone(
    monkeypatch, text: str, expected: set[str]
) -> None:
    """Without the pattern every case above is flagged, so its exemption is not vacuous.

    ``REI 150`` in plain Latin is never a homoglyph (``R`` has no Cyrillic twin); its
    exemption is shown on the spelling a recognition model produces, with a Cyrillic ``Е``.
    """
    monkeypatch.setattr(flags_module, "DESIGNATION", re.compile(r"(?!x)x"))
    assert set(flags_for(text)) == expected


@pytest.mark.parametrize(
    ("text", "flag", "word"),
    [
        ("Bход в здание", "mixed_script", "Bход"),  # a capital B, then lower-case Cyrillic
        ("оси 1.Aрхитектура", "mixed_script", "Aрхитектура"),  # 1.A with a letter glued on
        ("сталь A500Cталь", "mixed_script", "A500Cталь"),
        ("класс C0 здания", "homoglyph", "C0"),
    ],
)
def test_near_misses_of_a_designation_are_still_flagged(text: str, flag: str, word: str) -> None:
    assert word in inspect_recognised(text).evidence.get(flag, ())


def test_the_pattern_matches_the_four_designations_the_seam_names() -> None:
    for code in ("1.A", "B25", "A500C", "REI 150", "СП 7-АР"):
        assert flags_module.DESIGNATION.fullmatch(code), code


# --- cjk --------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["кажд梯й", "カタカナ", "ひらがな", "한글", "㐀", "𠀀"])
def test_a_cjk_ideograph_kana_or_hangul_is_cjk(text: str) -> None:
    assert "cjk" in flags_for(text)


@pytest.mark.parametrize("text", ["текст。", "точка・точка", "「текст」", "№ 5 — §2"])
def test_cjk_punctuation_alone_is_not_cjk(text: str) -> None:
    assert "cjk" not in flags_for(text)


# --- doubled_list_marker ----------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["- - 3.2. Внутренние", "• • пункт", "1. 1. пункт", "1) 2) пункт", "— — пункт", "  * * x", "- -"],
)
def test_two_list_markers_at_a_line_start_are_doubled(text: str) -> None:
    assert "doubled_list_marker" in flags_for("первая строка\n" + text)


@pytest.mark.parametrize(
    "text",
    [
        "- пункт",
        "1. пункт",
        "1.1. пункт",
        "1. 1.1 пункт",
        "- - -",
        "* * *",
        "***",
        "пункт - - пункт",
        "3.2. Внутренние - -",
    ],
)
def test_a_single_marker_a_thematic_break_or_a_marker_inside_a_line_is_not(text: str) -> None:
    assert "doubled_list_marker" not in flags_for(text)


# --- degeneracy -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("Act as a strict transcription engine.", "degenerate_instruction_echo"),
        ("I will transcribe the table exactly.", "degenerate_first_person_plan"),
        ("The document is a technical table.", "degenerate_page_narration"),
        ('[{"text": "Лист 1"}]', "degenerate_serialised_payload"),
    ],
)
def test_each_norms_degeneracy_signal_is_its_own_flag(text: str, flag: str) -> None:
    assert flags_for(text) == (flag,)


# --- empty_text and the stored text -------------------------------------------------------


@pytest.mark.parametrize("text", ["", "   ", "\n \n"])
def test_an_empty_body_is_empty_text(text: str) -> None:
    assert flags_for(text) == ("empty_text",)


def test_a_decomposed_letter_is_read_after_nfc() -> None:
    """``й`` written as ``и`` + combining breve is one Cyrillic letter, not a split word."""
    decomposed = "каждый этаж"
    assert flags_for(decomposed) == ()
    assert flags_for("Уровĕнь") == ("mixed_script",)  # Latin ĕ has no Cyrillic twin
