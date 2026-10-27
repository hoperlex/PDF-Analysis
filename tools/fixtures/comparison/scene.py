"""Sheets as lists of drawing operations, and the one writer that turns them into a PDF.

A sheet is a list of operations (`Text`, `Line`, `Rect`, `Circle`, `Hatch`), each with a
stable `id`. The id is what lets the corpus state, and check, what changed between two
versions: two operations with the same id in two versions are "the same object", and
`diff_sheets` reports what happened to it. Ids are authored, never derived from position,
so a moved label stays one object.

The same operations are drawn two ways: as PDF content (`render_content`) and, for the one
page that is a scan, as a 1-bit raster (`rasterise`). Nothing here knows about versions.

Units are PostScript points (1 mm = 2.8346 pt), origin at the lower left of the MediaBox.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

from ar_corpus import pdfwrite, ttfsubset
from ar_corpus.pdfwrite import Name, Pdf, RawBytes, Ref

from .outlines import OutlineFont, flatten

REPO_ROOT = Path(__file__).resolve().parents[3]
FONT_ASSET = REPO_ROOT / "tools" / "fixtures" / "assets" / "ARCorpusSans.ttf"

MM = 72.0 / 25.4
BLACK = (0.0, 0.0, 0.0)

# Sheet formats, portrait width x height in points; landscape swaps them.
A4 = (595.28, 841.89)
A3 = (841.89, 1190.55)
A2 = (1190.55, 1683.78)
A1 = (1683.78, 2383.94)
FORMAT_NAMES = {A4: "A4", A3: "A3", A2: "A2", A1: "A1"}


def landscape(size: tuple[float, float]) -> tuple[float, float]:
    return (size[1], size[0])


def format_name(width: float, height: float) -> str:
    short, long_ = sorted((round(width, 2), round(height, 2)))
    return FORMAT_NAMES[(short, long_)]


FRAME_LEFT = 20 * MM
FRAME_OTHER = 5 * MM
STAMP_W = 185 * MM
STAMP_H = 55 * MM

FONT_RESOURCE = "F1"
PATTERN_RESOURCE = "P1"
ASCENT = 1901 / 2048
DESCENT = 483 / 2048

PRODUCER = "PDF-Analysis synthetic comparison corpus generator (tools/fixtures/comparison)"
AUTHOR = "СИНТЕТИКПРОЕКТ (вымышленная организация)"


def load_font() -> pdfwrite.EmbeddedFont:
    """The committed `ARCorpusSans` subset, never a system font."""
    raw = FONT_ASSET.read_bytes()
    metrics = ttfsubset.read(raw)
    return pdfwrite.EmbeddedFont(
        font_bytes=raw,
        units_per_em=metrics.units_per_em,
        char_to_gid=metrics.char_to_gid,
        gid_advance=metrics.gid_advance,
        ascent=metrics.ascent,
        descent=metrics.descent,
        cap_height=metrics.cap_height,
        bbox=metrics.bbox,
    )


# --------------------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------------------

Color = tuple[float, float, float]


@dataclass(frozen=True)
class Op:
    """Common to every operation. `zone` is "content", "stamp" or "frame"; `layer` names an
    optional-content group, or None."""

    id: str
    zone: str = field(default="content", kw_only=True)
    layer: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class Text(Op):
    x: float = 0.0
    y: float = 0.0
    text: str = ""
    size: float = 10.0
    rgb: Color = BLACK


@dataclass(frozen=True)
class Line(Op):
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    width: float = 0.5
    rgb: Color = BLACK
    dash: tuple[float, ...] | None = None


@dataclass(frozen=True)
class Rect(Op):
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    width: float = 0.5
    rgb: Color = BLACK
    dash: tuple[float, ...] | None = None
    fill: Color | None = None


@dataclass(frozen=True)
class Circle(Op):
    cx: float = 0.0
    cy: float = 0.0
    r: float = 5.0
    width: float = 0.5
    rgb: Color = BLACK


@dataclass(frozen=True)
class Hatch(Op):
    """A rectangle filled with the document's 45-degree tiling pattern."""

    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0


@dataclass(frozen=True)
class Annotation:
    """A PDF annotation on a sheet: kind "text" (sticky note) or "square"."""

    id: str
    kind: str
    rect: tuple[float, float, float, float]
    contents: str
    author: str
    modified: str = "D:20260101000000Z"
    rgb: Color = (1.0, 0.9, 0.2)


