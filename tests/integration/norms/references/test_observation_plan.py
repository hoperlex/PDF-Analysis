"""W57b rule candidates keep exact PDF text anchors and only newer outcomes."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.norms.references.observation_plan import (
    ReferencePage,
    plan_newer_observations,
)
from auditmanager.norms.references.resolution import (
    CatalogueEntry,
    PinnedCatalogue,
    ReferenceRefused,
    TextPage,
    extract_references,
    resolve_references,
)
from auditmanager.norms.references.tokens import sql_designation_tokens


SNAPSHOT = "ns_" + "0" * 26


def _report(*pages: TextPage):
    slugs = ("СП_54.13330.2022", "СП_54.13330.2024", "ГОСТ_21.101-2020")
    catalogue = PinnedCatalogue(
        SNAPSHOT,
        tuple(
            CatalogueEntry(f"ndoc_{number}", slug, sql_designation_tokens(slug))
            for number, slug in enumerate(slugs, 1)
        ),
    )
    return resolve_references(
        extraction=extract_references(tuple(pages)),
        catalogue=catalogue,
        pinned_snapshot_id=SNAPSHOT,
    )


def test_only_newer_reference_becomes_rule_candidate_with_global_codepoint_offsets() -> None:
    first = "См. СП 54.13330.2022 и ГОСТ 21.101-2020."
    second = "Повтор: СП 54.13330.2022."
    report = _report(TextPage("A", first), TextPage("B", second), TextPage("C", None))
    candidates = plan_newer_observations(
        report=report,
        pages=(
            ReferencePage("A", 1, 0, first),
            ReferencePage("B", 2, len(first), second),
            ReferencePage("C", 3, len(first) + len(second), None),
        ),
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.rule_id == "normative_refs.newer_edition/1"
    assert candidate.matched_document_id == "ndoc_2"
    assert candidate.finding_text == (
        "Проект ссылается на СП 54.13330.2022; "
        "в корпусе есть более новая редакция: СП 54.13330.2024"
    )
    document = first + second
    assert [e.page_number for e in candidate.evidence] == [1, 2]
    assert all(document[e.char_start:e.char_end] == e.quote for e in candidate.evidence)
    assert candidate.evidence[1].char_start >= len(first)
    assert not hasattr(candidate, "proposed_severity")
    assert plan_newer_observations(
        report=report,
        pages=(
            ReferencePage("A", 1, 0, first),
            ReferencePage("B", 2, len(first), second),
            ReferencePage("C", 3, len(first) + len(second), None),
        ),
    ) == candidates


def test_at_most_ten_evidence_spans_are_planned() -> None:
    text = "; ".join(["СП 54.13330.2022"] * 11)
    report = _report(TextPage("1", text))
    assert report.references[0].total_occurrences == 11
    candidate, = plan_newer_observations(
        report=report, pages=(ReferencePage("1", 1, 0, text),)
    )
    assert len(candidate.evidence) == 10


def test_wrong_quote_or_global_page_start_is_refused() -> None:
    text = "СП 54.13330.2022"
    report = _report(TextPage("1", text))
    changed_occurrence = replace(report.references[0].occurrences[0], raw_text="СП 54.13330.2024")
    changed_reference = replace(report.references[0], occurrences=(changed_occurrence,))
    altered = replace(report, references=(changed_reference,))
    with pytest.raises(ReferenceRefused, match="does not match PDF text"):
        plan_newer_observations(report=altered, pages=(ReferencePage("1", 1, 0, text),))
    with pytest.raises(ReferenceRefused, match="not contiguous"):
        plan_newer_observations(report=report, pages=(ReferencePage("1", 1, 1, text),))


def test_unread_or_unknown_page_cannot_be_evidence() -> None:
    text = "СП 54.13330.2022"
    report = _report(TextPage("1", text))
    with pytest.raises(ReferenceRefused, match="unread pages differ"):
        plan_newer_observations(report=report, pages=(ReferencePage("1", 1, 0, None),))
    with pytest.raises(ReferenceRefused, match="no readable PDF text page"):
        plan_newer_observations(report=report, pages=(ReferencePage("other", 1, 0, text),))


def test_report_only_status_and_invalid_newer_provenance_fail_closed() -> None:
    text = "ГОСТ 21.101-2020"
    report = _report(TextPage("1", text))
    assert plan_newer_observations(report=report, pages=(ReferencePage("1", 1, 0, text),)) == ()
    altered = replace(report, references=(replace(report.references[0], observation_text="bad"),))
    with pytest.raises(ReferenceRefused, match="report-only"):
        plan_newer_observations(report=altered, pages=(ReferencePage("1", 1, 0, text),))

    newer_text = "СП 54.13330.2022"
    newer = _report(TextPage("1", newer_text))
    altered_newer = replace(
        newer,
        references=(replace(newer.references[0], matched_document_id="other"),),
    )
    with pytest.raises(ReferenceRefused, match="invalid catalogue provenance"):
        plan_newer_observations(
            report=altered_newer, pages=(ReferencePage("1", 1, 0, newer_text),)
        )


def test_duplicate_page_identity_is_refused() -> None:
    text = "СП 54.13330.2022"
    report = _report(TextPage("1", text))
    with pytest.raises(ReferenceRefused, match="duplicate or empty"):
        plan_newer_observations(
            report=report,
            pages=(ReferencePage("1", 1, 0, text), ReferencePage("1", 2, len(text), "")),
        )
