"""Immutable inputs and the complete map snapshot a C4 service can record."""

from __future__ import annotations

from dataclasses import dataclass


class RepairRefused(ValueError):
    """Malformed or incomplete proof cannot produce an automatic repair plan."""


@dataclass(frozen=True, slots=True)
class SheetTitle:
    profile_id: str
    title: str


@dataclass(frozen=True, slots=True)
class MapLink:
    item_id: str | None
    left_profile_id: str | None
    right_profile_id: str | None
    relation: str = "paired"
    confidence: str = "manual"
    source: str = "expert"


@dataclass(frozen=True, slots=True)
class PurposeCheck:
    status: str
    confidence: str
    reason: str


@dataclass(frozen=True, slots=True)
class ContentScore:
    """One cell of a complete deterministic fingerprint score matrix.

    The caller supplies scores and anchor counts from deterministic stored text,
    never from a model. Components count independent overlaps of at least .22;
    strong anchors are unique designations/systems/equipment/node names.
    """

    left_profile_id: str
    right_profile_id: str
    score: float
    independent_components: int
    strong_anchor_count: int
    anchor_count: int
    purpose_compatible: bool = True


@dataclass(frozen=True, slots=True)
class RepairChange:
    item_id: str
    right_profile_id: str
    before_left_profile_id: str
    after_left_profile_id: str
    rule: str
    score: float
    margin: float
    reverse_margin: float
    improvement: float
    confidence: str = "high"


@dataclass(frozen=True, slots=True)
class RepairPlan:
    run_id: str
    base_revision_id: str
    source_signature: str
    plan_key: str
    changes: tuple[RepairChange, ...]
    before_snapshot: tuple[MapLink, ...]
    after_snapshot: tuple[MapLink, ...]
    confidence: str = "high"


@dataclass(frozen=True, slots=True)
class RevertEligibility:
    eligible: bool
    reason: str
