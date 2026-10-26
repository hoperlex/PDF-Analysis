"""Approve and withdraw a sheet pairing (`COMPARE-PERSISTED-SUMMARY-01`, `approveSheetPairing`
and `withdrawSheetPairing`).

The served comparison (:class:`~auditmanager.comparison.service.VersionComparisonService`)
*proposes* sheet pairs and writes nothing. This module adds the writes an expert's confirmation
leads to, over the append-only history in ``comparison_sheet_link``
(:mod:`~auditmanager.comparison.sheet_links`):

* **Nothing is approved without the confirmation, and not what was not shown.** The comparison is
  recomputed for the request's versions, mode and runs inside the writing transaction and must
  still propose exactly the named pages under exactly the named ``suggestion_sha256`` (which binds
  both page texts and the pairing rule). A stale, swapped, foreign or invented pair is
  ``conflict`` / ``sheet_pair_not_proposed``. A pair the algorithm did not propose cannot be
  approved by this command.
* **The evidence is sealed with the approval.** The approved set after the new row is diffed by
  :func:`~auditmanager.comparison.raw_text.diff_approved_pairs` and bound by
  :func:`~auditmanager.comparison.raw_evidence_seal.seal_raw_version_evidence`; the seal is stored
  on the row. The read recomputes it, so a later change of the text is visible.
* **Withdrawal is a new row.** It repeats the approval's pages and digests, ends the link, and
  stores the seal of what remains (``NULL`` when nothing remains, or when what remains cannot be
  sealed). Nothing is updated or deleted.
* **Expert only** (`R-60`, like ``appendDecision`` and ``carryOverDecision``): the role set, read
  in the writing transaction, must hold ``expert``; ``admin`` alone is ``permission_denied``.
* **One transaction.** The receipt (``command_record``), the row and its audit event
  (:mod:`~auditmanager.comparison.audit`) commit together or not at all. A refusal raises after the
  receipt was claimed, and the caller's rollback takes the receipt with it.
* **Idempotent.** The same key replays the stored answer; an exact repeat of an active link under
  another key answers that link (``replayed``) and appends nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.comparison.approved_evidence import (
    ApprovedEvidenceRefused,
    link_is_verified,
    raw_artifact,
)
from auditmanager.comparison.audit import (
    record_sheet_link_approved,
    record_sheet_link_withdrawn,
)
from auditmanager.comparison.decision_carryover import (
    DecisionCarryoverRefused,
    require_carryover_expert,
)
from auditmanager.comparison.read_model import MODES
from auditmanager.comparison.service import ComparisonRequest, VersionComparisonService
from auditmanager.comparison.sheet_links import (
    KIND_APPROVED,
    KIND_WITHDRAWN,
    MAX_ACTIVE_LINKS,
    LinkEvent,
    NewLinkEvent,
    SheetLinkRepository,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    ComparisonId,
    DocumentUid,
    IdentityError,
    ProjectUid,
    RunId,
    SheetLinkId,
    VersionUid,
)

__all__ = [
    "ApproveSheetPairingRequest",
    "PairingOutcome",
    "SheetPairingService",
    "WithdrawSheetPairingRequest",
]

COMMAND_APPROVE: Final[str] = "approve_sheet_pairing"
COMMAND_WITHDRAW: Final[str] = "withdraw_sheet_pairing"
#: ``permission_denied`` detail of a pairing command by an account without the expert role.
REQUIRED_CAPABILITY: Final[str] = "role:expert"
AGGREGATE_TYPE: Final[str] = "SheetLink"

CONFLICT_SHEET_PAIR_NOT_PROPOSED: Final[str] = "sheet_pair_not_proposed"
CONFLICT_SHEET_PAGE_ALREADY_PAIRED: Final[str] = "sheet_page_already_paired"
CONFLICT_SHEET_PAIR_LIMIT_REACHED: Final[str] = "sheet_pair_limit_reached"
CONFLICT_SHEET_PAIR_TOO_LARGE: Final[str] = "sheet_pair_too_large"
CONFLICT_APPROVED_TEXT_CHANGED: Final[str] = "approved_text_changed"
CONFLICT_SHEET_LINK_NOT_ACTIVE: Final[str] = "sheet_link_not_active"
CONFLICT_COMPARISON_NOT_AVAILABLE: Final[str] = "comparison_not_available"
CONFLICT_REASONS: Final[tuple[str, ...]] = (
    CONFLICT_SHEET_PAIR_NOT_PROPOSED,
    CONFLICT_SHEET_PAGE_ALREADY_PAIRED,
    CONFLICT_SHEET_PAIR_LIMIT_REACHED,
    CONFLICT_SHEET_PAIR_TOO_LARGE,
    CONFLICT_APPROVED_TEXT_CHANGED,
    CONFLICT_SHEET_LINK_NOT_ACTIVE,
    CONFLICT_COMPARISON_NOT_AVAILABLE,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_PAGE_NUMBER: Final[int] = 500
MAX_LABEL_LENGTH: Final[int] = 128


@dataclass(frozen=True, slots=True)
class ApproveSheetPairingRequest:
    """One confirmation: the comparison it was shown in, the pages and the proposal's digest."""

    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    source_page_number: int
    target_page_number: int
    suggestion_sha256: str
    mode: str = "version"
    source_run_id: str | None = None
    target_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class WithdrawSheetPairingRequest:
    """The end of one link. ``mode`` and the runs choose the text the remaining set is sealed over."""

    project_uid: str
    document_uid: str
    source_version_uid: str
    sheet_link_id: str
    mode: str = "version"
    source_run_id: str | None = None
    target_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class PairingOutcome:
    """The row an operation wrote or answered. ``replayed``: nothing was appended by this call."""

    event: LinkEvent
    replayed: bool