@dataclass
class Sheet:
    sheet_id: str
    title: str
    sheet_no: str
    size: tuple[float, float]
    ops: list[Op]
    annotations: list[Annotation] = field(default_factory=list)
    scan: bool = False
    revision: int = 0
    stamp_bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    #: the sheet's role in its version: "regular", "duplicate", "split_part"
    role: str = "regular"

    @property
    def width(self) -> float:
        return self.size[0]

    @property
    def height(self) -> float:
        return self.size[1]

    def by_id(self) -> dict[str, Op]:
        index: dict[str, Op] = {}
        for op in self.ops:
            if op.id in index:
                raise ValueError(f"sheet {self.sheet_id}: duplicate operation id {op.id!r}")
            index[op.id] = op
        return index


# --------------------------------------------------------------------------------------
# Frame and title block (stamp)
# --------------------------------------------------------------------------------------


def frame_and_stamp(
    size: tuple[float, float], *, designation: str, title: str, stage: str,
    sheet_no: str, revision_label: str, date: str, organisation: str,
    font: pdfwrite.EmbeddedFont,
) -> tuple[list[Op], tuple[float, float, float, float]]:
    """The inner frame and a 185 x 55 mm title block at its lower right corner.

    Every value is its own `Text` operation with a fixed id, so a stamp field change is a
    one-object change. Returns the operations and the stamp's bounding box.
    """
    width, height = size
    left, bottom = FRAME_LEFT, FRAME_OTHER
    right, top = width - FRAME_OTHER, height - FRAME_OTHER
    sx, sy = right - STAMP_W, bottom
    ops: list[Op] = [
        Rect("frame.inner", x=left, y=bottom, w=right - left, h=top - bottom, width=1.5, zone="frame"),
        Rect("stamp.outer", x=sx, y=sy, w=STAMP_W, h=STAMP_H, width=1.0, zone="stamp"),
    ]

    def hline(name: str, x0: float, x1: float, y: float, w: float = 0.6) -> None:
        ops.append(Line(f"stamp.{name}", x1=sx + x0, y1=sy + y, x2=sx + x1, y2=sy + y, width=w, zone="stamp"))

    def vline(name: str, x: float, y0: float, y1: float, w: float = 0.6) -> None:
        ops.append(Line(f"stamp.{name}", x1=sx + x, y1=sy + y0, x2=sx + x, y2=sy + y1, width=w, zone="stamp"))

    def label(name: str, x: float, y: float, text: str) -> None:
        ops.append(Text(f"stamp.label.{name}", x=sx + x, y=sy + y, text=text, size=5.5, zone="stamp"))

    def value(name: str, x: float, y: float, text: str, size: float, max_width: float) -> None:
        if font.text_width(text, size) > max_width:
            raise ValueError(f"stamp field {name} {text!r} is wider than its cell ({max_width})")
        ops.append(Text(f"stamp.{name}", x=sx + x, y=sy + y, text=text, size=size, zone="stamp"))

    hline("row.designation", 0, STAMP_W, 113.4)
    vline("col.title", 340.0, 0, 113.4)
    hline("row.stage", 340.0, STAMP_W, 85.0)
    vline("col.stage", 432.0, 85.0, 113.4)
    hline("row.revision", 340.0, STAMP_W, 57.0)
    vline("col.revision", 432.0, 57.0, 85.0)

    label("designation", 4.0, 148.0, "Обозначение")
    value("designation", 12.0, 126.0, designation, 16.0, 500.0)
    label("title", 4.0, 106.0, "Наименование листа")
    value("title", 10.0, 80.0, title, 10.0, 326.0)
    label("stage", 344.0, 106.0, "Стадия")
    value("stage", 352.0, 92.0, stage, 12.0, 70.0)
    label("sheet_no", 436.0, 106.0, "Лист")
    value("sheet_no", 444.0, 92.0, sheet_no, 12.0, 70.0)
    label("revision", 344.0, 78.0, "Изм.")
    value("revision", 352.0, 63.0, revision_label, 12.0, 76.0)
    label("date", 436.0, 78.0, "Дата")
    value("date", 444.0, 63.0, date, 10.0, 76.0)
    label("org", 344.0, 49.0, "Организация")
    value("org", 352.0, 30.0, organisation, 9.0, 168.0)
    return ops, (sx, sy, sx + STAMP_W, sy + STAMP_H)


