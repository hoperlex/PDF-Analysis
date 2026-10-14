"""Which rule does this upload break? A fixture-side reference for the bundle envelope.

This mirrors plan B3.1 and B3.5 and the contract's `portal-blocks.schema.json` with its
`x-envelope-rules`, and answers with the constraint names `W55B-SEAL-01` registered for
`validation_failed`. It is not the product's envelope (that is INGEST's, under `src/`); it
is what lets a fixture say which rule it was built to break, and what lets the generator
refuse to write a bundle that breaks one by accident.

Rules run in gates, because a later rule is meaningless once an earlier one fails (a
member cannot be unpacked if the directory cannot be read), and a gate reports every
rule it found so a negative can be shown to break exactly its own:

    0  size of the upload, ZIP magic, directory, entry count
    1  per-entry and set rules: directory entries, names, links, encryption, method,
       duplicates, the member set, one stem
    2  declared sizes, then declared compression ratios
    3  the members unpacked and counted -- the declared sizes are never trusted
    4  contents: the PDF, the block list, the markdown against it, the stamp audit

Within gate 3 the first rule to trip ends it: bytes are counted as they come out and
unpacking stops there.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import zlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ar_corpus import pdfextract

from . import portal_format as fmt
from . import schemacheck, zipscan
from .pdffacts import PageFacts, read_pages

REPO_ROOT = Path(__file__).resolve().parents[3]
BLOCKS_SCHEMA = REPO_ROOT / "contracts" / "analysis" / "v1" / "portal-blocks.schema.json"

# The block-list envelope rules this module implements (one per entry of the schema's
# `x-envelope-rules`). If the contract gains one, `load_schema` refuses until it is added.
IMPLEMENTED_ENVELOPE_RULES = 5

# The registered classifier values and the field each is answered under. Bundle rules
# answer under `file`; the PDF member keeps the existing envelope's fields.
FIELD_FILE = "file"
CONSTRAINT_FIELDS = {
    "max_bytes": FIELD_FILE,
    "portal_bundle_required": FIELD_FILE,
    "bundle_unreadable": FIELD_FILE,
    "bundle_entry_count": FIELD_FILE,
    "bundle_directory_entry": FIELD_FILE,
    "bundle_member_name": FIELD_FILE,
    "bundle_symlink": FIELD_FILE,
    "bundle_encrypted_member": FIELD_FILE,
    "bundle_compression_method": FIELD_FILE,
    "bundle_duplicate_member": FIELD_FILE,
    "bundle_stem_mismatch": FIELD_FILE,
    "bundle_member_set": FIELD_FILE,
    "bundle_member_size": FIELD_FILE,
    "bundle_total_size": FIELD_FILE,
    "bundle_compression_ratio": FIELD_FILE,
    "blocks_json_invalid": FIELD_FILE,
    "blocks_page_count": FIELD_FILE,
    "blocks_count": FIELD_FILE,
    "results_blocks_mismatch": FIELD_FILE,
    "stamp_audit_invalid": FIELD_FILE,
    "pdf_magic_bytes": "content",
    "not_encrypted": "content",
    "parseable_pdf": "content",
    "page_count": "page_count",
    "every_page_has_extractable_text": "page_text",
}

_HEADER = re.compile(r"^### BLOCK #(\d+) \[([A-Za-z]+)\]: (\S+)[ \t]*$", re.MULTILINE)
_DRIVE_LETTER = re.compile(rb"^[A-Za-z]:")
_STRONG_ENCRYPTION = 0x0040
_PDF_READ_ERRORS = (pdfextract.PdfParseError, ValueError, KeyError, IndexError, TypeError,
                    RecursionError, zlib.error)


@dataclass(frozen=True)
class Limits:
    """The bounds a validation runs under.

    `member_bytes` and `stamp_audit_bytes` have no default on purpose: they are INGEST's
    to choose and the freeze does not fix them. The others are the freeze's values.
    """

    member_bytes: int
    stamp_audit_bytes: int
    entries: int = fmt.MAX_ENTRIES
    total_bytes: int = fmt.MAX_TOTAL_UNCOMPRESSED_BYTES
    ratio: int = fmt.MAX_COMPRESSION_RATIO
    upload_bytes: int = fmt.MAX_UPLOAD_BYTES
    min_pages: int = fmt.MIN_PAGES
    max_pages: int = fmt.MAX_PAGES


@dataclass(frozen=True)
class Violation:
    constraint: str
    field: str
    detail: str


@dataclass(frozen=True)
class MemberFact:
    name: str                    # decoded for display only
    role: str | None
    size: int                    # actual, counted while unpacking
    sha256: str


@dataclass(frozen=True)
class Verdict:
    violations: tuple[Violation, ...]
    members: tuple[MemberFact, ...] = ()
    stem: str | None = None
    page_count: int | None = None
    block_counts: dict[str, int] | None = None

    @property
    def accepted(self) -> bool:
        return not self.violations

    @property
    def constraints(self) -> tuple[str, ...]:
        """The distinct constraint names, in the order they were found."""
        seen: list[str] = []
        for violation in self.violations:
            if violation.constraint not in seen:
                seen.append(violation.constraint)
        return tuple(seen)


def _violation(constraint: str, detail: str) -> Violation:
    return Violation(constraint, CONSTRAINT_FIELDS[constraint], detail)


def _refused(constraint: str, detail: str) -> Verdict:
    return Verdict((_violation(constraint, detail),))


@lru_cache(maxsize=1)
def load_schema() -> dict:
    schema = json.loads(BLOCKS_SCHEMA.read_text(encoding="utf-8"))
    schemacheck.assert_supported(schema)
    rules = schema.get("x-envelope-rules", [])
    if len(rules) != IMPLEMENTED_ENVELOPE_RULES:
        raise schemacheck.SchemaSubsetError(
            f"the contract lists {len(rules)} envelope rules, this validator implements "
            f"{IMPLEMENTED_ENVELOPE_RULES}"
        )
    return schema


def _ratio_exceeded(size: int, compressed: int, ratio: int) -> bool:
    return size > ratio * compressed


def _is_directory_like(name: bytes) -> bool:
    return name.endswith(b"/") or name.startswith(b"__MACOSX/")


def _duplicate_key(entry: zipscan.Entry) -> str:
    shown = zipscan.decode_display_name(entry.name, entry.flags, entry.extra)
    folded = unicodedata.normalize("NFC", shown).casefold()
    return unicodedata.normalize("NFC", folded)


def _entry_rules(entries: tuple[zipscan.Entry, ...]) -> list[Violation]:
    """Gate 1: rules about single entries, then about the set, all collected."""
    found: list[Violation] = []
    for e in entries:
        n = e.name
        if _is_directory_like(n):
            found.append(_violation("bundle_directory_entry", f"entry {e.index}"))
        if (n.startswith(b"/") or b"\\" in n or _DRIVE_LETTER.match(n)
                or b".." in n.split(b"/")):
            found.append(_violation("bundle_member_name", f"entry {e.index}"))
        if e.is_symlink:
            found.append(_violation("bundle_symlink", f"entry {e.index}"))
        if e.is_encrypted or e.flags & _STRONG_ENCRYPTION:
            found.append(_violation("bundle_encrypted_member", f"entry {e.index}"))
        if e.method not in (0, 8):
            found.append(_violation("bundle_compression_method",
                                    f"entry {e.index}: method {e.method}"))

    groups: dict[str, list[int]] = {}
    for e in entries:
        groups.setdefault(_duplicate_key(e), []).append(e.index)
    for indexes in groups.values():
        if len(indexes) > 1:
            found.append(_violation("bundle_duplicate_member", f"entries {indexes}"))

    # The member set is judged on what is left once directory-like entries and repeated
    # names are set aside: those have a rule of their own.
    members: list[zipscan.Entry] = []
    taken: set[str] = set()
    for e in entries:
        if _is_directory_like(e.name) or _duplicate_key(e) in taken:
            continue
        taken.add(_duplicate_key(e))
        members.append(e)
    by_role: dict[str, list[zipscan.Entry]] = {}
    set_problems: list[Violation] = []
    for e in members:
        role = fmt.role_of(e.name)
        if role is None:
            set_problems.append(_violation("bundle_member_set", f"entry {e.index}: unknown member"))
        else:
            by_role.setdefault(role, []).append(e)
    for role in fmt.REQUIRED_ROLES:
        if len(by_role.get(role, [])) != 1:
            set_problems.append(_violation(
                "bundle_member_set", f"{role}: {len(by_role.get(role, []))} present, 1 required"))
    for role in fmt.OPTIONAL_ROLES:
        if len(by_role.get(role, [])) > 1:
            set_problems.append(_violation("bundle_member_set", f"{role}: repeated"))
    found += set_problems
    if not set_problems:
        stems = {fmt.stem_of(e.name, role) for role, es in by_role.items() for e in es}
        if len(stems) > 1:
            found.append(_violation("bundle_stem_mismatch", f"{len(stems)} different stems"))
    return found


def _declared_size_rules(entries: tuple[zipscan.Entry, ...], limits: Limits) -> list[Violation]:
    found = [_violation("bundle_member_size", f"entry {e.index}: declares {e.size} bytes")
             for e in entries if e.size > limits.member_bytes]
    if sum(e.size for e in entries) > limits.total_bytes:
        found.append(_violation("bundle_total_size", "the declared sizes add up past the bound"))
    return found


def _declared_ratio_rules(entries: tuple[zipscan.Entry, ...], archive_size: int,
                          limits: Limits) -> list[Violation]:
    found = [_violation("bundle_compression_ratio", f"entry {e.index}")
             for e in entries if _ratio_exceeded(e.size, e.compressed_size, limits.ratio)]
    if _ratio_exceeded(sum(e.size for e in entries), archive_size, limits.ratio):
        found.append(_violation("bundle_compression_ratio", "the archive as a whole"))
    return found


@dataclass
class _Unpacked:
    contents: dict[str, bytes]
    facts: list[MemberFact]


def _unpack(archive: zipscan.Archive, entries: tuple[zipscan.Entry, ...],
            limits: Limits) -> _Unpacked | Verdict:
    """Gate 3: unpack every member, counting the bytes that actually come out."""
    contents: dict[str, bytes] = {}
    facts: list[MemberFact] = []
    total = 0
    for e in entries:
        role = fmt.role_of(e.name)
        digest = hashlib.sha256()
        keep = bytearray()
        actual = 0
        crc = 0
        try:
            for chunk in archive.read_chunks(e):
                actual += len(chunk)
                total += len(chunk)
                if actual > limits.member_bytes:
                    return _refused("bundle_member_size", f"entry {e.index}: more than the bound")
                if total > limits.total_bytes:
                    return _refused("bundle_total_size", "the unpacked members pass the bound")
                if actual > e.size:
                    # `W55B-FIX` (X-5), as the product: a member's own declaration bounds its
                    # count, so a header that lies small stops here, a piece past its word.
                    return _refused(
                        "stamp_audit_invalid" if role == fmt.ROLE_STAMP_AUDIT
                        else "bundle_member_size",
                        f"entry {e.index}: unpacks past the {e.size} bytes it declares")
                crc = zlib.crc32(chunk, crc)
                digest.update(chunk)
                if role != fmt.ROLE_RESULTS_HTML:
                    keep += chunk
        except zipscan.ArchiveError as exc:
            return _refused("bundle_unreadable", str(exc))
        if actual != e.size:
            return _refused("bundle_unreadable",
                            f"entry {e.index}: declares {e.size} bytes, unpacks to {actual}")
        if crc & 0xFFFFFFFF != e.crc:
            return _refused("bundle_unreadable", f"entry {e.index}: the CRC-32 does not match")
        if _ratio_exceeded(actual, e.compressed_size, limits.ratio):
            return _refused("bundle_compression_ratio", f"entry {e.index}: unpacked")
        shown = zipscan.decode_display_name(e.name, e.flags, e.extra)
        facts.append(MemberFact(shown, role, actual, digest.hexdigest()))
        if role is not None and role != fmt.ROLE_RESULTS_HTML:
            contents[role] = bytes(keep)
    if _ratio_exceeded(total, archive.size, limits.ratio):
        return _refused("bundle_compression_ratio", "the archive as a whole, unpacked")
    return _Unpacked(contents, facts)


def _check_pdf(pdf: bytes, limits: Limits) -> tuple[list[Violation], tuple[PageFacts, ...] | None]:
    if pdf[:5] != b"%PDF-":
        return [_violation("pdf_magic_bytes", "the PDF member does not begin with %PDF-")], None
    try:
        pages = read_pages(pdf)
    except pdfextract.EncryptedPdfError:
        return [_violation("not_encrypted", "the PDF member is encrypted")], None
    except _PDF_READ_ERRORS as exc:
        return [_violation("parseable_pdf", f"the PDF member cannot be read: {exc}")], None
    if not limits.min_pages <= len(pages) <= limits.max_pages:
        return [_violation("page_count", f"{len(pages)} pages")], None
    return [], pages


def _reject_constant(token: str) -> object:
    raise ValueError(f"the non-finite number {token} is not JSON")


def _check_blocks(raw: bytes) -> tuple[list[Violation], dict | None]:
    """The block list against the pinned schema and its envelope rules."""
    def invalid(detail: str) -> tuple[list[Violation], None]:
        return [_violation("blocks_json_invalid", detail)], None

    try:
        document = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        return invalid(f"not JSON: {exc}")
    problems = schemacheck.check(document, load_schema())
    if problems:
        return invalid("; ".join(problems[:5]))

    pages = document["pages"]
    if [p["page_index"] for p in pages] != list(range(len(pages))):
        return invalid("pages[].page_index does not run 0..n-1")
    ids = [b["block_id"] for b in document["blocks"]]
    if len(set(ids)) != len(ids):
        return invalid("blocks[].block_id is not unique")
    for block in document["blocks"]:
        if block["page_index"] >= len(pages):
            return invalid(f"{block['block_id']}: page_index names no page")
        x0, y0, x1, y1 = block["coords_norm"]
        if not (x0 < x1 and y0 < y1):
            return invalid(f"{block['block_id']}: coords_norm is not x0<x1, y0<y1")
    return [], document


def _check_block_ceilings(document: dict) -> list[Violation]:
    """The block ceilings (`W55B-FIX`, X-4): per page, per bundle, and IMAGE blocks per bundle."""
    blocks = document["blocks"]
    per_page: dict[int, int] = {}
    for block in blocks:
        per_page[block["page_index"]] = per_page.get(block["page_index"], 0) + 1
    images = sum(1 for block in blocks if block["block_type"] == fmt.KIND_IMAGE)
    if len(blocks) > fmt.MAX_BLOCKS:
        return [_violation("blocks_count", f"{len(blocks)} blocks, at most {fmt.MAX_BLOCKS}")]
    if images > fmt.MAX_IMAGE_BLOCKS:
        return [_violation("blocks_count", f"{images} IMAGE blocks, at most {fmt.MAX_IMAGE_BLOCKS}")]
    if max(per_page.values(), default=0) > fmt.MAX_BLOCKS_PER_PAGE:
        return [_violation("blocks_count",
                           f"a page holds more than {fmt.MAX_BLOCKS_PER_PAGE} blocks")]
    return []


def _check_markdown(raw: bytes, document: dict) -> list[Violation]:
    """TEXT and IMAGE blocks and markdown headers agree both ways; a stamp has no header."""
    def mismatch(detail: str) -> list[Violation]:
        return [_violation("results_blocks_mismatch", detail)]

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return mismatch("the recognised-text markdown is not valid UTF-8")
    headers: dict[str, list[str]] = {}
    for _ordinal, kind, identifier in _HEADER.findall(text):
        headers.setdefault(identifier, []).append(kind.lower())
    expected = {b["block_id"]: b["block_type"] for b in document["blocks"]
                if b["block_type"] in (fmt.KIND_TEXT, fmt.KIND_IMAGE)}
    for identifier, kind in expected.items():
        if headers.get(identifier) != [kind]:
            return mismatch(f"{identifier}: expected one {kind} header, found "
                            f"{headers.get(identifier, [])}")
    extra = sorted(set(headers) - set(expected))
    if extra:
        return mismatch(f"{len(extra)} header(s) for blocks the list does not hold as TEXT or IMAGE")
    return []


def _check_stamp_audit(raw: bytes, limits: Limits) -> list[Violation]:
    if len(raw) > limits.stamp_audit_bytes:
        return [_violation("stamp_audit_invalid", "over the size cap")]
    try:
        json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return [_violation("stamp_audit_invalid", "not JSON")]
    return []


def _check_contents(unpacked: _Unpacked, limits: Limits) -> Verdict:
    """Gate 4. Each check runs when the facts it needs are known."""
    found: list[Violation] = []
    contents = unpacked.contents

    pdf_problems, pages = _check_pdf(contents[fmt.ROLE_PDF], limits)
    found += pdf_problems
    block_problems, document = _check_blocks(contents[fmt.ROLE_BLOCKS])
    found += block_problems
    if document is not None:
        found += _check_block_ceilings(document)

    if document is not None:
        found += _check_markdown(contents[fmt.ROLE_RESULTS_MD], document)
    page_count_known = pages is not None and document is not None
    if page_count_known and len(document["pages"]) != len(pages):
        found.append(_violation(
            "blocks_page_count",
            f"the block list has {len(document['pages'])} pages, the PDF has {len(pages)}"))
    elif page_count_known:
        with_block = {b["page_index"] for b in document["blocks"]}
        bare = [i + 1 for i, p in enumerate(pages) if not p.has_text and i not in with_block]
        if bare:
            found.append(_violation("every_page_has_extractable_text",
                                    f"page(s) {bare} have neither a text layer nor a block"))
    if fmt.ROLE_STAMP_AUDIT in contents:
        found += _check_stamp_audit(contents[fmt.ROLE_STAMP_AUDIT], limits)

    counts = None
    if document is not None:
        counts = {kind: sum(1 for b in document["blocks"] if b["block_type"] == kind)
                  for kind in fmt.KINDS}
    pdf_name = next((m.name for m in unpacked.facts if m.role == fmt.ROLE_PDF), "")
    return Verdict(
        tuple(found), tuple(unpacked.facts), stem=pdf_name[: -len(".pdf")],
        page_count=len(pages) if pages is not None else None, block_counts=counts,
    )


def validate(source: bytes | Path, limits: Limits) -> Verdict:
    """Judge an upload: the bytes of a ZIP, or a file holding them."""
    if isinstance(source, Path):
        size = source.stat().st_size
        with source.open("rb") as handle:
            head = handle.read(4)
    else:
        size, head = len(source), source[:4]

    if size > limits.upload_bytes:
        return _refused("max_bytes", f"{size} bytes")
    if head not in zipscan.ZIP_MAGICS:
        return _refused("portal_bundle_required", "the part is not a ZIP")
    try:
        archive = (zipscan.Archive.from_path(source) if isinstance(source, Path)
                   else zipscan.Archive.from_bytes(source))
    except zipscan.ArchiveError as exc:
        return _refused("bundle_unreadable", str(exc))
    with archive:
        if archive.declared_count > limits.entries:
            return _refused("bundle_entry_count", f"{archive.declared_count} entries")
        try:
            entries = archive.load_entries()
        except zipscan.ArchiveError as exc:
            return _refused("bundle_unreadable", str(exc))

        for rules in (
            lambda: _entry_rules(entries),
            lambda: _declared_size_rules(entries, limits),
            lambda: _declared_ratio_rules(entries, archive.size, limits),
        ):
            found = rules()
            if found:
                return Verdict(tuple(found))

        unpacked = _unpack(archive, entries, limits)
        if isinstance(unpacked, Verdict):
            return unpacked
    return _check_contents(unpacked, limits)
