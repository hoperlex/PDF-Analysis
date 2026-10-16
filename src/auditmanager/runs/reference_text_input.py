"""Read the saved W57b PDF text source for one current Run/Attempt.

This unserved seam holds caller-owned transaction locks across the Blob read.
It prepares reference input only; any later effect needs its own authority gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    RunScopedTextStage,
    SavedTextCustodyRefused,
    SuppliedTextSourceRefused,
    TextLayer,
    check_supplied_text_layer_bytes,
    select_run_text_layer_ref,
    sha256_hex,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, VersionUid
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id


_STAGE: Final[str] = "source_preparation"


@dataclass(frozen=True, slots=True)
class SavedReferenceTextInput:
    """Verified text layer and independently checked Version facts."""

    text_layer: TextLayer
    version_uid: str
    page_count: int


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved reference text cannot be bound to the current run",
        stage_id=_STAGE,
        reason=reason,
    )


def _one_source_stage(rows: tuple[StageResultRow, ...]) -> StageResultRow:
    matches = tuple(row for row in rows if row.stage_id == _STAGE)
    if len(matches) != 1:
        raise _refuse("source_stage_missing_or_duplicate")
    return matches[0]


def _read_exact(store: BlobStore, *, blob_id: str, sha256: str, size: int) -> bytes:
    try:
        chunks = store.open_stream(
            parse_blob_id(blob_id), expected_sha256=sha256, expected_size=size,
        )
        try:
            content = bytearray()
            for chunk in chunks:
                if type(chunk) is not bytes or len(content) + len(chunk) > size:
                    raise _refuse("saved_text_blob_size_mismatch")
                content.extend(chunk)
        finally:
            chunks.close()
    except (StorageError, IdentityError) as exc:
        raise _refuse("saved_text_blob_unreadable") from exc
    if len(content) != size:
        raise _refuse("saved_text_blob_size_mismatch")
    payload = bytes(content)
    if sha256_hex(payload) != sha256:
        raise _refuse("saved_text_blob_digest_mismatch")
    return payload


def load_saved_reference_text(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    max_input_bytes: int,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
    documents: DocumentRepository | None = None,
) -> SavedReferenceTextInput:
    """Return exact canonical text under two current-Attempt and row fences.

    The caller chooses a positive byte cap. This reader never infers a budget
    from a model or transforms an empty page into OCR text.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    document_repo = documents or DocumentRepository()

    job_repo.require_current(session, authority)
    if type(max_input_bytes) is not int or max_input_bytes < 1:
        raise _refuse("invalid_input_byte_ceiling")

    run = run_repo.get(session, authority.run_id)
    if run.run_id != authority.run_id or run.state != "running":
        raise _refuse("running_run_required")
    try:
        parsed_version = VersionUid.parse(run.version_uid)
    except IdentityError:
        raise _refuse("run_version_identity_invalid") from None
    version = document_repo.get_version(session, parsed_version)
    if (
        str(version.version_uid) != run.version_uid
        or str(version.project_uid) != run.project_uid
        or type(version.page_count) is not int
        or version.page_count < 1
    ):
        raise _refuse("run_version_mismatch")

    source_row = _one_source_stage(run_repo.stage_results(session, authority.run_id))
    stage = RunScopedTextStage(
        run_id=authority.run_id,
        stage_id=source_row.stage_id,
        stage_version=source_row.stage_version,
        status=source_row.status,
        artifacts=source_row.artifacts,
    )
    try:
        text_ref = select_run_text_layer_ref(run_id=authority.run_id, stage=stage)
    except SavedTextCustodyRefused as exc:
        raise _refuse("saved_text_reference_invalid") from exc
    if text_ref.size_bytes > max_input_bytes:
        raise _refuse("saved_text_input_too_large")

    payload = _read_exact(
        blob_store,
        blob_id=text_ref.blob_id,
        sha256=text_ref.sha256,
        size=text_ref.size_bytes,
    )
    try:
        text_layer = check_supplied_text_layer_bytes(
            version_uid=run.version_uid,
            expected_page_count=version.page_count,
            text_layer_ref=text_ref,
            supplied_bytes=payload,
        )
    except SuppliedTextSourceRefused as exc:
        raise _refuse("saved_text_integrity_invalid") from exc

    job_repo.require_current(session, authority)
    if run_repo.get(session, authority.run_id) != run:
        raise _refuse("run_changed_during_text_read")
    if document_repo.get_version(session, parsed_version) != version:
        raise _refuse("version_changed_during_text_read")
    if _one_source_stage(run_repo.stage_results(session, authority.run_id)) != source_row:
        raise _refuse("source_stage_changed_during_text_read")
    return SavedReferenceTextInput(text_layer, run.version_uid, version.page_count)


__all__ = ["SavedReferenceTextInput", "load_saved_reference_text"]