# --------------------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------------------


def text_width(font: pdfwrite.EmbeddedFont, op: Text) -> float:
    return font.text_width(op.text, op.size)


def bbox(op: Op, font: pdfwrite.EmbeddedFont) -> tuple[float, float, float, float]:
    """The operation's bounding box (x0, y0, x1, y1), rounded to 0.01 pt."""
    if isinstance(op, Text):
        box = (op.x, op.y - DESCENT * op.size, op.x + text_width(font, op), op.y + ASCENT * op.size)
    elif isinstance(op, Line):
        half = op.width / 2.0
        box = (min(op.x1, op.x2) - half, min(op.y1, op.y2) - half,
               max(op.x1, op.x2) + half, max(op.y1, op.y2) + half)
    elif isinstance(op, (Rect, Hatch)):
        half = getattr(op, "width", 0.0) / 2.0
        box = (op.x - half, op.y - half, op.x + op.w + half, op.y + op.h + half)
    elif isinstance(op, Circle):
        box = (op.cx - op.r - op.width / 2, op.cy - op.r - op.width / 2,
               op.cx + op.r + op.width / 2, op.cy + op.r + op.width / 2)
    else:  # pragma: no cover - a new operation type must say how to measure itself
        raise TypeError(type(op).__name__)
    return tuple(round(v, 2) for v in box)  # type: ignore[return-value]


# --------------------------------------------------------------------------------------
# PDF content
# --------------------------------------------------------------------------------------


def render_content(
    ops: list[Op], font: pdfwrite.EmbeddedFont, layer_tags: dict[str, str],
) -> str:
    """The content stream text for a vector page. Operations are drawn in list order."""
    out: list[str] = []
    open_layer: str | None = None
    for op in ops:
        if op.layer != open_layer:
            if open_layer is not None:
                out.append(pdfwrite.layer_end())
            if op.layer is not None:
                out.append(pdfwrite.layer_begin(layer_tags[op.layer]))
            open_layer = op.layer
        if isinstance(op, Text):
            shown = pdfwrite.show_text(font, FONT_RESOURCE, op.text, op.size, op.x, op.y)
            if op.rgb != BLACK:
                shown = f"q {pdfwrite._rgb(op.rgb, stroke=False)} " + shown + "Q\n"
            out.append(shown)
        elif isinstance(op, Line):
            out.append(pdfwrite.stroke_line_op(
                op.x1, op.y1, op.x2, op.y2, width=op.width, rgb=op.rgb, dash=op.dash, digits=2))
        elif isinstance(op, Rect):
            out.append(pdfwrite.stroke_rect_op(
                op.x, op.y, op.w, op.h, width=op.width, rgb=op.rgb, dash=op.dash, fill=op.fill, digits=2))
        elif isinstance(op, Circle):
            out.append(pdfwrite.stroke_circle_op(op.cx, op.cy, op.r, width=op.width, rgb=op.rgb, digits=2))
        elif isinstance(op, Hatch):
            out.append(pdfwrite.pattern_fill_op(PATTERN_RESOURCE, op.x, op.y, op.w, op.h, digits=2))
        else:  # pragma: no cover
            raise TypeError(type(op).__name__)
    if open_layer is not None:
        out.append(pdfwrite.layer_end())
    return "".join(out)


def content_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# --------------------------------------------------------------------------------------
# Raster (the scan page)
# --------------------------------------------------------------------------------------


