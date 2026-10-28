"""The handler of the ``page_profile`` work kind (`CMP-PROFILE-QUEUE-01`, ADR-0025 decisions 4, 6, 7, 8).

One item is one version: its payload is ``{"version_uid": "ver_..."}`` (and ``"retry_failed": true`` for an
item that asks for the pages that ended without a result to be built again). The handler calls
:func:`~auditmanager.comparison.profile.builder.build_version_page_profiles`, which stores the missing
profiles one page at a time, one transaction per page, and says so after each page (``on_page``). That
call is where the queue reaches a long build, and the handler uses it for three things:

* **the lease** is extended and checked (``WorkItem.check_current`` then the heartbeat) -- the item's own
  heartbeat thread beats every twenty seconds, and a page may take longer than that, so each page also
  proves the lease on its own;
* **a cancel** that was requested while the item runs is looked for in the database, not only in the
  thread's flag, so a build stops after the page it is on and not at the next beat;
* **either of them ends the build there**: the page just stored stays (it is the same row a later run
  would write), nothing after it is started, and the item answers ``Yielded`` -- the queue ends it
  ``cancelled`` when a cancel was requested (``ComparisonWorkRepository.finish``) and drops the answer
  of an attempt that no longer holds its lease.

How a build ends
----------------
* every page of the version has a row (``ready``, ``needs_review`` or ``refused``): ``Completed``. A page
  that ended without a result is a stored ``needs_review`` page, not a failed item;
* a child that never started (:class:`~auditmanager.comparison.profile.runner.ChildStartError`) is the
  server's fault, not a verdict on a page: ``Failed(..., retry=True)``;
* a version the database does not know: ``Failed`` without a retry (waiting does not create it);
* a source document that cannot be read, is missing from the manifest or does not match its recorded digest
  (``analysis_input_invalid`` or ``storage_integrity_error``): ``Failed`` with a retry (a storage outage is
  transient; a corrupted object uses the attempt budget and then ends the item);
* a payload that is not the shape above: ``Failed`` without a retry;
* anything else the builder raises reaches the runner, which ends the attempt with a retryable
  ``handler_error`` and logs it.

A resumed or repeated item is cheap: the builder skips every page that has a row, so it costs time, not
rows. An item that asked for ``retry_failed`` asks again at each attempt: a page that failed again in an
earlier attempt of the same item is built once more, which is bounded by the item's attempt budget.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.builder import (
    PageBuildReport,
    VersionBuildReport,
    build_version_page_profiles,
)
from auditmanager.comparison.profile.runner import ChildRunner, ChildStartError
from auditmanager.comparison.work.model import (
    Completed,
    Failed,
    Outcome,
    WorkDependencies,
    WorkItem,
    Yielded,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid

__all__ = [
    "PAGE_PROFILE_KIND",
    "PAYLOAD_KEYS",
    "PageProfileHandler",
    "REASON_CHILD_START_FAILED",
    "REASON_INCOMPLETE",
    "REASON_PAYLOAD_INVALID",
    "REASON_SOURCE_UNREADABLE",
    "REASON_VERSION_NOT_FOUND",
    "page_profile_handler",
    "page_profile_payload",
    "read_payload",
]

_LOG = logging.getLogger(__name__)

#: The work kind. ``comparison.public.PAGE_PROFILE_WORK_KIND`` names the same string (a test holds them equal).
PAGE_PROFILE_KIND: Final[str] = "page_profile"
PAYLOAD_KEYS: Final[frozenset[str]] = frozenset({"version_uid", "retry_failed"})

REASON_PAYLOAD_INVALID: Final[str] = "page_profile_payload_invalid"
REASON_VERSION_NOT_FOUND: Final[str] = "page_profile_version_not_found"
REASON_SOURCE_UNREADABLE: Final[str] = "page_profile_source_unreadable"
REASON_CHILD_START_FAILED: Final[str] = "page_profile_child_start_failed"
REASON_INCOMPLETE: Final[str] = "page_profile_incomplete"

_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset(
    {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}
)
#: What the builder raises for a source document it cannot hand to a child: none in the manifest, an object that
#: cannot be read, or bytes whose digest is not the one the version recorded.
_SOURCE_FAULTS: Final[frozenset[ErrorCode]] = frozenset(
    {ErrorCode.ANALYSIS_INPUT_INVALID, ErrorCode.STORAGE_INTEGRITY_ERROR}
)

BuildFunction = Callable[..., VersionBuildReport]


def page_profile_payload(version_uid: str, *, retry_failed: bool = False) -> dict[str, Any]:
    """The payload of an item: the version, and ``retry_failed`` only when it is asked for."""
    payload: dict[str, Any] = {"version_uid": version_uid}
    if retry_failed:
        payload["retry_failed"] = True
    return payload


def read_payload(payload: Mapping[str, Any]) -> tuple[str, bool]:
    """``(version_uid, retry_failed)`` of a payload, or ``ValueError`` for any other shape."""
    unknown = set(payload) - PAYLOAD_KEYS
    if unknown:
        raise ValueError("the payload of a page_profile item holds a key it does not define")
    version_uid = payload.get("version_uid")
    if not isinstance(version_uid, str):
        raise ValueError("the payload of a page_profile item names its version as a string")
    VersionUid(version_uid)  # IdentifierFormatError is a ValueError: a ver_ identity, nothing else
    retry_failed = payload.get("retry_failed", False)
    if not isinstance(retry_failed, bool):
        raise ValueError("retry_failed is true or false")
    return version_uid, retry_failed


class _StopBuild(Exception):
    """Raised from ``on_page`` to end the build there; it never leaves the handler."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PageProfileHandler:
    """The one handler of kind ``page_profile`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = PAGE_PROFILE_KIND

    def __init__(
        self,
        dependencies: WorkDependencies,
        *,
        runner: ChildRunner | None = None,
        build: BuildFunction = build_version_page_profiles,
    ) -> None:
        #: Read when an item runs, not when the factory is applied: the registry builds a handler to learn
        #: its kind, and that must cost nothing and touch nothing.
        self._dependencies = dependencies
        #: ``None`` makes the builder start its own ``SubprocessChildRunner``; a test may supply one.
        self._runner = runner
        self._build = build

    def run(self, item: WorkItem) -> Outcome:
        try:
            version_uid, retry_failed = read_payload(item.payload)
        except ValueError:
            _LOG.error("comparison work %s: the page_profile payload is not valid", item.work_id)
            return Failed(REASON_PAYLOAD_INVALID)

        def on_page(report: PageBuildReport) -> None:
            self._checkpoint(item)

        try:
            self._checkpoint(item)
            report = self._build(
                self._dependencies.session_factory,
                self._dependencies.blob_store,
                version_uid,
                runner=self._runner,
                retry_failed=retry_failed,
                on_page=on_page,
            )
        except _StopBuild as stop:
            _LOG.info(
                "comparison work %s (page_profile, attempt %d): the build of %s stopped between pages: %s",
                item.work_id, item.attempt_no, version_uid, stop.reason,
            )
            return Yielded()
        except ChildStartError:
            _LOG.error(
                "comparison work %s (page_profile, attempt %d): a page child never started; "
                "the attempt fails and is retried",
                item.work_id, item.attempt_no,
            )
            return Failed(REASON_CHILD_START_FAILED, retry=True)
        except DomainError as refusal:
            if refusal.code is ErrorCode.NOT_FOUND:
                return Failed(REASON_VERSION_NOT_FOUND)
            if refusal.code in _SOURCE_FAULTS:
                return Failed(REASON_SOURCE_UNREADABLE, retry=True)
            raise
        if not report.complete:
            _LOG.error(
                "comparison work %s (page_profile): %s of %d pages have a row after the build",
                item.work_id, len(report.pages) + report.skipped, report.page_count,
            )
            return Failed(REASON_INCOMPLETE, retry=True)
        return Completed()

    def _checkpoint(self, item: WorkItem) -> None:
        """Between pages: prove the lease, extend it, and stop on a cancel or a lease that is gone."""
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


def page_profile_handler(dependencies: WorkDependencies) -> PageProfileHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``)."""
    return PageProfileHandler(dependencies)
