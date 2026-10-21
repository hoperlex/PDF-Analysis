"""Read-path sheet pairing and the link-free line diff (`W59-VERSION-COMPARE-01`)."""

from __future__ import annotations

import pytest

from auditmanager.comparison.raw_text import (
    MAX_LINES_PER_PAGE,
    ApprovedSheetPair,
    RawTextDiffRefused,
    diff_approved_pairs,
    diff_page_lines,
)
from auditmanager.comparison.sheet_match_suggestions import (
    EXACT_PAIR_ALGORITHM,
    MAX_DISTINCTIVE_LINE_PAGES,
    SIMILAR_PAIR_ALGORITHM,
    SheetMatchSuggestionRefused,
    suggest_sheet_pairs,
)
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"


def _pair(source_pages: int, target_pages: int) -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT, DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 100, source_pages, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 2, "b" * 64, 100, target_pages, "application/pdf"),
    )


def _sheet(title: str, *notes: str) -> str:
    """A sheet: shared frame text plus its own distinctive lines."""
    return "\n".join(("ООО Проект", "Лист", title, *notes)) + "\n"


def _suggest(source: dict[int, str], target: dict[int, str]):
    return suggest_sheet_pairs(
        version_pair=_pair(len(source), len(target)), source_pages=source, target_pages=target,
    )


def test_exact_pages_pair_first_and_changed_sheet_pairs_by_shared_lines() -> None:
    source = {
        1: _sheet("План 1 этажа", "Ось А-Г", "Стена 200", "Дверь Д1"),
        2: _sheet("Разрез 1-1", "Отм. +3.000", "Перекрытие П1"),
    }
    target = {
        1: _sheet("Разрез 1-1", "Отм. +3.000", "Перекрытие П1"),
        2: _sheet("План 1 этажа", "Ось А-Г", "Стена 250", "Дверь Д1"),
    }
    similar, exact = _suggest(source, target)  # ordered by source page
    assert (exact.algorithm, exact.source_page_number, exact.target_page_number) == (
        EXACT_PAIR_ALGORITHM, 2, 1,
    )
    assert exact.similarity_permille == 1000 and exact.shared_line_count is None
    assert (similar.algorithm, similar.source_page_number, similar.target_page_number) == (
        SIMILAR_PAIR_ALGORITHM, 1, 2,
    )
    # "ООО Проект" and "Лист" occur on four pages; with cap 8 they still count here.
    assert similar.shared_line_count == 5
    assert similar.source_line_count == 6 and similar.target_line_count == 6
    assert similar.similarity_permille == 833
    assert similar.source_page_text_sha256 != similar.target_page_text_sha256


def test_frame_text_repeated_on_many_sheets_carries_no_pairing_signal() -> None:
    frame = [f"Штамп строка {n}" for n in range(6)]
    count = MAX_DISTINCTIVE_LINE_PAGES  # 2*count pages: frame lines are not distinctive
    source = {n: "\n".join((*frame, f"Лист {n}", f"Деталь {n}")) for n in range(1, count + 1)}
    target = {n: "\n".join((*frame, f"Лист {n}", f"Узел {n}")) for n in range(1, count + 1)}
    # Each pair shares only one distinctive line ("Лист n"): below MIN_SHARED, so no guess.
    assert _suggest(source, target) == ()


def test_blank_and_duplicate_pages_stay_unpaired() -> None:
    source = {1: "", 2: _sheet("Узел", "Деталь 1", "Деталь 2"), 3: _sheet("Узел", "Деталь 1", "Деталь 2")}
    target = {1: "  \n", 2: _sheet("Узел", "Деталь 1", "Деталь 2")}
    suggestions = _suggest(source, target)
    # The duplicated text is ambiguous for the exact rule; similarity then picks the lowest
    # source page deterministically, and blank pages get nothing.
    assert [(s.algorithm, s.source_page_number, s.target_page_number) for s in suggestions] == [
        (SIMILAR_PAIR_ALGORITHM, 2, 2),
    ]


def test_result_and_digests_do_not_depend_on_mapping_order() -> None:
    source = {n: _sheet(f"Лист {n}", f"Примечание {n}", f"Размер {n}0") for n in range(1, 7)}
    target = {n: _sheet(f"Лист {n}", f"Примечание {n}", f"Размер {n}5") for n in range(1, 7)}
    forward = _suggest(source, target)
    backward = _suggest(dict(reversed(source.items())), dict(reversed(target.items())))
    assert forward == backward
    assert [(s.source_page_number, s.target_page_number) for s in forward] == [
        (n, n) for n in range(1, 7)
    ]
    assert len({s.suggestion_sha256 for s in forward}) == 6


def test_low_similarity_is_not_paired() -> None:
    source = {1: "\n".join(["Общие данные", "А", "Б"] + [f"старое {n}" for n in range(10)])}
    target = {1: "\n".join(["Общие данные", "А", "Б"] + [f"новое {n}" for n in range(10)])}
    # Three shared lines of thirteen on each side: 230 permille, under the 500 threshold.
    assert _suggest(source, target) == ()


def test_incomplete_snapshot_refuses() -> None:
    with pytest.raises(SheetMatchSuggestionRefused, match="target_pages_incomplete"):
        suggest_sheet_pairs(
            version_pair=_pair(1, 2), source_pages={1: "a"}, target_pages={1: "a"},
        )


def test_page_line_diff_keeps_raw_text_and_counts() -> None:
    page = diff_page_lines("Ось А\r\nСтена 200\n", "Ось А\r\nСтена 250\nОкно\n")
    assert (page.source_line_count, page.target_line_count) == (2, 3)
    assert [c.tag for c in page.changes] == ["equal", "replace"]
    assert page.changes[1].source_lines == ("Стена 200\n",)
    assert page.changes[1].target_lines == ("Стена 250\n", "Окно\n")
    assert diff_page_lines("", "x\n").changes[0].tag == "insert"


def test_page_line_diff_refuses_oversized_page_instead_of_truncating() -> None:
    with pytest.raises(RawTextDiffRefused, match="target_text_too_many_lines"):
        diff_page_lines("", "x\n" * (MAX_LINES_PER_PAGE + 1))


def test_approved_raw_evidence_digest_is_unchanged_by_the_shared_core() -> None:
    """Pinned from base 890deb80 before ``diff_page_lines`` was extracted."""
    comparison = "cmp_00000000000000000000000001"
    source, target = "ver_00000000000000000000000001", "ver_00000000000000000000000002"
    (diff,) = diff_approved_pairs(
        comparison_id=comparison, source_version_uid=source, target_version_uid=target,
        link_revision=3,
        approved_pairs=(ApprovedSheetPair(
            comparison, "sln_00000000000000000000000001", 3, source, target, 1, 2,
        ),),
        source_pages={1: "Ось А\r\nСтена 200\nДверь Д1\n"},
        target_pages={2: "Ось А\r\nСтена 250\nДверь Д1\nОкно\n"},
    )
    assert diff.evidence_sha256 == "fdcfce59337f2f43d18008db79b95839efe705c412f4c0ece7ae7048c970a315"
    assert diff.source_sha256 == "60b42cfd945db903a7da19c196fb5b117bca8ea23945187900df21ab55b8dbc1"
