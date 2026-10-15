"""Offline AR v2 matcher against the committed synthetic manifest."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from evaluation.matcher import (  # noqa: E402
    EvidenceQuote, FindingMember, PredictedGroup, score,
)

MANIFEST = json.loads(
    (ROOT / "fixtures" / "evaluation" / "ar_v2" / "expected_issues.json").read_text()
)


def group(case: dict, *, quote: str | None = None, page: int | None = None,
          category: str | None = None, bundle: str | None = None) -> PredictedGroup:
    evidence = case["evidence"][0]
    return PredictedGroup(
        bundle or case["bundle_id"], category or case["category"],
        (FindingMember((EvidenceQuote(page or evidence["page"],
                                      quote or evidence["quote"]),)),),
    )


def test_empty_predictions_are_zero_recall_with_nonzero_denominators() -> None:
    report = score(MANIFEST, ())
    assert report.recall == 0.0
    assert len(report.missed_issue_ids) == 21
    assert report.control_count == 7
    assert report.control_false_positive_rate == 0.0
    assert report.finding_group_count == 0
    assert len(report.per_category) == 7


def test_one_exact_seeded_match_changes_recall_by_one_twenty_first() -> None:
    first = MANIFEST["issues"][0]
    report = score(MANIFEST, (group(first),))
    assert report.matched_issue_ids == (first["id"],)
    assert report.recall == 1 / 21
    assert len(report.missed_issue_ids) == 20


def test_any_member_may_match_even_when_the_first_member_does_not() -> None:
    first = MANIFEST["issues"][0]
    predicted = PredictedGroup(
        first["bundle_id"], first["category"],
        (
            FindingMember((EvidenceQuote(1, "Совсем другая цитата"),)),
            FindingMember((EvidenceQuote(first["evidence"][0]["page"],
                                         first["evidence"][0]["quote"]),)),
        ),
    )
    assert first["id"] in score(MANIFEST, (predicted,)).matched_issue_ids


def test_substring_works_in_either_direction_on_one_page() -> None:
    first = MANIFEST["issues"][0]
    seeded = first["evidence"][0]["quote"]
    assert first["id"] in score(MANIFEST, (group(first, quote=seeded[:15]),)).matched_issue_ids
    assert first["id"] in score(MANIFEST, (group(first, quote="Контекст: " + seeded),)).matched_issue_ids


@pytest.mark.parametrize("alteration", [
    {"page": 2}, {"category": "roof"}, {"bundle": "ar_v2_10"},
    {"quote": "Здесь нет заявленного факта"},
])
def test_document_category_page_and_quote_boundaries(alteration: dict) -> None:
    first = MANIFEST["issues"][0]
    report = score(MANIFEST, (group(first, **alteration),))
    assert first["id"] not in report.matched_issue_ids
    assert report.unmatched_group_indices == (0,)


def test_a_control_hit_is_false_positive_pressure_not_seeded_recall() -> None:
    control = MANIFEST["controls"][0]
    report = score(MANIFEST, (group(control),))
    assert report.matched_control_ids == (control["id"],)
    assert report.control_false_positive_rate == 1 / 7
    assert report.recall == 0.0
    category = next(item for item in report.per_category if item.category == control["category"])
    assert category.controls_hit == 1 and category.controls_total == 1


def test_one_group_matching_two_seeded_issues_is_reported_as_overmerge() -> None:
    manifest = copy.deepcopy(MANIFEST)
    first, second = manifest["issues"][:2]
    second["bundle_id"] = first["bundle_id"]
    second["category"] = first["category"]
    predicted = PredictedGroup(
        first["bundle_id"], first["category"],
        (
            FindingMember((EvidenceQuote(**first["evidence"][0]),)),
            FindingMember((EvidenceQuote(**second["evidence"][0]),)),
        ),
    )
    report = score(manifest, (predicted,))
    assert report.overmerged_groups == ((0, tuple(sorted((first["id"], second["id"])))),)
    assert set(report.matched_issue_ids) == {first["id"], second["id"]}


def test_duplicate_predictions_do_not_inflate_seeded_recall() -> None:
    first = MANIFEST["issues"][0]
    report = score(MANIFEST, (group(first), group(first)))
    assert report.matched_issue_ids == (first["id"],)
    assert report.finding_group_count == 2


def test_a_report_keeps_findings_matching_neither_gold_set() -> None:
    first = MANIFEST["issues"][0]
    report = score(MANIFEST, (group(first, quote="Неведомый факт на этом листе"),))
    assert report.unmatched_group_indices == (0,)


def test_an_empty_or_duplicate_or_mislabelled_ground_truth_is_refused() -> None:
    empty = copy.deepcopy(MANIFEST)
    empty["issues"] = []
    with pytest.raises(ValueError, match="no issues"):
        score(empty, ())
    duplicate = copy.deepcopy(MANIFEST)
    duplicate["controls"][0]["id"] = duplicate["issues"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        score(duplicate, ())
    false_control = copy.deepcopy(MANIFEST)
    false_control["controls"][0]["expected_finding"] = True
    with pytest.raises(ValueError, match="not a negative control"):
        score(false_control, ())


def test_a_prediction_without_an_observation_is_refused() -> None:
    first = MANIFEST["issues"][0]
    with pytest.raises(ValueError, match="no observation members"):
        score(MANIFEST, (PredictedGroup(first["bundle_id"], first["category"], ()),))


def test_an_unknown_predicted_category_is_refused() -> None:
    first = MANIFEST["issues"][0]
    with pytest.raises(ValueError, match="invalid bundle or category"):
        score(MANIFEST, (group(first, category="invented_category"),))
