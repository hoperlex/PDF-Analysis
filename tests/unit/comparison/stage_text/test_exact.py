"""Evidence properties that matter before stage text is persisted."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow, Word
from auditmanager.comparison.stage_text import (
    FragmentRefused, SheetLink, extract_fragments, prove_exact_exclusions,
)


def _page(profile_id: str, words: tuple[Word, ...], *, status: str = "ready") -> PageProfileData:
    return PageProfileData(
        row=PageProfileRow(profile_id, "ver_01", 1, "0" * 64, "test", status, None,
                           {}, None, None, None, datetime.now(timezone.utc)),
        width_pt=100, height_pt=100, rotation=0, has_text_layer=True,
        scan=False, content_merkle=None, words=words,
    )


def _word(value: str, x: float = 10, y: float = 10) -> Word:
    return Word(x, y, x + 40, y + 8, value)


def _prove(links: list[SheetLink], fragments: tuple, dimensions: dict):
    manifest = {
        profile_id: frozenset(f.content_key for f in fragments if f.profile_id == profile_id)
        for profile_id in dimensions
    }
    return prove_exact_exclusions(links, fragments, dimensions, manifest)


def test_extraction_is_stable_and_keeps_box_anchor() -> None:
    profile = _page("cpr_left", (_word("Мощность", 10), _word("10 кВт", 55), _word("Этаж 2", 10, 30)))
    first = extract_fragments(profile, side="left")
    second = extract_fragments(profile, side="left")
    assert first == second
    assert [item.normalised_text for item in first] == ["мощность 10 квт", "этаж 2"]
    assert first[0].box_anchor == {"x0": 10, "top": 10, "x1": 95, "bottom": 18}
    assert first[0].content_key != first[1].content_key


def test_unique_exact_proof_same_and_moved() -> None:
    left = extract_fragments(_page("cpr_left", (_word("Нагрузка 10 кВт"), _word("Кабель ВВГ 3х4", y=40))), side="left")
    right = extract_fragments(_page("cpr_right", (_word("Нагрузка 10 кВт", y=11), _word("Кабель ВВГ 3х4", y=48))), side="right")
    proof = _prove([SheetLink("cpr_left", "cpr_right")], left + right,
                   {"cpr_left": (100, 100), "cpr_right": (100, 100)})
    assert {(p.left_content_key, p.right_content_key, p.proof_kind) for p in proof} == {
        (left[0].content_key, right[0].content_key, "same"),
        (left[1].content_key, right[1].content_key, "moved"),
    }


def test_repeat_and_unlinked_evidence_never_prove_same() -> None:
    left = extract_fragments(_page("cpr_left", (_word("Общие указания"), _word("Общие указания", y=30))), side="left")
    right = extract_fragments(_page("cpr_right", (_word("Общие указания"),)), side="right")
    assert _prove([SheetLink("cpr_left", "cpr_right")], left + right,
                  {"cpr_left": (100, 100), "cpr_right": (100, 100)}) == ()
    with pytest.raises(ValueError, match="linked_profile_manifest_invalid"):
        _prove([], left, {"cpr_left": (100, 100)})


def test_malformed_or_incomplete_profile_refuses() -> None:
    with pytest.raises(FragmentRefused, match="word_box_invalid"):
        extract_fragments(_page("cpr_left", (_word("bad", x=90),)), side="left")
    with pytest.raises(FragmentRefused, match="profile_not_ready"):
        extract_fragments(_page("cpr_left", (), status="failed"), side="left")
    with pytest.raises(FragmentRefused, match="text_not_utf8"):
        extract_fragments(_page("cpr_left", (_word("\ud800"),)), side="left")


def test_position_gate_and_wrong_side_refuse_false_proof() -> None:
    left = extract_fragments(_page("cpr_left", (_word("Нагрузка 10 кВт", y=10),)), side="left")
    far = extract_fragments(_page("cpr_right", (_word("Нагрузка 10 кВт", y=75),)), side="right")
    dimensions = {"cpr_left": (100, 100), "cpr_right": (100, 100)}
    assert _prove([SheetLink("cpr_left", "cpr_right")], left + far, dimensions) == ()
    with pytest.raises(ValueError, match="fragment_not_in_links"):
        _prove([SheetLink("cpr_left", "cpr_right")],
               left + (replace(far[0], side="left"),), dimensions)


def test_missing_fragment_refuses_before_proof() -> None:
    left = extract_fragments(_page("cpr_left", (_word("Общие указания"), _word("Нагрузка 10 кВт", y=30))), side="left")
    right = extract_fragments(_page("cpr_right", (_word("Нагрузка 10 кВт", y=30),)), side="right")
    dimensions = {"cpr_left": (100, 100), "cpr_right": (100, 100)}
    manifest = {"cpr_left": frozenset(f.content_key for f in left),
                "cpr_right": frozenset(f.content_key for f in right)}
    with pytest.raises(ValueError, match="fragment_manifest_mismatch"):
        prove_exact_exclusions([SheetLink("cpr_left", "cpr_right")], left[1:] + right,
                               dimensions, manifest)


def test_scan_without_words_has_no_false_absence_proof() -> None:
    left = extract_fragments(_page("cpr_left", ()), side="left")
    right = extract_fragments(_page("cpr_right", (_word("Нагрузка 10 кВт"),)), side="right")
    assert not left
    assert _prove([SheetLink("cpr_left", "cpr_right")], left + right,
                  {"cpr_left": (100, 100), "cpr_right": (100, 100)}) == ()


def test_engineering_value_change_is_never_exact_exclusion() -> None:
    left = extract_fragments(_page("cpr_left", (_word("Нагрузка 10 кВт"),)), side="left")
    right = extract_fragments(_page("cpr_right", (_word("Нагрузка 20 кВт"),)), side="right")
    assert _prove([SheetLink("cpr_left", "cpr_right")], left + right,
                  {"cpr_left": (100, 100), "cpr_right": (100, 100)}) == ()


def test_repeated_text_across_sheet_links_does_not_become_proof() -> None:
    pages = (
        extract_fragments(_page("cpr_left_1", (_word("Общие указания"),)), side="left")
        + extract_fragments(_page("cpr_left_2", (_word("Общие указания"),)), side="left")
        + extract_fragments(_page("cpr_right_1", (_word("Общие указания"),)), side="right")
        + extract_fragments(_page("cpr_right_2", (_word("Общие указания"),)), side="right")
    )
    dimensions = {profile: (100, 100) for profile in
                  ("cpr_left_1", "cpr_left_2", "cpr_right_1", "cpr_right_2")}
    assert _prove([SheetLink("cpr_left_1", "cpr_right_1"),
                   SheetLink("cpr_left_2", "cpr_right_2")], pages, dimensions) == ()
