"""Shared helpers for the portal-geometry suite (`W55B-GEOMETRY-01`). Not a test module.

* :func:`make_pdf` writes small PDFs **at test time** -- pages of any size, ``/Rotate``,
  CropBox, filled rectangles and a line of standard-font text -- so every rotation is tested
  on a generated page (no real rotated page exists, plan section B3.7) and nothing binary is
  checked in. The writer is the PDF syntax itself, a few dozen lines, so what a test draws is
  exactly what it states.
* :func:`displayed_rect` is the **independent oracle** for where a rectangle drawn in PDF
  user space appears on the displayed (rotated) page: the four formulas of a clockwise
  ``/Rotate``, written here from the PDF reference rather than from the code under test.
* :func:`bundle_members` writes a ``_blocks.json`` and a matching ``_results.md`` for a
  generated PDF, so ``source_preparation`` and ``page_geometry_extraction`` run on it as on
  a real bundle.
* :func:`validate_crop_manifest` checks a manifest against
  ``contracts/analysis/v1/crop-manifest.schema.json``, read from the contract file, with the
  keywords that schema uses implemented here (``jsonschema`` is not in the runtime lock); a
  keyword it does not implement is refused loudly, never skipped.
* :func:`portal_blocks_violations` is the strict structural validator of
  ``geometry.portal_blocks`` (``P02_SEAMS`` section 4.9).
"""

from __future__ import annotations

import io
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from auditmanager.analysis.public import run_stage
from auditmanager.storage.public import parse_blob_id
from tests.integration.analysis.recognised.recognised_support import (
    VERSION_UID,
    members,
    publish,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CROP_MANIFEST_SCHEMA = REPOSITORY_ROOT / "contracts" / "analysis" / "v1" / "crop-manifest.schema.json"

RED = (1, 0, 0)
GREEN = (0, 1, 0)
BLUE = (0, 0, 1)


# -- generated PDFs ------------------------------------------------------------------------


@dataclass(frozen=True)
class Rect:
    """A filled rectangle in PDF user space: lower-left corner, width, height, colour."""

    x: float
    y: float
    w: float
    h: float
    rgb: tuple[float, float, float] = RED


@dataclass(frozen=True)
class PageSpec:
    width: float
    height: float
    rotate: int = 0
    rects: tuple[Rect, ...] = ()
    #: A line of Helvetica at the user-space point (8, 8), so the page has a text layer.
    text: str | None = "Page"
    #: ``[x0, y0, x1, y1]``; the MediaBox is always ``[0 0 width height]``.
    cropbox: tuple[float, float, float, float] | None = None


def make_pdf(pages: Sequence[PageSpec]) -> bytes:
    """A valid PDF 1.7 holding ``pages``, with a correct cross-reference table."""
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    contents = []
    for page in pages:
        operators = [
            f"{r.rgb[0]} {r.rgb[1]} {r.rgb[2]} rg {r.x} {r.y} {r.w} {r.h} re f" for r in page.rects
        ]
        if page.text:
            operators.append(f"0 0 0 rg BT /F1 9 Tf 8 8 Td ({page.text}) Tj ET")
        stream = "\n".join(operators).encode("ascii")
        contents.append(add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
    pages_id = len(objects) + len(pages) + 1
    kids = []
    for page, content in zip(pages, contents):
        extra = b""
        if page.cropbox is not None:
            extra += b" /CropBox [%s]" % " ".join(repr(float(v)) for v in page.cropbox).encode()
        if page.rotate:
            extra += b" /Rotate %d" % page.rotate
        kids.append(
            add(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %s %s]%s "
                b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                % (pages_id, repr(float(page.width)).encode(), repr(float(page.height)).encode(),
                   extra, font, content)
            )
        )
    assert add(
        b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (" ".join(f"{k} 0 R" for k in kids).encode(), len(kids))
    ) == pages_id
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, catalog, xref
    )
    return bytes(out)


