"""A pure-standard-library PDF text-layer extractor.

This exists to prove the acceptance oracle rather than assume it. Every seeded quotation
in the manifest has to be recoverable character-for-character from the *file bytes*, so
something has to read those bytes back independently of the code that wrote them. This
module parses the cross-reference table, the object graph, the content streams and the
`ToUnicode` CMaps from scratch; it shares no data structure with `pdfwrite`, so a writer
bug cannot cancel out against a reader bug.

It is not a general-purpose extractor. It handles what the corpus contains: classic
cross-reference tables, uncompressed and `FlateDecode` streams, and simple/Type0 fonts
with a `ToUnicode` CMap. Anything else raises rather than guessing, because a silent
partial extraction is exactly the failure this module is meant to catch.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field

WHITESPACE = b"\x00\t\n\x0c\r "
DELIMITERS = b"()<>[]{}/%"


class PdfParseError(RuntimeError):
    """The file is not a PDF this module can read."""


class EncryptedPdfError(PdfParseError):
    """The file declares an /Encrypt dictionary; its content cannot be read."""


class Name(str):
    """A PDF name, kept distinct from a string so `/Foo` never equals `(Foo)`."""


@dataclass(frozen=True)
class Ref:
    num: int
    gen: int = 0


@dataclass
class Stream:
    dictionary: dict
    raw: bytes

    def data(self, doc: "Document") -> bytes:
        filters = doc.resolve(self.dictionary.get("Filter"))
        if filters is None:
            return self.raw
        if isinstance(filters, Name):
            filters = [filters]
        out = self.raw
        for filt in filters:
            if str(filt) == "FlateDecode":
                out = zlib.decompress(out)
            else:
                raise PdfParseError(f"unsupported stream filter /{filt}")
        return out


class _Lexer:
    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    def skip_ws(self) -> None:
        data = self.data
        while self.pos < len(data):
            byte = data[self.pos]
            if byte in WHITESPACE:
                self.pos += 1
            elif byte == 0x25:  # '%' comment to end of line
                end = data.find(b"\n", self.pos)
                self.pos = len(data) if end < 0 else end + 1
            else:
                return

    def read_token(self) -> bytes:
        self.skip_ws()
        data = self.data
        if self.pos >= len(data):
            return b""
        start = self.pos
        byte = data[start]
        if byte in b"<>":
            if data[start:start + 2] in (b"<<", b">>"):
                self.pos += 2
                return data[start:start + 2]
            self.pos += 1
            return data[start:start + 1]
        if byte in DELIMITERS:
            self.pos += 1
            return data[start:start + 1]
        while self.pos < len(data) and data[self.pos] not in WHITESPACE \
                and data[self.pos] not in DELIMITERS:
            self.pos += 1
        return data[start:self.pos]

    def peek_token(self) -> bytes:
        saved = self.pos
        token = self.read_token()
        self.pos = saved
        return token

    def _read_literal_string(self) -> bytes:
        out = bytearray()
        depth = 1
        data = self.data
        while self.pos < len(data):
            byte = data[self.pos]
            self.pos += 1
            if byte == 0x5C:  # backslash
                if self.pos >= len(data):
                    break
                nxt = data[self.pos]
                self.pos += 1
                simple = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}
                if nxt in simple:
                    out.append(simple[nxt])
                elif nxt in b"()\\":
                    out.append(nxt)
                elif 0x30 <= nxt <= 0x37:  # octal
                    digits = chr(nxt)
                    while len(digits) < 3 and self.pos < len(data) \
                            and 0x30 <= data[self.pos] <= 0x37:
                        digits += chr(data[self.pos])
                        self.pos += 1
                    out.append(int(digits, 8) & 0xFF)
                elif nxt == 0x0A:
                    pass  # line continuation
                else:
                    out.append(nxt)
            elif byte == 0x28:
                depth += 1
                out.append(byte)
            elif byte == 0x29:
                depth -= 1
                if depth == 0:
                    return bytes(out)
                out.append(byte)
            else:
                out.append(byte)
        raise PdfParseError("unterminated literal string")

    def _read_hex_string(self) -> bytes:
        end = self.data.find(b">", self.pos)
        if end < 0:
            raise PdfParseError("unterminated hex string")
        digits = re.sub(rb"[^0-9A-Fa-f]", b"", self.data[self.pos:end])
        self.pos = end + 1
        if len(digits) % 2:
            digits += b"0"
        return bytes.fromhex(digits.decode("ascii"))

    def parse_object(self) -> object:
        self.skip_ws()
        data = self.data
        if self.pos >= len(data):
            raise PdfParseError("unexpected end of file")
        byte = data[self.pos]

        if byte == 0x28:  # (
            self.pos += 1
            return self._read_literal_string()
        if byte == 0x3C and data[self.pos:self.pos + 2] != b"<<":  # <
            self.pos += 1
            return self._read_hex_string()

        token = self.read_token()
        if token == b"<<":
            result: dict[str, object] = {}
            while True:
                self.skip_ws()
                nxt = self.peek_token()
                if nxt == b">>":
                    self.read_token()
                    break
                if nxt == b"":
                    raise PdfParseError("unterminated dictionary")
                key = self.parse_object()
                if not isinstance(key, Name):
                    raise PdfParseError(f"dictionary key is not a name: {key!r}")
                result[str(key)] = self.parse_object()
            return result
        if token == b"[":
            items: list[object] = []
            while True:
                self.skip_ws()
                nxt = self.peek_token()
                if nxt == b"]":
                    self.read_token()
                    break
                if nxt == b"":
                    raise PdfParseError("unterminated array")
                items.append(self.parse_object())
            return items
        if token == b"/":
            start = self.pos
            while self.pos < len(data) and data[self.pos] not in WHITESPACE \
                    and data[self.pos] not in DELIMITERS:
                self.pos += 1
            raw = data[start:self.pos].decode("latin-1")
            # `#xx` escapes inside names.
            return Name(re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), raw))
        if token == b"true":
            return True
        if token == b"false":
            return False
        if token == b"null":
            return None

        if re.fullmatch(rb"[+-]?\d+", token):
            saved = self.pos
            second = self.read_token()
            if re.fullmatch(rb"\d+", second):
                third = self.read_token()
                if third == b"R":
                    return Ref(int(token), int(second))
            self.pos = saved
            return int(token)
        if re.fullmatch(rb"[+-]?(\d*\.\d*|\d+)", token):
            return float(token)
        raise PdfParseError(f"unexpected token {token!r} at offset {self.pos}")


@dataclass
class Document:
    data: bytes
    offsets: dict[int, int] = field(default_factory=dict)
    trailer: dict = field(default_factory=dict)
    _cache: dict[int, object] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, data: bytes) -> "Document":
        doc = cls(data=data)
        doc._read_xref_chain()
        if "Encrypt" in doc.trailer:
            raise EncryptedPdfError(
                "the trailer declares /Encrypt; this document is encrypted"
            )
        return doc

    def _read_xref_chain(self) -> None:
        tail = self.data[-2048:]
        match = None
        for match in re.finditer(rb"startxref\s+(\d+)", tail):
            pass
        if match is None:
            raise PdfParseError("no startxref found")
        seen: set[int] = set()
        offset = int(match.group(1))
        first = True
        while offset not in seen:
            seen.add(offset)
            trailer = self._read_xref_section(offset)
            if first:
                self.trailer = dict(trailer)
                first = False
            else:
                for key, value in trailer.items():
                    self.trailer.setdefault(key, value)
            prev = trailer.get("Prev")
            if not isinstance(prev, int):
                break
            offset = prev

    def _read_xref_section(self, offset: int) -> dict:
        lexer = _Lexer(self.data, offset)
        token = lexer.read_token()
        if token != b"xref":
            raise PdfParseError(
                "only classic cross-reference tables are supported "
                f"(found {token!r} at {offset})"
            )
        while True:
            lexer.skip_ws()
            nxt = lexer.peek_token()
            if nxt == b"trailer":
                lexer.read_token()
                trailer = lexer.parse_object()
                if not isinstance(trailer, dict):
                    raise PdfParseError("trailer is not a dictionary")
                return trailer
            start = lexer.parse_object()
            count = lexer.parse_object()
            if not isinstance(start, int) or not isinstance(count, int):
                raise PdfParseError("malformed cross-reference subsection header")
            lexer.skip_ws()
            for i in range(count):
                entry = self.data[lexer.pos:lexer.pos + 20]
                if len(entry) < 18:
                    raise PdfParseError("truncated cross-reference entry")
                obj_offset = int(entry[0:10])
                kind = entry[17:18]
                # Later sections win, so an already-known object is not overwritten.
                if kind == b"n" and (start + i) not in self.offsets:
                    self.offsets[start + i] = obj_offset
                lexer.pos += 20 if entry[19:20] in (b"\n", b"\r") else 18

    def get(self, num: int) -> object:
        if num in self._cache:
            return self._cache[num]
        if num not in self.offsets:
            raise PdfParseError(f"object {num} is not in the cross-reference table")
        lexer = _Lexer(self.data, self.offsets[num])
        got_num = lexer.parse_object()
        lexer.parse_object()  # generation
        if lexer.read_token() != b"obj":
            raise PdfParseError(f"object {num} does not begin with 'obj'")
        if got_num != num:
            raise PdfParseError(f"cross-reference points at object {got_num}, wanted {num}")
        value = lexer.parse_object()
        if lexer.peek_token() == b"stream":
            lexer.read_token()
            if self.data[lexer.pos:lexer.pos + 2] == b"\r\n":
                lexer.pos += 2
            elif self.data[lexer.pos:lexer.pos + 1] in (b"\n", b"\r"):
                lexer.pos += 1
            length = self.resolve(value.get("Length"))
            if not isinstance(length, int):
                raise PdfParseError(f"object {num} has no usable /Length")
            value = Stream(dictionary=value, raw=self.data[lexer.pos:lexer.pos + length])
        self._cache[num] = value
        return value

    def resolve(self, value: object) -> object:
        seen = 0
        while isinstance(value, Ref):
            value = self.get(value.num)
            seen += 1
            if seen > 32:
                raise PdfParseError("reference chain too deep")
        return value

    def pages(self) -> list[dict]:
        root = self.resolve(self.trailer.get("Root"))
        if not isinstance(root, dict):
            raise PdfParseError("no document catalogue")
        tree = self.resolve(root.get("Pages"))
        if not isinstance(tree, dict):
            raise PdfParseError("no page tree")
        out: list[dict] = []
        self._walk(tree, {}, out)
        return out

    def _walk(self, node: dict, inherited: dict, out: list[dict]) -> None:
        merged = dict(inherited)
        for key in ("Resources", "MediaBox", "Rotate", "CropBox"):
            if key in node:
                merged[key] = node[key]
        kind = node.get("Type")
        kids = self.resolve(node.get("Kids"))
        if kind == "Page" or (kids is None and "Contents" in node):
            page = dict(node)
            for key, value in merged.items():
                page.setdefault(key, value)
            out.append(page)
            return
        if not isinstance(kids, list):
            raise PdfParseError("page tree node has neither /Kids nor page content")
        for kid in kids:
            resolved = self.resolve(kid)
            if not isinstance(resolved, dict):
                raise PdfParseError("page tree kid is not a dictionary")
            self._walk(resolved, merged, out)


def _parse_to_unicode(cmap: bytes) -> dict[int, str]:
    """Read `bfchar` and `bfrange` sections into code -> text."""
    text = cmap.decode("latin-1")
    mapping: dict[int, str] = {}

    def decode_utf16(hex_digits: str) -> str:
        return bytes.fromhex(hex_digits).decode("utf-16-be")

    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            mapping[int(src, 16)] = decode_utf16(dst)

    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for lo, hi, dst in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            start, end, base = int(lo, 16), int(hi, 16), bytes.fromhex(dst)
            for i in range(end - start + 1):
                shifted = bytearray(base)
                shifted[-2:] = ((int.from_bytes(base[-2:], "big") + i) & 0xFFFF).to_bytes(2, "big")
                mapping[start + i] = bytes(shifted).decode("utf-16-be")
        for lo, hi, arr in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", block, re.S
        ):
            start = int(lo, 16)
            for i, dst in enumerate(re.findall(r"<([0-9A-Fa-f]+)>", arr)):
                mapping[start + i] = decode_utf16(dst)
    return mapping


@dataclass
class _Font:
    two_byte: bool
    to_unicode: dict[int, str]

    def decode(self, raw: bytes) -> str:
        out = []
        step = 2 if self.two_byte else 1
        for i in range(0, len(raw) - (len(raw) % step), step):
            code = int.from_bytes(raw[i:i + step], "big")
            if code not in self.to_unicode:
                raise PdfParseError(
                    f"code {code:#06x} has no ToUnicode mapping; the text layer is "
                    "not fully recoverable"
                )
            out.append(self.to_unicode[code])
        return "".join(out)


def _load_fonts(doc: Document, page: dict) -> dict[str, _Font]:
    resources = doc.resolve(page.get("Resources"))
    if not isinstance(resources, dict):
        return {}
    fonts = doc.resolve(resources.get("Font"))
    if not isinstance(fonts, dict):
        return {}
    out: dict[str, _Font] = {}
    for name, ref in fonts.items():
        font = doc.resolve(ref)
        if not isinstance(font, dict):
            continue
        encoding = doc.resolve(font.get("Encoding"))
        two_byte = str(font.get("Subtype", "")) == "Type0" or (
            isinstance(encoding, Name) and "Identity" in str(encoding)
        )
        to_unicode_obj = doc.resolve(font.get("ToUnicode"))
        if not isinstance(to_unicode_obj, Stream):
            raise PdfParseError(
                f"font /{name} has no /ToUnicode CMap; its text is not reliably "
                "extractable"
            )
        out[str(name)] = _Font(
            two_byte=two_byte, to_unicode=_parse_to_unicode(to_unicode_obj.data(doc))
        )
    return out


_CONTENT_OPERATOR = re.compile(rb"[A-Za-z'\"][A-Za-z0-9*'\"]*")


def _tokenize_content(stream: bytes) -> list[tuple[str, list[object]]]:
    """Split a content stream into (operator, operands) pairs."""
    lexer = _Lexer(stream)
    operands: list[object] = []
    out: list[tuple[str, list[object]]] = []
    while True:
        lexer.skip_ws()
        if lexer.pos >= len(stream):
            break
        byte = stream[lexer.pos]
        if byte in b"(<[/+-." or byte.to_bytes(1, "big").isdigit():
            if byte == 0x3C and stream[lexer.pos:lexer.pos + 2] == b"<<":
                operands.append(lexer.parse_object())
            else:
                operands.append(lexer.parse_object())
            continue
        token = lexer.read_token()
        if not token:
            break
        if token in (b"true", b"false", b"null"):
            operands.append({b"true": True, b"false": False, b"null": None}[token])
            continue
        if token == b"BI":
            # Inline image: skip to EI. The corpus uses XObjects, but be safe.
            end = stream.find(b"EI", lexer.pos)
            lexer.pos = len(stream) if end < 0 else end + 2
            operands = []
            continue
        if _CONTENT_OPERATOR.fullmatch(token):
            out.append((token.decode("latin-1"), operands))
            operands = []
        else:
            operands = []
    return out


@dataclass
class TextRun:
    x: float
    y: float
    text: str


def page_runs(doc: Document, page: dict) -> list[TextRun]:
    """Return every text-showing operation on a page with its device position."""
    fonts = _load_fonts(doc, page)
    contents = doc.resolve(page.get("Contents"))
    chunks: list[bytes] = []
    for item in (contents if isinstance(contents, list) else [contents]):
        resolved = doc.resolve(item)
        if isinstance(resolved, Stream):
            chunks.append(resolved.data(doc))
    stream = b"\n".join(chunks)

    runs: list[TextRun] = []
    font: _Font | None = None
    leading = 0.0
    # Text matrix and text line matrix, as [a b c d e f].
    tm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    tlm = list(tm)

    def translate(tx: float, ty: float) -> None:
        nonlocal tm, tlm
        tlm = [
            tlm[0], tlm[1], tlm[2], tlm[3],
            tlm[0] * tx + tlm[2] * ty + tlm[4],
            tlm[1] * tx + tlm[3] * ty + tlm[5],
        ]
        tm = list(tlm)

    def show(raw: bytes) -> None:
        if font is None:
            raise PdfParseError("text shown before any /Tf font selection")
        runs.append(TextRun(x=tm[4], y=tm[5], text=font.decode(raw)))

    for operator, operands in _tokenize_content(stream):
        if operator == "BT":
            tm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
            tlm = list(tm)
        elif operator == "Tf" and len(operands) >= 2:
            font = fonts.get(str(operands[-2]))
            if font is None:
                raise PdfParseError(f"content selects unknown font /{operands[-2]}")
        elif operator == "TL" and operands:
            leading = float(operands[-1])
        elif operator == "Tm" and len(operands) >= 6:
            tm = [float(v) for v in operands[-6:]]
            tlm = list(tm)
        elif operator == "Td" and len(operands) >= 2:
            translate(float(operands[-2]), float(operands[-1]))
        elif operator == "TD" and len(operands) >= 2:
            leading = -float(operands[-1])
            translate(float(operands[-2]), float(operands[-1]))
        elif operator == "T*":
            translate(0.0, -leading)
        elif operator == "Tj" and operands:
            show(operands[-1])
        elif operator == "'" and operands:
            translate(0.0, -leading)
            show(operands[-1])
        elif operator == '"' and len(operands) >= 3:
            translate(0.0, -leading)
            show(operands[-1])
        elif operator == "TJ" and operands and isinstance(operands[-1], list):
            for element in operands[-1]:
                if isinstance(element, bytes):
                    show(element)
    return runs


def page_text(doc: Document, page: dict) -> str:
    """Reassemble a page's text: runs grouped into lines by baseline, top to bottom."""
    lines: dict[float, list[TextRun]] = {}
    for run in page_runs(doc, page):
        lines.setdefault(round(run.y, 1), []).append(run)
    ordered = []
    for baseline in sorted(lines, reverse=True):
        parts = sorted(lines[baseline], key=lambda r: r.x)
        ordered.append("".join(p.text for p in parts))
    return "\n".join(ordered)


def extract_pages(data: bytes) -> list[str]:
    """Extract the text layer of every page, in page order."""
    doc = Document.load(data)
    return [page_text(doc, page) for page in doc.pages()]


def page_count(data: bytes) -> int:
    return len(Document.load(data).pages())
