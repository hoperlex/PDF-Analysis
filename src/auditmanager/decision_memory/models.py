"""The values of the capture: what a case is made of, and the digest that proves it is the same case.

Plain frozen dataclasses with no behaviour beyond validation and the content digest. They are built by the capture assembler in the
composition root (``bootstrap/adapters.py``), which reads the other contexts, and written by :mod:`auditmanager.decision_memory.repository`.
Nothing here reads a database.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_id

#: The shape of what a capture writes. A change to the content of a case is a new version here, never an edit of an old case.
CAPTURE_VERSION: Final[str] = "dm-capture/1"

#: Where a memory decision came from. ``carried`` is exactly an event with ``carried_from_decision_id`` (`D-337`); ``imported`` is a
#: decision read back from a run's workbook (`D-391`: the import does not say so yet, so it is captured ``direct``).
ORIGIN_KINDS: Final[frozenset[str]] = frozenset({"direct", "carried", "imported"})

#: ``test`` or ``real``; an installation setting from phase M2 on (`D-390`). Every case of this phase is ``test``.
DATA_CLASSES: Final[frozenset[str]] = frozenset({"test", "real"})

#: The event types that are captured (`Q8`): a ``comment`` is not a decision.
CAPTURED_EVENT_TYPES: Final[frozenset[str]] = frozenset({"accept", "reject"})
VERDICT_FOR_CAPTURED_EVENT: Final[dict[str, str]] = {"accept": "accepted", "reject": "rejected"}

#: At most this many crop images a case references (`Q6`).
CROP_CAP: Final[int] = 4

#: The rule that picked a case's crops. v1 takes the portal image-block crops of the pages the evidence names, with no geometric test
#: against the evidence block (`D-392`); the name is stored on every crop so a better rule is distinguishable later.
SELECTION_RULE_PAGE_IMAGES: Final[str] = "page_images/1"

CROP_KIND_PORTAL_IMAGE_BLOCK: Final[str] = "portal_image_block"
CROP_MEDIA_TYPE: Final[str] = "image/png"

CROP_STATE_REFERENCED: Final[str] = "referenced"
CROP_STATE_NONE_AVAILABLE: Final[str] = "none_available"


def _invalid(message: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, message=message)


@dataclass(frozen=True, slots=True)
class CaseOrigin:
    """Where a case came from. Identities that resolve nowhere once the project is erased."""

    observation_id: str
    finding_uid: str
    project_uid: str
    document_uid: str
    version_uid: str
    run_id: str


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One quoted span the expert looked at. ``bbox`` is ``(x0, y0, x1, y1)`` in ``bbox_unit`` with ``bbox_origin``, or ``None``."""

    ordinal: int
    page_number: int
    quote: str
    char_start: int
    char_end: int
    block_ref: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    bbox_unit: str | None = None
    bbox_origin: str | None = None

    def __post_init__(self) -> None:
        if (self.bbox is None) != (self.bbox_unit is None) or (self.bbox is None) != (self.bbox_origin is None):
            raise _invalid("an evidence box carries its unit and origin, and neither without the box")


@dataclass(frozen=True, slots=True)
class NormRef:
    """One certified normative reference: ids that stay resolvable (the corpus is kept whole) and the quoted norm text."""

    ordinal: int
    norms_snapshot_id: str
    norm_document_id: str
    norm_paragraph_id: str
    designation: str
    clause_number: str | None
    page_label: int
    quote: str
    citation_state: str


@dataclass(frozen=True, slots=True)
class CropRef:
    """A reference to a crop image that already exists as a Blob (a binding, not a copy)."""

    ordinal: int
    evidence_ordinal: int | None
    selection_rule: str
    page_number: int
    bbox: tuple[float, float, float, float]
    blob_id: str
    sha256: str
    size_bytes: int
    width_px: int
    height_px: int
    source_ref: str
    portal_description: str | None = None
    kind: str = CROP_KIND_PORTAL_IMAGE_BLOCK
    media_type: str = CROP_MEDIA_TYPE

    def __post_init__(self) -> None:
        parse_blob_id(self.blob_id)
        if not 1 <= self.ordinal <= CROP_CAP:
            raise _invalid(f"a case references at most {CROP_CAP} crops")


