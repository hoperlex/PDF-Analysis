"""A minimal, byte-deterministic PDF writer (pure standard library).

The repository lock carries no PDF library and is a single-owner hotspot this session
does not own, so the corpus writes PDF 1.7 by hand. Only what the fixtures need is
implemented: a page tree, uncompressed content streams, one embedded CIDFontType2 font
with a `ToUnicode` CMap, image XObjects, and the 40-bit RC4 standard security handler for
the encrypted negative fixture.

Determinism, which is the whole point:

*   Nothing is compressed. Filters are the one place a "deterministic" generator usually
    is not: zlib output is stable in practice but is not contractually stable across
    versions or build flags. Uncompressed streams remove the question entirely, and the
    baseline is small enough that it costs nothing.
*   `/CreationDate`, `/ModDate`, `/ID` and the font subset tag are all caller-supplied
    constants or content-derived. No clock, no PRNG, no process id.
*   Objects are emitted in allocation order and every dictionary is built from a Python
    dict in a fixed literal order.

Numbers are formatted through one helper so the same value always prints the same way.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field

PDF_VERSION = b"%PDF-1.7"
# A binary comment after the header marks the file as containing binary data. Fixed bytes.
BINARY_MARKER = b"%\xe2\xe3\xcf\xd3"

# The 32-byte padding string from PDF 32000-1, Algorithm 2.
_PAD = bytes([
    0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00, 0x4E, 0x56,
    0xFF, 0xFA, 0x01, 0x08, 0x2E, 0x2E, 0x00, 0xB6, 0xD0, 0x68, 0x3E, 0x80,
    0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53, 0x69, 0x7A,
])


def num(value: float) -> str:
    """Format a PDF number identically for the same input, with no trailing zeros."""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def pdf_text_string(value: str) -> bytes:
    """Encode a text string as UTF-16BE with a BOM, hex-escaped, so any script survives."""
    return b"<" + (b"\xfe\xff" + value.encode("utf-16-be")).hex().upper().encode("ascii") + b">"


def pdf_literal(value: str) -> bytes:
    escaped = value.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return b"(" + escaped.encode("latin-1") + b")"


def rc4(key: bytes, data: bytes) -> bytes:
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) & 0xFF
        state[i], state[j] = state[j], state[i]
    out = bytearray(len(data))
    i = j = 0
    for n, byte in enumerate(data):
        i = (i + 1) & 0xFF
        j = (j + state[i]) & 0xFF
        state[i], state[j] = state[j], state[i]
        out[n] = byte ^ state[(state[i] + state[j]) & 0xFF]
    return bytes(out)


@dataclass
class StandardSecurity:
    """PDF standard security handler, revision 2 (V 1, 40-bit RC4).

    Deliberately the oldest and simplest revision: the negative fixture only has to be
    unambiguously encrypted and password-protected, and R2 is the variant every PDF
    parser in existence recognises. It is not offered as a security control.
    """

    user_password: str
    owner_password: str
    permissions: int = -3904  # print/copy denied; the usual "no rights" bit pattern
    key_length_bytes: int = 5

    _key: bytes = field(default=b"", init=False, repr=False)
    _o_entry: bytes = field(default=b"", init=False, repr=False)
    _u_entry: bytes = field(default=b"", init=False, repr=False)

    def _pad(self, password: str) -> bytes:
        raw = password.encode("latin-1")[:32]
        return raw + _PAD[: 32 - len(raw)]

    def prepare(self, doc_id: bytes) -> None:
        # Algorithm 3: the /O entry.
        owner_source = self.owner_password or self.user_password
        okey = hashlib.md5(self._pad(owner_source)).digest()[: self.key_length_bytes]
        self._o_entry = rc4(okey, self._pad(self.user_password))

        # Algorithm 2: the file encryption key.
        digest = hashlib.md5()
        digest.update(self._pad(self.user_password))
        digest.update(self._o_entry)
        digest.update(struct.pack("<i", self.permissions))
        digest.update(doc_id)
        self._key = digest.digest()[: self.key_length_bytes]

        # Algorithm 4: the /U entry for revision 2.
        self._u_entry = rc4(self._key, _PAD)

    def object_key(self, obj_num: int, gen_num: int) -> bytes:
        extended = (
            self._key
            + struct.pack("<i", obj_num)[:3]
            + struct.pack("<i", gen_num)[:2]
        )
        return hashlib.md5(extended).digest()[: min(self.key_length_bytes + 5, 16)]

    def encrypt(self, obj_num: int, gen_num: int, data: bytes) -> bytes:
        return rc4(self.object_key(obj_num, gen_num), data)

    def encrypt_dict(self) -> dict[str, object]:
        return {
            "Filter": Name("Standard"),
            "V": 1,
            "R": 2,
            "O": RawBytes(b"<" + self._o_entry.hex().upper().encode("ascii") + b">"),
            "U": RawBytes(b"<" + self._u_entry.hex().upper().encode("ascii") + b">"),
            "P": self.permissions,
        }


class Name(str):
    """A PDF name. A distinct type so a dict value is never ambiguous."""


class Ref(int):
    """An indirect reference to object number `self`."""


class RawBytes(bytes):
    """Pre-serialised PDF syntax, inserted verbatim."""


def serialize_value(value: object) -> bytes:
    if isinstance(value, RawBytes):
        return bytes(value)
    if isinstance(value, Name):
        return b"/" + str(value).encode("ascii")
    if isinstance(value, Ref):
        return f"{int(value)} 0 R".encode("ascii")
    if isinstance(value, bool):
        return b"true" if value else b"false"
    if isinstance(value, (int, float)):
        return num(value).encode("ascii")
    if isinstance(value, bytes):
        return value
    if isinstance(value, dict):
        parts = [b"<<"]
        for key, item in value.items():
            parts.append(b"/" + key.encode("ascii") + b" " + serialize_value(item))
        parts.append(b">>")
        return b" ".join(parts)
    if isinstance(value, (list, tuple)):
        return b"[ " + b" ".join(serialize_value(v) for v in value) + b" ]"
    raise TypeError(f"cannot serialize {type(value).__name__} into PDF syntax")


@dataclass
class _Object:
    payload: object = None
    stream: bytes | None = None


class Pdf:
    """An object graph that serialises to bytes in allocation order."""

    def __init__(self) -> None:
        self._objects: list[_Object | None] = []

    def reserve(self) -> Ref:
        self._objects.append(None)
        return Ref(len(self._objects))

    def put(self, ref: Ref, payload: object, stream: bytes | None = None) -> Ref:
        self._objects[int(ref) - 1] = _Object(payload=payload, stream=stream)
        return ref

    def add(self, payload: object, stream: bytes | None = None) -> Ref:
        return self.put(self.reserve(), payload, stream)

    def add_stream(self, extra: dict[str, object], data: bytes) -> Ref:
        payload = dict(extra)
        payload["Length"] = len(data)
        return self.add(payload, stream=data)

    def serialize(
        self,
        root: Ref,
        info: dict[str, object],
        doc_id: bytes,
        security: StandardSecurity | None = None,
    ) -> bytes:
        missing = [i + 1 for i, obj in enumerate(self._objects) if obj is None]
        if missing:
            raise ValueError(f"reserved but never written: objects {missing}")

        info_ref = self.add(info)
        encrypt_ref: Ref | None = None
        if security is not None:
            security.prepare(doc_id)
            # The /Encrypt dictionary itself is never encrypted.
            encrypt_ref = self.add(security.encrypt_dict())

        out = bytearray()
        out += PDF_VERSION + b"\n" + BINARY_MARKER + b"\n"
        offsets: list[int] = []
        for index, obj in enumerate(self._objects):
            assert obj is not None
            obj_num = index + 1
            offsets.append(len(out))
            body = obj.payload
            stream = obj.stream
            if security is not None and encrypt_ref is not None and obj_num != int(encrypt_ref):
                if stream is not None:
                    stream = security.encrypt(obj_num, 0, stream)
                    if isinstance(body, dict):
                        body = dict(body)
                        body["Length"] = len(stream)
                body = _encrypt_strings(body, security, obj_num)
            out += f"{obj_num} 0 obj\n".encode("ascii")
            out += serialize_value(body)
            if stream is not None:
                out += b"\nstream\n" + stream + b"\nendstream"
            out += b"\nendobj\n"

        xref_at = len(out)
        count = len(self._objects) + 1
        out += f"xref\n0 {count}\n".encode("ascii")
        out += b"0000000000 65535 f \n"
        for offset in offsets:
            out += f"{offset:010d} 00000 n \n".encode("ascii")

        trailer: dict[str, object] = {
            "Size": count,
            "Root": root,
            "Info": info_ref,
            "ID": [
                RawBytes(b"<" + doc_id.hex().upper().encode("ascii") + b">"),
                RawBytes(b"<" + doc_id.hex().upper().encode("ascii") + b">"),
            ],
        }
        if encrypt_ref is not None:
            trailer["Encrypt"] = encrypt_ref
        out += b"trailer\n" + serialize_value(trailer) + b"\n"
        out += f"startxref\n{xref_at}\n".encode("ascii") + b"%%EOF\n"
        return bytes(out)


def _encrypt_strings(value: object, security: StandardSecurity, obj_num: int) -> object:
    """Encrypt every literal/hex string in an object body, as the handler requires."""
    # EncryptableString subclasses RawBytes, so it has to be tested first.
    if isinstance(value, EncryptableString):
        return RawBytes(
            b"<"
            + security.encrypt(obj_num, 0, value.raw).hex().upper().encode("ascii")
            + b">"
        )
    if isinstance(value, (RawBytes, Name, Ref)):
        return value
    if isinstance(value, dict):
        return {k: _encrypt_strings(v, security, obj_num) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encrypt_strings(v, security, obj_num) for v in value]
    return value


class EncryptableString(RawBytes):
    """A string that must be encrypted when a security handler is active.

    Carries both the plain bytes and the serialised plaintext form, so the same object
    graph works with and without encryption.
    """

    raw: bytes

    def __new__(cls, text: str) -> "EncryptableString":
        raw = b"\xfe\xff" + text.encode("utf-16-be")
        obj = super().__new__(cls, b"<" + raw.hex().upper().encode("ascii") + b">")
        obj.raw = raw
        return obj


# --------------------------------------------------------------------------------------
# Embedded CIDFontType2
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EmbeddedFont:
    """An embedded font ready for the writer: glyph ids, widths and the font program."""

    font_bytes: bytes
    units_per_em: int
    char_to_gid: dict[str, int]
    gid_advance: dict[int, int]
    ascent: int
    descent: int
    cap_height: int
    bbox: tuple[int, int, int, int]
    base_name: str = "ARCorpusSans"

    def subset_tag(self) -> str:
        """A deterministic six-uppercase-letter subset tag derived from the font bytes."""
        digest = hashlib.sha256(self.font_bytes).digest()
        return "".join(chr(ord("A") + (b % 26)) for b in digest[:6])

    def scaled(self, font_units: int) -> int:
        return int(round(font_units * 1000.0 / self.units_per_em))

    def encode(self, text: str) -> bytes:
        """Encode text as Identity-H: two big-endian bytes of glyph id per character."""
        out = bytearray()
        for char in text:
            gid = self.char_to_gid.get(char)
            if gid is None:
                raise KeyError(
                    f"character {char!r} (U+{ord(char):04X}) is not in the font subset; "
                    "rerun tools/fixtures/build_font_subset.py"
                )
            out += struct.pack(">H", gid)
        return bytes(out)

    def text_width(self, text: str, size: float) -> float:
        total = 0
        for char in text:
            gid = self.char_to_gid[char]
            total += self.gid_advance[gid]
        return total * size / self.units_per_em


def _to_unicode_cmap(font: EmbeddedFont) -> bytes:
    """Build the `ToUnicode` CMap. This is what makes the text layer extractable."""
    # Identity-H addresses glyphs, so two characters sharing one glyph would be
    # indistinguishable in the text layer and `ToUnicode` could only name one of them.
    # That is silent corruption of the acceptance oracle, so it is a hard error.
    by_gid: dict[int, str] = {}
    for char, gid in sorted(font.char_to_gid.items()):
        if gid in by_gid and by_gid[gid] != char:
            raise ValueError(
                f"glyph {gid} is shared by U+{ord(by_gid[gid]):04X} and "
                f"U+{ord(char):04X}; the text layer could not distinguish them"
            )
        by_gid[gid] = char
    pairs = sorted(by_gid.items())
    header = (
        "/CIDInit /ProcSet findresource begin\n"
        "12 dict begin\n"
        "begincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def\n"
        "/CMapType 2 def\n"
        "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
    )
    body = ""
    # `bfchar` blocks are limited to 100 entries each by the CMap specification.
    for start in range(0, len(pairs), 100):
        chunk = pairs[start:start + 100]
        body += f"{len(chunk)} beginbfchar\n"
        for gid, char in chunk:
            unicode_hex = char.encode("utf-16-be").hex().upper()
            body += f"<{gid:04X}> <{unicode_hex}>\n"
        body += "endbfchar\n"
    footer = "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
    return (header + body + footer).encode("ascii")


def _widths_array(font: EmbeddedFont) -> list[object]:
    """The `/W` array, one contiguous run per block of consecutive glyph ids."""
    gids = sorted(font.gid_advance)
    out: list[object] = []
    run_start: int | None = None
    run: list[object] = []
    for gid in gids:
        if run_start is not None and gid == run_start + len(run):
            run.append(font.scaled(font.gid_advance[gid]))
            continue
        if run_start is not None:
            out.extend([run_start, run])
        run_start = gid
        run = [font.scaled(font.gid_advance[gid])]
    if run_start is not None:
        out.extend([run_start, run])
    return out


def add_font(pdf: Pdf, font: EmbeddedFont) -> Ref:
    """Add the Type0 font family and return the reference to put in `/Resources`."""
    base_name = f"{font.subset_tag()}+{font.base_name}"

    file_ref = pdf.add_stream({"Length1": len(font.font_bytes)}, font.font_bytes)
    to_unicode = _to_unicode_cmap(font)
    to_unicode_ref = pdf.add_stream({}, to_unicode)

    descriptor_ref = pdf.add({
        "Type": Name("FontDescriptor"),
        "FontName": Name(base_name),
        "Flags": 32,  # nonsymbolic
        "FontBBox": [
            font.scaled(font.bbox[0]), font.scaled(font.bbox[1]),
            font.scaled(font.bbox[2]), font.scaled(font.bbox[3]),
        ],
        "ItalicAngle": 0,
        "Ascent": font.scaled(font.ascent),
        "Descent": font.scaled(font.descent),
        "CapHeight": font.scaled(font.cap_height),
        "StemV": 80,
        "FontFile2": file_ref,
    })

    descendant_ref = pdf.add({
        "Type": Name("Font"),
        "Subtype": Name("CIDFontType2"),
        "BaseFont": Name(base_name),
        "CIDSystemInfo": {
            "Registry": pdf_literal_value("Adobe"),
            "Ordering": pdf_literal_value("Identity"),
            "Supplement": 0,
        },
        "FontDescriptor": descriptor_ref,
        "DW": 1000,
        "W": _widths_array(font),
        "CIDToGIDMap": Name("Identity"),
    })

    return pdf.add({
        "Type": Name("Font"),
        "Subtype": Name("Type0"),
        "BaseFont": Name(base_name),
        "Encoding": Name("Identity-H"),
        "DescendantFonts": [descendant_ref],
        "ToUnicode": to_unicode_ref,
    })


def pdf_literal_value(text: str) -> RawBytes:
    return RawBytes(pdf_literal(text))


# --------------------------------------------------------------------------------------
# Content streams
# --------------------------------------------------------------------------------------


def show_text(font: EmbeddedFont, resource_name: str, text: str,
              size: float, x: float, y: float) -> str:
    """One line of text as one text-showing operator at one absolute position.

    Keeping a line to a single `Tj` is what lets an extractor reproduce it verbatim
    instead of reassembling it from positioned fragments.
    """
    hex_glyphs = font.encode(text).hex().upper()
    return (
        f"BT /{resource_name} {num(size)} Tf "
        f"1 0 0 1 {num(x)} {num(y)} Tm "
        f"<{hex_glyphs}> Tj ET\n"
    )


# --------------------------------------------------------------------------------------
# CMP-FIXTURES-01 extensions
# --------------------------------------------------------------------------------------
#
# Everything from here down is additive and off by default. No function above this line was
# changed, and the AR corpus builders call none of what follows, so their output bytes cannot
# move (`tests/contract/fixtures_ar` and `build_ar_corpus.py --check` prove it). The comparison
# corpus (`tools/fixtures/comparison`) is the only caller. What it adds:
#
# *   a page dictionary with `/CropBox`, `/Rotate` and `/Annots`;
# *   a text annotation and a square annotation, each with an appearance stream so every
#     viewer draws the same thing;
# *   one optional-content group (`/OCG`) and the marked-content operators that use it;
# *   dashed and solid line, rectangle and circle operators;
# *   two hatch fills: a tiling pattern (one object) and clipped parallel lines (many);
# *   text drawn as paths instead of glyphs: the outline of each character stroked, which is
#     what a plotter export of a CAD font looks like to a PDF reader (no text layer at all).
#
# Numbers go through `_n`, which takes the digit count as a parameter, so a second "producer"
# can print the same coordinates at another precision.


def _n(value: float, digits: int = 3) -> str:
    """A PDF number with at most `digits` decimals and no trailing zeros."""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _rgb(rgb: tuple[float, float, float], *, stroke: bool, digits: int = 3) -> str:
    r, g, b = rgb
    return f"{_n(r, digits)} {_n(g, digits)} {_n(b, digits)} {'RG' if stroke else 'rg'}"


def page_dictionary(
    parent: Ref,
    media_box: list[float],
    resources: dict[str, object],
    contents: Ref,
    *,
    crop_box: list[float] | None = None,
    rotate: int | None = None,
    annots: list[Ref] | None = None,
) -> dict[str, object]:
    """A `/Page` dictionary. With every option left out it is the dictionary the AR builders write."""
    page: dict[str, object] = {
        "Type": Name("Page"),
        "Parent": parent,
        "MediaBox": list(media_box),
    }
    if crop_box is not None:
        page["CropBox"] = list(crop_box)
    if rotate is not None:
        if rotate % 90 != 0:
            raise ValueError("/Rotate is a multiple of 90")
        page["Rotate"] = rotate
    page["Resources"] = resources
    page["Contents"] = contents
    if annots:
        page["Annots"] = list(annots)
    return page


def _appearance(pdf: Pdf, width: float, height: float, content: str) -> Ref:
    return pdf.add_stream(
        {
            "Type": Name("XObject"),
            "Subtype": Name("Form"),
            "BBox": [0, 0, width, height],
            "Resources": {},
        },
        content.encode("ascii"),
    )


def add_text_annotation(
    pdf: Pdf,
    rect: tuple[float, float, float, float],
    contents: str,
    *,
    author: str,
    modified: str,
    color: tuple[float, float, float] = (1.0, 0.9, 0.2),
) -> Ref:
    """A `/Text` (sticky note) annotation with a drawn icon. `modified` is a PDF date string."""
    x0, y0, x1, y1 = rect
    width, height = x1 - x0, y1 - y0
    icon = (
        f"q {_rgb(color, stroke=False)} 0 0 {_n(width)} {_n(height)} re f "
        f"0 0 0 RG 0.8 w 0.4 0.4 {_n(width - 0.8)} {_n(height - 0.8)} re S "
        f"{_n(width * 0.2)} {_n(height * 0.65)} m {_n(width * 0.8)} {_n(height * 0.65)} l S "
        f"{_n(width * 0.2)} {_n(height * 0.4)} m {_n(width * 0.8)} {_n(height * 0.4)} l S Q\n"
    )
    return pdf.add({
        "Type": Name("Annot"),
        "Subtype": Name("Text"),
        "Rect": [x0, y0, x1, y1],
        "Contents": RawBytes(pdf_text_string(contents)),
        "T": RawBytes(pdf_text_string(author)),
        "M": RawBytes(pdf_literal(modified)),
        "Name": Name("Comment"),
        "C": list(color),
        "F": 4,
        "Open": False,
        "AP": {"N": _appearance(pdf, width, height, icon)},
    })


def add_square_annotation(
    pdf: Pdf,
    rect: tuple[float, float, float, float],
    *,
    color: tuple[float, float, float],
    border_width: float = 1.5,
    contents: str | None = None,
    author: str | None = None,
    modified: str | None = None,
) -> Ref:
    """A `/Square` annotation: an outlined rectangle drawn by its own appearance stream."""
    x0, y0, x1, y1 = rect
    width, height = x1 - x0, y1 - y0
    half = border_width / 2.0
    body = (
        f"q {_rgb(color, stroke=True)} {_n(border_width)} w "
        f"{_n(half)} {_n(half)} {_n(width - border_width)} {_n(height - border_width)} re S Q\n"
    )
    annotation: dict[str, object] = {
        "Type": Name("Annot"),
        "Subtype": Name("Square"),
        "Rect": [x0, y0, x1, y1],
    }
    if contents is not None:
        annotation["Contents"] = RawBytes(pdf_text_string(contents))
    if author is not None:
        annotation["T"] = RawBytes(pdf_text_string(author))
    if modified is not None:
        annotation["M"] = RawBytes(pdf_literal(modified))
    annotation["C"] = list(color)
    annotation["BS"] = {"W": border_width, "S": Name("S")}
    annotation["F"] = 4
    annotation["AP"] = {"N": _appearance(pdf, width, height, body)}
    return pdf.add(annotation)


def add_ocg(pdf: Pdf, name: str) -> Ref:
    """One optional-content group (a CAD "layer")."""
    return pdf.add({"Type": Name("OCG"), "Name": RawBytes(pdf_text_string(name))})


def ocg_properties(layers: list[Ref], *, hidden: tuple[Ref, ...] = ()) -> dict[str, object]:
    """The catalog's `/OCProperties` value. A layer in `hidden` is off by default."""
    default: dict[str, object] = {
        "Order": list(layers),
        "ON": [layer for layer in layers if layer not in hidden],
    }
    if hidden:
        default["OFF"] = list(hidden)
    return {"OCGs": list(layers), "D": default}


