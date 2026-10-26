"""Pure AR v3 replay of a supplied response against exact draft request inputs.

This evaluator does not obtain a provider response, prove Run/Blob custody,
write a stage result or turn a grounded proposal into an expert decision.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from auditmanager.analysis.profiles.ar_shared.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.citation_grounding import (
    V3GroundingResult,
    ground_v3_proposals,
)
from auditmanager.analysis.profiles.ar_v3.request_candidate import (
    V3RequestCandidate,
    V3RequestRefused,
    prepare_v3_request_candidate,
)
from auditmanager.analysis.profiles.ar_v3.response import parse_response
from auditmanager.analysis.profiles.ar_v3.set_input import (
    V3SetInputRefused,
    parse_v3_set_input,
)
from auditmanager.analysis.text.anchors import BlockIndex
from auditmanager.analysis.text.textlayer import TextLayer


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class V3LocalEvaluationRefused(ValueError):
    """The supplied response cannot be paired with these draft request inputs."""


@dataclass(frozen=True, slots=True)
class SuppliedV3Response:
    """Untrusted raw response text and its claimed draft request digest."""

    request_sha256: str
    output_text: str
    truncated: bool


@dataclass(frozen=True, slots=True)
class LocalV3Evaluation:
    """Reproducible local diagnostics, never a canonical finding or verdict."""

    request_sha256: str
    response_sha256: str
    grounding: V3GroundingResult


def evaluate_v3_supplied_response(
    candidate: V3RequestCandidate,
    response: SuppliedV3Response,
    text_layer: TextLayer,
    set_bytes: bytes,
    *,
    recognised_context: tuple[RecognisedContext, ...] = (),
    block_index: BlockIndex | None = None,
) -> LocalV3Evaluation:
    """Replay parsing and PDF-first/norm-second grounding without I/O.

    Rebuild and compare the entire candidate, not merely a caller-supplied
    digest. A matching claim in ``SuppliedV3Response`` still does not prove
    provider provenance; a later authorized adapter must establish that.
    """
    if not isinstance(candidate, V3RequestCandidate):
        raise V3LocalEvaluationRefused("request_candidate_required")
    if (not isinstance(response, SuppliedV3Response)
            or not isinstance(response.request_sha256, str)
            or _SHA256.fullmatch(response.request_sha256) is None
            or response.request_sha256 != candidate.request_sha256):
        raise V3LocalEvaluationRefused("response_request_digest_mismatch")
    try:
        rebuilt = prepare_v3_request_candidate(
            text_layer, set_bytes,
            expected_version_uid=candidate.version_uid,
            expected_set_sha256=candidate.set_sha256,
            expected_snapshot_id=candidate.norms_snapshot_id,
            expected_map_sha256=candidate.map_sha256,
            recognised_context=recognised_context,
                scope_id=candidate.scope_id,
                expected_composition_sha256=candidate.composition_sha256,
        )
    except V3RequestRefused as exc:
        raise V3LocalEvaluationRefused("request_inputs_invalid") from exc
    if rebuilt != candidate:
        raise V3LocalEvaluationRefused("request_candidate_mismatch")
    try:
        source = parse_v3_set_input(
            set_bytes, expected_sha256=candidate.set_sha256,
            expected_snapshot_id=candidate.norms_snapshot_id,
            expected_map_sha256=candidate.map_sha256,
        )
    except V3SetInputRefused as exc:
        raise V3LocalEvaluationRefused("request_set_invalid") from exc
    try:
        response_bytes = response.output_text.encode("utf-8")
    except (AttributeError, UnicodeError) as exc:
        raise V3LocalEvaluationRefused("response_text_not_utf8") from exc
    parsed = parse_response(response.output_text, truncated=response.truncated)
    grounding = ground_v3_proposals(
        parsed, text_layer,
        paragraphs=source.paragraphs,
        label_bindings=source.label_bindings,
        recognised_context=recognised_context,
        block_index=block_index,
    )
    return LocalV3Evaluation(
        request_sha256=candidate.request_sha256,
        response_sha256=hashlib.sha256(response_bytes).hexdigest(),
        grounding=grounding,
    )


__all__ = [
    "LocalV3Evaluation", "SuppliedV3Response", "V3LocalEvaluationRefused",
    "evaluate_v3_supplied_response",
]
