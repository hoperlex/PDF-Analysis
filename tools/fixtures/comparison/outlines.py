"""TrueType glyph outlines, for text that is drawn as paths and for the scan rasteriser.

The embedded `ARCorpusSans` subset already carries every outline the corpus needs; this reads
them out of the `glyf` table. TrueType contours are quadratic splines through on- and
off-curve points; they are returned as cubic Béziers, which is what a PDF path can draw.

Only the parts of the format the subset uses are read: simple glyphs and composites with
translation and scale. A glyph without outline (the space) returns no contours.
"""

from __future__ import annotations

import struct

Segment = tuple  # ("m", x, y) | ("l", x, y) | ("c", x1, y1, x2, y2, x3, y3) | ("h",)


class OutlineError(RuntimeError):
    pass


def _tables(data: bytes) -> dict[str, tuple[int, int]]:
    count = struct.unpack(">H", data[4:6])[0]
    out: dict[str, tuple[int, int]] = {}
    for index in range(count):
        tag, _checksum, offset, length = struct.unpack(">4sIII", data[12 + 16 * index:28 + 16 * index])
        out[tag.decode("ascii")] = (offset, length)
    return out


class OutlineFont:
    """Outlines of an `EmbeddedFont` (`pdfwrite.EmbeddedFont`), keyed by character."""

    def __init__(self, font) -> None:
        self._font = font
        data = font.font_bytes
        tables = _tables(data)
        for needed in ("head", "maxp", "loca", "glyf"):
            if needed not in tables:
                raise OutlineError(f"the font has no {needed} table")
        head_at = tables["head"][0]
        self.units_per_em: int = struct.unpack(">H", data[head_at + 18:head_at + 20])[0]
        long_loca = struct.unpack(">h", data[head_at + 50:head_at + 52])[0] == 1
        glyph_count = struct.unpack(">H", data[tables["maxp"][0] + 4:tables["maxp"][0] + 6])[0]
        loca_at = tables["loca"][0]
        if long_loca:
            self._loca = list(struct.unpack(f">{glyph_count + 1}I", data[loca_at:loca_at + 4 * (glyph_count + 1)]))
        else:
            half = struct.unpack(f">{glyph_count + 1}H", data[loca_at:loca_at + 2 * (glyph_count + 1)])
            self._loca = [value * 2 for value in half]
        self._glyf_at = tables["glyf"][0]
        self._data = data
        self._cache: dict[int, list[list[Segment]]] = {}

    def advance(self, char: str) -> int:
        return self._font.gid_advance[self._font.char_to_gid[char]]

    def contours(self, char: str) -> list[list[Segment]]:
        return _contours(self, self._font.char_to_gid[char])

    def raw_points(self, gid: int) -> list[list[tuple[float, float, bool]]]:
        """Contours as on/off-curve point lists in font units (components resolved)."""
        return self._points(gid, 0)

    def _points(self, gid: int, depth: int) -> list[list[tuple[float, float, bool]]]:
        if depth > 4:
            raise OutlineError("composite glyph nesting is too deep")
        start, end = self._loca[gid], self._loca[gid + 1]
        if end <= start:
            return []
        data = self._data
        base = self._glyf_at + start
        contour_count = struct.unpack(">h", data[base:base + 2])[0]
        cursor = base + 10
        if contour_count >= 0:
            return _simple(data, cursor, contour_count)
        contours: list[list[tuple[float, float, bool]]] = []
        while True:
            flags, component = struct.unpack(">HH", data[cursor:cursor + 4])
            cursor += 4
            if flags & 0x0001:
                arg1, arg2 = struct.unpack(">hh", data[cursor:cursor + 4])
                cursor += 4
            else:
                arg1, arg2 = struct.unpack(">bb", data[cursor:cursor + 2])
                cursor += 2
            if not flags & 0x0002:
                raise OutlineError("composite glyph placed by points is not supported")
            a, b, c, d = 1.0, 0.0, 0.0, 1.0
            if flags & 0x0008:
                a = d = struct.unpack(">h", data[cursor:cursor + 2])[0] / 16384.0
                cursor += 2
            elif flags & 0x0040:
                a, d = (v / 16384.0 for v in struct.unpack(">hh", data[cursor:cursor + 4]))
                cursor += 4
            elif flags & 0x0080:
                a, b, c, d = (v / 16384.0 for v in struct.unpack(">hhhh", data[cursor:cursor + 8]))
                cursor += 8
            for contour in self._points(component, depth + 1):
                contours.append([(a * x + c * y + arg1, b * x + d * y + arg2, on) for x, y, on in contour])
            if not flags & 0x0020:
                return contours


