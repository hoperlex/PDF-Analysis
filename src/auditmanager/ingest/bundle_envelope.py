"""What the members of a portal bundle say: the content half of the admission envelope.

`W55B-INGEST-01` (plan sections B3.2 and B3.5). :mod:`auditmanager.ingest.bundle_archive`
has already judged the archive and written the members out; this module judges them, in
the order that keeps a refusal attributable to one rule:

1. the PDF member, by the very rules of a bare PDF (:func:`~auditmanager.ingest.envelope.inspect_pdf`):
   a PDF header, at most 250 MiB, not encrypted, parseable, one to five hundred pages;
   its refusals keep their ``field``, ``constraint`` and message;
2. ``_blocks.json`` against the pinned schema ``contracts/analysis/v1/portal-blocks.schema.json``
   and its ``x-envelope-rules`` (``blocks_json_invalid``);
3. ``_results.md`` against the block list, **both ways**: every TEXT and IMAGE block has exactly
   one header of the same type, and the markdown has no header for any other block -- a STAMP
   block has none (``results_blocks_mismatch``);
4. the block list describes as many pages as the PDF has (``blocks_page_count``);
5. every page has an embedded text layer **or** at least one portal block of any type
   (``every_page_has_extractable_text``, field ``page_text``);
6. the stamp audit, when there is one, is JSON (``stamp_audit_invalid``).

**OCR is always marked.** A page that rests on a portal block has recognised text, kept as
its own artifact; nothing here merges it into a text layer, and the three counts below keep the
two apart.

``jsonschema`` is not in the lock, so the schema is implemented in code. It is not copied
blind: ``tests/integration/ingest/test_bundle_envelope.py`` reads the pinned schema file and
fails if a keyword, a bound, a pattern or an envelope rule here differs from it, and compares
this module with a generic checker over mutated block lists.

The counts a version records (migration ``0021``)
-----------------------------------------------
* ``text_character_count`` -- the sum over the pages of pypdfium2's ``get_text_range()``
  length, line breaks pypdfium2 generates included. It is the analysis input budget's
  measure (G-11), not a statement about the text;
* ``textless_pages`` -- the ascending, 1-based pages with fewer than
  :data:`~auditmanager.ingest.envelope.TEXTLESS_PAGE_CHARACTERS` (50) such characters; empty
  when none;
* ``recognised_character_count`` -- the characters of recognised text the markdown holds for
  those pages: for every TEXT block of the block list that sits on a text-less page, the length
  in characters of its body in ``_results.md``. A body is what follows the block's header and its
  ``> **Key:** value`` quote lines, up to the next block header or page heading, without the
  blank lines around it; its own line breaks count one character each. IMAGE bodies are the
  portal's *descriptions* of a picture (R-117), not recognised text, and a STAMP has no body in
  the markdown, so neither counts. ``crop_url`` values and ``> **Crop:**`` links are portal
  capability URLs and are never read for anything but being skipped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final

from .bundle_archive import (
    ROLE_BLOCKS,
    ROLE_PDF,
    ROLE_RESULTS_MD,
    ROLE_STAMP_AUDIT,
    ExtractedBundle,
    refuse,
)
from .envelope import TEXTLESS_PAGE_CHARACTERS, inspect_pdf, page_text_refusal

__all__ = [
    "BundleAdmission",
    "admit_bundle",
    "recognised_characters",
]

# -- the pinned schema, in code ---------------------------------------------------------
#
# Each constant below is one fact of ``portal-blocks.schema.json``; the test reads the file
# and compares them.

SCHEMA_REQUIRED_TOP: Final[tuple[str, ...]] = ("schema_version", "coordinate_space", "pages", "blocks")
SCHEMA_VERSION: Final[int] = 1
COORDINATE_SPACE: Final[str] = "normalized_page_top_left"
PAGES_MIN, PAGES_MAX = 1, 500
PAGE_REQUIRED: Final[tuple[str, ...]] = ("page_index", "width_px", "height_px", "rotation")
ROTATIONS: Final[tuple[int, ...]] = (0, 90, 180, 270)
BLOCK_REQUIRED: Final[tuple[str, ...]] = (
    "block_id", "page_index", "page_label", "ordinal", "block_type", "status", "coords_norm",
)
BLOCK_TYPES: Final[tuple[str, ...]] = ("text", "image", "stamp")
BLOCK_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^blk_[0-9a-f]{32}$")
STATUS_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
#: ``shape_type`` is optional; when present it is one of these, case-sensitively.
SHAPE_TYPES: Final[tuple[str, ...]] = ("rectangle", "polygon")
#: The shape that must carry its vertices (the block's ``if``/``then`` in the schema).
POLYGON_SHAPE: Final[str] = "polygon"
#: ``polygon_points`` is ``null`` or an empty list on a rectangle; a non-empty list holds
#: ``POLYGON_MIN`` to ``POLYGON_MAX`` vertices, so a list of one or two is refused.
POLYGON_MIN, POLYGON_MAX = 3, 64
#: The ``x-envelope-rules`` this module implements, one per entry of the schema.
IMPLEMENTED_ENVELOPE_RULES: Final[int] = 5

# ``### BLOCK #12 [TEXT]: blk_...`` -- the portal's header for a block in ``_results.md``.
_HEADER: Final[re.Pattern[str]] = re.compile(
    r"^### BLOCK #(\d+) \[([A-Za-z]+)\]: (\S+)[ \t\r]*$", re.MULTILINE
)
_HEADER_LINE: Final[re.Pattern[str]] = re.compile(r"^### BLOCK #(\d+) \[([A-Za-z]+)\]: (\S+)[ \t\r]*$")
_PAGE_HEADING: Final[re.Pattern[str]] = re.compile(r"^## Page \d+[ \t\r]*$")
#: ``> **Created:** ...``, ``> **Crop:** [Crop](...)``, ``> **Stamp:** ...`` -- a block's
#: metadata lines. They carry no recognised text.
_QUOTE_FIELD: Final[re.Pattern[str]] = re.compile(r"^> \*\*[^*\n]+:\*\*")


def _reject_constant(token: str) -> object:
    raise ValueError(f"the non-finite number {token} is not JSON")


def _loads(raw: bytes) -> Any:
    """Strict JSON: UTF-8, and neither NaN nor Infinity (Python reads them by default)."""
    return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)


# -- the schema's types -----------------------------------------------------------------


def _is_integer(value: object) -> bool:
    """A JSON integer as written: ``3``, never ``3.0`` and never ``true``.

    `W55B-FIX` (X-7, Y-1(a)). JSON Schema's ``integer`` admits a number with a zero
    fraction, and so did this check; both run stages (``analysis.recognised.portal`` and
    ``analysis.geometry.portal``) read a page index, a raster size, a rotation, a page label
    and an ordinal as a Python ``int`` and refuse ``3.0`` as ``portal_blocks_invalid``. An
    accepted version is immutable, so a block list one side admits and the other refuses
    was a version every run failed. One rule now holds on both sides: the integer the
    portal writes. The fixtures' reference checker (``tools/fixtures/portal_bundle``) reads
    ``integer`` the same way.
    """
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _int_at_least(value: object, minimum: int) -> bool:
    return _is_integer(value) and value >= minimum  # type: ignore[operator]


def _coordinates_ok(value: object, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(_is_number(v) and 0 <= v <= 1 for v in value)  # type: ignore[operator]
    )


def _blocks_problem(document: Any) -> str | None:
    """The first way ``document`` breaks the block-list schema or its envelope rules.

    Returns a short classifier of the defect for diagnostics, or ``None``. Never a value
    taken from the document: nothing it holds is echoed to a caller.
    """
    if not isinstance(document, dict):
        return "not an object"
    for name in SCHEMA_REQUIRED_TOP:
        if name not in document:
            return f"missing {name}"
    if not (_is_integer(document["schema_version"]) and document["schema_version"] == SCHEMA_VERSION):
        return "schema_version"
    if document["coordinate_space"] != COORDINATE_SPACE:
        return "coordinate_space"

    pages = document["pages"]
    if not isinstance(pages, list) or not PAGES_MIN <= len(pages) <= PAGES_MAX:
        return "pages"
    for page in pages:
        if not isinstance(page, dict):
            return "page is not an object"
        for name in PAGE_REQUIRED:
            if name not in page:
                return f"page lacks {name}"
        if not _int_at_least(page["page_index"], 0):
            return "page_index"
        if not _int_at_least(page["width_px"], 1) or not _int_at_least(page["height_px"], 1):
            return "page size"
        rotation = page["rotation"]
        if not _is_integer(rotation) or rotation not in ROTATIONS:
            return "rotation"

    blocks = document["blocks"]
    if not isinstance(blocks, list):
        return "blocks"
    for block in blocks:
        problem = _block_problem(block)
        if problem is not None:
            return problem

    # The envelope rules a JSON Schema cannot state.
    if [int(p["page_index"]) for p in pages] != list(range(len(pages))):
        return "page_index does not run 0..n-1"
    ids = [b["block_id"] for b in blocks]
    if len(set(ids)) != len(ids):
        return "block_id is not unique"
    for block in blocks:
        if int(block["page_index"]) >= len(pages):
            return "a block names no page"
        x0, y0, x1, y1 = block["coords_norm"]
        if not (x0 < x1 and y0 < y1):
            return "coords_norm is not x0<x1, y0<y1"
    return None


def _block_problem(block: Any) -> str | None:
    if not isinstance(block, dict):
        return "block is not an object"
    for name in BLOCK_REQUIRED:
        if name not in block:
            return f"block lacks {name}"
    block_id = block["block_id"]
    if not isinstance(block_id, str) or BLOCK_ID_PATTERN.fullmatch(block_id) is None:
        return "block_id"
    if not _int_at_least(block["page_index"], 0):
        return "block page_index"
    if not _int_at_least(block["page_label"], 1):
        return "page_label"
    ordinal = block["ordinal"]
    if ordinal is not None and not _int_at_least(ordinal, 0):
        return "ordinal"
    block_type = block["block_type"]
    if isinstance(block_type, bool) or block_type not in BLOCK_TYPES:
        return "block_type"
    status = block["status"]
    if not isinstance(status, str) or STATUS_PATTERN.fullmatch(status) is None:
        return "status"
    if not _coordinates_ok(block["coords_norm"], 4):
        return "coords_norm"
    if "shape_type" in block and (
        not isinstance(block["shape_type"], str) or block["shape_type"] not in SHAPE_TYPES
    ):
        return "shape_type"
    if "export_status" in block and not isinstance(block["export_status"], str):
        return "export_status"
    if "crop_url" in block and block["crop_url"] is not None and not isinstance(
        block["crop_url"], str
    ):
        return "crop_url"
    polygon = block.get("polygon_points")
    if polygon is not None:
        if not isinstance(polygon, list) or len(polygon) > POLYGON_MAX:
            return "polygon_points"
        if polygon and len(polygon) < POLYGON_MIN:        # empty is a rectangle's; 1 or 2 is not
            return "polygon_points"
        if not all(_coordinates_ok(point, 2) for point in polygon):
            return "polygon_points"
    if block.get("shape_type") == POLYGON_SHAPE and not polygon:
        return "polygon_points"                           # a polygon carries its vertices
    return None


# -- the markdown -----------------------------------------------------------------------


def _markdown_headers(text: str) -> dict[str, list[str]]:
    headers: dict[str, list[str]] = {}
    for _ordinal, kind, identifier in _HEADER.findall(text):
        headers.setdefault(identifier, []).append(kind.lower())
    return headers


def _markdown_problem(raw: bytes, document: dict[str, Any]) -> tuple[str | None, str]:
    """(a defect classifier or ``None``, the decoded markdown)."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "the recognised-text file is not UTF-8", ""
    headers = _markdown_headers(text)
    expected = {
        b["block_id"]: b["block_type"] for b in document["blocks"]
        if b["block_type"] in ("text", "image")
    }
    for identifier, kind in expected.items():
        if headers.get(identifier) != [kind]:
            return "a block of the list has no single header of its type", text
    if set(headers) - set(expected):
        return "a header for a block the list does not hold as TEXT or IMAGE", text
    return None, text


