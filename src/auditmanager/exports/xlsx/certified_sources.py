"""Project W57a's certified citation partitions into W57b XLSX sources.

The input DTOs must come from the verified readers in one caller-owned read
transaction. Constructing those DTOs by hand grants no custody or export
authority. This module performs no database or object-store access.
"""

from __future__ import annotations

from types import MappingProxyType

from auditmanager.exports.xlsx.package import ExportSources
from auditmanager.exports.xlsx.preflight import VerifiedXlsxRunSource
from auditmanager.exports.xlsx.projection import CitationRead
from auditmanager.exports.xlsx.source_labels import VerifiedPageLabels


class XlsxCertifiedSourcesRefused(ValueError):
    """The supplied run, page labels or citation partitions do not align."""


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _citations(partition: object) -> tuple[CitationRead, ...]:
    observation_id = getattr(partition, "finding_observation_id", None)
    count = getattr(partition, "citation_count", None)
    citations = getattr(partition, "citations", None)
    if (
        not _nonblank(observation_id)
        or type(count) is not int
        or not 0 <= count <= 5
        or not isinstance(citations, tuple)
        or len(citations) != count
    ):
        raise XlsxCertifiedSourcesRefused("xlsx_citation_partition_incomplete")
    projected: list[CitationRead] = []
    for ordinal, citation in enumerate(citations, start=1):
        designation = getattr(citation, "designation", None)
        clause = getattr(citation, "clause_number", None)
        quote = getattr(citation, "quote", None)
        if (
            type(getattr(citation, "citation_ordinal", None)) is not int
            or citation.citation_ordinal != ordinal
            or not _nonblank(designation)
            or not _nonblank(quote)
            or (clause is not None and not isinstance(clause, str))
            or getattr(citation, "state", None) not in {"verified", "rebound"}
        ):
            raise XlsxCertifiedSourcesRefused("xlsx_citation_partition_incomplete")
        projected.append(CitationRead(
            document=designation,
            clause=clause or "",
            quote=quote,
        ))
    return tuple(projected)


def sources_from_certified_reads(
    run_source: VerifiedXlsxRunSource,
    citation_read: object,
    *,
    attribution: str,
) -> ExportSources:
    """Carry every certified citation into the existing XLSX package input.

    Canonical citations precede member citations; each reader-certified row
    stays visible, including repeats. An empty tuple is produced only from
    partitions that explicitly certify zero. No finding or norm decision is
    made here.
    """
    read_run_id = getattr(citation_read, "run_id", None)
    read_version_uid = getattr(citation_read, "version_uid", None)
    read_state = getattr(citation_read, "run_state", None)
    read_snapshot_id = getattr(citation_read, "norms_snapshot_id", None)
    read_set_id = getattr(citation_read, "norm_retrieval_set_id", None)
    findings = getattr(citation_read, "findings", None)
    if (
        not isinstance(run_source, VerifiedXlsxRunSource)
        or not _nonblank(attribution)
        or not _nonblank(run_source.run_id)
        or not _nonblank(run_source.version_uid)
        or not _nonblank(getattr(citation_read, "project_uid", None))
        or not _nonblank(read_snapshot_id)
        or not _nonblank(read_set_id)
        or run_source.run_id != read_run_id
        or run_source.version_uid != read_version_uid
        or run_source.state != read_state
        or run_source.state not in {"published", "partial"}
        or not isinstance(run_source.page_labels, VerifiedPageLabels)
        or run_source.page_labels.version_uid != run_source.version_uid
        or not _nonblank(run_source.page_labels.source_ref)
    ):
        raise XlsxCertifiedSourcesRefused("xlsx_certified_source_identity_mismatch")
    if not isinstance(findings, tuple):
        raise XlsxCertifiedSourcesRefused("xlsx_citation_findings_incomplete")

    by_finding: dict[str, tuple[CitationRead, ...]] = {}
    for finding in findings:
        finding_uid = getattr(finding, "finding_uid", None)
        canonical = getattr(finding, "canonical", None)
        merged = getattr(finding, "merged_observations", None)
        if (
            not _nonblank(finding_uid)
            or finding_uid in by_finding
            or not isinstance(merged, tuple)
        ):
            raise XlsxCertifiedSourcesRefused("xlsx_citation_findings_incomplete")
        partitions = (canonical, *merged)
        seen_observations: set[str] = set()
        rows: list[CitationRead] = []
        for partition in partitions:
            projected = _citations(partition)
            observation_id = partition.finding_observation_id
            if observation_id in seen_observations:
                raise XlsxCertifiedSourcesRefused("xlsx_citation_partition_duplicate")
            seen_observations.add(observation_id)
            rows.extend(projected)
        by_finding[finding_uid] = tuple(rows)

    return ExportSources(
        page_labels=run_source.page_labels.page_labels,
        page_label_source_ref=run_source.page_labels.source_ref,
        citations_by_finding=MappingProxyType(by_finding),
        citation_source_ref=(
            f"{read_run_id}:{read_snapshot_id}:{read_set_id}"
        ),
        attribution=attribution,
    )


__all__ = ["XlsxCertifiedSourcesRefused", "sources_from_certified_reads"]