def layer_begin(tag: str) -> str:
    """Start marked content drawn on the group the page's `/Properties /<tag>` names."""
    return f"/OC /{tag} BDC\n"


def layer_end() -> str:
    return "EMC\n"


def _dash(dash: tuple[float, ...] | None, digits: int) -> str:
    if not dash:
        return ""
    return "[" + " ".join(_n(d, digits) for d in dash) + "] 0 d "


def stroke_line_op(
    x1: float, y1: float, x2: float, y2: float, *, width: float,
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0),
    dash: tuple[float, ...] | None = None, digits: int = 3,
) -> str:
    """One line, solid or dashed, in its own graphics state."""
    return (
        f"q {_n(width, digits)} w {_rgb(rgb, stroke=True, digits=digits)} {_dash(dash, digits)}"
        f"{_n(x1, digits)} {_n(y1, digits)} m {_n(x2, digits)} {_n(y2, digits)} l S Q\n"
    )


def stroke_rect_op(
    x: float, y: float, w: float, h: float, *, width: float,
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0),
    dash: tuple[float, ...] | None = None,
    fill: tuple[float, float, float] | None = None, digits: int = 3,
) -> str:
    """A rectangle outline, optionally dashed and optionally filled."""
    paint = "B" if fill is not None else "S"
    fill_part = _rgb(fill, stroke=False, digits=digits) + " " if fill is not None else ""
    return (
        f"q {_n(width, digits)} w {_rgb(rgb, stroke=True, digits=digits)} {fill_part}"
        f"{_dash(dash, digits)}{_n(x, digits)} {_n(y, digits)} {_n(w, digits)} {_n(h, digits)} re {paint} Q\n"
    )


