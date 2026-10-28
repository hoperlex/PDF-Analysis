"""The handler of the ``pair_result`` work kind (`CMP-ENGINE-01`, ADR-0025 decisions 4, 6, 7, 8, wave brief section 4 item 4).

One item is one **pair** (ADR-0025 decision 6: an item is one page or one pair, never a series). Its payload is
``{"page_a": "cpr_...", "page_b": "cpr_...", "reasons": [...], "part": "split" | "floors" | null}``. The handler calls
:func:`~auditmanager.comparison.engine.service.compare_sheet_pair` for the item's project, which returns the cached
result or computes it in the ceilinged child and writes it (blob first, then the row), and then ends the item.

What the queue is for here. The child runs up to 600 s and the item's own heartbeat thread keeps the lease while it
does; the handler adds the two proofs a long step needs: **before the blob is published** the lease is proved and
extended and a cancel is looked for (a stop there is a ``Yielded``, which the queue turns into ``cancelled`` for a
requested cancel and drops for a lease that is gone), and **in the transaction that inserts the row** the item is locked
(``WorkItem.require_current``), so an attempt that lost its lease writes nothing.

How an item ends
----------------
* the result exists (written now, or found): ``Completed``. A pair that could not be compared is a stored
  ``needs_review`` result, not a failed item;
* a child that never started is the server's fault: ``Failed(..., retry=True)``;
* pages that do not exist or are not the project's: ``Failed`` without a retry; a source that cannot be read: with one;
* a payload of another shape, or a result the contract refuses (a defect of the engine): ``Failed`` without a retry.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.engine.limits import PAIR_WORK_KIND
from auditmanager.comparison.engine.runner import ChildRunner, ChildStartError
from auditmanager.comparison.engine.service import PART_KINDS, PairOutcome, compare_sheet_pair
from auditmanager.comparison.engine.validate import ResultInvalid
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonPageProfileId

__all__ = [
    "PAIR_RESULT_KIND",
    "PAYLOAD_KEYS",
    "PairResultHandler",
    "REASON_CHILD_START_FAILED",
    "REASON_PAGES_NOT_FOUND",
    "REASON_PAYLOAD_INVALID",
    "REASON_RESULT_INVALID",
    "REASON_SOURCE_UNREADABLE",
    "pair_result_handler",
    "pair_result_payload",
    "read_payload",
]

_LOG = logging.getLogger(__name__)

PAIR_RESULT_KIND: Final[str] = PAIR_WORK_KIND
PAYLOAD_KEYS: Final[frozenset[str]] = frozenset({"page_a", "page_b", "reasons", "part"})
REASON_PAYLOAD_INVALID: Final[str] = "pair_result_payload_invalid"
REASON_PAGES_NOT_FOUND: Final[str] = "pair_result_pages_not_found"
REASON_SOURCE_UNREADABLE: Final[str] = "pair_result_source_unreadable"
REASON_CHILD_START_FAILED: Final[str] = "pair_result_child_start_failed"
REASON_RESULT_INVALID: Final[str] = "pair_result_invalid"
_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})
_SOURCE_FAULTS: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.ANALYSIS_INPUT_INVALID, ErrorCode.STORAGE_INTEGRITY_ERROR})
_REASON_SHAPE = 64

CompareFunction = Callable[..., PairOutcome]


def pair_result_payload(
    page_a_profile_id: str, page_b_profile_id: str, *, reasons: Sequence[str] = (), part: str | None = None
) -> dict[str, Any]:
    return {"page_a": page_a_profile_id, "page_b": page_b_profile_id, "reasons": sorted(set(reasons)), "part": part}


def read_payload(payload: Mapping[str, Any]) -> tuple[str, str, list[str], str | None]:
    """``(page_a, page_b, reasons, part)`` of a payload, or ``ValueError`` for any other shape."""
    if set(payload) - PAYLOAD_KEYS or not {"page_a", "page_b"} <= set(payload):
        raise ValueError("the payload of a pair_result item holds the keys page_a, page_b, reasons and part, nothing else")
    pages = []
    for name in ("page_a", "page_b"):
        value = payload[name]
        if not isinstance(value, str):
            raise ValueError("a page is named by its cpr_ identity")
        ComparisonPageProfileId(value)  # IdentifierFormatError is a ValueError
        pages.append(value)
    reasons = payload.get("reasons", [])
    if not isinstance(reasons, list) or not all(isinstance(r, str) and 0 < len(r) <= _REASON_SHAPE for r in reasons):
        raise ValueError("reasons is a list of short codes")
    part = payload.get("part")
    if part is not None and part not in PART_KINDS:
        raise ValueError("part is split, floors or absent")
    return pages[0], pages[1], list(reasons), part


class _StopWork(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PairResultHandler:
    """The one handler of kind ``pair_result`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = PAIR_RESULT_KIND

    def __init__(self, dependencies: WorkDependencies, *, runner: ChildRunner | None = None,
                 compare: CompareFunction = compare_sheet_pair) -> None:
        #: Read when an item runs, not when the factory is applied (the registry builds a handler to learn its kind).
        self._dependencies = dependencies
        self._runner = runner
        self._compare = compare

    def run(self, item: WorkItem) -> Outcome:
        try:
            page_a, page_b, reasons, part = read_payload(item.payload)
        except ValueError:
            _LOG.error("comparison work %s: the pair_result payload is not valid", item.work_id)
            return Failed(REASON_PAYLOAD_INVALID)
        try:
            self._checkpoint(item)
            outcome = self._compare(
                self._dependencies.session_factory, self._dependencies.blob_store, project_uid=item.project_uid,
                page_a_profile_id=page_a, page_b_profile_id=page_b, link_reasons=reasons, part=part, runner=self._runner,
                before_publish=lambda: self._checkpoint(item), fence=item.require_current)
        except _StopWork as stop:
            _LOG.info("comparison work %s (pair_result, attempt %d): stopped: %s", item.work_id, item.attempt_no, stop.reason)
            return Yielded()
        except ChildStartError:
            _LOG.error("comparison work %s (pair_result, attempt %d): the pair child never started", item.work_id, item.attempt_no)
            return Failed(REASON_CHILD_START_FAILED, retry=True)
        except ResultInvalid:
            _LOG.error("comparison work %s (pair_result): the engine produced a result the contract refuses", item.work_id)
            return Failed(REASON_RESULT_INVALID)
        except DomainError as refusal:
            if refusal.code is ErrorCode.NOT_FOUND:
                return Failed(REASON_PAGES_NOT_FOUND)
            if refusal.code in _SOURCE_FAULTS:
                return Failed(REASON_SOURCE_UNREADABLE, retry=True)
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            raise
        _LOG.info(
            "comparison work %s (pair_result): %s result %s status=%s child=%s",
            item.work_id, "found" if outcome.cached else "written", outcome.result_id, outcome.status, outcome.child_end,
        )
        return Completed()

    def _checkpoint(self, item: WorkItem) -> None:
        """Prove the lease, extend it, and stop on a cancel or a lease that is gone."""
        if item.lease_lost.is_set():
            raise _StopWork("the lease is gone")
        if item.cancelled.is_set():
            raise _StopWork("a cancel was requested")
        sessions: sessionmaker[Session] = self._dependencies.session_factory
        work = self._dependencies.work
        with sessions() as session:
            try:
                item.check_current(session)
            except DomainError as refusal:
                if refusal.code in _LEASE_GONE:
                    item.lease_lost.set()
                    raise _StopWork("the lease is gone") from refusal
                raise
            holds = work.heartbeat(session, item.authority)
            cancel = holds and work.cancel_requested(session, item.work_id)
            session.commit()
        if not holds:
            item.lease_lost.set()
            raise _StopWork("the lease is gone")
        if cancel:
            item.cancelled.set()
            raise _StopWork("a cancel was requested")


def pair_result_handler(dependencies: WorkDependencies) -> PairResultHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``)."""
    return PairResultHandler(dependencies)
