"""Synthetic AR v2 evidence survives independent PDF/ZIP reads and mutations."""

from __future__ import annotations

import copy
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "fixtures"))

from ar_corpus import pdfextract  # noqa: E402
from seeded import cases, generate, validate  # noqa: E402

CORPUS = ROOT / "fixtures" / "evaluation" / "ar_v2"


@pytest.fixture(scope="module")
def committed() -> tuple[dict, dict[str, bytes]]:
    manifest = json.loads((CORPUS / "expected_issues.json").read_text(encoding="utf-8"))
    files = {
        str(path.relative_to(CORPUS)): path.read_bytes()
        for path in CORPUS.rglob("*") if path.is_file()
    }
    return manifest, files


def test_committed_corpus_is_complete_and_independently_readable(committed) -> None:
    manifest, files = committed
    validate.validate_bytes(manifest, files, require_full=True)
    assert len(manifest["bundles"]) == 10
    assert len(manifest["issues"]) == 21
    assert len(manifest["controls"]) == 7
    assert {item["category"] for item in manifest["issues"]} == set(cases.CATEGORIES)
    assert {item["category"] for item in manifest["controls"]} == set(cases.CATEGORIES)
    for entry in manifest["bundles"]:
        assert len(pdfextract.extract_pages(files[entry["pdf"]])) == 2


def test_seeded_categories_equal_the_sealed_api_enum() -> None:
    contract = json.loads((ROOT / "contracts" / "api" / "v1" / "openapi.json").read_text())
    assert tuple(contract["components"]["schemas"]["FindingCategory"]["enum"]) == cases.CATEGORIES


def test_regeneration_is_byte_stable_and_matches_committed_bytes(committed) -> None:
    _, files = committed
    assert generate.build() == generate.build() == files


@pytest.mark.parametrize("kind,index", [
    *(("issues", index) for index in range(len(cases.ISSUES))),
    *(("controls", index) for index in range(len(cases.CONTROLS))),
])
def test_each_case_has_a_non_vacuous_quote_guard(committed, kind: str, index: int) -> None:
    manifest, files = committed
    broken = copy.deepcopy(manifest)
    item = broken[kind][index]
    item["evidence"][0]["quote"] = "Цитата отсутствует в PDF " + item["id"]
    with pytest.raises(validate.CorpusError, match="quote absent from PDF text layer"):
        validate.validate_bytes(broken, files, require_full=True)


@pytest.mark.parametrize("category", cases.CATEGORIES)
def test_each_category_has_three_issues_across_two_bundles_and_a_control(
    committed, category: str,
) -> None:
    manifest, _ = committed
    issues = [item for item in manifest["issues"] if item["category"] == category]
    controls = [item for item in manifest["controls"] if item["category"] == category]
    assert len(issues) >= 3
    assert len({item["bundle_id"] for item in issues}) >= 2
    assert len(controls) >= 1


def test_a_promise_removed_from_a_missing_content_case_is_refused(committed) -> None:
    manifest, files = committed
    broken = copy.deepcopy(manifest)
    case = next(item for item in broken["issues"] if item["id"] == "do_sheet")
    case["missing_content"] = "лист АР-88 Не обещан"
    with pytest.raises(validate.CorpusError, match="lacks an explicit promise"):
        validate.validate_bytes(broken, files, require_full=True)


def test_a_control_reclassified_as_a_finding_is_refused(committed) -> None:
    manifest, files = committed
    broken = copy.deepcopy(manifest)
    broken["controls"][0]["expected_finding"] = True
    with pytest.raises(validate.CorpusError, match="control expects a finding"):
        validate.validate_bytes(broken, files, require_full=True)


def test_portal_only_recognition_cannot_be_used_as_a_pdf_citation(committed) -> None:
    manifest, files = committed
    with zipfile.ZipFile(io.BytesIO(files[manifest["bundles"][0]["portal_bundle"]])) as archive:
        recognised_text = next(name for name in archive.namelist() if name.endswith("_results.md"))
        assert generate.RECOGNISED_ONLY_DECOY in archive.read(recognised_text).decode("utf-8")
    assert generate.RECOGNISED_ONLY_DECOY not in pdfextract.extract_pages(
        files[manifest["bundles"][0]["pdf"]]
    )[0]
    broken = copy.deepcopy(manifest)
    first = next(item for item in broken["issues"] if item["bundle_id"] == "ar_v2_01")
    first["evidence"][0]["quote"] = generate.RECOGNISED_ONLY_DECOY
    with pytest.raises(validate.CorpusError, match="quote absent from PDF text layer"):
        validate.validate_bytes(broken, files, require_full=True)
