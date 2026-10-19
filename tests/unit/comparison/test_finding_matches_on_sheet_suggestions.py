"""Finding match proposals across rebuildable sheet suggestions (`W59-VERSION-COMPARE-01`)."""

from __future__ import annotations

import pytest

from auditmanager.comparison.finding_match_suggestions import (
    SUGGESTED_SHEETS_ALGORITHM,
    FindingForMatch,
    FindingMatchSuggestionRefused,
    FindingQuote,
    SuggestedSheetPair,
    suggest_exact_finding_matches,
    suggest_finding_matches_on_sheet_suggestions,
)
from auditmanager.comparison.raw_text import ApprovedSheetPair
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
SOURCE = "ver_00000000000000000000000001"
TARGET = "ver_00000000000000000000000002"
SOURCE_RUN = "run_00000000000000000000000001"
TARGET_RUN = "run_00000000000000000000000002"


def _pair() -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT, DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 100, 3, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 2, "b" * 64, 101, 3, "application/pdf"),
    )


def _finding(number: int, *, source: bool, quotes, text: str = "Нет дверного проёма"):
    return FindingForMatch(
        f"fnd_{number:026d}", f"fobs_{number:026d}",
        SOURCE_RUN if source else TARGET_RUN, SOURCE if source else TARGET,
        "layout", text, tuple(FindingQuote(page, quote) for page, quote in quotes),
    )


SHEETS = (SuggestedSheetPair(1, 3, "1" * 64), SuggestedSheetPair(2, 1, "2" * 64))


def _propose(source_findings, target_findings, sheets=SHEETS):
    return suggest_finding_matches_on_sheet_suggestions(
        version_pair=_pair(), sheet_suggestions=sheets,
        source_run_id=SOURCE_RUN, target_run_id=TARGET_RUN,
        source_findings=source_findings, target_findings=target_findings,
    )


def test_exact_issue_follows_suggested_moved_sheets_and_names_them() -> None:
    (proposal,) = _propose(
        (_finding(1, source=True, quotes=[(1, "Проём  отсутствует"), (2, "Ось Б")]),),
        (_finding(2, source=False, quotes=[(3, "Проём отсутствует"), (1, "Ось Б")]),),
    )
    assert proposal.algorithm == SUGGESTED_SHEETS_ALGORITHM
    assert (proposal.source_finding_uid, proposal.target_finding_uid) == (
        f"fnd_{1:026d}", f"fnd_{2:026d}",
    )
    assert proposal.sheet_suggestion_sha256s == ("1" * 64, "2" * 64)
    assert len(proposal.proposal_sha256) == 64


def test_unpaired_page_or_changed_text_yields_no_proposal() -> None:
    source = (_finding(1, source=True, quotes=[(3, "Проём отсутствует")]),)
    target = (_finding(2, source=False, quotes=[(3, "Проём отсутствует")]),)
    assert _propose(source, target) == ()  # source page 3 has no suggested counterpart
    moved = (_finding(3, source=True, quotes=[(1, "Проём отсутствует")]),)
    reworded = (_finding(4, source=False, quotes=[(3, "Проём отсутствует")], text="Иное"),)
    assert _propose(moved, reworded) == ()


def test_empty_suggestions_are_allowed_and_link_nothing() -> None:
    source = (_finding(1, source=True, quotes=[(1, "Проём отсутствует")]),)
    target = (_finding(2, source=False, quotes=[(1, "Проём отсутствует")]),)
    assert _propose(source, target, sheets=()) == ()


@pytest.mark.parametrize(
    ("sheets", "reason"),
    [
        ((SuggestedSheetPair(1, 3, "1" * 64), SuggestedSheetPair(1, 2, "2" * 64)),
         "sheet_suggestions_not_one_to_one"),
        ((SuggestedSheetPair(4, 1, "1" * 64),), "sheet_suggestion_page_invalid"),
        ((SuggestedSheetPair(1, 1, "not-a-digest"),), "sheet_suggestion_digest_invalid"),
    ],
)
def test_malformed_suggestions_refuse(sheets, reason) -> None:
    with pytest.raises(FindingMatchSuggestionRefused, match=reason):
        _propose((), (), sheets=sheets)


def test_approved_link_digest_is_unchanged_by_the_shared_core() -> None:
    """Pinned from base 890deb80 before ``_unique_exact_pairs`` was extracted."""
    comparison = "cmp_00000000000000000000000001"
    pair = OrderedVersionPair(
        "prj_01M2545JSD15ETSNNV904X991J", "doc_01M2545JSD15ETSNNV904X991J",
        VersionFacts(SOURCE, "doc_01M2545JSD15ETSNNV904X991J", "prj_01M2545JSD15ETSNNV904X991J",
                     1, "a" * 64, 100, 3, "application/pdf"),
        VersionFacts(TARGET, "doc_01M2545JSD15ETSNNV904X991J", "prj_01M2545JSD15ETSNNV904X991J",
                     2, "b" * 64, 101, 3, "application/pdf"),
    )
    (suggestion,) = suggest_exact_finding_matches(
        version_pair=pair, comparison_id=comparison, link_revision=4,
        approved_pairs=(
            ApprovedSheetPair(comparison, "sln_00000000000000000000000001", 4, SOURCE, TARGET, 1, 3),
            ApprovedSheetPair(comparison, "sln_00000000000000000000000002", 4, SOURCE, TARGET, 2, 1),
        ),
        source_run_id=SOURCE_RUN, target_run_id=TARGET_RUN,
        source_findings=(_finding(
            1, source=True, quotes=[(1, "Проём отсутствует"), (2, "Ось Б")],
            text="Нет  дверного проёма",
        ),),
        target_findings=(_finding(2, source=False, quotes=[(1, "Ось Б"), (3, "Проём  отсутствует")]),),
    )
    assert suggestion.suggestion_sha256 == (
        "631130310b078b247c6828a7a60de2ff48d202265e04b84b28e24de1fac54125"
    )
