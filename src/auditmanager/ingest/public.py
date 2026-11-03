"""Cross-context surface of the ingest boundary."""

from __future__ import annotations

from auditmanager.ingest.commands import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.ingest.envelope import PDFIUM_LOCK as PDFIUM_LOCK  # W55B-GEOMETRY-01: the process's one PDFium lock, for analysis's page renderer
from auditmanager.ingest.intake_mode import intake_relaxed as intake_relaxed  # REVIEW-FIX-BOUNDS-1102: the deployment's one intake-mode reader
from auditmanager.ingest.intake_mode import quota as quota  # the ADR figure, or the lifted one when the deployment is relaxed

__all__ = [
    "CommandReplay",
    "CommandRepository",
    "CommandStarted",
    "intake_relaxed",
    "payload_fingerprint",
    "quota",
]