class Bitmap:
    """A 1-bit-per-pixel page image drawn with scan-line fills. Ink is 1 while drawing."""

    def __init__(self, width_pt: float, height_pt: float, dpi: int) -> None:
        self.scale = dpi / 72.0
        self.height_pt = height_pt
        self.width = int(round(width_pt * self.scale))
        self.height = int(round(height_pt * self.scale))
        self.rows = [bytearray(self.width) for _ in range(self.height)]

    def _to_px(self, x: float, y: float) -> tuple[float, float]:
        return x * self.scale, (self.height_pt - y) * self.scale

    def fill(self, polygons: list[list[tuple[float, float]]]) -> None:
        """Even-odd fill of polygons given in page points."""
        edges: list[tuple[float, float, float, float]] = []
        for polygon in polygons:
            pts = [self._to_px(x, y) for x, y in polygon]
            for index, (x0, y0) in enumerate(pts):
                x1, y1 = pts[(index + 1) % len(pts)]
                if y0 != y1:
                    edges.append((x0, y0, x1, y1))
        if not edges:
            return
        first = max(0, int(math.floor(min(min(e[1], e[3]) for e in edges))))
        last = min(self.height - 1, int(math.ceil(max(max(e[1], e[3]) for e in edges))))
        for row in range(first, last + 1):
            yc = row + 0.5
            crossings = sorted(
                x0 + (yc - y0) * (x1 - x0) / (y1 - y0)
                for x0, y0, x1, y1 in edges
                if (y0 <= yc < y1) or (y1 <= yc < y0)
            )
            line = self.rows[row]
            for index in range(0, len(crossings) - 1, 2):
                start = max(0, int(math.ceil(crossings[index] - 0.5)))
                stop = min(self.width, int(math.ceil(crossings[index + 1] - 0.5)))
                if stop > start:
                    line[start:stop] = b"\x01" * (stop - start)

    def stroke(self, x1: float, y1: float, x2: float, y2: float, width: float) -> None:
        """A line segment `width` points thick (at least one pixel)."""
        half = max(width, 1.0 / self.scale) / 2.0
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            return
        nx, ny = -dy / length * half, dx / length * half
        self.fill([[(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]])

    def dashed(self, x1: float, y1: float, x2: float, y2: float, width: float,
               dash: tuple[float, ...]) -> None:
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            return
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        position, index = 0.0, 0
        while position < length:
            run = dash[index % len(dash)]
            if index % 2 == 0:
                end = min(position + run, length)
                self.stroke(x1 + ux * position, y1 + uy * position, x1 + ux * end, y1 + uy * end, width)
            position += run
            index += 1

    def packed(self) -> bytes:
        """Rows packed 8 pixels to a byte, 0 = black, 1 = white (DeviceGray, 1 bit)."""
        table = bytes.maketrans(b"\x00\x01", b"10")
        stride = (self.width + 7) // 8
        out = bytearray()
        for row in self.rows:
            bits = row.translate(table).decode("ascii").ljust(stride * 8, "1")
            out += int(bits, 2).to_bytes(stride, "big")
        return bytes(out)


def rasterise(sheet: Sheet, outlines: OutlineFont, dpi: int) -> Bitmap:
    """Draw a sheet's operations onto a bitmap, text as filled glyph outlines."""
    bitmap = Bitmap(sheet.width, sheet.height, dpi)
    for op in sheet.ops:
        if isinstance(op, Text):
            scale = op.size / outlines.units_per_em
            pen = op.x
            for char in op.text:
                polygons = [
                    [(pen + px * scale, op.y + py * scale) for px, py in flatten(contour)]
                    for contour in outlines.contours(char)
                ]
                if polygons:
                    bitmap.fill(polygons)
                pen += outlines.advance(char) * scale
        elif isinstance(op, Line):
            if op.dash:
                bitmap.dashed(op.x1, op.y1, op.x2, op.y2, op.width, op.dash)
            else:
                bitmap.stroke(op.x1, op.y1, op.x2, op.y2, op.width)
        elif isinstance(op, Rect):
            corners = [(op.x, op.y), (op.x + op.w, op.y), (op.x + op.w, op.y + op.h), (op.x, op.y + op.h)]
            for index, (ax, ay) in enumerate(corners):
                bx, by = corners[(index + 1) % 4]
                if op.dash:
                    bitmap.dashed(ax, ay, bx, by, op.width, op.dash)
                else:
                    bitmap.stroke(ax, ay, bx, by, op.width)
        elif isinstance(op, Circle):
            ring = [(op.cx + op.r * math.cos(t * math.pi / 12), op.cy + op.r * math.sin(t * math.pi / 12))
                    for t in range(24)]
            for index, (ax, ay) in enumerate(ring):
                bx, by = ring[(index + 1) % 24]
                bitmap.stroke(ax, ay, bx, by, op.width)
        elif isinstance(op, Hatch):
            offset = -op.h
            while offset < op.w:
                x0, y0 = op.x + max(offset, 0.0), op.y + max(-offset, 0.0)
                run = min(op.w - max(offset, 0.0), op.h - max(-offset, 0.0))
                if run > 0:
                    bitmap.stroke(x0, y0, x0 + run, y0 + run, 0.4)
                offset += 4.0
    return bitmap


# --------------------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentMeta:
    title: str
    subject: str
    doc_id_seed: str
    creation_date: str


def _info(meta: DocumentMeta) -> dict[str, object]:
    return {
        "Title": pdfwrite.EncryptableString(meta.title),
        "Author": pdfwrite.EncryptableString(AUTHOR),
        "Subject": pdfwrite.EncryptableString(meta.subject),
        "Keywords": pdfwrite.EncryptableString("synthetic; fixture; comparison corpus"),
        "Creator": pdfwrite.EncryptableString(PRODUCER),
        "Producer": pdfwrite.EncryptableString(PRODUCER),
        "CreationDate": RawBytes(pdfwrite.pdf_literal(meta.creation_date)),
        "ModDate": RawBytes(pdfwrite.pdf_literal(meta.creation_date)),
    }


@dataclass(frozen=True)
class BuiltPage:
    sheet_id: str
    content: bytes
    media_box: tuple[float, float]
    has_text_layer: bool
    image_bytes: bytes | None


@dataclass(frozen=True)
class BuiltDocument:
    data: bytes
    pages: list[BuiltPage]


def build_document(
    sheets: list[Sheet], meta: DocumentMeta, font: pdfwrite.EmbeddedFont,
    *, scan_dpi: int = 100,
) -> BuiltDocument:
    """One PDF with one page per sheet, in order."""
    outlines = OutlineFont(font)
    pdf = Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)

    layer_names = sorted({op.layer for sheet in sheets for op in sheet.ops if op.layer})
    layer_refs = {name: pdfwrite.add_ocg(pdf, name) for name in layer_names}
    layer_tags = {name: f"OC{index + 1}" for index, name in enumerate(layer_names)}
    uses_hatch = any(isinstance(op, Hatch) for sheet in sheets for op in sheet.ops)
    pattern_ref = (
        pdfwrite.add_hatch_pattern(pdf, spacing=4.0, width=0.4, rgb=BLACK) if uses_hatch else None
    )

    page_refs: list[Ref] = []
    built: list[BuiltPage] = []
    for sheet in sheets:
        resources: dict[str, object] = {}
        image_bytes: bytes | None = None
        if sheet.scan:
            bitmap = rasterise(sheet, outlines, scan_dpi)
            image_bytes = bitmap.packed()
            image_ref = pdf.add_stream({
                "Type": Name("XObject"), "Subtype": Name("Image"),
                "Width": bitmap.width, "Height": bitmap.height,
                "ColorSpace": Name("DeviceGray"), "BitsPerComponent": 1,
            }, image_bytes)
            resources["XObject"] = {"Im1": image_ref}
            content = f"q {pdfwrite._n(sheet.width, 2)} 0 0 {pdfwrite._n(sheet.height, 2)} 0 0 cm /Im1 Do Q\n"
        else:
            resources["Font"] = {FONT_RESOURCE: font_ref}
            if pattern_ref is not None and any(isinstance(op, Hatch) for op in sheet.ops):
                resources["Pattern"] = {PATTERN_RESOURCE: pattern_ref}
            used_layers = sorted({op.layer for op in sheet.ops if op.layer})
            if used_layers:
                resources["Properties"] = {layer_tags[name]: layer_refs[name] for name in used_layers}
            content = render_content(sheet.ops, font, layer_tags)
        content_bytes = content.encode("ascii")
        content_ref = pdf.add_stream({}, content_bytes)

        annot_refs: list[Ref] = []
        for note in sheet.annotations:
            if note.kind == "text":
                annot_refs.append(pdfwrite.add_text_annotation(
                    pdf, note.rect, note.contents, author=note.author, modified=note.modified, color=note.rgb))
            elif note.kind == "square":
                annot_refs.append(pdfwrite.add_square_annotation(
                    pdf, note.rect, color=note.rgb, contents=note.contents, author=note.author,
                    modified=note.modified))
            else:
                raise ValueError(f"unknown annotation kind {note.kind!r}")

        page_refs.append(pdf.add(pdfwrite.page_dictionary(
            pages_ref, [0, 0, round(sheet.width, 2), round(sheet.height, 2)],
            resources, content_ref, annots=annot_refs or None)))
        built.append(BuiltPage(
            sheet_id=sheet.sheet_id, content=content_bytes, media_box=(sheet.width, sheet.height),
            has_text_layer=not sheet.scan, image_bytes=image_bytes))

    pdf.put(pages_ref, {"Type": Name("Pages"), "Kids": page_refs, "Count": len(page_refs)})
    catalog: dict[str, object] = {
        "Type": Name("Catalog"),
        "Pages": pages_ref,
        "Lang": RawBytes(pdfwrite.pdf_literal("ru-RU")),
    }
    if layer_refs:
        catalog["OCProperties"] = pdfwrite.ocg_properties([layer_refs[name] for name in layer_names])
    pdf.put(catalog_ref, catalog)
    doc_id = hashlib.sha256(meta.doc_id_seed.encode("utf-8")).digest()[:16]
    data = pdf.serialize(catalog_ref, _info(meta), doc_id)
    return BuiltDocument(data=data, pages=built)


