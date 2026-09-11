"""The A4/pdfplumber extractor divergence: real, and inert. Confirmed independently.

``fixtures/synthetic/ar/expected_issues.json`` records ``baseline.page_text_sha256`` from
the corpus generator's reference extractor. The pinned ``pdfplumber`` produces different
page text -- ``extract_text()`` collapses runs of spaces -- and the hashes differ on every
page. The question that matters is not whether they differ but whether any **evidence
anchor** moved, because an anchor that shifted would make every quotation in the system
suspect.

This suite checks the anchors, not the hashes. It asserts each declared quotation appears
at its declared ``char_offset_in_page_text`` in the text the chain's own extractor
produces -- offset, not mere presence, so a shift anywhere before an anchor fails here.
It also pins the divergence itself, so that silently "fixing" the extractor to match the
reference shows up as a change rather than passing unnoticed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The corpus this suite reads. Overridable **only** so that the guards below can be
#: shown to fail, which the dispatch requires of every guard: the anchors live in a
#: tracked fixture, and mutating a tracked file to prove a test is forbidden. Point this
#: at a scratch copy with a perturbed offset and
#: ``test_every_declared_quotation_resolves_at_its_declared_offset`` goes red. It defaults
#: to the real corpus, so a normal run reads exactly what the chain reads.
CORPUS = Path(os.environ.get("B3CONV_CORPUS_DIR", REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"))
EXPECTED = CORPUS / "expected_issues.json"
BASELINE = CORPUS / "ar_baseline.pdf"


@pytest.fixture(scope="module")
def fixture_manifest() -> dict:
    return json.loads(EXPECTED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def extracted_pages():
    """The page text the chain itself produces, through the stage's own extractor.

    Calling ``pdfplumber`` directly here would test a different extractor than the one
    ``source_preparation`` runs, and could agree with the fixture while the chain did not.
    """
    from auditmanager.analysis.stages.extraction import extract_document

    return extract_document(BASELINE.read_bytes()).pages


def declared_anchors(manifest: dict) -> list[tuple[str, dict]]:
    anchors: list[tuple[str, dict]] = []

    def collect(node: object, ident: str) -> None:
        if isinstance(node, dict):
            if "quotation" in node and "page" in node:
                anchors.append((ident, node))
            for value in node.values():
                collect(value, ident)
        elif isinstance(node, list):
            for value in node:
                collect(value, ident)

    for issue in manifest["seeded_issues"]:
        collect(issue, issue["id"])
    for control in manifest.get("controls", []):
        collect(control, control.get("id", "control"))
    return anchors


def test_the_corpus_declares_the_anchors_this_suite_checks(fixture_manifest):
    """Without this, an empty anchor list would make every assertion below vacuous."""
    anchors = declared_anchors(fixture_manifest)
    assert len(anchors) == 12, f"expected 12 declared anchors, found {len(anchors)}"
    for _, anchor in anchors:
        assert "char_offset_in_page_text" in anchor
        assert anchor["quotation"]


def test_every_declared_quotation_resolves_at_its_declared_offset(
    fixture_manifest, extracted_pages
):
    """The property that makes the divergence inert."""
    failures = []
    for ident, anchor in declared_anchors(fixture_manifest):
        text = extracted_pages[anchor["page"] - 1].text
        quotation = anchor["quotation"]
        offset = anchor["char_offset_in_page_text"]
        if text[offset : offset + len(quotation)] != quotation:
            failures.append(
                f"{ident} page {anchor['page']}: declared offset {offset}, "
                f"quotation actually at {text.find(quotation)}"
            )
    assert not failures, (
        "evidence anchors have moved against the chain's extractor; every quotation in "
        "the system is suspect until this is explained:\n  " + "\n  ".join(failures)
    )


def test_the_divergence_is_real_and_is_confined_to_the_page_hashes(
    fixture_manifest, extracted_pages
):
    """Pins the known divergence. If the extractor is ever changed to agree with the
    reference, this fails and the change is noticed rather than absorbed."""
    declared = fixture_manifest["baseline"]["page_text_sha256"]
    assert len(declared) == len(extracted_pages) == 8
    differing = [
        index + 1
        for index, page in enumerate(extracted_pages)
        if hashlib.sha256(page.text.encode("utf-8")).hexdigest() != declared[index]
    ]
    assert differing == [1, 2, 3, 4, 5, 6, 7, 8], (
        f"the extractor divergence changed shape: pages differing are {differing}. "
        "It was all eight at base 92bece8."
    )


def test_no_module_consumes_the_manifest_page_hashes():
    """The structural half of the claim: nothing in the chain reads ``page_text_sha256``.

    Source text is scanned rather than imported, because the property is an absence and
    an absence cannot be asserted by calling something.
    """
    import auditmanager

    # The package as actually imported, not a hardcoded path: a mutation applied through
    # ``-o pythonpath=<copy>/src`` must be visible here, or the "proof" that this guard
    # can fail would be scanning a tree the run never used.
    source_root = Path(auditmanager.__file__).resolve().parent
    consumers = [
        f"{path}:{number}"
        for path in source_root.rglob("*.py")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "page_text_sha256" in line
    ]
    assert not consumers, (
        "a module now reads the reference extractor's page hashes, which the pinned "
        f"extractor does not reproduce: {consumers}"
    )
