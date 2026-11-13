"""The values of the capture: what a case is made of, and the digest that proves it is the same case.

Plain frozen dataclasses with no behaviour beyond validation and the content digest. They are built by the capture assembler in the
composition root (``bootstrap/adapters.py``), which reads the other contexts, and written by :mod:`auditmanager.decision_memory.repository`.
Nothing here reads a database.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId, IdentityError
from auditmanager.storage.public import parse_blob_id

#: The shape of what a capture writes. A change to the content of a case is a new version here, never an edit of an old case.
CAPTURE_VERSION: Final[str] = "dm-capture/1"
#: `F8-PUBLISH` (ADR-0029 decision 7): the capture of a case whose evidence is blocks. A case with block evidence is written under this version;
#: a case without it stays ``dm-capture/1`` byte for byte (:func:`capture_version_of`), so an old case and its digest are never touched.
CAPTURE_VERSION_BLOCK_EVIDENCE: Final[str] = "dm-capture/2"

#: Where a memory decision came from. ``carried`` is exactly an event with ``carried_from_decision_id`` (`D-337`); ``imported`` is a
#: decision read back from a run's workbook (`D-391`: the import does not say so yet, so it is captured ``direct``).
ORIGIN_KINDS: Final[frozenset[str]] = frozenset({"direct", "carried", "imported"})

#: ``test`` or ``real``; an installation setting from phase M2 on (`D-390`). Every case of this phase is ``test``.
DATA_CLASSES: Final[frozenset[str]] = frozenset({"test", "real"})

#: The event types that are captured as decisions (`Q8`): a ``comment`` is not a decision.
CAPTURED_EVENT_TYPES: Final[frozenset[str]] = frozenset({"accept", "reject"})
#: The ledger event whose text is kept in ``decision_memory_comment``, a table of its own beside the decisions (`ADR-0029` decision 10,
#: `R-153ag`). It never makes a case and never changes a vote.
COMMENT_EVENT_TYPE: Final[str] = "comment"
#: The length ceiling of ``decision_memory_comment.comment`` (the ledger's own is the same, ``ck_expert_decision_event_comment_length``).
COMMENT_MAX_CHARS: Final[int] = 4000

#: What :meth:`MemoryRepository.capture_comment` did with a comment event.
COMMENT_CAPTURED: Final[str] = "captured"
COMMENT_ALREADY_CAPTURED: Final[str] = "already_captured"
#: The observation has no case yet. Nothing is lost: the comment is carried over by the capture of the case's first ✓/✕, which is handed
#: the earlier comments of the observation (:attr:`CaptureSnapshot.earlier_comments`).
COMMENT_WAITS_FOR_CASE: Final[str] = "waits_for_case"
#: The case was forgotten: it takes no words back (`ADR-0027`, the forget guard). Not an error, and not stored.
COMMENT_REFUSED_CASE_FORGOTTEN: Final[str] = "case_forgotten"
COMMENT_OUTCOMES: Final[frozenset[str]] = frozenset(
    {COMMENT_CAPTURED, COMMENT_ALREADY_CAPTURED, COMMENT_WAITS_FOR_CASE, COMMENT_REFUSED_CASE_FORGOTTEN}
)
VERDICT_FOR_CAPTURED_EVENT: Final[dict[str, str]] = {"accept": "accepted", "reject": "rejected"}

#: At most this many crop images a case references (`Q6`).
CROP_CAP: Final[int] = 4

#: The rule that picked a case's crops. v1 takes the portal image-block crops of the pages the evidence names, with no geometric test
#: against the evidence block (`D-392`); the name is stored on every crop so a better rule is distinguishable later.
SELECTION_RULE_PAGE_IMAGES: Final[str] = "page_images/1"

#: The rule of ``dm-capture/2``: the crop of the block the evidence names, not the crops of the page (`F8-PUBLISH`).
SELECTION_RULE_BLOCK_CROP: Final[str] = "block_crop/1"

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


_PORTAL_BLOCK_ID = re.compile(r"blk_[0-9a-f]{32}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
#: ``ck_decision_memory_block_evidence_recognised_quote``.
BLOCK_QUOTE_MAX_CHARS: Final[int] = 2000


@dataclass(frozen=True, slots=True)
class BlockEvidenceFact:
    """One block a candidate case stood on (`dm-capture/2`, ``decision_memory_block_evidence``): where it is, the crop on record, an optional quote.

    ``bbox`` is the block's normalised box in the page, ``(x0, y0, x1, y1)``, from the run's verified geometry. A block link proves a place,
    not a content (ADR-0029 decision 7); the quote, when there is one, was verbatim in the block's recognised text when the finding was
    published.
    """

    ordinal: int
    page_number: int
    portal_block_id: str
    bbox: tuple[float, float, float, float]
    crop_sha256: str
    recognised_quote: str | None = None

    def __post_init__(self) -> None:
        x0, y0, x1, y1 = self.bbox
        if self.ordinal < 0 or self.page_number < 1:
            raise _invalid("block evidence has a non-negative ordinal and a page from 1")
        if not _PORTAL_BLOCK_ID.fullmatch(self.portal_block_id) or not _SHA256.fullmatch(self.crop_sha256):
            raise _invalid("block evidence names a portal block and the digest of its crop")
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise _invalid("a block's box lies in the normalised page and has an area")
        if self.recognised_quote is not None and not 1 <= len(self.recognised_quote) <= BLOCK_QUOTE_MAX_CHARS:
            raise _invalid(f"a block's quote is 1 to {BLOCK_QUOTE_MAX_CHARS} characters")


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
    #: `F8-PUBLISH`: the blocks of a candidate finding of a ``one_list`` run. Empty for a text finding, whose case is ``dm-capture/1``.
    block_evidence: tuple[BlockEvidenceFact, ...] = ()
    unverified_reason: str | None = None
    # Fresh semantic groups retain every raw claim and its actual source limitation.
    # (observation_id, finding_text, recommendation_text, grounding_kind, reason)
    source_observations: tuple[tuple[str, str, str, str, str | None], ...] = ()


#: The shape of a precedent mark as ``decision_memory_decision.precedent_label_at_decision`` holds it (``ck_decision_memory_decision_precedent_label``): a
#: code, so a new mark of the programme needs no change here. The memory does not import the precedent core to name them.
_PRECEDENT_LABEL = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
#: The only verdicts the document's history can have shown (``ck_decision_memory_decision_precedent_history_verdict_shown``).
_HISTORY_VERDICTS: Final[frozenset[str]] = frozenset({"accepted", "rejected"})


@dataclass(frozen=True, slots=True)
class DecisionFact:
    """One ledger event, as the memory keeps it.

    The last three members are **decision metadata, not case content** (`CRIT-CAPTURE-01`, plan-v5 2.1): what the server was showing for the finding when the
    expert decided -- the mark in force, the revision of the pass it comes from and the verdict of the document's history (hint P5) that was shown. They
    are written beside the decision and read by the vote's independence rule; :func:`content_digest` is over :class:`CaseContent` and never sees them, so a
    second decision on a known observation, taken under another mark, is no conflict. ``None`` means none was known: the label and the revision are both
    given or both absent, as the table holds them.
    """

    source_decision_id: str
    event_type: str
    severity: str | None
    comment: str | None
    author_user_uid: str | None
    origin_kind: str
    decided_at: datetime
    precedent_label_at_decision: str | None = None
    precedent_revision: int | None = None
    precedent_history_verdict_shown: str | None = None

    def __post_init__(self) -> None:
        if (self.precedent_label_at_decision is None) != (self.precedent_revision is None):
            raise _invalid("the mark at the decision and the revision it comes from are both given or both absent")
        if self.precedent_label_at_decision is not None and not _PRECEDENT_LABEL.match(self.precedent_label_at_decision):
            raise _invalid(f"{self.precedent_label_at_decision!r} is not a precedent mark")
        if self.precedent_revision is not None and (isinstance(self.precedent_revision, bool) or self.precedent_revision < 1):
            raise _invalid("a pass revision is a whole number from 1")
        if self.precedent_history_verdict_shown is not None and self.precedent_history_verdict_shown not in _HISTORY_VERDICTS:
            raise _invalid(f"{self.precedent_history_verdict_shown!r} is not a verdict the history can show")
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
class CommentFact:
    """One ``comment`` ledger event, as the memory keeps it: the expert's own words on a finding's observation.

    The words are never the system's: a ``comment`` event is written by an expert only (the carry-over writes ``accept`` and ``reject``
    events), so unlike a decision's comment there is no provenance sentence to leave out.
    """

    source_decision_id: str
    comment: str
    author_user_uid: str | None
    decided_at: datetime

    def __post_init__(self) -> None:
        try:
            DecisionId.parse(self.source_decision_id)
        except IdentityError:
            raise _invalid("a comment names the ledger event it comes from by its identity") from None
        if not self.comment.strip():
            raise _invalid("a comment carries words")
        if len(self.comment) > COMMENT_MAX_CHARS:
            raise _invalid(f"a comment is at most {COMMENT_MAX_CHARS} characters")


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
    #: The ``comment`` events of this observation recorded before the decision. The capture of a case carries them over (idempotently:
    #: a comment already kept is left alone), so an expert's note written before the first ✓/✕ is not lost to the memory. The memory
    #: reads no ledger: the assembler passes them in.
    earlier_comments: tuple[CommentFact, ...] = ()

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
    #: How many earlier comments this capture newly stored; ``0`` for a replay, for a forgotten case and when none were handed in.
    comments_carried: int = 0


@dataclass(frozen=True, slots=True)
class CommentCaptureResult:
    """What :meth:`MemoryRepository.capture_comment` did. ``case_id`` is ``None`` while the observation has no case."""

    case_id: str | None
    outcome: str

    def __post_init__(self) -> None:
        if self.outcome not in COMMENT_OUTCOMES:
            raise _invalid(f"{self.outcome!r} is not a comment capture outcome")

    @property
    def comment_created(self) -> bool:
        return self.outcome == COMMENT_CAPTURED


def capture_version_of(content: CaseContent) -> str:
    """``dm-capture/2`` for a case whose evidence is blocks, ``dm-capture/1`` for every other case."""
    if content.source_observations:
        return "dm-capture/4"
    if content.unverified_reason is not None:
        return "dm-capture/3"
    return CAPTURE_VERSION_BLOCK_EVIDENCE if content.block_evidence else CAPTURE_VERSION


def content_digest(content: CaseContent) -> str:
    """SHA-256 over the observation's immutable content, as sorted-key JSON without insignificant whitespace.

    It covers the finding, its provenance classifiers, the evidence (page, quote, offsets, block reference) and the normative references
    -- everything that comes from immutable rows -- and **not** the box geometry, the crops, the section or the data class, which are read
    from artifacts or settings that may differ between the first decision on an observation and a later one. So a later decision on the
    same observation always produces the digest of the first, and a different digest means the stored observation itself differs, which
    no ledger event can cause (a conflict, never an overwrite).

    `F8-PUBLISH`: the block evidence (ordinal, page, block, crop digest, quote; **not** the box, which is geometry) joins the body **only when there
    is some**, so the digest of every case without it is the one it always was.
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
    if content.block_evidence:
        body["block_evidence"] = [
            [b.ordinal, b.page_number, b.portal_block_id, b.crop_sha256, b.recognised_quote] for b in content.block_evidence
        ]
    if content.unverified_reason is not None:
        body["unverified_reason"] = content.unverified_reason
    if content.source_observations:
        body["source_observations"] = content.source_observations
    encoded = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
