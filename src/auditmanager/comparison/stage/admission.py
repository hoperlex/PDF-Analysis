"""Admit a verified raw PDF/ZIP into proposed stage candidates atomically.

No PDF member is published here. Candidate confirmation later reopens a member,
rechecks its facts and stores the validated PDF before binding a document.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest import domain_error_from_storage
from auditmanager.ingest.comparison_pdf.public import COMPARISON_POLICY, inspect_comparison_pdf
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import StageUploadCandidateId
from auditmanager.storage.public import BlobStore, StorageError, new_multipart_token, parse_blob_id

from .intake import ChunkReader, MIN_FREE_RESERVE_BYTES, admit_stage_zip_stream
from .uploads import StageUploadCandidateRow, StageUploadService

__all__ = ["StageCandidateAdmissionService"]

_ADMISSION_LOCK = "stage_upload:admission"
_PROCESS_LEASE = "stage_upload:admission_process"
_PDF_READ_CHUNK = 1024 * 1024


@dataclass(frozen=True, slots=True)
class _Proposal:
    number: int
    display_name: str
    facts: dict[str, object]


class StageCandidateAdmissionService:
    def __init__(self, session_factory: sessionmaker[Session], store: BlobStore) -> None:
        self._sessions = session_factory
        self._store = store
        bind = session_factory.kw.get("bind")
        if bind is None:
            raise ValueError("stage admission needs a database bind for its process lease")
        self._engine: Engine = bind.engine

    def admit(self, *, upload_id: str, file_id: str) -> tuple[StageUploadCandidateRow, ...]:
        """Reserve the sole installation admission, validate every PDF, then commit all candidates."""
        with self._lease():
            return self._admit_under_lease(upload_id=upload_id, file_id=file_id)

    @contextmanager
    def _lease(self) -> Iterator[None]:
        """A session advisory lock spans extraction and dies with the process.

        A short transaction marks the file `admitting`; this separate connection
        proves whether that process is still active. Releasing it is explicit,
        so a pooled connection cannot retain a phantom lock.
        """
        with self._engine.connect() as lease:
            held = bool(lease.execute(
                text("SELECT pg_try_advisory_lock(hashtext(:lock))"), {"lock": _PROCESS_LEASE},
            ).scalar_one())
            lease.commit()
            if not held:
                raise DomainError(
                    ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_zip_admission",
                )
            try:
                yield
            finally:
                released = bool(lease.execute(
                    text("SELECT pg_advisory_unlock(hashtext(:lock))"), {"lock": _PROCESS_LEASE},
                ).scalar_one())
                lease.commit()
                if not released:
                    raise RuntimeError("the stage admission process lease was lost")

    def _admit_under_lease(
        self, *, upload_id: str, file_id: str,
    ) -> tuple[StageUploadCandidateRow, ...]:
        with session_scope(self._sessions) as session:
            session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock))"), {"lock": _ADMISSION_LOCK})
            # The lease proves that no prior admission process is alive. Its
            # transaction may have committed `admitting` before the process died.
            interrupted = session.execute(
                text(
                    "UPDATE stage_upload_file SET state = 'received', updated_at = clock_timestamp() "
                    "WHERE state = 'admitting' RETURNING stage_upload_id"
                ),
            ).scalars().all()
            if interrupted:
                session.execute(
                    text(
                        "UPDATE stage_upload SET state = 'uploading', updated_at = clock_timestamp() "
                        "WHERE state = 'admitting'"
                    ),
                )
            row = session.execute(
                text(
                    "SELECT u.state, f.state, f.media_kind, f.display_name, f.declared_size_bytes, "
                    "f.declared_sha256, f.source_blob_id "
                    "FROM stage_upload_file f JOIN stage_upload u ON u.stage_upload_id = f.stage_upload_id "
                    "WHERE u.stage_upload_id = :upload AND f.stage_upload_file_id = :file "
                    "FOR UPDATE OF u, f"
                ), {"upload": upload_id, "file": file_id},
            ).first()
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadFile")
            upload_state, file_state, kind, display_name, size, digest, blob_id = row
            if file_state == "ready":
                return self._candidates(session, upload_id, file_id)
            if upload_state != "uploading" or file_state != "received" or blob_id is None:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_state")
            active = int(session.execute(
                text("SELECT count(*) FROM stage_upload_file WHERE state = 'admitting'"),
            ).scalar_one())
            if active:
                raise DomainError(
                    ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_zip_admission",
                )
            session.execute(
                text(
                    "UPDATE stage_upload_file SET state = 'admitting', updated_at = clock_timestamp() "
                    "WHERE stage_upload_file_id = :file"
                ), {"file": file_id},
            )
            session.execute(
                text(
                    "UPDATE stage_upload SET state = 'admitting', updated_at = clock_timestamp() "
                    "WHERE stage_upload_id = :upload"
                ), {"upload": upload_id},
            )

        try:
            try:
                free_bytes = shutil.disk_usage(tempfile.gettempdir()).free
            except OSError:
                raise DomainError(
                    ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_temp_disk",
                ) from None
            chunks = self._store.open_stream(
                parse_blob_id(str(blob_id)), expected_sha256=str(digest), expected_size=int(size),
            )
            try:
                reader = ChunkReader(chunks)
                if kind == "zip":
                    proposals = self._zip_proposals(
                        reader, size=int(size), digest=str(digest), free_bytes=free_bytes,
                    )
                else:
                    proposals = self._pdf_proposal(
                        reader, name=str(display_name), size=int(size),
                        digest=str(digest), free_bytes=free_bytes,
                    )
            finally:
                chunks.close()
            with session_scope(self._sessions) as session:
                state = session.execute(
                    text(
                        "SELECT state FROM stage_upload_file WHERE stage_upload_file_id = :file "
                        "AND stage_upload_id = :upload FOR UPDATE"
                    ), {"file": file_id, "upload": upload_id},
                ).scalar_one_or_none()
                if state != "admitting":
                    raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_state")
                for proposal in proposals:
                    session.execute(
                        text(
                            "INSERT INTO stage_upload_candidate "
                            "(stage_upload_candidate_id, stage_upload_file_id, member_number, "
                            "display_name, pdf_facts) "
                            "VALUES (:candidate, :file, :number, :name, CAST(:facts AS jsonb))"
                        ),
                        {
                            "candidate": str(StageUploadCandidateId.new()), "file": file_id,
                            "number": proposal.number, "name": proposal.display_name,
                            "facts": json.dumps({
                                **proposal.facts, "publication_token": new_multipart_token(),
                            }),
                        },
                    )
                session.execute(
                    text(
                        "UPDATE stage_upload_file SET state = 'ready', updated_at = clock_timestamp() "
                        "WHERE stage_upload_file_id = :file"
                    ), {"file": file_id},
                )
                self._settle_upload(session, upload_id)
                return self._candidates(session, upload_id, file_id)
        except StorageError as exc:
            self._reset(upload_id, file_id, failed=False)
            raise domain_error_from_storage(exc) from None
        except DomainError as exc:
            self._reset(upload_id, file_id, failed=exc.code is ErrorCode.VALIDATION_FAILED)
            raise
        except Exception:
            self._reset(upload_id, file_id, failed=False)
            raise

    @staticmethod
    def _zip_proposals(
        reader: ChunkReader, *, size: int, digest: str, free_bytes: int,
    ) -> tuple[_Proposal, ...]:
        with admit_stage_zip_stream(
            reader, declared_bytes=size, declared_sha256=digest,
            active_admissions=0, free_bytes=free_bytes,
        ) as accepted:
            proposals: list[_Proposal] = []
            for member in accepted.members:
                if member.facts is None:
                    raise RuntimeError("a ZIP member reached the candidate boundary without PDF facts")
                proposals.append(_Proposal(
                    member.ordinal + 1, member.base_name,
                    {**asdict(member.facts), "member_sha256": member.sha256, "member_size": member.size},
                ))
            return tuple(proposals)

    @staticmethod
    def _pdf_proposal(
        reader: ChunkReader, *, name: str, size: int, digest: str, free_bytes: int,
    ) -> tuple[_Proposal, ...]:
        if size > COMPARISON_POLICY.max_bytes:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="file",
                constraint=f"pdf_bytes <= {COMPARISON_POLICY.max_bytes}",
            )
        if free_bytes < size + MIN_FREE_RESERVE_BYTES:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_pdf_disk",
            )
        measured = 0
        checksum = hashlib.sha256()
        with tempfile.TemporaryFile(mode="w+b") as spool:
            while chunk := reader.read(_PDF_READ_CHUNK):
                measured += len(chunk)
                if measured > size:
                    raise DomainError(
                        ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_raw",
                    )
                checksum.update(chunk)
                spool.write(chunk)
            if measured != size or checksum.hexdigest() != digest:
                raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_raw")
            spool.seek(0)
            facts = inspect_comparison_pdf(spool)
        return (_Proposal(
            1, name.rsplit("/", 1)[-1] or "document.pdf",
            {**asdict(facts), "member_sha256": digest, "member_size": size},
        ),)

    def _reset(self, upload_id: str, file_id: str, *, failed: bool) -> None:
        with session_scope(self._sessions) as session:
            session.execute(
                text(
                    "UPDATE stage_upload_file SET state = :state, failure_reason = :reason, "
                    "updated_at = clock_timestamp() WHERE stage_upload_file_id = :file "
                    "AND stage_upload_id = :upload AND state = 'admitting'"
                ),
                {"state": "failed" if failed else "received",
                 "reason": "validation_failed" if failed else None,
                 "file": file_id, "upload": upload_id},
            )
            self._settle_upload(session, upload_id)

    @staticmethod
    def _settle_upload(session: Session, upload_id: str) -> None:
        pending, failed = session.execute(
            text(
                "SELECT count(*) FILTER (WHERE state IN ('declared', 'receiving', 'received', 'admitting')), "
                "count(*) FILTER (WHERE state = 'failed') "
                "FROM stage_upload_file WHERE stage_upload_id = :upload"
            ), {"upload": upload_id},
        ).one()
        state = "uploading" if pending else "failed" if failed else "completed"
        session.execute(
            text(
                "UPDATE stage_upload SET state = :state, updated_at = clock_timestamp() "
                "WHERE stage_upload_id = :upload AND state = 'admitting'"
            ), {"state": state, "upload": upload_id},
        )

    @staticmethod
    def _candidates(
        session: Session, upload_id: str, file_id: str,
    ) -> tuple[StageUploadCandidateRow, ...]:
        upload = StageUploadService._read(session, upload_id)
        return tuple(item for item in upload.candidates if item.file_id == file_id)
