"""The contract-shaped dictionaries of a report (`CMP-VC-REPORT-01`): ``ComparisonReport``, its parts, its artifacts and the list page.

Pure: no database. The adapter in the composition root validates them with the generated models. The **state a reader sees is derived from the
job**, the one source of truth for what is queued, running, paused, failed or cancelled; the stored ``state`` of the report is kept in step by the
service and the handler, and a reader that finds it behind (a crash between a command and its follow-up) still sees the right one:

========================  =================================================================================
the job is                the report reads
========================  =================================================================================
(none)                    the stored state: ``draft`` (or ``cancelled`` for a draft that was cancelled)
``queued`` ``running``    the same; ``paused`` and ``cancelled`` likewise; ``failed`` with the job's reason
``completed``             ``completed`` when a PDF was written, else ``partial`` («неполный результат»)
========================  =================================================================================
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.report.model import ARTIFACT_PDF, ARTIFACT_SOURCE_MD
from auditmanager.comparison.report.repository import ArtifactRow, PartRow, ReportRepository, ReportRow

__all__ = ["derived_state", "part_dict", "report_dict"]

#: The artifact kinds the contract shows (``ComparisonReportArtifactKind``); the stored text of the PDF is internal.
_PUBLIC_ARTIFACTS: Final[tuple[str, ...]] = (ARTIFACT_PDF, ARTIFACT_SOURCE_MD)
_FACT_KEYS: Final[tuple[str, ...]] = ("found", "confirmed", "contradicted", "unconfirmed")


def derived_state(row: ReportRow, job: Mapping[str, Any] | None, artifacts: Sequence[ArtifactRow]) -> str:
    """The state of the report a reader sees (see the module docstring)."""
    if job is None:
        return row.state
    state = str(job["state"])
    if state == "completed":
        return "completed" if ReportRepository.latest(artifacts, ARTIFACT_PDF) is not None else "partial"
    return state


def part_dict(part: PartRow) -> dict[str, Any]:
    out: dict[str, Any] = {"transition_id": part.transition_id}
    for name in ("analysis", "verification", "selection"):
        value = getattr(part, name)
        if value is not None:
            out[name] = value
    facts = part.facts or {}
    if all(isinstance(facts.get(k), int) for k in _FACT_KEYS):
        out["facts"] = {k: int(facts[k]) for k in _FACT_KEYS}
    for name in ("warnings", "points", "questions"):
        value = getattr(part, name)
        if value is not None:
            out[name] = int(value)
    return out


def report_dict(
    row: ReportRow, parts: Sequence[PartRow], artifacts: Sequence[ArtifactRow], job: Mapping[str, Any] | None, *, document_uid: str | None = None,
) -> dict[str, Any]:
    """``ComparisonReport``. ``job`` is the contract's ``ComparisonAiJob`` (``AiJobView.as_dict()``) of a started report."""
    state = derived_state(row, job, artifacts)
    out: dict[str, Any] = {
        "report_id": row.report_id, "series_id": row.series_id, "project_uid": row.project_uid, "document_uid": document_uid or row.document_uid,
        "kind": row.kind, "source": row.source, "state": state, "reuse": row.reuse,
        "parts": [part_dict(p) for p in parts],
        "artifacts": [
            {"kind": a.kind, "size_bytes": a.size_bytes, "sha256": a.sha256, "created_at": a.created_at}
            for kind in _PUBLIC_ARTIFACTS for a in [ReportRepository.latest(artifacts, kind)] if a is not None
        ],
        "created_at": row.created_at, "updated_at": row.updated_at,
    }
    if row.stage is not None:
        out["stage"] = row.stage
    if job is None:
        out["estimate"] = dict(row.estimate)
    else:
        out["job"] = dict(job)
    if row.source_name is not None:
        out["source_name"] = row.source_name
    if row.prepared_from_id is not None:
        out["prepared_from_id"] = row.prepared_from_id
    reason = (job or {}).get("failure_reason") if state == "failed" else None
    if state == "failed":
        out["failure_reason"] = reason or row.failure_reason or "report_failed"
    finished = (job or {}).get("finished_at") if state in ("completed", "partial", "failed", "cancelled") else None
    if state in ("completed", "partial", "failed", "cancelled"):
        out["finished_at"] = finished or row.finished_at or row.updated_at
    return out
