"""Helpers of the comparison-upload suites: the corpus, a declared batch, a file sent in parts, a padded PDF.

Nothing here decides a result: every assertion is made by the tests, against the database and against the bucket through
a plain ``boto3`` client that does not go through the adapter under test.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from auditmanager.ingest.comparison_pdf.public import (
    PART_BYTES,
    ComparisonUploadService,
    DeclaredFileRequest,
    UploadView,
)
ROOT = Path(__file__).resolve().parents[4]
CORPUS = ROOT / "fixtures" / "comparison"
LABEL = "Эксперт Проверкин"
EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})


def corpus(path: str) -> bytes:
    return (CORPUS / path).read_bytes()


def vs1() -> dict[str, bytes]:
    return {f"v{n}.pdf": corpus(f"vs1/v{n}.pdf") for n in range(1, 6)}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def declare(name: str, data: bytes, *, page_count: int | None = None) -> DeclaredFileRequest:
    return DeclaredFileRequest(display_name=name, size_bytes=len(data), sha256=sha256(data), page_count=page_count)


def create(service: ComparisonUploadService, project_uid: str, files: Mapping[str, bytes], *, user: str,
           key: str = "create-1") -> UploadView:
    return service.create_upload(
        project_uid=project_uid, files=[declare(name, data) for name, data in files.items()],
        user_uid=user, actor_label=LABEL, idempotency_key=key,
    )


def parts_of(data: bytes, size: int = PART_BYTES) -> list[bytes]:
    return [data[offset : offset + size] for offset in range(0, len(data), size)]


def send(service: ComparisonUploadService, upload_id: str, file_id: str, data: bytes, *, key: str, user: str,
         only: Sequence[int] | None = None) -> None:
    """Send the parts of one file (all, or only the numbered ones) under keys ``<key>-p<n>``."""
    for number, part in enumerate(parts_of(data), start=1):
        if only is not None and number not in only:
            continue
        service.put_part(upload_id=upload_id, file_id=file_id, part_number=number, content=part,
                         user_uid=user, idempotency_key=f"{key}-p{number}")


def complete(service: ComparisonUploadService, upload_id: str, file_id: str, *, key: str, user: str):
    return service.complete_file(upload_id=upload_id, file_id=file_id, user_uid=user, idempotency_key=key)


def upload_batch(service: ComparisonUploadService, project_uid: str, files: Mapping[str, bytes], *, user: str,
                 key: str = "batch") -> UploadView:
    """Declare, send and complete every file; return the batch as the service reads it afterwards."""
    view = create(service, project_uid, files, key=f"{key}-create", user=user)
    by_name = {item.display_name: item.file_id for item in view.files or ()}
    for index, (name, data) in enumerate(files.items()):
        send(service, view.upload_id, by_name[name], data, key=f"{key}-f{index}", user=user)
        complete(service, view.upload_id, by_name[name], key=f"{key}-f{index}-done", user=user)
    return service.get_upload(upload_id=view.upload_id)


def padded_pdf(size: int) -> bytes:
    """A valid one-page PDF of at least ``size`` bytes: an unreferenced stream of deterministic bytes pads it."""
    chunk = hashlib.sha256(b"padding").digest()
    padding = (chunk * (size // len(chunk) + 1))[:size]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
        b"<< /Length 60 >>\nstream\nBT /F1 12 Tf 50 50 Td (A page with a text layer, padded.) Tj ET\nendstream",
        b"<< /Length %d >>\nstream\n" % len(padding) + padding + b"\nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


def table(session: Any, sql: str, **params: Any) -> list[tuple[Any, ...]]:
    from sqlalchemy import text

    return [tuple(row) for row in session.execute(text(sql), params).all()]
