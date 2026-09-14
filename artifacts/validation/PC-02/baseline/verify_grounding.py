"""Verify every published quotation against an extractor the product does not share.

The product extracts with ``pdfplumber`` (``src/auditmanager/analysis/stages/extraction.py``
line 51, ``EXTRACTOR_NAME = "pdfplumber"``). Asking ``pdfplumber`` whether ``pdfplumber``
read the page correctly would be certifying the product against itself, so the reader here
is ``tools/fixtures/ar_corpus/pdfextract.py``: a from-scratch PDF parser that imports no
PDF library at all -- only ``re`` and ``zlib`` -- and shares no code and no data structure
with the writer of the quotations.

That reader is pinned before it is trusted. The corpus manifest records
``page_text_sha256`` per page; if this extractor does not reproduce those digests it is
not reading what the corpus declares, and every downstream answer would be about the
extractor rather than about the product. A digest mismatch fails the run.

Three properties are then checked per published evidence item:

1. **Page.** The quotation occurs in the independently extracted text of the page the
   finding declares. This is the substantive grounding claim.
2. **Offset integrity.** ``char_start``/``char_end`` index the *document-global*
   character sequence of the product's prepared text layer -- the frozen ``Evidence``
   schema says so -- and therefore cannot be resolved directly against a different
   extractor's page texts. What is checkable from outside, and what catches a real class
   of defect, is that the span is exactly as long as the quotation it anchors, that
   spans are distinct, and that a document-global sequence runs in page order.
3. **Page-local offset, independently.** Where the quotation occurs on the page
   according to this extractor, reported as a measurement. Offsets computed against a
   different extractor are not expected to equal the product's global offsets and no
   gate is placed on them; they are recorded so that P05 can see the two extractors
   agree about where on the page the text sits.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MANIFEST = ROOT / "fixtures" / "validation" / "PC-02" / "corpus_manifest.json"
RUNS = HERE / "runs"
EXTRACTOR = ROOT / "tools" / "fixtures" / "ar_corpus" / "pdfextract.py"


def load_independent_extractor() -> Any:
    """Load the corpus's own parser by explicit path, under its own module name."""
    name = "p4run01_independent_pdfextract"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EXTRACTOR)
    assert spec is not None and spec.loader is not None, EXTRACTOR
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    documents = {d["label"]: d for d in manifest["documents"]}
    extractor = load_independent_extractor()

    report: dict[str, Any] = {
        "independent_reader": str(EXTRACTOR.relative_to(ROOT)),
        "independent_reader_note": "a from-scratch PDF parser importing only re and "
                                   "zlib; the product extracts with pdfplumber",
        "product_extractor": "pdfplumber "
                             "(src/auditmanager/analysis/stages/extraction.py:51)",
        "documents": {},
    }
    verified = 0
    failures: list[dict] = []
    pinned_documents = 0

    for path in sorted(RUNS.glob("PC02-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        label = record["label"]
        document = documents.get(label)
        if document is None:            # a negative-envelope document; nothing published
            continue
        findings = record.get("findings") or []

        data = (ROOT / document["path"]).read_bytes()
        pages = extractor.extract_pages(data)

        declared = document.get("page_text_sha256") or []
        actual = [sha256(text) for text in pages]
        pinned = actual == declared
        if pinned:
            pinned_documents += 1
        else:
            failures.append({"document": label, "failure": "page_text_sha256 mismatch",
                             "declared": declared, "actual": actual})

        items: list[dict] = []
        anchors: list[tuple[int, int, int, str]] = []
        for finding in findings:
            evidence = (finding.get("observation") or {}).get("evidence") or []
            if not evidence:
                failures.append({"document": label,
                                 "finding_uid": finding.get("finding_uid"),
                                 "failure": "finding published no evidence"})
            for item in evidence:
                page = item["page_number"]
                quote = item["quote"]
                start, end = item["char_start"], item["char_end"]
                anchors.append((start, end, page, quote))

                in_range = 1 <= page <= len(pages)
                page_text = pages[page - 1] if in_range else ""
                present = bool(quote) and quote in page_text
                local = page_text.find(quote) if present else None
                span_ok = 0 <= start < end and (end - start) == len(quote)

                entry = {
                    "finding_uid": finding.get("finding_uid"),
                    "evidence_ordinal": item.get("evidence_ordinal"),
                    "page_number": page,
                    "page_in_range": in_range,
                    "quote": quote,
                    "present_on_declared_page": present,
                    "page_local_offset_independent": local,
                    "declared_char_start": start,
                    "declared_char_end": end,
                    "span_length_matches_quotation": span_ok,
                    "pinned_to_manifest": pinned,
                    "verified": bool(in_range and present and span_ok and pinned),
                }
                items.append(entry)
                if entry["verified"]:
                    verified += 1
                else:
                    failures.append({"document": label, **entry})

        ordered = sorted(anchors)
        page_order = [p for _, _, p, _ in ordered]
        starts = [s for s, _, _, _ in ordered]
        report["documents"][label] = {
            "page_text_sha256_pinned": pinned,
            "pages_extracted": len(pages),
            "evidence_items": items,
            "global_offsets_run_in_page_order": page_order == sorted(page_order),
            "global_offsets_distinct": len(set(starts)) == len(starts),
        }
        if page_order != sorted(page_order):
            failures.append({"document": label,
                             "failure": "document-global offsets run against page order",
                             "pages": page_order})
        if len(set(starts)) != len(starts):
            failures.append({"document": label,
                             "failure": "two anchors claim the same start offset",
                             "starts": starts})

    report["quotations_verified"] = verified
    report["failures"] = failures
    report["failure_count"] = len(failures)
    report["documents_pinned_to_manifest"] = pinned_documents
    report["vacuity_note"] = (
        "A loop over an empty evidence set verifies nothing and would report no "
        "failures. quotations_verified is therefore reported beside the count, and a "
        "finding that published no evidence at all is itself recorded as a failure."
    )

    (HERE / "grounding.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"independent reader: {report['independent_reader']}")
    print(f"documents pinned to manifest page_text_sha256: {pinned_documents}")
    print(f"quotations verified at declared page and offset: {verified}")
    print(f"failures: {len(failures)}")
    for failure in failures[:10]:
        print("  " + json.dumps(failure, ensure_ascii=False)[:300])
    return 0 if not failures and verified > 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
