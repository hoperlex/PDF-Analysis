#!/usr/bin/env python3
"""Build the synthetic portal bundles that sit beside the AR corpus.

    python3 tools/fixtures/build_portal_bundles.py           # write the bundles
    python3 tools/fixtures/build_portal_bundles.py --check   # verify, write nothing

Every synthetic PDF in `fixtures/synthetic/ar/` gets a bundle (the PDF, the portal's block
list, the recognised-text markdown, and for the complete one the HTML and a stamp audit).
The bundles are written to `fixtures/synthetic/ar/bundles/`, described by
`bundle_manifest.json` -- the oracle INGEST and the judges read -- and covered by the
`bundles/` lines this script appends to `fixtures/synthetic/ar/SHA256SUMS`.

`--check` rebuilds everything in memory and compares it byte for byte with what is
committed, then judges the COMMITTED archives with the validator and compares each verdict
with the manifest. A bundle on disk can be wrong in ways a fresh build never is.

What the build refuses to do: write a bundle whose own validator verdict is not the one it
was declared to have, or build one around a PDF that differs from the committed PDF.

Pure standard library, like `build_ar_corpus.py`, which owns the PDFs and the other lines
of `SHA256SUMS`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ar_corpus  # noqa: E402
from ar_corpus import document, negatives  # noqa: E402
from portal_bundle import committed, portal_format as fmt, validate, zipscan  # noqa: E402
from portal_bundle.bundle import BuiltBundle, BundleError, build_bundle  # noqa: E402

REPO_ROOT = build_ar_corpus.REPO_ROOT
CORPUS_DIR = build_ar_corpus.OUT_DIR
BUNDLE_DIR = CORPUS_DIR / "bundles"
MANIFEST_NAME = "bundle_manifest.json"
CHECKSUM_PATH = CORPUS_DIR / build_ar_corpus.CHECKSUM_NAME
PREFIX = "bundles/"

MANIFEST_SCHEMA = "ar-portal-bundles/1"

# Refusals of the PDF member are answered under the existing envelope's fields; refusals of
# the archive and its other members under `file`.
CHECK_LIMITS = validate.Limits(member_bytes=fmt.MAX_UPLOAD_BYTES, stamp_audit_bytes=fmt.MiB)


class BuildError(RuntimeError):
    """An invariant the bundles are not allowed to be written without."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_pdfs() -> dict[str, bytes]:
    """The corpus PDFs a bundle carries, rebuilt by the corpus' own generators.

    A bundle's PDF member must be the committed PDF's bytes, so a rebuilt PDF that differs
    from the committed one stops the build: the corpus has to be regenerated first.
    """
    font = build_ar_corpus.load_font()
    built = {
        committed.BASELINE_PDF: document.build_baseline(font),
        committed.IMAGE_ONLY_PDF: negatives.build_image_only(font),
        committed.ENCRYPTED_PDF: negatives.build_encrypted(font),
        committed.TOO_MANY_PAGES_PDF: negatives.build_too_many_pages(font),
    }
    for relative, data in built.items():
        path = REPO_ROOT / relative
        if path.is_file() and path.read_bytes() != data:
            raise BuildError(
                f"{relative} differs from what the corpus generator builds; run "
                "tools/fixtures/build_ar_corpus.py first"
            )
    return built


def build_bundles() -> list[tuple[committed.CommittedBundle, BuiltBundle]]:
    pdfs = source_pdfs()
    built = []
    for spec in committed.COMMITTED:
        files = spec.make(pdfs[spec.source_pdf])
        built.append((spec, build_bundle(files, expect=spec.expect, limits=CHECK_LIMITS)))
    return built


def _bundle_entry(spec: committed.CommittedBundle, bundle: BuiltBundle) -> dict[str, object]:
    verdict = bundle.verdict
    refusal = None
    if spec.expect is not None:
        refusal = {"constraint": spec.expect, "field": validate.CONSTRAINT_FIELDS[spec.expect]}
    members = [
        {"name": m.name, "role": m.role, "size": m.size, "sha256": m.sha256}
        for m in verdict.members
    ]
    entry: dict[str, object] = {
        "file": spec.file,
        "path": f"fixtures/synthetic/ar/bundles/{spec.file}",
        "size": len(bundle.data),
        "sha256": sha256(bundle.data),
        "source_pdf": spec.source_pdf,
        "stem": bundle.files.stem,
        "description": spec.description,
        "page_count": bundle.files.page_count,
        "members": members,
        "blocks": verdict.block_counts,
        "expected": "accepted" if spec.expect is None else "refused",
        "refusal": refusal,
    }
    if bundle.files.defects:
        entry["seeded_text_defects"] = [
            {"page": d.page_index + 1, "block_id": d.block_id, "kind": d.kind,
             "flaggable": d.flaggable, "original": d.original, "recognised": d.recognised}
            for d in bundle.files.defects
        ]
    return entry


