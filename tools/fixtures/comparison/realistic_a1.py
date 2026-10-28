#!/usr/bin/env python3
"""A "realistic A1" sheet, for measurements. Never committed: it is written where the caller says.

    python3 tools/fixtures/comparison/realistic_a1.py OUT.pdf
    python3 tools/fixtures/comparison/realistic_a1.py OUT.pdf --second OUT_B.pdf --paint-ops 76000

What real A1 exports do to a PDF reader, and what the synthetic A4 corpus cannot show:

*   text is strokes: every character is a stroked outline, so the page has no text layer at all
    (the stamp, the sheet number and the text channel are all empty);
*   the page is stored portrait and shown landscape with `/Rotate 90`, and its `/CropBox` is
    not the `/MediaBox` (here inset 8.5 pt), so a reader that ignores either disagrees with
    PDFium about where a mark is;
*   one optional-content group (a "construction grid") is hidden by default: PDFium does not
    draw it, a reader that walks the content stream still counts it;
*   hatches (a tiling pattern in some rooms, thousands of parallel strokes in others), dashed
    axes and hidden lines, and contour lines exported as thousands of tiny segments;
*   a big element count: at least 76 000 painted paths and 75 000 reader elements (see below).

`--second` writes the same sheet again as a second producer would: the same marks, grouped by
line style and written in the opposite order, with the coordinates printed to three decimals
instead of two, a different `/Producer`, and a different document id. A comparison tuned on one
rendering must not call the other a different sheet.

Counting. The product's reader counts a drawing element as a segment of a path or any other page
object (`src/auditmanager/ingest/pdf_reader.py::_elements`), and the largest real page measured
had 75 486 of them. Another tool may count painted paths instead (a two-point line is one path and
two segments). So the sheet is padded until BOTH counts reach their minimum: `--paint-ops`
(default 76 000 painted paths) and `--elements` (default 75 000, the reader's count). The
default sheet therefore holds about 76 000 painted paths and about 180 000 reader elements: a
conservative stand-in for the real maximum, heavier than it by the reader's count. Pass
`--paint-ops 0` to ask only for the reader's count (about 75 000 elements, about 22 000 paths).
The tests measure with PDFium, the way the product does.

Deterministic: a fixed-seed linear congruential generator, no clock, no environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ar_corpus import pdfwrite  # noqa: E402
from ar_corpus.pdfwrite import Name, Pdf, RawBytes  # noqa: E402
from comparison import scene  # noqa: E402
from comparison.outlines import OutlineFont  # noqa: E402

DEFAULT_PAINT_OPS = 76_000
DEFAULT_ELEMENTS = 75_000
#: Landscape sheet (what a viewer shows) and the portrait page that stores it.
SHEET_W, SHEET_H = scene.landscape(scene.A1)
PAGE_W, PAGE_H = scene.A1
CROP_INSET = 8.5
LAYER = "Строительная сетка"
MIN_FREE_BYTES = 256 * 1024 * 1024

Color = tuple[float, float, float]
BLACK: Color = (0.0, 0.0, 0.0)
GREY: Color = (0.5, 0.5, 0.5)
RED: Color = (0.75, 0.0, 0.0)
BLUE: Color = (0.0, 0.3, 0.75)
DASH_AXIS = (12.0, 3.0, 2.0, 3.0)
DASH_HIDDEN = (4.0, 2.0)


@dataclass(frozen=True)
class Mark:
    """One painted thing: a line, a rectangle outline, or a string drawn as stroked outlines."""

    kind: str  # "line" | "rect" | "text" | "pattern"
    args: tuple
    width: float = 0.5
    rgb: Color = BLACK
    dash: tuple[float, ...] | None = None
    layer: str | None = None


class Lcg:
    """A fixed-seed generator; the output must never depend on the interpreter."""

    def __init__(self, seed: int) -> None:
        self.state = seed

    def next(self) -> float:
        self.state = (1103515245 * self.state + 12345) % 2147483648
        return self.state / 2147483648.0


def _r(value: float) -> float:
    return round(value, 3)


def _glyph_elements(outlines: OutlineFont, char: str) -> tuple[int, int]:
    """(painted paths, reader elements) of one stroked character.

    The reader (and PDFium's `FPDFPath_CountSegments`) counts a move and a line as one segment
    each, a cubic as three, and a closed contour that does not end at its start as one more (the
    closing line).
    `tests/contract/fixtures_comparison` checks this estimate against PDFium's own count.
    """
    contours = outlines.contours(char)
    if not contours:
        return 0, 0
    total = 0
    for contour in contours:
        start = current = (contour[0][1], contour[0][2])
        for seg in contour:
            kind = seg[0]
            if kind in ("m", "l"):
                total += 1
                current = (seg[1], seg[2])
            elif kind == "c":
                total += 3
                current = (seg[5], seg[6])
            elif kind == "h" and current != start:
                total += 1
    return 1, total


def build_marks(
    outlines: OutlineFont, font, paint_ops: int, min_elements: int,
) -> tuple[list[Mark], int, int]:
    """The sheet's marks in producer A's order, the painted paths and the reader's element count."""
    marks: list[Mark] = []
    counts = [0, 0]  # painted paths, reader elements
    rng = Lcg(20260427)

    def add(mark: Mark) -> None:
        marks.append(mark)
        if mark.kind == "text":
            for char in mark.args[0]:
                paths, elements = _glyph_elements(outlines, char)
                counts[0] += paths
                counts[1] += elements
        else:
            counts[0] += 1
            counts[1] += 2 if mark.kind == "line" else 5

    def short() -> bool:
        return counts[0] < paint_ops or counts[1] < min_elements

    def text(x: float, y: float, value: str, size: float, rgb: Color = BLACK, layer: str | None = None) -> None:
        add(Mark("text", (value, size, _r(x), _r(y)), width=0.18 if size < 12 else 0.3, rgb=rgb, layer=layer))

    # Frame and title block, drawn as strokes like everything else.
    stamp_ops, _box = scene.frame_and_stamp(
        (SHEET_W, SHEET_H), designation="СИНТ-03-ЭМ", title="План этажа 1. Корпус 1 (реалистичный лист А1)",
        stage="Р", sheet_no="1", revision_label="Изм.0", date="27.04.2026", organisation="СИНТЕТИКПРОЕКТ",
        font=font)
    for op in stamp_ops:
        if isinstance(op, scene.Rect):
            add(Mark("rect", (_r(op.x), _r(op.y), _r(op.w), _r(op.h)), width=op.width))
        elif isinstance(op, scene.Line):
            add(Mark("line", (_r(op.x1), _r(op.y1), _r(op.x2), _r(op.y2)), width=op.width))
        elif isinstance(op, scene.Text):
            text(op.x, op.y, op.text, op.size)

    # The room grid: 12 x 6 rooms in the upper part of the sheet.
    columns, rows = 12, 6
    left, right, bottom, top = 80.0, 2340.0, 360.0, 1650.0
    cell_w, cell_h = (right - left) / columns, (top - bottom) / rows
    for j in range(rows):
        for i in range(columns):
            x, y = left + i * cell_w, bottom + j * cell_h
            number = 101 + i + columns * j
            add(Mark("rect", (_r(x), _r(y), _r(cell_w), _r(cell_h)), width=1.2))
            text(x + 8, y + cell_h - 18, f"Пом. {number}", 9.0)
            area = 8.0 + ((i * 7 + j * 13) % 40) + ((i + j) % 10) / 10.0
            text(x + 8, y + cell_h - 32, f"{area:.1f} м²".replace(".", ","), 8.0)
            if (i + j) % 2 == 0:
                for x0, y0, x1, y1 in pdfwrite.hatch_segments(
                        x + 6, y + 6, cell_w - 12, cell_h - 50, spacing=2.0):
                    add(Mark("line", (_r(x0), _r(y0), _r(x1), _r(y1)), width=0.2, rgb=GREY))
            if (i + 2 * j) % 5 == 0:
                add(Mark("pattern", (_r(x + 10), _r(y + 10), _r(cell_w - 20), 24.0)))
            if (i * j) % 3 == 0:
                add(Mark("line", (_r(x), _r(y), _r(x + cell_w), _r(y + cell_h)), width=0.35,
                                  rgb=BLUE, dash=DASH_HIDDEN))
    for i in range(columns + 1):
        x = left + i * cell_w
        add(Mark("line", (_r(x), 330.0, _r(x), 1655.0), width=0.4, dash=DASH_AXIS))
        text(x - 4, 1657.0, str(i + 1), 9.0)
    for j in range(rows + 1):
        y = bottom + j * cell_h
        add(Mark("line", (60.0, _r(y), 2350.0, _r(y)), width=0.4, dash=DASH_AXIS))
        text(62.0, y + 2, chr(0x410 + j % 25), 11.0)
    for i in range(columns):
        text(left + i * cell_w + cell_w / 2 - 14, 1634.0, str(int(cell_w * 42.5)), 8.0, rgb=RED)

    # The hidden layer: a construction grid. PDFium does not draw it; a content-stream reader sees it.
    for _ in range(1500):
        x, y = left + rng.next() * (right - left), 200.0 + rng.next() * 1450.0
        add(Mark("line", (_r(x), _r(y), _r(x + 30 + 40 * rng.next()), _r(y)), width=0.25, rgb=GREY,
                          dash=DASH_HIDDEN, layer=LAYER))

    # Contour lines of the site, exported as thousands of 1.5-point segments: the padding that
    # brings the sheet to the requested size.
    curve = 0
    while short():
        base = 200.0 + (curve % 20) * 7.0
        amp = 6.0 + (curve % 5)
        phase = rng.next() * math.tau
        x = left
        previous = (x, base + amp * math.sin(phase))
        while x < 1800.0 and short():
            x += 1.5
            point = (x, base + amp * math.sin(0.012 * (x - left) + phase) + 0.4 * math.sin(0.11 * x))
            add(Mark("line", (_r(previous[0]), _r(previous[1]), _r(point[0]), _r(point[1])), width=0.18, rgb=RED if curve % 7 == 0 else BLACK))
            previous = point
        curve += 1
    return marks, counts[0], counts[1]


# --------------------------------------------------------------------------------------
# Producers
# --------------------------------------------------------------------------------------

_CM = f"0 1 -1 0 {pdfwrite._n(PAGE_W, 2)} 0 cm\n"


def _emit_a(marks: list[Mark], outlines: OutlineFont) -> list[str]:
    """Producer A: every mark in its own graphics state, in authored order, two decimals."""
    out: list[str] = []
    open_layer = None
    for mark in marks:
        if mark.layer != open_layer:
            if open_layer is not None:
                out.append(pdfwrite.layer_end())
            if mark.layer is not None:
                out.append(pdfwrite.layer_begin("OC1"))
            open_layer = mark.layer
        if mark.kind == "line":
            out.append(pdfwrite.stroke_line_op(*mark.args, width=mark.width, rgb=mark.rgb, dash=mark.dash, digits=2))
        elif mark.kind == "rect":
            out.append(pdfwrite.stroke_rect_op(*mark.args, width=mark.width, rgb=mark.rgb, dash=mark.dash, digits=2))
        elif mark.kind == "text":
            value, size, x, y = mark.args
            out.append(pdfwrite.stroke_text_op(outlines, value, size, x, y, width=mark.width, rgb=mark.rgb, digits=2))
        else:
            out.append(pdfwrite.pattern_fill_op(scene.PATTERN_RESOURCE, *mark.args, digits=2))
    if open_layer is not None:
        out.append(pdfwrite.layer_end())
    return out


def _emit_b(marks: list[Mark], outlines: OutlineFont) -> list[str]:
    """Producer B: strokes grouped by style (widest first), each group reversed, three decimals."""
    n = lambda v: pdfwrite._n(v, 3)  # noqa: E731
    groups: dict[tuple, list[Mark]] = {}
    patterns: list[Mark] = []
    for mark in marks:
        if mark.kind == "pattern":
            patterns.append(mark)
            continue
        key = (mark.layer or "", -mark.width, mark.rgb, mark.dash or ())
        groups.setdefault(key, []).append(mark)
    out: list[str] = []
    open_layer = None
    for key in sorted(groups):
        layer = key[0] or None
        if layer != open_layer:
            if open_layer is not None:
                out.append(pdfwrite.layer_end())
            if layer is not None:
                out.append(pdfwrite.layer_begin("OC1"))
            open_layer = layer
        members = groups[key]
        first = members[0]
        out.append(f"q {n(first.width)} w {pdfwrite._rgb(first.rgb, stroke=True)} 1 j 1 J {pdfwrite._dash(first.dash, 3)}\n")
        for mark in reversed(members):
            if mark.kind == "line":
                x1, y1, x2, y2 = mark.args
                out.append(f"{n(x1)} {n(y1)} m {n(x2)} {n(y2)} l S\n")
            elif mark.kind == "rect":
                x, y, w, h = mark.args
                out.append(f"{n(x)} {n(y)} {n(w)} {n(h)} re S\n")
            else:
                value, size, x, y = mark.args
                out.append(pdfwrite.stroke_text_op(outlines, value, size, x, y, width=mark.width, rgb=mark.rgb,
                                                   digits=3, bare=True))
        out.append("Q\n")
    if open_layer is not None:
        out.append(pdfwrite.layer_end())
    for mark in reversed(patterns):
        out.append(pdfwrite.pattern_fill_op(scene.PATTERN_RESOURCE, *mark.args, digits=3))
    return out


def _document(content: str, producer: str, seed: str, font: pdfwrite.EmbeddedFont) -> bytes:
    pdf = Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    ocg = pdfwrite.add_ocg(pdf, LAYER)
    pattern = pdfwrite.add_hatch_pattern(pdf, spacing=6.0, width=0.3, rgb=GREY)
    content_ref = pdf.add_stream({}, content.encode("ascii"))
    page = pdfwrite.page_dictionary(
        pages_ref, [0, 0, round(PAGE_W, 2), round(PAGE_H, 2)],
        {"Pattern": {scene.PATTERN_RESOURCE: pattern}, "Properties": {"OC1": ocg}},
        content_ref,
        crop_box=[CROP_INSET, CROP_INSET, round(PAGE_W - CROP_INSET, 2), round(PAGE_H - CROP_INSET, 2)],
        rotate=90,
    )
    page_ref = pdf.add(page)
    pdf.put(pages_ref, {"Type": Name("Pages"), "Kids": [page_ref], "Count": 1})
    pdf.put(catalog_ref, {
        "Type": Name("Catalog"), "Pages": pages_ref,
        "Lang": RawBytes(pdfwrite.pdf_literal("ru-RU")),
        "OCProperties": pdfwrite.ocg_properties([ocg], hidden=(ocg,)),
    })
    info = {
        "Title": pdfwrite.EncryptableString("СИНТ-03-ЭМ. План этажа 1 (реалистичный лист А1, синтетический)"),
        "Author": pdfwrite.EncryptableString(scene.AUTHOR),
        "Creator": pdfwrite.EncryptableString(producer),
        "Producer": pdfwrite.EncryptableString(producer),
        "CreationDate": RawBytes(pdfwrite.pdf_literal("D:20260427000000Z")),
        "ModDate": RawBytes(pdfwrite.pdf_literal("D:20260427000000Z")),
    }
    return pdf.serialize(catalog_ref, info, hashlib.sha256(seed.encode("utf-8")).digest()[:16])


@dataclass(frozen=True)
class Rendering:
    data: bytes
    producer: str
    painted_paths: int
    elements: int
    marks: int


def generate(
    paint_ops: int = DEFAULT_PAINT_OPS, min_elements: int = DEFAULT_ELEMENTS,
) -> tuple[Rendering, Rendering]:
    """The sheet as producer A and as producer B, in memory."""
    font = scene.load_font()
    outlines = OutlineFont(font)
    marks, painted, elements = build_marks(outlines, font, paint_ops, min_elements)
    a = _document(_CM + "".join(_emit_a(marks, outlines)), "SyntheticCAD Plotter 3.1 (producer A)",
                  "cmp-fixtures-01/a1/A", font)
    b = _document(_CM + "".join(_emit_b(marks, outlines)), "SyntheticCAD Export 9.4 (producer B)",
                  "cmp-fixtures-01/a1/B", font)
    return (Rendering(a, "A", painted, elements, len(marks)), Rendering(b, "B", painted, elements, len(marks)))


def write(
    path: Path, second: Path | None = None, paint_ops: int = DEFAULT_PAINT_OPS,
    min_elements: int = DEFAULT_ELEMENTS,
) -> dict[str, object]:
    """Write the sheet (and optionally the second rendering). Refuses on a nearly full disk."""
    for target in [p for p in (path, second) if p is not None]:
        target.parent.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(target.parent).free
        if free < MIN_FREE_BYTES:
            raise SystemExit(f"refusing to write: only {free // (1024 * 1024)} MiB free under {target.parent}")
    a, b = generate(paint_ops, min_elements)
    path.write_bytes(a.data)
    report: dict[str, object] = {
        "files": [{"path": str(path), "producer": a.producer, "bytes": len(a.data),
                   "sha256": hashlib.sha256(a.data).hexdigest()}],
        "painted_paths": a.painted_paths,
        "elements_by_the_readers_count": a.elements,
        "marks": a.marks,
        "page": {"media_box": [0, 0, round(PAGE_W, 2), round(PAGE_H, 2)], "rotate": 90,
                 "crop_box": [CROP_INSET, CROP_INSET, round(PAGE_W - CROP_INSET, 2), round(PAGE_H - CROP_INSET, 2)],
                 "optional_content_groups": [LAYER], "hidden_by_default": [LAYER]},
    }
    if second is not None:
        second.write_bytes(b.data)
        report["files"].append({"path": str(second), "producer": b.producer, "bytes": len(b.data),  # type: ignore[union-attr]
                                "sha256": hashlib.sha256(b.data).hexdigest()})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the realistic A1 sheet to a caller-given path.")
    parser.add_argument("out", type=Path, help="where to write producer A's rendering (outside the repository)")
    parser.add_argument("--second", type=Path, default=None, help="also write producer B's rendering here")
    parser.add_argument("--paint-ops", type=int, default=DEFAULT_PAINT_OPS,
                        help=f"minimum painted paths (default {DEFAULT_PAINT_OPS}; 0 to ask only for --elements)")
    parser.add_argument("--elements", type=int, default=DEFAULT_ELEMENTS,
                        help=f"minimum drawing elements by the product reader's count (default {DEFAULT_ELEMENTS})")
    args = parser.parse_args(argv)
    repo = scene.REPO_ROOT.resolve()
    for target in [p for p in (args.out, args.second) if p is not None]:
        if repo in target.resolve().parents:
            print(f"refusing: {target} is inside the repository; the sheet is never committed", file=sys.stderr)
            return 2
    print(json.dumps(write(args.out, args.second, args.paint_ops, args.elements), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
