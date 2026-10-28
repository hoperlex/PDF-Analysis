"""The handler of the ``matrix_build`` work kind: build the algorithmic matrix of a document set.

`CMP-MATRIX-01` (ADR-0025 decisions 4, 6, 7). ``prepareComparisonMatrix`` enqueues the ``page_profile`` items of the
versions that lack profiles (through :func:`~auditmanager.comparison.profile_queue.enqueue.enqueue_version_page_profiles`)
and then one ``matrix_build`` item, payload ``{"document_uid": "doc_..."}``, dedupe key ``matrix_build:<document_uid>``.
The build item may be claimed before the profiles are finished, so it does not fail on incomplete profiles; it
*waits*:

* every page of every version has a stored profile -> the matrix is built (once per input set: an input set that was
  built meanwhile is ``existing``) and the item is ``Completed``;
* a profile is missing and a ``page_profile`` item of one of the versions is still going to run -> ``Yielded`` with a
  delay: a yield is no failure and spends none of the attempt budget;
* a profile is missing and nothing is going to build it -> ``Failed("matrix_build_profiles_missing")`` without a retry
  (waiting would never end it; the expert prepares again);
* a cancel, or a lease that is gone, noticed between versions -> ``Yielded`` (the queue ends a requested cancel
  ``cancelled`` and drops the answer of an attempt that lost its lease); the publishing transaction calls
  ``WorkItem.require_current``, so a worker that lost its lease writes nothing;
* an unknown document -> ``Failed("matrix_build_document_not_found")`` without a retry; a payload of another shape ->
  ``Failed("matrix_build_payload_invalid")`` without a retry. Anything else reaches the runner, which ends the
  attempt with a retryable ``handler_error`` and logs it.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.matrix.service import MATRIX_BUILD_KIND, ComparisonMatrixService
from auditmanager.comparison.work.model import (
    Completed,
    Failed,
    Outcome,
    WorkDependencies,
    WorkItem,
    Yielded,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdentityError

__all__ = [
    "PAYLOAD_KEYS",
    "REASON_DOCUMENT_NOT_FOUND",
    "REASON_PAYLOAD_INVALID",
    "REASON_PROFILES_MISSING",
    "WAIT_FOR_PROFILES_SECONDS",
    "MatrixBuildHandler",
    "matrix_build_handler",
    "matrix_build_payload",
    "read_payload",
]

_LOG = logging.getLogger(__name__)

PAYLOAD_KEYS: Final[frozenset[str]] = frozenset({"document_uid"})
REASON_PAYLOAD_INVALID: Final[str] = "matrix_build_payload_invalid"
REASON_DOCUMENT_NOT_FOUND: Final[str] = "matrix_build_document_not_found"
REASON_PROFILES_MISSING: Final[str] = "matrix_build_profiles_missing"
#: How long the item waits before it looks at the profiles again.
WAIT_FOR_PROFILES_SECONDS: Final[float] = 5.0
_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})


def matrix_build_payload(document_uid: str) -> dict[str, Any]:
    return {"document_uid": document_uid}


def read_payload(payload: Mapping[str, Any]) -> str:
    """The document of a payload, or ``ValueError`` for any other shape."""
    if set(payload) - PAYLOAD_KEYS:
        raise ValueError("the payload of a matrix_build item holds a key it does not define")
    document_uid = payload.get("document_uid")
    if not isinstance(document_uid, str):
        raise ValueError("the payload of a matrix_build item names its document as a string")
    try:
        DocumentUid.parse(document_uid)
    except IdentityError as failure:
        raise ValueError("not a document identity") from failure
    return document_uid


class _StopBuild(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MatrixBuildHandler:
    """The one handler of kind ``matrix_build`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = MATRIX_BUILD_KIND

    def __init__(self, dependencies: WorkDependencies, *, service: ComparisonMatrixService | None = None) -> None:
        #: Read when an item runs, not when the factory is applied: the registry builds a handler to learn its kind,
        #: and that must cost nothing and touch nothing.
        self._dependencies = dependencies
        self._service = service

    def _service_for_run(self) -> ComparisonMatrixService:
        if self._service is None:
            self._service = ComparisonMatrixService(
                session_factory=self._dependencies.session_factory, blob_store=self._dependencies.blob_store
            )
        return self._service

    def run(self, item: WorkItem) -> Outcome:
        try:
            document_uid = read_payload(item.payload)
        except ValueError:
            _LOG.error("comparison work %s: the matrix_build payload is not valid", item.work_id)
            return Failed(REASON_PAYLOAD_INVALID)
        service = self._service_for_run()
        try:
            self._checkpoint(item)
            result = service.build_matrix(
                project_uid=item.project_uid,
                document_uid=document_uid,
                checkpoint=lambda: self._checkpoint(item),
                publish_guard=item.require_current,
            )
        except _StopBuild as stop:
            _LOG.info("comparison work %s (matrix_build): stopped: %s", item.work_id, stop.reason)
            return Yielded()
        except DomainError as refusal:
            if refusal.code is ErrorCode.NOT_FOUND:
                return Failed(REASON_DOCUMENT_NOT_FOUND)
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            raise
        if result.outcome == "incomplete":
            if service.profiles_pending(
                project_uid=item.project_uid, document_uid=document_uid, versions=result.missing
            ):
                return Yielded(delay_seconds=WAIT_FOR_PROFILES_SECONDS)
            _LOG.error(
                "comparison work %s (matrix_build): %d version(s) lack profiles and nothing is building them",
                item.work_id, len(result.missing),
            )
            return Failed(REASON_PROFILES_MISSING)
        return Completed()

    def _checkpoint(self, item: WorkItem) -> None:
        """Prove the lease, extend it, and stop on a cancel or a lease that is gone (as the profile handler does)."""
        if item.lease_lost.is_set():
            raise _StopBuild("the lease is gone")
        if item.cancelled.is_set():
            raise _StopBuild("a cancel was requested")
        sessions: sessionmaker[Session] = self._dependencies.session_factory
        work = self._dependencies.work
        with sessions() as session:
            try:
                item.check_current(session)
            except DomainError as refusal:
                if refusal.code in _LEASE_GONE:
                    item.lease_lost.set()
                    raise _StopBuild("the lease is gone") from refusal
                raise
            holds = work.heartbeat(session, item.authority)
            cancel = holds and work.cancel_requested(session, item.work_id)
            session.commit()
        if not holds:
            item.lease_lost.set()
            raise _StopBuild("the lease is gone")
        if cancel:
            item.cancelled.set()
            raise _StopBuild("a cancel was requested")


def matrix_build_handler(dependencies: WorkDependencies) -> MatrixBuildHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``)."""
    return MatrixBuildHandler(dependencies)
