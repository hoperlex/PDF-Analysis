"""Transactional publication of a validated AR v2 merge plan.

This module is deliberately not exported by the runtime finding surface. The
caller supplies the outer unit of work; all groups are written in one savepoint.
The trusted caller must build the plan through ``plan_v2_merge_publication``
after ``finish_response``. A hand-built dataclass does not prove merge-rule
consistency or PDF grounding. Rejected proposals remain diagnostics and never
receive a finding or observation ID.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.analysis.public import AR_V2_CATEGORIES, AR_V2_SEVERITIES, RejectedProposal
from auditmanager.findings.merge_publication_plan import MergePublicationPlan, PlannedObservation
from auditmanager.shared.db import SQLSTATE_TO_CATALOG_CODE, nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId, FindingObservationId, FindingUid, ModelCallId,
    ProjectUid, PromptBundleId, RunId, VersionUid,
)


_INSERT_FINDING = text(
    "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
    "VALUES (:finding_uid, :project_uid, :version_uid, :run_id, :category)"
)
_INSERT_OBSERVATION = text(
    "INSERT INTO finding_observation ("
    "finding_observation_id, run_id, finding_uid, stage_id, category, "
    "finding_text, recommendation_text, grounded, ungrounded_reason, "
    "analysis_profile_id, prompt_bundle_id, model_call_id, provider_mode, proposed_severity"
    ") VALUES ("
    ":finding_observation_id, :run_id, :finding_uid, :stage_id, :category, "
    ":finding_text, :recommendation_text, :grounded, :ungrounded_reason, "
    ":analysis_profile_id, :prompt_bundle_id, :model_call_id, :provider_mode, :proposed_severity"
    ")"
)
_INSERT_EVIDENCE = text(
    "INSERT INTO finding_evidence ("
    "finding_observation_id, evidence_ordinal, page_number, quote, char_start, char_end, block_id"
    ") VALUES ("
    ":finding_observation_id, :evidence_ordinal, :page_number, :quote, "
    ":char_start, :char_end, :block_id"
    ")"
)
_SET_CANONICAL = text(
    "UPDATE finding SET canonical_observation_id = :canonical_observation_id "
    "WHERE finding_uid = :finding_uid AND canonical_observation_id IS NULL"
)


@dataclass(frozen=True, slots=True)
class V2PublicationContext:
    """Run and provider provenance supplied by the caller, never by the model."""

    run_id: str
    project_uid: str
    version_uid: str
    analysis_profile_id: str
    prompt_bundle_id: str
    provider_mode: str
    model_call_id: str | None = None


@dataclass(frozen=True, slots=True)
class PublishedV2Observation:
    finding_observation_id: str
    observation_ordinal: int
    source_proposal_ordinal: int
    evidence_count: int


@dataclass(frozen=True, slots=True)
class PublishedV2Finding:
    finding_uid: str
    category: str
    canonical_observation_id: str
    members: tuple[PublishedV2Observation, ...]


@dataclass(frozen=True, slots=True)
class V2PublicationResult:
    run_id: str
    findings: tuple[PublishedV2Finding, ...]
    rejected: tuple[RejectedProposal, ...]
    malformed_count: int
    salvaged: bool

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def observation_count(self) -> int:
        return sum(len(finding.members) for finding in self.findings)


def _validate_plan(plan: MergePublicationPlan) -> None:
    """Check structural invariants; the caller owns grounding and merge proof."""
    if not isinstance(plan, MergePublicationPlan):
        raise ValueError("v2_merge_publication_plan_required")
    seen: set[int] = set()
    sources: set[int] = set()
    for group in plan.groups:
        if not group.members or group.canonical not in group.members or group.category not in AR_V2_CATEGORIES:
            raise ValueError("v2_publication_group_invalid")
        for member in group.members:
            if not isinstance(member, PlannedObservation):
                raise ValueError("v2_publication_member_invalid")
            if member.proposal.category != group.category or member.proposal.proposed_severity not in AR_V2_SEVERITIES:
                raise ValueError("v2_publication_member_invalid")
            if (not member.evidence or len(member.evidence) != len(member.proposal.evidence)
                    or type(member.observation_ordinal) is not int
                    or type(member.source_proposal_ordinal) is not int
                    or member.observation_ordinal < 0 or member.source_proposal_ordinal < 0
                    or member.observation_ordinal in seen
                    or member.source_proposal_ordinal in sources):
                raise ValueError("v2_publication_member_invalid")
            for evidence in member.evidence:
                if (evidence.page_number < 1 or evidence.char_start < 0
                        or evidence.char_end - evidence.char_start != len(evidence.quote)
                        or not 1 <= len(evidence.quote) <= 2000):
                    raise ValueError("v2_publication_evidence_invalid")
            seen.add(member.observation_ordinal)
            sources.add(member.source_proposal_ordinal)
    if seen != set(range(len(seen))):
        raise ValueError("v2_publication_ordinals_not_dense")
    rejected = {item.proposal_ordinal for item in plan.rejected}
    if (sources & rejected or len(rejected) != len(plan.rejected)
            or sources | rejected != set(range(len(sources) + len(rejected)))):
        raise ValueError("v2_publication_source_ordinals_invalid")


def _validate_context(context: V2PublicationContext) -> None:
    if not isinstance(context, V2PublicationContext):
        raise ValueError("v2_publication_context_required")
    RunId.parse(context.run_id)
    ProjectUid.parse(context.project_uid)
    VersionUid.parse(context.version_uid)
    AnalysisProfileId.parse(context.analysis_profile_id)
    PromptBundleId.parse(context.prompt_bundle_id)
    ModelCallId.parse_optional(context.model_call_id)
    if context.provider_mode not in {"recorded", "live"}:
        raise ValueError("v2_publication_provider_mode_invalid")


def _translate_db_error(exc: DBAPIError) -> DomainError:
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(exc, "code", None)
    mapped = SQLSTATE_TO_CATALOG_CODE.get(str(sqlstate)) if sqlstate else None
    if mapped is not None:
        return DomainError(ErrorCode(mapped), message=f"the database refused the write ({sqlstate})")
    return DomainError(ErrorCode.INTERNAL_ERROR, message="the database refused the write")


def publish_v2_merge_plan(
    session: Session,
    *,
    plan: MergePublicationPlan,
    context: V2PublicationContext,
) -> V2PublicationResult:
    """Write all merged findings in one savepoint, without committing the run.

    A retry after savepoint rollback allocates new opaque IDs; run-level
    idempotency remains the caller's responsibility.
    """
    _validate_plan(plan)
    _validate_context(context)
    findings: list[PublishedV2Finding] = []
    try:
        with nested_transaction(session):
            for group in plan.groups:
                finding_uid = FindingUid.new().value
                session.execute(_INSERT_FINDING, {
                    "finding_uid": finding_uid,
                    "project_uid": context.project_uid,
                    "version_uid": context.version_uid,
                    "run_id": context.run_id,
                    "category": group.category,
                })
                members: list[PublishedV2Observation] = []
                canonical_id: str | None = None
                for member in group.members:
                    observation_id = FindingObservationId.new().value
                    proposal = member.proposal
                    session.execute(_INSERT_OBSERVATION, {
                        "finding_observation_id": observation_id,
                        "run_id": context.run_id,
                        "finding_uid": finding_uid,
                        "stage_id": "text_analysis",
                        "category": proposal.category,
                        "finding_text": proposal.finding_text,
                        "recommendation_text": proposal.recommendation_text,
                        "grounded": True,
                        "ungrounded_reason": None,
                        "analysis_profile_id": context.analysis_profile_id,
                        "prompt_bundle_id": context.prompt_bundle_id,
                        "model_call_id": context.model_call_id,
                        "provider_mode": context.provider_mode,
                        "proposed_severity": proposal.proposed_severity,
                    })
                    for evidence_ordinal, item in enumerate(member.evidence):
                        session.execute(_INSERT_EVIDENCE, {
                            "finding_observation_id": observation_id,
                            "evidence_ordinal": evidence_ordinal,
                            "page_number": item.page_number,
                            "quote": item.quote,
                            "char_start": item.char_start,
                            "char_end": item.char_end,
                            "block_id": item.block_id,
                        })
                    members.append(PublishedV2Observation(
                        observation_id, member.observation_ordinal,
                        member.source_proposal_ordinal, len(member.evidence),
                    ))
                    if member == group.canonical:
                        canonical_id = observation_id
                assert canonical_id is not None  # checked before opening the savepoint
                result = session.execute(_SET_CANONICAL, {
                    "canonical_observation_id": canonical_id,
                    "finding_uid": finding_uid,
                })
                if result.rowcount != 1:
                    raise RuntimeError("v2_canonical_update_refused")
                findings.append(PublishedV2Finding(
                    finding_uid, group.category, canonical_id, tuple(members)
                ))
    except DBAPIError as exc:
        raise _translate_db_error(exc) from exc
    return V2PublicationResult(
        context.run_id, tuple(findings), plan.rejected, plan.malformed_count, plan.salvaged
    )