@dataclass(frozen=True, slots=True)
class CaseContent:
    """The observation's immutable content: what the model proposed and the evidence it stood on."""

    category: str
    finding_text: str
    recommendation_text: str
    proposed_severity: str | None
    required_value: str | None
    stated_value: str | None
    stage_id: str
    analysis_profile_id: str
    prompt_bundle_id: str
    provider_mode: str
    evidence: tuple[EvidenceItem, ...]
    norm_refs: tuple[NormRef, ...]


@dataclass(frozen=True, slots=True)
class DecisionFact:
    """One ledger event, as the memory keeps it."""

    source_decision_id: str
    event_type: str
    severity: str | None
    comment: str | None
    author_user_uid: str | None
    origin_kind: str
    decided_at: datetime

    def __post_init__(self) -> None:
        if self.event_type not in CAPTURED_EVENT_TYPES:
            raise _invalid(f"{self.event_type!r} is not a captured decision event")
        if self.origin_kind not in ORIGIN_KINDS:
            raise _invalid(f"{self.origin_kind!r} is not a decision origin")
        if self.origin_kind == "carried" and self.comment is not None:
            # `decision_memory_decision_text` is the expert's own words. A carried event's ledger comment is the system's rendering of
            # its provenance (`decisions.carryover.carryover_comment`: identities of the source finding, decision and versions), not
            # anything the expert wrote, so it is not stored as theirs; `origin_kind = carried` says where the decision came from.
            raise _invalid("a carried decision stores no comment text: its ledger comment is the system's, not the expert's")

    @property
    def verdict(self) -> str:
        return VERDICT_FOR_CAPTURED_EVENT[self.event_type]


@dataclass(frozen=True, slots=True)
class CaptureSnapshot:
    """Everything one capture writes.

    ``crops`` and the geometry of the evidence are read from published artifacts only when the case does not exist yet, so a second
    decision on a known observation carries none (and the repository would write none): the case is a snapshot of the first.
    """

    origin: CaseOrigin
    content: CaseContent
    section_code: str | None
    data_class: str
    crops: tuple[CropRef, ...]
    decision: DecisionFact

    def __post_init__(self) -> None:
        if self.data_class not in DATA_CLASSES:
            raise _invalid(f"{self.data_class!r} is not a data class")
        if len(self.crops) > CROP_CAP:
            raise _invalid(f"a case references at most {CROP_CAP} crops")


@dataclass(frozen=True, slots=True)
class CaptureResult:
    """What a capture did: the identities of the case and the decision, and which of them it created."""

    case_id: str
    memory_decision_id: str | None
    case_created: bool
    decision_created: bool


def content_digest(content: CaseContent) -> str:
    """SHA-256 over the observation's immutable content, as sorted-key JSON without insignificant whitespace.

    It covers the finding, its provenance classifiers, the evidence (page, quote, offsets, block reference) and the normative references
    -- everything that comes from immutable rows -- and **not** the box geometry, the crops, the section or the data class, which are read
    from artifacts or settings that may differ between the first decision on an observation and a later one. So a later decision on the
    same observation always produces the digest of the first, and a different digest means the stored observation itself differs, which
    no ledger event can cause (a conflict, never an overwrite).
    """
    body = {
        "category": content.category,
        "finding_text": content.finding_text,
        "recommendation_text": content.recommendation_text,
        "proposed_severity": content.proposed_severity,
        "required_value": content.required_value,
        "stated_value": content.stated_value,
        "stage_id": content.stage_id,
        "analysis_profile_id": content.analysis_profile_id,
        "prompt_bundle_id": content.prompt_bundle_id,
        "provider_mode": content.provider_mode,
        "evidence": [
            [e.ordinal, e.page_number, e.quote, e.char_start, e.char_end, e.block_ref] for e in content.evidence
        ],
        "norm_refs": [
            [
                n.ordinal, n.norms_snapshot_id, n.norm_document_id, n.norm_paragraph_id, n.designation,
                n.clause_number, n.page_label, n.quote, n.citation_state,
            ]
            for n in content.norm_refs
        ],
    }
    encoded = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
