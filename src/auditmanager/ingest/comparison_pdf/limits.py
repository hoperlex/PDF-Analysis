"""Temporary statistics intake for comparison PDF batches.

The application quotas on file count, set count, declared bytes, pages and
project bytes are raised to the database representation limits. Multipart
storage still accepts at most 10 000 parts per file, each 16 MiB. Active batch
counts remain a concurrency guard. Tests can lower constants to check refusals.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Final

from auditmanager.ingest.envelope import MAX_BYTES, MAX_PAGES
from auditmanager.shared.errors import DomainError, ErrorCode

from .names import group_key, name_hint

__all__ = [
    "ACTIVE_UPLOADS_PER_ACCOUNT",
    "ACTIVE_UPLOADS_PER_INSTALLATION",
    "MAX_BATCH_BYTES",
    "MAX_BATCH_PAGES",
    "MAX_FILES",
    "MAX_FILE_BYTES",
    "MAX_PROJECT_BYTES",
    "MAX_SETS",
    "PART_BYTES",
    "DeclaredFile",
    "check_declaration",
    "parts_needed",
]

GIB: Final[int] = 1024 * 1024 * 1024
MAX_FILES: Final[int] = 2**31 - 1
MAX_SETS: Final[int] = 2**31 - 1
MAX_BATCH_BYTES: Final[int] = 2**63 - 1
MAX_BATCH_PAGES: Final[int] = 2**31 - 1
MAX_PROJECT_BYTES: Final[int] = 2**63 - 1
#: The envelope's size bound for one PDF (250 MiB, R-116): the comparison path does not widen it.
MAX_FILE_BYTES: Final[int] = MAX_BYTES
ACTIVE_UPLOADS_PER_ACCOUNT: Final[int] = 1
ACTIVE_UPLOADS_PER_INSTALLATION: Final[int] = 2
#: ADR-0025 decision 10: every part but the last is exactly this long (16 MiB, under the proxy's body cap).
PART_BYTES: Final[int] = 16 * 1024 * 1024
#: ``comparison_upload_part.part_number`` is ``1..10000`` (S3's own bound); 250 MiB needs 16 at 16 MiB.
_MAX_PART_NUMBER: Final[int] = 10_000
assert MAX_PAGES == 2**31 - 1  # document_version.page_count INTEGER


class DeclaredFile:
    """One declared file as the limits read it: a name hint, a size and, optionally, a page count."""

    __slots__ = ("display_name", "size_bytes", "page_count")

    def __init__(self, display_name: str, size_bytes: int, page_count: int | None = None) -> None:
        self.display_name = display_name
        self.size_bytes = size_bytes
        self.page_count = page_count


def _refuse(constraint: str, *, field: str = "files") -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)


def parts_needed(size_bytes: int, part_bytes: int = PART_BYTES) -> int:
    """How many parts a file of ``size_bytes`` is sent in: every part but the last is ``part_bytes`` long."""
    if size_bytes < 1:
        raise ValueError("a file has at least one byte")
    return -(-size_bytes // part_bytes)


def name_sets(files: Iterable[DeclaredFile]) -> int:
    """How many document sets the names alone group the files into."""
    return len({group_key(name_hint(item.display_name)) for item in files})


def check_declaration(
    files: Sequence[DeclaredFile], *, project_stored_bytes: int
) -> None:
    """Refuse a batch that is over a decision-9 limit, with nothing created.

    ``project_stored_bytes`` is what the project already stores (sources, derived data and the declared bytes of
    batches in flight); the declared bytes are added to it, as the ADR says ("refused when the declared bytes
    plus the stored bytes pass it").
    """
    if len(files) > MAX_FILES:
        raise _refuse("comparison_files_limit")
    for item in files:
        if item.size_bytes > MAX_FILE_BYTES:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                field="content",
                constraint=f"byte_size <= {MAX_FILE_BYTES}",
            )
        if parts_needed(item.size_bytes) > _MAX_PART_NUMBER:  # pragma: no cover - bounded by the file size
            raise _refuse("comparison_batch_bytes_limit")
    declared_bytes = sum(item.size_bytes for item in files)
    if declared_bytes > MAX_BATCH_BYTES:
        raise _refuse("comparison_batch_bytes_limit")
    if sum(item.page_count or 0 for item in files) > MAX_BATCH_PAGES:
        raise _refuse("comparison_batch_pages_limit")
    if name_sets(files) > MAX_SETS:
        raise _refuse("comparison_sets_limit")
    if project_stored_bytes + declared_bytes > MAX_PROJECT_BYTES:
        raise _refuse("comparison_project_bytes_limit")
