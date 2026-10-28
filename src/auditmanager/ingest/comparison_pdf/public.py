"""Cross-context surface of the comparison upload (`CMP-INGEST-01`): what the composition root and the batch
operations (`CMP-INGEST-02`) import. Everything else in this package is reached through here or not at all."""

from __future__ import annotations

from .envelope import COMPARISON_POLICY, ComparisonEnvelopePolicy, inspect_comparison_pdf
from .limits import (
    ACTIVE_UPLOADS_PER_ACCOUNT,
    ACTIVE_UPLOADS_PER_INSTALLATION,
    MAX_BATCH_BYTES,
    MAX_BATCH_PAGES,
    MAX_FILES,
    MAX_PROJECT_BYTES,
    MAX_SETS,
    PART_BYTES,
    parts_needed,
)
from .orders import ComparisonVersionOrderService
from .proposal import FileEntry, SetProposal, propose_set
from .reading import PdfReading, read_pdf
from .repository import ACTIVE_BATCH_STATES, ComparisonUploadRepository
from .service import (
    RETRYABLE_FILE_REASONS,
    ComparisonStore,
    ComparisonUploadService,
    ConfirmedFile,
    DeclaredFileRequest,
    require_expert,
)
from .views import (
    FileView,
    OrderPageView,
    OrderView,
    PartReceiptView,
    ProposalView,
    ProposedFileView,
    SetView,
    UploadView,
)

__all__ = [
    "ACTIVE_BATCH_STATES",
    "ACTIVE_UPLOADS_PER_ACCOUNT",
    "ACTIVE_UPLOADS_PER_INSTALLATION",
    "COMPARISON_POLICY",
    "MAX_BATCH_BYTES",
    "MAX_BATCH_PAGES",
    "MAX_FILES",
    "MAX_PROJECT_BYTES",
    "MAX_SETS",
    "PART_BYTES",
    "RETRYABLE_FILE_REASONS",
    "ComparisonEnvelopePolicy",
    "ComparisonStore",
    "ComparisonUploadRepository",
    "ComparisonUploadService",
    "ComparisonVersionOrderService",
    "ConfirmedFile",
    "DeclaredFileRequest",
    "FileEntry",
    "FileView",
    "OrderPageView",
    "OrderView",
    "PartReceiptView",
    "PdfReading",
    "ProposalView",
    "ProposedFileView",
    "SetProposal",
    "SetView",
    "UploadView",
    "inspect_comparison_pdf",
    "parts_needed",
    "propose_set",
    "read_pdf",
    "require_expert",
]
