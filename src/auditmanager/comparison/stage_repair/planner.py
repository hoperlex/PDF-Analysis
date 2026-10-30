"""Complete deterministic repair plans, restricted to caller-identified problem links."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, replace
from difflib import SequenceMatcher

from .purpose import normalize_title, precheck_purpose, purpose_family, specific_title, subject_tokens
from .types import (
    ContentScore, MapLink, RepairChange, RepairPlan, RepairRefused,
    RevertEligibility, SheetTitle,
)

_EPSILON = 1e-12


def _at_least(value: float, threshold: float) -> bool:
    return value >= threshold - _EPSILON


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _ranking(scores: Sequence[tuple[str, float]]) -> tuple[str, float, float] | None:
    if not scores:
        return None
    ranked = sorted(scores, key=lambda value: (-value[1], value[0]))
    best_id, score = ranked[0]
    return best_id, score, score - (ranked[1][1] if len(ranked) > 1 else 0.0)


def _validate(
    links: Sequence[MapLink], left: Sequence[SheetTitle], right: Sequence[SheetTitle],
    problems: frozenset[str], scores: Sequence[ContentScore],
) -> tuple[dict[str, SheetTitle], dict[str, SheetTitle]]:
    if len(links) > 1_000 or len(left) > 500 or len(right) > 500 or len(scores) > 100_000:
        raise RepairRefused("repair_input_budget_exceeded")
    left_by_id, right_by_id = ({s.profile_id: s for s in sheets} for sheets in (left, right))
    if (len(left_by_id) != len(left) or len(right_by_id) != len(right)
            or left_by_id.keys() & right_by_id.keys()
            or any(not isinstance(s.profile_id, str) or not s.profile_id
                   or not isinstance(s.title, str) or len(s.title) > 512 for s in (*left, *right))):
        raise RepairRefused("sheet_inventory_invalid")
    ids = [link.item_id for link in links]
    if any(not item for item in ids) or len(set(ids)) != len(ids) or not problems <= set(ids):
        raise RepairRefused("link_identity_invalid")
    seen: set[tuple[str | None, str | None]] = set()
    paired_left: set[str] = set()
    paired_right: set[str] = set()
    unmatched_left: set[str] = set()
    unmatched_right: set[str] = set()
    for link in links:
        valid = (
            (link.relation == "paired" and link.left_profile_id in left_by_id
             and link.right_profile_id in right_by_id)
            or (link.relation == "only_left" and link.left_profile_id in left_by_id
                and link.right_profile_id is None)
            or (link.relation == "only_right" and link.left_profile_id is None
                and link.right_profile_id in right_by_id)
        )
        pair = (link.left_profile_id, link.right_profile_id)
        if not valid or pair in seen:
            raise RepairRefused("map_snapshot_invalid")
        seen.add(pair)
        if link.relation == "paired":
            paired_left.add(str(link.left_profile_id))
            paired_right.add(str(link.right_profile_id))
        elif link.relation == "only_left":
            unmatched_left.add(str(link.left_profile_id))
        else:
            unmatched_right.add(str(link.right_profile_id))
    if paired_left & unmatched_left or paired_right & unmatched_right:
        raise RepairRefused("map_unpaired_conflict")
    if scores:
        cells: set[tuple[str, str]] = set()
        for cell in scores:
            key = (cell.left_profile_id, cell.right_profile_id)
            if (key in cells or key[0] not in left_by_id or key[1] not in right_by_id
                    or isinstance(cell.score, bool) or not isinstance(cell.score, (int, float))
                    or not math.isfinite(cell.score) or not 0 <= cell.score <= 1
                    or any(isinstance(value, bool) or not isinstance(value, int) or value < 0
                           for value in (cell.independent_components,
                                         cell.strong_anchor_count, cell.anchor_count))
                    or cell.independent_components > 5
                    or cell.strong_anchor_count > cell.anchor_count
                    or not isinstance(cell.purpose_compatible, bool)):
                raise RepairRefused("content_score_invalid")
            cells.add(key)
        if len(cells) != len(left) * len(right):
            raise RepairRefused("content_matrix_incomplete")
    return left_by_id, right_by_id


def _title_candidate(
    link: MapLink, left: dict[str, SheetTitle], right: dict[str, SheetTitle],
    counts_left: Counter[str], counts_right: Counter[str],
    ratios: dict[tuple[str, str], float],
) -> RepairChange | None:
    target_right = right[str(link.right_profile_id)]
    title = normalize_title(target_right.title)
    exact = [sheet for sheet in left.values() if normalize_title(sheet.title) == title]
    if (specific_title(title) and len(exact) == 1
            and counts_left[title] == counts_right[title] == 1):
        target = exact[0].profile_id
        if target != link.left_profile_id:
            return RepairChange(str(link.item_id), target_right.profile_id,
                                str(link.left_profile_id), target,
                                "TITLE_EXACT", 1.0, 1.0, 1.0, 1.0)
        return None

    def ratio(a: SheetTitle, b: SheetTitle) -> float:
        key = (a.profile_id, b.profile_id)
        if key not in ratios:
            if len(ratios) >= 4_096:
                raise RepairRefused("title_comparison_budget_exceeded")
            compatible = (
                specific_title(a.title) and specific_title(b.title)
                and purpose_family(a.title) is not None
                and purpose_family(a.title) == purpose_family(b.title)
                and bool(subject_tokens(a.title) & subject_tokens(b.title))
            )
            ratios[key] = (SequenceMatcher(None, normalize_title(a.title),
                                           normalize_title(b.title), autojunk=False).ratio()
                           if compatible else 0.0)
        return ratios[key]

    best = _ranking([(sheet.profile_id, ratio(sheet, target_right)) for sheet in left.values()])
    if best is None or best[0] == link.left_profile_id or not (
        _at_least(best[1], 0.94) and _at_least(best[2], 0.02)
    ):
        return None
    reverse = _ranking([(sheet.profile_id, ratio(left[best[0]], sheet)) for sheet in right.values()])
    if reverse is None or reverse[0] != target_right.profile_id or not _at_least(reverse[2], 0.02):
        return None
    return RepairChange(str(link.item_id), target_right.profile_id,
                        str(link.left_profile_id), best[0], "TITLE_MUTUAL_FUZZY",
                        best[1], best[2], reverse[2], 1.0)


def _content_candidate(
    link: MapLink, left: dict[str, SheetTitle], right: dict[str, SheetTitle],
    matrix: dict[tuple[str, str], ContentScore],
) -> RepairChange | None:
    right_id = str(link.right_profile_id)
    best = _ranking([(profile, matrix[profile, right_id].score) for profile in left])
    if best is None or best[0] == link.left_profile_id:
        return None
    cell = matrix[best[0], right_id]
    reverse = _ranking([(profile, matrix[best[0], profile].score) for profile in right])
    improvement = best[1] - matrix[str(link.left_profile_id), right_id].score
    current_purpose = precheck_purpose([left[str(link.left_profile_id)].title], [right[right_id].title])
    target_purpose = precheck_purpose([left[best[0]].title], [right[right_id].title])
    confidence = {"low": 0, "medium": 1, "high": 2}
    if (not _at_least(best[1], 0.44) or not _at_least(best[2], 0.14)
            or reverse is None or reverse[0] != right_id or not _at_least(reverse[2], 0.10)
            or not _at_least(improvement, 0.18) or not cell.purpose_compatible
            or target_purpose.status == "PAIR_REVIEW_REQUIRED"
            or (current_purpose.status == "PAIR_OK"
                and confidence[target_purpose.confidence] < confidence[current_purpose.confidence])
            or cell.independent_components < 2
            or (cell.strong_anchor_count < 1 and cell.anchor_count < 3)):
        return None
    return RepairChange(str(link.item_id), right_id, str(link.left_profile_id), best[0],
                        "CONTENT_UNIQUE_ANCHORS" if cell.strong_anchor_count >= 2 else "CONTENT_MUTUAL_BEST",
                        best[1], best[2], reverse[2], improvement)


def _complete_components(
    proposals: dict[str, RepairChange], links: Sequence[MapLink], eligible_ids: set[str],
) -> dict[str, RepairChange]:
    targets = Counter(change.after_left_profile_id for change in proposals.values())
    proposals = {key: value for key, value in proposals.items()
                 if targets[value.after_left_profile_id] == 1}
    owners: dict[str, list[str]] = {}
    for link in links:
        if link.relation == "paired":
            owners.setdefault(str(link.left_profile_id), []).append(str(link.item_id))
    safe: set[str] = set()
    for start in proposals:
        path: set[str] = set()
        current = start
        while current not in path:
            if current not in proposals:
                break
            path.add(current)
            held_by = owners.get(proposals[current].after_left_profile_id, [])
            if not held_by:
                safe.update(path)
                break
            if len(held_by) != 1 or held_by[0] not in eligible_ids:
                break
            current = held_by[0]
        else:
            # Every displaced link in this closed cycle has its own HIGH proof.
            safe.update(path)
    return {key: change for key, change in proposals.items() if key in safe}


def plan_repairs(
    *, run_id: str, base_revision_id: str, links: Sequence[MapLink],
    left_sheets: Sequence[SheetTitle], right_sheets: Sequence[SheetTitle],
    problem_link_ids: frozenset[str], content_scores: Sequence[ContentScore] = (),
    already_repaired_run_ids: frozenset[str] = frozenset(),
) -> RepairPlan | None:
    """Plan one atomic HIGH repair pass over purpose-problem one-to-one links.

    The returned snapshots are data to record, not persistence authority. Runtime
    must compare ``base_revision_id`` and allocate fresh canonical row IDs when it
    writes the complete after snapshot; ``item_id=None`` marks a new unmatched row.
    """
    if not run_id or not base_revision_id:
        raise RepairRefused("repair_scope_invalid")
    if run_id in already_repaired_run_ids:
        raise RepairRefused("repair_cycle_already_used")
    before = tuple(links)
    left, right = _validate(before, left_sheets, right_sheets, problem_link_ids, content_scores)
    left_count = Counter(link.left_profile_id for link in before if link.relation == "paired")
    right_count = Counter(link.right_profile_id for link in before if link.relation == "paired")
    eligible = [link for link in before if link.item_id in problem_link_ids and link.relation == "paired"
                and left_count[link.left_profile_id] == right_count[link.right_profile_id] == 1]
    counts_left = Counter(normalize_title(sheet.title) for sheet in left.values())
    counts_right = Counter(normalize_title(sheet.title) for sheet in right.values())
    matrix = {(cell.left_profile_id, cell.right_profile_id): cell for cell in content_scores}
    ratios: dict[tuple[str, str], float] = {}
    proposals: dict[str, RepairChange] = {}
    for link in eligible:
        proposal = _title_candidate(link, left, right, counts_left, counts_right, ratios)
        if proposal is None and matrix:
            proposal = _content_candidate(link, left, right, matrix)
        if proposal is not None:
            proposals[str(link.item_id)] = proposal
    safe = _complete_components(proposals, before, {str(link.item_id) for link in eligible})
    if not safe:
        return None
    consumed = {change.after_left_profile_id for change in safe.values()}
    after = [replace(link, left_profile_id=safe[str(link.item_id)].after_left_profile_id,
                     confidence="automatic_repair", source="automatic")
             if link.item_id in safe else link
             for link in before
             if not (link.relation == "only_left" and link.left_profile_id in consumed)]
    paired_after = {link.left_profile_id for link in after if link.relation == "paired"}
    unpaired_after = {link.left_profile_id for link in after if link.relation == "only_left"}
    released = {change.before_left_profile_id for change in safe.values()} - paired_after - unpaired_after
    after.extend(MapLink(None, profile, None, "only_left", "unpaired", "automatic")
                 for profile in sorted(released))
    changes = tuple(safe[str(link.item_id)] for link in before if link.item_id in safe)
    signature = _digest({
        "links": [asdict(link) for link in before],
        "left": [asdict(sheet) for sheet in sorted(left.values(), key=lambda s: s.profile_id)],
        "right": [asdict(sheet) for sheet in sorted(right.values(), key=lambda s: s.profile_id)],
        "problems": sorted(problem_link_ids),
        "content": [asdict(cell) for cell in sorted(content_scores,
                    key=lambda c: (c.left_profile_id, c.right_profile_id))],
    })
    plan_key = _digest({"run_id": run_id, "revision": base_revision_id,
                        "source": signature, "changes": [asdict(change) for change in changes]})
    return RepairPlan(run_id, base_revision_id, signature, plan_key,
                      changes, before, tuple(after))


def revert_eligibility(
    plan: RepairPlan, current_snapshot: Sequence[MapLink], *,
    later_manual_edit: bool, already_reverted: bool = False,
) -> RevertEligibility:
    """A later manual act supersedes repair authority even if it restores its shape."""
    if already_reverted:
        return RevertEligibility(False, "already_reverted")
    if later_manual_edit:
        return RevertEligibility(False, "superseded_by_manual_edit")

    def semantic(snapshot: Sequence[MapLink]) -> tuple[tuple[object, ...], ...]:
        return tuple((row.relation, row.left_profile_id, row.right_profile_id, row.confidence)
                     for row in snapshot)

    if semantic(current_snapshot) != semantic(plan.after_snapshot):
        return RevertEligibility(False, "after_snapshot_no_longer_current")
    return RevertEligibility(True, "current_recorded_repair")
