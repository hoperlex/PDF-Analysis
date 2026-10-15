"""Compose a caller-authorized XLSX read, projection and deterministic package.

The caller owns the export policy decision, one consistent read transaction and
verification of the supplied page labels and citations against their sources.
The references below preserve that provenance; they do not prove it themselves.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.exports.xlsx.projection import CitationRead, project_workbook
from auditmanager.exports.xlsx.query import read_xlsx_projection
from auditmanager.exports.xlsx.writer import render_xlsx


_OPERATION = "exportRunXlsx"


@dataclass(frozen=True, slots=True)
class ExportAuthorization:
    run_id: str
    principal_id: str
    operation: str
    decision: str
    decision_ref: str


@dataclass(frozen=True, slots=True)
class ExportSources:
    page_labels: Mapping[int, str]
    page_label_source_ref: str
    citations_by_finding: Mapping[str, tuple[CitationRead, ...]]
    citation_source_ref: str
    attribution: str


@dataclass(frozen=True, slots=True)
class PreparedXlsx:
    content: bytes
    content_type: str
    replacement_count: int
    decision_ref: str
    page_label_source_ref: str
    citation_source_ref: str


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_inputs(authorization: ExportAuthorization, sources: ExportSources) -> None:
    if (
        not isinstance(authorization, ExportAuthorization)
        or not _nonblank(authorization.run_id)
        or not _nonblank(authorization.principal_id)
        or authorization.operation != _OPERATION
        or authorization.decision != "allow"
        or not _nonblank(authorization.decision_ref)
    ):
        raise ValueError("xlsx_package_authorization_invalid")
    if (
        not isinstance(sources, ExportSources)
        or not _nonblank(sources.page_label_source_ref)
        or not _nonblank(sources.citation_source_ref)
        or not _nonblank(sources.attribution)
        or not isinstance(sources.page_labels, Mapping)
        or not isinstance(sources.citations_by_finding, Mapping)
    ):
        raise ValueError("xlsx_package_sources_invalid")
    for page, label in sources.page_labels.items():
        if type(page) is not int or page < 1 or not _nonblank(label):
            raise ValueError("xlsx_package_page_label_invalid")
    for finding_id, citations in sources.citations_by_finding.items():
        if (
            not _nonblank(finding_id)
            or not isinstance(citations, tuple)
            or any(not isinstance(citation, CitationRead) for citation in citations)
        ):
            raise ValueError("xlsx_package_citations_invalid")


def prepare_xlsx_package(
    session: Session,
    *,
    authorization: ExportAuthorization,
    sources: ExportSources,
) -> PreparedXlsx | None:
    """Return XLSX bytes for an explicitly permitted run, or ``None`` if absent.

    This function never grants a role, decides an export state, starts or commits
    a transaction, chooses a filename, or repairs missing source material.
    ``authorization`` must come from the sealed policy; source references and
    values must come from the caller's verified page/citation readers.
    """
    _validate_inputs(authorization, sources)
    read = read_xlsx_projection(
        session,
        authorization.run_id,
        page_labels=sources.page_labels,
        citations_by_finding=sources.citations_by_finding,
        attribution=sources.attribution,
    )
    if read is None:
        return None
    rendered = render_xlsx(project_workbook(*read))
    return PreparedXlsx(
        content=rendered.content,
        content_type=rendered.content_type,
        replacement_count=rendered.replacement_count,
        decision_ref=authorization.decision_ref,
        page_label_source_ref=sources.page_label_source_ref,
        citation_source_ref=sources.citation_source_ref,
    )


__all__ = [
    "ExportAuthorization",
    "ExportSources",
    "PreparedXlsx",
    "prepare_xlsx_package",
]