def displayed_size(page: PageSpec) -> tuple[float, float]:
    """The oracle's displayed page: the CropBox (or MediaBox) after a clockwise ``/Rotate``."""
    x0, y0, x1, y1 = page.cropbox or (0.0, 0.0, page.width, page.height)
    width, height = x1 - x0, y1 - y0
    return (height, width) if page.rotate % 180 else (width, height)


def displayed_rect(page: PageSpec, rect: Rect) -> tuple[float, float, float, float]:
    """Where ``rect`` appears on the displayed page, top-left origin, in points.

    The PDF reference rotates the displayed page **clockwise** by ``/Rotate``; with the box
    ``[bx0 by0 bx1 by1]``, a user-space point ``(u, v)`` is displayed at:

    * 0:   ``(u - bx0, by1 - v)``
    * 90:  ``(v - by0, u - bx0)``
    * 180: ``(bx1 - u, v - by0)``
    * 270: ``(by1 - v, bx1 - u)``
    """
    bx0, by0, bx1, by1 = page.cropbox or (0.0, 0.0, page.width, page.height)
    corners = [(rect.x, rect.y), (rect.x + rect.w, rect.y + rect.h)]
    rotate = page.rotate % 360
    mapped = []
    for u, v in corners:
        if rotate == 0:
            mapped.append((u - bx0, by1 - v))
        elif rotate == 90:
            mapped.append((v - by0, u - bx0))
        elif rotate == 180:
            mapped.append((bx1 - u, v - by0))
        else:
            mapped.append((by1 - v, bx1 - u))
    xs = [p[0] for p in mapped]
    ys = [p[1] for p in mapped]
    return min(xs), min(ys), max(xs), max(ys)


def normalised(page: PageSpec, box: tuple[float, float, float, float]) -> tuple[float, ...]:
    """A displayed box in points as ``bbox_norm``."""
    width, height = displayed_size(page)
    return (box[0] / width, box[1] / height, box[2] / width, box[3] / height)


def grown(box: tuple[float, ...], by: float) -> list[float]:
    """A normalised box grown by ``by`` on every side, kept inside [0, 1]."""
    return [max(0.0, box[0] - by), max(0.0, box[1] - by), min(1.0, box[2] + by), min(1.0, box[3] + by)]


# -- generated bundles ---------------------------------------------------------------------


@dataclass(frozen=True)
class BlockSpec:
    """One block of a generated block list."""

    block_type: str
    page_number: int
    bbox_norm: Sequence[float]
    ordinal: int | None = 0
    polygon_points: Any = None
    body: str = "Распознанный текст блока."
    status: str = "recognized"


def block_id(n: int) -> str:
    return f"blk_{n:032x}"


@dataclass(frozen=True)
class Members:
    """The three stored members of a generated bundle."""

    pdf: bytes
    block_list: bytes
    markdown: bytes
    ids: tuple[str, ...] = field(default=())


