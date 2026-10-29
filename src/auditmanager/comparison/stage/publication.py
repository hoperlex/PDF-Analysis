"""Resume a confirmed candidate through PDF custody and version publication.

The candidate's immutable facts contain the temporary upload token. Its blob
binding and a metadata row commit before any ZIP member reaches object storage.
The candidate stays `admitting` until the version and classification commit.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import (
    MANIFEST_ROLE_COMPARISON_PDF, ROLE_COMPARISON_PDF, UPLOAD_KIND_COMPARISON_PDF,
    DocumentRepository, ManifestEntry,
)
from auditmanager.ingest import domain_error_from_storage
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, DocumentUid, ProjectUid
from auditmanager.storage.public import (
    BlobMetadataRepository, BlobNotFoundError, BlobStore, StorageError, TemporaryBlob,
    VerifiedBlob, declare_blob, parse_blob_id,
)

from .admission import StageCandidateAdmissionService
from .intake import ChunkReader, admit_stage_zip_stream
from .uploads import StageUploadCandidateRow, StageUploadService

__all__ = ["StageCandidatePublicationService"]

_PDF = "application/pdf"


@dataclass(frozen=True, slots=True)
class _Work:
    candidate_id: str
    upload_id: str
    project_uid: str
    source_blob_id: str
    raw_sha256: str
    raw_size: int
    kind: str
    member_number: int
    name: str
    stage: str
    section: str
    designation: str
    actor: str
    document_uid: str | None
    blob_id: str
    sha256: str
    size: int
    page_count: int
    token: str


class StageCandidatePublicationService:
    def __init__(self, session_factory: sessionmaker[Session], store: BlobStore) -> None:
        self._sessions = session_factory
        self._store = store
        self._blobs = BlobMetadataRepository()
        self._documents = DocumentRepository()
        # The same process lease bounds ZIP extraction during admission and
        # publication. A dead process releases it while its DB intent remains.
        self._admission = StageCandidateAdmissionService(session_factory, store)

    def publish(self, *, candidate_id: str) -> StageUploadCandidateRow:
        with self._admission._lease():
            work, already = self._reserve(candidate_id)
            if already is not None:
                return already
            assert work is not None
            try:
                if work.kind == "zip":
                    self._ensure_zip_member(work)
                else:
                    self._ensure_plain_pdf(work)
            except StorageError as exc:
                raise domain_error_from_storage(exc) from None
            return self._finish(work)

    def _reserve(self, candidate_id: str) -> tuple[_Work | None, StageUploadCandidateRow | None]:
        with session_scope(self._sessions) as session:
            row = session.execute(
                text(
                    "SELECT c.state, c.pdf_facts, c.pdf_blob_id, c.member_number, "
                    "c.display_name, c.confirmed_stage, c.confirmed_section, c.designation, "
                    "c.confirmed_by_user_uid, c.document_uid, f.state, f.media_kind, "
                    "f.source_blob_id, f.declared_sha256, f.declared_size_bytes, "
                    "u.stage_upload_id, u.project_uid "
                    "FROM stage_upload_candidate c "
                    "JOIN stage_upload_file f ON f.stage_upload_file_id = c.stage_upload_file_id "
                    "JOIN stage_upload u ON u.stage_upload_id = f.stage_upload_id "
                    "WHERE c.stage_upload_candidate_id = :candidate FOR UPDATE OF c, f, u"
                ), {"candidate": candidate_id},
            ).first()
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadCandidate")
            (state, facts, bound_blob, number, name, stage, section, designation,
             actor, document_uid, file_state, kind, source_blob, raw_sha, raw_size,
             upload_id, project_uid) = row
            if state == "published":
                return None, self._view(session, str(upload_id), candidate_id)
            if state not in ("confirmed", "admitting") or file_state != "ready":
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_candidate_state")
            if not isinstance(facts, dict):
                raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_pdf")
            sha = str(facts["member_sha256"])
            size = int(facts["member_size"])
            token = str(facts["publication_token"])
            declaration = declare_blob(
                sha256=sha, size=size, role=ROLE_COMPARISON_PDF, media_type=_PDF,
            )
            if bound_blob is not None and str(bound_blob) != str(declaration.blob_id):
                raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_pdf")
            if kind == "pdf" and (
                str(source_blob) != str(declaration.blob_id)
                or str(raw_sha) != sha or int(raw_size) != size
            ):
                raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_raw")
            self._blobs.record_declared(session, declaration)
            session.execute(
                text(
                    "UPDATE stage_upload_candidate SET state = 'admitting', "
                    "pdf_blob_id = :blob, updated_at = clock_timestamp() "
                    "WHERE stage_upload_candidate_id = :candidate"
                ), {"candidate": candidate_id, "blob": str(declaration.blob_id)},
            )
            return _Work(
                candidate_id, str(upload_id), str(project_uid), str(source_blob),
                str(raw_sha), int(raw_size), str(kind), int(number), str(name),
                str(stage), str(section), str(designation), str(actor),
                None if document_uid is None else str(document_uid),
                str(declaration.blob_id), sha, size, int(facts["page_count"]), token,
            ), None

    def _ensure_plain_pdf(self, work: _Work) -> None:
        # Admission already streamed and checked the entire raw PDF. The raw
        # content-derived Blob is the PDF; a second object write adds no proof.
        with session_scope(self._sessions) as session:
            if not self._blobs.require(session, parse_blob_id(work.blob_id)).is_available:
                raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_pdf")
        published = self._store.inspect(parse_blob_id(work.blob_id))
        self._assert_content(work, published.sha256, published.size, published.media_type)

    def _ensure_zip_member(self, work: _Work) -> None:
        blob_id = parse_blob_id(work.blob_id)
        try:
            published = self._store.inspect(blob_id)
        except BlobNotFoundError:
            published = None
        if published is not None:
            self._assert_content(work, published.sha256, published.size, published.media_type)
            with session_scope(self._sessions) as session:
                self._blobs.record_verified(session, self._verified(work))
                self._blobs.mark_available(session, blob_id)
            return

        temporary = TemporaryBlob(
            upload_token=work.token, declared_sha256=work.sha256,
            declared_size=work.size, role=ROLE_COMPARISON_PDF, media_type=_PDF,
        )
        if not self._store.temporary_exists(temporary):
            try:
                free_bytes = shutil.disk_usage(tempfile.gettempdir()).free
            except OSError:
                raise DomainError(
                    ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_temp_disk",
                ) from None
            chunks = self._store.open_stream(
                parse_blob_id(work.source_blob_id),
                expected_sha256=work.raw_sha256, expected_size=work.raw_size,
            )
            try:
                with admit_stage_zip_stream(
                    ChunkReader(chunks), declared_bytes=work.raw_size,
                    declared_sha256=work.raw_sha256, active_admissions=0,
                    free_bytes=free_bytes,
                ) as accepted:
                    member = next(
                        (item for item in accepted.members
                         if item.ordinal + 1 == work.member_number), None,
                    )
                    if member is None or member.facts is None:
                        raise DomainError(
                            ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_pdf",
                        )
                    self._assert_content(work, member.sha256, member.size)
                    if member.facts.page_count != work.page_count:
                        raise DomainError(
                            ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_pdf",
                        )
                    with accepted.open(member) as source:
                        temporary = self._store.stage_temporary(
                            source, declared_sha256=work.sha256,
                            declared_size=work.size, role=ROLE_COMPARISON_PDF,
                            media_type=_PDF, upload_token=work.token,
                        )
            finally:
                chunks.close()

        verified = self._store.verify_temporary(temporary)
        self._assert_content(work, verified.sha256, verified.size)
        with session_scope(self._sessions) as session:
            self._blobs.record_verified(session, verified)
        published = self._store.publish(verified)
        self._assert_content(work, published.sha256, published.size, published.media_type)
        with session_scope(self._sessions) as session:
            self._blobs.mark_available(session, blob_id)

    @staticmethod
    def _verified(work: _Work) -> VerifiedBlob:
        return VerifiedBlob(
            blob_id=parse_blob_id(work.blob_id), upload_token=work.token,
            sha256=work.sha256, size=work.size, role=ROLE_COMPARISON_PDF,
            media_type=_PDF,
        )

    @staticmethod
    def _assert_content(
        work: _Work, sha256: str, size: int, media_type: str = _PDF,
    ) -> None:
        if sha256 != work.sha256 or size != work.size or media_type != _PDF:
            raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_pdf")

    def _finish(self, work: _Work) -> StageUploadCandidateRow:
        with session_scope(self._sessions) as session:
            row = session.execute(
                text(
                    "SELECT state, document_uid, pdf_blob_id FROM stage_upload_candidate "
                    "WHERE stage_upload_candidate_id = :candidate FOR UPDATE"
                ), {"candidate": work.candidate_id},
            ).one()
            if row[0] == "published":
                return self._view(session, work.upload_id, work.candidate_id)
            if row[0] != "admitting" or str(row[2]) != work.blob_id:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_candidate_state")
            if not self._blobs.require(session, parse_blob_id(work.blob_id)).is_available:
                raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_pdf")
            if row[1] is None:
                document_uid = self._documents.create_document(
                    session, ProjectUid.parse(work.project_uid), work.designation,
                    work.section,
                )
            else:
                document_uid = DocumentUid.parse(str(row[1]))
                if self._documents.require_document(session, document_uid) != ProjectUid.parse(
                    work.project_uid
                ):
                    raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
            version_uid = self._documents.publish_version(
                session, document_uid=document_uid, media_type=_PDF,
                byte_size=work.size, sha256=work.sha256, page_count=work.page_count,
                source_filename=work.name,
                entries=(ManifestEntry(
                    role=MANIFEST_ROLE_COMPARISON_PDF,
                    blob_id=parse_blob_id(work.blob_id), sha256=work.sha256,
                    size_bytes=work.size, media_type=_PDF,
                ),), upload_kind=UPLOAD_KIND_COMPARISON_PDF,
            )
            self._documents.insert_classification(
                session, version_uid=version_uid, project_stage=work.stage,
                section_code=work.section, confirmed_by_user_uid=work.actor,
            )
            session.execute(
                text(
                    "UPDATE stage_upload_candidate SET state = 'published', "
                    "document_uid = :document, version_uid = :version, "
                    "updated_at = clock_timestamp() "
                    "WHERE stage_upload_candidate_id = :candidate"
                ), {
                    "candidate": work.candidate_id, "document": str(document_uid),
                    "version": str(version_uid),
                },
            )
            session.execute(
                text(
                    "INSERT INTO audit_event "
                    "(audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
                    "VALUES (:event, 'stage.upload_candidate_published', "
                    "'StageUploadCandidate', :candidate, CAST(:payload AS jsonb))"
                ), {
                    "event": str(AuditEventId.new()), "candidate": work.candidate_id,
                    "payload": json.dumps({
                        "document_uid": str(document_uid), "version_uid": str(version_uid),
                        "pdf_blob_id": work.blob_id,
                    }, sort_keys=True),
                },
            )
            return self._view(session, work.upload_id, work.candidate_id)

    @staticmethod
    def _view(session: Session, upload_id: str, candidate_id: str) -> StageUploadCandidateRow:
        for item in StageUploadService._read(session, upload_id).candidates:
            if item.candidate_id == candidate_id:
                return item
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadCandidate")
