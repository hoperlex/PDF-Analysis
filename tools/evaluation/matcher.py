"""Mechanical AR v2 evidence matching from PC-02 protocol §11.

Run identities never enter matching. A group's every observation member is
eligible; over-merge is reported when one group matches multiple seeded cases.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class EvidenceQuote:
    page: int
    quote: str


@dataclass(frozen=True, slots=True)
class FindingMember:
    evidence: tuple[EvidenceQuote, ...]


@dataclass(frozen=True, slots=True)
class PredictedGroup:
    bundle_id: str
    category: str
    members: tuple[FindingMember, ...]


@dataclass(frozen=True, slots=True)
class _GroundCase:
    identifier: str
    bundle_id: str
    category: str
    evidence: tuple[EvidenceQuote, ...]


@dataclass(frozen=True, slots=True)
class CategoryScore:
    category: str
    issues_found: int
    issues_total: int
    controls_hit: int
    controls_total: int

    @property
    def recall(self) -> float:
        return self.issues_found / self.issues_total

    @property
    def control_false_positive_rate(self) -> float:
        return self.controls_hit / self.controls_total


@dataclass(frozen=True, slots=True)
class MatchReport:
    matched_issue_ids: tuple[str, ...]
    missed_issue_ids: tuple[str, ...]
    matched_control_ids: tuple[str, ...]
    control_count: int
    finding_group_count: int
    unmatched_group_indices: tuple[int, ...]
    overmerged_groups: tuple[tuple[int, tuple[str, ...]], ...]
    per_category: tuple[CategoryScore, ...]

    @property
    def recall(self) -> float:
        total = len(self.matched_issue_ids) + len(self.missed_issue_ids)
        return len(self.matched_issue_ids) / total

    @property
    def control_false_positive_rate(self) -> float:
        return len(self.matched_control_ids) / self.control_count


def _evidence(raw: object, where: str) -> tuple[EvidenceQuote, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{where}: evidence must be a nonempty list")
    items = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError(f"{where}: evidence item must be an object")
        page, quote = item.get("page"), item.get("quote")
        if type(page) is not int or page < 1 or not isinstance(quote, str) or not quote:
            raise ValueError(f"{where}: invalid evidence page or quote")
        items.append(EvidenceQuote(page, quote))
    return tuple(items)


def _ground_truth(manifest: Mapping[str, object]) -> tuple[tuple[_GroundCase, ...], tuple[_GroundCase, ...]]:
    if manifest.get("schema") != "ar-v2-seeded/1":
        raise ValueError("unexpected seeded manifest schema")
    if manifest.get("profile") != "ar_v2":
        raise ValueError("unexpected seeded analysis profile")
    bundles = manifest.get("bundles")
    if not isinstance(bundles, list) or not bundles:
        raise ValueError("seeded manifest has no bundles")
    bundle_ids: set[str] = set()
    for item in bundles:
        if not isinstance(item, Mapping):
            raise ValueError("seeded manifest has an invalid bundle")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in bundle_ids:
            raise ValueError("seeded manifest has duplicate or invalid bundle IDs")
        bundle_ids.add(identifier)
    all_ids: set[str] = set()

    def parse(key: str) -> tuple[_GroundCase, ...]:
        raw = manifest.get(key)
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"seeded manifest has no {key}")
        cases = []
        for position, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise ValueError(f"{key}[{position}] is not an object")
            identifier = item.get("id")
            bundle_id = item.get("bundle_id")
            category = item.get("category")
            if not isinstance(identifier, str) or not identifier or identifier in all_ids:
                raise ValueError(f"{key}[{position}] has a duplicate or invalid ID")
            all_ids.add(identifier)
            if (not isinstance(bundle_id, str) or bundle_id not in bundle_ids
                    or not isinstance(category, str) or not category):
                raise ValueError(f"{identifier} has an invalid bundle or category")
            if key == "controls" and item.get("expected_finding") is not False:
                raise ValueError(f"{identifier} is not a negative control")
            cases.append(_GroundCase(identifier, bundle_id, category,
                                     _evidence(item.get("evidence"), identifier)))
        return tuple(cases)

    issues, controls = parse("issues"), parse("controls")
    categories = {case.category for case in issues}
    if categories != {case.category for case in controls}:
        raise ValueError("issue and control category sets differ")
    return issues, controls


def _validate_predictions(
    groups: Sequence[PredictedGroup], bundle_ids: set[str], categories: set[str]
) -> None:
    for index, group in enumerate(groups):
        if (not isinstance(group.bundle_id, str) or group.bundle_id not in bundle_ids
                or not isinstance(group.category, str) or group.category not in categories):
            raise ValueError(f"group {index} has an invalid bundle or category")
        if not group.members:
            raise ValueError(f"group {index} has no observation members")
        for member in group.members:
            if not member.evidence:
                raise ValueError(f"group {index} has a member without evidence")
            for citation in member.evidence:
                if (type(citation.page) is not int or citation.page < 1
                        or not isinstance(citation.quote, str) or not citation.quote):
                    raise ValueError(f"group {index} has invalid evidence")


def _matches(group: PredictedGroup, case: _GroundCase) -> bool:
    if group.bundle_id != case.bundle_id or group.category != case.category:
        return False
    return any(
        predicted.page == seeded.page
        and (predicted.quote in seeded.quote or seeded.quote in predicted.quote)
        for member in group.members
        for predicted in member.evidence
        for seeded in case.evidence
    )


def score(manifest: Mapping[str, object], groups: Sequence[PredictedGroup]) -> MatchReport:
    """Score on evidence; zero predictions produce zero recall, never vacuous pass."""
    issues, controls = _ground_truth(manifest)
    _validate_predictions(
        groups,
        {item["id"] for item in manifest["bundles"]},  # type: ignore[index]
        {case.category for case in issues},
    )
    found: set[str] = set()
    control_hits: set[str] = set()
    unmatched = []
    overmerged = []
    for index, group in enumerate(groups):
        matched_issues = tuple(sorted(case.identifier for case in issues if _matches(group, case)))
        matched_controls = tuple(sorted(case.identifier for case in controls if _matches(group, case)))
        found.update(matched_issues)
        control_hits.update(matched_controls)
        if not matched_issues and not matched_controls:
            unmatched.append(index)
        if len(matched_issues) > 1:
            overmerged.append((index, matched_issues))

    issue_totals = Counter(case.category for case in issues)
    control_totals = Counter(case.category for case in controls)
    issue_by_id = {case.identifier: case.category for case in issues}
    control_by_id = {case.identifier: case.category for case in controls}
    found_categories = Counter(issue_by_id[identifier] for identifier in found)
    hit_categories = Counter(control_by_id[identifier] for identifier in control_hits)
    per_category = tuple(
        CategoryScore(category, found_categories[category], issue_totals[category],
                      hit_categories[category], control_totals[category])
        for category in sorted(issue_totals)
    )
    return MatchReport(
        matched_issue_ids=tuple(sorted(found)),
        missed_issue_ids=tuple(sorted(set(issue_by_id) - found)),
        matched_control_ids=tuple(sorted(control_hits)),
        control_count=len(controls),
        finding_group_count=len(groups),
        unmatched_group_indices=tuple(unmatched),
        overmerged_groups=tuple(overmerged),
        per_category=per_category,
    )
