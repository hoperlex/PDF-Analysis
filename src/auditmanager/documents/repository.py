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
from auditmanager.storage.public import BlobId, parse_blob_id

from .models import (
    ROLE_SOURCE_DOCUMENT,
    ClassificationRevisionRecord,
    CurrentVersionPlacementRecord,
    DocumentVersionRecord,
    ManifestEntry,
    ProjectListingRecord,
    ProjectRecord,
    VersionClassificationRecord,
)

__all__ = [
    "MAX_DISPLAY_TITLE",
    "MAX_PLACEMENT_PAGE",
    "MAX_PROJECT_NAME",
    "DocumentRepository",
]

#: The schema's own bounds, restated so a caller is refused with a typed error before
#: the CHECK constraint refuses it with a driver error.
MAX_PROJECT_NAME: Final[int] = 200
MAX_DISPLAY_TITLE: Final[int] = 400

#: The most placements one page of ``list_current_versions_in_section`` /
#: ``list_unclassified_current_versions`` returns. A caller that needs more reads the next
#: page; no read here is unbounded.
MAX_PLACEMENT_PAGE: Final[int] = 1000

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
    #
    # `document_count` is the fourth column, under owner ruling `R-10`. **The two joins are
    # `_LIST_DOCUMENTS`' join, verbatim**: `document d` to `document_version v` on
    # `v.version_uid = d.current_version_uid`. That is the whole argument that the count
    # agrees with `listDocuments` - it is not a second definition of "a document in this
    # project" that has to be kept in step with the first, it is the same join with the
    # rows counted instead of returned. A document whose `current_version_uid` is NULL is
    # not listed by `listDocuments` and is not counted here.
    #
    # `LEFT JOIN`, twice, and `count(v.version_uid)` rather than `count(*)`: an inner join
    # would drop a project with no documents out of the listing entirely, and `count(*)`
    # over the outer-joined NULL row would report 1 for it. `count` of a column ignores
    # NULLs, so an empty project reports **0** - a measurement, not an omission. `D-3` is
    # what a flattering default costs.
    #
    # **One statement, not one per project.** A count fetched in a loop over a page of
    # projects is N+1 round trips at any page size, and the alternative `R-10` rejected was
    # exactly that shape moved into the browser.
    #
    # No row multiplication: `document_version.version_uid` is the primary key, so each
    # `document` row joins at most one version row, and `GROUP BY p.project_uid` is legal
    # because it is `project`'s primary key and the other two columns are functionally
    # dependent on it.
    "SELECT p.project_uid, p.name, p.created_at, count(v.version_uid) AS document_count "
    "FROM project p "
    "LEFT JOIN document d ON d.project_uid = p.project_uid "
    "LEFT JOIN document_version v ON v.version_uid = d.current_version_uid "
    "GROUP BY p.project_uid, p.name, p.created_at "
    "ORDER BY p.created_at DESC, p.project_uid DESC"
)
_INSERT_DOCUMENT = text(
    "INSERT INTO document (document_uid, project_uid, display_title, section) "
    "VALUES (:document_uid, :project_uid, :display_title, :section)"
)
_SELECT_DOCUMENT = text(
    "SELECT document_uid, project_uid FROM document WHERE document_uid = :document_uid"
)
#: `W59-VERSION-UPLOAD-01`. The document row is locked before its next ordinal is read, so
#: two publications into one document serialise here and the second reads the first's
#: committed ordinal (each statement under ``READ COMMITTED`` takes a fresh snapshot).
#: Without it both read the same ``max + 1`` and the second insert dies on
#: ``uq_document_version_ordinal`` -- an ``internal_error`` for a perfectly valid upload.
#: ``FOR NO KEY UPDATE`` is exactly the lock the closing ``UPDATE document`` takes anyway,
#: taken earlier; unlike ``FOR UPDATE`` it does not block other transactions' foreign-key
#: checks against the document.
_LOCK_DOCUMENT = text(
    "SELECT document_uid FROM document WHERE document_uid = :document_uid "
    "FOR NO KEY UPDATE"
)
_NEXT_ORDINAL = text(
    "SELECT coalesce(max(version_ordinal), 0) + 1 FROM document_version "
    "WHERE document_uid = :document_uid"
)
#: The three counts are written together or not at all (``0021``'s
#: ``ck_document_version_bundle_counts_together``): all three NULL for a version published
#: without a portal bundle. The list is cast because an empty one has no element to type it.
_INSERT_VERSION = text(
    "INSERT INTO document_version ("
    "  version_uid, document_uid, version_ordinal, source_filename,"
    "  media_type, byte_size, sha256, page_count,"
    "  text_character_count, textless_pages, recognised_character_count"
    ") VALUES ("
    "  :version_uid, :document_uid, :version_ordinal, :source_filename,"
    "  :media_type, :byte_size, :sha256, :page_count,"
    "  :text_character_count, CAST(:textless_pages AS integer[]),"
    "  :recognised_character_count"
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
    "       d.display_title, d.section, v.media_type, v.byte_size,"
    "       v.sha256, v.page_count, v.published_at,"
    "       v.text_character_count, v.textless_pages, v.recognised_character_count,"
    "       c.project_stage, c.section_code, c.confirmed_by_user_uid, c.confirmed_at,"
    "       c.revision "
    "FROM document_version v JOIN document d ON d.document_uid = v.document_uid "
    "LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid "
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
    "       d.display_title, d.section, v.media_type, v.byte_size,"
    "       v.sha256, v.page_count, v.published_at,"
    "       v.text_character_count, v.textless_pages, v.recognised_character_count,"
    "       c.project_stage, c.section_code, c.confirmed_by_user_uid, c.confirmed_at,"
    "       c.revision "
    "FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
    "LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid "
    "WHERE d.project_uid = :project_uid "
    "ORDER BY v.published_at DESC, v.version_uid DESC"
)

