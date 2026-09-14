"""Turn a `content.Doc` into deterministic PDF bytes.

Layout is deliberately dumb, for the same reason session A4's was: each `Line` becomes
exactly one text-showing operator at one absolute position. Text is never reflowed and
never justified, so no extractor has to decide where a soft wrap was or how wide an
inter-word gap has to be before it counts as a space. That is the property that makes a
seeded quotation recoverable character-for-character, and it is the only reason the
grounding gate downstream can be trusted.

The one thing layout *must* police is overflow: a line wider than the text box runs off
the page, and a reader reconstructing columns could then split it. `too_wide()` reports
every such line and the build refuses to write.

Unlike PC-01 - one document, one fixed `/ID` - PC-02 is a corpus, so the document id,
title and subject are per document. They are still derived deterministically from the
document label and never from a clock or a PRNG.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ar_corpus import pdfwrite
from ar_corpus.pdfwrite import Name, Pdf, Ref

from . import content

# A4 in PostScript points, matching the PC-01 fixture geometry.
PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89

MARGIN_LEFT = 56.7
MARGIN_RIGHT = 56.7
MARGIN_TOP = 70.0
TEXT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
FOOTER_BASELINE = 34.0
FOOTER_SIZE = 8.0

LINE_HEIGHT_FACTOR = 1.35

FONT_RESOURCE = "F1"

# Fixed metadata. No clock, no PRNG: these are the values that make the output stable.
CREATION_DATE = "D:20260101000000Z"
PRODUCER = "PDF-Analysis PC-02 validation corpus generator (fixtures/validation/PC-02)"


@dataclass(frozen=True)
class PlacedLine:
    page: int
    index: int
    text: str
    x: float
    y: float
    size: float


def document_id(label: str) -> bytes:
    """A stable 16-byte /ID derived from the document label.

    Derived, not random: two runs of the generator on two machines must produce the same
    bytes, and two different documents must not share an id.
    """
    return hashlib.sha256(f"PC-02/{label}".encode("utf-8")).digest()[:16]


def _line_advance(line: content.Line) -> float:
    return line.space_before + line.size * LINE_HEIGHT_FACTOR


def place(doc: content.Doc, font: pdfwrite.EmbeddedFont) -> list[PlacedLine]:
    """Compute the absolute position of every drawn line in the document."""
    placed: list[PlacedLine] = []
    for page in doc.pages:
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


def too_wide(doc: content.Doc,
             font: pdfwrite.EmbeddedFont) -> list[tuple[int, str, float]]:
    """Every line that would overflow the text box, as (page, text, width)."""
    out: list[tuple[int, str, float]] = []
    for page in doc.pages:
        for line in page.lines:
            if not line.text:
                continue
            width = font.text_width(line.text, line.size)
            if width > TEXT_WIDTH:
                out.append((page.number, line.text, round(width, 2)))
        footer = doc.footer.format(page=page.number)
        width = font.text_width(footer, FOOTER_SIZE)
        if width > TEXT_WIDTH:
            out.append((page.number, footer, round(width, 2)))
    return out


def runs_off_page(doc: content.Doc) -> list[tuple[int, str, float]]:
    """Every line whose baseline would fall into or below the footer band.

    An overfull page is as damaging as an overwide line: text drawn under the footer
    baseline can collide with the footer and merge into one extracted line.
    """
    out: list[tuple[int, str, float]] = []
    floor = FOOTER_BASELINE + 3.0 * FOOTER_SIZE
    for page in doc.pages:
        y = PAGE_HEIGHT - MARGIN_TOP
        for line in page.lines:
            y -= _line_advance(line)
            if line.text and y < floor:
                out.append((page.number, line.text, round(y, 2)))
    return out


def _page_content(doc: content.Doc, font: pdfwrite.EmbeddedFont,
                  page: content.Page, placed: list[PlacedLine]) -> bytes:
    parts: list[str] = []
    for line in placed:
        if line.page != page.number:
            continue
        parts.append(pdfwrite.show_text(
            font, FONT_RESOURCE, line.text, line.size, line.x, line.y
        ))
    footer = doc.footer.format(page=page.number)
    parts.append(pdfwrite.show_text(
        font, FONT_RESOURCE, footer, FOOTER_SIZE, MARGIN_LEFT, FOOTER_BASELINE
    ))
    return "".join(parts).encode("ascii")


def info_dictionary(doc: content.Doc) -> dict[str, object]:
    return {
        "Title": pdfwrite.EncryptableString(doc.title),
        "Author": pdfwrite.EncryptableString(content.AUTHOR),
        "Subject": pdfwrite.EncryptableString(doc.subject),
        "Keywords": pdfwrite.EncryptableString(
            f"synthetic; fixture; PC-02; {doc.label}; АР; "
            "internal_contradiction; explicit_placeholder"
        ),
        "Creator": pdfwrite.EncryptableString(PRODUCER),
        "Producer": pdfwrite.EncryptableString(PRODUCER),
        "CreationDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(CREATION_DATE)),
        "ModDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(CREATION_DATE)),
    }


def build(doc: content.Doc, font: pdfwrite.EmbeddedFont) -> bytes:
    """Build one measurable document's PDF bytes."""
    overflow = too_wide(doc, font)
    if overflow:
        detail = "\n".join(
            f"  {doc.label} page {p}: width {w} > {TEXT_WIDTH} - {t!r}"
            for p, t, w in overflow
        )
        raise ValueError(
            "these lines would overflow the text box, so a quotation on them could be "
            f"split by a reader:\n{detail}"
        )
    spill = runs_off_page(doc)
    if spill:
        detail = "\n".join(
            f"  {doc.label} page {p}: baseline {y} - {t!r}" for p, t, y in spill
        )
        raise ValueError(
            "these lines would be drawn into the footer band, where they could merge "
            f"with the footer into one extracted line:\n{detail}"
        )

    placed = place(doc, font)
    pdf = Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)

    page_refs: list[Ref] = []
    for page in doc.pages:
        content_ref = pdf.add_stream({}, _page_content(doc, font, page, placed))
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
    return pdf.serialize(catalog_ref, info_dictionary(doc), document_id(doc.label))
