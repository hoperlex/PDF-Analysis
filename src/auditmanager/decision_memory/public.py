"""Cross-context surface of the decision-memory boundary.

The composition root's capture assembler builds a :class:`CaptureSnapshot` from the other contexts and hands it to
:class:`MemoryRepository`; nothing else outside this package is meant to write the memory.
"""

from __future__ import annotations

from auditmanager.decision_memory.models import (
    CAPTURE_VERSION,
    CAPTURED_EVENT_TYPES,
    CROP_CAP,
    CROP_KIND_PORTAL_IMAGE_BLOCK,
    CROP_STATE_NONE_AVAILABLE,
    CROP_STATE_REFERENCED,
    DATA_CLASSES,
    ORIGIN_KINDS,
    SELECTION_RULE_PAGE_IMAGES,
    CaptureResult,
    CaptureSnapshot,
    CaseContent,
    CaseOrigin,
    CropRef,
    DecisionFact,
    EvidenceItem,
    NormRef,
    content_digest,
)
from auditmanager.decision_memory.repository import MemoryRepository
from auditmanager.decision_memory.selection import DESCRIPTION_MAX_CHARS, select_page_image_crops

__all__ = [
    "CAPTURE_VERSION",
    "CAPTURED_EVENT_TYPES",
    "CROP_CAP",
    "CROP_KIND_PORTAL_IMAGE_BLOCK",
    "CROP_STATE_NONE_AVAILABLE",
    "CROP_STATE_REFERENCED",
    "DATA_CLASSES",
    "DESCRIPTION_MAX_CHARS",
    "ORIGIN_KINDS",
    "SELECTION_RULE_PAGE_IMAGES",
    "CaptureResult",
    "CaptureSnapshot",
    "CaseContent",
    "CaseOrigin",
    "CropRef",
    "DecisionFact",
    "EvidenceItem",
    "MemoryRepository",
    "NormRef",
    "content_digest",
    "select_page_image_crops",
]
