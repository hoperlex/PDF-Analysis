"""Ingest: the admission envelope, the portal-bundle upload command, and reconciliation.

    from auditmanager.ingest import IngestService, Reconciler

    service = IngestService(store)
    project = service.create_project("Q3 review")
    with open("annual_report.zip", "rb") as bundle:      # a portal bundle: the PDF and its files
        outcome = service.upload_bundle(
            project_uid=project.project_uid,
            content=bundle,
            source_filename="annual_report.zip",
            display_title="Annual report",
            idempotency_key=IdempotencyKey("upload-2026-09-10-0001"),
        )
    outcome.version.source.blob_id      # the only handle to the stored PDF

The accepted envelope is one portal bundle -- a ZIP holding an unencrypted PDF of at most
250 MiB and one to five hundred pages, the portal's block list and its recognised-text file
(and optionally an HTML rendering, kept as a digest only, and a stamp audit) -- entered with
``IngestService.upload_bundle``. Until the last step of ``W55B-INGEST-01`` a bare PDF is still
accepted through ``upload_single_pdf``, under the same limits and with every page carrying
extractable embedded text. Everything outside the envelope is ``validation_failed`` with a
``field`` and a ``constraint``, raised before any service is touched, so nothing is
published. **OCR is always marked, and never substituted for a missing text layer.**

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
from .bundle_archive import ZIP_MAGICS, looks_like_zip
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
    Reconciler,
    ReconciliationReport,
    UnattributedBlob,
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
    "ZIP_MAGICS",
    "AdmissionReport",
    "CommandRecord",
    "CommandReplay",
    "CommandRepository",
    "CommandStarted",
    "IngestService",
    "MissingObject",
    "Reconciler",
    "ReconciliationReport",
    "UnattributedBlob",
    "domain_error_from_storage",
    "looks_like_zip",
    "payload_fingerprint",
    "probe",
    "validate_source_filename",
]
