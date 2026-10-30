"""Pure Stage AI request/validation boundary; no calls, persistence or raw mutation."""

from .classifier import build_classification_request, parse_classification
from .model import (
    CATEGORIES, CLASSES, CONFIDENCES, HIGH_LEVEL_TYPES, STATUSES, SYSTEMS,
    AtomicEvidence, ClassifiedCard, ClassificationResult, EvidenceGroup, Fragment,
    HighLevelChange, ReviewDecision, ReviewGroup, ReviewItem, ReviewResult, SynthesisGroup,
)
from .requests import CallPlan
from .reviewer import accept_review_group, build_review_requests, parse_review_chunk
from .synthesis import build_synthesis_request, parse_synthesis
from .validation import StageAiValidationError

__all__ = [
    "CATEGORIES", "CLASSES", "CONFIDENCES", "HIGH_LEVEL_TYPES", "STATUSES", "SYSTEMS",
    "AtomicEvidence", "CallPlan", "ClassifiedCard", "ClassificationResult", "EvidenceGroup",
    "Fragment", "HighLevelChange", "ReviewDecision", "ReviewGroup", "ReviewItem", "ReviewResult",
    "StageAiValidationError", "SynthesisGroup", "accept_review_group",
    "build_classification_request", "build_review_requests", "build_synthesis_request",
    "parse_classification", "parse_review_chunk", "parse_synthesis",
]
