"""Persistence for projects, documents, published versions and their input manifests.

This is the write side of ``P2-META-01`` and the read side of seam ``S2`` -- "input
manifest query for one published version", which ``B5`` consumes.

Three things are deliberate here.

**No base repository.** ``docs/program/P02_SEAMS.md`` section 3.5 rules one out, along
with a generic CRUD service and any automatic retry. Every statement below is written
out, so what it writes can be read without following an inheritance chain.

**The immutable tables are only ever inserted into.** ``document_version`` and
``input_manifest_entry`` are refused UPDATE and DELETE by ``am_immutable_row`` with
SQLSTATE ``AM003``. This module contains no UPDATE or DELETE against either, which is
checkable by reading it; the trigger is what makes it true of every other caller too.
``document.current_version_uid`` *does* move -- ``document`` is a mutable aggregate --
and that is the only write here that changes an existing row.

**Non-identities are written but not projected.** ``source_filename`` and
``version_ordinal`` are stored, because the schema asks for them and a reviewer wants
them. Neither reaches :mod:`auditmanager.documents.models`, so neither can travel out in
a return value. See that module's docstring for why omission beats redaction.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage import BlobId, parse_blob_id

from .models import (
    ROLE_SOURCE_DOCUMENT,
    DocumentVersionRecord,
    ManifestEntry,
    ProjectRecord,
)

__all__ = [
    "MAX_DISPLAY_TITLE",
    "MAX_PROJECT_NAME",
    "DocumentRepository",
]

#: The schema's own bounds, restated so a caller is refused with a typed error before
#: the CHECK constraint refuses it with a driver error.
MAX_PROJECT_NAME: Final[int] = 200
MAX_DISPLAY_TITLE: Final[int] = 400

_INSERT_PROJECT = text(
    "INSERT INTO project (project_uid, name) VALUES (:project_uid, :name) "
    "RETURNING project_uid, name, created_at"
)
_SELECT_PROJECT = text(
    "SELECT project_uid, name, created_at FROM project WHERE project_uid = :project_uid"
)
_LIST_PROJECTS = text(
    # Newest first, as `listProjects` declares. The tiebreaker makes the order **total and
    # stable** - two rows sharing a `created_at` tick always come back in the same order,
    # which is what a cursor pages over. It deliberately does **not** claim to reproduce
    # creation order inside a tick: a ULID is monotonic across milliseconds, not within one,
    # so its random tail decides there. Ordering by timestamp is the contract's guarantee;
    # a total order is the implementation's.
    "SELECT project_uid, name, created_at FROM project "
    "ORDER BY created_at DESC, project_uid DESC"
)
_INSERT_DOCUMENT = text(
    "INSERT INTO document (document_uid, project_uid, display_title) "
    "VALUES (:document_uid, :project_uid, :display_title)"
)
_SELECT_DOCUMENT = text(
    "SELECT document_uid, project_uid FROM document WHERE document_uid = :document_uid"
)
_NEXT_ORDINAL = text(
    "SELECT coalesce(max(version_ordinal), 0) + 1 FROM document_version "
    "WHERE document_uid = :document_uid"
)
_INSERT_VERSION = text(
    "INSERT INTO document_version ("
    "  version_uid, document_uid, version_ordinal, source_filename,"
    "  media_type, byte_size, sha256, page_count"
    ") VALUES ("
    "  :version_uid, :document_uid, :version_ordinal, :source_filename,"
    "  :media_type, :byte_size, :sha256, :page_count"
    ")"
)
_INSERT_MANIFEST_ENTRY = text(
    "INSERT INTO input_manifest_entry ("
    "  version_uid, role, blob_id, sha256, size_bytes, media_type"
    ") VALUES (:version_uid, :role, :blob_id, :sha256, :size_bytes, :media_type)"
)
_POINT_DOCUMENT_AT_VERSION = text(
    "UPDATE document SET current_version_uid = :version_uid, updated_at = now() "
    "WHERE document_uid = :document_uid"
)
_SELECT_VERSION = text(
    "SELECT v.version_uid, v.document_uid, d.project_uid, v.version_ordinal,"
    "       d.display_title, v.media_type, v.byte_size,"
    "       v.sha256, v.page_count, v.published_at "
    "FROM document_version v JOIN document d ON d.document_uid = v.document_uid "
    "WHERE v.version_uid = :version_uid"
)
_SELECT_MANIFEST = text(
    "SELECT role, blob_id, sha256, size_bytes, media_type FROM input_manifest_entry "
    "WHERE version_uid = :version_uid ORDER BY role"
)
#: `listDocuments`. One row per document in the project: the version the document
#: *currently* points at, which is what a reader would act on. `current_version_uid` is
#: maintained by `publish_version` through `_POINT_DOCUMENT_AT_VERSION`, so this is a join
#: and never a per-document subquery over `max(version_ordinal)`.
#:
#: A document whose `current_version_uid` is still NULL is deliberately **not** listed: it
#: has no published version, so there is nothing a caller could open, start a run against
#: or stream. The INNER JOIN is that rule, written as a join rather than as a filter a
#: later reader could take for an optimisation.
#:
#: Newest first, like `listProjects`, with the opaque identity as the tiebreaker so the
#: order is total and stable across pages.
_LIST_DOCUMENTS = text(
    "SELECT v.version_uid, v.document_uid, d.project_uid, v.version_ordinal,"
    "       d.display_title, v.media_type, v.byte_size,"
    "       v.sha256, v.page_count, v.published_at "
    "FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
    "WHERE d.project_uid = :project_uid "
    "ORDER BY v.published_at DESC, v.version_uid DESC"
)

#: `listVersions`. Every published version of one document, newest first.
#: `version_ordinal` is the document's own publication order and is monotonic per
#: document, so it orders these rows exactly and needs no tiebreaker: the schema's
#: `uq_document_version_ordinal` makes `(document_uid, version_ordinal)` unique. It is a
#: display value and not an identity -- `P02_SEAMS.md` section 2.2 -- and ordering by it
#: does not make it one.
_LIST_VERSIONS = text(
    "SELECT v.version_uid, v.document_uid, d.project_uid, v.version_ordinal,"
    "       d.display_title, v.media_type, v.byte_size,"
    "       v.sha256, v.page_count, v.published_at "
    "FROM document_version v JOIN document d ON d.document_uid = v.document_uid "
    "WHERE v.document_uid = :document_uid "
    "ORDER BY v.version_ordinal DESC"
)

#: The manifests of a whole page of versions in one statement. The frozen
#: `DocumentVersion` declares `input_manifest` **required**, so a listing has to carry one
#: per row; calling `manifest_for` in a loop would make a list of twenty versions twenty-one
#: round trips. Same columns and same `ORDER BY role` as `_SELECT_MANIFEST`, so a manifest
#: read through a listing and the same manifest read through `getDocumentVersion` are the
#: same tuple in the same order.
_SELECT_MANIFESTS = text(
    "SELECT version_uid, role, blob_id, sha256, size_bytes, media_type "
    "FROM input_manifest_entry WHERE version_uid = ANY(:version_uids) "
    "ORDER BY version_uid, role"
)

_VERSIONS_REFERENCING = text(
    "SELECT version_uid, role FROM input_manifest_entry WHERE blob_id = :blob_id "
    "ORDER BY version_uid"
)
_ALL_MANIFEST_BLOBS = text(
    "SELECT DISTINCT blob_id FROM input_manifest_entry ORDER BY blob_id"
)


def _project_record(row: Any) -> ProjectRecord:
    project_uid, name, created_at = tuple(row)
    return ProjectRecord(
        project_uid=ProjectUid(project_uid), name=name, created_at=created_at
    )


def _version_record(
    row: Any, manifest: tuple[ManifestEntry, ...]
) -> DocumentVersionRecord:
    """One ``document_version`` row, in the column order every SELECT here uses.

    Written once. ``get_version``, ``list_documents`` and ``list_versions`` project the
    same ten columns in the same order, and three hand-unpacked copies of that tuple would
    be three places for one of them to shift a column silently -- which is a fault the
    reader cannot see, because every value here is a string or an int.
    """
    (
        version_uid,
        document_uid,
        project_uid,
        version_ordinal,
        display_title,
        media_type,
        byte_size,
        sha256,
        page_count,
        published_at,
    ) = tuple(row)
    return DocumentVersionRecord(
        version_uid=VersionUid(version_uid),
        document_uid=DocumentUid(document_uid),
        project_uid=ProjectUid(project_uid),
        version_ordinal=int(version_ordinal),
        display_title=display_title,
        media_type=media_type,
        byte_size=int(byte_size),
        sha256=sha256,
        page_count=int(page_count),
        published_at=published_at,
        manifest=manifest,
    )


class DocumentRepository:
    """Write and read projects, documents, versions and manifests."""

    __slots__ = ()

    # -- projects ------------------------------------------------------------

    def create_project(self, session: Session, name: str) -> ProjectRecord:
        """Allocate a project. The name is a display label, never an identity."""
        cleaned = _require_text(name, field="name", maximum=MAX_PROJECT_NAME)
        row = session.execute(
            _INSERT_PROJECT,
            {"project_uid": str(ProjectUid.new()), "name": cleaned},
        ).one()
        return _project_record(row)

    def get_project(self, session: Session, project_uid: ProjectUid) -> ProjectRecord:
        row = session.execute(
            _SELECT_PROJECT, {"project_uid": str(project_uid)}
        ).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Project")
        return _project_record(row)

    def list_projects(self, session: Session) -> tuple[ProjectRecord, ...]:
        rows = session.execute(_LIST_PROJECTS).all()
        return tuple(_project_record(row) for row in rows)

    # -- documents -----------------------------------------------------------

    def create_document(
        self, session: Session, project_uid: ProjectUid, display_title: str
    ) -> DocumentUid:
        """Create a document inside a project. ``current_version_uid`` starts unset."""
        cleaned = _require_text(
            display_title, field="display_title", maximum=MAX_DISPLAY_TITLE
        )
        document_uid = DocumentUid.new()
        session.execute(
            _INSERT_DOCUMENT,
            {
                "document_uid": str(document_uid),
                "project_uid": str(project_uid),
                "display_title": cleaned,
            },
        )
        return document_uid

    def require_document(
        self, session: Session, document_uid: DocumentUid
    ) -> ProjectUid:
        """The project a document belongs to. Refuses an unknown document."""
        row = session.execute(
            _SELECT_DOCUMENT, {"document_uid": str(document_uid)}
        ).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
        return ProjectUid(tuple(row)[1])

    # -- versions ------------------------------------------------------------

    def publish_version(
        self,
        session: Session,
        *,
        document_uid: DocumentUid,
        media_type: str,
        byte_size: int,
        sha256: str,
        page_count: int,
        source_filename: str | None,
        entries: tuple[ManifestEntry, ...],
    ) -> VersionUid:
        """Insert one immutable version with its complete manifest.

        The version row and every manifest row are written inside the caller's unit of
        work, so a version never becomes visible without the manifest that makes it
        reproducible. The ordinal is derived here rather than supplied: it is a display
        value, and letting a caller choose one would make it look like a key.
        """
        if not entries:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR, role=ROLE_SOURCE_DOCUMENT
            )
        version_uid = VersionUid.new()
        ordinal = int(
            session.execute(_NEXT_ORDINAL, {"document_uid": str(document_uid)}).scalar_one()
        )
        session.execute(
            _INSERT_VERSION,
            {
                "version_uid": str(version_uid),
                "document_uid": str(document_uid),
                "version_ordinal": ordinal,
                "source_filename": source_filename,
                "media_type": media_type,
                "byte_size": byte_size,
                "sha256": sha256,
                "page_count": page_count,
            },
        )
        for entry in entries:
            session.execute(
                _INSERT_MANIFEST_ENTRY,
                {
                    "version_uid": str(version_uid),
                    "role": entry.role,
                    "blob_id": str(entry.blob_id),
                    "sha256": entry.sha256,
                    "size_bytes": entry.size_bytes,
                    "media_type": entry.media_type,
                },
            )
        session.execute(
            _POINT_DOCUMENT_AT_VERSION,
            {"document_uid": str(document_uid), "version_uid": str(version_uid)},
        )
        return version_uid

    def get_version(
        self, session: Session, version_uid: VersionUid
    ) -> DocumentVersionRecord:
        """One published version and its manifest. Refuses an unknown identity."""
        row = session.execute(
            _SELECT_VERSION, {"version_uid": str(version_uid)}
        ).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")
        return _version_record(
            row, self.manifest_for(session, VersionUid(tuple(row)[0]))
        )

    def list_documents(
        self, session: Session, project_uid: ProjectUid
    ) -> tuple[DocumentVersionRecord, ...]:
        """`listDocuments`: the current version of every document in one project.

        **The project is proved to exist first**, so an unknown project is ``not_found``
        and not an empty page. The two answers are different facts and a caller acts on
        them differently -- an empty page says "this project has nothing in it yet", which
        is a wrong and reassuring thing to say about a project that does not exist. The
        same rule ``get_project`` already applies to a single read.
        """
        self.get_project(session, project_uid)
        rows = session.execute(
            _LIST_DOCUMENTS, {"project_uid": str(project_uid)}
        ).all()
        return self._with_manifests(session, rows)

    def list_versions(
        self, session: Session, document_uid: DocumentUid
    ) -> tuple[DocumentVersionRecord, ...]:
        """`listVersions`: every published version of one document, newest first.

        ``require_document`` first, for the reason ``list_documents`` states: an unknown
        document is ``not_found``, never an empty page.
        """
        self.require_document(session, document_uid)
        rows = session.execute(
            _LIST_VERSIONS, {"document_uid": str(document_uid)}
        ).all()
        return self._with_manifests(session, rows)

    @staticmethod
    def _with_manifests(
        session: Session, rows: Any
    ) -> tuple[DocumentVersionRecord, ...]:
        """Attach each row's manifest, in one statement rather than one per row."""
        uids = [str(tuple(row)[0]) for row in rows]
        if not uids:
            return ()
        grouped: dict[str, list[ManifestEntry]] = {uid: [] for uid in uids}
        for entry in session.execute(_SELECT_MANIFESTS, {"version_uids": uids}).all():
            version_uid, role, blob_id, sha256, size_bytes, media_type = tuple(entry)
            grouped[version_uid].append(
                ManifestEntry(
                    role=role,
                    blob_id=parse_blob_id(blob_id),
                    sha256=sha256,
                    size_bytes=int(size_bytes),
                    media_type=media_type,
                )
            )
        return tuple(
            _version_record(row, tuple(grouped[str(tuple(row)[0])])) for row in rows
        )

    def find_version(
        self, session: Session, version_uid: VersionUid
    ) -> DocumentVersionRecord | None:
        try:
            return self.get_version(session, version_uid)
        except DomainError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise

    def manifest_for(
        self, session: Session, version_uid: VersionUid
    ) -> tuple[ManifestEntry, ...]:
        """Seam ``S2``: the input manifest of one published version.

        Returns role, blob identity, checksum, size and media type -- and nothing that
        addresses a location. A consumer reads the bytes through the BlobStore port by
        ``blob_id``; there is no other route, because no other route exists.
        """
        rows = session.execute(_SELECT_MANIFEST, {"version_uid": str(version_uid)}).all()
        return tuple(
            ManifestEntry(
                role=role,
                blob_id=parse_blob_id(blob_id),
                sha256=sha256,
                size_bytes=int(size_bytes),
                media_type=media_type,
            )
            for role, blob_id, sha256, size_bytes, media_type in (
                tuple(row) for row in rows
            )
        )

    def versions_referencing(
        self, session: Session, blob_id: BlobId
    ) -> tuple[tuple[VersionUid, str], ...]:
        """Every ``(version, role)`` whose manifest points at these bytes."""
        rows = session.execute(
            _VERSIONS_REFERENCING, {"blob_id": str(blob_id)}
        ).all()
        return tuple(
            (VersionUid(version_uid), role)
            for version_uid, role in (tuple(row) for row in rows)
        )

    def manifest_blob_ids(self, session: Session) -> tuple[BlobId, ...]:
        """Every blob any published manifest references. Used by reconciliation."""
        rows = session.execute(_ALL_MANIFEST_BLOBS).all()
        return tuple(parse_blob_id(tuple(row)[0]) for row in rows)


def _require_text(value: str, *, field: str, maximum: int) -> str:
    """Refuse a display value the schema's CHECK would refuse, with a typed error.

    The offending value is never echoed. ``validation_failed`` declares ``field`` and
    ``constraint`` as safe detail keys and nothing that would carry the input itself.
    """
    if not isinstance(value, str) or not value.strip():
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field=field, constraint="non_empty"
        )
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            field=field,
            constraint=f"char_length <= {maximum}",
        )
    return cleaned