def bundle_members(
    pages: Sequence[PageSpec],
    blocks: Sequence[BlockSpec],
    *,
    rasters: Mapping[int, tuple[int, int, int]] | None = None,
    first_id: int = 1,
) -> Members:
    """A PDF, its ``_blocks.json`` and a matching ``_results.md``.

    Each page's portal raster defaults to the displayed page at 300 dpi (``width_px`` x
    ``height_px``, ``rotation`` = the page's ``/Rotate``); ``rasters`` overrides a page as
    ``{page_number: (width_px, height_px, rotation)}``.
    """
    pdf = make_pdf(pages)
    page_entries = []
    for number, page in enumerate(pages, start=1):
        width, height = displayed_size(page)
        default = (round(width * 300 / 72), round(height * 300 / 72), page.rotate % 360)
        width_px, height_px, rotation = (rasters or {}).get(number, default)
        page_entries.append(
            {"page_index": number - 1, "width_px": width_px, "height_px": height_px, "rotation": rotation}
        )
    ids = []
    block_entries = []
    for offset, block in enumerate(blocks):
        identifier = block_id(first_id + offset)
        ids.append(identifier)
        block_entries.append(
            {
                "block_id": identifier,
                "ordinal": None if block.block_type == "stamp" else block.ordinal,
                "page_index": block.page_number - 1,
                "page_label": block.page_number,
                "block_type": block.block_type,
                "shape_type": "polygon" if block.polygon_points else "rectangle",
                "status": block.status,
                "export_status": block.status,
                "coords_norm": list(block.bbox_norm),
                "polygon_points": block.polygon_points,
                "crop_url": None if block.block_type == "stamp" else f"https://portal.invalid/api/crops/{identifier}",
            }
        )
    block_list = json.dumps(
        {
            "schema_version": 1,
            "document_id": "doc_" + "0" * 32,
            "document_name": "generated.pdf",
            "document_path": "generated",
            "generated_at": "2026-10-14T00:00:00Z",
            "coordinate_space": "normalized_page_top_left",
            "pages": page_entries,
            "blocks": block_entries,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    lines = ["# generated", ""]
    for number in range(1, len(pages) + 1):
        lines += [f"## Page {number}", ""]
        for identifier, block in zip(ids, blocks):
            if block.page_number != number or block.block_type == "stamp":
                continue
            label = "TEXT" if block.block_type == "text" else "IMAGE"
            lines += [
                f"### BLOCK #{block.ordinal or 0} [{label}]: {identifier}",
                "",
                "> **Created:** 2026-10-14 00:00:00 UTC",
                f"> **Crop:** [Crop](https://portal.invalid/api/crops/{identifier})",
                "",
                block.body,
                "",
            ]
    return Members(pdf=pdf, block_list=block_list, markdown="\n".join(lines).encode("utf-8"), ids=tuple(ids))


# -- running the two stages ----------------------------------------------------------------


@dataclass
class Prepared:
    """The blobs and the results of ``source_preparation`` for one generated version."""

    pdf_blob: Any
    blocks_blob: Any | None
    markdown_blob: Any | None
    preparation: Any

    def geometry_inputs(self, *, with_companion: bool = True) -> dict[str, Any]:
        inputs = {ref.role: parse_blob_id(ref.blob_id) for ref in self.preparation.artifacts}
        inputs.pop("prepared.recognised_text", None)
        if with_companion and self.blocks_blob is not None:
            inputs["source.structured_companion"] = self.blocks_blob
        return inputs


def prepare(store: Any, member_set: Members | Any, *, bundle: bool = True) -> Prepared:
    """Publish the members and run ``source_preparation`` (a bundle, or the bare PDF)."""
    pdf_blob = publish(store, member_set.pdf, role="source_document", media_type="application/pdf")
    inputs: dict[str, Any] = {"source.document": pdf_blob}
    blocks_blob = markdown_blob = None
    if bundle:
        blocks_blob = publish(
            store, member_set.block_list, role="source_structured_companion", media_type="application/json"
        )
        markdown_blob = publish(store, member_set.markdown, role="source_markdown", media_type="text/markdown")
        inputs |= {"source.structured_companion": blocks_blob, "source.markdown": markdown_blob}
    preparation = run_stage("source_preparation", version_uid=VERSION_UID, inputs=inputs, blob_store=store)
    assert preparation.status.value == "succeeded", preparation.error
    return Prepared(pdf_blob, blocks_blob, markdown_blob, preparation)


def run_geometry(store: Any, prepared: Prepared, *, with_companion: bool = True) -> Any:
    return run_stage(
        "page_geometry_extraction",
        version_uid=VERSION_UID,
        inputs=prepared.geometry_inputs(with_companion=with_companion),
        blob_store=store,
    )


def artifact_document(store: Any, result: Any, role: str) -> dict[str, Any]:
    return json.loads(store.read(parse_blob_id(result.artifact(role).blob_id)))


def committed_bundle(name: str) -> Any:
    return members(name)


def decode_png(payload: bytes) -> Any:
    from PIL import Image

    image = Image.open(io.BytesIO(payload))
    image.load()
    return image


# -- the crop manifest against its contract schema -----------------------------------------

_ANNOTATIONS = frozenset({"$schema", "$id", "title", "description", "contract_version"})
_KEYWORDS = frozenset({
    "type", "enum", "const", "required", "properties", "additionalProperties", "items",
    "minItems", "maxItems", "minimum", "maximum", "exclusiveMinimum", "minLength", "pattern", "$ref",
    "$defs", "if", "then",
})


class SchemaKeywordError(ValueError):
    """The contract uses a keyword this checker does not implement."""


def _assert_known(schema: Any, where: str = "$") -> None:
    if not isinstance(schema, dict):
        raise SchemaKeywordError(f"{where}: a schema is an object")
    unknown = set(schema) - _ANNOTATIONS - _KEYWORDS
    if unknown:
        raise SchemaKeywordError(f"{where}: unsupported keyword(s) {sorted(unknown)}")
    for name, sub in schema.get("properties", {}).items():
        _assert_known(sub, f"{where}.{name}")
    for name, sub in schema.get("$defs", {}).items():
        _assert_known(sub, f"{where}.$defs.{name}")
    for keyword in ("items", "if", "then"):
        if keyword in schema:
            _assert_known(schema[keyword], f"{where}.{keyword}")


def _type_ok(value: Any, name: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }[name]


def _check(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    if "$ref" in schema:
        reference = schema["$ref"]
        assert reference.startswith("#/$defs/"), reference
        return _check(value, root["$defs"][reference.split("/")[-1]], root, path)
    errors: list[str] = []
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, n) for n in names):
            return [f"{path}: type"]
    if "const" in schema and (value != schema["const"] or isinstance(value, bool)):
        errors.append(f"{path}: const")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: enum")
    if isinstance(value, str) and "pattern" in schema and re.search(schema["pattern"], value) is None:
        errors.append(f"{path}: pattern")
    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(f"{path}: minLength")
    if _type_ok(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: exclusiveMinimum")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: maxItems")
        if "items" in schema:
            for index, item in enumerate(value):
                errors += _check(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(value, dict):
        for name in schema.get("required", ()):
            if name not in value:
                errors.append(f"{path}: required {name}")
        properties = schema.get("properties", {})
        for name, sub in properties.items():
            if name in value:
                errors += _check(value[name], sub, root, f"{path}.{name}")
        if schema.get("additionalProperties") is False:
            errors += [f"{path}: additional {name}" for name in value if name not in properties]
    if "if" in schema and not _check(value, schema["if"], root, path):
        errors += _check(value, schema["then"], root, path)
    return errors


def validate_crop_manifest(document: Any) -> list[str]:
    """Every violation of the crop-manifest contract schema by ``document``."""
    schema = json.loads(CROP_MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    _assert_known(schema)
    return _check(document, schema, schema, "$")


# -- geometry.portal_blocks, strictly ------------------------------------------------------

_BLOCK_ID = re.compile(r"^blk_[0-9a-f]{32}$")
_VERSION = re.compile(r"^ver_[0-9A-HJKMNP-TV-Z]{26}$")
_STATUS = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_PAGE_KEYS = {"page_number", "width_px", "height_px", "rotation_deg", "geometry"}
_BLOCK_KEYS = {
    "portal_block_id", "page_number", "page_label", "ordinal", "block_type", "status",
    "bbox_norm", "geometry",
}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _unit(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def portal_blocks_violations(document: Any) -> list[str]:
    """Every way ``document`` departs from section 4.9 (and this lane's per-block ``geometry``)."""
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["$: not an object"]
    expected = {"artifact_role", "artifact_version", "version_uid", "blocks_sha256", "pages", "blocks"}
    if set(document) != expected:
        errors.append(f"$: members {sorted(set(document) ^ expected)}")
    if document.get("artifact_role") != "geometry.portal_blocks":
        errors.append("$.artifact_role")
    if document.get("artifact_version") != "1.0.0":
        errors.append("$.artifact_version")
    if not isinstance(document.get("version_uid"), str) or not _VERSION.match(document["version_uid"]):
        errors.append("$.version_uid")
    if not isinstance(document.get("blocks_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", document["blocks_sha256"]):
        errors.append("$.blocks_sha256")
    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        return errors + ["$.pages"]
    verdict: dict[int, str] = {}
    for index, page in enumerate(pages):
        where = f"$.pages[{index}]"
        if not isinstance(page, dict) or set(page) != _PAGE_KEYS:
            errors.append(f"{where}: members")
            continue
        if page["page_number"] != index + 1:
            errors.append(f"{where}.page_number: not contiguous from 1")
        if not (_is_int(page["width_px"]) and page["width_px"] >= 1 and _is_int(page["height_px"]) and page["height_px"] >= 1):
            errors.append(f"{where}: raster")
        if page["rotation_deg"] not in (0, 90, 180, 270) or not _is_int(page["rotation_deg"]):
            errors.append(f"{where}.rotation_deg")
        if page["geometry"] not in ("ok", "geometry_mismatch"):
            errors.append(f"{where}.geometry")
        verdict[page["page_number"]] = page["geometry"]
    blocks = document.get("blocks")
    if not isinstance(blocks, list):
        return errors + ["$.blocks"]
    keys = []
    seen = set()
    for index, block in enumerate(blocks):
        where = f"$.blocks[{index}]"
        if not isinstance(block, dict) or not (_BLOCK_KEYS <= set(block) <= _BLOCK_KEYS | {"polygon_points"}):
            errors.append(f"{where}: members")
            continue
        identifier = block["portal_block_id"]
        if not isinstance(identifier, str) or not _BLOCK_ID.match(identifier) or identifier in seen:
            errors.append(f"{where}.portal_block_id")
        seen.add(identifier)
        if block["page_number"] not in verdict:
            errors.append(f"{where}.page_number")
        elif block["geometry"] != verdict[block["page_number"]]:
            errors.append(f"{where}.geometry: not its page's")
        if not (_is_int(block["page_label"]) and block["page_label"] >= 1):
            errors.append(f"{where}.page_label")
        if block["block_type"] not in ("text", "image", "stamp"):
            errors.append(f"{where}.block_type")
        ordinal = block["ordinal"]
        if ordinal is not None and not (_is_int(ordinal) and ordinal >= 0):
            errors.append(f"{where}.ordinal")
        if block["block_type"] == "stamp" and ordinal is not None:
            errors.append(f"{where}.ordinal: a stamp's is null")
        if not (isinstance(block["status"], str) and _STATUS.match(block["status"])):
            errors.append(f"{where}.status")
        box = block["bbox_norm"]
        if not (isinstance(box, list) and len(box) == 4 and all(_unit(v) for v in box) and box[0] < box[2] and box[1] < box[3]):
            errors.append(f"{where}.bbox_norm")
        if "polygon_points" in block:
            points = block["polygon_points"]
            if not (
                isinstance(points, list) and 3 <= len(points) <= 64
                and all(isinstance(p, list) and len(p) == 2 and all(_unit(c) for c in p) for p in points)
            ):
                errors.append(f"{where}.polygon_points")
        keys.append((block["page_number"], ordinal is None, ordinal or 0, identifier))
    if keys != sorted(keys):
        errors.append("$.blocks: not ordered by page, ordinal (null last), id")
    return errors


def every_string(value: Any) -> Iterable[str]:
    """Every string and every key anywhere in a JSON value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from every_string(item)
    elif isinstance(value, list):
        for item in value:
            yield from every_string(item)
