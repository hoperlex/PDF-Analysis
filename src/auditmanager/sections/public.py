"""Cross-context surface of the sections boundary (`W59-SECTION-SEAL-01`).

Run start (``runs``) routes through :func:`route_classified_version`; the composition root
serves :func:`classify_document_version` and the section review; the pure rules of the
append-only correction (`CLASSIFICATION-CORRECTION-01`) are :func:`plan_classification_correction`
and its value types. Everything else in this
package is reached through here or not at all.
"""

from __future__ import annotations

from auditmanager.sections.classification import (
    CONFLICT_VERSION_ALREADY_CLASSIFIED,
    REFERENCE_KIND_ANALYSIS_PROFILE,
    REFERENCE_KIND_VERSION_CLASSIFICATION,
    SECTION_CODES,
    ClassifiedRoute,
    RecognisedTextReader,
    ReviewFacts,
    build_section_review,
    classify_document_version,
    read_section_review,
    route_classified_version,
    section_names,
)
from auditmanager.sections.correction import (
    CONFLICT_REVISION_STALE,
    CONFLICT_VERSION_NOT_CLASSIFIED,
    MAX_REASON_LENGTH,
    ORIGINAL_REVISION,
    ClassificationRevision,
    CorrectionPlan,
    CorrectionRequest,
    plan_classification_correction,
)
from auditmanager.sections.review import (
    SectionReviewOption,
    SectionReviewPacket,
    SectionReviewUnavailable,
)
from auditmanager.sections.routing import SectionRouteUnavailable
from auditmanager.sections.suggestion import SectionSuggestion

__all__ = [
    "CONFLICT_REVISION_STALE",
    "CONFLICT_VERSION_ALREADY_CLASSIFIED",
    "CONFLICT_VERSION_NOT_CLASSIFIED",
    "MAX_REASON_LENGTH",
    "ORIGINAL_REVISION",
    "REFERENCE_KIND_ANALYSIS_PROFILE",
    "REFERENCE_KIND_VERSION_CLASSIFICATION",
    "SECTION_CODES",
    "ClassificationRevision",
    "ClassifiedRoute",
    "CorrectionPlan",
    "CorrectionRequest",
    "RecognisedTextReader",
    "ReviewFacts",
    "SectionReviewOption",
    "SectionReviewPacket",
    "SectionReviewUnavailable",
    "SectionRouteUnavailable",
    "SectionSuggestion",
    "build_section_review",
    "classify_document_version",
    "plan_classification_correction",
    "read_section_review",
    "route_classified_version",
    "section_names",
]