def _invalid(field: str, constraint: str = "format") -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, aggregate_type=AGGREGATE_TYPE, conflict_reason=reason)


def _check_identities(request: object, fields: tuple[tuple[str, type], ...]) -> None:
    for field, kind in fields:
        try:
            kind.parse(getattr(request, field))  # type: ignore[attr-defined]
        except (IdentityError, DomainError, TypeError):
            raise _invalid(field) from None


def _check_common(request: ApproveSheetPairingRequest | WithdrawSheetPairingRequest) -> None:
    for field in ("source_run_id", "target_run_id"):
        value = getattr(request, field)
        if value is None:
            continue
        try:
            RunId.parse(value)
        except (IdentityError, DomainError, TypeError):
            raise _invalid(field) from None
    if request.mode not in MODES:
        raise _invalid("mode", "enum")


def _check_approve(request: ApproveSheetPairingRequest) -> None:
    if not isinstance(request, ApproveSheetPairingRequest):
        raise _invalid("request")
    _check_identities(request, (
        ("project_uid", ProjectUid), ("document_uid", DocumentUid),
        ("source_version_uid", VersionUid), ("target_version_uid", VersionUid),
    ))
    _check_common(request)
    for field in ("source_page_number", "target_page_number"):
        value = getattr(request, field)
        if type(value) is not int or not 1 <= value <= MAX_PAGE_NUMBER:
            raise _invalid(field, "range")
    if not isinstance(request.suggestion_sha256, str) or _SHA256.fullmatch(request.suggestion_sha256) is None:
        raise _invalid("suggestion_sha256")
    if request.source_version_uid == request.target_version_uid:
        raise _conflict(CONFLICT_SHEET_PAIR_NOT_PROPOSED)


def _check_withdraw(request: WithdrawSheetPairingRequest) -> None:
    if not isinstance(request, WithdrawSheetPairingRequest):
        raise _invalid("request")
    _check_identities(request, (
        ("project_uid", ProjectUid), ("document_uid", DocumentUid),
        ("source_version_uid", VersionUid), ("sheet_link_id", SheetLinkId),
    ))
    _check_common(request)


def _check_label(actor_label: str) -> None:
    if (
        not isinstance(actor_label, str)
        or not 1 <= len(actor_label) <= MAX_LABEL_LENGTH
        or actor_label != actor_label.strip(" \t\r\n")
    ):
        raise _invalid("actor_label")