#: `SECTION-READ-MODEL-01`. The document sets whose **current** version is confirmed in one
#: section: ``document.current_version_uid`` selects the version, and that version's own row in
#: ``version_classification_current`` (``W59-SECTION-IDENTITY-DECISION-01``; the latest
#: revision since `CLASSIFICATION-CORRECTION-01`) is the confirmation. The inner join on the
#: classification is the rule: a set whose current version
#: has none is not a member, and neither is a set whose *older* version was confirmed in this
#: section -- the legacy ``document.section`` is not read at all. ``_LIST_DOCUMENTS``' join
#: (``document`` to ``document_version`` on ``current_version_uid``), so a document with no
#: published current version is absent here exactly as it is from ``listDocuments``.
#:
#: Keyset-paged on ``document_uid`` -- the primary key of ``document``, and one current version
#: per document, so the order is total and a page never repeats or skips a row while the next
#: is read. The optional filters use ``CAST(:x AS text) IS NULL`` so one statement serves
#: "every project" and "this project" without string assembly.
_LIST_SECTION_MEMBERS = text(
    "SELECT d.document_uid, d.project_uid, p.name, d.display_title, v.version_uid,"
    "       v.version_ordinal, v.page_count, c.project_stage, c.section_code "
    "FROM document d "
    "JOIN project p ON p.project_uid = d.project_uid "
    "JOIN document_version v ON v.version_uid = d.current_version_uid "
    "JOIN version_classification_current c ON c.version_uid = v.version_uid "
    "WHERE c.section_code = :section_code "
    "  AND (CAST(:project_uid AS text) IS NULL OR d.project_uid = CAST(:project_uid AS text)) "
    "  AND (CAST(:after AS text) IS NULL OR d.document_uid > CAST(:after AS text)) "
    "ORDER BY d.document_uid "
    "LIMIT :limit"
)
#: The complement: the sets whose current version no expert has classified (the ``LEFT JOIN``
#: finds no row). Same join, same keyset, same filters; ``project_stage`` and ``section_code``
#: come back NULL by construction.
_LIST_UNCLASSIFIED_CURRENT = text(
    "SELECT d.document_uid, d.project_uid, p.name, d.display_title, v.version_uid,"
    "       v.version_ordinal, v.page_count, c.project_stage, c.section_code "
    "FROM document d "
    "JOIN project p ON p.project_uid = d.project_uid "
    "JOIN document_version v ON v.version_uid = d.current_version_uid "
    "LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid "
    "WHERE c.version_uid IS NULL "
    "  AND (CAST(:project_uid AS text) IS NULL OR d.project_uid = CAST(:project_uid AS text)) "
    "  AND (CAST(:after AS text) IS NULL OR d.document_uid > CAST(:after AS text)) "
    "ORDER BY d.document_uid "
    "LIMIT :limit"
)
_COUNT_PROJECTS = text("SELECT count(*) FROM project")