def stroke_circle_op(
    cx: float, cy: float, r: float, *, width: float,
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0), digits: int = 3,
) -> str:
    """A circle as four cubic Béziers (kappa = 0.5523)."""
    k = 0.5522847498 * r
    points = [
        (cx + r, cy),
        (cx + r, cy + k, cx + k, cy + r, cx, cy + r),
        (cx - k, cy + r, cx - r, cy + k, cx - r, cy),
        (cx - r, cy - k, cx - k, cy - r, cx, cy - r),
        (cx + k, cy - r, cx + r, cy - k, cx + r, cy),
    ]
    parts = [f"{_n(points[0][0], digits)} {_n(points[0][1], digits)} m"]
    for curve in points[1:]:
        parts.append(" ".join(_n(v, digits) for v in curve) + " c")
    return (
        f"q {_n(width, digits)} w {_rgb(rgb, stroke=True, digits=digits)} "
        + " ".join(parts) + " h S Q\n"
    )


def add_hatch_pattern(
    pdf: Pdf, *, spacing: float, width: float, rgb: tuple[float, float, float],
) -> Ref:
    """A coloured tiling pattern: 45-degree parallel lines, `spacing` points apart."""
    s = _n(spacing)
    body = f"{_rgb(rgb, stroke=True)} {_n(width)} w 0 0 m {s} {s} l S\n"
    return pdf.add_stream(
        {
            "Type": Name("Pattern"),
            "PatternType": 1,
            "PaintType": 1,
            "TilingType": 1,
            "BBox": [0, 0, spacing, spacing],
            "XStep": spacing,
            "YStep": spacing,
            "Resources": {},
        },
        body.encode("ascii"),
    )


