#!/usr/bin/env python3
"""Build the synthetic comparison corpus and its answer keys (CMP-FIXTURES-01).

    python3 tools/fixtures/comparison/build.py           # write fixtures/comparison/
    python3 tools/fixtures/comparison/build.py --check   # rebuild in memory, compare, write nothing

`--check` rebuilds every artefact and compares it byte for byte with what is committed, then
reads the committed PDFs back with the in-tree extractor (`ar_corpus/pdfextract.py`) and checks
every claim of the answer keys that a text layer can show: page counts, stamp fields and the
before/after of each text change at its bounding box. The tests in
`tests/contract/fixtures_comparison` repeat that with three independent readers.

The realistic A1 sheet is not part of this build: `realistic_a1.py` writes it where the
caller says, and it is never committed.

Pure standard library, like the rest of `tools/fixtures`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ar_corpus import pdfextract  # noqa: E402
from comparison import sp1, vs1  # noqa: E402
from comparison.scene import REPO_ROOT  # noqa: E402

OUT_DIR = REPO_ROOT / "fixtures" / "comparison"
KEY_NAME = "answer_key.json"
CHECKSUM_NAME = "SHA256SUMS"
#: The task keeps the committed PDFs under 2 MB in all.
PDF_BUDGET_BYTES = 2_000_000


class BuildError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def key_bytes(key: dict[str, object]) -> bytes:
    return (json.dumps(key, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_all() -> dict[str, bytes]:
    """Every artefact as relative path -> bytes. Refuses to return an inconsistent corpus."""
    vs_files, vs_key = vs1.build()
    sp_files, sp_key = sp1.build()
    artefacts: dict[str, bytes] = {}
    artefacts.update(vs_files)
    artefacts["vs1/" + KEY_NAME] = key_bytes(vs_key)
    artefacts.update(sp_files)
    artefacts["sp1/" + KEY_NAME] = key_bytes(sp_key)

    pdf_total = sum(len(data) for name, data in artefacts.items() if name.endswith(".pdf"))
    if pdf_total >= PDF_BUDGET_BYTES:
        raise BuildError(f"the PDFs come to {pdf_total} bytes, the budget is {PDF_BUDGET_BYTES}")

    problems = verify_text_layer(artefacts, vs_key, sp_key)
    if problems:
        raise BuildError("the text layer does not carry the keys' claims:\n  " + "\n  ".join(problems))

    artefacts[CHECKSUM_NAME] = (
        "\n".join(f"{sha256(data)}  {name}" for name, data in sorted(artefacts.items())) + "\n"
    ).encode("utf-8")
    return artefacts


def _runs(data: bytes) -> list[list[pdfextract.TextRun]]:
    doc = pdfextract.Document.load(data)
    return [pdfextract.page_runs(doc, page) for page in doc.pages()]


def _found(runs: list[pdfextract.TextRun], text: str, bbox: list[float]) -> bool:
    x0, y0, x1, y1 = bbox
    return any(r.text == text and x0 - 0.01 <= r.x <= x1 and y0 <= r.y <= y1 for r in runs)


def verify_text_layer(artefacts: dict[str, bytes], vs_key: dict, sp_key: dict) -> list[str]:
    """Read the PDFs back and check what the keys say about their text. Returns problems."""
    problems: list[str] = []
    read: dict[str, list[list[pdfextract.TextRun]]] = {}
    versions = {v["id"]: v for v in vs_key["versions"]}  # type: ignore[index]
    for version in versions.values():
        runs = _runs(artefacts[version["file"]])
        read[version["id"]] = runs
        if len(runs) != version["page_count"]:
            problems.append(f"{version['file']}: {len(runs)} pages, the key says {version['page_count']}")
            continue
        for page in version["pages"]:
            page_runs = runs[page["page"] - 1]
            if not page["text_layer"]:
                if page_runs:
                    problems.append(f"{version['file']} page {page['page']}: a scan with {len(page_runs)} text runs")
                continue
            for name, value in page["stamp"].items():
                if not any(r.text == value for r in page_runs):
                    problems.append(f"{version['file']} page {page['page']}: stamp {name} {value!r} is not in the text layer")
    for transition in vs_key["transitions"]:  # type: ignore[index]
        for sheet in transition["sheets"]:
            for change in sheet.get("text_changes", []):
                if "before" in change and "bbox_before" in change:
                    pages = [sheet["from_page"]] if sheet["from_page"] else []
                    if not any(_found(read[transition["from"]][p - 1], change["before"], change["bbox_before"]) for p in pages):
                        problems.append(f"{transition['id']} {sheet['sheet_id']}: before {change['before']!r} not at its bbox")
                if "after" in change and "bbox_after" in change:
                    pages = sheet.get("to_pages") or ([sheet["to_page"]] if sheet["to_page"] else [])
                    if not any(_found(read[transition["to"]][p - 1], change["after"], change["bbox_after"]) for p in pages):
                        problems.append(f"{transition['id']} {sheet['sheet_id']}: after {change['after']!r} not at its bbox")

    sp_runs = {d["name"]: _runs(artefacts[d["file"]]) for d in sp_key["documents"]}  # type: ignore[index]
    for sheet in sp_key["sheets"]:  # type: ignore[index]
        page_runs = sp_runs[sheet["document"]][sheet["page"] - 1]
        for name, value in sheet["stamp"].items():
            if not any(r.text == value for r in page_runs):
                problems.append(f"sp1 {sheet['sheet_id']}: stamp {name} {value!r} is not in the text layer")
        for fragment in sheet["fragments"]:
            if not _found(page_runs, fragment["text"], fragment["bbox"]):
                problems.append(f"sp1 {sheet['sheet_id']}: fragment {fragment['key']} not at its bbox")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the synthetic comparison corpus.")
    parser.add_argument("--check", action="store_true",
                        help="verify the committed corpus against a fresh build; write nothing")
    args = parser.parse_args(argv)
    try:
        artefacts = build_all()
    except (BuildError, vs1.BuildError, sp1.BuildError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.check:
        failures: list[str] = []
        for name, data in sorted(artefacts.items()):
            path = OUT_DIR / name
            if not path.is_file():
                failures.append(f"fixtures/comparison/{name}: missing")
            elif path.read_bytes() != data:
                failures.append(f"fixtures/comparison/{name}: differs from a fresh build "
                                f"(committed {sha256(path.read_bytes())}, rebuilt {sha256(data)})")
        if failures:
            print("FAIL: the committed corpus does not match a fresh build:", file=sys.stderr)
            for failure in failures:
                print(f"  {failure}", file=sys.stderr)
            return 1
        for name, data in sorted(artefacts.items()):
            print(f"OK  fixtures/comparison/{name}  {sha256(data)}  {len(data)} bytes")
        return 0

    for name, data in sorted(artefacts.items()):
        path = OUT_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"wrote fixtures/comparison/{name}  {sha256(data)}  {len(data)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
