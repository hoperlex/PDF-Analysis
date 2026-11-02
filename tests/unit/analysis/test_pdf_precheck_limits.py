"""The precheck child runs under finite limits unless a caller says otherwise.

`REVIEW-FIX-BOUNDS-1102` (finding S6-01): ``af581631`` set every limit of ``PdfPrecheckLimits`` to the
integer ceiling, so the child ran with no memory cap and no clock. The sandbox is back; the counts
follow the upload envelope (see ``tests/unit/ingest/test_intake_mode.py`` for the relaxed mode).
"""

from __future__ import annotations

import dataclasses

from auditmanager.analysis.stages.pdf_precheck import PdfPrecheckLimits

MiB = 1024 * 1024


def test_the_child_sandbox_is_the_reported_one() -> None:
    limits = PdfPrecheckLimits()
    assert limits.address_space_bytes == 1536 * MiB
    assert (limits.cpu_seconds, limits.wall_seconds, limits.startup_seconds, limits.page_seconds) == (1200, 1800, 45, 180)
    assert (limits.max_line_bytes, limits.max_output_bytes) == (32 * MiB, 256 * MiB)


def test_the_counts_are_the_envelope_quotas_of_a_strict_deployment() -> None:
    limits = PdfPrecheckLimits()
    assert (limits.max_pages, limits.max_page_characters, limits.max_document_characters) == (500, 200_000, 20_000_000)


def test_no_limit_is_the_integer_ceiling() -> None:
    for field in dataclasses.fields(PdfPrecheckLimits):
        assert getattr(PdfPrecheckLimits(), field.name) < 2**31 - 1, field.name
