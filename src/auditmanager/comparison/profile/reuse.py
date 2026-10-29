"""Take over the stored page profiles of a version whose source bytes are identical (`CMP-C1-FIX-C` item 3).

`MEASURE-ENGINE-01.md` section 9 item 4: a version uploaded again with the same bytes cost 63 s of wall and 59 s of child CPU to
produce profiles whose blobs the store then shared with the first one's. The page content Merkle cannot key a cache that skips
the work: it is a product of the extraction child, which is most of the cost, so it is known only after the work is done. What is
known before is the **source bytes**: the same bytes, the same page and the same algorithm version (``cmp-profile/3``) are the
same profile, byte for byte (the content key is a function of the page and its Merkle only, and the blobs are addressed by
content).

A version may take over the rows of another version when

* the other version is **in the same project** (a profile of another project's version is never read or copied),
* its source is bound under one of the two source roles and equals this version's bytes (digest, size and page count), and
* the row is of the current algorithm version and is not a page that ended without a result (``RENDER_FAILED`` is not
  evidence: it says what a host could not do, and the retry path rebuilds it).

The copy is a new row of this version with the same status, reason, content key, summary and blob references; nothing is
rendered, nothing is written to the object store. It is one transaction; the unique keys of the table and ``ON CONFLICT DO
NOTHING`` make a repeated or concurrent take-over a no-op. Anything the donor lacks is built by the builder as before.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.repository import PageProfileRepository
from auditmanager.comparison.profile.source import SourceVersion
from auditmanager.shared.db import session_scope

__all__ = ["ReusedPage", "reuse_identical_pages"]


@dataclass(frozen=True, slots=True)
class ReusedPage:
    page_number: int
    page_profile_id: str
    status: str
    reason: str | None
    #: The version the row was taken from.
    donor_version_uid: str
    #: False when the page already had a row (another worker wrote it first).
    created: bool


def _donors(session: Session, source: SourceVersion) -> Iterator[str]:
    """The other versions of this project whose source is these exact bytes, in a fixed order."""
    from auditmanager.documents.public import (
        MANIFEST_ROLE_COMPARISON_PDF,
        MANIFEST_ROLE_SOURCE_DOCUMENT,
        DocumentRepository,
    )
    from auditmanager.shared.identity import VersionUid
    from auditmanager.storage.public import parse_blob_id

    roles = (MANIFEST_ROLE_SOURCE_DOCUMENT, MANIFEST_ROLE_COMPARISON_PDF)
    documents = DocumentRepository()
    referencing = documents.versions_referencing(session, parse_blob_id(source.blob_id))
    for uid in sorted({str(version) for version, role in referencing if role in roles}):
        if uid == source.version_uid:
            continue
        record = documents.get_version(session, VersionUid(uid))
        if str(record.project_uid) != source.project_uid or int(record.page_count) != source.page_count:
            continue
        entries = [item for item in record.manifest if item.role in roles]
        if len(entries) == 1 and entries[0].sha256 == source.sha256 and int(entries[0].size_bytes) == source.size_bytes:
            yield uid


def reuse_identical_pages(
    session_factory: sessionmaker[Session],
    repository: PageProfileRepository,
    source: SourceVersion,
    wanted: Sequence[int],
) -> list[ReusedPage]:
    """Give ``source``'s version a row for each of ``wanted`` that an identical version of its project already has."""
    if not wanted:
        return []
    taken: dict[int, ReusedPage] = {}
    with session_scope(session_factory) as session:
        for donor in _donors(session, source):
            missing = [number for number in wanted if number not in taken]
            if not missing:
                break
            for row in repository.reusable_rows(session, donor, limits.ALGO_VERSION, missing):
                inserted = repository.insert(
                    session,
                    version_uid=source.version_uid,
                    page_number=row.page_number,
                    content_key=row.content_key,
                    algo_version=limits.ALGO_VERSION,
                    status=row.status,
                    reason=row.reason,
                    summary=row.summary,
                    profile_blob_id=row.profile_blob_id,
                    preview_blob_id=row.preview_blob_id,
                    thumbnail_blob_id=row.thumbnail_blob_id,
                )
                page_id, status, reason = inserted, row.status, row.reason
                if inserted is None:
                    existing = repository.get_for_page(session, source.version_uid, row.page_number, limits.ALGO_VERSION)
                    if existing is None:
                        continue  # the content key is held by another page of this version: build this page instead
                    page_id, status, reason = existing.page_profile_id, existing.status, existing.reason
                taken[row.page_number] = ReusedPage(
                    page_number=row.page_number,
                    page_profile_id=page_id,
                    status=status,
                    reason=reason,
                    donor_version_uid=donor,
                    created=inserted is not None,
                )
    return [taken[number] for number in sorted(taken)]