#: `listVersions`. Every published version of one document, newest first.
#: `version_ordinal` is the document's own publication order and is monotonic per
#: document, so it orders these rows exactly and needs no tiebreaker: the schema's
#: `uq_document_version_ordinal` makes `(document_uid, version_ordinal)` unique. It is a
#: display value and not an identity -- `P02_SEAMS.md` section 2.2 -- and ordering by it
#: does not make it one.
_LIST_VERSIONS = text(
    "SELECT v.version_uid, v.document_uid, d.project_uid, v.version_ordinal,"
    "       d.display_title, d.section, v.media_type, v.byte_size,"
    "       v.sha256, v.page_count, v.published_at,"
    "       v.text_character_count, v.textless_pages, v.recognised_character_count,"
    "       c.project_stage, c.section_code, c.confirmed_by_user_uid, c.confirmed_at,"
    "       c.revision "
    "FROM document_version v JOIN document d ON d.document_uid = v.document_uid "
    "LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid "
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

#: `W59-SECTION-SEAL-01`. The version's chain, so a version addressed through a document and a
#: project is refused when either link names something else.
_SELECT_VERSION_CHAIN = text(
    "SELECT v.document_uid, d.project_uid FROM document_version v "
    "JOIN document d ON d.document_uid = v.document_uid WHERE v.version_uid = :version_uid"
)
#: The stored upload name, read only as review evidence inside this process. It is never
#: projected onto a record that leaves this package (see the module docstring).
_SELECT_SOURCE_FILENAME = text(
    "SELECT source_filename FROM document_version WHERE version_uid = :version_uid"
)
#: `CLASSIFICATION-CORRECTION-01`. Every classification read goes through the **current**
#: view -- the latest revision, the original confirmation while there is no correction -- so a
#: corrected version is read the same way by every consumer. Only the first-confirmation
#: insert below touches the base table.
_SELECT_CLASSIFICATION = text(
    "SELECT version_uid, project_stage, section_code, confirmed_by_user_uid, confirmed_at,"
    "       revision "
    "FROM version_classification_current WHERE version_uid = :version_uid"
)
#: One row per version, decided by the primary key. ``DO NOTHING`` waits for a concurrent
#: uncommitted insert of the same version and then returns no row, so the caller re-reads the
#: winner instead of overwriting it: the first confirmation stands.
_INSERT_CLASSIFICATION = text(
    "INSERT INTO document_version_classification "
    "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
    "VALUES (:version_uid, :project_stage, :section_code, :confirmed_by_user_uid) "
    "ON CONFLICT (version_uid) DO NOTHING "
    "RETURNING version_uid, project_stage, section_code, confirmed_by_user_uid, confirmed_at,"
    "          1 AS revision"
)
#: `CLASSIFICATION-CORRECTION-01`. A correction of one version is decided against its whole
#: history, so the original row is locked first: two corrections of the same version serialise
#: here, and the second reads the first's committed revision. ``FOR NO KEY UPDATE`` fires no
#: trigger (the original row's UPDATE/DELETE guard fires only on those statements) and does not
#: conflict with the ``FOR KEY SHARE`` a correction's foreign key takes on the same row. No row
#: means the version has no classification yet.
_LOCK_CLASSIFICATION = text(
    "SELECT version_uid FROM document_version_classification "
    "WHERE version_uid = :version_uid FOR NO KEY UPDATE"
)
#: Every revision of one version, oldest first: the original as revision 1 (no reason) and the
#: corrections after it (``version_classification_revision``).
_LIST_CLASSIFICATION_REVISIONS = text(
    "SELECT version_uid, revision, project_stage, section_code, actor_user_uid, reason, "
    "       decided_at "
    "FROM version_classification_revision WHERE version_uid = :version_uid ORDER BY revision"
)
#: Append revision ``:revision`` -- the caller computed it under the lock; the primary key
#: ``(version_uid, revision)`` and ``am_check_classification_correction_chain`` are the second
#: and third layers behind that.
_INSERT_CORRECTION = text(
    "INSERT INTO document_version_classification_correction "
    "(version_uid, revision, project_stage, section_code, corrected_by_user_uid, reason) "
    "VALUES (:version_uid, :revision, :project_stage, :section_code, :corrected_by_user_uid, "
    "        :reason) "
    "RETURNING version_uid, revision, project_stage, section_code, corrected_by_user_uid, "
    "          reason, corrected_at"
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


def _project_listing_record(row: Any) -> ProjectListingRecord:
    """One ``_LIST_PROJECTS`` row. ``count()`` never returns NULL, so this never coerces.

    The cast is to ``int`` because PostgreSQL's ``count`` is ``bigint``; psycopg already
    hands that back as a Python ``int``, and the call is here so the type is the record's
    own claim rather than the driver's.
    """
    project_uid, name, created_at, document_count = tuple(row)
    return ProjectListingRecord(
        project_uid=ProjectUid(project_uid),
        name=name,
        created_at=created_at,
        document_count=int(document_count),
    )


def _classification_record(row: Any) -> VersionClassificationRecord:
    version_uid, project_stage, section_code, confirmed_by, confirmed_at, revision = tuple(row)
    return VersionClassificationRecord(
        version_uid=VersionUid(version_uid),
        project_stage=project_stage,
        section_code=section_code,
        confirmed_by_user_uid=confirmed_by,
        confirmed_at=confirmed_at,
        revision=int(revision),
    )


def _revision_record(row: Any) -> ClassificationRevisionRecord:
    (
        version_uid, revision, project_stage, section_code, actor_user_uid, reason, decided_at,
    ) = tuple(row)
    return ClassificationRevisionRecord(
        version_uid=VersionUid(version_uid),
        revision=int(revision),
        project_stage=project_stage,
        section_code=section_code,
        actor_user_uid=actor_user_uid,
        reason=reason,
        decided_at=decided_at,
    )


def _placement_record(row: Any) -> CurrentVersionPlacementRecord:
    """One ``_LIST_SECTION_MEMBERS`` / ``_LIST_UNCLASSIFIED_CURRENT`` row, in column order."""
    (
        document_uid,
        project_uid,
        project_name,
        display_title,
        version_uid,
        version_ordinal,
        page_count,
        project_stage,
        section_code,
    ) = tuple(row)
    return CurrentVersionPlacementRecord(
        project_uid=ProjectUid(project_uid),
        project_name=project_name,
        document_uid=DocumentUid(document_uid),
        display_title=display_title,
        version_uid=VersionUid(version_uid),
        version_ordinal=int(version_ordinal),
        page_count=int(page_count),
        project_stage=project_stage,
        section_code=section_code,
    )


def _placements(
    session: Session,
    statement: Any,
    parameters: dict[str, Any],
    *,
    project_uid: ProjectUid | None,
    after: DocumentUid | None,
    limit: int,
) -> tuple[CurrentVersionPlacementRecord, ...]:
    """Run one placement statement with its optional filters and a checked page size."""
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="limit", constraint="type")
    if not 1 <= limit <= MAX_PLACEMENT_PAGE:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="limit", constraint=f"1..{MAX_PLACEMENT_PAGE}"
        )
    rows = session.execute(
        statement,
        {
            **parameters,
            "project_uid": None if project_uid is None else str(project_uid),
            "after": None if after is None else str(after),
            "limit": limit,
        },
    ).all()
    return tuple(_placement_record(row) for row in rows)