def recognised_characters(text: str, wanted: set[str]) -> dict[str, int]:
    """The length of the body of each wanted block in the markdown, by block identifier.

    See the module docstring for what a body is. A block whose header is not in ``text``
    is absent from the result.
    """
    lengths: dict[str, int] = {}
    current: str | None = None
    lines: list[str] = []

    def flush() -> None:
        if current is not None and current in wanted:
            lengths[current] = len(_body_of(lines))

    for line in text.split("\n"):
        header = _HEADER_LINE.match(line)
        if header is not None:
            flush()
            current, lines = header.group(3), []
            continue
        if _PAGE_HEADING.match(line):
            flush()
            current, lines = None, []
            continue
        if current is not None:
            lines.append(line.rstrip("\r"))
    flush()
    return lengths


def _body_of(lines: list[str]) -> str:
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    while start < len(lines) and _QUOTE_FIELD.match(lines[start]):
        start += 1
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    while start < end and not lines[start].strip():
        start += 1
    return "\n".join(lines[start:end])


# -- the admission ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BundleAdmission:
    """What an accepted bundle established: the PDF's facts and the three counts."""

    page_count: int
    pdf_size: int
    text_character_count: int
    textless_pages: tuple[int, ...]
    recognised_character_count: int
    block_count: int


def admit_bundle(bundle: ExtractedBundle) -> BundleAdmission:
    """Judge the extracted members, cheapest and most attributable first (module docstring)."""
    with bundle.open(ROLE_PDF) as handle:
        pdf = inspect_pdf(handle, require_text=False)

    try:
        document = _loads(bundle.read_bytes(ROLE_BLOCKS))
        problem = _blocks_problem(document)
    except (UnicodeDecodeError, ValueError, RecursionError):
        problem = "not JSON"
    if problem is not None:
        raise refuse("blocks_json_invalid")

    problem, markdown = _markdown_problem(bundle.read_bytes(ROLE_RESULTS_MD), document)
    if problem is not None:
        raise refuse("results_blocks_mismatch")

    if len(document["pages"]) != pdf.page_count:
        raise refuse("blocks_page_count")

    blocks = document["blocks"]
    with_block = {int(b["page_index"]) for b in blocks}
    bare = [
        index + 1 for index, layer in enumerate(pdf.page_has_layer)
        if not layer and index not in with_block
    ]
    if bare:
        raise page_text_refusal()

    if ROLE_STAMP_AUDIT in bundle.members:
        try:
            _loads(bundle.read_bytes(ROLE_STAMP_AUDIT))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise refuse("stamp_audit_invalid") from None

    textless = tuple(
        index + 1 for index, count in enumerate(pdf.page_characters)
        if count < TEXTLESS_PAGE_CHARACTERS
    )
    textless_set = set(textless)
    text_blocks = {
        b["block_id"] for b in blocks
        if b["block_type"] == "text" and int(b["page_index"]) + 1 in textless_set
    }
    recognised = sum(recognised_characters(markdown, text_blocks).values()) if text_blocks else 0

    return BundleAdmission(
        page_count=pdf.page_count,
        pdf_size=pdf.byte_size,
        text_character_count=sum(pdf.page_characters),
        textless_pages=textless,
        recognised_character_count=recognised,
        block_count=len(blocks),
    )
