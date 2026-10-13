"""What a bundle needs to know about a PDF: its pages' boxes and its text layer.

Read with the repository's own independent extractor (`ar_corpus/pdfextract.py`), which
shares no code with the writer, so the recognised text of a clean bundle is the text
layer as a second reader sees it and not as the generator meant it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ar_corpus import pdfextract


@dataclass(frozen=True)
class PageFacts:
    width_pt: float
    height_pt: float
    rotation: int
    text: str                   # the text layer; empty when the page has none

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())


def _number(doc: pdfextract.Document, value: object) -> float:
    resolved = doc.resolve(value)
    if isinstance(resolved, bool) or not isinstance(resolved, (int, float)):
        raise pdfextract.PdfParseError(f"a page box entry is not a number: {resolved!r}")
    return float(resolved)


def read_pages(pdf: bytes) -> tuple[PageFacts, ...]:
    """Every page's size in points, rotation and text layer, in page order.

    Raises `pdfextract.EncryptedPdfError` for an encrypted file: its text cannot be read,
    so the caller must supply the facts it wants a bundle to carry.
    """
    doc = pdfextract.Document.load(pdf)
    pages: list[PageFacts] = []
    for page in doc.pages():
        box = doc.resolve(page.get("CropBox", page.get("MediaBox")))
        if not isinstance(box, list) or len(box) != 4:
            raise pdfextract.PdfParseError("a page without a four-number box")
        x0, y0, x1, y1 = (_number(doc, v) for v in box)
        rotation = int(_number(doc, page["Rotate"])) % 360 if "Rotate" in page else 0
        width, height = abs(x1 - x0), abs(y1 - y0)
        if rotation in (90, 270):
            width, height = height, width
        pages.append(PageFacts(width, height, rotation, pdfextract.page_text(doc, page)))
    return tuple(pages)