# --------------------------------------------------------------------------------------
# What changed between two versions of a sheet
# --------------------------------------------------------------------------------------


def _geometry_key(op: Op) -> tuple:
    if isinstance(op, Text):
        return (op.x, op.y)
    if isinstance(op, Line):
        return (op.x1, op.y1, op.x2, op.y2)
    if isinstance(op, (Rect, Hatch)):
        return (op.x, op.y, op.w, op.h)
    if isinstance(op, Circle):
        return (op.cx, op.cy, op.r)
    raise TypeError(type(op).__name__)


def _style_key(op: Op) -> tuple:
    if isinstance(op, Text):
        return (op.rgb, op.size)
    if isinstance(op, Line):
        return (op.rgb, op.width, op.dash)
    if isinstance(op, Rect):
        return (op.rgb, op.width, op.dash, op.fill)
    if isinstance(op, Circle):
        return (op.rgb, op.width)
    return ()


def diff_sheets(
    before: Sheet | None, after: Sheet | None, font: pdfwrite.EmbeddedFont,
) -> list[dict[str, object]]:
    """Every object-level change between two versions of a sheet, in a stable order.

    Frame objects are compared like the others. A `kind` is one of `text_added`,
    `text_removed`, `text_changed`, `text_moved`, `text_style`, `graphic_added`, `graphic_removed`,
    `graphic_moved`, `graphic_color`, `graphic_width`, `graphic_dash`.
    """
    old = before.by_id() if before else {}
    new = after.by_id() if after else {}
    changes: list[dict[str, object]] = []

    def record(kind: str, op_id: str, zone: str, a: Op | None, b: Op | None, **extra: object) -> None:
        entry: dict[str, object] = {"id": op_id, "kind": kind, "zone": zone}
        entry.update(extra)
        if a is not None:
            entry["bbox_before"] = list(bbox(a, font))
        if b is not None:
            entry["bbox_after"] = list(bbox(b, font))
        changes.append(entry)

    for op_id in sorted(set(old) | set(new)):
        a, b = old.get(op_id), new.get(op_id)
        if a is None and b is not None:
            if isinstance(b, Text):
                record("text_added", op_id, b.zone, None, b, after=b.text)
            else:
                record("graphic_added", op_id, b.zone, None, b)
        elif b is None and a is not None:
            if isinstance(a, Text):
                record("text_removed", op_id, a.zone, a, None, before=a.text)
            else:
                record("graphic_removed", op_id, a.zone, a, None)
        elif a is not None and b is not None:
            if isinstance(a, Text) and isinstance(b, Text):
                if a.text != b.text:
                    record("text_changed", op_id, b.zone, a, b, before=a.text, after=b.text)
                elif _geometry_key(a) != _geometry_key(b):
                    record("text_moved", op_id, b.zone, a, b, before=a.text, after=b.text)
                elif _style_key(a) != _style_key(b):
                    record("text_style", op_id, b.zone, a, b)
                continue
            if _geometry_key(a) != _geometry_key(b):
                record("graphic_moved", op_id, b.zone, a, b)
            if getattr(a, "rgb", None) != getattr(b, "rgb", None):
                record("graphic_color", op_id, b.zone, a, b,
                       before=list(a.rgb), after=list(b.rgb))  # type: ignore[attr-defined]
            if getattr(a, "width", None) != getattr(b, "width", None):
                record("graphic_width", op_id, b.zone, a, b,
                       before=a.width, after=b.width)  # type: ignore[attr-defined]
            if getattr(a, "dash", None) != getattr(b, "dash", None):
                record("graphic_dash", op_id, b.zone, a, b,
                       before=a.dash, after=b.dash)  # type: ignore[attr-defined]
    return changes
