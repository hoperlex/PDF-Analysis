"""Ingest: the admission envelope, the single-PDF upload command, and reconciliation.

    from auditmanager.ingest import IngestService, Reconciler

    service = IngestService(store)
    project = service.create_project("Q3 review")
    outcome = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=pdf_bytes,
        source_filename="annual_report.pdf",
        display_title="Annual report",
        idempotency_key=IdempotencyKey("upload-2026-09-10-0001"),
    )
    outcome.version.source.blob_id      # the only handle to the stored bytes

The accepted envelope is one unencrypted PDF, at most 25 MiB, one to thirty pages, every
page carrying extractable embedded text. Everything outside it is ``validation_failed``
with a ``field`` and a ``constraint``, raised before any service is touched, so nothing
is published. **OCR is never substituted for a missing text layer.**

The publication order and the reconciliation model are documented in
:mod:`auditmanager.ingest.service` and :mod:`auditmanager.ingest.reconciliation`. The
short version: the database is canonical, and an interrupted publication leaves an
adoptable orphan object rather than a half-written version.
"""

from __future__ import annotations

from .commands import (
    COMMAND_MACHINE,
    COMMAND_TYPE_UPLOAD,
    CommandRecord,
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from .envelope import (
    ACCEPTED_MEDIA_TYPE,
    MAX_BYTES,
    MAX_PAGES,
    MAX_SOURCE_FILENAME,
    MIN_PAGES,
    PDF_MAGIC,
    AdmissionReport,
    probe,
    validate_source_filename,
)
from .failures import domain_error_from_storage
from .reconciliation import (
    MissingObject,
    OrphanObject,
    Reconciler,
    ReconciliationReport,
)
from .service import IngestService

__all__ = [
    "ACCEPTED_MEDIA_TYPE",
    "COMMAND_MACHINE",
    "COMMAND_TYPE_UPLOAD",
    "MAX_BYTES",
    "MAX_PAGES",
    "MAX_SOURCE_FILENAME",
    "MIN_PAGES",
    "PDF_MAGIC",
    "AdmissionReport",
    "CommandRecord",
    "CommandReplay",
    "CommandRepository",
    "CommandStarted",
    "IngestService",
    "MissingObject",
    "OrphanObject",
    "Reconciler",
    "ReconciliationReport",
    "domain_error_from_storage",
    "payload_fingerprint",
    "probe",
    "validate_source_filename",
]
