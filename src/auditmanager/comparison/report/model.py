"""The vocabulary of the report lane (`CMP-VC-REPORT-01`): kinds, sources, states, stages, marks, artifacts, limits and the registered refusals.

Nothing here reads a database or calls a model. The states and stages are those of the CHECKs of migration ``0040`` and of the
contract's enums; the edges are the table trigger's (``EDGES``), restated here so the lane can walk a report from where it is to
where its job says it is without a forbidden step.
"""

from __future__ import annotations

from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ARTIFACT_KINDS",
    "ARTIFACT_PDF",
    "ARTIFACT_SOURCE_MD",
    "ARTIFACT_TEXT",
    "CONFLICT_REPORT_STATE",
    "CONFLICT_SUMMARY_UNAVAILABLE",
    "CONSTRAINT_SOURCE_INVALID",
    "EDGES",
    "FAIL_CHECK",
    "FAIL_PDF",
    "FAIL_PDF_CHECK",
    "FAIL_SOURCE",
    "KINDS",
    "KIND_ANALYTIC",
    "KIND_CLIENT",
    "LIVE_STATES",
    "MARKS",
    "MAX_SOURCE_BYTES",
    "METHOD",
    "RECORDED_LABEL",
    "SOURCES",
    "SOURCE_SERIES_SUMMARY",
    "SOURCE_UPLOADED_MD",
    "STAGES",
    "STAGE_CLIENT_WRITING",
    "STAGE_COMPOSITION",
    "STAGE_INTAKE",
    "STAGE_PDF_WRITING",
    "STAGE_TRANSITION_ANALYSIS",
    "STAGE_VERIFICATION",
    "STATES",
    "TERMINAL_STATES",
    "UNCONFIRMED_LABEL",
    "WORK_KIND",
    "conflict",
    "path_between",
    "source_invalid",
]

METHOD: Final[str] = "report"
#: The executor work kind of a report (``ExecutorWorkKind``), routed in «Назначения» (ADR-0025 decision 17).
WORK_KIND: Final[str] = "comparison_report"

KIND_CLIENT: Final[str] = "client"
KIND_ANALYTIC: Final[str] = "analytic"
KINDS: Final[tuple[str, ...]] = (KIND_CLIENT, KIND_ANALYTIC)
SOURCE_SERIES_SUMMARY: Final[str] = "series_summary"
SOURCE_UPLOADED_MD: Final[str] = "uploaded_md"
SOURCES: Final[tuple[str, ...]] = (SOURCE_SERIES_SUMMARY, SOURCE_UPLOADED_MD)

#: The states of ``comparison_report`` (the CHECK of migration ``0040``).
STATES: Final[tuple[str, ...]] = ("draft", "queued", "running", "paused", "completed", "partial", "failed", "cancelled")
LIVE_STATES: Final[frozenset[str]] = frozenset({"queued", "running", "paused"})
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"completed", "partial", "failed", "cancelled"})
#: The only state changes the table's trigger allows (the same list as migration ``0040`` ``EDGES``).
EDGES: Final[frozenset[tuple[str, str]]] = frozenset({
    ("draft", "queued"), ("draft", "cancelled"), ("queued", "running"), ("queued", "paused"), ("queued", "failed"),
    ("queued", "cancelled"), ("running", "paused"), ("running", "completed"), ("running", "partial"),
    ("running", "failed"), ("running", "cancelled"), ("paused", "queued"), ("paused", "running"),
    ("paused", "cancelled"), ("partial", "queued"), ("failed", "queued"), ("cancelled", "queued"),
})

STAGE_INTAKE: Final[str] = "intake"
STAGE_TRANSITION_ANALYSIS: Final[str] = "transition_analysis"
STAGE_VERIFICATION: Final[str] = "verification"
STAGE_COMPOSITION: Final[str] = "composition"
STAGE_CLIENT_WRITING: Final[str] = "client_writing"
STAGE_PDF_WRITING: Final[str] = "pdf_writing"
STAGES: Final[tuple[str, ...]] = (
    STAGE_INTAKE, STAGE_TRANSITION_ANALYSIS, STAGE_VERIFICATION, STAGE_COMPOSITION, STAGE_CLIENT_WRITING,
    STAGE_PDF_WRITING,
)

#: «✓ ⟳ ✗ ·» (the contract's ``ComparisonReportUnitMark``).
MARKS: Final[tuple[str, ...]] = ("done", "running", "failed", "pending")

ARTIFACT_PDF: Final[str] = "report_pdf"
ARTIFACT_SOURCE_MD: Final[str] = "source_md"
#: The text a PDF is written from (the client view or the analytic report as JSON): «Пересобрать PDF» reads it, no model.
ARTIFACT_TEXT: Final[str] = "report_text"
ARTIFACT_KINDS: Final[tuple[str, ...]] = (ARTIFACT_PDF, ARTIFACT_SOURCE_MD, ARTIFACT_TEXT)

#: The original's limit for an uploaded summary (`md_report/settings.py:22`, ``MAX_UPLOAD_BYTES`` 20 MiB); the router refuses a body over it.
MAX_SOURCE_BYTES: Final[int] = 20 * 1024 * 1024

#: Printed on every page of a PDF (ADR-0025 decisions 16 and 20; plan ``A-7``): the text is model output no engineer has confirmed.
UNCONFIRMED_LABEL: Final[str] = "Текст подготовлен моделью, инженером не подтверждено"
#: Printed instead of nothing when the answers were recorded test answers (the counterpart of the original's «ТЕСТОВЫЙ ОТВЕТ»).
RECORDED_LABEL: Final[str] = "Записанный (тестовый) ответ, не ответ рабочей модели"

#: Registered refusals (`CMP-SEAL-C2` section 3): reasons under existing codes, no new error code.
CONFLICT_REPORT_STATE: Final[str] = "comparison_report_state"
CONFLICT_SUMMARY_UNAVAILABLE: Final[str] = "comparison_summary_unavailable"
CONSTRAINT_SOURCE_INVALID: Final[str] = "comparison_report_source_invalid"

#: Why a report (its job) failed: a code, never free text (``ck_comparison_report_failure_reason``).
FAIL_CHECK: Final[str] = "report_check_failed"
FAIL_PDF: Final[str] = "pdf_failed"
FAIL_PDF_CHECK: Final[str] = "pdf_check_failed"
FAIL_SOURCE: Final[str] = "report_source_unavailable"


def conflict(reason: str) -> DomainError:
    """``409 conflict`` with a registered ``conflict_reason``."""
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


def source_invalid() -> DomainError:
    """``422 validation_failed`` (field ``content``): an uploaded MD file that is empty, over 20 MiB, not UTF-8 or without a
    transition headed «## N. … A → B» (``error-codes.json``)."""
    return DomainError(ErrorCode.VALIDATION_FAILED, field="content", constraint=CONSTRAINT_SOURCE_INVALID)


def path_between(current: str, target: str) -> list[str]:
    """The states to pass from ``current`` to ``target`` along the table's edges (excluding ``current``), by breadth first search;
    ``[]`` when they are equal; ``ValueError`` when the target cannot be reached (the caller must not write it then)."""
    if current == target:
        return []
    seen = {current}
    queue: list[tuple[str, list[str]]] = [(current, [])]
    while queue:
        state, path = queue.pop(0)
        for source, destination in sorted(EDGES):
            if source != state or destination in seen:
                continue
            if destination == target:
                return [*path, destination]
            seen.add(destination)
            queue.append((destination, [*path, destination]))
    raise ValueError(f"a report cannot go from {current} to {target}")
