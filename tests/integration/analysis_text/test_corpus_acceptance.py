"""The recorded run over the AR corpus, against the seeded issues and the controls.

``fixtures/synthetic/ar/expected_issues.json`` seeds two cross-page contradictions and
one explicit placeholder, and six controls built as real near-misses that a correct
analyzer must **not** flag: a third value of the same attribute belonging to a
*different building*, a resolved statement that merely contains the stem «уточн», two
storey heights that differ because the storeys do, an attribute repeated with the same
value, and a basement exit the next line explicitly excludes from the count.

Both halves are checked by **document-global offsets**, not by string matching. Each
control quotation resolves to exactly one interval in the corpus, and the assertion is
that no emitted evidence interval intersects any of them. That is a stronger statement
than "no emitted quote equals a control": it also catches an observation that quoted a
control with a word trimmed off either end.
"""

from __future__ import annotations

from typing import Any

from auditmanager.analysis.text import STATUS_SUCCEEDED, load_text_layer, run_text_analysis
from auditmanager.shared.identity import RunId


def _span_of(text_layer: Any, page_number: int, quotation: str) -> tuple[int, int]:
    page = text_layer.page(page_number)
    assert page is not None, f"the corpus has no page {page_number}"
    offset = page.text.find(quotation)
    assert offset >= 0, "an expected-issues quotation is absent from the corpus text layer"
    start = page.char_start + offset
    return start, start + len(quotation)


def _intersects(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _emitted_spans(artifact: dict[str, Any]) -> list[tuple[int, int]]:
    return [
        (item["char_start"], item["char_end"])
        for observation in artifact["observations"]
        for item in observation["evidence"]
    ]


def test_recorded_run_surfaces_every_seeded_issue(
    text_layer_document, recorded_adapter, expected_issues
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    assert outcome.status == STATUS_SUCCEEDED
    text_layer = load_text_layer(text_layer_document)
    emitted = _emitted_spans(outcome.artifact)

    surfaced: list[str] = []
    for issue in expected_issues["seeded_issues"]:
        wanted = [
            _span_of(text_layer, evidence["page"], evidence["quotation"])
            for evidence in issue["evidence"]
        ]
        for observation in outcome.artifact["observations"]:
            if observation["category"] != issue["category"]:
                continue
            spans = [(item["char_start"], item["char_end"]) for item in observation["evidence"]]
            # Every seeded quotation must be present: half a contradiction is not the
            # contradiction, and a reviewer opening it would see only one value.
            if all(span in spans for span in wanted):
                surfaced.append(issue["id"])
                break

    assert sorted(surfaced) == ["SI-01", "SI-02", "SI-03"]
    assert len(surfaced) == expected_issues["seeded_issue_count"] == 3
    assert emitted, "the run emitted no evidence at all"


def test_recorded_run_flags_none_of_the_controls(
    text_layer_document, recorded_adapter, expected_issues
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    text_layer = load_text_layer(text_layer_document)
    emitted = _emitted_spans(outcome.artifact)

    flagged: list[str] = []
    control_count = 0
    for control in expected_issues["controls"]:
        control_count += 1
        for anchor in control["anchors"]:
            span = _span_of(text_layer, anchor["page"], anchor["quotation"])
            if any(_intersects(span, other) for other in emitted):
                flagged.append(control["id"])
                break

    assert control_count == 6
    assert flagged == [], f"controls were flagged: {flagged}"


def test_the_run_emits_exactly_the_three_seeded_observations(
    text_layer_document, recorded_adapter
):
    """Counts, stated plainly, so a regression shows up as a number and not a diff."""
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    categories = [obs["category"] for obs in outcome.artifact["observations"]]
    assert len(categories) == 3
    assert categories.count("internal_contradiction") == 2
    assert categories.count("explicit_placeholder") == 1
    assert outcome.metrics["evidence_emitted"] == 5
    assert outcome.metrics["evidence_unresolved"] == 0
    assert outcome.metrics["observations_dropped_unresolved"] == 0
    assert outcome.metrics["pages_analysed"] == outcome.metrics["pages_total"] == 8


def test_every_seeded_and_control_quotation_resolves_in_the_text_layer(
    text_layer_document, expected_issues
):
    """The fixture text layer is faithful to the corpus manifest: 12 of 12.

    If this fails, the text layer drifted from ``ar_baseline.pdf`` and every offset
    assertion above is measuring the wrong document.
    """
    text_layer = load_text_layer(text_layer_document)
    resolved = 0
    for issue in expected_issues["seeded_issues"]:
        for evidence in issue["evidence"]:
            page = text_layer.page(evidence["page"])
            assert page.text.count(evidence["quotation"]) == 1
            resolved += 1
    for control in expected_issues["controls"]:
        for anchor in control["anchors"]:
            page = text_layer.page(anchor["page"])
            assert page.text.count(anchor["quotation"]) == 1
            resolved += 1
    assert resolved == 12
