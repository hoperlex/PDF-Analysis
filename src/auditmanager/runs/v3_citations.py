"""Unserved bridge from a Run's verified norm-set Blob to AR v3 citations.

This prepares material and publication candidates. It never dispatches a model,
claims provider provenance, writes a StageResult or publishes a finding.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    BlockIndex,
    LocalV3Evaluation,
    RecognisedContext,
    SuppliedV3Response,
    TextLayer,
    V3RequestCandidate,
    evaluate_v3_supplied_response,
    prepare_v3_request_candidate,
)
from auditmanager.findings.public import (
    CitationEvidence,
    V3PublicationCandidate,
    VerifiedRetrievalSetInput,
    load_verified_retrieval_set,
)
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs.repository import RunRow
from auditmanager.storage.public import BlobStore


class V3CorpusCitationRefused(ValueError):
    """The saved Run, verified set and intended v3 profile do not agree."""


@dataclass(frozen=True, slots=True)
class PinnedV3CorpusRequest:
    run_id: str
    profile_id: str
    bundle_id: str
    verified_set: VerifiedRetrievalSetInput
    recognised_context: tuple[RecognisedContext, ...]
    candidate: V3RequestCandidate


@dataclass(frozen=True, slots=True)
class V3CorpusCitationPlan:
    request: PinnedV3CorpusRequest
    evaluation: LocalV3Evaluation
    normative_candidates: tuple[V3PublicationCandidate, ...]


def _require_binding(
    run: RunRow, verified: VerifiedRetrievalSetInput, text_layer: TextLayer, *,
    profile_id: str, bundle_id: str, map_sha256: str,
) -> None:
    if (
        not isinstance(run, RunRow)
        or not isinstance(verified, VerifiedRetrievalSetInput)
        or not isinstance(text_layer, TextLayer)
        or run.state not in {"running", "validating"}
        or run.run_id != verified.run_id
        or run.version_uid != text_layer.version_uid
        or run.norms_snapshot_id != verified.norms_snapshot_id
        or run.norm_retrieval_set_id != verified.norm_retrieval_set_id
        or run.analysis_profile_id != profile_id
        or run.prompt_bundle_id != bundle_id
        or not isinstance(map_sha256, str)
        or len(map_sha256) != 64
        or verified.map_sha256 != map_sha256
    ):
        raise V3CorpusCitationRefused("run_set_profile_binding_invalid")


def prepare_v3_corpus_request(
    session: Session, *, run: RunRow, authority: AttemptAuthority,
    blob_store: BlobStore, text_layer: TextLayer, profile_id: str,
    bundle_id: str, map_sha256: str,
    recognised_context: tuple[RecognisedContext, ...] = (),
) -> PinnedV3CorpusRequest:
    """Read confirmed DB/Blob custody and send only its selected norm rows.

    ``profile_id``, ``bundle_id`` and ``map_sha256`` must come from a trusted
    registered v3 profile. The later provider boundary must recheck current
    Attempt and budget before any external effect.
    """
    if (not isinstance(run, RunRow)
            or not isinstance(authority, AttemptAuthority)
            or authority.run_id != run.run_id):
        raise V3CorpusCitationRefused("attempt_run_mismatch")
    verified = load_verified_retrieval_set(
        session, authority=authority, blob_store=blob_store,
    )
    _require_binding(
        run, verified, text_layer, profile_id=profile_id,
        bundle_id=bundle_id, map_sha256=map_sha256,
    )
    candidate = prepare_v3_request_candidate(
        text_layer, verified.data, expected_version_uid=run.version_uid,
        expected_set_sha256=verified.set_sha256,
        expected_snapshot_id=verified.norms_snapshot_id,
        expected_map_sha256=verified.map_sha256,
        recognised_context=recognised_context,
    )
    return PinnedV3CorpusRequest(
        run_id=run.run_id, profile_id=profile_id, bundle_id=bundle_id,
        verified_set=verified, recognised_context=recognised_context,
        candidate=candidate,
    )


def plan_v3_corpus_citations(
    request: PinnedV3CorpusRequest, response: SuppliedV3Response,
    text_layer: TextLayer, *, block_index: BlockIndex | None = None,
) -> V3CorpusCitationPlan:
    """Ground a supplied answer against the request's exact saved set bytes.

    The result remains untrusted for publication until the caller checks the
    saved model call/effect, current Attempt and CITE stage in one transaction.
    """
    if not isinstance(request, PinnedV3CorpusRequest):
        raise V3CorpusCitationRefused("pinned_request_required")
    if (request.run_id != request.verified_set.run_id
            or request.candidate.norms_snapshot_id != request.verified_set.norms_snapshot_id
            or request.candidate.map_sha256 != request.verified_set.map_sha256
            or request.candidate.set_sha256 != request.verified_set.set_sha256):
        raise V3CorpusCitationRefused("pinned_request_set_mismatch")
    evaluation = evaluate_v3_supplied_response(
        request.candidate, response, text_layer, request.verified_set.data,
        recognised_context=request.recognised_context,
        block_index=block_index,
    )
    candidates: list[V3PublicationCandidate] = []
    for accepted in evaluation.grounding.accepted:
        if not accepted.norm_citations:
            continue
        proposal = accepted.proposal
        if proposal.required_value is None or proposal.stated_value is None:
            raise V3CorpusCitationRefused("normative_value_missing")
        candidates.append(V3PublicationCandidate(
            category=proposal.category,
            finding_text=proposal.finding_text,
            recommendation_text=proposal.recommendation_text,
            proposed_severity=proposal.proposed_severity,
            evidence=tuple(CitationEvidence(
                anchor.page_number, anchor.quote, anchor.char_start,
                anchor.char_end, anchor.block_id,
            ) for anchor in accepted.evidence),
            norm_citations=accepted.norm_citations,
            required_value=proposal.required_value,
            stated_value=proposal.stated_value,
        ))
    return V3CorpusCitationPlan(request, evaluation, tuple(candidates))


__all__ = [
    "PinnedV3CorpusRequest", "V3CorpusCitationPlan", "V3CorpusCitationRefused",
    "prepare_v3_corpus_request", "plan_v3_corpus_citations",
]
