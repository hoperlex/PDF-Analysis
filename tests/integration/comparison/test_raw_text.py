"""Recorded, small inputs for W59's raw version-comparison preparation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from auditmanager.comparison.raw_text import (
    MAX_LINES_PER_PAGE,
    MAX_PAGE_CHARACTERS,
    ApprovedSheetPair,
    RawTextDiffRefused,
    diff_approved_pairs,
)

CMP = "cmp_00000000000000000000000001"
SOURCE = "ver_00000000000000000000000001"
TARGET = "ver_00000000000000000000000002"
OTHER = "ver_00000000000000000000000003"
LINK_1 = "sln_00000000000000000000000001"
LINK_2 = "sln_00000000000000000000000002"


def _pair(
    *,
    link: str = LINK_1,
    source_page: int = 1,
    target_page: int = 2,
    revision: int = 3,
    source_version: str = SOURCE,
) -> ApprovedSheetPair:
    return ApprovedSheetPair(CMP, link, revision, source_version, TARGET, source_page, target_page)


def _diff(
    pairs: tuple[ApprovedSheetPair, ...] = (_pair(),),
    source_pages: dict[int, str] | None = None,
    target_pages: dict[int, str] | None = None,
):
    return diff_approved_pairs(
        comparison_id=CMP,
        source_version_uid=SOURCE,
        target_version_uid=TARGET,
        link_revision=3,
        approved_pairs=pairs,
        source_pages={1: "Ось А\r\nСтена 200\n"} if source_pages is None else source_pages,
        target_pages={2: "Ось А\r\nСтена 250\n"} if target_pages is None else target_pages,
    )


def test_exact_text_and_provenance_are_immutable_and_repeatable() -> None:
    one = _diff()[0]
    two = _diff()[0]
    assert one == two
    assert one.source_version_uid == SOURCE
    assert one.target_version_uid == TARGET
    assert one.sheet_link_id == LINK_1
    assert one.link_revision == 3
    assert [(change.tag, change.source_lines, change.target_lines) for change in one.changes] == [
        ("equal", ("Ось А\r\n",), ("Ось А\r\n",)),
        ("replace", ("Стена 200\n",), ("Стена 250\n",)),
    ]
    assert "".join(line for change in one.changes for line in change.source_lines) == (
        "Ось А\r\nСтена 200\n"
    )
    assert "".join(line for change in one.changes for line in change.target_lines) == (
        "Ось А\r\nСтена 250\n"
    )
    with pytest.raises(FrozenInstanceError):
        one.evidence_sha256 = "0" * 64  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        one.changes[0].source_lines = ()  # type: ignore[misc]


def test_one_character_change_changes_raw_evidence_without_normalizing_text() -> None:
    baseline = _diff()[0]
    changed = _diff(target_pages={2: "Ось А\r\nСтена 251\n"})[0]
    assert baseline.source_sha256 == changed.source_sha256
    assert baseline.target_sha256 != changed.target_sha256
    assert baseline.evidence_sha256 != changed.evidence_sha256
    assert changed.changes[-1].target_lines == ("Стена 251\n",)


def test_explicit_links_can_reorder_pages_but_output_order_is_stable() -> None:
    first = _pair(source_page=5, target_page=1)
    second = _pair(link=LINK_2, source_page=1, target_page=9)
    pages_before = {1: "A\n", 5: "B\n"}
    pages_after = {1: "B2\n", 9: "A2\n"}
    forward = _diff((first, second), pages_before, pages_after)
    reverse = _diff((second, first), pages_before, pages_after)
    assert forward == reverse
    assert [
        (item.sheet_link_id, item.source_page_number, item.target_page_number)
        for item in forward
    ] == [
        (LINK_2, 1, 9),
        (LINK_1, 5, 1),
    ]


@pytest.mark.parametrize(
    ("pairs", "reason"),
    [
        ((), "pair_count_invalid"),
        ((_pair(), _pair()), "pair_not_one_to_one"),
        ((_pair(), _pair(link=LINK_2, source_page=1, target_page=3)), "pair_not_one_to_one"),
        ((_pair(), _pair(link=LINK_2, source_page=3, target_page=2)), "pair_not_one_to_one"),
        ((_pair(revision=4),), "pair_revision_mismatch"),
        ((_pair(source_version=OTHER),), "pair_version_mismatch"),
        ((_pair(link="sln_invalid"),), "sheet_link_id_invalid"),
        ((_pair(source_page=0),), "source_page_number_invalid"),
    ],
)
def test_ambiguous_or_stale_pairing_refuses(
    pairs: tuple[ApprovedSheetPair, ...], reason: str
) -> None:
    with pytest.raises(RawTextDiffRefused, match=f"^{reason}$"):
        _diff(pairs)


def test_missing_page_and_wrong_version_refuse() -> None:
    with pytest.raises(RawTextDiffRefused, match="^page_text_missing$"):
        _diff(source_pages={})
    with pytest.raises(RawTextDiffRefused, match="^same_version$"):
        diff_approved_pairs(
            comparison_id=CMP,
            source_version_uid=SOURCE,
            target_version_uid=SOURCE,
            link_revision=3,
            approved_pairs=(_pair(),),
            source_pages={1: "x"},
            target_pages={2: "y"},
        )


def test_size_ceilings_refuse_without_a_truncated_diff() -> None:
    with pytest.raises(RawTextDiffRefused, match="^source_text_too_large$"):
        _diff(source_pages={1: "x" * (MAX_PAGE_CHARACTERS + 1)})
    with pytest.raises(RawTextDiffRefused, match="^source_text_too_many_lines$"):
        _diff(source_pages={1: "x\n" * (MAX_LINES_PER_PAGE + 1)})
    with pytest.raises(RawTextDiffRefused, match="^text_not_utf8_encodable$"):
        _diff(source_pages={1: "\ud800"})


def test_aggregate_limits_are_checked_before_diffing_any_pair() -> None:
    pairs = tuple(
        _pair(
            link=f"sln_{index:026d}",
            source_page=index,
            target_page=index,
        )
        for index in range(1, 7)
    )
    large = "x" * MAX_PAGE_CHARACTERS
    pages = {index: large for index in range(1, 7)}
    with pytest.raises(RawTextDiffRefused, match="^comparison_input_too_large$"):
        _diff(pairs, pages, pages)

    too_many = tuple(
        _pair(link=f"sln_{index:026d}", source_page=index, target_page=index)
        for index in range(1, 34)
    )
    with pytest.raises(RawTextDiffRefused, match="^pair_count_invalid$"):
        _diff(too_many)
