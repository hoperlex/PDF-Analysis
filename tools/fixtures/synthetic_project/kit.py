"""Drawing kit for the synthetic production project: a builder of `scene` operations.

Everything is in PDF points, origin at the lower left of the page (`scene`'s convention).
`Ops` hands out unique, stable operation ids, so a sheet can be rebuilt byte for byte and two
versions of a sheet can be compared object by object.

The embedded font (`tools/fixtures/assets/ARCorpusSans.ttf`) covers ASCII, Cyrillic and
`«»°²³×–—‘’“”„…№−` only. `Ops.text` refuses any other character (no `Ø`, `±`, `≤`, `≥`):
write «Ду50», «не менее» instead.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from comparison import scene
from comparison.scene import BLACK, Circle, Hatch, Line, Rect, Text

MM = scene.MM
GREY = (0.55, 0.55, 0.55)
LIGHT = (0.78, 0.78, 0.78)
WALL_FILL = (0.82, 0.82, 0.82)
RED = (0.85, 0.1, 0.1)
BLUE = (0.1, 0.25, 0.85)
GREEN = (0.05, 0.55, 0.2)
ORANGE = (0.95, 0.5, 0.0)
MAGENTA = (0.7, 0.1, 0.6)
CYAN = (0.0, 0.6, 0.75)
BROWN = (0.55, 0.3, 0.1)

_FONT = None


def font():
    global _FONT
    if _FONT is None:
        _FONT = scene.load_font()
    return _FONT


def width_of(text: str, size: float) -> float:
    return font().text_width(text, size)


def check_chars(text: str) -> None:
    missing = sorted({c for c in text if c not in font().char_to_gid})
    if missing:
        raise ValueError(f"characters not in the embedded font: {missing!r} in {text!r}")


def wrap(text: str, size: float, max_width: float) -> list[str]:
    """Greedy word wrap by the font's real advance widths."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if width_of(candidate, size) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class Ops:
    """Accumulates operations for one sheet; ids are `<prefix>.<kind><n>` or `<prefix>.f.<key>`."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.ops: list[scene.Op] = []
        self._n = 0
        self._keys: set[str] = set()

    def _id(self, kind: str, key: str | None = None) -> str:
        if key is not None:
            if key in self._keys:
                raise ValueError(f"{self.prefix}: duplicate fragment key {key!r}")
            self._keys.add(key)
            return f"{self.prefix}.f.{key}"
        self._n += 1
        return f"{self.prefix}.{kind}{self._n}"

    def extend(self, other: "Ops") -> None:
        self.ops.extend(other.ops)

    # -- primitives -------------------------------------------------------------------

    def text(self, x: float, y: float, s: str, size: float = 9.0, rgb=BLACK, key: str | None = None) -> Text:
        check_chars(s)
        op = Text(self._id("t", key), x=round(x, 2), y=round(y, 2), text=s, size=size, rgb=rgb)
        self.ops.append(op)
        return op

    def ctext(self, cx: float, y: float, s: str, size: float = 9.0, rgb=BLACK, key: str | None = None) -> Text:
        return self.text(cx - width_of(s, size) / 2, y, s, size, rgb, key)

    def para(self, x: float, y: float, width: float, s: str, size: float = 9.0, leading: float | None = None,
             rgb=BLACK, key: str | None = None) -> float:
        """A wrapped paragraph whose first baseline is `y`; returns the next free baseline.

        With `key`, the first line gets the fragment id `key` and the others `key.2`, `key.3`...
        """
        lead = leading or size * 1.35
        for index, line in enumerate(wrap(s, size, width)):
            k = None if key is None else (key if index == 0 else f"{key}.{index + 1}")
            self.text(x, y, line, size, rgb, k)
            y -= lead
        return y

    def line(self, x1, y1, x2, y2, width: float = 0.5, rgb=BLACK, dash=None) -> None:
        self.ops.append(Line(self._id("l"), x1=round(x1, 2), y1=round(y1, 2), x2=round(x2, 2), y2=round(y2, 2),
                             width=width, rgb=rgb, dash=dash))

    def polyline(self, points: Sequence[tuple[float, float]], width: float = 0.5, rgb=BLACK, dash=None,
                 closed: bool = False) -> None:
        pts = list(points) + ([points[0]] if closed else [])
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.line(x1, y1, x2, y2, width, rgb, dash)

    def rect(self, x, y, w, h, width: float = 0.5, rgb=BLACK, dash=None, fill=None) -> None:
        self.ops.append(Rect(self._id("r"), x=round(x, 2), y=round(y, 2), w=round(w, 2), h=round(h, 2),
                             width=width, rgb=rgb, dash=dash, fill=fill))

    def circle(self, cx, cy, r, width: float = 0.5, rgb=BLACK) -> None:
        self.ops.append(Circle(self._id("c"), cx=round(cx, 2), cy=round(cy, 2), r=round(r, 2), width=width, rgb=rgb))

    def hatch(self, x, y, w, h) -> None:
        self.ops.append(Hatch(self._id("h"), x=round(x, 2), y=round(y, 2), w=round(w, 2), h=round(h, 2)))

    def arc(self, cx, cy, r, a0: float, a1: float, width: float = 0.4, rgb=BLACK, segments: int = 10) -> None:
        pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / segments)),
                cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / segments))) for i in range(segments + 1)]
        self.polyline(pts, width, rgb)

    def arrow(self, x1, y1, x2, y2, width: float = 0.6, rgb=BLACK, head: float = 6.0) -> None:
        self.line(x1, y1, x2, y2, width, rgb)
        ang = math.atan2(y2 - y1, x2 - x1)
        for side in (-1, 1):
            a = ang + math.pi + side * math.radians(25)
            self.line(x2, y2, x2 + head * math.cos(a), y2 + head * math.sin(a), width, rgb)

    def dim(self, x1, y1, x2, y2, label: str, offset: float = 14.0, size: float = 7.0) -> None:
        """A dimension line parallel to (x1,y1)-(x2,y2), shifted by `offset` to its left side."""
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length * offset, dx / length * offset
        a1, b1, a2, b2 = x1 + nx, y1 + ny, x2 + nx, y2 + ny
        self.line(x1, y1, a1 + nx * 0.25, b1 + ny * 0.25, 0.3)
        self.line(x2, y2, a2 + nx * 0.25, b2 + ny * 0.25, 0.3)
        self.line(a1, b1, a2, b2, 0.35)
        for (px, py) in ((a1, b1), (a2, b2)):
            self.line(px - 3, py - 3, px + 3, py + 3, 0.6)
        mx, my = (a1 + a2) / 2, (b1 + b2) / 2
        if abs(dy) < 1e-6:
            self.ctext(mx, my + 2.5, label, size)
        else:
            self.text(mx + 3, my - size / 3, label, size)

    def axis_bubble(self, x: float, y: float, label: str, r: float = 9.0) -> None:
        self.circle(x, y, r, 0.5)
        self.ctext(x, y - 3.2, label, 9.0)

    def leader(self, x1, y1, x2, y2, label: str, size: float = 7.5, rgb=BLACK, key: str | None = None) -> None:
        """A leader from a point to a shelf with a label above it."""
        self.line(x1, y1, x2, y2, 0.35, rgb)
        w = width_of(label, size) + 4
        self.line(x2, y2, x2 + w, y2, 0.35, rgb)
        self.text(x2 + 2, y2 + 2, label, size, rgb, key)

    # -- tables ---------------------------------------------------------------------

    def table(self, x: float, top: float, widths: Sequence[float], rows: Sequence[Sequence[str]], *,
              size: float = 7.5, row_h: float = 15.0, header_rows: int = 1, key: str | None = None,
              wrap_cells: bool = True) -> tuple[float, float, float, float]:
        """A ruled table; rows are lists of cell strings. Returns (x0, y0, x1, y1) with y0 the bottom.

        Cells wrap inside their column; a row is as tall as its tallest cell. With `key`, every cell's
        first line gets the fragment id `<key>.r<row>c<col>`.
        """
        total = sum(widths)
        y = top
        self.line(x, y, x + total, y, 0.8)
        for r_index, row in enumerate(rows):
            if len(row) != len(widths):
                raise ValueError(f"table row {r_index} has {len(row)} cells for {len(widths)} columns: {row!r}")
            cells = [wrap(str(c), size, w - 5) if wrap_cells and str(c) else [str(c)] for c, w in zip(row, widths)]
            lines_needed = max(1, *(len(c) for c in cells))
            h = max(row_h, lines_needed * size * 1.25 + 6)
            cx = x
            for c_index, (lines, w) in enumerate(zip(cells, widths)):
                ty = y - size - 3.5
                for l_index, line in enumerate(lines):
                    if line:
                        k = None
                        if key is not None and l_index == 0:
                            k = f"{key}.r{r_index}c{c_index}"
                        self.text(cx + 2.5, ty, line, size, key=k)
                    ty -= size * 1.25
                cx += w
            y -= h
            self.line(x, y, x + total, y, 0.8 if r_index == header_rows - 1 else 0.35)
        cx = x
        for w in [0, *widths]:
            cx += w
            self.line(cx, top, cx, y, 0.6)
        return (x, y, x + total, top)

    # -- architecture ----------------------------------------------------------------

    def wall(self, x1, y1, x2, y2, thick: float, underlay: bool = False) -> None:
        if abs(y1 - y2) < 1e-6:
            x0, x3 = min(x1, x2), max(x1, x2)
            self.rect(x0, y1 - thick / 2, x3 - x0, thick, 0.3 if underlay else 0.6,
                      LIGHT if underlay else BLACK, fill=None if underlay else WALL_FILL)
        else:
            y0, y3 = min(y1, y2), max(y1, y2)
            self.rect(x1 - thick / 2, y0, thick, y3 - y0, 0.3 if underlay else 0.6,
                      LIGHT if underlay else BLACK, fill=None if underlay else WALL_FILL)

    def door(self, x: float, y: float, w: float, direction: str, underlay: bool = False) -> None:
        """A door leaf and swing arc. (x, y) is the hinge; direction is one of 'ne','nw','se','sw','en','es','wn','ws'.

        The first letter is the wall the door sits in ('n'/'s' horizontal wall: the leaf swings north/south;
        'e'/'w' vertical wall), the second the side the leaf opens to.
        """
        rgb = LIGHT if underlay else BLACK
        lw = 0.3 if underlay else 0.5
        a, b = direction[0], direction[1]
        if a in "ns":
            sy = 1 if a == "n" else -1
            sx = 1 if b == "e" else -1
            self.line(x, y, x, y + sy * w, lw, rgb)
            start, end = (90, 0) if (sy, sx) == (1, 1) else (90, 180) if (sy, sx) == (1, -1) else (270, 360) if (sy, sx) == (-1, 1) else (270, 180)
            self.arc(x, y, w, start, end, 0.3 if underlay else 0.35, rgb)
        else:
            sx = 1 if a == "e" else -1
            sy = 1 if b == "n" else -1
            self.line(x, y, x + sx * w, y, lw, rgb)
            start, end = (0, 90) if (sx, sy) == (1, 1) else (0, -90) if (sx, sy) == (1, -1) else (180, 90) if (sx, sy) == (-1, 1) else (180, 270)
            self.arc(x, y, w, start, end, 0.3 if underlay else 0.35, rgb)

    def window(self, x1, y1, x2, y2, thick: float, underlay: bool = False) -> None:
        rgb = LIGHT if underlay else BLACK
        if abs(y1 - y2) < 1e-6:
            self.rect(min(x1, x2), y1 - thick / 2, abs(x2 - x1), thick, 0.4, rgb, fill=(1, 1, 1))
            self.line(min(x1, x2), y1, max(x1, x2), y1, 0.3, rgb)
        else:
            self.rect(x1 - thick / 2, min(y1, y2), thick, abs(y2 - y1), 0.4, rgb, fill=(1, 1, 1))
            self.line(x1, min(y1, y2), x1, max(y1, y2), 0.3, rgb)

    def stairs(self, x, y, w, h, steps: int = 10, underlay: bool = False) -> None:
        rgb = LIGHT if underlay else BLACK
        half = w / 2
        for i in range(steps + 1):
            yy = y + h * i / steps
            self.line(x, yy, x + w, yy, 0.3, rgb)
        self.line(x + half, y, x + half, y + h, 0.4, rgb)
        if not underlay:
            self.arrow(x + half / 2, y + 4, x + half / 2, y + h - 4, 0.4)

    # -- engineering symbols -----------------------------------------------------------

    def box_label(self, x, y, w, h, label: str, size: float = 7.0, rgb=BLACK, fill=None, key: str | None = None) -> None:
        self.rect(x, y, w, h, 0.7, rgb, fill=fill)
        self.ctext(x + w / 2, y + h / 2 - size / 3, label, size, rgb, key)

    def lamp(self, cx, cy, r: float = 5.0, rgb=BLACK) -> None:
        self.circle(cx, cy, r, 0.5, rgb)
        d = r * 0.7
        self.line(cx - d, cy - d, cx + d, cy + d, 0.4, rgb)
        self.line(cx - d, cy + d, cx + d, cy - d, 0.4, rgb)

    def socket(self, cx, cy, r: float = 4.0, rgb=BLACK) -> None:
        self.arc(cx, cy, r, 0, 180, 0.5, rgb, 8)
        self.line(cx - r, cy, cx + r, cy, 0.5, rgb)
        self.line(cx, cy + r, cx, cy + r + 3, 0.5, rgb)

    def detector(self, cx, cy, r: float = 4.5, rgb=RED) -> None:
        self.circle(cx, cy, r, 0.6, rgb)
        self.line(cx - r * 0.6, cy, cx + r * 0.6, cy, 0.5, rgb)

    def sprinkler(self, cx, cy, r: float = 3.5, rgb=RED) -> None:
        self.circle(cx, cy, r, 0.6, rgb)
        self.line(cx, cy - r, cx, cy + r, 0.5, rgb)

    def valve(self, cx, cy, s: float = 5.0, rgb=BLACK, vertical: bool = False) -> None:
        if vertical:
            self.polyline([(cx - s, cy - s), (cx + s, cy - s), (cx - s, cy + s), (cx + s, cy + s)], 0.6, rgb, closed=True)
        else:
            self.polyline([(cx - s, cy - s), (cx - s, cy + s), (cx + s, cy - s), (cx + s, cy + s)], 0.6, rgb, closed=True)

    def pump(self, cx, cy, r: float = 8.0, rgb=BLACK) -> None:
        self.circle(cx, cy, r, 0.7, rgb)
        self.polyline([(cx - r * 0.5, cy - r * 0.6), (cx + r * 0.8, cy), (cx - r * 0.5, cy + r * 0.6)], 0.6, rgb, closed=True)

    def fan(self, cx, cy, r: float = 9.0, rgb=BLACK) -> None:
        self.circle(cx, cy, r, 0.7, rgb)
        for a in (90, 210, 330):
            self.line(cx, cy, cx + r * 0.85 * math.cos(math.radians(a)), cy + r * 0.85 * math.sin(math.radians(a)), 0.5, rgb)

    def breaker(self, x, y, h: float = 18.0, rgb=BLACK) -> None:
        """A switching device on a vertical line from (x, y) downward: line, inclined contact, line."""
        self.line(x, y, x, y - h * 0.35, 0.6, rgb)
        self.line(x, y - h * 0.35, x + h * 0.3, y - h * 0.62, 0.6, rgb)
        self.line(x, y - h * 0.68, x, y - h, 0.6, rgb)
        self.line(x - 3, y - h * 0.35, x + 3, y - h * 0.35, 0.6, rgb)

    def duct(self, points: Sequence[tuple[float, float]], w: float, rgb=BLUE, dash=None) -> None:
        """A rectangular duct along an orthogonal polyline, drawn as two parallel lines."""
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if abs(y1 - y2) < 1e-6:
                self.line(x1, y1 - w / 2, x2, y2 - w / 2, 0.6, rgb, dash)
                self.line(x1, y1 + w / 2, x2, y2 + w / 2, 0.6, rgb, dash)
            else:
                self.line(x1 - w / 2, y1, x2 - w / 2, y2, 0.6, rgb, dash)
                self.line(x1 + w / 2, y1, x2 + w / 2, y2, 0.6, rgb, dash)

    def north_arrow(self, cx, cy, r: float = 14.0) -> None:
        self.circle(cx, cy, r, 0.5)
        self.polyline([(cx, cy + r), (cx - r * 0.35, cy - r * 0.6), (cx, cy - r * 0.2), (cx + r * 0.35, cy - r * 0.6)],
                      0.6, closed=True)
        self.ctext(cx, cy + r + 4, "С", 8)

    def tree(self, cx, cy, r: float = 7.0) -> None:
        self.circle(cx, cy, r, 0.5, GREEN)
        self.circle(cx, cy, r * 0.25, 0.5, GREEN)


def bbox_norm(box: tuple[float, float, float, float], size: tuple[float, float]) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) in PDF points, lower-left origin -> the portal's normalised top-left box."""
    x0, y0, x1, y1 = box
    w, h = size
    return (round(x0 / w, 4), round(1 - y1 / h, 4), round(x1 / w, 4), round(1 - y0 / h, 4))


def texts_in(ops: Iterable[scene.Op], box: tuple[float, float, float, float]) -> list[Text]:
    """The text operations anchored inside a box, in reading order (top to bottom, left to right)."""
    x0, y0, x1, y1 = box
    found = [op for op in ops if isinstance(op, Text) and op.zone == "content" and x0 <= op.x <= x1 and y0 <= op.y <= y1]
    return sorted(found, key=lambda t: (-round(t.y, 0), t.x))
