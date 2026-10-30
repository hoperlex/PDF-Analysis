"""Bounded ZIP admission for version comparison (HOTFIX-VERSIONS-1030).

Reuse the reviewed ZIP reader, including rejection of __MACOSX, unsafe names and
non-PDF entries. Validate every PDF before declaring any durable upload. Files
then use the existing multipart/blob reconciliation and keyed completion path.
No archive path is an identity; child receipts use an opaque request namespace
and the member's stable ordinal. Retry resumes the same upload and file rows.
"""
from __future__ import annotations

import hashlib
import tempfile
from typing import TYPE_CHECKING, BinaryIO

from sqlalchemy import text

from auditmanager.ingest.comparison_zip import SetPolicy, extract_pdf_set
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

if TYPE_CHECKING:
    from .service import ComparisonUploadService
    from .views import UploadView

MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_PDFS = 100
ZIP_POLICY = SetPolicy(total_bytes=MAX_EXPANDED_BYTES)


def _key(request_key: str, operation: str) -> str:
    return 'zip-' + hashlib.sha256((request_key + '\x00' + operation).encode()).hexdigest()


def _refuse(constraint: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field='file', constraint=constraint)


def import_zip(
    service: ComparisonUploadService, *, project_uid: str, source: BinaryIO,
    user_uid: str, actor_label: str, idempotency_key: str, archive_name: str | None = None,
) -> UploadView:
    from .service import DeclaredFileRequest

    # This single bounded read also works for a nonseekable request stream.
    raw = source.read(MAX_ARCHIVE_BYTES + 1)
    if not raw or len(raw) > MAX_ARCHIVE_BYTES:
        raise _refuse('comparison_zip_raw_max_16_mib')
    source_digest = hashlib.sha256(raw).hexdigest()
    # The installation lock bounds temporary expansion across concurrent callers;
    # the nested PDF service uses a different creation lock and owns its own commits.
    with session_scope(service._factory) as admission:
        admission.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'), {'key': 'comparison_zip_import:v1'})
        import shutil
        if shutil.disk_usage(tempfile.gettempdir()).free < MAX_EXPANDED_BYTES * 2:
            raise _refuse('comparison_zip_temporary_space')
        with tempfile.TemporaryFile() as archive:
            archive.write(raw)
            archive.seek(0)
            # Use the same PDF envelope as ordinary comparison intake. read_pdf
            # also checks stamps, so a late refusal cannot publish a partial set.
            def envelope(handle: BinaryIO):
                result = service._read(handle)
                return result.facts
            with extract_pdf_set(archive, policy=ZIP_POLICY, envelope=envelope) as accepted:
                if len(accepted.members) > MAX_PDFS:
                    raise _refuse('comparison_zip_max_100_pdfs')
                files = [DeclaredFileRequest(m.display_name[-255:], m.size, m.sha256, m.facts.page_count if m.facts else None)
                         for m in accepted.members]
                upload = service.create_upload(
                    project_uid=project_uid, files=files, user_uid=user_uid, actor_label=actor_label,
                    idempotency_key=_key(idempotency_key, 'declare'), source_sha256=source_digest,
                )
                # The declaration preserves input order. Receipt keys contain no
                # filenames, paths, user labels or model output.
                declared = upload.files or ()
                if len(declared) != len(accepted.members):
                    raise RuntimeError('ZIP declaration does not match its accepted members')
                for member, file in zip(accepted.members, declared, strict=True):
                    if file.sha256 != member.sha256 or file.size_bytes != member.size:
                        raise RuntimeError('ZIP member differs from its durable declaration')
                    if file.state == 'verified':
                        continue
                    with accepted.open(member) as pdf:
                        part = 1
                        while chunk := pdf.read(upload.part_size_bytes):
                            service.put_part(
                                upload_id=upload.upload_id, file_id=file.file_id, part_number=part,
                                content=chunk, user_uid=user_uid,
                                idempotency_key=_key(idempotency_key, f'{member.ordinal}:part:{part}'),
                            )
                            part += 1
                    service.complete_file(
                        upload_id=upload.upload_id, file_id=file.file_id, user_uid=user_uid,
                        idempotency_key=_key(idempotency_key, f'{member.ordinal}:complete'),
                    )
                return service.get_upload(upload_id=upload.upload_id)
