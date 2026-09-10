"""Layout for the AR baseline: turn `content.PAGES` into a deterministic PDF.

Layout is deliberately dumb. Text is never reflowed and never justified: each `Line`
becomes exactly one text-showing operator at one absolute position. That is what keeps a
seeded quotation recoverable character-for-character, because no extractor ever has to
decide where a soft wrap was or how wide an inter-word gap has to be before it counts as
a space.

The one thing layout *must* police is overflow. A line wider than the text box would run
off the page, and a reader reconstructing columns could then split it. `too_wide()`
reports any such line and the build refuses to write.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import content, pdfwrite
from .pdfwrite import Name, Pdf, Ref

# A4 in PostScript points.
PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89

MARGIN_LEFT = 56.7
MARGIN_RIGHT = 56.7
MARGIN_TOP = 70.0
TEXT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
FOOTER_BASELINE = 34.0

LINE_HEIGHT_FACTOR = 1.35

FONT_RESOURCE = "F1"

# Fixed metadata. No clock, no PRNG: these are the values that make the output stable.
CREATION_DATE = "D:20260101000000Z"
DOC_ID = bytes.fromhex("50432d3031204152206261736520646f63")[:16].ljust(16, b"\x00")
PRODUCER = "PDF-Analysis synthetic AR corpus generator (tools/fixtures)"
TITLE = "СП-7-АР. Раздел 3. Архитектурные решения (синтетический документ)"
AUTHOR = "СИНТЕТИКПРОЕКТ (вымышленная организация)"
SUBJECT = "Синтетическая приёмочная фикстура PC-01. Не проектная документация."


@dataclass(frozen=True)
class PlacedLine:
    page: int
    index: int
    text: str
    x: float
    y: float
    size: float


def _line_advance(line: content.Line) -> float:
    return line.space_before + line.size * LINE_HEIGHT_FACTOR


def place(font: pdfwrite.EmbeddedFont) -> list[PlacedLine]:
    """Compute the absolute position of every drawn line in the document."""
    placed: list[PlacedLine] = []
    for page in content.PAGES:
        y = PAGE_HEIGHT - MARGIN_TOP
        for index, line in enumerate(page.lines):
            y -= _line_advance(line)
            if not line.text:
                continue
            if line.center:
                width = font.text_width(line.text, line.size)
                x = MARGIN_LEFT + (TEXT_WIDTH - width) / 2.0
            else:
                x = MARGIN_LEFT + line.indent
            placed.append(PlacedLine(
                page=page.number, index=index, text=line.text,
                x=round(x, 3), y=round(y, 3), size=line.size,
            ))
    return placed


def too_wide(font: pdfwrite.EmbeddedFont) -> list[tuple[int, str, float]]:
    """Every line that would overflow the text box, as (page, text, width)."""
    out: list[tuple[int, str, float]] = []
    for page in content.PAGES:
        for line in page.lines:
            if not line.text:
                continue
            width = font.text_width(line.text, line.size)
            if width > TEXT_WIDTH:
                out.append((page.number, line.text, round(width, 2)))
        footer = content.FOOTER_TEMPLATE.format(page=page.number)
        width = font.text_width(footer, content.FOOTER_SIZE)
        if width > TEXT_WIDTH:
            out.append((page.number, footer, round(width, 2)))
    return out


def _page_content(font: pdfwrite.EmbeddedFont, page: content.Page,
                  placed: list[PlacedLine]) -> bytes:
    parts: list[str] = []
    for line in placed:
        if line.page != page.number:
            continue
        parts.append(pdfwrite.show_text(
            font, FONT_RESOURCE, line.text, line.size, line.x, line.y
        ))
    footer = content.FOOTER_TEMPLATE.format(page=page.number)
    parts.append(pdfwrite.show_text(
        font, FONT_RESOURCE, footer, content.FOOTER_SIZE, MARGIN_LEFT, FOOTER_BASELINE
    ))
    return "".join(parts).encode("ascii")


def info_dictionary() -> dict[str, object]:
    return {
        "Title": pdfwrite.EncryptableString(TITLE),
        "Author": pdfwrite.EncryptableString(AUTHOR),
        "Subject": pdfwrite.EncryptableString(SUBJECT),
        "Keywords": pdfwrite.EncryptableString(
            "synthetic; fixture; PC-01; АР; internal_contradiction; explicit_placeholder"
        ),
        "Creator": pdfwrite.EncryptableString(PRODUCER),
        "Producer": pdfwrite.EncryptableString(PRODUCER),
        "CreationDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(CREATION_DATE)),
        "ModDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(CREATION_DATE)),
    }


def simple_text_pdf(
    font: pdfwrite.EmbeddedFont,
    pages: list[list[tuple[str, float, float, float]]],
    *,
    security: pdfwrite.StandardSecurity | None = None,
    extra_objects=None,
) -> bytes:
    """Build a PDF from explicit (text, size, x, y) placements per page.

    Used for the baseline and for every negative fixture that still needs a real text
    layer, so they all share one code path and one set of fixed metadata.
    """
    pdf = Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)

    page_refs: list[Ref] = []
    for placements in pages:
        stream = "".join(
            pdfwrite.show_text(font, FONT_RESOURCE, text, size, x, y)
            for text, size, x, y in placements
        ).encode("ascii")
        content_ref = pdf.add_stream({}, stream)
        page_refs.append(pdf.add({
            "Type": Name("Page"),
            "Parent": pages_ref,
            "MediaBox": [0, 0, PAGE_WIDTH, PAGE_HEIGHT],
            "Resources": {"Font": {FONT_RESOURCE: font_ref}},
            "Contents": content_ref,
        }))

    if extra_objects is not None:
        extra_objects(pdf)

    pdf.put(pages_ref, {
        "Type": Name("Pages"),
        "Kids": page_refs,
        "Count": len(page_refs),
    })
    pdf.put(catalog_ref, {
        "Type": Name("Catalog"),
        "Pages": pages_ref,
        "Lang": pdfwrite.RawBytes(pdfwrite.pdf_literal("ru-RU")),
    })
    return pdf.serialize(catalog_ref, info_dictionary(), DOC_ID, security=security)


def build_baseline(font: pdfwrite.EmbeddedFont) -> bytes:
    """Build the AR baseline PDF from `content.PAGES`."""
    overflow = too_wide(font)
    if overflow:
        detail = "\n".join(
            f"  page {p}: width {w} > {TEXT_WIDTH} - {t!r}" for p, t, w in overflow
        )
        raise ValueError(
            "these lines would overflow the text box, so a quotation on them could be "
            f"split by a reader:\n{detail}"
        )

    placed = place(font)
    pdf = Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)

    page_refs: list[Ref] = []
    for page in content.PAGES:
        content_ref = pdf.add_stream({}, _page_content(font, page, placed))
        page_refs.append(pdf.add({
            "Type": Name("Page"),
            "Parent": pages_ref,
            "MediaBox": [0, 0, PAGE_WIDTH, PAGE_HEIGHT],
            "Resources": {"Font": {FONT_RESOURCE: font_ref}},
            "Contents": content_ref,
        }))

    pdf.put(pages_ref, {
        "Type": Name("Pages"),
        "Kids": page_refs,
        "Count": len(page_refs),
    })
    pdf.put(catalog_ref, {
        "Type": Name("Catalog"),
        "Pages": pages_ref,
        "Lang": pdfwrite.RawBytes(pdfwrite.pdf_literal("ru-RU")),
    })
    return pdf.serialize(catalog_ref, info_dictionary(), DOC_ID)
