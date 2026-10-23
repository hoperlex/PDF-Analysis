"""Unserved bridge from a Run's verified norm-set Blob to AR v3 citations.

This prepares material and publication candidates. It never dispatches a model,
claims provider provenance, writes a StageResult or publishes a finding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    BetaSourcePolicyRefused,
    BlockIndex,
    LocalV3Evaluation,
    RecognisedContext,
    SuppliedV3Response,
    TextLayer,
    V3RequestCandidate,
    evaluate_v3_supplied_response,
    load_beta_source_policy,
    parse_v3_set_input,
    prepare_v3_scoped_request_candidate,
    V3SetInputRefused,
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
    scope_id: str
    composition_sha256: str
    verified_set: VerifiedRetrievalSetInput
    recognised_context: tuple[RecognisedContext, ...]
    candidate: V3RequestCandidate


@dataclass(frozen=True, slots=True)
class V3CorpusCitationPlan:
    request: PinnedV3CorpusRequest
    evaluation: LocalV3Evaluation
    normative_candidates: tuple[V3PublicationCandidate, ...]


@dataclass(frozen=True, slots=True)
class V3BetaTopicReview:
    item_id: str
    mode: str
    reason: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class V3BetaCitationReview:
    """Diagnostic-only beta review; it carries no publication candidates."""

    request: PinnedV3CorpusRequest
    evaluation: LocalV3Evaluation
    source_policy_sha256: str
    scenario: str
    numeric_output_policy: str
    topics: tuple[V3BetaTopicReview, ...]
    provisional_proposal_ordinals: tuple[int, ...]
    withheld_proposal_ordinals: tuple[int, ...]


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
    bundle_id: str, map_sha256: str, scope_id: str,
    composition_sha256: str,
    recognised_context: tuple[RecognisedContext, ...] = (),
    lock_authority: bool = True,
) -> PinnedV3CorpusRequest:
    """Read confirmed DB/Blob custody and send only its selected norm rows.

    Profile, bundle, map, scope and composition must come from a trusted
    reviewed pack. The later provider boundary must recheck current Attempt
    and budget before any external effect.
    """
    if (not isinstance(run, RunRow)
            or not isinstance(authority, AttemptAuthority)
            or authority.run_id != run.run_id):
        raise V3CorpusCitationRefused("attempt_run_mismatch")
    verified = load_verified_retrieval_set(
        session, authority=authority, blob_store=blob_store,
        lock_authority=lock_authority,
    )
    _require_binding(
        run, verified, text_layer, profile_id=profile_id,
        bundle_id=bundle_id, map_sha256=map_sha256,
    )
    candidate = prepare_v3_scoped_request_candidate(
        text_layer, verified.data, expected_version_uid=run.version_uid,
        expected_set_sha256=verified.set_sha256,
        expected_snapshot_id=verified.norms_snapshot_id,
        expected_map_sha256=verified.map_sha256,
        scope_id=scope_id,
        expected_composition_sha256=composition_sha256,
        recognised_context=recognised_context,
    )
    return PinnedV3CorpusRequest(
        run_id=run.run_id, profile_id=profile_id, bundle_id=bundle_id,
        scope_id=scope_id, composition_sha256=composition_sha256,
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
            or request.candidate.scope_id != request.scope_id
            or request.candidate.composition_sha256 != request.composition_sha256
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


def plan_v3_beta_citation_review(
    request: PinnedV3CorpusRequest, response: SuppliedV3Response,
    text_layer: TextLayer, *, block_index: BlockIndex | None = None,
) -> V3BetaCitationReview:
    """Classify a grounded v3 response against the frozen F1.3 beta policy.

    A provisional citation is still an expert-review suggestion. Context-only
    topics and observations mixing them with provisional labels are withheld.
    The returned object deliberately has no publication-candidate field.
    """
    if not isinstance(request, PinnedV3CorpusRequest):
        raise V3CorpusCitationRefused("pinned_request_required")
    try:
        policy = load_beta_source_policy()
        if (request.verified_set.norms_snapshot_id != policy.snapshot_id
                or request.composition_sha256 != policy.composition_sha256
                or request.candidate.item_ids != tuple(
                    item.item_id for item in policy.group(request.scope_id)
                )):
            raise V3CorpusCitationRefused("beta_policy_scope_mismatch")
        selected = parse_v3_set_input(
            request.verified_set.data,
            expected_sha256=request.verified_set.set_sha256,
            expected_snapshot_id=policy.snapshot_id,
            expected_map_sha256=request.verified_set.map_sha256,
        )
        if selected.selected_item_ids != request.candidate.item_ids:
            raise V3CorpusCitationRefused("beta_set_items_mismatch")
        rows = json.loads(selected.prompt_part)["paragraphs"]
        label_items = {row["label"]: row["item_id"] for row in rows}
        if len(label_items) != len(rows):
            raise V3CorpusCitationRefused("beta_set_labels_invalid")
    except (BetaSourcePolicyRefused, V3SetInputRefused,
            json.JSONDecodeError, KeyError, TypeError) as exc:
        raise V3CorpusCitationRefused("beta_policy_or_set_invalid") from exc
    plan = plan_v3_corpus_citations(
        request, response, text_layer, block_index=block_index,
    )
    by_item = {item.item_id: item for item in policy.group(request.scope_id)}
    provisional: list[int] = []
    withheld: list[int] = []
    for accepted in plan.evaluation.grounding.accepted:
        if not accepted.norm_citations:
            continue
        citations = accepted.proposal.norm_citations
        if citations is None:
            raise V3CorpusCitationRefused("beta_normative_citations_missing")
        try:
            modes = tuple(by_item[label_items[citation.label]].mode
                          for citation in citations)
        except KeyError as exc:
            raise V3CorpusCitationRefused("beta_citation_label_invalid") from exc
        if all(mode == "provisional_citation" for mode in modes):
            provisional.append(accepted.proposal_ordinal)
        else:
            withheld.append(accepted.proposal_ordinal)
    return V3BetaCitationReview(
        request, plan.evaluation, policy.sha256, policy.scenario,
        policy.numeric_output_policy,
        tuple(V3BetaTopicReview(item.item_id, item.mode, item.reason, item.source_ids)
              for item in policy.group(request.scope_id)),
        tuple(provisional), tuple(withheld),
    )


__all__ = [
    "PinnedV3CorpusRequest", "V3BetaCitationReview", "V3BetaTopicReview",
    "V3CorpusCitationPlan", "V3CorpusCitationRefused",
    "prepare_v3_corpus_request", "plan_v3_corpus_citations",
    "plan_v3_beta_citation_review",
]
