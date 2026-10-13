#!/usr/bin/env python3
"""Write the browser journey's generated inputs: the two uploads that are never committed.

    python3 tools/fixtures/build_journey_inputs.py <dir>     # write them into <dir>
    python3 tools/fixtures/build_journey_inputs.py --list    # print their names, write nothing
    python3 tools/fixtures/build_journey_inputs.py --check   # build, judge, delete

The PC-01 journey's refusal drive (`tests/e2e/pc01/journey/refusals.mjs`) attaches files
through the application's own file control. Four of its six files are committed. These two
are not, because the limit they sit past is too large to commit or exists only to sit one
step past it:

    oversize_bundle.zip    a SPARSE file of 251 MiB that begins with a ZIP's first bytes.
                           It breaks the browser's 250 MiB pre-check, so no byte of it is
                           ever sent. It is made with `truncate`, so it costs a few
                           kilobytes of disk; if the file system does not honour holes,
                           the build removes the file and fails rather than allocate 251 MiB.
    bundle_501_pages.zip   a portal bundle around a 501-page text PDF: the smallest
                           archive past the 500-page limit, refused by the server as
                           `page_count`. It is a few hundred KiB.

The journey is Node and the builders are Python (`portal_bundle/generated.py`), so the
runner calls this once, into a temporary directory it deletes afterwards. Nothing is written
to the repository. Standard library only, like the rest of `tools/fixtures`.

Exit status: 0 done, 1 an input could not be built as declared, 2 a usage error.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

#: The generated files, by name. `manifest.json` (`refusals.generated.files`) declares the same
#: names and `tests/e2e/test_pc01_journey_conformance.py` holds the two lists equal.
OVERSIZE = "oversize_bundle.zip"
PAGES_501 = "bundle_501_pages.zip"
NAMES = (OVERSIZE, PAGES_501)

#: How far past the limit the stand-in goes, so it is over the bound by more than a byte.
MARGIN_BYTES = 1024 * 1024
#: A sparse file takes a few blocks. More than this means the file system allocated it.
MAX_ALLOCATED_BYTES = 1024 * 1024


def build(directory: Path) -> dict[str, Path]:
    """Write both inputs into `directory` and return them by name."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ar_corpus import envelope
    from portal_bundle import generated

    directory.mkdir(parents=True, exist_ok=True)

    oversize = generated.oversize_sparse_file(directory / OVERSIZE, envelope.MAX_BYTES + MARGIN_BYTES)
    stat = oversize.stat()
    allocated = getattr(stat, "st_blocks", 0) * 512
    if stat.st_size <= envelope.MAX_BYTES or allocated > MAX_ALLOCATED_BYTES:
        oversize.unlink()
        raise SystemExit(
            f"{OVERSIZE}: {stat.st_size} bytes long and {allocated} allocated. It must be past "
            f"{envelope.MAX_BYTES} bytes and sparse; this file system did not give a hole, and a "
            f"{stat.st_size}-byte file is not worth allocating. Use a directory on a file system "
            "that supports sparse files."
        )

    pages = directory / PAGES_501
    pages.write_bytes(generated.bundle_with_pages(envelope.MAX_PAGES + 1))
    return {OVERSIZE: oversize, PAGES_501: pages}


def check() -> None:
    """Build into a temporary directory, judge what came out, delete it."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ar_corpus import envelope
    from portal_bundle import generated

    scratch = Path(tempfile.mkdtemp(prefix="journey-inputs-"))
    try:
        built = build(scratch)
        if sorted(built) != sorted(NAMES):
            raise SystemExit(f"built {sorted(built)}, declared {sorted(NAMES)}")
        head = built[OVERSIZE].read_bytes()[:4]
        if head != generated.OVERSIZE_MAGIC:
            raise SystemExit(f"{OVERSIZE} begins {head!r}, not a ZIP's first bytes")
        if built[OVERSIZE].stat().st_size <= envelope.MAX_BYTES:
            raise SystemExit(f"{OVERSIZE} is not past {envelope.MAX_BYTES} bytes")
        if built[PAGES_501].read_bytes()[:4] != generated.OVERSIZE_MAGIC:
            raise SystemExit(f"{PAGES_501} is not a ZIP")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("directory", nargs="?", type=Path, help="where to write the inputs")
    parser.add_argument("--list", action="store_true", help="print the names and exit")
    parser.add_argument("--check", action="store_true", help="build, judge and delete")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(NAMES))
        return 0
    if args.check:
        check()
        print(f"journey inputs OK: {', '.join(NAMES)}")
        return 0
    if args.directory is None:
        parser.error("a directory is required (or --list, or --check)")
    built = build(args.directory)
    for name, path in built.items():
        print(f"{name}\t{path.stat().st_size}\t{os.fspath(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