def pattern_fill_op(
    pattern_name: str, x: float, y: float, w: float, h: float, *, digits: int = 3,
) -> str:
    """Fill a rectangle with a tiling pattern in the page's `/Pattern` resources."""
    return (
        f"q /Pattern cs /{pattern_name} scn "
        f"{_n(x, digits)} {_n(y, digits)} {_n(w, digits)} {_n(h, digits)} re f Q\n"
    )


def hatch_segments(
    x: float, y: float, w: float, h: float, *, spacing: float,
) -> list[tuple[float, float, float, float]]:
    """Parallel 45-degree lines across a rectangle as (x0, y0, x1, y1), clipped exactly to it.

    The lines run from the left or bottom edge to the right or top edge, `spacing` apart
    along the x axis, in a fixed order (bottom-right corner first).
    """
    out: list[tuple[float, float, float, float]] = []
    offset = -h
    while offset < w:
        x0, y0 = x + max(offset, 0.0), y + max(-offset, 0.0)
        run = min(w - max(offset, 0.0), h - max(-offset, 0.0))
        if run > 0:
            out.append((x0, y0, x0 + run, y0 + run))
        offset += spacing
    return out


def hatch_lines(
    x: float, y: float, w: float, h: float, *, spacing: float, width: float,
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0), digits: int = 3,
) -> list[str]:
    """`hatch_segments` as finished strokes, one `q ... Q` each, so a caller can reorder them."""
    return [
        f"q {_n(width, digits)} w {_rgb(rgb, stroke=True, digits=digits)} "
        f"{_n(x0, digits)} {_n(y0, digits)} m {_n(x1, digits)} {_n(y1, digits)} l S Q\n"
        for x0, y0, x1, y1 in hatch_segments(x, y, w, h, spacing=spacing)
    ]