def _require_expert(actor_uid: str, actor_roles: frozenset[str]) -> None:
    try:
        require_carryover_expert(actor_uid, actor_roles)
    except DecisionCarryoverRefused:
        raise DomainError(
            ErrorCode.PERMISSION_DENIED, required_capability=REQUIRED_CAPABILITY,
        ) from None


def _outcome(event: LinkEvent) -> dict[str, object]:
    return {
        "comparison_id": event.comparison_id,
        "link_revision": event.link_revision,
        "sheet_link_id": event.sheet_link_id,
        "event_kind": event.event_kind,
    }


class SheetPairingService:
    """The two pairing commands over a freshly recomputed comparison."""

    def __init__(self, *, comparisons: VersionComparisonService, links: SheetLinkRepository) -> None:
        if not isinstance(comparisons, VersionComparisonService):
            raise TypeError("comparisons must be the served VersionComparisonService")
        if not isinstance(links, SheetLinkRepository):
            raise TypeError("links must be the SheetLinkRepository")
        self._comparisons = comparisons
        self._links = links

    # -- approve -----------------------------------------------------------------

    def approve(
        self,
        session: Session,
        request: ApproveSheetPairingRequest,
        *,
        actor_uid: str,
        actor_label: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> PairingOutcome:
        """Approve the confirmed pair, or refuse. The caller owns the (write) transaction.

        Order: request shape (``validation_failed``), the expert role (``permission_denied``),
        the path (``not_found``), the receipt, the recomputed proposal (``conflict``), the
        history's own rules, the seal, the row, its audit event, the receipt's outcome.
        """
        _check_approve(request)
        _check_label(actor_label)
        _require_expert(actor_uid, actor_roles)
        self._prove_path(session, request.project_uid, request.document_uid, request.source_version_uid)
        commands = CommandRepository()
        claimed = commands.begin(
            session,
            command_type=COMMAND_APPROVE,
            idempotency_key=idempotency_key,  # type: ignore[arg-type]
            fingerprint=payload_fingerprint({
                "command": "approve_sheet_pairing.v1",
                "project_uid": request.project_uid,
                "document_uid": request.document_uid,
                "source_version_uid": request.source_version_uid,
                "target_version_uid": request.target_version_uid,
                "source_page_number": request.source_page_number,
                "target_page_number": request.target_page_number,
                "suggestion_sha256": request.suggestion_sha256,
                "mode": request.mode,
                "source_run_id": request.source_run_id,
                "target_run_id": request.target_run_id,
                "actor_uid": actor_uid,
            }),
        )
        if isinstance(claimed, CommandReplay):
            return PairingOutcome(self._stored(session, claimed.outcome, COMMAND_APPROVE), True)

        self._links.lock_pair(
            session, source_version_uid=request.source_version_uid,
            target_version_uid=request.target_version_uid,
        )
        current = self._comparisons.current_comparison(session, ComparisonRequest(
            project_uid=request.project_uid,
            document_uid=request.document_uid,
            source_version_uid=request.source_version_uid,
            target_version_uid=request.target_version_uid,
            source_run_id=request.source_run_id,
            target_run_id=request.target_run_id,
            mode=request.mode,
        ))
        proposed = next(
            (
                item for item in current.suggestions
                if item.source_page_number == request.source_page_number
                and item.target_page_number == request.target_page_number
                and item.suggestion_sha256 == request.suggestion_sha256
            ),
            None,
        )
        if current.pair is None or proposed is None:
            raise _conflict(CONFLICT_SHEET_PAIR_NOT_PROPOSED)

        state = self._links.state(
            session, source_version_uid=request.source_version_uid,
            target_version_uid=request.target_version_uid,
        )
        active = state.active
        same = next(
            (
                link for link in active
                if link.source_page_number == request.source_page_number
                and link.target_page_number == request.target_page_number
                and link.suggestion_sha256 == proposed.suggestion_sha256
                and link.source_page_text_sha256 == proposed.source_page_text_sha256
                and link.target_page_text_sha256 == proposed.target_page_text_sha256
            ),
            None,
        )
        if same is not None:
            commands.succeed(session, claimed.command_id, _outcome(same))
            return PairingOutcome(same, True)
        if any(
            link.source_page_number == request.source_page_number
            or link.target_page_number == request.target_page_number
            for link in active
        ):
            raise _conflict(CONFLICT_SHEET_PAGE_ALREADY_PAIRED)
        if len(active) >= MAX_ACTIVE_LINKS:
            raise _conflict(CONFLICT_SHEET_PAIR_LIMIT_REACHED)
        if not all(
            link_is_verified(link, current.source_pages, current.target_pages) for link in active
        ):
            raise _conflict(CONFLICT_APPROVED_TEXT_CHANGED)

        comparison_id = state.comparison_id or str(ComparisonId.new())
        sheet_link_id = str(SheetLinkId.new())
        revision = state.latest_revision + 1
        try:
            _, seal = raw_artifact(
                pair=current.pair,
                comparison_id=comparison_id,
                link_revision=revision,
                links=[
                    (link.sheet_link_id, link.source_page_number, link.target_page_number)
                    for link in active
                ] + [(sheet_link_id, request.source_page_number, request.target_page_number)],
                source_pages=current.source_pages,
                target_pages=current.target_pages,
            )
        except ApprovedEvidenceRefused:
            raise _conflict(CONFLICT_SHEET_PAIR_TOO_LARGE) from None

        event = self._links.append(session, NewLinkEvent(
            comparison_id=comparison_id,
            link_revision=revision,
            event_kind=KIND_APPROVED,
            sheet_link_id=sheet_link_id,
            project_uid=request.project_uid,
            document_uid=request.document_uid,
            source_version_uid=request.source_version_uid,
            target_version_uid=request.target_version_uid,
            source_page_number=request.source_page_number,
            target_page_number=request.target_page_number,
            source_page_text_sha256=proposed.source_page_text_sha256,
            target_page_text_sha256=proposed.target_page_text_sha256,
            suggestion_sha256=proposed.suggestion_sha256,
            raw_evidence_seal_sha256=seal.seal_sha256,
            actor_user_uid=actor_uid,
            actor_label=actor_label,
            command_id=str(claimed.command_id),
        ))
        record_sheet_link_approved(
            session,
            comparison_id=event.comparison_id,
            sheet_link_id=event.sheet_link_id,
            link_revision=event.link_revision,
            source_version_uid=event.source_version_uid,
            target_version_uid=event.target_version_uid,
            source_page_number=event.source_page_number,
            target_page_number=event.target_page_number,
            actor_uid=actor_uid,
            raw_evidence_seal_sha256=seal.seal_sha256,
            correlation_id=correlation_id,
        )
        commands.succeed(session, claimed.command_id, _outcome(event))
        return PairingOutcome(event, False)

    # -- withdraw ----------------------------------------------------------------

    def withdraw(
        self,
        session: Session,
        request: WithdrawSheetPairingRequest,
        *,
        actor_uid: str,
        actor_label: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> PairingOutcome:
        """End one active link with a new row, or refuse. The caller owns the transaction."""
        _check_withdraw(request)
        _check_label(actor_label)
        _require_expert(actor_uid, actor_roles)
        self._prove_path(session, request.project_uid, request.document_uid, request.source_version_uid)
        commands = CommandRepository()
        claimed = commands.begin(
            session,
            command_type=COMMAND_WITHDRAW,
            idempotency_key=idempotency_key,  # type: ignore[arg-type]
            fingerprint=payload_fingerprint({
                "command": "withdraw_sheet_pairing.v1",
                "project_uid": request.project_uid,
                "document_uid": request.document_uid,
                "source_version_uid": request.source_version_uid,
                "sheet_link_id": request.sheet_link_id,
                "mode": request.mode,
                "source_run_id": request.source_run_id,
                "target_run_id": request.target_run_id,
                "actor_uid": actor_uid,
            }),
        )
        if isinstance(claimed, CommandReplay):
            return PairingOutcome(self._stored(session, claimed.outcome, COMMAND_WITHDRAW), True)

        approval = self._links.find_approval(
            session, project_uid=request.project_uid, document_uid=request.document_uid,
            source_version_uid=request.source_version_uid, sheet_link_id=request.sheet_link_id,
        )
        if approval is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_TYPE)
        self._links.lock_pair(
            session, source_version_uid=approval.source_version_uid,
            target_version_uid=approval.target_version_uid,
        )
        state = self._links.state(
            session, source_version_uid=approval.source_version_uid,
            target_version_uid=approval.target_version_uid,
        )
        if request.sheet_link_id not in {link.sheet_link_id for link in state.active}:
            raise _conflict(CONFLICT_SHEET_LINK_NOT_ACTIVE)
        current = self._comparisons.current_comparison(session, ComparisonRequest(
            project_uid=request.project_uid,
            document_uid=request.document_uid,
            source_version_uid=approval.source_version_uid,
            target_version_uid=approval.target_version_uid,
            source_run_id=request.source_run_id,
            target_run_id=request.target_run_id,
            mode=request.mode,
        ))
        if current.pair is None:
            raise _conflict(CONFLICT_COMPARISON_NOT_AVAILABLE)

        revision = state.latest_revision + 1
        remaining = [link for link in state.active if link.sheet_link_id != request.sheet_link_id]
        seal: str | None = None
        if remaining and all(
            link_is_verified(link, current.source_pages, current.target_pages) for link in remaining
        ):
            try:
                _, sealed = raw_artifact(
                    pair=current.pair,
                    comparison_id=approval.comparison_id,
                    link_revision=revision,
                    links=[
                        (link.sheet_link_id, link.source_page_number, link.target_page_number)
                        for link in remaining
                    ],
                    source_pages=current.source_pages,
                    target_pages=current.target_pages,
                )
                seal = sealed.seal_sha256
            except ApprovedEvidenceRefused:
                seal = None
        event = self._links.append(session, NewLinkEvent(
            comparison_id=approval.comparison_id,
            link_revision=revision,
            event_kind=KIND_WITHDRAWN,
            sheet_link_id=approval.sheet_link_id,
            project_uid=approval.project_uid,
            document_uid=approval.document_uid,
            source_version_uid=approval.source_version_uid,
            target_version_uid=approval.target_version_uid,
            source_page_number=approval.source_page_number,
            target_page_number=approval.target_page_number,
            source_page_text_sha256=approval.source_page_text_sha256,
            target_page_text_sha256=approval.target_page_text_sha256,
            suggestion_sha256=approval.suggestion_sha256,
            raw_evidence_seal_sha256=seal,
            actor_user_uid=actor_uid,
            actor_label=actor_label,
            command_id=str(claimed.command_id),
        ))
        record_sheet_link_withdrawn(
            session,
            comparison_id=event.comparison_id,
            sheet_link_id=event.sheet_link_id,
            link_revision=event.link_revision,
            source_version_uid=event.source_version_uid,
            target_version_uid=event.target_version_uid,
            source_page_number=event.source_page_number,
            target_page_number=event.target_page_number,
            actor_uid=actor_uid,
            raw_evidence_seal_sha256=seal,
            correlation_id=correlation_id,
        )
        commands.succeed(session, claimed.command_id, _outcome(event))
        return PairingOutcome(event, False)

    # -- shared ------------------------------------------------------------------

    @staticmethod
    def _prove_path(
        session: Session, project_uid: str, document_uid: str, source_version_uid: str,
    ) -> None:
        """An unknown project, a document of another project or a source version of another
        document is ``404`` exactly as for every addressed read (`D-67`)."""
        DocumentRepository().get_version_in(
            session,
            project_uid=ProjectUid.parse(project_uid),
            document_uid=DocumentUid.parse(document_uid),
            version_uid=VersionUid.parse(source_version_uid),
        )

    def _stored(self, session: Session, outcome: object, command_type: str) -> LinkEvent:
        """The row an earlier success of this key wrote (or answered)."""
        comparison_id = outcome.get("comparison_id") if hasattr(outcome, "get") else None
        revision = outcome.get("link_revision") if hasattr(outcome, "get") else None
        event = (
            self._links.event_at(session, comparison_id=comparison_id, link_revision=revision)
            if isinstance(comparison_id, str) and type(revision) is int else None
        )
        if event is None:
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=command_type)
        return event
