"""Recorded W59 inputs for conservative cross-version finding suggestions."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from auditmanager.comparison.finding_match_suggestions import (
    FindingForMatch,
    FindingMatchSuggestionRefused,
    FindingQuote,
    suggest_exact_finding_matches,
)
from auditmanager.comparison.raw_text import ApprovedSheetPair
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"
CMP = "cmp_00000000000000000000000001"
SOURCE_RUN = "run_00000000000000000000000001"
TARGET_RUN = "run_00000000000000000000000002"


def _id(prefix: str, number: int) -> str:
    return f"{prefix}_{number:026d}"


def _version_pair() -> OrderedVersionPair:
    return OrderedVersionPair(
        PROJECT, DOCUMENT,
        VersionFacts(SOURCE, DOCUMENT, PROJECT, 1, "a" * 64, 100, 3, "application/pdf"),
        VersionFacts(TARGET, DOCUMENT, PROJECT, 2, "b" * 64, 101, 3, "application/pdf"),
    )


def _links() -> tuple[ApprovedSheetPair, ...]:
    return (
        ApprovedSheetPair(CMP, _id("sln", 1), 4, SOURCE, TARGET, 1, 3),
        ApprovedSheetPair(CMP, _id("sln", 2), 4, SOURCE, TARGET, 2, 1),
    )


def _finding(number: int, *, source: bool, page: int, text: str = "Нет дверного проёма",
             quote: str = "Проём отсутствует") -> FindingForMatch:
    return FindingForMatch(
        _id("fnd", number), _id("fobs", number),
        SOURCE_RUN if source else TARGET_RUN,
        SOURCE if source else TARGET,
        "layout", text, (FindingQuote(page, quote),),
    )


def _suggest(**changes):
    arguments = {
        "version_pair": _version_pair(),
        "comparison_id": CMP,
        "link_revision": 4,
        "approved_pairs": _links(),
        "source_run_id": SOURCE_RUN,
        "target_run_id": TARGET_RUN,
        "source_findings": (_finding(1, source=True, page=1),),
        "target_findings": (_finding(2, source=False, page=3),),
    }
    arguments.update(changes)
    return suggest_exact_finding_matches(**arguments)


def test_exact_issue_and_quote_follow_approved_moved_sheet() -> None:
    one = _suggest()[0]
    assert one.source_finding_uid == _id("fnd", 1)
    assert one.target_finding_uid == _id("fnd", 2)
    assert one.matched_sheet_link_ids == (_id("sln", 1),)
    assert one.source_version_uid == SOURCE and one.target_version_uid == TARGET
    assert one.link_revision == 4
    assert len(one.suggestion_sha256) == 64
    with pytest.raises(FrozenInstanceError):
        one.source_finding_uid = _id("fnd", 3)  # type: ignore[misc]


def test_order_of_findings_and_links_does_not_change_suggestions() -> None:
    old = (
        _finding(10, source=True, page=2, text="Нет обозначения", quote="Обозначение отсутствует"),
        _finding(1, source=True, page=1),
    )
    new = (
        _finding(2, source=False, page=3),
        _finding(20, source=False, page=1, text="Нет обозначения", quote="Обозначение отсутствует"),
    )
    first = _suggest(source_findings=old, target_findings=new)
    second = _suggest(
        approved_pairs=tuple(reversed(_links())),
        source_findings=tuple(reversed(old)), target_findings=tuple(reversed(new)),
    )
    assert first == second
    assert tuple(item.target_finding_uid for item in first) == (_id("fnd", 2), _id("fnd", 20))


def test_whitespace_normalization_is_bounded_and_digest_retains_exact_input() -> None:
    original = _suggest()[0]
    new = _finding(2, source=False, page=3, text="Нет  дверного\nпроёма",
                   quote="Проём\tотсутствует")
    normalized = _suggest(target_findings=(new,))[0]
    assert normalized.target_finding_uid == original.target_finding_uid
    assert normalized.suggestion_sha256 != original.suggestion_sha256


def test_changed_issue_or_quote_and_unlinked_sheet_yield_no_guess() -> None:
    assert _suggest(target_findings=(_finding(2, source=False, page=3, quote="Проём есть"),)) == ()
    assert _suggest(target_findings=(_finding(2, source=False, page=3, text="Иной вопрос"),)) == ()
    assert _suggest(source_findings=(_finding(1, source=True, page=3),)) == ()
    assert _suggest(source_findings=()) == ()
    assert _suggest(target_findings=()) == ()


def test_ambiguous_duplicate_issue_on_either_side_yields_no_suggestion() -> None:
    first_old = _finding(1, source=True, page=1)
    first_new = _finding(2, source=False, page=3)
    assert _suggest(source_findings=(first_old, replace(first_old,
        finding_uid=_id("fnd", 3), finding_observation_id=_id("fobs", 3)))) == ()
    assert _suggest(target_findings=(first_new, replace(first_new,
        finding_uid=_id("fnd", 4), finding_observation_id=_id("fobs", 4)))) == ()


@pytest.mark.parametrize("change,reason", [
    ({"link_revision": 5}, "approved_pair_binding_mismatch"),
    ({"approved_pairs": ()}, "approved_pairs_invalid"),
    ({"source_run_id": TARGET_RUN}, "same_run"),
    ({"comparison_id": "cmp_invalid"}, "comparison_id_invalid"),
])
def test_invalid_comparison_inputs_refuse(change, reason) -> None:
    with pytest.raises(FindingMatchSuggestionRefused, match=f"^{reason}$"):
        _suggest(**change)


def test_duplicate_link_or_source_page_refuses_before_suggestion() -> None:
    first = _links()[0]
    with pytest.raises(FindingMatchSuggestionRefused, match="^approved_pair_revision_invalid$"):
        _suggest(approved_pairs=(replace(first, link_revision=True),))
    with pytest.raises(FindingMatchSuggestionRefused, match="^approved_pairs_not_one_to_one$"):
        _suggest(approved_pairs=(first, replace(first, sheet_link_id=_id("sln", 3),
                                             target_page_number=2)))


def test_foreign_run_version_or_out_of_range_evidence_refuses() -> None:
    older = _finding(1, source=True, page=1)
    with pytest.raises(FindingMatchSuggestionRefused, match="^finding_source_mismatch$"):
        _suggest(source_findings=(replace(older, version_uid=TARGET),))
    with pytest.raises(FindingMatchSuggestionRefused, match="^finding_source_mismatch$"):
        _suggest(source_findings=(replace(older, run_id=TARGET_RUN),))
    with pytest.raises(FindingMatchSuggestionRefused, match="^finding_evidence_page_invalid$"):
        _suggest(source_findings=(replace(older, evidence=(FindingQuote(4, "Quote"),)),))


def test_duplicate_or_cross_version_identity_and_malformed_quote_refuse() -> None:
    older = _finding(1, source=True, page=1)
    with pytest.raises(FindingMatchSuggestionRefused, match="^finding_duplicate$"):
        _suggest(source_findings=(older, older))
    with pytest.raises(FindingMatchSuggestionRefused, match="^finding_identity_crosses_versions$"):
        _suggest(target_findings=(replace(_finding(2, source=False, page=3),
            finding_uid=older.finding_uid),))
    with pytest.raises(FindingMatchSuggestionRefused, match="^quote_invalid$"):
        _suggest(source_findings=(replace(older, evidence=(FindingQuote(1, " \n "),)),))


def test_multi_quote_match_requires_every_source_page_to_be_linked() -> None:
    old = replace(_finding(1, source=True, page=1), evidence=(
        FindingQuote(1, "Проём отсутствует"), FindingQuote(2, "Ось А"),
    ))
    new = replace(_finding(2, source=False, page=3), evidence=(
        FindingQuote(1, "Ось А"), FindingQuote(3, "Проём отсутствует"),
    ))
    assert len(_suggest(source_findings=(old,), target_findings=(new,))) == 1
    assert _suggest(source_findings=(replace(old, evidence=old.evidence +
        (FindingQuote(3, "Другой лист"),)),), target_findings=(new,)) == ()