def _version_record(
    row: Any, manifest: tuple[ManifestEntry, ...]
) -> DocumentVersionRecord:
    """One ``document_version`` row, in the column order every SELECT here uses.

    Written once. ``get_version``, ``list_documents`` and ``list_versions`` project the
    same nineteen columns in the same order (`W59-SECTION-SEAL-01` added the four of the
    left-joined classification, `CLASSIFICATION-CORRECTION-01` its revision, and the join is
    now to the current view), and three hand-unpacked copies of that tuple
    would be three places for one of them to shift a column silently -- which is a fault
    the reader cannot see, because every value here is a string, an int or (``section``)
    possibly ``None``.
    """
    (
        version_uid,
        document_uid,
        project_uid,
        version_ordinal,
        display_title,
        section,
        media_type,
        byte_size,
        sha256,
        page_count,
        published_at,
        text_character_count,
        textless_pages,
        recognised_character_count,
        project_stage,
        section_code,
        confirmed_by_user_uid,
        confirmed_at,
        classification_revision,
    ) = tuple(row)
    # The left join yields all five or none: every column is NOT NULL in its own table.
    classification = (
        None
        if project_stage is None
        else VersionClassificationRecord(
            version_uid=VersionUid(version_uid),
            project_stage=project_stage,
            section_code=section_code,
            confirmed_by_user_uid=confirmed_by_user_uid,
            confirmed_at=confirmed_at,
            revision=int(classification_revision),
        )
    )
    return DocumentVersionRecord(
        version_uid=VersionUid(version_uid),
        document_uid=DocumentUid(document_uid),
        project_uid=ProjectUid(project_uid),
        version_ordinal=int(version_ordinal),
        display_title=display_title,
        section=section,
        media_type=media_type,
        byte_size=int(byte_size),
        sha256=sha256,
        page_count=int(page_count),
        published_at=published_at,
        manifest=manifest,
        text_character_count=(
            None if text_character_count is None else int(text_character_count)
        ),
        textless_pages=(
            None if textless_pages is None else tuple(int(page) for page in textless_pages)
        ),
        recognised_character_count=(
            None if recognised_character_count is None else int(recognised_character_count)
        ),
        classification=classification,
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

    def list_projects(self, session: Session) -> tuple[ProjectListingRecord, ...]:
        """`listProjects`: every project, newest first, each with its document count.

        One statement for the whole listing -- see ``_LIST_PROJECTS``. The count is the
        number of documents ``listDocuments`` would return for that project.
        """
        rows = session.execute(_LIST_PROJECTS).all()
        return tuple(_project_listing_record(row) for row in rows)

    # -- documents -----------------------------------------------------------

    def create_document(
        self,
        session: Session,
        project_uid: ProjectUid,
        display_title: str,
        section: str | None = None,
    ) -> DocumentUid:
        """Create a document inside a project. ``current_version_uid`` starts unset.

        ``section`` is one of the fifteen sections (``0024_version_classification``'s
        widened CHECK; ``0011_document_section`` wrote legacy's fourteen), or ``None`` for
        a document nobody has classified yet -- the CHECK constraint is the same
        vocabulary the frozen ``ProjectSection`` enum declares, and this method does not
        re-validate it: an unrecognised value is refused by the database, not silently
        accepted here and disagreed with there.
        """
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
                "section": section,
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
        text_character_count: int | None = None,
        textless_pages: tuple[int, ...] | None = None,
        recognised_character_count: int | None = None,
    ) -> VersionUid:
        """Insert one immutable version with its complete manifest.

        The version row and every manifest row are written inside the caller's unit of
        work, so a version never becomes visible without the manifest that makes it
        reproducible. The ordinal is derived here rather than supplied: it is a display
        value, and letting a caller choose one would make it look like a key.

        The document row is locked first (``_LOCK_DOCUMENT``), so concurrent publications
        into one document get consecutive ordinals instead of one of them failing on the
        unique ordinal. The lock is held to the caller's commit. A document that does not
        exist is refused as ``not_found`` before anything is written.

        The three counts of a portal bundle are all given or all absent; a partial set is
        refused here with the typed error the database would refuse it with, so a caller
        learns before a statement is issued.
        """
        given = (text_character_count, textless_pages, recognised_character_count)
        if any(value is None for value in given) and any(value is not None for value in given):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                aggregate_type="DocumentVersion",
                field="text_character_count",
                constraint="the three counts are all set or all absent",
            )
        if not entries:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR, role=ROLE_SOURCE_DOCUMENT
            )
        locked = session.execute(
            _LOCK_DOCUMENT, {"document_uid": str(document_uid)}
        ).first()
        if locked is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
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
                "text_character_count": text_character_count,
                "textless_pages": None if textless_pages is None else list(textless_pages),
                "recognised_character_count": recognised_character_count,
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

    # -- the section view's membership (`SECTION-READ-MODEL-01`) -------------

    def count_projects(self, session: Session) -> int:
        """How many projects exist -- one statement, no listing."""
        return int(session.execute(_COUNT_PROJECTS).scalar_one())

    def list_current_versions_in_section(
        self,
        session: Session,
        *,
        section_code: str,
        project_uid: ProjectUid | None = None,
        after: DocumentUid | None = None,
        limit: int = MAX_PLACEMENT_PAGE,
    ) -> tuple[CurrentVersionPlacementRecord, ...]:
        """The document sets whose **current** version is confirmed in ``section_code``.

        One statement over the whole deployment (or over one project, when ``project_uid``
        is given) instead of one ``list_documents`` per project. A set is a member when
        ``document.current_version_uid`` has a current classification
        (``version_classification_current``) with this code; an older version's confirmation,
        the legacy ``document.section``, a file name and a suggestion never make it one. At most ``limit`` records, ascending by
        ``document_uid``; pass the last record's ``document_uid`` as ``after`` for the next
        page, and a page shorter than ``limit`` ends the walk. An unknown project filter is
        an empty answer here -- a caller that must tell the two apart proves the project with
        :meth:`get_project` first. ``section_code`` is not re-validated: an unrecognised code
        matches nothing.
        """
        return _placements(
            session,
            _LIST_SECTION_MEMBERS,
            {"section_code": section_code},
            project_uid=project_uid,
            after=after,
            limit=limit,
        )

    def list_unclassified_current_versions(
        self,
        session: Session,
        *,
        project_uid: ProjectUid | None = None,
        after: DocumentUid | None = None,
        limit: int = MAX_PLACEMENT_PAGE,
    ) -> tuple[CurrentVersionPlacementRecord, ...]:
        """The document sets whose current version no expert has classified.

        Paged like :meth:`list_current_versions_in_section`. ``project_stage`` and
        ``section_code`` are ``None`` on every record: an unclassified version is not a
        sixteenth section.
        """
        return _placements(
            session,
            _LIST_UNCLASSIFIED_CURRENT,
            {},
            project_uid=project_uid,
            after=after,
            limit=limit,
        )

    # -- version classification (`W59-SECTION-SEAL-01`) ----------------------

    def get_version_in(
        self,
        session: Session,
        *,
        project_uid: ProjectUid,
        document_uid: DocumentUid,
        version_uid: VersionUid,
    ) -> DocumentVersionRecord:
        """One version addressed through its document and project, or ``not_found``.

        Each link is proved: an unknown project is ``Project``, a document of another
        project (or none) is ``Document``, and a version of another document (or none) is
        ``DocumentVersion`` -- exactly the answer an unknown identity gets, so a foreign
        version is never served under a path that does not own it.
        """
        self.get_project(session, project_uid)
        if self.require_document(session, document_uid) != project_uid:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
        chain = session.execute(
            _SELECT_VERSION_CHAIN, {"version_uid": str(version_uid)}
        ).first()
        if chain is None or tuple(chain)[0] != str(document_uid):
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")
        return self.get_version(session, version_uid)

    def source_filename_of(self, session: Session, version_uid: VersionUid) -> str | None:
        """The stored upload name, as section-review evidence only. Never projected."""
        return session.execute(
            _SELECT_SOURCE_FILENAME, {"version_uid": str(version_uid)}
        ).scalar_one_or_none()

    def get_classification(
        self, session: Session, version_uid: VersionUid
    ) -> VersionClassificationRecord | None:
        row = session.execute(
            _SELECT_CLASSIFICATION, {"version_uid": str(version_uid)}
        ).first()
        return None if row is None else _classification_record(row)

    def lock_classification(self, session: Session, version_uid: VersionUid) -> bool:
        """Lock the version's original classification row; ``False`` when it has none.

        The first step of a correction (`CLASSIFICATION-CORRECTION-01`): corrections of one
        version serialise on this lock until the holder's transaction ends, and the caller
        reads the history only after it holds it.
        """
        return (
            session.execute(_LOCK_CLASSIFICATION, {"version_uid": str(version_uid)}).first()
            is not None
        )

    def list_classification_revisions(
        self, session: Session, version_uid: VersionUid
    ) -> tuple[ClassificationRevisionRecord, ...]:
        """Every revision of one version's classification, oldest first; empty if unclassified."""
        rows = session.execute(
            _LIST_CLASSIFICATION_REVISIONS, {"version_uid": str(version_uid)}
        ).all()
        return tuple(_revision_record(row) for row in rows)

    def insert_correction(
        self,
        session: Session,
        *,
        version_uid: VersionUid,
        revision: int,
        project_stage: str,
        section_code: str,
        corrected_by_user_uid: str,
        reason: str,
    ) -> ClassificationRevisionRecord:
        """Append revision ``revision`` (>= 2). Never updates a row.

        The caller holds :meth:`lock_classification` and has decided the revision number from
        the history it read under it; a duplicate number, a gap or a no-op is refused by the
        database (primary key, ``am_check_classification_correction_chain``).
        """
        row = session.execute(
            _INSERT_CORRECTION,
            {
                "version_uid": str(version_uid),
                "revision": revision,
                "project_stage": project_stage,
                "section_code": section_code,
                "corrected_by_user_uid": corrected_by_user_uid,
                "reason": reason,
            },
        ).one()
        return _revision_record(row)

    def insert_classification(
        self,
        session: Session,
        *,
        version_uid: VersionUid,
        project_stage: str,
        section_code: str,
        confirmed_by_user_uid: str,
    ) -> VersionClassificationRecord | None:
        """Insert the first classification of a version, or ``None`` when one already exists.

        The row is append-only (``trg_document_version_classification_immutable``); this
        method never updates one. ``None`` means a row was already there -- possibly
        committed by a concurrent request a moment ago -- and the caller re-reads it.
        """
        row = session.execute(
            _INSERT_CLASSIFICATION,
            {
                "version_uid": str(version_uid),
                "project_stage": project_stage,
                "section_code": section_code,
                "confirmed_by_user_uid": confirmed_by_user_uid,
            },
        ).first()
        return None if row is None else _classification_record(row)

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
