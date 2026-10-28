"""Generate and store the AI summary of the approved pairs (`COMPARE-PERSISTED-SUMMARY-01`, B2; owner's `C-2`).

«Sheet pairing, deterministic text differences as evidence, AI classification and summary on top; AI
never alters the raw differences.» The deterministic layer is :mod:`~auditmanager.comparison.pairing`
and :mod:`~auditmanager.comparison.approved_evidence`; this module is the summary on top:

* **A command, never a read.** :meth:`SummaryService.generate` is the only way to a model call, and it
  needs the caller's idempotency key. ``compareDocumentVersions`` only *reads* the latest stored
  summary, so a reader cannot cause spend.
* **It summarises the sealed evidence, recomputed in the writing transaction.** The approved set must be
  ``sealed`` (every page still the approved text, the seal reproduced); the bounded input is projected by
  :func:`~auditmanager.comparison.summary_input.prepare_version_summary_input`, which rechecks the seal and
  refuses an oversize input instead of shortening it. The input digest and the seal are computed here,
  never taken from the request.
* **An exact repeat never pays twice.** One ``ready`` summary exists per (comparison, revision, input
  digest, prompt version); asking again answers it.
* **The reply is checked, not trusted.** The validator holds every cited span to the input
  (:mod:`~auditmanager.comparison.summary_validation`). A rejected reply is **recorded** (it was paid for)
  as a ``rejected`` row without statements and is shown as an answer, not an error.
* **Cost goes through the meter.** ``check_before_call`` before the call; after it the reply's cost is
  recorded through the same meter: ``unmetered`` for the recorded binding only. An implementation that
  reports a cost this wave cannot verify is refused.
* **Append-only, and the raw differences are never touched.** The row holds the model's statements and the
  span identities they cite; nothing in it is read back into the approved differences.
* **Expert only** (`R-60`), one transaction with the receipt, the row and its audit event (whose identity is
  the summary's), like the pairing commands.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Protocol, runtime_checkable

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.audit import record_summary_generated
from auditmanager.comparison.pairing import (
    CONFLICT_COMPARISON_NOT_AVAILABLE,
    _check_common,
    _check_identities,
    _check_label,
    _conflict,
    _require_expert,
    _stored_outcome,
)
from auditmanager.comparison.service import ComparisonRequest, SealedEvidence, VersionComparisonService
from auditmanager.comparison.sheet_links import SheetLinkRepository
from auditmanager.comparison.summary_input import SummaryInputRefused, prepare_version_summary_input
from auditmanager.comparison.summary_model import SummaryModel
from auditmanager.comparison.summary_records import (
    COST_BASES,
    STATE_READY,
    STATE_REJECTED,
    SUMMARY_STATES,
    LatestSummaryReader,
    StoredSummary,
)
from auditmanager.comparison.summary_prompt import PROMPT_VERSION, build_request
from auditmanager.comparison.summary_validation import (
    REJECTION_REASONS,
    Statement,
    SummaryRejected,
    parse_reply,
    statements_json,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AuditEventId,
    DocumentUid,
    ProjectUid,
    VersionUid,
)

COMMAND_GENERATE: Final[str] = "generate_comparison_summary"
AGGREGATE_TYPE: Final[str] = "ComparisonSummary"
CONFLICT_SUMMARY_EVIDENCE_NOT_SEALED: Final[str] = "summary_evidence_not_sealed"
CONFLICT_SUMMARY_INPUT_EMPTY: Final[str] = "summary_input_empty"
CONFLICT_SUMMARY_INPUT_TOO_LARGE: Final[str] = "summary_input_too_large"
SUMMARY_CONFLICT_REASONS: Final[tuple[str, ...]] = (
    CONFLICT_SUMMARY_EVIDENCE_NOT_SEALED,
    CONFLICT_SUMMARY_INPUT_EMPTY,
    CONFLICT_SUMMARY_INPUT_TOO_LARGE,
)
DEPENDENCY_SUMMARY_MODEL: Final[str] = "comparison_summary_model"



@runtime_checkable
class SummaryCostGate(Protocol):
    """The cost meter, as this command needs it. The composition root backs it with ``CostMeter``."""

    def before_call(self) -> None:
        """Halt (``cost_budget_exceeded``) before spending anything once the ceiling is reached."""

    def after_unmetered_call(self) -> tuple[str, int]:
        """Record one call through the unmetered recorded binding: ``(cost_basis, cost_micros)``."""


@dataclass(frozen=True, slots=True)
class GenerateSummaryRequest:
    """One command: the comparison view the expert is looking at. Nothing else is taken from the client."""

    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    mode: str = "version"
    source_run_id: str | None = None
    target_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class SummaryOutcome:
    """The summary the command answers, and whether it describes the approved set as it stands now.

    ``is_current`` is judged from the sealed evidence recomputed in the same transaction, for a first
    answer and for a replay alike: a retry with an old key after the set changed answers the old row
    and says it is not current (the same rule as the served read, ``VersionComparisonService.compare``).
    """

    summary: StoredSummary
    replayed: bool
    is_current: bool


_COLUMNS: Final[str] = (
    "summary_id, comparison_id, link_revision, project_uid, raw_evidence_seal_sha256, input_sha256, "
    "request_sha256, prompt_version, provider_mode, model_identity, state, rejection_reason, "
    "statements, cost_basis, cost_micros, actor_user_uid, actor_label, command_id, created_at"
)
_LATEST = text(
    f"SELECT {_COLUMNS} FROM comparison_summary WHERE comparison_id = :comparison_id "
    "ORDER BY created_at DESC, summary_id DESC LIMIT 1"
)
_READY_FOR = text(
    f"SELECT {_COLUMNS} FROM comparison_summary WHERE comparison_id = :comparison_id "
    "AND link_revision = :link_revision AND input_sha256 = :input_sha256 "
    "AND prompt_version = :prompt_version AND state = 'ready'"
)
_BY_ID = text(f"SELECT {_COLUMNS} FROM comparison_summary WHERE summary_id = :summary_id")
_INSERT = text(
    "INSERT INTO comparison_summary (summary_id, comparison_id, link_revision, project_uid, "
    "raw_evidence_seal_sha256, input_sha256, request_sha256, prompt_version, provider_mode, "
    "model_identity, state, rejection_reason, statements, cost_basis, cost_micros, actor_user_uid, "
    "actor_label, command_id) VALUES (:summary_id, :comparison_id, :link_revision, :project_uid, "
    ":raw_evidence_seal_sha256, :input_sha256, :request_sha256, :prompt_version, :provider_mode, "
    ":model_identity, :state, :rejection_reason, CAST(:statements AS jsonb), :cost_basis, "
    ":cost_micros, :actor_user_uid, :actor_label, :command_id) RETURNING created_at"
)


def _stored(row: object) -> StoredSummary:
    values = list(row)  # type: ignore[call-overload]
    raw = values[12]
    statements = tuple(
        Statement(str(item["text"]), tuple(str(i) for i in item["hunk_ids"]))
        for item in (json.loads(raw) if isinstance(raw, str) else raw)
    )
    return StoredSummary(*values[:12], statements, *values[13:])


class SummaryStore:
    """SQL for ``comparison_summary``. The caller owns the transaction."""

    def latest(self, session: Session, *, comparison_id: str) -> StoredSummary | None:
        row = session.execute(_LATEST, {"comparison_id": comparison_id}).first()
        return None if row is None else _stored(row)

    def ready_for(
        self, session: Session, *, comparison_id: str, link_revision: int, input_sha256: str,
        prompt_version: str,
    ) -> StoredSummary | None:
        row = session.execute(_READY_FOR, {
            "comparison_id": comparison_id, "link_revision": link_revision,
            "input_sha256": input_sha256, "prompt_version": prompt_version,
        }).first()
        return None if row is None else _stored(row)

    def by_id(self, session: Session, *, summary_id: str) -> StoredSummary | None:
        row = session.execute(_BY_ID, {"summary_id": summary_id}).first()
        return None if row is None else _stored(row)

    def append(self, session: Session, summary: StoredSummary) -> StoredSummary:
        """INSERT one summary. The database refuses a stale revision, a foreign project or a wrong seal."""
        created_at = session.execute(_INSERT, {
            "summary_id": summary.summary_id, "comparison_id": summary.comparison_id,
            "link_revision": summary.link_revision, "project_uid": summary.project_uid,
            "raw_evidence_seal_sha256": summary.raw_evidence_seal_sha256,
            "input_sha256": summary.input_sha256, "request_sha256": summary.request_sha256,
            "prompt_version": summary.prompt_version, "provider_mode": summary.provider_mode,
            "model_identity": summary.model_identity, "state": summary.state,
            "rejection_reason": summary.rejection_reason,
            "statements": json.dumps(statements_json(summary.statements), ensure_ascii=False),
            "cost_basis": summary.cost_basis, "cost_micros": summary.cost_micros,
            "actor_user_uid": summary.actor_user_uid, "actor_label": summary.actor_label,
            "command_id": summary.command_id,
        }).scalar_one()
        return StoredSummary(
            **{name: getattr(summary, name) for name in StoredSummary.__dataclass_fields__
               if name != "created_at"},
            created_at=created_at,
        )


class SummaryService:
    """The one command that calls a model about a comparison."""

    def __init__(
        self,
        *,
        comparisons: VersionComparisonService,
        links: SheetLinkRepository,
        summaries: SummaryStore,
        model: SummaryModel | None,
        cost_gate: Callable[[], SummaryCostGate] | None,
    ) -> None:
        if not isinstance(comparisons, VersionComparisonService):
            raise TypeError("comparisons must be the served VersionComparisonService")
        if model is not None and not isinstance(model, SummaryModel):
            raise TypeError("model must satisfy SummaryModel")
        if model is not None and cost_gate is None:
            raise TypeError("a summary model without a cost gate would spend unmeasured")
        self._comparisons = comparisons
        self._links = links
        self._summaries = summaries
        self._model = model
        self._cost_gate = cost_gate

    def generate(
        self,
        session: Session,
        request: GenerateSummaryRequest,
        *,
        actor_uid: str,
        actor_label: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> SummaryOutcome:
        """Summarise the sealed approved pairs, or refuse. The caller owns the (write) transaction.

        Order: request shape (``validation_failed``), the expert role (``permission_denied``), the path
        (``not_found``), a model to call (``dependency_unavailable``), the receipt, the recomputed sealed
        evidence and its bounded input (``conflict``), an answer already stored for this exact input, the
        cost ceiling, the model call, the validator, the row, its audit event, the receipt's outcome.
        """
        if not isinstance(request, GenerateSummaryRequest):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="request", constraint="format")
        _check_identities(request, (
            ("project_uid", ProjectUid), ("document_uid", DocumentUid),
            ("source_version_uid", VersionUid), ("target_version_uid", VersionUid),
        ))
        _check_common(request)
        _check_label(actor_label)
        _require_expert(actor_uid, actor_roles)
        DocumentRepository().get_version_in(
            session,
            project_uid=ProjectUid.parse(request.project_uid),
            document_uid=DocumentUid.parse(request.document_uid),
            version_uid=VersionUid.parse(request.source_version_uid),
        )
        if self._model is None or self._cost_gate is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY_SUMMARY_MODEL)

        commands = CommandRepository()
        claimed = commands.begin(
            session,
            command_type=COMMAND_GENERATE,
            idempotency_key=idempotency_key,  # type: ignore[arg-type]
            fingerprint=payload_fingerprint({
                "command": "generate_comparison_summary.v1",
                "project_uid": request.project_uid,
                "document_uid": request.document_uid,
                "source_version_uid": request.source_version_uid,
                "target_version_uid": request.target_version_uid,
                "mode": request.mode,
                "source_run_id": request.source_run_id,
                "target_run_id": request.target_run_id,
                "actor_uid": actor_uid,
            }),
        )
        comparison_request = ComparisonRequest(
            project_uid=request.project_uid, document_uid=request.document_uid,
            source_version_uid=request.source_version_uid,
            target_version_uid=request.target_version_uid,
            source_run_id=request.source_run_id, target_run_id=request.target_run_id,
            mode=request.mode,
        )
        if isinstance(claimed, CommandReplay):
            # The stored row is the answer, but whether it still describes the approved set is judged
            # from the evidence recomputed now: a pair withdrawn since, or a sheet redrawn, makes it old.
            stored = self._replayed(session, claimed.outcome)
            return SummaryOutcome(
                stored, True,
                _describes(stored, self._comparisons.sealed_evidence(session, comparison_request)),
            )

        self._links.lock_pair(
            session, source_version_uid=request.source_version_uid,
            target_version_uid=request.target_version_uid,
        )
        evidence = self._comparisons.sealed_evidence(session, comparison_request)
        if evidence is None:
            raise _conflict(CONFLICT_COMPARISON_NOT_AVAILABLE, AGGREGATE_TYPE)
        if evidence.seal is None or evidence.comparison_id is None:
            raise _conflict(CONFLICT_SUMMARY_EVIDENCE_NOT_SEALED, AGGREGATE_TYPE)
        try:
            summary_input = prepare_version_summary_input(
                version_pair=evidence.pair, raw_diffs=evidence.raw_diffs, raw_seal=evidence.seal,
            )
        except SummaryInputRefused:
            raise _conflict(CONFLICT_SUMMARY_INPUT_TOO_LARGE, AGGREGATE_TYPE) from None
        if not any(sheet.changes for sheet in summary_input.sheets):
            raise _conflict(CONFLICT_SUMMARY_INPUT_EMPTY, AGGREGATE_TYPE)

        prompt = build_request(summary_input)
        revision = evidence.link_revision
        existing = self._summaries.ready_for(
            session, comparison_id=evidence.comparison_id, link_revision=revision,
            input_sha256=summary_input.input_sha256, prompt_version=PROMPT_VERSION,
        )
        if existing is not None:
            commands.succeed(session, claimed.command_id, _summary_outcome(existing))
            return SummaryOutcome(existing, True, _describes(existing, evidence))

        cost = self._cost_gate()  # a fresh meter for this command: the ceiling is per command
        if not isinstance(cost, SummaryCostGate):
            raise TypeError("the cost gate must satisfy SummaryCostGate")
        cost.before_call()
        reply = self._model.complete(prompt)
        if not self._model.unmetered:
            # This wave builds no metered path: a reply whose cost cannot be verified is refused, as the
            # AR v3 worker refuses «a metered call without a verifiable cost amount».
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="comparison_summary",
                reason="cost_unverifiable",
            )
        basis, micros = cost.after_unmetered_call()
        try:
            statements, state, reason = parse_reply(reply.output_text, prompt.hunk_ids), STATE_READY, None
        except SummaryRejected as rejected:
            statements, state, reason = (), STATE_REJECTED, rejected.reason
        summary_id = str(AuditEventId.new())
        stored = self._summaries.append(session, StoredSummary(
            summary_id=summary_id,
            comparison_id=evidence.comparison_id,
            link_revision=revision,
            project_uid=request.project_uid,
            raw_evidence_seal_sha256=evidence.seal.seal_sha256,
            input_sha256=summary_input.input_sha256,
            request_sha256=prompt.request_sha256,
            prompt_version=PROMPT_VERSION,
            provider_mode=self._model.provider_mode,
            model_identity=self._model.model_identity,
            state=state,
            rejection_reason=reason,
            statements=statements,
            cost_basis=basis,
            cost_micros=micros,
            actor_user_uid=actor_uid,
            actor_label=actor_label,
            command_id=str(claimed.command_id),
            created_at=_EPOCH,
        ))
        record_summary_generated(
            session,
            event_id=summary_id,
            comparison_id=stored.comparison_id,
            link_revision=stored.link_revision,
            input_sha256=stored.input_sha256,
            raw_evidence_seal_sha256=stored.raw_evidence_seal_sha256,
            state=stored.state,
            actor_uid=actor_uid,
            correlation_id=correlation_id,
        )
        commands.succeed(session, claimed.command_id, _summary_outcome(stored))
        return SummaryOutcome(stored, False, _describes(stored, evidence))

    def _replayed(self, session: Session, outcome: object) -> StoredSummary:
        identity = _stored_outcome(outcome, "summary_id")
        found = None if identity is None else self._summaries.by_id(session, summary_id=identity)
        if found is None:
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_GENERATE)
        return found


_EPOCH: Final[datetime] = datetime(1970, 1, 1)


def _describes(stored: StoredSummary, evidence: SealedEvidence | None) -> bool:
    """Does ``stored`` describe the approved set as ``evidence`` (recomputed now) has it?

    The rule of the served read: the set is ``sealed`` (a seal exists), the revision is the stored
    one and the seal is the stored one. A refused comparison, an unsealed set, another revision or
    another seal is not current.
    """
    return (
        evidence is not None
        and evidence.seal is not None
        and evidence.comparison_id == stored.comparison_id
        and evidence.link_revision == stored.link_revision
        and evidence.seal.seal_sha256 == stored.raw_evidence_seal_sha256
    )


def _summary_outcome(summary: StoredSummary) -> dict[str, object]:
    return {
        "summary_id": summary.summary_id,
        "comparison_id": summary.comparison_id,
        "link_revision": summary.link_revision,
        "state": summary.state,
    }


__all__ = [
    "AGGREGATE_TYPE", "COMMAND_GENERATE", "CONFLICT_SUMMARY_EVIDENCE_NOT_SEALED",
    "CONFLICT_SUMMARY_INPUT_EMPTY", "CONFLICT_SUMMARY_INPUT_TOO_LARGE", "COST_BASES",
    "DEPENDENCY_SUMMARY_MODEL", "GenerateSummaryRequest", "LatestSummaryReader", "STATE_READY",
    "STATE_REJECTED", "SUMMARY_CONFLICT_REASONS", "SUMMARY_STATES", "StoredSummary",
    "SummaryCostGate", "SummaryOutcome", "SummaryService", "SummaryStore",
]
