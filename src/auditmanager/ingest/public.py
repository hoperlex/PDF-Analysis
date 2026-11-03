"""Cross-context surface of the ingest boundary."""

from __future__ import annotations

from auditmanager.ingest.commands import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
# The comparison context's stage intake (`comparison.stage*`) reaches the ingest context through here (ALR-05): the
# comparison PDF envelope and expert check, the ZIP set reader and the storage-failure mapping. The composition root
# keeps importing the sub-packages' own `public` modules, which ALR-05 exempts.
from auditmanager.ingest.comparison_pdf.public import COMPARISON_POLICY as COMPARISON_POLICY
from auditmanager.ingest.comparison_pdf.public import inspect_comparison_pdf as inspect_comparison_pdf
from auditmanager.ingest.comparison_pdf.public import require_expert as require_expert
from auditmanager.ingest.comparison_zip import DEFAULT_SET_POLICY as DEFAULT_SET_POLICY
from auditmanager.ingest.comparison_zip import SET_TOTAL_BYTES as SET_TOTAL_BYTES
from auditmanager.ingest.comparison_zip import ExtractedSet as ExtractedSet
from auditmanager.ingest.comparison_zip import extract_pdf_set as extract_pdf_set
from auditmanager.ingest.envelope import PDFIUM_LOCK as PDFIUM_LOCK  # W55B-GEOMETRY-01: the process's one PDFium lock, for analysis's page renderer
from auditmanager.ingest.failures import domain_error_from_storage as domain_error_from_storage
from auditmanager.ingest.intake_mode import intake_relaxed as intake_relaxed  # REVIEW-FIX-BOUNDS-1102: the deployment's one intake-mode reader
from auditmanager.ingest.intake_mode import quota as quota  # the ADR figure, or the lifted one when the deployment is relaxed

__all__ = [
    "COMPARISON_POLICY",
    "DEFAULT_SET_POLICY",
    "SET_TOTAL_BYTES",
    "CommandReplay",
    "CommandRepository",
    "CommandStarted",
    "ExtractedSet",
    "domain_error_from_storage",
    "extract_pdf_set",
    "inspect_comparison_pdf",
    "intake_relaxed",
    "payload_fingerprint",
    "quota",
    "require_expert",
]