def _simple(data: bytes, cursor: int, contour_count: int) -> list[list[tuple[float, float, bool]]]:
    if contour_count == 0:
        return []
    ends = list(struct.unpack(f">{contour_count}H", data[cursor:cursor + 2 * contour_count]))
    cursor += 2 * contour_count
    instruction_length = struct.unpack(">H", data[cursor:cursor + 2])[0]
    cursor += 2 + instruction_length
    point_count = ends[-1] + 1
    flags: list[int] = []
    while len(flags) < point_count:
        flag = data[cursor]
        cursor += 1
        flags.append(flag)
        if flag & 0x08:
            repeat = data[cursor]
            cursor += 1
            flags.extend([flag] * repeat)
    xs: list[int] = []
    value = 0
    for flag in flags:
        if flag & 0x02:
            delta = data[cursor]
            cursor += 1
            value += delta if flag & 0x10 else -delta
        elif not flag & 0x10:
            value += struct.unpack(">h", data[cursor:cursor + 2])[0]
            cursor += 2
        xs.append(value)
    ys: list[int] = []
    value = 0
    for flag in flags:
        if flag & 0x04:
            delta = data[cursor]
            cursor += 1
            value += delta if flag & 0x20 else -delta
        elif not flag & 0x20:
            value += struct.unpack(">h", data[cursor:cursor + 2])[0]
            cursor += 2
        ys.append(value)
    out: list[list[tuple[float, float, bool]]] = []
    first = 0
    for end in ends:
        out.append([(float(xs[i]), float(ys[i]), bool(flags[i] & 0x01)) for i in range(first, end + 1)])
        first = end + 1
    return out


def _to_segments(points: list[tuple[float, float, bool]]) -> list[Segment]:
    """One contour of quadratic-spline points as `m`, `l`, `c` and `h` segments."""
    count = len(points)
    if count < 2:
        return []
    expanded: list[tuple[float, float, bool]] = []
    for index, point in enumerate(points):
        following = points[(index + 1) % count]
        expanded.append(point)
        if not point[2] and not following[2]:
            expanded.append(((point[0] + following[0]) / 2.0, (point[1] + following[1]) / 2.0, True))
    first_on = next((i for i, p in enumerate(expanded) if p[2]), None)
    if first_on is None:
        return []
    ring = expanded[first_on:] + expanded[:first_on]
    size = len(ring)
    segments: list[Segment] = [("m", ring[0][0], ring[0][1])]
    current = ring[0]
    index = 1
    while index < size:
        point = ring[index]
        if point[2]:
            segments.append(("l", point[0], point[1]))
            current = point
            index += 1
            continue
        target = ring[(index + 1) % size]
        segments.append((
            "c",
            current[0] + 2.0 / 3.0 * (point[0] - current[0]),
            current[1] + 2.0 / 3.0 * (point[1] - current[1]),
            target[0] + 2.0 / 3.0 * (point[0] - target[0]),
            target[1] + 2.0 / 3.0 * (point[1] - target[1]),
            target[0], target[1],
        ))
        current = target
        index += 2
    segments.append(("h",))
    return segments


def _contours(font: OutlineFont, gid: int) -> list[list[Segment]]:
    cache = font._cache
    if gid not in cache:
        cache[gid] = [seg for seg in (_to_segments(c) for c in font.raw_points(gid)) if seg]
    return cache[gid]


def flatten(contour: list[Segment], steps: int = 6) -> list[tuple[float, float]]:
    """A contour as a polygon (cubic segments sampled in `steps` pieces), for the rasteriser."""
    polygon: list[tuple[float, float]] = []
    current = (0.0, 0.0)
    for seg in contour:
        kind = seg[0]
        if kind in ("m", "l"):
            current = (seg[1], seg[2])
            polygon.append(current)
        elif kind == "c":
            x0, y0 = current
            x1, y1, x2, y2, x3, y3 = seg[1:]
            for step in range(1, steps + 1):
                t = step / steps
                u = 1.0 - t
                polygon.append((
                    u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3,
                    u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3,
                ))
            current = (x3, y3)
    return polygon
