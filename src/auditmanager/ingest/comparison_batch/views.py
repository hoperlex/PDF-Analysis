"""What the listing answers with: plain records, no transport type (the adapter maps them onto the contract)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from auditmanager.ingest.comparison_pdf.public import UploadView

__all__ = ["UploadPageView"]


@dataclass(frozen=True, slots=True)
class UploadPageView:
    """A page of a project's batches, newest first, each without its files (``UploadView.files`` is ``None``).

    ``next_after`` is the ``(created_at, id)`` of the last row when older rows remain (the keyset the next page
    starts after), else ``None``.
    """

    items: tuple[UploadView, ...]
    next_after: tuple[datetime, str] | None
