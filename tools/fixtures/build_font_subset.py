#!/usr/bin/env python3
"""Rebuild the committed `ARCorpusSans` font subset that the AR baseline embeds.

This is a *maintenance* tool, not part of the corpus build. It runs once, against a
source font on the build machine, and writes `tools/fixtures/assets/ARCorpusSans.ttf`.
`build_ar_corpus.py` then embeds that committed file and never touches a system font, so
regenerating the corpus does not depend on which fonts happen to be installed.

Run it again only when the baseline text starts using a character the subset lacks;
`build_ar_corpus.py` fails loudly in that case rather than dropping the glyph.

    python3 tools/fixtures/build_font_subset.py
    python3 tools/fixtures/build_font_subset.py --check

`--check` rebuilds in memory and compares against the committed asset without writing.

Licence: the source is DejaVu Sans, whose Bitstream Vera licence permits redistribution
and modification provided that a modified font is renamed away from the "Bitstream" and
"Vera" names and that the copyright and permission notice travels with every copy. The
subset is therefore named `ARCorpusSans`, the notice is embedded in the font's `name`
table, and the full text sits beside the asset in `ARCorpusSans-LICENCE.txt`.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ar_corpus import content, ttfsubset  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET = REPO_ROOT / "tools" / "fixtures" / "assets" / "ARCorpusSans.ttf"

FONT_NAME = "ARCorpusSans"

# Recorded so a source-font change is visible rather than silent. A different digest is a
# warning, not a hard stop: the subset is committed, and this tool only rebuilds it.
SOURCE_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
    Path("/Library/Fonts/DejaVuSans.ttf"),
)
RECORDED_SOURCE_SHA256 = "ae7b7855e115a5966d8b1b3f80f254ccc117ec86f9965e202ee2940453837280"

NOTICE = (
    "ARCorpusSans is a subset of DejaVu Sans, renamed as the Bitstream Vera licence "
    "requires of a modified font. Copyright (c) 2003 by Bitstream, Inc. All Rights "
    "Reserved. Bitstream Vera is a trademark of Bitstream, Inc. DejaVu changes are in "
    "public domain. Permission is hereby granted, free of charge, to any person "
    "obtaining a copy of the fonts accompanying this licence (\"Fonts\") and associated "
    "documentation files (the \"Font Software\"), to reproduce and distribute the Font "
    "Software, including without limitation the rights to use, copy, merge, publish, "
    "distribute, and/or sell copies of the Font Software, subject to the conditions in "
    "the accompanying ARCorpusSans-LICENCE.txt. THE FONT SOFTWARE IS PROVIDED \"AS IS\", "
    "WITHOUT WARRANTY OF ANY KIND."
)


def _find_source(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f"source font not found: {path}")
        return path
    for candidate in SOURCE_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise SystemExit(
        "no source font found. Pass --source /path/to/DejaVuSans.ttf. Searched: "
        + ", ".join(str(c) for c in SOURCE_CANDIDATES)
    )


def build(source_path: Path) -> bytes:
    source = source_path.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    if digest != RECORDED_SOURCE_SHA256:
        print(
            f"warning: {source_path} has sha256 {digest}, recorded is "
            f"{RECORDED_SOURCE_SHA256}. The rebuilt subset may differ from the "
            "committed asset.",
            file=sys.stderr,
        )
    result = ttfsubset.subset(
        source, content.character_set(), font_name=FONT_NAME, notice=NOTICE
    )
    return result.font_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="path to the source DejaVuSans.ttf")
    parser.add_argument(
        "--check", action="store_true",
        help="rebuild in memory and compare with the committed asset; write nothing",
    )
    args = parser.parse_args(argv)

    built = build(_find_source(args.source))
    digest = hashlib.sha256(built).hexdigest()

    if args.check:
        if not ASSET.is_file():
            print(f"FAIL: committed asset missing: {ASSET}", file=sys.stderr)
            return 1
        current = ASSET.read_bytes()
        if current != built:
            print(
                f"FAIL: {ASSET} does not match a fresh subset build\n"
                f"  committed sha256 {hashlib.sha256(current).hexdigest()}\n"
                f"  rebuilt   sha256 {digest}",
                file=sys.stderr,
            )
            return 1
        print(f"OK  {ASSET.relative_to(REPO_ROOT)}  sha256 {digest}  {len(built)} bytes")
        return 0

    ASSET.parent.mkdir(parents=True, exist_ok=True)
    ASSET.write_bytes(built)
    print(f"wrote {ASSET.relative_to(REPO_ROOT)}  sha256 {digest}  {len(built)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
