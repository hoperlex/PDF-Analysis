"""Read six AR v3 beta outcomes without exposing internal review custody facts."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_group import SCOPES, get_ar_v3_group
from auditmanager.runs.v3_review_reader import V3SavedReview, read_v3_saved_review
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobMetadataRepository, BlobStore


@dataclass(frozen=True, slots=True)
class V3VisibleTopic:
    item_id: str
    mode: str
    reason: str
    source_ids: tuple[str, ...]
    review_status: str
    provisional_citation_count: int


@dataclass(frozen=True, slots=True)
class V3VisibleEvidence:
    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class V3VisibleCitation:
    item_id: str
    label: str
    document_id: str
    paragraph_id: str
    raw_quote: str
    state: str


@dataclass(frozen=True, slots=True)
class V3VisibleProposal:
    proposal_ordinal: int
    evidence: tuple[V3VisibleEvidence, ...]
    citations: tuple[V3VisibleCitation, ...]


@dataclass(frozen=True, slots=True)
class V3VisibleReview:
    topics: tuple[V3VisibleTopic, ...]
    provisional_citations: tuple[V3VisibleProposal, ...]
    withheld_proposal_count: int
    rejected_proposal_count: int


@dataclass(frozen=True, slots=True)
class V3ScopeOutcome:
    scope_id: str
    run_id: str
    run_state: str
    review_state: str
    terminal_reason: str | None = None
    refusal_code: str | None = None
    review: V3VisibleReview | None = None


@dataclass(frozen=True, slots=True)
class V3GroupReview:
    group_id: str
    version_uid: str
    members: tuple[V3ScopeOutcome, ...]


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="AR v3 group review membership changed or is incomplete",
        stage_id="ar_v3_citation_review", reason=reason,
    )


def _visible(saved: V3SavedReview) -> V3VisibleReview:
    """Copy a small declared subset; private hashes and Blob pointers never leave."""
    document = saved.document
    try:
        topics = tuple(V3VisibleTopic(
            item_id=row["item_id"], mode=row["mode"], reason=row["reason"],
            source_ids=tuple(row["source_ids"]),
            review_status=row["review_status"],
            provisional_citation_count=row["provisional_citation_count"],
        ) for row in document["topics"])
        proposals = tuple(V3VisibleProposal(
            proposal_ordinal=row["proposal_ordinal"],
            evidence=tuple(V3VisibleEvidence(
                page_number=item["page_number"], quote=item["quote"],
            ) for item in row["evidence"]),
            citations=tuple(V3VisibleCitation(
                item_id=item["item_id"], label=item["label"],
                document_id=item["document_id"], paragraph_id=item["paragraph_id"],
                raw_quote=item["raw_quote"], state=item["state"],
            ) for item in row["citations"]),
        ) for row in document["provisional_citations"])
        return V3VisibleReview(
            topics, proposals, len(document["withheld_proposals"]),
            len(document["rejected_proposals"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _refuse("review_projection_invalid") from exc


def read_v3_group_review(
    session: Session, group_id: str, *, blob_store: BlobStore,
    runs: RunRepository | None = None,
    blobs: BlobMetadataRepository | None = None,
) -> V3GroupReview:
    """Collect every durable member and report each review or explicit refusal."""
    run_repo = runs or RunRepository()
    blob_repo = blobs or BlobMetadataRepository()
    group = get_ar_v3_group(session, group_id)
    if (tuple(member.scope_id for member in group.members) != SCOPES
            or len({member.run_id for member in group.members}) != len(SCOPES)):
        raise _refuse("group_members_invalid")
    outcomes: list[V3ScopeOutcome] = []
    for member in group.members:
        if member.state in {"created", "queued", "running", "validating"}:
            outcomes.append(V3ScopeOutcome(
                member.scope_id, member.run_id, member.state, "pending",
            ))
            continue
        if member.state in {"failed", "cancelled"}:
            run = run_repo.get(session, member.run_id)
            if run.state != member.state:
                raise _refuse("group_member_state_changed")
            outcomes.append(V3ScopeOutcome(
                member.scope_id, member.run_id, member.state, "failed",
                terminal_reason=run.terminal_reason,
            ))
            continue
        if member.state not in {"published", "partial"}:
            raise _refuse("group_member_state_unknown")
        try:
            saved = read_v3_saved_review(
                session, member.run_id, blob_store=blob_store,
                runs=run_repo, blobs=blob_repo,
            )
            if (saved.group_id != group.group_id
                    or saved.scope_id != member.scope_id):
                raise _refuse("review_member_scope_invalid")
            visible = _visible(saved)
        except DomainError as error:
            if error.code not in {
                ErrorCode.ANALYSIS_INPUT_INVALID,
                ErrorCode.STORAGE_INTEGRITY_ERROR,
            }:
                raise
            outcomes.append(V3ScopeOutcome(
                member.scope_id, member.run_id, member.state,
                "verification_refused", refusal_code=error.code.value,
            ))
        else:
            outcomes.append(V3ScopeOutcome(
                member.scope_id, member.run_id, member.state,
                "available", review=visible,
            ))
    if get_ar_v3_group(session, group_id) != group:
        raise _refuse("group_changed_during_review_read")
    return V3GroupReview(group.group_id, group.version_uid, tuple(outcomes))


__all__ = [
    "V3GroupReview", "V3ScopeOutcome", "V3VisibleCitation", "V3VisibleEvidence",
    "V3VisibleProposal", "V3VisibleReview", "V3VisibleTopic", "read_v3_group_review",
]