def clip_rect_op(x: float, y: float, w: float, h: float, *, digits: int = 3) -> str:
    """Begin a clip to a rectangle; the caller closes it with `Q`."""
    return f"q {_n(x, digits)} {_n(y, digits)} {_n(w, digits)} {_n(h, digits)} re W n\n"


def stroke_text_op(
    outlines: object, text: str, size: float, x: float, y: float, *, width: float,
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0), digits: int = 3, bare: bool = False,
) -> str:
    """Text as paths: every character's outline stroked, one path object per character.

    `outlines` is any object with `units_per_em`, `advance(char) -> font units` and
    `contours(char) -> list of contours`, each contour a list of segments `("m", x, y)`,
    `("l", x, y)`, `("c", x1, y1, x2, y2, x3, y3)` or `("h",)` in font units
    (`tools/fixtures/comparison/outlines.py`). The result contains no text-showing operator.
    With `bare` each character is just its path and `S`: the caller has set the line width,
    colour, join and cap, which is how a producer that groups strokes by style writes them.
    """
    scale = size / outlines.units_per_em  # type: ignore[attr-defined]
    pen = x
    out: list[str] = []
    for char in text:
        contours = outlines.contours(char)  # type: ignore[attr-defined]
        if contours:
            body: list[str] = []
            for contour in contours:
                for seg in contour:
                    kind = seg[0]
                    if kind == "h":
                        body.append("h")
                        continue
                    coords: list[str] = []
                    for index in range(1, len(seg), 2):
                        coords.append(_n(pen + seg[index] * scale, digits))
                        coords.append(_n(y + seg[index + 1] * scale, digits))
                    body.append(" ".join(coords) + " " + kind)
            if bare:
                out.append(" ".join(body) + " S\n")
            else:
                out.append(
                    f"q {_n(width, digits)} w {_rgb(rgb, stroke=True, digits=digits)} 1 j 1 J "
                    + " ".join(body) + " S Q\n"
                )
        pen += outlines.advance(char) * scale  # type: ignore[attr-defined]
    return "".join(out)
