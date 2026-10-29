"""The three work kinds of the series (`CMP-SERIES-01`; ADR-0025 decisions 4, 6, 7, 8, 23).

``series_pair`` -- one item is one **sheet pair** (decision 6: an item is one page or one pair, never a series). Its payload
is ``{"sheet_pair_id": "ctp_..."}``. The handler marks the pair ``computing``, asks the engine for the pair's result
(:func:`~auditmanager.comparison.engine.service.compare_sheet_pair`, which returns the cached result or computes it in the
ceilinged child and writes it, blob first and then the row), writes the pair ``done`` with its status and result, and lets the
series advance. **Every transaction that writes the pair starts with** ``WorkItem.require_current``: an attempt that lost its
lease writes nothing (decision 7). The same function proves the lease and looks for a cancel before the slow steps, as the
engine's own handler does.

``series_drive`` -- one polling item per series. It calls :meth:`~.advance.SeriesAdvancer.advance`, which marks a pair whose
item ended without a result as failed, finalises the transitions whose pairs are all in, and concludes the series; it then
yields until its next look, or ends when the series is no longer live. It is what makes a series that nothing else will
touch (a pair whose item the queue gave up on) end visibly.

``series_after_preparation`` -- one item per set of a batch that asked for «После подготовки сравнить все соседние версии»
(``compare_after_preparation``). It waits (a yield spends no attempt) until the document set's matrix is ``ready``, queueing
the profiles and the build it needs, and then starts the series on behalf of the person who declared the batch.

How a pair item ends
--------------------
* the pair is written ``done``: ``Completed``;
* a cancel or a lost lease at a checkpoint: the pair goes back to ``queued`` (if the lease still holds) and the item
  ``Yielded`` -- the queue turns that into ``cancelled`` for a requested cancel;
* the child never started, or a source could not be read: a retry (``Failed(..., retry=True)``) until the last attempt, when
  the pair is written ``failed`` and the item ``Failed`` without a retry;
* the pages are not the project's, the payload is not a pair, the result is one the contract refuses: the pair is written
  ``failed`` and the item ``Failed`` without a retry.

A pair left ``failed`` is not the end of the series: its transition is ``completed`` with the verdict ``incomplete`` and
``calculation_failed``, and «Досчитать» queues the pair again.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.engine.runner import ChildRunner, ChildStartError
from auditmanager.comparison.engine.service import PART_KINDS, PairOutcome, compare_sheet_pair
from auditmanager.comparison.engine.validate import ResultInvalid
from auditmanager.comparison.series.advance import Advance, SeriesAdvancer
from auditmanager.comparison.series.model import (
    COMPARED_STATUSES,
    PAIR_DONE,
    REASON_SPLIT_SHEET,
    SERIES_AFTER_PREPARATION_KIND,
    SERIES_DRIVE_KIND,
    SERIES_LIVE,
    SERIES_PAIR_KIND,
)
from auditmanager.comparison.series.planning import link_reasons
from auditmanager.comparison.series.repository import PairRow, SeriesRepository, SeriesRow
from auditmanager.comparison.series.service import ComparisonSeriesService
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonSeriesId, ComparisonSheetPairId, DocumentUid

__all__ = [
    "REASON_CHILD_START_FAILED",
    "REASON_FOLLOW_UP_PAYLOAD_INVALID",
    "REASON_PAIR_NOT_FOUND",
    "REASON_PAIR_PAYLOAD_INVALID",
    "REASON_RESULT_INVALID",
    "REASON_SOURCE_UNREADABLE",
    "SeriesAfterPreparationHandler",
    "SeriesDriveHandler",
    "SeriesPairHandler",
    "series_after_preparation_handler",
    "series_drive_handler",
    "series_pair_handler",
]

_LOG = logging.getLogger(__name__)

REASON_PAIR_PAYLOAD_INVALID: Final[str] = "series_pair_payload_invalid"
REASON_PAIR_NOT_FOUND: Final[str] = "series_pair_not_found"
REASON_CHILD_START_FAILED: Final[str] = "series_pair_child_start_failed"
REASON_SOURCE_UNREADABLE: Final[str] = "series_pair_source_unreadable"
REASON_RESULT_INVALID: Final[str] = "series_pair_result_invalid"
REASON_NO_RESULT: Final[str] = "series_pair_no_result"
REASON_FOLLOW_UP_PAYLOAD_INVALID: Final[str] = "series_follow_up_payload_invalid"
REASON_FOLLOW_UP_SERIES_ACTIVE: Final[str] = "comparison_series_active"
_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})
_SOURCE_FAULTS: Final[frozenset[ErrorCode]] = frozenset(
    {ErrorCode.ANALYSIS_INPUT_INVALID, ErrorCode.STORAGE_INTEGRITY_ERROR}
)
#: How soon a follow-up looks again at a matrix that is not ready.
FOLLOW_UP_WAIT_SECONDS: Final[float] = 15.0

CompareFunction = Callable[..., PairOutcome]


class _StopWork(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _checkpoint(item: WorkItem, dependencies: WorkDependencies) -> None:
    """Prove the lease, extend it, and stop on a cancel or a lease that is gone (the engine handler's checkpoint)."""
    if item.lease_lost.is_set():
        raise _StopWork("the lease is gone")
    if item.cancelled.is_set():
        raise _StopWork("a cancel was requested")
    sessions: sessionmaker[Session] = dependencies.session_factory
    with sessions() as session:
        try:
            item.check_current(session)
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                raise _StopWork("the lease is gone") from refusal
            raise
        holds = dependencies.work.heartbeat(session, item.authority)
        cancel = holds and dependencies.work.cancel_requested(session, item.work_id)
        session.commit()
    if not holds:
        item.lease_lost.set()
        raise _StopWork("the lease is gone")
    if cancel:
        item.cancelled.set()
        raise _StopWork("a cancel was requested")


def _pair_id_of(payload: Mapping[str, Any]) -> str:
    if set(payload) != {"sheet_pair_id"} or not isinstance(payload["sheet_pair_id"], str):
        raise ValueError("the payload of a series_pair item holds sheet_pair_id and nothing else")
    ComparisonSheetPairId(payload["sheet_pair_id"])  # IdentifierFormatError is a ValueError
    return str(payload["sheet_pair_id"])


def _part_of(pair: PairRow) -> str | None:
    kind = (pair.parts or {}).get("kind")
    return kind if kind in PART_KINDS else None


class SeriesPairHandler:
    """The one handler of kind ``series_pair`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = SERIES_PAIR_KIND

    def __init__(
        self, dependencies: WorkDependencies, *, runner: ChildRunner | None = None,
        compare: CompareFunction = compare_sheet_pair, advancer: SeriesAdvancer | None = None,
        repository: SeriesRepository | None = None,
    ) -> None:
        #: Read when an item runs, not when the factory is applied (the registry builds a handler to learn its kind).
        self._dependencies = dependencies
        self._runner = runner
        self._compare = compare
        self._repo = repository or SeriesRepository()
        self._advancer = advancer

    def _advance(self) -> SeriesAdvancer:
        if self._advancer is None:
            self._advancer = SeriesAdvancer(
                self._dependencies.session_factory, self._dependencies.blob_store, repository=self._repo
            )
        return self._advancer

    def run(self, item: WorkItem) -> Outcome:
        try:
            pair_id = _pair_id_of(item.payload)
        except ValueError:
            _LOG.error("comparison work %s: the series_pair payload is not valid", item.work_id)
            return Failed(REASON_PAIR_PAYLOAD_INVALID)
        factory = self._dependencies.session_factory
        started = False
        try:
            _checkpoint(item, self._dependencies)
            begun = self._begin(item, pair_id)
            if isinstance(begun, Outcome):
                return begun
            pair, _series = begun
            started = True
            outcome = self._compare(
                factory, self._dependencies.blob_store, project_uid=item.project_uid,
                page_a_profile_id=pair.page_a_profile_id, page_b_profile_id=pair.page_b_profile_id,
                link_reasons=link_reasons(pair.confidence, pair.flags), part=_part_of(pair), runner=self._runner,
                before_publish=lambda: _checkpoint(item, self._dependencies), fence=item.require_current,
            )
            if outcome.status not in COMPARED_STATUSES or outcome.result_id is None:
                return self._give_up(item, pair_id, REASON_NO_RESULT)
            self._finish(item, pair, outcome)
        except _StopWork as stop:
            _LOG.info("comparison work %s (series_pair, attempt %d): stopped: %s", item.work_id, item.attempt_no, stop.reason)
            if started:
                self._put_back(item, pair_id)
            return Yielded()
        except ChildStartError:
            _LOG.error("comparison work %s (series_pair): the pair child never started", item.work_id)
            return self._retry_or_give_up(item, pair_id, REASON_CHILD_START_FAILED)
        except ResultInvalid:
            _LOG.error("comparison work %s (series_pair): the engine produced a result the contract refuses", item.work_id)
            return self._give_up(item, pair_id, REASON_RESULT_INVALID)
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            if refusal.code is ErrorCode.NOT_FOUND:
                return self._give_up(item, pair_id, REASON_PAIR_NOT_FOUND)
            if refusal.code in _SOURCE_FAULTS:
                return self._retry_or_give_up(item, pair_id, REASON_SOURCE_UNREADABLE)
            raise
        return self._advance_after(item, pair_id)

    # -- the steps --------------------------------------------------------------------------------------------------

    def _begin(self, item: WorkItem, pair_id: str) -> "tuple[PairRow, SeriesRow] | Outcome":
        """Fenced: the pair is ``computing`` and the series and its transition are ``running``; or why nothing is done."""
        with session_scope(self._dependencies.session_factory) as session:
            item.require_current(session)
            pair = self._repo.get_pair(session, pair_id)
            if pair is None:
                return Failed(REASON_PAIR_NOT_FOUND)
            transition = self._repo.get_transition(session, pair.transition_id)
            series = None if transition is None else self._repo.get_series(session, transition.series_id)
            if transition is None or series is None or series.project_uid != item.project_uid:
                return Failed(REASON_PAIR_NOT_FOUND)
            if pair.state == PAIR_DONE:
                return Completed()
            if series.state not in SERIES_LIVE or pair.page_a_profile_id is None or pair.page_b_profile_id is None:
                return Completed()  # a cancelled or concluded series, or a pair that is not the engine's
            self._repo.set_series_state(session, series.series_id, from_states=["queued"], to_state="running")
            self._repo.run_transition(session, transition.transition_id)
            self._repo.mark_computing(session, pair_id)
            return pair, series

    def _finish(self, item: WorkItem, pair: PairRow, outcome: PairOutcome) -> None:
        """Fenced: write the pair ``done`` with its status and its result. A split sheet is never better than a review."""
        status, parts = outcome.status, pair.parts
        if parts is not None and parts.get("kind") == "split":
            status = "needs_review"
            parts = {**parts, "series_reasons": sorted({*parts.get("series_reasons", ()), REASON_SPLIT_SHEET})}
        with session_scope(self._dependencies.session_factory) as session:
            item.require_current(session)
            self._repo.finish_pair(session, pair.pair_id, status=status, result_id=outcome.result_id, parts=parts)

    def _advance_after(self, item: WorkItem, pair_id: str) -> Outcome:
        with session_scope(self._dependencies.session_factory) as session:
            pair = self._repo.get_pair(session, pair_id)
            transition = None if pair is None else self._repo.get_transition(session, pair.transition_id)
        if transition is not None:
            try:
                self._advance().advance(transition.series_id, fence=item.require_current)
            except DomainError as refusal:
                if refusal.code not in _LEASE_GONE:
                    raise
                item.lease_lost.set()  # the pair is written; the drive finalises
        return Completed()

    def _put_back(self, item: WorkItem, pair_id: str) -> None:
        """A cancel or a stop at a checkpoint: the pair waits again (if this attempt still holds the item)."""
        try:
            with session_scope(self._dependencies.session_factory) as session:
                item.require_current(session)
                self._repo.requeue_pair(session, pair_id)
        except DomainError as refusal:
            if refusal.code not in _LEASE_GONE:
                raise

    def _retry_or_give_up(self, item: WorkItem, pair_id: str, reason: str) -> Outcome:
        if item.attempt_no < item.max_attempts:
            return Failed(reason, retry=True)
        return self._give_up(item, pair_id, reason)

    def _give_up(self, item: WorkItem, pair_id: str, reason: str) -> Outcome:
        """Fenced: the pair is ``failed`` with the reason and the item ends without a retry."""
        try:
            with session_scope(self._dependencies.session_factory) as session:
                item.require_current(session)
                self._repo.fail_pair(session, pair_id, reason)
        except DomainError as refusal:
            if refusal.code not in _LEASE_GONE:
                raise
            item.lease_lost.set()
            return Yielded()
        self._advance_after(item, pair_id)
        return Failed(reason)


class SeriesDriveHandler:
    """The one handler of kind ``series_drive``: payload ``{"series_id": "cser_..."}``."""

    kind: str = SERIES_DRIVE_KIND

    def __init__(self, dependencies: WorkDependencies, *, advancer: SeriesAdvancer | None = None) -> None:
        self._dependencies = dependencies
        self._advancer = advancer

    def run(self, item: WorkItem) -> Outcome:
        payload = item.payload
        try:
            if set(payload) != {"series_id"} or not isinstance(payload["series_id"], str):
                raise ValueError("series_id and nothing else")
            ComparisonSeriesId(payload["series_id"])
        except ValueError:
            return Failed(REASON_PAIR_PAYLOAD_INVALID)
        advancer = self._advancer or SeriesAdvancer(self._dependencies.session_factory, self._dependencies.blob_store)
        try:
            if item.lease_lost.is_set() or item.cancelled.is_set():
                return Yielded()
            step: Advance = advancer.advance(str(payload["series_id"]), fence=item.require_current)
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            raise
        if not step.live:
            return Completed()
        return Yielded(delay_seconds=step.delay_seconds)


class SeriesAfterPreparationHandler:
    """The one handler of kind ``series_after_preparation``: payload ``{"document_uid", "set_id", "actor_label"}``."""

    kind: str = SERIES_AFTER_PREPARATION_KIND

    def __init__(self, dependencies: WorkDependencies, *, service: ComparisonSeriesService | None = None) -> None:
        self._dependencies = dependencies
        self._service = service

    def run(self, item: WorkItem) -> Outcome:
        payload = item.payload
        try:
            if set(payload) != {"document_uid", "set_id", "actor_label"} or item.created_by_user_uid is None:
                raise ValueError("document_uid, set_id and actor_label")
            document_uid = str(DocumentUid(payload["document_uid"]))
            set_id, label = str(payload["set_id"]), str(payload["actor_label"])
            if not set_id or len(set_id) > 64:
                raise ValueError("set_id")
        except (ValueError, TypeError):
            return Failed(REASON_FOLLOW_UP_PAYLOAD_INVALID)
        service = self._service or ComparisonSeriesService(
            session_factory=self._dependencies.session_factory, blob_store=self._dependencies.blob_store
        )
        try:
            if item.lease_lost.is_set() or item.cancelled.is_set():
                return Yielded()
            state, detail = service.follow_up(
                project_uid=item.project_uid, document_uid=document_uid, user_uid=item.created_by_user_uid,
                actor_label=label, idempotency_key=f"auto-{set_id}", fence=item.require_current,
            )
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            if refusal.code is ErrorCode.CONFLICT and refusal.detail_fields.get("conflict_reason") in (
                REASON_FOLLOW_UP_SERIES_ACTIVE, "comparison_matrix_stale",
            ):
                if refusal.detail_fields.get("conflict_reason") == REASON_FOLLOW_UP_SERIES_ACTIVE:
                    return Failed(REASON_FOLLOW_UP_SERIES_ACTIVE)
                return Yielded(delay_seconds=FOLLOW_UP_WAIT_SECONDS)  # the matrix moved between the look and the start
            raise
        if state == "started":
            return Completed()
        if state == "failed":
            return Failed(str(detail or "matrix_build_failed"))
        return Yielded(delay_seconds=FOLLOW_UP_WAIT_SECONDS)


def series_pair_handler(dependencies: WorkDependencies) -> SeriesPairHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``)."""
    return SeriesPairHandler(dependencies)


def series_drive_handler(dependencies: WorkDependencies) -> SeriesDriveHandler:
    return SeriesDriveHandler(dependencies)


def series_after_preparation_handler(dependencies: WorkDependencies) -> SeriesAfterPreparationHandler:
    return SeriesAfterPreparationHandler(dependencies)
