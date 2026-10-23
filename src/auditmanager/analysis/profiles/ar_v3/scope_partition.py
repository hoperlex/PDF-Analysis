"""Pure, unserved AR v3 candidate partition for the measured C01–C22 map.

The groups encode a technical budget proposal, not legal applicability or Run
authority. A later owner must bind a selected scope to a reviewed map, qualified
set and Run. Rendering remains with the norms context behind its public surface.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar


PARTITION_VERSION = "ar-scope-partition-prep-v1"
PROMPT_CHAR_CAP = 22_000
_EXPECTED_IDS = tuple(f"C{number:02d}" for number in range(1, 23))
_MEMBERS = (
    ("F1", _EXPECTED_IDS[0:3]),
    ("F2", _EXPECTED_IDS[3:10]),
    ("A1", _EXPECTED_IDS[10:14]),
    ("A2", _EXPECTED_IDS[14:20]),
    ("S1", _EXPECTED_IDS[20:21]),
    ("S2", _EXPECTED_IDS[21:22]),
)


class ScopePartitionRefused(ValueError):
    """The candidate set or rendered part cannot form this technical scope."""


class CandidateItem(Protocol):
    item_id: str


ItemT = TypeVar("ItemT", bound=CandidateItem)


@dataclass(frozen=True, slots=True)
class ScopeGroup(Generic[ItemT]):
    scope_id: str
    item_ids: tuple[str, ...]
    items: tuple[ItemT, ...]


@dataclass(frozen=True, slots=True)
class ScopePlan(Generic[ItemT]):
    groups: tuple[ScopeGroup[ItemT], ...]
    composition_sha256: str

    def group(self, scope_id: str) -> ScopeGroup[ItemT]:
        for group in self.groups:
            if group.scope_id == scope_id:
                return group
        raise ScopePartitionRefused("unknown scope id")


@dataclass(frozen=True, slots=True)
class ScopeMembership:
    scope_id: str
    item_ids: tuple[str, ...]
    composition_sha256: str


@dataclass(frozen=True, slots=True)
class RenderedScope:
    scope_id: str
    item_ids: tuple[str, ...]
    composition_sha256: str
    prompt_part_sha256: str
    prompt_part_characters: int


def _composition_sha256() -> str:
    payload = {
        "version": PARTITION_VERSION,
        "groups": [
            {"scope_id": scope_id, "item_ids": item_ids}
            for scope_id, item_ids in _MEMBERS
        ],
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def scope_membership(scope_id: str) -> ScopeMembership:
    """Return fixed membership without accepting caller-supplied item ordering."""
    for known_id, item_ids in _MEMBERS:
        if scope_id == known_id:
            return ScopeMembership(known_id, item_ids, _composition_sha256())
    raise ScopePartitionRefused("unknown scope id")


def plan_scope_partition(items: tuple[ItemT, ...]) -> ScopePlan[ItemT]:
    """Require every C01–C22 once and return the fixed six-group composition.

    Input order cannot change group order or digest. Source targets and branch
    eligibility are deliberately outside this planner's authority.
    """
    if not isinstance(items, tuple):
        raise ScopePartitionRefused("candidate items must be a tuple")
    by_id: dict[str, ItemT] = {}
    for item in items:
        item_id = getattr(item, "item_id", None)
        if not isinstance(item_id, str) or item_id not in _EXPECTED_IDS:
            raise ScopePartitionRefused("unknown candidate item")
        if item_id in by_id:
            raise ScopePartitionRefused("duplicate candidate item")
        by_id[item_id] = item
    if len(by_id) != len(_EXPECTED_IDS):
        raise ScopePartitionRefused("missing candidate item")
    members = tuple(item_id for _, item_ids in _MEMBERS for item_id in item_ids)
    if members != _EXPECTED_IDS or len({scope_id for scope_id, _ in _MEMBERS}) != 6:
        raise ScopePartitionRefused("scope partition definition invalid")
    groups = tuple(
        ScopeGroup(scope_id, item_ids, tuple(by_id[item_id] for item_id in item_ids))
        for scope_id, item_ids in _MEMBERS
    )
    return ScopePlan(groups, _composition_sha256())


def validate_rendered_scope(
    plan: ScopePlan[ItemT], scope_id: str, prompt_part: str,
) -> RenderedScope:
    """Record the exact W57 prompt part, refusing an empty or over-cap render.

    This is a size/digest check, not a source or renderer authenticity check.
    The caller must supply the unchanged W57 rendering of ``plan.group(...).items``.
    """
    if not isinstance(plan, ScopePlan):
        raise ScopePartitionRefused("scope plan composition invalid")
    try:
        replay = plan_scope_partition(tuple(item for group in plan.groups for item in group.items))
    except (AttributeError, ScopePartitionRefused) as exc:
        raise ScopePartitionRefused("scope plan composition invalid") from exc
    if plan != replay:
        raise ScopePartitionRefused("scope plan composition invalid")
    group = plan.group(scope_id)
    if not isinstance(prompt_part, str) or not 1 <= len(prompt_part) <= PROMPT_CHAR_CAP:
        raise ScopePartitionRefused("rendered prompt part exceeds character cap or is empty")
    return RenderedScope(
        scope_id=scope_id,
        item_ids=group.item_ids,
        composition_sha256=plan.composition_sha256,
        prompt_part_sha256=hashlib.sha256(prompt_part.encode("utf-8")).hexdigest(),
        prompt_part_characters=len(prompt_part),
    )


__all__ = [
    "PARTITION_VERSION", "PROMPT_CHAR_CAP", "RenderedScope", "ScopeGroup",
    "ScopeMembership", "ScopePartitionRefused", "ScopePlan", "plan_scope_partition",
    "scope_membership",
    "validate_rendered_scope",
]
