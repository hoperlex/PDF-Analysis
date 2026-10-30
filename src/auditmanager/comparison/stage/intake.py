"""First-use admission for a ZIP set of stage-comparison PDFs.

The durable upload service must hold its database admission lock while it counts
active ZIP admissions and calls this function. The raw file is measured before
the reader gets it; the free-space budget includes both that file and the
reader's maximum temporary extraction. No member can leave the returned
context until the comparison PDF envelope has produced facts for every PDF.
"""

from __future__ import annotations

import contextlib
import hashlib
import tempfile
from collections.abc import Iterable, Iterator
from typing import BinaryIO, Final

from auditmanager.ingest.comparison_pdf.public import inspect_comparison_pdf
from auditmanager.ingest.comparison_zip import (
    DEFAULT_SET_POLICY, SET_TOTAL_BYTES, ExtractedSet, extract_pdf_set,
)
from auditmanager.shared.errors import DomainError, ErrorCode

from .limits import RAW_BATCH_BYTES

__all__ = [
    "MAX_RAW_ZIP_BYTES", "MIN_FREE_RESERVE_BYTES", "admit_stage_zip_stream",
    "open_stage_zip",
    "ChunkReader",
]

MAX_RAW_ZIP_BYTES: Final[int] = RAW_BATCH_BYTES
MIN_FREE_RESERVE_BYTES: Final[int] = 512 * 1024 * 1024
_READ_CHUNK: Final[int] = 1024 * 1024


class ChunkReader:
    """Expose a verified Blob chunk iterator as a bounded, nonseekable read."""

    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._chunks = iter(chunks)
        self._pending = memoryview(b"")

    def read(self, size: int) -> bytes:
        if size < 1:
            raise ValueError("read size must be positive")
        output = bytearray()
        while len(output) < size:
            if not self._pending:
                try:
                    self._pending = memoryview(next(self._chunks))
                except StopIteration:
                    break
            take = min(size - len(output), len(self._pending))
            output.extend(self._pending[:take])
            self._pending = self._pending[take:]
        return bytes(output)


def _refuse(constraint: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field="file", constraint=constraint)


def _check_budget(*, declared_bytes: int, active_admissions: int, free_bytes: int) -> None:
    if not 1 <= declared_bytes <= MAX_RAW_ZIP_BYTES:
        raise _refuse(f"raw_zip_bytes <= {MAX_RAW_ZIP_BYTES}")
    if active_admissions < 0 or free_bytes < 0:
        raise ValueError("admission counters cannot be negative")
    if active_admissions:
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_zip_admission"
        )
    # The raw spool and the reader's extracted files can coexist on the same
    # filesystem. Reserve both maxima before the reader creates a temp dir.
    if free_bytes < declared_bytes + SET_TOTAL_BYTES + MIN_FREE_RESERVE_BYTES:
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_zip_disk"
        )


def open_stage_zip(
    handle: BinaryIO,
    *,
    declared_bytes: int,
    active_admissions: int,
    free_bytes: int,
) -> ExtractedSet:
    """Return a fully validated set, or refuse before any member is published.

    ``active_admissions`` is counted from durable rows under an installation-wide
    database lock. The caller owns the lock until admission finishes, closes the
    returned set, and reconciles staged blobs after a refusal or cancellation.
    ``free_bytes`` is measured on the filesystem that holds the reader's
    temporary directory immediately before this call under that same lock.
    """
    _check_budget(
        declared_bytes=declared_bytes, active_admissions=active_admissions,
        free_bytes=free_bytes,
    )
    measured_bytes = handle.seek(0, 2)
    handle.seek(0)
    if measured_bytes != declared_bytes:
        raise _refuse("raw_zip_size_matches_declaration")
    accepted = extract_pdf_set(
        handle, policy=DEFAULT_SET_POLICY, envelope=inspect_comparison_pdf
    )
    if any(member.facts is None for member in accepted.members):
        accepted.close()
        raise RuntimeError("the comparison PDF envelope returned no facts")
    return accepted


@contextlib.contextmanager
def admit_stage_zip_stream(
    source: BinaryIO | ChunkReader,
    *,
    declared_bytes: int,
    declared_sha256: str,
    active_admissions: int,
    free_bytes: int,
) -> Iterator[ExtractedSet]:
    """Bound a nonseekable raw stream before extraction and clean both temp layers.

    The source is the staged raw object whose declared size and digest are in the
    durable file row. Reading stops as soon as it exceeds that declaration. The
    caller holds the database admission lock across this entire context and
    publishes members only after all have comparison PDF facts.
    """
    _check_budget(
        declared_bytes=declared_bytes, active_admissions=active_admissions,
        free_bytes=free_bytes,
    )
    digest = hashlib.sha256()
    measured = 0
    with tempfile.TemporaryFile(mode="w+b") as spool:
        while chunk := source.read(_READ_CHUNK):
            measured += len(chunk)
            if measured > declared_bytes:
                raise _refuse("raw_zip_size_matches_declaration")
            digest.update(chunk)
            spool.write(chunk)
        if measured != declared_bytes:
            raise _refuse("raw_zip_size_matches_declaration")
        if digest.hexdigest() != declared_sha256:
            raise _refuse("raw_zip_sha256_matches_declaration")
        spool.seek(0)
        with open_stage_zip(
            spool, declared_bytes=declared_bytes,
            active_admissions=active_admissions, free_bytes=free_bytes,
        ) as accepted:
            yield accepted
