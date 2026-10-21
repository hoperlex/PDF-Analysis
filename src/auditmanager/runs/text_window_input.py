"""Read W56b saved TEXT windows under one current Run/Attempt.

This unserved read service returns checked input only. The caller owns the
transaction, whose Run → Job → Attempt → Lease locks are held during the Blob
read. Any later provider effect needs a fresh authority check and journal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    CheckedRunTextWindowInput,
    ChunkPreflightError,
    RunScopedTextStage,
    SavedTextCustodyRefused,
    check_run_text_window_input,
    select_run_text_layer_ref,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, VersionUid
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id


_STAGE: Final[str] = "source_preparation"


@dataclass(frozen=True, slots=True)
class SavedTextWindowInput:
    """One read result, with no reservation for a later model effect."""

    checked: CheckedRunTextWindowInput


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved text windows cannot be bound to the current run",
        stage_id=_STAGE,
        reason=reason,
    )


def _one_source_stage(rows: tuple[StageResultRow, ...]) -> StageResultRow:
    matches = tuple(row for row in rows if row.stage_id == _STAGE)
    if len(matches) != 1:
        raise _refuse("source_stage_missing_or_duplicate")
    return matches[0]


def _stage_claim(run_id: str, row: StageResultRow) -> RunScopedTextStage:
    return RunScopedTextStage(
        run_id=run_id,
        stage_id=row.stage_id,
        stage_version=row.stage_version,
        status=row.status,
        artifacts=row.artifacts,
    )


def _read_exact_text(store: BlobStore, *, ref_blob_id: str, sha256: str, size: int) -> bytes:
    try:
        chunks = store.open_stream(
            parse_blob_id(ref_blob_id), expected_sha256=sha256, expected_size=size,
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
    return bytes(content)


def load_saved_text_windows(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    max_input_bytes: int,
    max_chunk_characters: int,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
    documents: DocumentRepository | None = None,
) -> SavedTextWindowInput:
    """Read saved TEXT bytes once, fenced by current Attempt and exact rows.

    Both ceilings are explicit inputs. The caller must derive the document-text
    character ceiling from an approved W56b request budget; this service does
    not infer or authorize one.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    document_repo = documents or DocumentRepository()

    job_repo.require_current(session, authority)
    if type(max_input_bytes) is not int or max_input_bytes < 1:
        raise _refuse("invalid_input_byte_ceiling")
    if type(max_chunk_characters) is not int or max_chunk_characters < 1:
        raise _refuse("invalid_text_character_ceiling")

    run = run_repo.get(session, authority.run_id)
    if run.run_id != authority.run_id or run.state != "running":
        raise _refuse("running_run_required")
    try:
        version = document_repo.get_version(session, VersionUid.parse(run.version_uid))
    except IdentityError:
        raise _refuse("run_version_identity_invalid") from None
    if (
        str(version.version_uid) != run.version_uid
        or str(version.project_uid) != run.project_uid
        or type(version.page_count) is not int
        or version.page_count < 1
    ):
        raise _refuse("run_version_mismatch")
    source_row = _one_source_stage(run_repo.stage_results(session, authority.run_id))
    stage = _stage_claim(authority.run_id, source_row)
    try:
        text_ref = select_run_text_layer_ref(run_id=authority.run_id, stage=stage)
    except SavedTextCustodyRefused as exc:
        raise _refuse("saved_text_reference_invalid") from exc
    if text_ref.size_bytes > max_input_bytes:
        raise _refuse("saved_text_input_too_large")

    payload = _read_exact_text(
        blob_store, ref_blob_id=text_ref.blob_id,
        sha256=text_ref.sha256, size=text_ref.size_bytes,
    )
    try:
        checked = check_run_text_window_input(
            run_id=authority.run_id,
            version_uid=run.version_uid,
            expected_page_count=version.page_count,
            stage=stage,
            supplied_text_bytes=payload,
            max_chunk_characters=max_chunk_characters,
        )
    except SavedTextCustodyRefused as exc:
        raise _refuse("saved_text_integrity_invalid") from exc
    except ChunkPreflightError as exc:
        raise _refuse(exc.reason) from exc

    job_repo.require_current(session, authority)
    if run_repo.get(session, authority.run_id) != run:
        raise _refuse("run_changed_during_text_read")
    if document_repo.get_version(session, VersionUid.parse(run.version_uid)) != version:
        raise _refuse("version_changed_during_text_read")
    if _one_source_stage(run_repo.stage_results(session, authority.run_id)) != source_row:
        raise _refuse("source_stage_changed_during_text_read")
    return SavedTextWindowInput(checked)


__all__ = ["SavedTextWindowInput", "load_saved_text_windows"]