def build_manifest(built: list[tuple[committed.CommittedBundle, BuiltBundle]]) -> dict[str, object]:
    return {
        "schema": MANIFEST_SCHEMA,
        "synthetic": True,
        "notice": (
            "Synthetic bundles. Every byte was written by tools/fixtures/build_portal_bundles.py "
            "from the synthetic AR corpus; no customer, production or portal-export bytes, and "
            "no real organisation, address or person. The crop URLs sit under the reserved "
            ".invalid domain and are never to be fetched."
        ),
        "generated_by": "tools/fixtures/build_portal_bundles.py",
        "regenerate": "python3 tools/fixtures/build_portal_bundles.py",
        "verify": "python3 tools/fixtures/build_portal_bundles.py --check",
        "rules": {
            "max_entries": fmt.MAX_ENTRIES,
            "max_total_uncompressed_bytes": fmt.MAX_TOTAL_UNCOMPRESSED_BYTES,
            "max_compression_ratio": fmt.MAX_COMPRESSION_RATIO,
            "max_upload_bytes": fmt.MAX_UPLOAD_BYTES,
            "pages": [fmt.MIN_PAGES, fmt.MAX_PAGES],
        },
        "refusal_fields": (
            "A refusal of the archive or of a member other than the PDF is answered under "
            "field `file`. A refusal of the PDF member keeps the existing envelope's field: "
            "`not_encrypted` under `content`, `every_page_has_extractable_text` under "
            "`page_text`. If INGEST moves them, this oracle moves with them."
        ),
        "text_layer_rule": (
            "A page needs a text layer or at least one portal block (of any type). "
            "Where a page has no text layer, its text is recognised text and nothing else."
        ),
        "bundles": [_bundle_entry(spec, bundle) for spec, bundle in built],
    }


def manifest_bytes(manifest: dict[str, object]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def checksum_bytes(existing: bytes, entries: list[tuple[str, bytes]]) -> bytes:
    """`SHA256SUMS` with the corpus generator's lines first and unchanged, then ours."""
    kept = [line for line in existing.decode("utf-8").splitlines()
            if line.strip() and not line.split("  ", 1)[-1].startswith(PREFIX)]
    ours = [f"{sha256(data)}  {name}" for name, data in entries]
    return ("\n".join(kept + ours) + "\n").encode("utf-8")


def build_all() -> list[tuple[Path, bytes]]:
    built = build_bundles()
    manifest = manifest_bytes(build_manifest(built))
    artefacts: list[tuple[Path, bytes]] = [
        (BUNDLE_DIR / spec.file, bundle.data) for spec, bundle in sorted(
            built, key=lambda pair: pair[0].file)
    ]
    artefacts.append((BUNDLE_DIR / MANIFEST_NAME, manifest))
    existing = CHECKSUM_PATH.read_bytes() if CHECKSUM_PATH.is_file() else b""
    sums = checksum_bytes(
        existing, [(PREFIX + path.name, data) for path, data in artefacts])
    artefacts.append((CHECKSUM_PATH, sums))
    return artefacts


def judge_committed() -> list[str]:
    """Judge the archives on disk, not the fresh build, against the committed manifest."""
    problems: list[str] = []
    manifest_path = BUNDLE_DIR / MANIFEST_NAME
    if not manifest_path.is_file():
        return [f"{manifest_path.relative_to(REPO_ROOT)}: missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["bundles"]:
        path = REPO_ROOT / entry["path"]
        if not path.is_file():
            problems.append(f"{entry['path']}: missing")
            continue
        data = path.read_bytes()
        if sha256(data) != entry["sha256"] or len(data) != entry["size"]:
            problems.append(f"{entry['path']}: differs from the manifest's size and digest")
        verdict = validate.validate(data, CHECK_LIMITS)
        wanted = () if entry["refusal"] is None else (entry["refusal"]["constraint"],)
        if verdict.constraints != wanted:
            problems.append(f"{entry['path']}: the validator says {verdict.constraints or 'accepted'},"
                            f" the manifest says {wanted or 'accepted'}")
        pdf = (REPO_ROOT / entry["source_pdf"]).read_bytes()
        with zipscan.Archive.from_bytes(data) as archive:
            for member in archive.load_entries():
                if member.name.endswith(b".pdf"):
                    stored = b"".join(archive.read_chunks(member))
                    if stored != pdf:
                        problems.append(f"{entry['path']}: the PDF member is not {entry['source_pdf']}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the synthetic portal bundles.")
    parser.add_argument("--check", action="store_true",
                        help="verify the committed bundles against a fresh build; write nothing")
    args = parser.parse_args(argv)

    try:
        artefacts = build_all()
    except (BuildError, BundleError, build_ar_corpus.BuildError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.check:
        failures: list[str] = []
        for path, data in artefacts:
            relative = path.relative_to(REPO_ROOT)
            if not path.is_file():
                failures.append(f"{relative}: missing")
            elif path.read_bytes() != data:
                failures.append(
                    f"{relative}: committed sha256 {sha256(path.read_bytes())} != rebuilt "
                    f"sha256 {sha256(data)}")
        failures += judge_committed()
        if failures:
            print("FAIL: the committed bundles do not match a fresh build:", file=sys.stderr)
            for failure in failures:
                print(f"  {failure}", file=sys.stderr)
            return 1
        for path, data in artefacts:
            print(f"OK  {path.relative_to(REPO_ROOT)}  {sha256(data)}  {len(data)} bytes")
        return 0

    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    for path, data in artefacts:
        path.write_bytes(data)
        print(f"wrote {path.relative_to(REPO_ROOT)}  {sha256(data)}  {len(data)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
