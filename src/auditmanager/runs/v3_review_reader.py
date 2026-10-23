"""Verify a saved AR v3 beta review before a future read-only API exposes it."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID, canonical_bytes, sha256_hex,
)
from auditmanager.findings.public import publication_rows_exist
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_group import GroupView, get_ar_v3_group
from auditmanager.runs.v3_provider_call import MAX_REPLY_BYTES
from auditmanager.runs.v3_review_artifact import FORMAT, MAX_REVIEW_BYTES, ROLE
from auditmanager.runs.v3_review_terminal import _checked_review
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ArV3RunGroupId
from auditmanager.storage.public import (
    BlobMetadataRepository, BlobStore, derive_blob_id, parse_blob_id,
)


_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ITEM = re.compile(r"C(?:0[1-9]|1[0-9]|2[0-2])\Z")
_FIELDS = frozenset({
    "format", "artifact_role", "artifact_version", "run_id", "group_id",
    "scope_id", "version_uid", "norms_snapshot_id", "norm_retrieval_set_id",
    "analysis_profile_id", "prompt_bundle_id", "source_policy_sha256",
    "scenario", "numeric_output_policy", "map_sha256", "set_sha256",
    "candidate_sha256", "provider_body_sha256", "provider_response_sha256",
    "answer_text_sha256", "model_call_id", "reply_ref", "topics",
    "provisional_citations", "withheld_proposals", "rejected_proposals",
})
_TOPIC_FIELDS = frozenset({
    "item_id", "mode", "reason", "source_ids", "review_status",
    "provisional_citation_count",
})
_STAGES = frozenset({
    "source_preparation", "page_geometry_extraction",
    "document_context_build", "ar_v3_citation_review",
})


@dataclass(frozen=True, slots=True)
class V3SavedReview:
    run_id: str
    group_id: str
    scope_id: str
    document: Mapping[str, Any]


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the saved AR v3 review is unavailable or inconsistent",
        stage_id="ar_v3_citation_review", reason=reason,
    )


def _document(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
        if (not isinstance(value, dict) or frozenset(value) != _FIELDS
                or canonical_bytes(value) != payload):
            raise ValueError("noncanonical review document")
    except (UnicodeError, ValueError, TypeError, OverflowError) as exc:
        raise _refuse("review_json_invalid") from exc
    return value


def _verify_topics(value: Mapping[str, Any], metrics: Mapping[str, Any]) -> None:
    topics = value["topics"]
    provisional = value["provisional_citations"]
    withheld = value["withheld_proposals"]
    rejected = value["rejected_proposals"]
    if (not isinstance(topics, list) or not topics
            or any(not isinstance(rows, list) for rows in (
                provisional, withheld, rejected,
            ))
            or len(provisional) != metrics["provisional_citation_count"]
            or len(withheld) != metrics["withheld_proposal_count"]
            or len(rejected) != metrics["rejected_proposal_count"]):
        raise _refuse("review_topic_counts_invalid")
    by_item: dict[str, Mapping[str, Any]] = {}
    for topic in topics:
        if (not isinstance(topic, dict) or frozenset(topic) != _TOPIC_FIELDS
                or not isinstance(topic["item_id"], str)
                or _ITEM.fullmatch(topic["item_id"]) is None
                or topic["item_id"] in by_item
                or not isinstance(topic["mode"], str)
                or topic["mode"] not in {"provisional_citation", "context_only"}
                or topic["review_status"] != "requires_expert_review"
                or not isinstance(topic["reason"], str)
                or not isinstance(topic["source_ids"], list)
                or any(not isinstance(source, str) or not source
                       for source in topic["source_ids"])
                or type(topic["provisional_citation_count"]) is not int
                or topic["provisional_citation_count"] < 0):
            raise _refuse("review_topic_invalid")
        by_item[topic["item_id"]] = topic
    counted = {item_id: 0 for item_id in by_item}
    ordinals: set[int] = set()
    for proposal in provisional:
        if (not isinstance(proposal, dict)
                or frozenset(proposal) != {"proposal_ordinal", "evidence", "citations"}
                or type(proposal["proposal_ordinal"]) is not int
                or proposal["proposal_ordinal"] < 0
                or not isinstance(proposal["evidence"], list)
                or not isinstance(proposal["citations"], list)
                or not proposal["citations"]):
            raise _refuse("review_citation_invalid")
        if proposal["proposal_ordinal"] in ordinals:
            raise _refuse("review_proposal_duplicate")
        ordinals.add(proposal["proposal_ordinal"])
        for citation in proposal["citations"]:
            if (not isinstance(citation, dict)
                    or not isinstance(citation.get("item_id"), str)
                    or citation.get("item_id") not in by_item
                    or by_item[citation["item_id"]]["mode"] != "provisional_citation"):
                raise _refuse("review_context_citation_invalid")
            counted[citation["item_id"]] += 1
    for collection in (withheld, rejected):
        for proposal in collection:
            if (not isinstance(proposal, dict)
                    or type(proposal.get("proposal_ordinal")) is not int
                    or proposal["proposal_ordinal"] < 0
                    or proposal["proposal_ordinal"] in ordinals):
                raise _refuse("review_proposal_duplicate_or_invalid")
            ordinals.add(proposal["proposal_ordinal"])
    if any(counted[item_id] != topic["provisional_citation_count"]
           for item_id, topic in by_item.items()):
        raise _refuse("review_citation_count_invalid")


def _verify_binding(
    value: Mapping[str, Any], *, run: object, metrics: Mapping[str, Any],
    group: GroupView,
) -> None:
    members = tuple(member for member in group.members
                    if member.run_id == value["run_id"])
    if len(members) != 1:
        raise _refuse("review_group_member_missing")
    member = members[0]
    expected = {
        "format": FORMAT, "artifact_role": ROLE, "artifact_version": "1.0.0",
        "run_id": run.run_id, "group_id": group.group_id,
        "scope_id": member.scope_id, "version_uid": run.version_uid,
        "norms_snapshot_id": run.norms_snapshot_id,
        "norm_retrieval_set_id": member.norm_retrieval_set_id,
        "analysis_profile_id": str(AR_V3_BETA_PROFILE_ID),
        "prompt_bundle_id": str(AR_V3_BETA_BUNDLE_ID),
        "scenario": "new_multi_apartment_residential_F1.3",
        "numeric_output_policy": "expert_review_required",
        "map_sha256": member.map_sha256,
        "set_sha256": metrics["set_sha256"],
        "candidate_sha256": metrics["candidate_sha256"],
        "provider_body_sha256": metrics["provider_body_sha256"],
        "provider_response_sha256": metrics["provider_response_sha256"],
        "model_call_id": metrics["model_call_id"],
    }
    if (any(value.get(key) != wanted for key, wanted in expected.items())
            or group.version_uid != run.version_uid
            or group.norms_snapshot_id != run.norms_snapshot_id
            or group.analysis_profile_id != run.analysis_profile_id
            or group.prompt_bundle_id != run.prompt_bundle_id
            or group.provider_mode != run.provider_mode
            or member.state != run.state
            or member.norm_retrieval_set_id != run.norm_retrieval_set_id):
        raise _refuse("review_run_group_binding_invalid")
    reply = value["reply_ref"]
    if (not isinstance(reply, dict)
            or set(reply) != {"blob_id", "sha256", "size_bytes"}
            or reply["sha256"] != metrics["reply_blob_sha256"]
            or not isinstance(reply["blob_id"], str)
            or type(reply["size_bytes"]) is not int
            or reply["size_bytes"] <= 0
            or reply["size_bytes"] > MAX_REPLY_BYTES
            or reply["blob_id"] != str(derive_blob_id(
                sha256=reply["sha256"], size=reply["size_bytes"],
            ))
            or any(not isinstance(value[key], str) or _SHA.fullmatch(value[key]) is None
                   for key in ("source_policy_sha256", "answer_text_sha256"))):
        raise _refuse("review_reply_or_policy_invalid")
    _verify_topics(value, metrics)


def read_v3_saved_review(
    session: Session, run_id: str, *, blob_store: BlobStore,
    runs: RunRepository | None = None,
    blobs: BlobMetadataRepository | None = None,
) -> V3SavedReview:
    """Read the bounded review Blob, then recheck its immutable DB witnesses."""
    run_repo = runs or RunRepository()
    blob_repo = blobs or BlobMetadataRepository()
    run = run_repo.get(session, run_id)
    if (run.analysis_profile_id != str(AR_V3_BETA_PROFILE_ID)
            or run.prompt_bundle_id != str(AR_V3_BETA_BUNDLE_ID)):
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    if run.state not in {"published", "partial"}:
        raise _refuse("review_run_not_publishable")
    stages = run_repo.stage_results(session, run_id)
    if (len(stages) != len(_STAGES)
            or {row.stage_id for row in stages} != _STAGES):
        raise _refuse("review_stages_invalid")
    citations = tuple(row for row in stages
                      if row.stage_id == "ar_v3_citation_review")
    if (len(citations) != 1 or citations[0].error is not None
            or publication_rows_exist(session, run_id)):
        raise _refuse("review_stage_or_findings_invalid")
    stage = _checked_review(citations[0])
    reference = stage.artifacts[0]
    if reference.size_bytes < 1 or reference.size_bytes > MAX_REVIEW_BYTES:
        raise _refuse("review_blob_size_invalid")
    try:
        blob_id = parse_blob_id(reference.blob_id)
    except (TypeError, ValueError) as exc:
        raise _refuse("review_blob_reference_invalid") from exc
    metadata = blob_repo.get(session, blob_id)
    if (metadata is None or not metadata.is_available
            or metadata.sha256 != reference.sha256
            or metadata.size_bytes != reference.size_bytes
            or metadata.media_type != reference.media_type):
        raise _refuse("review_blob_metadata_invalid")
    payload = blob_store.read(blob_id, verify=True)
    if (len(payload) != reference.size_bytes
            or sha256_hex(payload) != reference.sha256):
        raise _refuse("review_blob_digest_invalid")
    document = _document(payload)
    try:
        ArV3RunGroupId.parse(document["group_id"])
    except (TypeError, ValueError) as exc:
        raise _refuse("review_group_id_invalid") from exc
    group = get_ar_v3_group(session, document["group_id"])
    _verify_binding(document, run=run, metrics=stage.metrics, group=group)
    if (run_repo.get(session, run_id) != run
            or run_repo.stage_results(session, run_id) != stages
            or blob_repo.get(session, blob_id) != metadata
            or get_ar_v3_group(session, group.group_id) != group
            or publication_rows_exist(session, run_id)):
        raise _refuse("review_saved_facts_changed")
    return V3SavedReview(run_id, group.group_id, document["scope_id"], document)


__all__ = ["V3SavedReview", "read_v3_saved_review"]
