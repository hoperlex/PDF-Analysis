"""Build and store the page profiles of one version.

`CMP-PROFILE-01`. :func:`build_version_page_profiles` is the function the comparison queue calls as a
work kind (`CMP-WORK-01` registers a handler for it; this module imports nothing of the queue). For one
published version it

1. reads the version and the blob of its source document, and the pages that already have a profile of
   the current :data:`~auditmanager.comparison.profile.limits.ALGO_VERSION`;
2. streams the source PDF once into a private temporary file;
3. for each page without a profile, **in order and one at a time**, profiles it
   (:func:`~auditmanager.comparison.profile.profiling.profile_page`: a render child, then an extraction
   child, each under its kernel ceiling), publishes its archive, preview and thumbnail through the
   durable blob journal, and inserts the row -- one transaction per page, so a stopped build is resumed
   by running it again and nothing already stored is touched;
4. reports, per page, what was written.

**Bounded.** ``max_pages`` (`CMP-C1-FIX-C` item 2) limits one call to that many pages built by the children; the
rest is reported as ``remaining`` and a later call (the queue's next attempt) continues after the stored pages. The
queue's attempt is fenced after 900 s whatever its progress, so the size of a call is what keeps a long version
inside it (``profile_queue/handler.py`` holds the number and the measurement it comes from).

**Idempotent.** The unique keys of the table make a second run a no-op (``skipped``), and two builds of
one version at once cost duplicated work, not duplicated rows. **A page that failed does not stop the
version**: it is stored ``needs_review`` / ``RENDER_FAILED`` (or ``refused`` / ``PAGE_TOO_LARGE``) and the
next page is built. A child that never started is the server's fault (:class:`ChildStartError`) and ends
the build with what was stored so far.

``on_page`` is called after every page with its report; whatever it raises (a lost lease, a
cancellation) ends the build there, which is how the queue's heartbeat and cancel reach a long build
without this module knowing about the queue.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.profiling import PageOutcome, profile_page
from auditmanager.comparison.profile.pack import PACK_MEDIA_TYPE
from auditmanager.comparison.profile.publish import (
    PNG_MEDIA_TYPE,
    ROLE_PAGE_PREVIEW,
    ROLE_PAGE_PROFILE,
    ROLE_PAGE_THUMBNAIL,
    ProfileBlobPublisher,
)
from auditmanager.comparison.profile.repository import PageProfileRepository
from auditmanager.comparison.profile.runner import ChildRunner, SubprocessChildRunner
from auditmanager.comparison.profile.source import load_source_version, materialised_source
from auditmanager.shared.db import session_scope

__all__ = ["PageBuildReport", "VersionBuildReport", "build_version_page_profiles"]

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PageBuildReport:
    page_number: int
    page_profile_id: str
    status: str
    reason: str | None
    #: True when this call wrote the row; False when another worker had written it first.
    created: bool
    timings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VersionBuildReport:
    version_uid: str
    algo_version: str
    page_count: int
    pages: tuple[PageBuildReport, ...] = ()
    #: Pages that already had a profile of this algorithm version and were left as they were.
    skipped: int = 0
    #: Failed rows removed before this build because ``retry_failed`` was asked for.
    replaced_failed: int = 0
    #: Pages without a row that this call left for a later one because ``max_pages`` was reached.
    remaining: int = 0

    def count(self, status: str) -> int:
        return sum(1 for page in self.pages if page.status == status)

    @property
    def complete(self) -> bool:
        """Every page of the version has a row (of any status) after this call."""
        return self.remaining == 0 and len(self.pages) + self.skipped >= self.page_count


def _store_page(
    publisher: ProfileBlobPublisher,
    repository: PageProfileRepository,
    factory: sessionmaker[Session],
    version_uid: str,
    outcome: PageOutcome,
) -> PageBuildReport:
    pack_id = (
        publisher.publish(outcome.pack, role=ROLE_PAGE_PROFILE, media_type=PACK_MEDIA_TYPE)
        if outcome.pack is not None
        else None
    )
    preview_id = (
        publisher.publish(outcome.preview, role=ROLE_PAGE_PREVIEW, media_type=PNG_MEDIA_TYPE)
        if outcome.preview is not None
        else None
    )
    thumbnail_id = (
        publisher.publish(outcome.thumbnail, role=ROLE_PAGE_THUMBNAIL, media_type=PNG_MEDIA_TYPE)
        if outcome.thumbnail is not None
        else None
    )
    with session_scope(factory) as session:
        inserted = repository.insert(
            session,
            version_uid=version_uid,
            page_number=outcome.page_number,
            content_key=outcome.content_key,
            algo_version=limits.ALGO_VERSION,
            status=outcome.status,
            reason=outcome.reason,
            summary=outcome.summary,
            profile_blob_id=pack_id,
            preview_blob_id=preview_id,
            thumbnail_blob_id=thumbnail_id,
        )
        row_id = inserted
        if row_id is None:
            row = repository.get_for_page(session, version_uid, outcome.page_number, limits.ALGO_VERSION)
            row_id = None if row is None else row.page_profile_id
    if row_id is None:  # pragma: no cover - a conflict on the content key of another page
        raise RuntimeError("the page profile row could not be written or found")
    return PageBuildReport(
        page_number=outcome.page_number,
        page_profile_id=row_id,
        status=outcome.status,
        reason=outcome.reason,
        created=inserted is not None,
        timings=outcome.timings,
    )


def build_version_page_profiles(
    session_factory: sessionmaker[Session],
    blob_store: Any,
    version_uid: str,
    *,
    runner: ChildRunner | None = None,
    pages: Collection[int] | None = None,
    retry_failed: bool = False,
    retry_cutoff: datetime | None = None,
    max_pages: int | None = None,
    on_page: Callable[[PageBuildReport], None] | None = None,
    render_limits: limits.ChildLimits = limits.RENDER_LIMITS,
    extract_limits: limits.ChildLimits = limits.EXTRACT_LIMITS,
    work_dir: str | None = None,
) -> VersionBuildReport:
    """Store the missing page profiles of ``version_uid``; see the module docstring.

    ``pages`` (1-based) limits the build to those pages; ``retry_failed`` first removes the rows of
    pages that ended without a result so that they are built again (with ``retry_cutoff`` only those
    written before that instant: the queue passes the instant its retry item was asked for, so that a page
    which fails again while the item runs is not removed by the item's next attempt); ``max_pages`` bounds
    the pages the children are started for in this call (``ValueError`` below one).
    """
    if max_pages is not None and max_pages < 1:
        raise ValueError("a build call profiles at least one page")
    repository = PageProfileRepository()
    with session_scope(session_factory) as session:
        source = load_source_version(session, version_uid)
        replaced = (
            repository.delete_failed(session, version_uid, limits.ALGO_VERSION, created_before=retry_cutoff)
            if retry_failed
            else 0
        )
        existing = repository.existing(session, version_uid, limits.ALGO_VERSION)
    wanted = [
        number
        for number in range(1, source.page_count + 1)
        if number not in existing and (pages is None or number in pages)
    ]
    skipped = sum(1 for number in range(1, source.page_count + 1) if number in existing)
    if not wanted:
        return VersionBuildReport(version_uid, limits.ALGO_VERSION, source.page_count, (), skipped, replaced)

    remaining = 0
    if max_pages is not None and len(wanted) > max_pages:
        remaining = len(wanted) - max_pages
        wanted = wanted[:max_pages]

    runner = runner or SubprocessChildRunner()
    publisher = ProfileBlobPublisher(session_factory, blob_store)
    reports: list[PageBuildReport] = []
    with materialised_source(blob_store, source) as path:
        for number in wanted:
            outcome = profile_page(
                runner,
                pdf_path=path,
                page_index=number - 1,
                version_sha256=source.sha256,
                work_dir=work_dir,
                render_limits=render_limits,
                extract_limits=extract_limits,
            )
            report = _store_page(publisher, repository, session_factory, version_uid, outcome)
            reports.append(report)
            _LOG.info(
                "comparison_page_profile page=%s status=%s reason=%s created=%s",
                number, report.status, report.reason, report.created,
            )
            if on_page is not None:
                on_page(report)
    return VersionBuildReport(
        version_uid, limits.ALGO_VERSION, source.page_count, tuple(reports), skipped, replaced, remaining
    )
