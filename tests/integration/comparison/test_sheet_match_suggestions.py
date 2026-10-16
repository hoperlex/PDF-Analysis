"""Exact page suggestions never promote a guess into an approved sheet link."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from auditmanager.comparison.sheet_match_suggestions import (
    MAX_SNAPSHOT_CHARACTERS,
    MAX_SNAPSHOT_PAGE_CHARACTERS,
    SheetMatchSuggestionRefused,
    suggest_exact_sheet_matches,
)
from auditmanager.comparison.version_reader import MAX_VERSION_PAGES
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


def test_complete_500_page_text_rich_snapshot_can_suggest_moved_sheets() -> None:
    source = {number: f"Лист {number}\n" + "А" * 3_570
              for number in range(1, MAX_VERSION_PAGES + 1)}
    target = {number: source[MAX_VERSION_PAGES + 1 - number]
              for number in range(1, MAX_VERSION_PAGES + 1)}
    assert sum(len(page.encode("utf-8")) for page in source.values()) > 2_000_000
    result = _suggest(version_pair=_pair(500, 500), source_pages=source, target_pages=target)
    assert len(result) == 500
    assert (result[0].source_page_number, result[0].target_page_number) == (1, 500)
    assert (result[-1].source_page_number, result[-1].target_page_number) == (500, 1)


def test_full_snapshot_abstains_on_duplicate_at_page_500() -> None:
    source = {number: f"Лист {number}\n" for number in range(1, 501)}
    target = dict(source)
    target[500] = source[1]
    result = _suggest(version_pair=_pair(500, 500), source_pages=source, target_pages=target)
    assert len(result) == 498
    assert all(item.source_page_number != 1 for item in result)


def test_snapshot_above_document_character_budget_refuses() -> None:
    full_page = "x" * MAX_SNAPSHOT_PAGE_CHARACTERS
    source = {number: full_page for number in range(1, 101)} | {101: "x"}
    assert sum(map(len, source.values())) == MAX_SNAPSHOT_CHARACTERS + 1
    with pytest.raises(SheetMatchSuggestionRefused, match="^source_pages_too_large$"):
        _suggest(version_pair=_pair(101, 3), source_pages=source)


class _EncodeForbidden(str):
    def encode(self, *args: object, **kwargs: object) -> bytes:
        raise AssertionError("oversized page was encoded before refusal")


@pytest.mark.parametrize("side", ("source", "target"))
def test_page_limit_refuses_before_encoding_oversized_text(side: str) -> None:
    pages = {1: _EncodeForbidden("А" * (MAX_SNAPSHOT_PAGE_CHARACTERS + 1)),
             2: "План", 3: "Разрез"}
    with pytest.raises(SheetMatchSuggestionRefused, match=f"^{side}_page_too_large$"):
        _suggest(**{f"{side}_pages": pages})


def test_document_limit_refuses_before_encoding_crossing_page() -> None:
    full_page = "x" * MAX_SNAPSHOT_PAGE_CHARACTERS
    source = {number: full_page for number in range(1, 101)}
    source[101] = _EncodeForbidden("x")
    with pytest.raises(SheetMatchSuggestionRefused, match="^source_pages_too_large$"):
        _suggest(version_pair=_pair(101, 3), source_pages=source)


def test_exact_page_and_document_boundaries_keep_frozen_digests() -> None:
    blank_page = " " * MAX_SNAPSHOT_PAGE_CHARACTERS
    unicode_page = "А" * MAX_SNAPSHOT_PAGE_CHARACTERS
    pages = {number: blank_page for number in range(1, 100)} | {100: unicode_page}
    assert sum(map(len, pages.values())) == MAX_SNAPSHOT_CHARACTERS
    suggestion, = _suggest(version_pair=_pair(100, 100),
                           source_pages=pages, target_pages=pages)
    assert (suggestion.source_page_number, suggestion.target_page_number) == (100, 100)
    assert suggestion.page_text_sha256 == "e125e459ef1f20607b55f5e1430a143b7a3d7ada463cb6c56b7ec9953a4c44d7"
    assert suggestion.suggestion_sha256 == "dd38eb7c61170ad2fa8ef3c8e3b2d7ef1917d63b0d2c224ec726935950cb9d00"


def test_duplicate_text_on_either_side_is_ambiguous_and_does_not_match() -> None:
    assert _suggest(source_pages={1: "План этажа\nОсь А-Б\n", 2: "План этажа\nОсь А-Б\n", 3: "\n"}) == ()
    assert _suggest(target_pages={1: "План этажа\nОсь А-Б\n", 2: "План этажа\nОсь А-Б\n", 3: "\n"}) == ()


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"source_pages": {1: "x", 2: "y"}}, "source_pages_incomplete"),
        ({"target_pages": {True: "x", 2: "y", 3: "z"}}, "target_pages_incomplete"),
        ({"source_pages": {1: "x", 2: "y", 3: "\ud800"}}, "source_page_text_invalid"),
        ({"target_pages": {1: "x" * (MAX_SNAPSHOT_PAGE_CHARACTERS + 1), 2: "y", 3: "z"}}, "target_page_too_large"),
        ({"version_pair": replace(_pair(), target=replace(_pair().target, version_ordinal=1))}, "version_order_invalid"),
        ({"version_pair": replace(_pair(), source=replace(_pair().source, page_count=2))}, "source_pages_incomplete"),
        ({"version_pair": replace(_pair(), target=replace(_pair().target, document_uid="doc_01M2545JSD15ETSNNV904X991K"))}, "version_pair_mismatch"),
        ({"version_pair": _pair(501, 3)}, "version_facts_invalid"),
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
