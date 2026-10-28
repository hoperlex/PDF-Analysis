"""Canonical, review-only AR v3 citation bytes before any publication effect."""

from __future__ import annotations

import json
from dataclasses import dataclass

from auditmanager.analysis.public import canonical_bytes, sha256_hex
from auditmanager.runs.v3_citations import (
    V3CorpusCitationRefused, grounded_citations_are_provisional, index_prompt_rows,
)
from auditmanager.runs.v3_cite_preflight import V3CitePreflight
from auditmanager.shared.errors import DomainError, ErrorCode


ROLE = "analysis.v3_beta_review"
FORMAT = "ar-v3-beta-citation-review/1"
MAX_REVIEW_BYTES = 2_097_152


@dataclass(frozen=True, slots=True)
class BuiltV3ReviewArtifact:
    role: str
    payload: bytes
    sha256: str
    size_bytes: int
    media_type: str = "application/json"


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="AR v3 beta review cannot be sealed from mismatched evidence",
        stage_id="text_analysis", reason=reason,
    )


def build_v3_beta_review_artifact(value: V3CitePreflight) -> BuiltV3ReviewArtifact:
    """Preserve grounded quotes and all C-topic states, without numeric verdicts.

    The result has no blob ID or StageResult authority. A later CITE writer must
    publish it through the outbox and recheck the same call and Attempt.
    """
    if not isinstance(value, V3CitePreflight):
        raise _refuse("preflight_required")
    prepared, call, reply, review = (
        value.prepared, value.completed_call, value.recovered_reply, value.review,
    )
    request = prepared.pinned_corpus
    candidate = request.candidate
    grounding = review.evaluation.grounding
    try:
        answer_sha = sha256_hex(reply.model_response.output_text.encode("utf-8"))
    except UnicodeError as exc:
        raise _refuse("answer_text_invalid") from exc
    if (review.request != request
            or review.evaluation.request_sha256 != call.candidate_sha256
            or review.evaluation.response_sha256 != answer_sha
            or prepared.candidate_sha256 != call.candidate_sha256
            or prepared.provider_body_sha256 != call.request_sha256
            or reply.model_response.response_sha256 != call.response_sha256
            or prepared.binding.run_id != call.run_id
            or prepared.binding.scope_id != call.scope_id
            or prepared.binding.set_sha256 != call.set_sha256
            or prepared.binding.policy_sha256 != review.source_policy_sha256
            or request.verified_set.norms_snapshot_id != prepared.binding.norms_snapshot_id
            or request.verified_set.map_sha256 != prepared.binding.map_sha256
            or request.verified_set.set_sha256 != call.set_sha256
            or candidate.scope_id != call.scope_id
            or tuple(topic.item_id for topic in review.topics) != candidate.item_ids
            or len(set(candidate.item_ids)) != len(candidate.item_ids)
            or grounding.salvaged or grounding.malformed_count != 0):
        raise _refuse("review_binding_or_completeness_invalid")

    try:
        set_document = json.loads(request.verified_set.data)
        rows = index_prompt_rows(json.loads(set_document["prompt_part"])["paragraphs"])
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise _refuse("review_label_map_invalid") from exc
    label_items = rows.label_items
    if (set(label_items.values()) != set(candidate.item_ids)
            or len(set(label_items.values())) != len(candidate.item_ids)):
        raise _refuse("review_label_map_invalid")
    topic_modes = {topic.item_id: topic.mode for topic in review.topics}
    if len(topic_modes) != len(review.topics):
        raise _refuse("review_topics_duplicate")

    provisional = set(review.provisional_proposal_ordinals)
    withheld = set(review.withheld_proposal_ordinals)
    if (len(provisional) != len(review.provisional_proposal_ordinals)
            or len(withheld) != len(review.withheld_proposal_ordinals)
            or provisional & withheld):
        raise _refuse("review_classification_invalid")
    accepted_ordinals = set()
    provisional_entries = []
    withheld_entries = []
    citation_counts = {item_id: 0 for item_id in candidate.item_ids}
    for accepted in grounding.accepted:
        ordinal = accepted.proposal_ordinal
        if ordinal in accepted_ordinals:
            raise _refuse("review_accepted_duplicate")
        accepted_ordinals.add(ordinal)
        if not accepted.norm_citations:
            if ordinal in provisional or ordinal in withheld:
                raise _refuse("review_nonnormative_classified")
            continue
        if (ordinal in provisional) == (ordinal in withheld):
            raise _refuse("review_normative_unclassified")
        items = []
        for citation in accepted.norm_citations:
            item_id = label_items.get(citation.label)
            if item_id is None:
                raise _refuse("review_citation_label_invalid")
            items.append(item_id)
        if ordinal in provisional:
            # the same rule the classifier applied: by the paragraph each citation was grounded
            # to, not by its label (a rebound quote can land on a context-only paragraph)
            try:
                provisional_ok = grounded_citations_are_provisional(
                    tuple(item.label for item in accepted.proposal.norm_citations or ()),
                    accepted.norm_citations, rows=rows, modes=topic_modes,
                )
            except V3CorpusCitationRefused as exc:
                raise _refuse("review_citation_grounding_invalid") from exc
            if not provisional_ok:
                raise _refuse("review_context_laundered")
            for item_id in items:
                citation_counts[item_id] += 1
            provisional_entries.append({
                "proposal_ordinal": ordinal,
                "evidence": [{
                    "page_number": anchor.page_number,
                    "quote": anchor.quote,
                    "char_start": anchor.char_start,
                    "char_end": anchor.char_end,
                    "block_id": anchor.block_id,
                } for anchor in accepted.evidence],
                "citations": [{
                    "item_id": label_items[citation.label],
                    "label": citation.label,
                    "document_id": citation.document_id,
                    "paragraph_id": citation.paragraph_id,
                    "raw_offset": citation.raw_offset,
                    "raw_quote": citation.raw_quote,
                    "state": citation.state,
                } for citation in accepted.norm_citations],
            })
        else:
            withheld_entries.append({
                "proposal_ordinal": ordinal,
                "reason": "context_only_or_mixed_source",
            })
    if not (provisional | withheld) <= accepted_ordinals:
        raise _refuse("review_classification_missing_accepted")
    rejected = grounding.rejected
    if (len({item.proposal_ordinal for item in rejected}) != len(rejected)
            or any(item.proposal_ordinal in accepted_ordinals for item in rejected)):
        raise _refuse("review_rejected_overlap")

    binding = prepared.binding
    document = {
        "format": FORMAT,
        "artifact_role": ROLE,
        "artifact_version": "1.0.0",
        "run_id": call.run_id,
        "group_id": binding.group_id,
        "scope_id": call.scope_id,
        "version_uid": binding.version_uid,
        "norms_snapshot_id": binding.norms_snapshot_id,
        "norm_retrieval_set_id": binding.norm_retrieval_set_id,
        "analysis_profile_id": binding.analysis_profile_id,
        "prompt_bundle_id": binding.prompt_bundle_id,
        "source_policy_sha256": review.source_policy_sha256,
        "scenario": review.scenario,
        "numeric_output_policy": review.numeric_output_policy,
        "map_sha256": binding.map_sha256,
        "set_sha256": call.set_sha256,
        "candidate_sha256": call.candidate_sha256,
        "provider_body_sha256": call.request_sha256,
        "provider_response_sha256": call.response_sha256,
        "answer_text_sha256": answer_sha,
        "model_call_id": call.model_call_id,
        "reply_ref": {
            "blob_id": call.reply_blob_id,
            "sha256": call.reply_blob_sha256,
            "size_bytes": call.reply_blob_size,
        },
        "topics": [{
            "item_id": topic.item_id,
            "mode": topic.mode,
            "reason": topic.reason,
            "source_ids": list(topic.source_ids),
            "review_status": "requires_expert_review",
            "provisional_citation_count": citation_counts[topic.item_id],
        } for topic in review.topics],
        "provisional_citations": sorted(
            provisional_entries, key=lambda item: item["proposal_ordinal"],
        ),
        "withheld_proposals": sorted(
            withheld_entries, key=lambda item: item["proposal_ordinal"],
        ),
        "rejected_proposals": [{
            "proposal_ordinal": item.proposal_ordinal,
            "reason": item.reason,
        } for item in sorted(rejected, key=lambda item: item.proposal_ordinal)],
    }
    payload = canonical_bytes(document)
    if len(payload) > MAX_REVIEW_BYTES:
        raise _refuse("review_artifact_too_large")
    return BuiltV3ReviewArtifact(
        ROLE, payload, sha256_hex(payload), len(payload),
    )


__all__ = ["BuiltV3ReviewArtifact", "build_v3_beta_review_artifact"]
