"""The pure W57b pipeline uses one text source for report and rule evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.norms.references.catalogue_query import CatalogueExpectation
from auditmanager.norms.references.observation_plan import ReferencePage
from auditmanager.norms.references.pipeline import run_reference_pipeline
from auditmanager.norms.references.resolution import (
    ABSENT,
    NEWER,
    OLDER,
    PRESENT,
    UNPARSED,
    ReferenceRefused,
)
from auditmanager.norms.references.tokens import sql_designation_tokens


SNAPSHOT = "ns_" + "0" * 26
UNPARSED_SLUG = "неизвестный_документ"


def _catalogue() -> tuple[bytes, CatalogueExpectation]:
    slugs = (
        "СП_54.13330.2022",
        "СП_54.13330.2024",
        "ГОСТ_21.101-2020",
        UNPARSED_SLUG,
    )
    documents = [
        {
            "norm_document_id": f"ndoc_{number:026d}",
            "slug": slug,
            "designation_tokens": sql_designation_tokens(slug),
            "title": f"Document {number}",
            "doc_type": "СП",
        }
        for number, slug in enumerate(slugs, 1)
    ]
    payload = {
        "catalogue_version": "norm-catalogue-prep-v1",
        "norms_snapshot_id": SNAPSHOT,
        "content_key": "reviewed-key",
        "snapshot_content_digest": "a" * 64,
        "document_count": len(documents),
        "documents": documents,
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    expected = CatalogueExpectation(SNAPSHOT, "reviewed-key", "a" * 64, 4, hashlib.sha256(blob).hexdigest())
    return blob, expected


def _pages() -> tuple[ReferencePage, ...]:
    first = (
        "См. СП 54.13330.2022, ГОСТ 21.101-2020, СНиП 31-01-2003, "
        "СП 2.13130 и ГОСТ 21.101-2024."
    )
    second = "Повтор: СП 54.13330.2022."
    return (
        ReferencePage("1", 1, 0, first),
        ReferencePage("2", 2, len(first), second),
        ReferencePage("3", 3, len(first) + len(second), None),
    )


def _run(*, pages: tuple[ReferencePage, ...] | None = None, expected: CatalogueExpectation | None = None):
    blob, actual_expected = _catalogue()
    return run_reference_pipeline(
        catalogue_blob=blob,
        expected_catalogue=expected or actual_expected,
        listed_unparsed_slugs=(UNPARSED_SLUG,),
        pages=_pages() if pages is None else pages,
    )


def test_one_source_yields_five_outcomes_and_only_newer_rule_evidence() -> None:
    result = _run()
    outcomes = {ref.cited: ref.outcome for ref in result.report.references}
    assert outcomes == {
        "СП 54.13330.2022": NEWER,
        "ГОСТ 21.101-2020": PRESENT,
        "СНиП 31-01-2003": ABSENT,
        "СП 2.13130": UNPARSED,
        "ГОСТ 21.101-2024": OLDER,
    }
    assert result.report.unread_pages == ("3",)
    candidate, = result.newer_candidates
    assert candidate.cited == "СП 54.13330.2022"
    assert candidate.matched_document_id == f"ndoc_{2:026d}"
    assert candidate.rule_id == "normative_refs.newer_edition/1"
    assert [span.page_number for span in candidate.evidence] == [1, 2]
    source = "".join(page.text or "" for page in _pages())
    assert all(source[span.char_start:span.char_end] == span.quote for span in candidate.evidence)
    assert not hasattr(candidate, "proposed_severity")
    assert _run() == result


def test_mismatched_pinned_facts_and_unreviewed_slug_are_refused() -> None:
    blob, expected = _catalogue()
    with pytest.raises(ReferenceRefused, match="digest differs"):
        _run(expected=replace(expected, catalogue_sha256="b" * 64))
    with pytest.raises(ReferenceRefused, match="snapshot differs"):
        _run(expected=replace(expected, snapshot_id="ns_" + "1" * 26))
    with pytest.raises(ReferenceRefused, match="unlisted unparsed"):
        run_reference_pipeline(
            catalogue_blob=blob,
            expected_catalogue=expected,
            listed_unparsed_slugs=(),
            pages=_pages(),
        )


@pytest.mark.parametrize(
    ("pages", "message"),
    [
        (_pages()[:1] + (replace(_pages()[1], char_start=0),) + _pages()[2:], "not contiguous"),
        (_pages()[:1] + (replace(_pages()[1], page_label="1"),) + _pages()[2:], "duplicate or invalid"),
        (_pages()[:1] + (replace(_pages()[1], page_number=1),) + _pages()[2:], "unordered"),
        (_pages()[:2] + (replace(_pages()[2], text=1),), "text must be text or absent"),
        ((), "nonempty tuple"),
    ],
)
def test_inconsistent_pdf_page_sources_fail_closed(pages, message: str) -> None:
    with pytest.raises(ReferenceRefused, match=message):
        _run(pages=pages)
