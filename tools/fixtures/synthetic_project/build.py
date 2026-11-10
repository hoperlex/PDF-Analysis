"""Build the synthetic production project: one portal bundle per section, the АР version series and
the АР stage pair, with answer keys and previews.

    .venv/bin/python -m synthetic_project.build OUT_DIR [--only EOM,AR] [--no-previews]

(run with `tools/fixtures` and `src` on PYTHONPATH; see README.md). Nothing here calls the network or
the application. The build refuses to write a bundle the portal validator rejects or an answer key
whose quotes are not on their pages.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import sys
from pathlib import Path

from .render import RenderError, dump_json, render, write_previews

# The product's order of sections (legacy fourteen, then ПЗ); the number prefixes the file names.
SECTIONS = ("AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS")


def _module(code: str):
    return importlib.import_module(f"synthetic_project.sec_{code.lower()}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--only", default="")
    ap.add_argument("--no-previews", action="store_true")
    ap.add_argument("--no-ar-family", action="store_true")
    args = ap.parse_args(argv)
    only = {c.strip().upper() for c in args.only.split(",") if c.strip()}
    out: Path = args.out
    (out / "sections").mkdir(parents=True, exist_ok=True)
    (out / "keys").mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"sections": [], "ar_family": None}
    failures: list[str] = []
    for number, code in enumerate(SECTIONS, start=1):
        if only and code not in only:
            continue
        try:
            module = _module(code)
        except ModuleNotFoundError as exc:
            if exc.name == f"synthetic_project.sec_{code.lower()}":
                print(f"{code}: no module yet, skipped")
                continue
            raise
        try:
            doc = module.build()
            if doc.code != code:
                raise RenderError(f"module sec_{code.lower()} built section {doc.code}")
            r = render(doc, number)
        except (RenderError, ValueError, KeyError) as exc:
            failures.append(f"{code}: {exc}")
            print(f"{code}: FAILED: {exc}", file=sys.stderr)
            continue
        name = f"{number:02d}_{code}_{r.stem}"
        (out / "sections" / f"{name}.zip").write_bytes(r.zip_bytes)
        (out / "keys" / f"{name}.answer_key.json").write_bytes(dump_json(r.answer_key))
        if not args.no_previews:
            write_previews(r, out / "previews" / name, [p.size for p in doc.pages])
        entry = {"number": number, "code": code, "abbr": doc.abbr, "name": doc.name, "file": f"sections/{name}.zip",
                 "stem": r.stem, "pages": len(doc.pages), "blocks": r.answer_key["blocks"],
                 "expected": len(doc.expected), "traps": len(doc.traps),
                 "zip_sha256": hashlib.sha256(r.zip_bytes).hexdigest(), "zip_bytes": len(r.zip_bytes)}
        manifest["sections"].append(entry)
        print(f"{code}: {name}.zip {len(r.zip_bytes)} B, {len(doc.pages)} pages, blocks {r.answer_key['blocks']}, "
              f"expected {len(doc.expected)}, traps {len(doc.traps)}")
    if not args.no_ar_family and (not only or "AR" in only or "ARFAM" in only):
        try:
            from . import ar_family
        except ModuleNotFoundError as exc:
            if exc.name != "synthetic_project.ar_family":
                raise
            print("ar_family: no module yet, skipped")
        else:
            manifest["ar_family"] = ar_family.write(out, previews=not args.no_previews)
    (out / "manifest.json").write_bytes(dump_json(manifest))
    if failures:
        print("FAILED:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print("BUILD OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
