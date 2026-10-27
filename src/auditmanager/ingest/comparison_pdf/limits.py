"""The limits of ADR-0025 decision 9 for a comparison upload, as typed refusals before the first part.

The numbers are the architect's defaults (``CMP-ADR-01``), revisable only by a dated addendum to the ADR
(decision 27), so they are constants here and **not** schema bounds: the contract carries structure only.

====================== =============================== =====================================================
quantity               value                           refusal (``validation_failed``, field ``files``)
====================== =============================== =====================================================
files per batch        10 000                          ``comparison_files_limit``
document sets          100                             ``comparison_sets_limit``
declared bytes         8 GiB                           ``comparison_batch_bytes_limit``
declared pages         10 000                          ``comparison_batch_pages_limit``
project stored bytes   8 GiB (stored + declared)       ``comparison_project_bytes_limit``
one file               250 MiB (the envelope's)        ``byte_size <= 262144000`` on ``content``
active batches         1 per account, 2 per install    ``conflict`` / ``comparison_upload_active``
====================== =============================== =====================================================

Each is refused **before the first part and before any row exists** (a refusal has nothing to roll back). The
checks run cheapest first, so a batch that breaks several is refused for the first on the list. A file name is
never echoed.

**Sets.** A batch's real grouping is read from the stamps, after the bytes arrive. At declaration only the
names exist, so the limit is checked on the *name* grouping (the folder, else the base name:
:func:`auditmanager.ingest.comparison_pdf.names.group_key`), the original's own limit of 100 projects. The stamp
grouping is held to the same number when files are placed (:mod:`auditmanager.ingest.comparison_pdf.service`).
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
MAX_FILES: Final[int] = 10_000
MAX_SETS: Final[int] = 100
MAX_BATCH_BYTES: Final[int] = 8 * GIB
MAX_BATCH_PAGES: Final[int] = 10_000
MAX_PROJECT_BYTES: Final[int] = 8 * GIB
#: The envelope's size bound for one PDF (250 MiB, R-116): the comparison path does not widen it.
MAX_FILE_BYTES: Final[int] = MAX_BYTES
ACTIVE_UPLOADS_PER_ACCOUNT: Final[int] = 1
ACTIVE_UPLOADS_PER_INSTALLATION: Final[int] = 2
#: ADR-0025 decision 10: every part but the last is exactly this long (16 MiB, under the proxy's body cap).
PART_BYTES: Final[int] = 16 * 1024 * 1024
#: ``comparison_upload_part.part_number`` is ``1..10000`` (S3's own bound); 250 MiB needs 16 at 16 MiB.
_MAX_PART_NUMBER: Final[int] = 10_000
assert MAX_PAGES == 500  # the declaration's own bound (``ComparisonUploadFileDeclaration.page_count``)


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
