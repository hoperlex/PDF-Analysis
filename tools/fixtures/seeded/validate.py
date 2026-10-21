"""Independent checks on committed AR v2 seed bytes and their evidence oracle."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from ar_corpus import pdfextract
from portal_bundle import bundle as portal_bundle
from portal_bundle import validate as portal_validate

from .cases import CATEGORIES, PROFILE


class CorpusError(ValueError):
    """The synthetic corpus is incomplete, corrupt or cites unsupported evidence."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CorpusError(message)


def _quote_on_page(pages: list[str], evidence: dict, owner: str) -> None:
    page = evidence.get("page")
    quote = evidence.get("quote")
    _require(isinstance(page, int) and 1 <= page <= len(pages), f"{owner}: invalid page")
    _require(isinstance(quote, str) and bool(quote.strip()), f"{owner}: empty quote")
    _require(quote in pages[page - 1], f"{owner}: quote absent from PDF text layer page {page}")


def validate_bytes(manifest: dict, files: dict[str, bytes], *, require_full: bool) -> None:
    """Validate semantic claims against independently extracted PDF and ZIP bytes."""
    _require(manifest.get("schema") == "ar-v2-seeded/1", "unexpected manifest schema")
    _require(manifest.get("profile") == PROFILE, "unexpected profile")
    _require(manifest.get("source") == "synthetic", "source must be synthetic")
    entries = manifest.get("bundles")
    issues = manifest.get("issues")
    controls = manifest.get("controls")
    _require(isinstance(entries, list) and isinstance(issues, list) and isinstance(controls, list),
             "manifest collections are missing")
    _require(len(entries) == 10, "expected ten synthetic bundles")
    by_bundle = {}
    pages_by_bundle = {}
    for entry in entries:
        identifier = entry["id"]
        _require(identifier not in by_bundle, f"duplicate bundle {identifier}")
        pdf_path, zip_path = entry["pdf"], entry["portal_bundle"]
        _require(pdf_path in files and zip_path in files, f"{identifier}: absent fixture bytes")
        pdf, archive = files[pdf_path], files[zip_path]
        _require(hashlib.sha256(pdf).hexdigest() == entry["pdf_sha256"],
                 f"{identifier}: PDF digest mismatch")
        _require(hashlib.sha256(archive).hexdigest() == entry["portal_bundle_sha256"],
                 f"{identifier}: portal bundle digest mismatch")
        pages = pdfextract.extract_pages(pdf)
        _require(len(pages) == entry["page_count"] == 2, f"{identifier}: page count mismatch")
        _require(all("Синтетический комплект" in page for page in pages),
                 f"{identifier}: synthetic marker absent")
        actual_headers = sorted({
            line.split(":", 1)[0]
            for page in pages for line in page.splitlines()
            if line.startswith("Лист АР-")
        })
        _require(actual_headers == entry["supplied_headers"],
                 f"{identifier}: supplied-header inventory differs from PDF")
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as packed:
                pdf_members = [name for name in packed.namelist() if name.endswith(".pdf")]
                _require(len(pdf_members) == 1 and packed.read(pdf_members[0]) == pdf,
                         f"{identifier}: portal archive carries a different PDF")
        except (OSError, zipfile.BadZipFile) as exc:
            raise CorpusError(f"{identifier}: unreadable portal archive") from exc
        verdict = portal_validate.validate(archive, portal_bundle.GENERATOR_LIMITS)
        _require(not verdict.constraints, f"{identifier}: invalid portal archive {verdict.constraints}")
        by_bundle[identifier] = entry
        pages_by_bundle[identifier] = pages

    all_ids: set[str] = set()
    positive_counts: Counter[str] = Counter()
    control_counts: Counter[str] = Counter()
    spread: dict[str, set[str]] = defaultdict(set)
    for kind, collection in (("issue", issues), ("control", controls)):
        for item in collection:
            identifier = item.get("id")
            _require(isinstance(identifier, str) and identifier not in all_ids,
                     f"duplicate or invalid {kind} id {identifier!r}")
            all_ids.add(identifier)
            category = item.get("category")
            _require(category in CATEGORIES, f"{identifier}: unknown category {category}")
            bundle_id = item.get("bundle_id")
            _require(bundle_id in by_bundle, f"{identifier}: unknown bundle")
            evidence = item.get("evidence")
            _require(isinstance(evidence, list) and bool(evidence), f"{identifier}: no evidence")
            for citation in evidence:
                _quote_on_page(pages_by_bundle[bundle_id], citation, identifier)
            if kind == "issue":
                positive_counts[category] += 1
                spread[category].add(bundle_id)
                missing = item.get("missing_content")
                if missing is not None:
                    _require(any(missing in citation["quote"] for citation in evidence),
                             f"{identifier}: absent content lacks an explicit promise")
                    _require(not any(missing in heading for heading in by_bundle[bundle_id]["supplied_headers"]),
                             f"{identifier}: promised content is actually supplied")
                    if item["archetype"] == "promised_sheet_missing":
                        sheet = re.search(r"АР-\d+", missing)
                        _require(sheet is not None and not any(
                            sheet.group() in heading for heading in by_bundle[bundle_id]["supplied_headers"]
                        ), f"{identifier}: promised sheet is supplied")
                    if item["archetype"] == "promised_section_missing":
                        section = re.search(r"раздел\s+\d+", missing, re.I)
                        _require(section is not None and not any(
                            line.lower().startswith(section.group().lower())
                            for page in pages_by_bundle[bundle_id] for line in page.splitlines()
                        ), f"{identifier}: promised section is supplied")
            else:
                control_counts[category] += 1
                _require(item.get("control_archetype") == "near_miss", f"{identifier}: wrong control type")
                _require(item.get("expected_finding") is False, f"{identifier}: control expects a finding")
                _require(bool(item.get("scope")) and bool(item.get("why_not_issue")),
                         f"{identifier}: missing near-miss explanation")

    if require_full:
        _require(set(positive_counts) == set(CATEGORIES), "positive category coverage incomplete")
        _require(set(control_counts) == set(CATEGORIES), "control category coverage incomplete")
        for category in CATEGORIES:
            _require(positive_counts[category] >= 3, f"{category}: fewer than three issues")
            _require(control_counts[category] >= 1, f"{category}: no near-miss")
            _require(len(spread[category]) >= 2, f"{category}: positives in only one bundle")
        _require(len(issues) >= 3 * len(CATEGORIES) and len(controls) >= len(CATEGORIES),
                 "minimum case count not met")


def validate_directory(root: Path) -> dict:
    data = json.loads((root / "expected_issues.json").read_text(encoding="utf-8"))
    files = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    validate_bytes(data, files, require_full=True)
    return data
