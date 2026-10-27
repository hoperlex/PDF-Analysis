"""What the use cases of a comparison upload answer with: plain records, no transport type.

The composition root's adapters map these onto the contract's models (``ComparisonUpload``,
``ComparisonUploadProposal``, ...); nothing here knows a wire shape, and nothing carries a bucket, an object key, a
path or a multipart token (the token is write-once state of the file row and never leaves it).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "FileView",
    "OrderPageView",
    "OrderView",
    "PartReceiptView",
    "ProposalView",
    "ProposedFileView",
    "SetView",
    "UploadView",
]


@dataclass(frozen=True, slots=True)
class FileView:
    file_id: str
    display_name: str
    size_bytes: int
    sha256: str
    state: str
    parts_staged: int
    set_id: str | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class UploadView:
    upload_id: str
    project_uid: str
    state: str
    part_size_bytes: int
    declared_files: int
    declared_bytes: int
    created_at: datetime
    updated_at: datetime
    #: ``None`` for a listing row (the files are read with the batch).
    files: tuple[FileView, ...] | None


@dataclass(frozen=True, slots=True)
class PartReceiptView:
    file_id: str
    part_number: int
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ProposedFileView:
    file_id: str
    position: int
    version_label: str


@dataclass(frozen=True, slots=True)
class SetView:
    set_id: str
    state: str
    files: tuple[ProposedFileView, ...]
    designation: str | None
    existing_document_uid: str | None
    project_stage: str | None
    section_code: str | None
    warnings: tuple[str, ...]
    failure_reason: str | None
    document_uid: str | None


@dataclass(frozen=True, slots=True)
class ProposalView:
    upload_id: str
    state: str
    sets: tuple[SetView, ...]


@dataclass(frozen=True, slots=True)
class OrderView:
    order_id: str
    document_uid: str
    revision_no: int
    version_uids: tuple[str, ...]
    source: str
    created_at: datetime
    created_by: str


@dataclass(frozen=True, slots=True)
class OrderPageView:
    items: tuple[OrderView, ...]
    #: The oldest revision this page holds when older ones remain, else ``None``.
    next_before_revision: int | None
