#!/usr/bin/env python3
"""Package a portal export into the one ZIP an upload now takes.

    python3 tools/fixtures/assemble_portal_bundle.py <input_dir> <out.zip> [--stamp-audit FILE]

`<input_dir>` holds the portal's files side by side, named after the PDF's stem:
`<stem>.pdf`, `<stem>_blocks.json`, `<stem>_results.md`, and optionally `<stem>_results.html`
and `<stem>_stamp_audit.json`. Anything else in the directory is left out and listed. The
archive is written with the same deterministic writer as the fixtures, then judged by the
fixture validator; a bundle it refuses is deleted, not kept.

This is how a real export is packaged for a local run under `.local/`. It reads the
directory and writes one file; it copies nothing into the repository, and a real export's
bytes are never committed.

Exit status: 0 packaged and accepted, 1 refused by the validator, 2 the directory is not
a portal export.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portal_bundle import portal_format as fmt  # noqa: E402
from portal_bundle import validate, zipwrite  # noqa: E402


class NotAnExport(RuntimeError):
    """The input directory does not hold exactly one portal export."""


def find_members(directory: Path, stamp_audit: Path | None) -> dict[str, Path]:
    """Role -> file, from the names. The PDF decides the stem; the rest must follow it."""
    files = sorted(p for p in directory.iterdir() if p.is_file())
    pdfs = [p for p in files if p.name.endswith(".pdf")]
    if len(pdfs) != 1:
        raise NotAnExport(f"expected exactly one .pdf in the directory, found {len(pdfs)}")
    stem = pdfs[0].name[: -len(".pdf")]
    found = {fmt.ROLE_PDF: pdfs[0]}
    for role in (fmt.ROLE_BLOCKS, fmt.ROLE_RESULTS_MD, fmt.ROLE_RESULTS_HTML,
                 fmt.ROLE_STAMP_AUDIT):
        candidate = directory / (stem + fmt.ROLE_SUFFIX[role].decode("ascii"))
        if candidate.is_file():
            found[role] = candidate
    if stamp_audit is not None:
        found[fmt.ROLE_STAMP_AUDIT] = stamp_audit
    for role in fmt.REQUIRED_ROLES:
        if role not in found:
            raise NotAnExport(f"no {stem}{fmt.ROLE_SUFFIX[role].decode('ascii')} in the directory")
    return found


def build_members(found: dict[str, Path]) -> list[zipwrite.Member]:
    stem = found[fmt.ROLE_PDF].name[: -len(".pdf")]
    members = []
    for role in fmt.ROLE_ORDER:
        if role not in found:
            continue
        name = (stem + fmt.ROLE_SUFFIX[role].decode("ascii")).encode("utf-8")
        members.append(zipwrite.Member(
            name=name, payload=zipwrite.FromFile(found[role]),
            # The PDF is compressed already; the rest are text and shrink.
            method=zipwrite.STORED if role == fmt.ROLE_PDF else zipwrite.DEFLATED,
            deflate="zlib", flags=zipwrite.FLAG_UTF8,
        ))
    return members


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Package a portal export as a bundle ZIP.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--stamp-audit", type=Path, default=None,
                        help="a stamp audit to include, named after the PDF's stem")
    parser.add_argument("--max-member-bytes", type=int, default=fmt.MAX_UPLOAD_BYTES,
                        help="per-member bound the validator applies (default: the upload bound)")
    parser.add_argument("--max-stamp-audit-bytes", type=int, default=fmt.MiB)
    args = parser.parse_args(argv)

    try:
        found = find_members(args.input_dir, args.stamp_audit)
    except (NotAnExport, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    ignored = sorted(p.name for p in args.input_dir.iterdir()
                     if p.is_file() and p not in found.values())

    partial = args.out.with_name(args.out.name + ".part")
    zipwrite.write_zip(partial, build_members(found))
    verdict = validate.validate(partial, validate.Limits(
        member_bytes=args.max_member_bytes, stamp_audit_bytes=args.max_stamp_audit_bytes))
    if not verdict.accepted:
        partial.unlink()
        print("REFUSED: the validator rejects this bundle:", file=sys.stderr)
        for violation in verdict.violations:
            print(f"  {violation.constraint} (field {violation.field}): {violation.detail}",
                  file=sys.stderr)
        return 1
    partial.replace(args.out)

    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"wrote {args.out}  {digest}  {args.out.stat().st_size} bytes")
    for member in verdict.members:
        print(f"  {member.role:12} {member.size:>10} bytes  {member.name}")
    print(f"  {verdict.page_count} pages; blocks {verdict.block_counts}")
    if ignored:
        print(f"  left out: {', '.join(ignored)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
