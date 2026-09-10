"""Minimal, deterministic TrueType subsetter (pure standard library).

Why this exists: the AR baseline needs a real embedded font so the Cyrillic text layer
renders as well as it extracts, but the repository lock carries no font tooling and the
generator must not depend on a font that happens to be installed on the build machine.
So the subset is built once from a system source font, committed under
``tools/fixtures/assets/``, and the committed subset is what the generator embeds. The
build machine is then irrelevant and byte-reproduction is unconditional.

Output determinism: table order is fixed, glyph order is the sorted source glyph order,
every padding byte is zero and ``head.checkSumAdjustment`` is derived from the bytes. The
same input font and the same character set always produce the same output bytes.

Scope: what PDF 32000-1 section 9.9 requires of an embedded CIDFontType2 program, plus
``cmap``, ``name`` and ``post`` so the result is a well-formed standalone TrueType font.
Only format-4 ``cmap`` sources and ``glyf``/``loca`` outlines are handled; CFF-flavoured
(OpenType) sources are rejected explicitly rather than mis-parsed.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# Composite-glyph component flags (OpenType spec, `glyf` table).
_ARG_1_AND_2_ARE_WORDS = 0x0001
_WE_HAVE_A_SCALE = 0x0008
_MORE_COMPONENTS = 0x0020
_WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
_WE_HAVE_A_TWO_BY_TWO = 0x0080

# Tables copied through untouched. `cvt `, `fpgm` and `prep` are the hinting environment
# that the retained glyph instructions reference; copying them verbatim keeps those
# instructions consistent, which is safer and shorter than stripping instructions.
_COPY_TABLES = ("cvt ", "fpgm", "prep")

# Fixed emission order, which is also the tag-sorted order the directory requires.
_TABLE_ORDER = (
    "cmap", "cvt ", "fpgm", "glyf", "head", "hhea",
    "hmtx", "loca", "maxp", "name", "post", "prep",
)


class SubsetError(RuntimeError):
    """The source font cannot be subset by this module."""


@dataclass(frozen=True)
class SubsetResult:
    """A built subset plus the mapping the PDF writer needs to address its glyphs."""

    font_bytes: bytes
    units_per_em: int
    char_to_gid: dict[str, int]
    gid_advance: dict[int, int]
    ascent: int
    descent: int
    cap_height: int
    bbox: tuple[int, int, int, int]


def _read_tables(data: bytes) -> dict[str, tuple[int, int]]:
    if len(data) < 12:
        raise SubsetError("source font is shorter than an sfnt offset table")
    tag = data[:4]
    if tag == b"OTTO":
        raise SubsetError(
            "source font is CFF-flavoured (OTTO); only glyf outlines are supported"
        )
    if tag not in (b"\x00\x01\x00\x00", b"true"):
        raise SubsetError(f"unsupported sfnt version {tag!r}")
    num_tables = struct.unpack_from(">H", data, 4)[0]
    tables: dict[str, tuple[int, int]] = {}
    for i in range(num_tables):
        off = 12 + i * 16
        name, _checksum, toff, tlen = struct.unpack_from(">4sIII", data, off)
        tables[name.decode("latin-1")] = (toff, tlen)
    return tables


def _table(data: bytes, tables: dict[str, tuple[int, int]], name: str) -> bytes:
    if name not in tables:
        raise SubsetError(f"source font has no {name!r} table")
    off, length = tables[name]
    return data[off:off + length]


def _parse_cmap4(data: bytes, tables: dict[str, tuple[int, int]]) -> dict[int, int]:
    """Return codepoint -> source glyph id from the best available format-4 subtable."""
    cmap_off, _ = tables["cmap"]
    num_sub = struct.unpack_from(">H", data, cmap_off + 2)[0]
    chosen: int | None = None
    for i in range(num_sub):
        plat, enc, sub_off = struct.unpack_from(">HHI", data, cmap_off + 4 + i * 8)
        fmt = struct.unpack_from(">H", data, cmap_off + sub_off)[0]
        if fmt != 4:
            continue
        # Prefer Windows/Unicode BMP (3,1); accept a Unicode platform table otherwise.
        if (plat, enc) == (3, 1):
            chosen = cmap_off + sub_off
            break
        if plat == 0 and chosen is None:
            chosen = cmap_off + sub_off
    if chosen is None:
        raise SubsetError("source font has no format-4 Unicode cmap subtable")

    seg_x2 = struct.unpack_from(">H", data, chosen + 6)[0]
    seg = seg_x2 // 2
    ends = struct.unpack_from(f">{seg}H", data, chosen + 14)
    starts = struct.unpack_from(f">{seg}H", data, chosen + 16 + seg_x2)
    deltas = struct.unpack_from(f">{seg}h", data, chosen + 16 + 2 * seg_x2)
    range_off_pos = chosen + 16 + 3 * seg_x2
    range_offsets = struct.unpack_from(f">{seg}H", data, range_off_pos)

    out: dict[int, int] = {}
    for i in range(seg):
        start, end = starts[i], ends[i]
        if start == 0xFFFF:
            continue
        for code in range(start, end + 1):
            if range_offsets[i] == 0:
                gid = (code + deltas[i]) & 0xFFFF
            else:
                gpos = range_off_pos + i * 2 + range_offsets[i] + (code - start) * 2
                if gpos + 2 > len(data):
                    continue
                gid = struct.unpack_from(">H", data, gpos)[0]
                if gid != 0:
                    gid = (gid + deltas[i]) & 0xFFFF
            if gid:
                out[code] = gid
    return out


def _parse_loca(loca: bytes, num_glyphs: int, long_format: bool) -> list[int]:
    n = num_glyphs + 1
    if long_format:
        return list(struct.unpack_from(f">{n}I", loca, 0))
    return [v * 2 for v in struct.unpack_from(f">{n}H", loca, 0)]


def _composite_components(glyph: bytes) -> list[tuple[int, int]]:
    """Return (offset of the glyphIndex field, component gid) for a composite glyph."""
    pos = 10
    found: list[tuple[int, int]] = []
    while True:
        flags, glyph_index = struct.unpack_from(">HH", glyph, pos)
        found.append((pos + 2, glyph_index))
        pos += 4
        pos += 4 if flags & _ARG_1_AND_2_ARE_WORDS else 2
        if flags & _WE_HAVE_A_SCALE:
            pos += 2
        elif flags & _WE_HAVE_AN_X_AND_Y_SCALE:
            pos += 4
        elif flags & _WE_HAVE_A_TWO_BY_TWO:
            pos += 8
        if not flags & _MORE_COMPONENTS:
            break
    return found


def _checksum(table: bytes) -> int:
    padded = table + b"\x00" * (-len(table) % 4)
    total = 0
    for (word,) in struct.iter_unpack(">I", padded):
        total = (total + word) & 0xFFFFFFFF
    return total


def _name_table(strings: list[tuple[int, str]]) -> bytes:
    """Minimal `name` table: Windows / Unicode BMP / English-US records, UTF-16BE."""
    records = sorted(strings)
    storage = b""
    offsets: list[tuple[int, int, int]] = []
    for name_id, text in records:
        encoded = text.encode("utf-16-be")
        offsets.append((name_id, len(encoded), len(storage)))
        storage += encoded
    out = struct.pack(">HHH", 0, len(records), 6 + 12 * len(records))
    for name_id, length, offset in offsets:
        out += struct.pack(">HHHHHH", 3, 1, 0x0409, name_id, length, offset)
    return out + storage


def _cmap4_table(char_to_new_gid: dict[int, int]) -> bytes:
    """Build a format-4 subtable, one segment per contiguous run of codepoints."""
    codes = sorted(char_to_new_gid)
    segments: list[tuple[int, int]] = []
    for code in codes:
        if segments and code == segments[-1][1] + 1:
            segments[-1] = (segments[-1][0], code)
        else:
            segments.append((code, code))
    segments.append((0xFFFF, 0xFFFF))

    seg = len(segments)
    end_codes: list[int] = []
    start_codes: list[int] = []
    id_deltas: list[int] = []
    id_range_offsets: list[int] = []
    glyph_ids: list[int] = []
    # Every real segment resolves through glyphIdArray, so no delta arithmetic can wrap.
    for i, (start, end) in enumerate(segments):
        start_codes.append(start)
        end_codes.append(end)
        if start == 0xFFFF:
            id_deltas.append(1)
            id_range_offsets.append(0)
            continue
        id_deltas.append(0)
        # Offset measured from this entry's own position to its first glyphIdArray slot.
        id_range_offsets.append((seg - i) * 2 + len(glyph_ids) * 2)
        for code in range(start, end + 1):
            glyph_ids.append(char_to_new_gid[code])

    seg_x2 = seg * 2
    entry_selector = max(0, seg.bit_length() - 1)
    search_range = 2 * (1 << entry_selector)
    body = struct.pack(">HHHH", seg_x2, search_range, entry_selector, seg_x2 - search_range)
    body += struct.pack(f">{seg}H", *end_codes)
    body += struct.pack(">H", 0)
    body += struct.pack(f">{seg}H", *start_codes)
    body += struct.pack(f">{seg}h", *id_deltas)
    body += struct.pack(f">{seg}H", *id_range_offsets)
    if glyph_ids:
        body += struct.pack(f">{len(glyph_ids)}H", *glyph_ids)
    subtable = struct.pack(">HHH", 4, len(body) + 6, 0) + body
    header = struct.pack(">HH", 0, 1) + struct.pack(">HHI", 3, 1, 12)
    return header + subtable


def subset(source: bytes, characters: str, *, font_name: str, notice: str) -> SubsetResult:
    """Build a standalone TrueType font holding only the glyphs `characters` needs.

    `font_name` is written into the `name` table and is what the PDF ``/BaseFont`` should
    use. `notice` is the copyright/licence string that the source font's licence requires
    to travel with every copy.
    """
    tables = _read_tables(source)

    head = bytearray(_table(source, tables, "head"))
    units_per_em = struct.unpack_from(">H", head, 18)[0]
    index_to_loc = struct.unpack_from(">h", head, 50)[0]
    x_min, y_min, x_max, y_max = struct.unpack_from(">hhhh", head, 36)

    maxp = bytearray(_table(source, tables, "maxp"))
    num_glyphs = struct.unpack_from(">H", maxp, 4)[0]

    hhea = bytearray(_table(source, tables, "hhea"))
    ascent, descent = struct.unpack_from(">hh", hhea, 4)
    num_h_metrics = struct.unpack_from(">H", hhea, 34)[0]

    hmtx = _table(source, tables, "hmtx")
    loca = _parse_loca(_table(source, tables, "loca"), num_glyphs, index_to_loc == 1)
    glyf = _table(source, tables, "glyf")
    cmap = _parse_cmap4(source, tables)

    def source_advance(gid: int) -> int:
        return struct.unpack_from(">H", hmtx, min(gid, num_h_metrics - 1) * 4)[0]

    def source_lsb(gid: int) -> int:
        if gid < num_h_metrics:
            return struct.unpack_from(">h", hmtx, gid * 4 + 2)[0]
        return struct.unpack_from(">h", hmtx, num_h_metrics * 4 + (gid - num_h_metrics) * 2)[0]

    def glyph_bytes(gid: int) -> bytes:
        return glyf[loca[gid]:loca[gid + 1]]

    wanted = {c for c in characters if c != "\n"}
    missing = sorted(c for c in wanted if ord(c) not in cmap)
    if missing:
        raise SubsetError(f"source font has no glyph for: {''.join(missing)!r}")

    # Glyph closure: every requested character plus every component a composite glyph
    # reaches, transitively. `.notdef` (gid 0) is always present.
    needed = {0}
    pending = [cmap[ord(c)] for c in wanted]
    while pending:
        gid = pending.pop()
        if gid in needed:
            continue
        needed.add(gid)
        raw = glyph_bytes(gid)
        if len(raw) >= 10 and struct.unpack_from(">h", raw, 0)[0] < 0:
            pending.extend(comp for _pos, comp in _composite_components(raw))

    old_gids = sorted(needed)
    old_to_new = {old: new for new, old in enumerate(old_gids)}

    new_glyf = bytearray()
    new_loca = [0]
    for old in old_gids:
        raw = bytearray(glyph_bytes(old))
        if len(raw) >= 10 and struct.unpack_from(">h", raw, 0)[0] < 0:
            for pos, comp in _composite_components(bytes(raw)):
                struct.pack_into(">H", raw, pos, old_to_new[comp])
        new_glyf += raw
        new_glyf += b"\x00" * (-len(new_glyf) % 4)
        new_loca.append(len(new_glyf))

    new_count = len(old_gids)
    out_tables: dict[str, bytes] = {
        "glyf": bytes(new_glyf),
        "loca": struct.pack(f">{new_count + 1}I", *new_loca),
    }

    hmtx_out = bytearray()
    gid_advance: dict[int, int] = {}
    for old in old_gids:
        advance = source_advance(old)
        gid_advance[old_to_new[old]] = advance
        hmtx_out += struct.pack(">Hh", advance, source_lsb(old))
    out_tables["hmtx"] = bytes(hmtx_out)

    struct.pack_into(">h", head, 50, 1)  # long loca
    struct.pack_into(">I", head, 8, 0)  # checkSumAdjustment, computed over the result
    out_tables["head"] = bytes(head)

    struct.pack_into(">H", hhea, 34, new_count)
    out_tables["hhea"] = bytes(hhea)

    struct.pack_into(">H", maxp, 4, new_count)
    out_tables["maxp"] = bytes(maxp)

    out_tables["cmap"] = _cmap4_table({ord(c): old_to_new[cmap[ord(c)]] for c in wanted})
    out_tables["name"] = _name_table([
        (0, notice), (1, font_name), (2, "Regular"), (4, font_name), (6, font_name),
    ])
    # `post` version 3.0: no glyph names, which is all an embedded subset needs.
    out_tables["post"] = struct.pack(">IIhhIIIIII", 0x00030000, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    for name in _COPY_TABLES:
        if name in tables:
            out_tables[name] = _table(source, tables, name)

    emitted = [t for t in _TABLE_ORDER if t in out_tables]
    if set(emitted) != set(out_tables):
        raise SubsetError("internal: a built table is missing from the fixed emission order")

    num_tables = len(emitted)
    entry_selector = max(0, num_tables.bit_length() - 1)
    search_range = 16 * (1 << entry_selector)
    font = bytearray(struct.pack(
        ">IHHHH", 0x00010000, num_tables,
        search_range, entry_selector, num_tables * 16 - search_range,
    ))
    offset = 12 + 16 * num_tables
    directory = bytearray()
    body = bytearray()
    for name in emitted:
        payload = out_tables[name]
        directory += struct.pack(
            ">4sIII", name.encode("latin-1"), _checksum(payload), offset, len(payload)
        )
        padded = payload + b"\x00" * (-len(payload) % 4)
        body += padded
        offset += len(padded)
    font += directory + body

    # head.checkSumAdjustment must make the whole file sum to 0xB1B0AFBA.
    head_dir = 12 + 16 * emitted.index("head")
    head_start = struct.unpack_from(">I", font, head_dir + 8)[0]
    struct.pack_into(
        ">I", font, head_start + 8, (0xB1B0AFBA - _checksum(bytes(font))) & 0xFFFFFFFF
    )

    return SubsetResult(
        font_bytes=bytes(font),
        units_per_em=units_per_em,
        char_to_gid={c: old_to_new[cmap[ord(c)]] for c in wanted},
        gid_advance=gid_advance,
        ascent=ascent,
        descent=descent,
        cap_height=int(round(0.73 * units_per_em)),
        bbox=(x_min, y_min, x_max, y_max),
    )
