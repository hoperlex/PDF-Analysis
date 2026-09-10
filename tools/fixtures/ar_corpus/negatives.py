"""The negative corpus: one fixture per envelope rule, violating that rule and no other.

Attributable failure is the whole design constraint. If a fixture violated two rules at
once, a lane that rejected it would have proved nothing about which rule fired, and a
regression in one rule could hide behind another. So each builder here is written to be
unimpeachable on every rule except its own, and `build_ar_corpus.py` asserts exactly that
against `envelope.check` before writing anything.

Every fixture is deterministic for the same reasons the baseline is: no clock, no PRNG
seeded from the environment, no compression.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import document, pdfwrite
from .pdfwrite import Name

# Kept small: these exist to be rejected, not read.
_NEG_BODY_SIZE = 11.0
_NEG_X = document.MARGIN_LEFT
_NEG_TOP = document.PAGE_HEIGHT - document.MARGIN_TOP


@dataclass(frozen=True)
class NegativeFixture:
    name: str
    filename: str
    violates: str
    description: str
    data: bytes


def _lines(*texts: str) -> list[tuple[str, float, float, float]]:
    out: list[tuple[str, float, float, float]] = []
    y = _NEG_TOP
    for text in texts:
        out.append((text, _NEG_BODY_SIZE, _NEG_X, y))
        y -= _NEG_BODY_SIZE * 1.5
    return out


def build_encrypted(font: pdfwrite.EmbeddedFont) -> bytes:
    """A password-protected PDF. Violates ENV-ENCRYPTED and nothing else.

    Two pages, both with a real text layer, well inside the size and page limits, so the
    only thing wrong with it is that it is encrypted. The user password is not empty, so
    it cannot be opened by a reader that only tries the default.
    """
    security = pdfwrite.StandardSecurity(
        user_password="synthetic-user-pw", owner_password="synthetic-owner-pw"
    )
    return document.simple_text_pdf(
        font,
        [
            _lines(
                "Синтетическая негативная фикстура: зашифрованный документ.",
                "Файл защищён паролем и должен быть отклонён явно.",
                "Пароль пользователя: synthetic-user-pw",
            ),
            _lines(
                "Страница 2. Текстовый слой присутствует, но недоступен",
                "без пароля. Нарушено единственное правило: ENV-ENCRYPTED.",
            ),
        ],
        security=security,
    )


ENCRYPTED_USER_PASSWORD = "synthetic-user-pw"
ENCRYPTED_OWNER_PASSWORD = "synthetic-owner-pw"


def _scan_bitmap(width: int, height: int, seed: int) -> bytes:
    """A 1-bit-per-pixel bitmap that reads as a scanned page: dark word-shaped blocks.

    Deterministic: a fixed linear congruential generator, seeded by the caller, never by
    the clock. 0 bits are black under the default /Decode for /DeviceGray.
    """
    row_bytes = (width + 7) // 8
    rows = [bytearray(b"\xff" * row_bytes) for _ in range(height)]
    state = seed

    def rand(bound: int) -> int:
        nonlocal state
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state % bound

    margin = width // 10
    y = height // 8
    while y < height - height // 8:
        x = margin
        line_height = 11
        while x < width - margin:
            word = 18 + rand(60)
            if x + word > width - margin:
                break
            for row in range(y, min(y + line_height, height)):
                for col in range(x, x + word):
                    rows[row][col >> 3] &= ~(0x80 >> (col & 7)) & 0xFF
            x += word + 8 + rand(6)
        y += line_height + 12
    return b"".join(bytes(r) for r in rows)


def build_image_only(font: pdfwrite.EmbeddedFont) -> bytes:
    """A scanned-looking PDF with no text operators. Violates ENV-TEXT and nothing else.

    The `font` argument is deliberately unused for drawing: the point of this fixture is
    that OCR must not be silently substituted, so there is no text layer to fall back on.
    """
    width, height = 827, 1170  # A4 at roughly 100 dpi
    pdf = pdfwrite.Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()

    page_refs = []
    for index in range(2):
        image = _scan_bitmap(width, height, seed=1_000_003 + index)
        image_ref = pdf.add_stream({
            "Type": Name("XObject"),
            "Subtype": Name("Image"),
            "Width": width,
            "Height": height,
            "ColorSpace": Name("DeviceGray"),
            "BitsPerComponent": 1,
        }, image)
        stream = (
            f"q {pdfwrite.num(document.PAGE_WIDTH)} 0 0 "
            f"{pdfwrite.num(document.PAGE_HEIGHT)} 0 0 cm /Im1 Do Q\n"
        ).encode("ascii")
        content_ref = pdf.add_stream({}, stream)
        page_refs.append(pdf.add({
            "Type": Name("Page"),
            "Parent": pages_ref,
            "MediaBox": [0, 0, document.PAGE_WIDTH, document.PAGE_HEIGHT],
            "Resources": {"XObject": {"Im1": image_ref}},
            "Contents": content_ref,
        }))

    pdf.put(pages_ref, {"Type": Name("Pages"), "Kids": page_refs, "Count": len(page_refs)})
    pdf.put(catalog_ref, {"Type": Name("Catalog"), "Pages": pages_ref})
    return pdf.serialize(catalog_ref, document.info_dictionary(), document.DOC_ID)


_PADDING_LINE = (
    b"%% synthetic padding: this object exists only to carry the file past the "
    b"25 MiB envelope limit. It is unreferenced and holds no document content.\n"
)


def build_oversize(font: pdfwrite.EmbeddedFont) -> bytes:
    """A valid two-page text PDF carried past 25 MiB. Violates ENV-SIZE and nothing else.

    The bulk is one unreferenced, uncompressed stream of a repeating ASCII line. That
    keeps the fixture honest - it really is over the limit on disk - while staying cheap
    in Git, because the repository's own zlib compresses a repeating pattern to almost
    nothing.
    """
    target = document.MAX_OVERSIZE_TARGET_BYTES
    repeats = target // len(_PADDING_LINE) + 1
    padding = _PADDING_LINE * repeats

    def add_padding(pdf: pdfwrite.Pdf) -> None:
        pdf.add_stream({"Type": Name("SyntheticPadding")}, padding)

    return document.simple_text_pdf(
        font,
        [
            _lines(
                "Синтетическая негативная фикстура: превышение размера файла.",
                "Документ корректен во всём, кроме объёма: он больше 25 МиБ.",
            ),
            _lines(
                "Страница 2. Текстовый слой присутствует на каждой странице.",
                "Нарушено единственное правило: ENV-SIZE.",
            ),
        ],
        extra_objects=add_padding,
    )


def build_too_many_pages(font: pdfwrite.EmbeddedFont) -> bytes:
    """A 31-page text PDF. Violates ENV-PAGES and nothing else.

    Every page carries real text, so ENV-TEXT genuinely passes rather than being skipped:
    the fixture is one page over the limit and correct in every other respect.
    """
    page_count = document.MAX_PAGES_LIMIT + 1
    pages = [
        _lines(
            f"Синтетическая негативная фикстура: страница {n} из {page_count}.",
            "Документ превышает предел в 30 страниц.",
            "Нарушено единственное правило: ENV-PAGES.",
        )
        for n in range(1, page_count + 1)
    ]
    return document.simple_text_pdf(font, pages)


NOT_A_PDF_TEXT = (
    "Синтетическая негативная фикстура: это не PDF.\n"
    "\n"
    "Файл представлен как исходный документ, но не имеет заголовка %PDF-.\n"
    "Приём такого входа должен завершаться явной ошибкой: смешанные форматы\n"
    "в конверт PC-01 не входят (PROTOTYPE_PROFILE.md, раздел 7.1).\n"
    "\n"
    "Нарушено единственное правило: ENV-PDF.\n"
)


def build_not_a_pdf() -> bytes:
    return NOT_A_PDF_TEXT.encode("utf-8")


def build_companion_archive() -> bytes:
    """A ZIP holding a PDF plus a companion file. Violates ENV-PDF and nothing else.

    Built by hand rather than through `zipfile` so every field, including the timestamps
    `zipfile` would take from the clock, is fixed.
    """
    import struct

    entries = [
        ("readme.txt",
         "Синтетическая негативная фикстура: архив с сопроводительными файлами.\n"
         "ZIP и companion-входы в конверт PC-01 не входят.\n"
         "Нарушено единственное правило: ENV-PDF.\n".encode("utf-8")),
        ("ar_document.pdf",
         b"%PDF-1.7\n% synthetic stub inside an archive; the archive itself is the "
         b"fixture\n%%EOF\n"),
        ("companion.dwg.txt",
         "Синтетическая заглушка сопроводительного файла.\n".encode("utf-8")),
    ]

    dos_time = 0  # 00:00:00
    dos_date = (1980 - 1980) << 9 | 1 << 5 | 1  # 1980-01-01
    import zlib as _zlib

    local = bytearray()
    central = bytearray()
    for name, payload in entries:
        raw_name = name.encode("utf-8")
        crc = _zlib.crc32(payload) & 0xFFFFFFFF
        offset = len(local)
        local += struct.pack(
            "<IHHHHHIIIHH", 0x04034B50, 20, 0, 0, dos_time, dos_date,
            crc, len(payload), len(payload), len(raw_name), 0,
        )
        local += raw_name + payload
        central += struct.pack(
            "<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, 0, dos_time, dos_date,
            crc, len(payload), len(payload), len(raw_name), 0, 0, 0, 0, 0, offset,
        )
        central += raw_name

    end = struct.pack(
        "<IHHHHIIH", 0x06054B50, 0, 0, len(entries), len(entries),
        len(central), len(local), 0,
    )
    return bytes(local + central + end)


def build_all(font: pdfwrite.EmbeddedFont) -> list[NegativeFixture]:
    from . import envelope

    return [
        NegativeFixture(
            name="encrypted",
            filename="encrypted.pdf",
            violates=envelope.RULE_NOT_ENCRYPTED,
            description=(
                "Password-protected PDF (standard security handler, revision 2). "
                f"User password {ENCRYPTED_USER_PASSWORD!r}, owner password "
                f"{ENCRYPTED_OWNER_PASSWORD!r}. Two pages, well inside the size and "
                "page limits."
            ),
            data=build_encrypted(font),
        ),
        NegativeFixture(
            name="image_only",
            filename="image_only.pdf",
            violates=envelope.RULE_TEXT_LAYER,
            description=(
                "Scanned-looking PDF: two pages, each a single 1-bit image XObject and "
                "no text operator anywhere. OCR must not be silently substituted."
            ),
            data=build_image_only(font),
        ),
        NegativeFixture(
            name="oversize",
            filename="oversize.pdf",
            violates=envelope.RULE_MAX_BYTES,
            description=(
                "Valid two-page PDF with a real text layer, carried past 25 MiB by one "
                "unreferenced uncompressed padding stream."
            ),
            data=build_oversize(font),
        ),
        NegativeFixture(
            name="too_many_pages",
            filename="too_many_pages.pdf",
            violates=envelope.RULE_MAX_PAGES,
            description=(
                f"{document.MAX_PAGES_LIMIT + 1}-page PDF, one page over the limit. "
                "Every page carries real extractable text."
            ),
            data=build_too_many_pages(font),
        ),
        NegativeFixture(
            name="not_a_pdf",
            filename="not_a_pdf.txt",
            violates=envelope.RULE_IS_PDF,
            description="A UTF-8 text file presented as the source document.",
            data=build_not_a_pdf(),
        ),
        NegativeFixture(
            name="companion_archive",
            filename="companion_archive.zip",
            violates=envelope.RULE_IS_PDF,
            description=(
                "A ZIP archive holding a PDF plus companion files. ZIP and companion "
                "inputs are outside the PC-01 envelope."
            ),
            data=build_companion_archive(),
        ),
    ]
