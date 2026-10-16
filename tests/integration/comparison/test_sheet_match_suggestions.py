"""Exact page suggestions never promote a guess into an approved sheet link."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from auditmanager.comparison.sheet_match_suggestions import (
    MAX_PAGE_BYTES,
    SheetMatchSuggestionRefused,
    suggest_exact_sheet_matches,
)
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"
COMPARISON = "cmp_00000000000000000000000001"


def _pair(source_pages: int = 3, target_pages: int = 3) -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT,
        DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 100, source_pages, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 2, "b" * 64, 101, target_pages, "application/pdf"),
    )


def _suggest(**changes):
    data = {
        "version_pair": _pair(),
        "comparison_id": COMPARISON,
        "source_pages": {1: "Общие данные\nСтена 200 мм\n", 2: "План этажа\nОсь А-Б\n", 3: "\n"},
        "target_pages": {1: "План этажа\nОсь А-Б\n", 2: "Общие данные\nСтена 250 мм\n", 3: "\n"},
    }
    return suggest_exact_sheet_matches(**(data | changes))


def test_exact_moved_sheet_is_only_suggestion_and_has_no_link_identity() -> None:
    result = _suggest()
    assert len(result) == 1
    match = result[0]
    assert (match.source_page_number, match.target_page_number) == (2, 1)
    assert match.source_version_uid == SOURCE and match.target_version_uid == TARGET
    assert len(match.page_text_sha256) == len(match.suggestion_sha256) == 64
    assert not hasattr(match, "sheet_link_id")
    with pytest.raises(FrozenInstanceError):
        match.target_page_number = 2  # type: ignore[misc]


def test_reordered_maps_are_stable_and_changed_text_has_no_match() -> None:
    first = _suggest()
    assert first == _suggest(
        source_pages={3: "\n", 2: "План этажа\nОсь А-Б\n", 1: "Общие данные\nСтена 200 мм\n"},
        target_pages={3: "\n", 2: "Общие данные\nСтена 250 мм\n", 1: "План этажа\nОсь А-Б\n"},
    )
    assert _suggest(target_pages={1: "План этажа\nОсь А-В\n", 2: "Иной лист", 3: "\n"}) == ()
    assert _suggest(comparison_id="cmp_00000000000000000000000002")[0].suggestion_sha256 != first[0].suggestion_sha256


def test_duplicate_text_on_either_side_is_ambiguous_and_does_not_match() -> None:
    assert _suggest(source_pages={1: "План этажа\nОсь А-Б\n", 2: "План этажа\nОсь А-Б\n", 3: "\n"}) == ()
    assert _suggest(target_pages={1: "План этажа\nОсь А-Б\n", 2: "План этажа\nОсь А-Б\n", 3: "\n"}) == ()


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"source_pages": {1: "x", 2: "y"}}, "source_pages_incomplete"),
        ({"target_pages": {True: "x", 2: "y", 3: "z"}}, "target_pages_incomplete"),
        ({"source_pages": {1: "x", 2: "y", 3: "\ud800"}}, "source_page_text_invalid"),
        ({"target_pages": {1: "x" * (MAX_PAGE_BYTES + 1), 2: "y", 3: "z"}}, "target_page_too_large"),
        ({"version_pair": replace(_pair(), target=replace(_pair().target, version_ordinal=1))}, "version_order_invalid"),
        ({"version_pair": replace(_pair(), source=replace(_pair().source, page_count=2))}, "source_pages_incomplete"),
        ({"version_pair": replace(_pair(), target=replace(_pair().target, document_uid="doc_01M2545JSD15ETSNNV904X991K"))}, "version_pair_mismatch"),
        ({"comparison_id": "cmp_bad"}, "comparison_id_invalid"),
    ],
)
def test_incomplete_or_forged_input_refuses(changes, reason) -> None:
    with pytest.raises(SheetMatchSuggestionRefused, match=f"^{reason}$"):
        _suggest(**changes)


def test_version_checksum_changes_suggestion_provenance() -> None:
    original = _suggest()[0]
    updated = _suggest(version_pair=replace(
        _pair(), target=replace(_pair().target, sha256="c" * 64),
    ))[0]
    assert original.page_text_sha256 == updated.page_text_sha256
    assert original.suggestion_sha256 != updated.suggestion_sha256
