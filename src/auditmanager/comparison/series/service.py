"""The use cases of the series: start it, read it, steer it, read its sheet pairs (`CMP-SERIES-01`).

One class holds the nine operations the contract seals; it takes plain values and answers contract-shaped dictionaries
(:mod:`.views`) that the adapter in the composition root validates with the generated models.

**Reads** start nothing and change nothing: a series is read from its rows; whether it is stale is *derived* on every read
by comparing the digest of the inputs it was started on with the digest of the inputs now (:mod:`.inputs`).

**Writes** are an expert's act, checked in the transaction that acts (ADR-0025 decision 16), keyed (a repeat of the same key
and payload replays the recorded outcome, a repeat with another payload is ``idempotency_key_reuse``) and append-only apart
from the state edges the database allows.

**Start** (``startComparisonSeries``): the document set's matrix must be ``ready`` (a build that matches the order and the
page profiles as they are), no series of the set may be live, the caller's ``base_order_revision_no`` must be the latest
order revision; then one transaction writes the series (bound to the matrix revision ``{matrix_id, edit_no}``, the order
revision and the digest of those inputs), every adjacent transition, every sheet pair of the matrix, and the work: one
``series_pair`` item for each pair that needs the engine, one ``series_drive`` item. A pair of versions that are not
neighbours is never written (:func:`.planning.assert_adjacent`). The advisory lock the matrix's edit chain takes is held
during the read of the pairs and the writes, so an edit cannot slip between them.

**Steering**: pause, resume and cancel update the series' work items first and the series then (the lock order of
:mod:`.repository`); «Досчитать» (finish) queues, in the same series, the transitions that have no complete result and the
pairs that failed or were left unfinished, and reuses what is done; «Заново» is a start with ``restart`` and names the
series it replaced.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.engine.limits import ALGO_VERSION as ENGINE_ALGO_VERSION
from auditmanager.comparison.matrix.inputs import (
    profile_digest,
    resolve_order,
    stale_reasons as matrix_stale_reasons,
    versions_missing_profiles,
)
from auditmanager.comparison.matrix.pairs import AdjacentSheetPairs
from auditmanager.comparison.matrix.repository import MatrixRepository
from auditmanager.comparison.matrix.service import (
    MATRIX_BUILD_KIND,
    ComparisonMatrixService,
    matrix_build_dedupe_key,
    read_adjacent_sheet_pairs,
    require_expert,
)
from auditmanager.comparison.modules import MODULE_VERSIONS
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.profile_queue.enqueue import enqueue_version_page_profiles
from auditmanager.comparison.series import views
from auditmanager.comparison.series.inputs import CurrentInputs, SeriesInputs, chain_of, input_digest, stale_reasons
from auditmanager.comparison.series.model import (
    COMMAND_CANCEL,
    COMMAND_FINISH,
    COMMAND_PAUSE,
    COMMAND_RESUME,
    COMMAND_START,
    SERIES_DRIVE_KIND,
    SERIES_LIVE,
    SERIES_PAIR_KIND,
    SERIES_TERMINAL,
    STATE_CANCELLED,
    STATE_COMPLETED,
    STATE_PAUSED,
    STATE_QUEUED,
    STATE_RUNNING,
    PartRecord,
    SeriesPlan,
)
from auditmanager.comparison.series.planning import plan_series
from auditmanager.comparison.series.repository import SeriesRepository, SeriesRow, TransitionRow, pair_dedupe_key
from auditmanager.comparison.series.verdict import PairFacts, summarize
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonSeriesId, DocumentUid, IdempotencyKey, ProjectUid

__all__ = [
    "ComparisonSeriesService",
    "PairPage",
    "SeriesPage",
    "drive_dedupe_key",
]

_LOG = logging.getLogger(__name__)

PAGE_MAX: Final[int] = 200
#: The first look of a new series' drive is after the first pairs have had time to start.
DRIVE_FIRST_DELAY_SECONDS: Final[float] = 5.0
_TRANSITION_PRIORITY_STEP: Final[int] = 1
_FINISHABLE_TRANSITION_STATES: Final[tuple[str, ...]] = ("queued", "running", "failed", "cancelled")

Fence = Callable[[Session], None]


def drive_dedupe_key(series_id: str) -> str:
    """One live polling item per series."""
    return f"{SERIES_DRIVE_KIND}:{series_id}"


@dataclass(frozen=True, slots=True)
class SeriesPage:
    items: list[dict[str, Any]]
    next_after: tuple[datetime, str] | None


@dataclass(frozen=True, slots=True)
class PairPage:
    items: list[dict[str, Any]]
    next_after: int | None


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


def _not_found(what: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=what)


def _parts_record(part: PartRecord | None) -> dict[str, Any] | None:
    """The ``parts`` column a planned pair is written with: the contract's three members and the series' own working ones."""
    if part is None:
        return None
    whole = part.role == "whole"
    return {
        "kind": part.kind, "role": part.role, "source_profile_id": part.source_profile_id,
        "text_percent": part.text_percent,
        # a typical sheet repeated per floor is compared whole; a split sheet starts from the matrix's text coverage
        # until the post-phase has the engine's measure (``coverage_reliable``)
        "covered_percent": 100.0 if whole else part.text_percent, "coverage_reliable": whole,
        "parts": list(part.parts), "series_reasons": [],
    }


class ComparisonSeriesService:
    __slots__ = ("_factory", "_blobs", "_repo", "_matrix", "_documents", "_commands", "_work", "_read_pairs")

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        blob_store: Any = None,
        repository: SeriesRepository | None = None,
        work: ComparisonWorkRepository | None = None,
        read_pairs: Callable[..., AdjacentSheetPairs] | None = None,
    ) -> None:
        self._factory = session_factory
        self._blobs = blob_store
        self._repo = repository or SeriesRepository()
        self._matrix = MatrixRepository()
        self._documents = DocumentRepository()
        self._commands = CommandRepository()
        self._work = work or ComparisonWorkRepository()
        self._read_pairs = read_pairs or read_adjacent_sheet_pairs

    # -- shared reads -----------------------------------------------------------------------------------------

    def _require_document(self, session: Session, project_uid: str, document_uid: str) -> None:
        """The project exists and owns the document; either missing is ``not_found`` naming what was addressed."""
        self._documents.get_project(session, ProjectUid.parse(project_uid))
        if str(self._documents.require_document(session, DocumentUid.parse(document_uid))) != project_uid:
            raise _not_found("Document")

    def _order(self, session: Session, document_uid: str) -> tuple[list[str], dict[str, int], Any]:
        """``(the versions in the order a build would walk them, page counts, the latest order revision)``."""
        versions = sorted(
            self._documents.list_versions(session, DocumentUid.parse(document_uid)), key=lambda v: v.version_ordinal
        )
        own = [str(v.version_uid) for v in versions]
        latest = self._matrix.latest_order(session, document_uid)
        order = resolve_order(None if latest is None else latest.version_uids, own)
        return order, {str(v.version_uid): int(v.page_count) for v in versions}, latest

    # -- staleness -----------------------------------------------------------------------------------------------

    def _stale(self, session: Session, row: SeriesRow, transitions: Sequence[TransitionRow]) -> list[str]:
        """Why the series no longer matches the inputs of the document set (empty: it does)."""
        chain = chain_of([(t.source_version_uid, t.target_version_uid) for t in transitions])
        bound = self._repo.bound_build(session, row.matrix_id)
        order, _counts, _latest = self._order(session, row.document_uid)
        facts = self._matrix.profile_facts(session, list(chain), PAGE_PROFILE_ALGO_VERSION)
        current = CurrentInputs(
            order=tuple(order), matrix_id=self._repo.latest_build_id(session, row.document_uid),
            edit_no=self._matrix.max_edit_no(session, row.document_uid), profile_signature=profile_digest(facts),
            engine_algo=ENGINE_ALGO_VERSION,
        )
        bound_inputs = SeriesInputs(
            chain=chain, matrix_id=row.matrix_id, edit_no=row.edit_no,
            profile_signature="" if bound is None else bound[0], engine_algo=ENGINE_ALGO_VERSION,
        )
        return stale_reasons(row.input_sha256, bound_inputs, current)

    # -- the views --------------------------------------------------------------------------------------------------

    def _transition_views(self, session: Session, transitions: Sequence[TransitionRow]) -> list[dict[str, Any]]:
        ids = [t.transition_id for t in transitions]
        progress = self._repo.progress(session, ids)
        open_ids = [t.transition_id for t in transitions if t.state != STATE_COMPLETED]
        by_transition: dict[str, list[PairFacts]] = {}
        for fact in self._repo.facts(session, open_ids):
            by_transition.setdefault(fact.transition_id, []).append(
                PairFacts(fact.state, fact.status, fact.both_pages, fact.ai_dependent, fact.style_only)
            )
        out: list[dict[str, Any]] = []
        for t in transitions:
            counts = progress.get(t.transition_id, {"total": 0, "done": 0})
            summary = t.summary if t.state == STATE_COMPLETED and t.summary is not None else summarize(
                by_transition.get(t.transition_id, [])
            )
            out.append(views.transition_dict(t, items_total=counts["total"], items_done=counts["done"], summary=summary))
        return out

    def _series_view(self, session: Session, series_id: str, *, with_transitions: bool) -> dict[str, Any]:
        row = self._repo.get_series(session, series_id)
        if row is None:
            raise _not_found("ComparisonSeries")
        return self._view_of(session, row, with_transitions=with_transitions)

    def _view_of(self, session: Session, row: SeriesRow, *, with_transitions: bool) -> dict[str, Any]:
        transitions = self._repo.transitions(session, row.series_id)
        return views.series_dict(
            row,
            transitions_total=len(transitions),
            transitions_done=sum(1 for t in transitions if t.state == STATE_COMPLETED),
            stale_reasons=self._stale(session, row, transitions),
            transitions=self._transition_views(session, transitions) if with_transitions else None,
        )

    def get_series(self, *, series_id: str) -> dict[str, Any]:
        with session_scope(self._factory) as session:
            return self._series_view(session, series_id, with_transitions=True)

    def list_series(
        self, *, project_uid: str, document_uid: str, after: tuple[datetime, str] | None, limit: int
    ) -> SeriesPage:
        bounded = max(1, min(limit, PAGE_MAX))
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            rows = self._repo.list_series(session, document_uid, after=after, limit=bounded + 1)
            page = rows[:bounded]
            items = [self._view_of(session, row, with_transitions=False) for row in page]
            more = len(rows) > bounded
            return SeriesPage(items=items, next_after=(page[-1].created_at, page[-1].series_id) if more and page else None)

    def list_sheet_pairs(
        self, *, transition_id: str, status: str | None, only_changes: bool, after_no: int | None, limit: int
    ) -> PairPage:
        bounded = max(1, min(limit, PAGE_MAX))
        with session_scope(self._factory) as session:
            if self._repo.transition_owner(session, transition_id) is None:
                raise _not_found("ComparisonTransition")
            rows = self._repo.pair_page(
                session, transition_id, after=after_no, status=status, only_changes=only_changes, limit=bounded + 1
            )
            page = rows[:bounded]
            return PairPage(
                items=[views.pair_dict(r, with_evidence=False) for r in page],
                next_after=int(page[-1]["pair_no"]) if len(rows) > bounded and page else None,
            )

    def get_sheet_pair(self, *, sheet_pair_id: str) -> dict[str, Any]:
        with session_scope(self._factory) as session:
            row = self._repo.pair_view(session, sheet_pair_id)
            if row is None:
                raise _not_found("ComparisonSheetPair")
            return views.pair_dict(row, with_evidence=True)

    # -- start --------------------------------------------------------------------------------------------------------

    def start_series(
        self, *, project_uid: str, document_uid: str, restart: bool, base_order_revision_no: int | None, user_uid: str,
        actor_label: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        """«Запустить» / «Заново»: see the module."""
        require_expert(actor_roles)
        return self._start(
            project_uid=project_uid, document_uid=document_uid, restart=restart,
            base_order_revision_no=base_order_revision_no, user_uid=user_uid, actor_label=actor_label,
            idempotency_key=idempotency_key, fence=None,
        )

    def start_after_preparation(
        self, *, project_uid: str, document_uid: str, user_uid: str, actor_label: str, idempotency_key: str, fence: Fence
    ) -> str:
        """The series a batch asked for with ``compare_after_preparation`` (the worker's, fenced): the act is the upload
        creator's, who set the flag when the batch was declared. Answers the new series' identity."""
        view = self._start(
            project_uid=project_uid, document_uid=document_uid, restart=False, base_order_revision_no=None,
            user_uid=user_uid, actor_label=actor_label, idempotency_key=idempotency_key, fence=fence,
        )
        return str(view["series_id"])

    def _start(
        self, *, project_uid: str, document_uid: str, restart: bool, base_order_revision_no: int | None, user_uid: str,
        actor_label: str, idempotency_key: str, fence: Fence | None,
    ) -> dict[str, Any]:
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint({
            "command": "start_comparison_series.v1", "project_uid": project_uid, "document_uid": document_uid,
            "restart": bool(restart), "base_order_revision_no": base_order_revision_no,
        })
        label = " ".join(actor_label.split())[:128] or "эксперт"
        with session_scope(self._factory) as session:
            if fence is not None:
                fence(session)
            self._require_document(session, project_uid, document_uid)
            claim = self._commands.begin(
                session, command_type=COMMAND_START, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                return self._series_view(session, str(claim.outcome["series_id"]), with_transitions=True)
            live = self._repo.live_series(session, document_uid)
            if live is not None:
                raise _conflict("comparison_series_active")
            order, _counts, latest = self._order(session, document_uid)
            current_revision = 0 if latest is None else latest.revision_no
            if base_order_revision_no is not None and base_order_revision_no != current_revision:
                raise _conflict("comparison_version_order_stale")
            # The matrix's edit chain takes this lock: no edit can land between the read of the pairs and the writes.
            self._matrix.lock_edits(session, document_uid)
            build = self._matrix.latest_build(session, document_uid)
            facts = self._matrix.profile_facts(session, order, PAGE_PROFILE_ALGO_VERSION)
            if build is None or matrix_stale_reasons(
                build, order=order, order_id=None if latest is None else latest.order_id, digest=profile_digest(facts)
            ):
                raise _conflict("comparison_matrix_stale")
            if len(order) < 2:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="document_uid", constraint="comparison_versions_few")
            pairs = self._read_pairs(self._factory, project_uid=project_uid, document_uid=document_uid)
            if pairs.matrix_id != build.matrix_id or pairs.edit_no != self._matrix.max_edit_no(session, document_uid):
                raise _conflict("comparison_matrix_stale")
            plan = plan_series(pairs)
            digest = input_digest(SeriesInputs(
                chain=plan.order, matrix_id=plan.matrix_id, edit_no=plan.edit_no,
                profile_signature=build.profile_signature, engine_algo=ENGINE_ALGO_VERSION,
            ))
            replaced = self._repo.latest_series(session, document_uid) if restart else None
            series_id = str(ComparisonSeriesId.new())
            self._repo.insert_series(
                session, series_id=series_id, project_uid=project_uid, document_uid=document_uid, order_id=plan.order_id,
                matrix_id=plan.matrix_id, edit_no=plan.edit_no, digest=digest,
                restarted_from=None if replaced is None else replaced.series_id, actor_user_uid=user_uid,
                actor_label=label, command_id=str(claim.command_id),
            )
            self._write_plan(session, plan, series_id=series_id, project_uid=project_uid, user_uid=user_uid)
            self._commands.succeed(session, claim.command_id, {"series_id": series_id})
            return self._series_view(session, series_id, with_transitions=True)

    def _write_plan(self, session: Session, plan: SeriesPlan, *, series_id: str, project_uid: str, user_uid: str) -> None:
        for transition in plan.transitions:
            transition_id = self._repo.insert_transition(
                session, series_id=series_id, number=transition.transition_no,
                source=transition.source_version_uid, target=transition.target_version_uid,
            )
            for pair in transition.pairs:
                pair_id = self._repo.insert_pair(session, transition_id, pair, parts=_parts_record(pair.part))
                if pair.compare:
                    self._enqueue_pair(
                        session, project_uid=project_uid, series_id=series_id, pair_id=pair_id,
                        transition_no=transition.transition_no, user_uid=user_uid,
                    )
        self._enqueue_drive(session, project_uid=project_uid, series_id=series_id, user_uid=user_uid)

    def _enqueue_pair(
        self, session: Session, *, project_uid: str, series_id: str, pair_id: str, transition_no: int, user_uid: str
    ) -> None:
        # Earlier transitions first: the queue claims the higher priority first.
        priority = max(-100, -(transition_no - 1) * _TRANSITION_PRIORITY_STEP)
        self._work.enqueue(
            session, project_uid=project_uid, module=MODULE_VERSIONS, kind=SERIES_PAIR_KIND,
            payload={"sheet_pair_id": pair_id}, dedupe_key=pair_dedupe_key(pair_id), priority=priority,
            comparison_series_id=series_id, created_by_user_uid=user_uid,
        )

    def _enqueue_drive(self, session: Session, *, project_uid: str, series_id: str, user_uid: str) -> None:
        self._work.enqueue(
            session, project_uid=project_uid, module=MODULE_VERSIONS, kind=SERIES_DRIVE_KIND,
            payload={"series_id": series_id}, dedupe_key=drive_dedupe_key(series_id),
            delay_seconds=DRIVE_FIRST_DELAY_SECONDS, comparison_series_id=series_id, created_by_user_uid=user_uid,
        )

    # -- steering -----------------------------------------------------------------------------------------------------

    def _steer(
        self, *, series_id: str, command_type: str, actor_roles: frozenset[str], idempotency_key: str,
        apply: Callable[[Session, SeriesRow], None],
    ) -> dict[str, Any]:
        require_expert(actor_roles)
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint({"command": f"{command_type}.v1", "series_id": series_id})
        with session_scope(self._factory) as session:
            row = self._repo.get_series(session, series_id)
            if row is None:
                raise _not_found("ComparisonSeries")
            claim = self._commands.begin(session, command_type=command_type, idempotency_key=key, fingerprint=fingerprint)
            if isinstance(claim, CommandReplay):
                return self._series_view(session, series_id, with_transitions=True)
            apply(session, row)
            self._commands.succeed(session, claim.command_id, {"series_id": series_id})
            return self._series_view(session, series_id, with_transitions=True)

    def pause_series(
        self, *, series_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> dict[str, Any]:
        """«Пауза»: the items that wait are paused, the pair in flight finishes (an item is one pair)."""

        def apply(session: Session, row: SeriesRow) -> None:
            if row.state not in (STATE_QUEUED, STATE_RUNNING):
                raise _conflict("comparison_series_state")
            self._work.pause_for_series(session, row.series_id)
            if not self._repo.set_series_state(
                session, row.series_id, from_states=[STATE_QUEUED, STATE_RUNNING], to_state=STATE_PAUSED
            ):
                raise _conflict("comparison_series_state")

        return self._steer(
            series_id=series_id, command_type=COMMAND_PAUSE, actor_roles=actor_roles, idempotency_key=idempotency_key,
            apply=apply,
        )

    def resume_series(
        self, *, series_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> dict[str, Any]:
        def apply(session: Session, row: SeriesRow) -> None:
            if row.state != STATE_PAUSED:
                raise _conflict("comparison_series_state")
            self._work.resume_for_series(session, row.series_id)
            if not self._repo.set_series_state(
                session, row.series_id, from_states=[STATE_PAUSED], to_state=STATE_RUNNING
            ):
                raise _conflict("comparison_series_state")

        return self._steer(
            series_id=series_id, command_type=COMMAND_RESUME, actor_roles=actor_roles, idempotency_key=idempotency_key,
            apply=apply,
        )

    def cancel_series(
        self, *, series_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> dict[str, Any]:
        """The items at rest end, the ones in flight are asked to stop; the transitions that are not complete are
        ``cancelled``. What is done stays done (a «Досчитать» takes it up)."""

        def apply(session: Session, row: SeriesRow) -> None:
            if row.state not in SERIES_LIVE:
                raise _conflict("comparison_series_state")
            self._work.cancel_for_series(session, row.series_id)
            if not self._repo.set_series_state(session, row.series_id, from_states=SERIES_LIVE, to_state=STATE_CANCELLED):
                raise _conflict("comparison_series_state")
            self._repo.cancel_transitions(session, row.series_id)

        return self._steer(
            series_id=series_id, command_type=COMMAND_CANCEL, actor_roles=actor_roles, idempotency_key=idempotency_key,
            apply=apply,
        )

    def finish_series(
        self, *, series_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> dict[str, Any]:
        """«Досчитать»: see the module."""

        def apply(session: Session, row: SeriesRow) -> None:
            if row.state not in SERIES_TERMINAL:
                raise _conflict("comparison_series_state")
            if any(n for state, n in self._work.counts(session, series_id=row.series_id).items()
                   if state not in ("succeeded", "failed", "cancelled")):
                raise _conflict("comparison_series_state")  # an item is still winding down
            transitions = self._repo.transitions(session, row.series_id)
            progress = self._repo.progress(session, [t.transition_id for t in transitions])
            unfinished = [
                t for t in transitions
                if t.state in _FINISHABLE_TRANSITION_STATES
                or (t.state == STATE_COMPLETED and progress.get(t.transition_id, {}).get("failed", 0))
            ]
            if not unfinished:
                raise _conflict("comparison_series_state")
            if not self._repo.set_series_state(session, row.series_id, from_states=SERIES_TERMINAL, to_state=STATE_QUEUED):
                raise _conflict("comparison_series_state")
            for t in unfinished:
                if t.state != STATE_QUEUED:
                    self._repo.set_transition_state(session, t.transition_id, from_states=[t.state], to_state=STATE_QUEUED)
            self._repo.requeue_unfinished(session, [t.transition_id for t in unfinished])
            for pair_id, transition_no, _pair_no in self._repo.queued_pairs(session, row.series_id):
                self._enqueue_pair(
                    session, project_uid=row.project_uid, series_id=row.series_id, pair_id=pair_id,
                    transition_no=transition_no, user_uid=user_uid,
                )
            self._enqueue_drive(session, project_uid=row.project_uid, series_id=row.series_id, user_uid=user_uid)

        return self._steer(
            series_id=series_id, command_type=COMMAND_FINISH, actor_roles=actor_roles, idempotency_key=idempotency_key,
            apply=apply,
        )

    # -- the preparation a batch asked for -----------------------------------------------------------------------------------

    def follow_up(
        self, *, project_uid: str, document_uid: str, user_uid: str, actor_label: str, idempotency_key: str, fence: Fence
    ) -> tuple[str, str | None]:
        """One look of the item that waits for a prepared set (``series_after_preparation``): ``("started", series)``,
        ``("waiting", None)`` (the matrix is not ready; what it needs is queued) or ``("failed", reason)``."""
        matrix = ComparisonMatrixService(session_factory=self._factory, blob_store=self._blobs)
        state = matrix.get_matrix(project_uid=project_uid, document_uid=document_uid)
        if state["state"] == "ready":
            series = self.start_after_preparation(
                project_uid=project_uid, document_uid=document_uid, user_uid=user_uid, actor_label=actor_label,
                idempotency_key=idempotency_key, fence=fence,
            )
            return "started", series
        if state["state"] == "failed":
            return "failed", str(state.get("failure_reason") or "matrix_build_failed")[:128]
        if state["state"] in ("absent", "stale"):
            self._queue_preparation(project_uid=project_uid, document_uid=document_uid, user_uid=user_uid, fence=fence)
        return "waiting", None

    def _queue_preparation(self, *, project_uid: str, document_uid: str, user_uid: str, fence: Fence) -> None:
        """What ``prepareComparisonMatrix`` queues, without the command: the profiles that are missing or failed, then
        the build (every item is deduplicated, so a repeat queues nothing twice)."""
        with session_scope(self._factory) as session:
            fence(session)
            order, counts, _latest = self._order(session, document_uid)
            facts = self._matrix.profile_facts(session, order, PAGE_PROFILE_ALGO_VERSION)
            missing, failed = versions_missing_profiles(facts, order, counts)
            for version in order:
                if version in missing or version in failed:
                    enqueue_version_page_profiles(
                        session, project_uid=project_uid, version_uid=version, created_by_user_uid=user_uid,
                        retry_failed=version in failed,
                    )
            self._work.enqueue(
                session, project_uid=project_uid, module=MODULE_VERSIONS, kind=MATRIX_BUILD_KIND,
                payload={"document_uid": document_uid}, dedupe_key=matrix_build_dedupe_key(document_uid),
                created_by_user_uid=user_uid,
            )

