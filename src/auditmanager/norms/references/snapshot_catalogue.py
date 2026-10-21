"""The pinned catalogue of one norms snapshot, read straight from its document rows.

`NORM-REFS-RUN-01`. The W57b resolver wants a :class:`PinnedCatalogue`: every document of
exactly one snapshot, with the SQL-generated designation tokens, plus the explicit list of
slugs the family parser cannot read. ``catalogue_input`` builds it from a *verified retrieval
set's* saved catalogue blob and only for a running Run; a finished Run's page has neither the
attempt nor (for runs older than W57a) a set. This module is the per-request alternative: a
SELECT-only, bounded and paged read of ``norm_document`` for the snapshot the Run pinned.

The two read paths stay one rule. Both end in :class:`PinnedCatalogue`, both are checked by the
resolver's own ``_catalogue_index`` (identities unique, stored tokens equal the Python twin,
every unparsed slug listed and every listed slug unparsed), and the unparsed list is computed
here by the very parser the resolver uses -- it is never a reviewed list that could drift.

Bounds: documents are read ``page_size`` at a time by keyset on ``norm_document_id`` (so no
statement holds an offset or an unbounded result), and a snapshot that declares more than
:data:`MAX_SNAPSHOT_DOCUMENTS` documents, or stores a different number than it declares, is
refused rather than cut. Nothing is written; the caller owns the transaction.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.norms.embedding.profile import require_snapshot_id
from auditmanager.norms.references.families import parse_designation
from auditmanager.norms.references.resolution import (
    CatalogueEntry,
    PinnedCatalogue,
    ReferenceRefused,
)

__all__ = [
    "MAX_SNAPSHOT_DOCUMENTS",
    "SNAPSHOT_PAGE_SIZE",
    "catalogue_from_rows",
    "read_snapshot_catalogue",
]

#: Documents per statement. The real corpus holds 674, so it is read in two statements.
SNAPSHOT_PAGE_SIZE: Final[int] = 500
#: A snapshot declaring more documents than this is refused (the saved-catalogue reader's
#: ten-megabyte ceiling is the same bound in bytes; 20 000 rows are well below it).
MAX_SNAPSHOT_DOCUMENTS: Final[int] = 20_000

_DOCUMENT_ID = re.compile(r"ndoc_[0-9A-HJKMNP-TV-Z]{26}\Z")

_DECLARED_COUNT = text(
    "SELECT document_count FROM norms_snapshot WHERE norms_snapshot_id = :snapshot_id"
)
# ``COLLATE "C"`` is the order the snapshot's own readers use, so the keyset and the
# canonical catalogue order are the same byte order whatever the database collation is.
_DOCUMENT_PAGE = text("""
    SELECT norm_document_id, slug, designation_tokens
      FROM norm_document
     WHERE norms_snapshot_id = :snapshot_id
       AND norm_document_id COLLATE "C" > :after
     ORDER BY norm_document_id COLLATE "C"
     LIMIT :page_size
""")


def _entry(row: Mapping[str, Any]) -> CatalogueEntry:
    document_id, slug, tokens = row["norm_document_id"], row["slug"], row["designation_tokens"]
    if not isinstance(document_id, str) or _DOCUMENT_ID.fullmatch(document_id) is None:
        raise ReferenceRefused("invalid snapshot document id")
    if not isinstance(slug, str) or not slug:
        raise ReferenceRefused("snapshot document slug is empty")
    if (
        not isinstance(tokens, (tuple, list))
        or not tokens
        or any(not isinstance(token, str) or not token for token in tokens)
    ):
        raise ReferenceRefused("snapshot document designation tokens are missing")
    return CatalogueEntry(document_id, slug, tuple(tokens))


def catalogue_from_rows(
    *, snapshot_id: str, declared_count: int, rows: Iterable[Mapping[str, Any]]
) -> PinnedCatalogue:
    """Validate one snapshot's rows (in canonical order) and compute its unparsed slugs.

    Pure. The rows are the whole snapshot: fewer or more than ``declared_count`` is refused,
    as is any order but strictly increasing ``norm_document_id`` (the order the saved
    catalogue uses, which keeps the two read paths comparable byte for byte).
    """
    try:
        require_snapshot_id(snapshot_id)
    except (TypeError, ValueError) as exc:
        raise ReferenceRefused("invalid pinned snapshot id") from exc
    if (
        type(declared_count) is not int
        or not 1 <= declared_count <= MAX_SNAPSHOT_DOCUMENTS
    ):
        raise ReferenceRefused("snapshot declares an unusable document count")
    entries: list[CatalogueEntry] = []
    unparsed: list[str] = []
    previous: str | None = None
    for row in rows:
        entry = _entry(row)
        if previous is not None and entry.document_id <= previous:
            raise ReferenceRefused("snapshot documents are out of canonical order")
        previous = entry.document_id
        if len(entries) >= declared_count:
            raise ReferenceRefused("snapshot stores more documents than it declares")
        entries.append(entry)
        if parse_designation(entry.slug) is None:
            unparsed.append(entry.slug)
    if len(entries) != declared_count:
        raise ReferenceRefused("snapshot stores fewer documents than it declares")
    return PinnedCatalogue(snapshot_id, tuple(entries), tuple(unparsed))


def _pages(
    session: Session, *, snapshot_id: str, page_size: int
) -> Iterable[Mapping[str, Any]]:
    after = ""
    while True:
        page = session.execute(
            _DOCUMENT_PAGE,
            {"snapshot_id": snapshot_id, "after": after, "page_size": page_size},
        ).mappings().all()
        yield from page
        if len(page) < page_size:
            return
        after = page[-1]["norm_document_id"]


def read_snapshot_catalogue(
    session: Session, *, snapshot_id: str, page_size: int = SNAPSHOT_PAGE_SIZE
) -> PinnedCatalogue:
    """Read one snapshot's documents, page by page, under the caller's transaction.

    An absent snapshot or a stored document count that differs from the declared one is
    refused with :class:`ReferenceRefused`; nothing is guessed or repaired.
    """
    try:
        require_snapshot_id(snapshot_id)
    except (TypeError, ValueError) as exc:
        raise ReferenceRefused("invalid pinned snapshot id") from exc
    if type(page_size) is not int or not 1 <= page_size <= SNAPSHOT_PAGE_SIZE:
        raise ReferenceRefused("invalid snapshot page size")
    declared = session.execute(_DECLARED_COUNT, {"snapshot_id": snapshot_id}).scalar_one_or_none()
    if declared is None:
        raise ReferenceRefused("pinned snapshot is absent")
    return catalogue_from_rows(
        snapshot_id=snapshot_id,
        declared_count=declared,
        rows=_pages(session, snapshot_id=snapshot_id, page_size=page_size),
    )
