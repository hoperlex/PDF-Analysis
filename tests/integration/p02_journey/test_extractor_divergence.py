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

import ast
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


#: The field name the corpus generator's reference extractor uses for a page's text hash.
PAGE_HASH_FIELD = "page_text_sha256"

#: Modules that may *name* the field, keyed by their path under the ``auditmanager`` package,
#: with the reason. An entry is not a licence to read the manifest: the guard below still
#: rejects, in these files too, every use of the name other than declaring a field, keying a
#: dict that is being built, or prose in a docstring -- and the behavioural test after it
#: shows the values these modules put under the name are digests of the text they are given.
#: A stale entry (file gone, or no longer naming the field) is itself a failure, so the
#: list cannot outlive the thing it excuses.
OWN_PAGE_HASH_ALLOWANCES = {
    "comparison/sheet_match_suggestions.py": (
        "Sheet-pair suggestions (W59). `page_text_sha256` there is the SHA-256 the module "
        "itself computes over the UTF-8 bytes of a page's text, taken from the verified "
        "`prepared.text_layer` snapshot its caller supplies, to compare two versions' pages "
        "with each other. It reads neither the portal manifest nor `expected_issues.json`, "
        "so the pinned extractor's divergence from the reference hashes cannot reach it."
    ),
}


def _lines_naming_the_field(path: Path) -> list[int]:
    return [
        number
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if PAGE_HASH_FIELD in line
    ]


def _lines_reading_the_field(path: Path) -> list[int]:
    """Where a module uses the field name for anything but declaring or building.

    Not a read: a class-body field declaration (``page_text_sha256: str``), a string key of
    a dict display (``{"page_text_sha256": digest}``, where the value is whatever the module
    computed), and prose in a docstring. A read is every other occurrence -- a subscript,
    ``.get("page_text_sha256")``, an attribute access, a comparison, a keyword argument.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    declared: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            declared.update(
                id(stmt.target)
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            )
        elif isinstance(node, ast.Dict):
            declared.update(id(key) for key in node.keys if isinstance(key, ast.Constant))
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                declared.add(id(first.value))

    def carries_the_name(node: ast.AST) -> bool:
        if isinstance(node, ast.Constant):
            return isinstance(node.value, str) and PAGE_HASH_FIELD in node.value
        if isinstance(node, ast.Name):
            return PAGE_HASH_FIELD in node.id
        if isinstance(node, ast.Attribute):
            return PAGE_HASH_FIELD in node.attr
        if isinstance(node, (ast.arg, ast.keyword)):
            return node.arg is not None and PAGE_HASH_FIELD in node.arg
        return False

    return sorted(
        node.lineno for node in ast.walk(tree)
        if carries_the_name(node) and id(node) not in declared
    )


def _package_root() -> Path:
    import auditmanager

    # The package as actually imported, not a hardcoded path: a mutation applied through
    # ``-o pythonpath=<copy>/src`` must be visible here, or the "proof" that this guard
    # can fail would be scanning a tree the run never used.
    return Path(auditmanager.__file__).resolve().parent


def test_no_module_consumes_the_manifest_page_hashes():
    """The structural half of the claim: nothing in the chain reads the manifest's page hashes.

    Source text is scanned rather than imported, because the property is an absence and
    an absence cannot be asserted by calling something. Every module naming the field is a
    suspect, except the named allowances above -- which are held to the stricter rule that
    they may only declare and build with the name, never read it.
    """
    root = _package_root()
    allowed = {root / relative: reason for relative, reason in OWN_PAGE_HASH_ALLOWANCES.items()}

    stale = [
        str(path) for path in allowed
        if not path.is_file() or not _lines_naming_the_field(path)
    ]
    assert not stale, (
        f"an allowance names a module that is gone or no longer names {PAGE_HASH_FIELD}; "
        f"remove it from OWN_PAGE_HASH_ALLOWANCES: {stale}"
    )

    consumers = [
        f"{path}:{number}"
        for path in sorted(root.rglob("*.py"))
        if path not in allowed
        for number in _lines_naming_the_field(path)
    ]
    assert not consumers, (
        "a module now reads the reference extractor's page hashes, which the pinned "
        f"extractor does not reproduce: {consumers}"
    )

    readers = [
        f"{path}:{number}"
        for path in allowed
        for number in _lines_reading_the_field(path)
    ]
    assert not readers, (
        f"a module allowed to name {PAGE_HASH_FIELD} reads it instead of building it; the "
        f"allowance covers declaring a field and keying a dict it computes: {readers}"
    )


def test_the_allowed_module_digests_the_text_it_is_given_and_not_the_manifest(
    fixture_manifest, extracted_pages
):
    """The behavioural half: what the allowed module puts under the name is its own digest.

    The pinned extractor's pages hash differently from the manifest's declared hashes on
    every page (pinned above). If ``sheet_match_suggestions`` consumed the manifest's value
    it could not agree with the chain's text; it digests the text it is handed, so the value
    it reports equals the SHA-256 of the extractor's own page text and equals none of the
    manifest's.
    """
    from auditmanager.comparison.sheet_match_suggestions import (
        EXACT_PAIR_ALGORITHM,
        suggest_exact_sheet_matches,
        suggest_sheet_pairs,
    )
    from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

    project, document = "prj_01M2545JSD15ETSNNV904X991J", "doc_01M2545JSD15ETSNNV904X991J"
    pair = OrderedVersionPair(
        project, document,
        VersionFacts("ver_01M2545JSD15ETSNNV904X991J", document, project, 1, "a" * 64, 100,
                     len(extracted_pages), "application/pdf"),
        VersionFacts("ver_01M2545JSD15ETSNNV904X991K", document, project, 2, "b" * 64, 101,
                     len(extracted_pages), "application/pdf"),
    )
    pages = {number: page.text for number, page in enumerate(extracted_pages, 1)}
    declared = fixture_manifest["baseline"]["page_text_sha256"]

    def own(number: int) -> str:
        return hashlib.sha256(pages[number].encode("utf-8")).hexdigest()

    bound = suggest_exact_sheet_matches(
        version_pair=pair, comparison_id="cmp_00000000000000000000000001",
        source_pages=pages, target_pages=pages,
    )
    read_only = [
        item for item in suggest_sheet_pairs(version_pair=pair, source_pages=pages, target_pages=pages)
        if item.algorithm == EXACT_PAIR_ALGORITHM
    ]
    for label, found in (("bound", bound), ("read-only", read_only)):
        assert found, f"the {label} rule paired no page of the baseline; this would be vacuous"
        for item in found:
            number = item.source_page_number
            assert item.target_page_number == number
            reported = (
                item.page_text_sha256 if label == "bound" else item.source_page_text_sha256
            )
            assert reported == own(number), f"{label}: page {number} is not the text's own digest"
            assert reported != declared[number - 1], (
                f"{label}: page {number} reports the manifest's declared hash"
            )
