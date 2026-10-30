"""Immutable source and result DTOs for Stage AI, independent of transport/storage."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Final

STATUSES: Final = ("SAME", "MOVED", "CHANGED", "REMOVED", "ADDED", "UNCERTAIN")
CONFIDENCES: Final = ("high", "medium", "low")
CLASSES: Final = ("PROJECT_CHANGE", "SERVICE_STRUCTURE", "REVIEW")
CATEGORIES: Final = (
    "areas", "floors", "electrical_load", "calculation_method", "consumer_composition",
    "room_composition", "dimensions", "materials", "equipment_parameters", "system_configuration",
    "fire_safety", "designation_rename", "administrative", "documentation_structure", "formatting",
    "other_project", "other_service", "uncertain",
)
SYSTEMS: Final = (
    "unknown", "architecture", "structural", "electrical", "heating_ventilation", "water_sewage",
    "fire_protection", "low_current", "technology", "site", "other",
)
SYNTHESIS_DECISIONS: Final = ("REAL_CHANGE", "DETAIL_ONLY", "NO_HIGH_LEVEL_CHANGE", "INSUFFICIENT_CONTEXT")
HIGH_LEVEL_TYPES: Final = (
    "DESIGN_PRINCIPLE_CHANGED", "SYSTEM_OPERATION_CHANGED", "SYSTEM_STRUCTURE_CHANGED",
    "SPACE_PROGRAM_CHANGED", "CALCULATION_APPROACH_CHANGED", "PARAMETER_SET_CHANGED",
    "EQUIPMENT_OR_MATERIAL_CHANGED", "QUANTITY_OR_CAPACITY_CHANGED", "DETAIL_LEVEL_INCREASED",
    "NO_HIGH_LEVEL_CHANGE", "UNRESOLVED_HIGH_LEVEL_CHANGE",
)
_ULID = r"[0-9A-HJKMNP-TV-Z]{26}"
_OPAQUE = re.compile(rf"^[a-z][a-z0-9]{{1,7}}_{_ULID}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def require_id(value: str, prefix: str | None = None) -> None:
    if not isinstance(value, str) or not _OPAQUE.fullmatch(value) or (prefix and not value.startswith(prefix + "_")):
        raise ValueError("source_identity_invalid")


def require_digest(value: str) -> None:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError("source_digest_invalid")


@dataclass(frozen=True, slots=True)
class Fragment:
    fragment_id: str
    profile_id: str
    side: str
    text: str
    content_key: str
    box: tuple[float, float, float, float]
    source_kind: str = "native_pdf_text"

    def __post_init__(self) -> None:
        require_id(self.fragment_id, "stf")
        require_id(self.profile_id, "cpr")
        require_digest(self.content_key)
        if self.side not in {"left", "right"} or self.source_kind not in {"native_pdf_text", "recognised_text"}:
            raise ValueError("fragment_provenance_invalid")
        if not isinstance(self.text, str) or not 1 <= len(self.text) <= 20_000:
            raise ValueError("fragment_text_invalid")
        if (not isinstance(self.box, tuple) or len(self.box) != 4
                or any(type(v) not in {int, float} or not math.isfinite(v) for v in self.box)
                or not (0 <= self.box[0] < self.box[2] and 0 <= self.box[1] < self.box[3])):
            raise ValueError("fragment_box_invalid")

    def document(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewItem:
    evidence_id: str
    left_fragment_ids: tuple[str, ...]
    right_fragment_ids: tuple[str, ...]
    deterministic_status: str

    def __post_init__(self) -> None:
        require_id(self.evidence_id)
        if not isinstance(self.left_fragment_ids, tuple) or not isinstance(self.right_fragment_ids, tuple):
            raise ValueError("review_item_fragments_must_be_immutable")
        for fragment_id in self.left_fragment_ids + self.right_fragment_ids:
            require_id(fragment_id, "stf")
        if (not self.left_fragment_ids and not self.right_fragment_ids
                or self.deterministic_status not in STATUSES):
            raise ValueError("review_item_invalid")
        if (len(set(self.left_fragment_ids)) != len(self.left_fragment_ids)
                or len(set(self.right_fragment_ids)) != len(self.right_fragment_ids)):
            raise ValueError("review_item_duplicate_fragment")
        if ((self.deterministic_status in {"SAME", "MOVED", "CHANGED"}
             and not (self.left_fragment_ids and self.right_fragment_ids))
                or (self.deterministic_status == "REMOVED" and (not self.left_fragment_ids or self.right_fragment_ids))
                or (self.deterministic_status == "ADDED" and (self.left_fragment_ids or not self.right_fragment_ids))):
            raise ValueError("review_item_shape_invalid")


@dataclass(frozen=True, slots=True)
class ReviewGroup:
    group_id: str
    fragments: tuple[Fragment, ...]
    items: tuple[ReviewItem, ...]
    accepted_left_profiles: tuple[str, ...]
    accepted_right_profiles: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(not isinstance(value, tuple) for value in (
            self.fragments, self.items, self.accepted_left_profiles, self.accepted_right_profiles,
        )):
            raise ValueError("review_group_must_be_immutable")


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    left_fragment_ids: tuple[str, ...]
    right_fragment_ids: tuple[str, ...]
    status: str
    confidence: str
    summary: str
    reason: str
    actual_right_profile_ids: tuple[str, ...]
    model_status: str
    policy_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReviewResult:
    group_id: str
    source_sha256: str
    decisions: tuple[ReviewDecision, ...]
    raw_evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AtomicEvidence:
    evidence_id: str
    content_key: str
    source_status: str
    left_fragment_ids: tuple[str, ...]
    right_fragment_ids: tuple[str, ...]
    before: str
    after: str
    summary: str
    class_hint: str = "UNCLASSIFIED"
    source_kind: str = "TEXT"

    def __post_init__(self) -> None:
        require_id(self.evidence_id)
        require_digest(self.content_key)
        if not isinstance(self.left_fragment_ids, tuple) or not isinstance(self.right_fragment_ids, tuple):
            raise ValueError("atomic_evidence_must_be_immutable")
        if self.source_status not in STATUSES or self.class_hint not in (*CLASSES, "UNCLASSIFIED"):
            raise ValueError("atomic_evidence_status_invalid")
        if self.source_kind not in {"TEXT", "TABLE", "GRAPHIC"}:
            raise ValueError("atomic_evidence_kind_invalid")
        if not self.left_fragment_ids and not self.right_fragment_ids and self.source_kind != "GRAPHIC":
            raise ValueError("atomic_evidence_empty")
        for fragment_id in self.left_fragment_ids + self.right_fragment_ids:
            require_id(fragment_id, "stf")
        if len(set(self.left_fragment_ids + self.right_fragment_ids)) != len(self.left_fragment_ids + self.right_fragment_ids):
            raise ValueError("atomic_evidence_duplicate_fragment")
        if self.source_kind != "GRAPHIC" and (
            (self.source_status in {"SAME", "MOVED", "CHANGED"} and not (self.left_fragment_ids and self.right_fragment_ids))
            or (self.source_status == "REMOVED" and (not self.left_fragment_ids or self.right_fragment_ids))
            or (self.source_status == "ADDED" and (self.left_fragment_ids or not self.right_fragment_ids))
        ):
            raise ValueError("atomic_evidence_shape_invalid")
        if any(not isinstance(value, str) or len(value) > 20_000
               for value in (self.before, self.after, self.summary)):
            raise ValueError("atomic_evidence_text_invalid")


@dataclass(frozen=True, slots=True)
class EvidenceGroup:
    group_id: str
    evidence: tuple[AtomicEvidence, ...]
    source_link_uncertain: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence_group_must_be_immutable")


@dataclass(frozen=True, slots=True)
class ClassifiedCard:
    card_key: str
    evidence_digest: str
    class_name: str
    category: str
    title: str
    system: str
    evidence_ids: tuple[str, ...]
    model_class: str
    policy_reasons: tuple[str, ...] = ()
    materiality: str = "unknown"
    importance: str = "unknown"
    detail_increased: bool = False

    def __post_init__(self) -> None:
        require_digest(self.card_key)
        require_digest(self.evidence_digest)
        if (not isinstance(self.materiality, str) or self.materiality not in {"material", "non_material", "unknown"}
                or not isinstance(self.importance, str) or self.importance not in {"high", "normal", "unknown"}
                or type(self.detail_increased) is not bool):
            raise ValueError("classified_card_hint_invalid")
        if (self.class_name not in CLASSES or self.model_class not in CLASSES
                or self.category not in CATEGORIES or self.system not in SYSTEMS):
            raise ValueError("classified_card_enum_invalid")
        if (not isinstance(self.evidence_ids, tuple) or not self.evidence_ids
                or len(self.evidence_ids) != len(set(self.evidence_ids))):
            raise ValueError("classified_card_evidence_invalid")
        for evidence_id in self.evidence_ids:
            require_id(evidence_id)
        if not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 260:
            raise ValueError("classified_card_title_invalid")


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    group_id: str
    source_sha256: str
    cards: tuple[ClassifiedCard, ...]


@dataclass(frozen=True, slots=True)
class SynthesisGroup:
    group_id: str
    evidence: tuple[AtomicEvidence, ...]
    cards: tuple[ClassifiedCard, ...]
    source_link_uncertain: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, tuple) or not isinstance(self.cards, tuple):
            raise ValueError("synthesis_group_must_be_immutable")


@dataclass(frozen=True, slots=True)
class HighLevelChange:
    group_id: str
    source_sha256: str
    evidence_ids: tuple[str, ...]
    decision: str
    change_type: str
    title: str
    reason: str
