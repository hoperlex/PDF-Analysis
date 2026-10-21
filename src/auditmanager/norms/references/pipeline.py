"""Pure W57b reference report and newer-edition plan from one PDF text source.

The caller supplies independently pinned catalogue facts. This function cannot
establish verified-set custody or publish a rule observation.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.norms.references.catalogue_query import (
    CatalogueExpectation,
    load_pinned_catalogue,
)
from auditmanager.norms.references.observation_plan import (
    NewerEditionCandidate,
    ReferencePage,
    plan_newer_observations,
)
from auditmanager.norms.references.resolution import (
    ReferenceRefused,
    ReferenceReport,
    TextPage,
    extract_references,
    resolve_references,
)


@dataclass(frozen=True, slots=True)
class ReferencePipelineResult:
    report: ReferenceReport
    newer_candidates: tuple[NewerEditionCandidate, ...]


def run_reference_pipeline(
    *,
    catalogue_blob: bytes,
    expected_catalogue: CatalogueExpectation,
    listed_unparsed_slugs: tuple[str, ...],
    pages: tuple[ReferencePage, ...],
) -> ReferencePipelineResult:
    """Resolve references and anchor newer ones to the same PDF text pages.

    One immutable page tuple supplies both page-local extraction and the
    numbered, contiguous-offset evidence plan. There is no second text input
    whose contents could drift between the two steps.
    """
    if not isinstance(pages, tuple) or not pages or any(
        not isinstance(page, ReferencePage) for page in pages
    ):
        raise ReferenceRefused("reference pages must be a nonempty tuple of PDF text pages")
    catalogue = load_pinned_catalogue(
        blob=catalogue_blob,
        expected=expected_catalogue,
        listed_unparsed_slugs=listed_unparsed_slugs,
    )
    extraction = extract_references(
        tuple(TextPage(page.page_label, page.text) for page in pages)
    )
    report = resolve_references(
        extraction=extraction,
        catalogue=catalogue,
        pinned_snapshot_id=expected_catalogue.snapshot_id,
    )
    newer_candidates = plan_newer_observations(report=report, pages=pages)
    return ReferencePipelineResult(report, newer_candidates)


__all__ = ["ReferencePipelineResult", "run_reference_pipeline"]
