"""Put the page profiles of a version on the comparison queue (`CMP-PROFILE-QUEUE-01`).

:func:`enqueue_version_page_profiles` is what `CMP-INGEST-02` calls after a set is confirmed (one call per
version of the set; an item is one version, and the version's pages are built one at a time inside it).
It writes one ``comparison_work`` row of module ``versions`` and kind ``page_profile`` in the caller's
transaction -- the caller commits -- and the worker that runs the module takes it from there.

Identity of an item. The version is addressed by its ``ver_`` identity, never by a name or a path, and
the dedupe key is a function of that identity alone: ``page_profile:<version_uid>``. A live item of the
same project, kind and key is returned instead of a second one, so a double click, a retried command and
a re-run of the confirmation enqueue the build once; once the item has ended, the next call makes a new
one, which finds every page already stored and completes at once. A request to build the failed pages
again has a key of its own (``page_profile:<version_uid>:retry_failed``): it is a different request, and
a live ordinary build, which would not touch the failed pages, must not swallow it.

The version must exist and belong to the project: the item is owned by the project (the erase of a
project waits for its live items), so an item that named another project's version would be filed under
the wrong owner. A version of another project is ``not_found``, the answer an unknown one gets.
"""

from __future__ import annotations

from typing import Final

from sqlalchemy.orm import Session

from auditmanager.comparison.modules import MODULE_VERSIONS
from auditmanager.comparison.profile_queue.handler import PAGE_PROFILE_KIND, page_profile_payload
from auditmanager.comparison.work.repository import ComparisonWorkRepository, Enqueued
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, VersionUid

__all__ = ["enqueue_version_page_profiles", "page_profile_dedupe_key"]

_RETRY_SUFFIX: Final[str] = ":retry_failed"


def page_profile_dedupe_key(version_uid: str, *, retry_failed: bool = False) -> str:
    """The key under which one version's live ``page_profile`` item is held (at most 256 characters)."""
    key = f"{PAGE_PROFILE_KIND}:{version_uid}"
    return key + _RETRY_SUFFIX if retry_failed else key


def enqueue_version_page_profiles(
    session: Session,
    *,
    project_uid: str,
    version_uid: str,
    created_by_user_uid: str,
    retry_failed: bool = False,
    comparison_upload_id: str | None = None,
) -> Enqueued:
    """Enqueue the build of ``version_uid``'s page profiles, or answer the live item that already is.

    ``retry_failed`` asks for the pages that ended without a result to be built again (it deletes only
    such rows, see ``build_version_page_profiles``). The caller owns the transaction. A malformed
    version identity is ``validation_failed``; an unknown version, or one of another project, is
    ``not_found``.

    ``comparison_upload_id`` (`CMP-INGEST-02`) names the upload batch the item belongs to, so that the
    batch's pause, resume and cancel reach it (``ComparisonWorkRepository.pause_for_upload`` and its
    siblings) and the batch can count its live items. It is not part of the item's identity: the dedupe
    key stays a function of the version alone, so a live item of the version is returned whichever batch
    asked first.
    """
    try:
        version = VersionUid(version_uid)
    except IdentityError as failure:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="version_uid", constraint="pattern"
        ) from failure
    record = DocumentRepository().get_version(session, version)
    if str(record.project_uid) != project_uid:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")
    return ComparisonWorkRepository().enqueue(
        session,
        project_uid=project_uid,
        module=MODULE_VERSIONS,
        kind=PAGE_PROFILE_KIND,
        payload=page_profile_payload(str(version), retry_failed=retry_failed),
        dedupe_key=page_profile_dedupe_key(str(version), retry_failed=retry_failed),
        created_by_user_uid=created_by_user_uid,
        comparison_upload_id=comparison_upload_id,
    )
