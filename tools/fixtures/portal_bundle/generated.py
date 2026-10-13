"""Fixtures that are generated when a test runs and never committed.

Three of the committed negatives change meaning under the bundle rules and cannot stay
as they are: a 26 MiB PDF is no longer over any limit, and 31 pages are no longer too
many. Their replacements are too big to commit (a sparse file past 250 MiB) or exist only
to sit one page past a limit (501 pages), so they are built on demand from the same
writer the committed corpus uses. The committed negatives stay until INGEST switches
their consumers.
"""

from __future__ import annotations

from pathlib import Path

from ar_corpus import document, pdfwrite
from ar_corpus.pdfwrite import Name

from . import portal_format as fmt
from .bundle import PortalFiles, build_bundle, make_files, text_blocks
from .pdffacts import read_pages

OVERSIZE_MAGIC = b"PK\x03\x04"           # the part still sniffs as a ZIP


def _font() -> pdfwrite.EmbeddedFont:
    # The loader lives in the corpus build script; reuse it rather than copy it.
    import build_ar_corpus

    return build_ar_corpus.load_font()


def oversize_sparse_file(path: Path, size: int) -> Path:
    """A sparse file of exactly `size` bytes that reads as a ZIP at its first bytes.

    Nothing is allocated: the file is extended with `truncate`, so a 251 MiB stand-in for
    an upload past the limit costs a few kilobytes of disk. `size` is the caller's -- the
    limit is 250 MiB and a test chooses how far past it to go.
    """
    if size < len(OVERSIZE_MAGIC):
        raise ValueError("the file must be at least as long as its magic bytes")
    with path.open("wb") as handle:
        handle.write(OVERSIZE_MAGIC)
        handle.truncate(size)
    return path


def _page_lines(texts: list[str]) -> list[tuple[str, float, float, float]]:
    out = []
    y = document.PAGE_HEIGHT - document.MARGIN_TOP
    for text in texts:
        out.append((text, 11.0, document.MARGIN_LEFT, y))
        y -= 16.5
    return out


def pdf_with_n_pages(count: int) -> bytes:
    """A text PDF of exactly `count` pages, every page with a real text layer.

    501 of them are the smallest document that is over the 500-page limit; it builds in
    a few seconds and is a few hundred KiB.
    """
    pages = [
        _page_lines([
            f"Синтетическая страница {number} из {count}.",
            "Документ создан для проверки границы по числу страниц.",
        ])
        for number in range(1, count + 1)
    ]
    return document.simple_text_pdf(_font(), pages)


def _scan_bitmap(width: int, height: int) -> bytes:
    """A 1-bit bitmap of horizontal bars that reads as a scan. 0 bits are black."""
    row_bytes = (width + 7) // 8
    rows = bytearray()
    for y in range(height):
        bar = (y // 5) % 3 == 0 and height // 8 < y < height - height // 8
        rows += (b"\x00" if bar else b"\xff") * row_bytes
    return bytes(rows)


def pdf_page_without_text_layer(page_count: int = 3, textless_page: int = 2) -> bytes:
    """A PDF whose page `textless_page` (1-based) is a bare image and every other page text.

    The page has neither a text layer nor, in the bundle built for it by
    `bundle_without_block`, any portal block -- the one case the text-layer rule refuses.
    """
    if not 1 <= textless_page <= page_count:
        raise ValueError("textless_page must name a page of the document")
    font = _font()
    pdf = pdfwrite.Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)
    page_refs = []
    for number in range(1, page_count + 1):
        if number == textless_page:
            image_ref = pdf.add_stream({
                "Type": Name("XObject"), "Subtype": Name("Image"), "Width": 64, "Height": 88,
                "ColorSpace": Name("DeviceGray"), "BitsPerComponent": 1,
            }, _scan_bitmap(64, 88))
            stream = (f"q {pdfwrite.num(document.PAGE_WIDTH)} 0 0 "
                      f"{pdfwrite.num(document.PAGE_HEIGHT)} 0 0 cm /Im1 Do Q\n").encode("ascii")
            resources = {"XObject": {"Im1": image_ref}}
        else:
            lines = _page_lines([f"Синтетическая страница {number} из {page_count}.",
                                 "Эта страница несёт текстовый слой."])
            stream = "".join(
                pdfwrite.show_text(font, document.FONT_RESOURCE, text, size, x, y)
                for text, size, x, y in lines
            ).encode("ascii")
            resources = {"Font": {document.FONT_RESOURCE: font_ref}}
        content_ref = pdf.add_stream({}, stream)
        page_refs.append(pdf.add({
            "Type": Name("Page"), "Parent": pages_ref,
            "MediaBox": [0, 0, document.PAGE_WIDTH, document.PAGE_HEIGHT],
            "Resources": resources, "Contents": content_ref,
        }))
    pdf.put(pages_ref, {"Type": Name("Pages"), "Kids": page_refs, "Count": len(page_refs)})
    pdf.put(catalog_ref, {"Type": Name("Catalog"), "Pages": pages_ref})
    return pdf.serialize(catalog_ref, document.info_dictionary(), document.DOC_ID)


def files_without_block(stem: str = "page_without_text", *, page_count: int = 3,
                        textless_page: int = 2) -> PortalFiles:
    """Portal files for `pdf_page_without_text_layer`, with no block on the textless page.

    The bundle is refused by the text-layer rule: that page has neither a layer nor a block.
    """
    pdf = pdf_page_without_text_layer(page_count, textless_page)
    return make_files(pdf, stem)


def files_with_block(stem: str = "page_without_text_with_block", *, page_count: int = 3,
                     textless_page: int = 2) -> PortalFiles:
    """The same PDF with one TEXT block on the textless page, so the rule is satisfied."""
    pdf = pdf_page_without_text_layer(page_count, textless_page)
    pages = read_pages(pdf)
    index = textless_page - 1
    recognised = {index: "Синтетический распознанный текст страницы без текстового слоя.\n"
                         "Текст получен только из блока портала."}
    blocks = text_blocks(pages, only=range(len(pages)), bodies=recognised)
    return make_files(pdf, stem, blocks=blocks)


def bundle_with_pages(count: int) -> bytes:
    """A bundle around `pdf_with_n_pages(count)`: accepted up to 500 pages, refused past it.

    The block list is capped at 500 pages because the pinned schema allows no more, so a
    501-page bundle breaks the page-count rule and nothing else.
    """
    pdf = pdf_with_n_pages(count)
    pages = read_pages(pdf)
    files = make_files(pdf, f"pages_{count}", pages=pages[:fmt.MAX_PAGES])
    expect = None if count <= fmt.MAX_PAGES else "page_count"
    return build_bundle(files, expect=expect).data


def bundle_without_block_on_textless_page() -> bytes:
    """`files_without_block` as an archive: refused, because one page has neither."""
    return build_bundle(files_without_block(), expect="every_page_has_extractable_text").data


def bundle_with_block_on_textless_page() -> bytes:
    """`files_with_block` as an archive: the same PDF, accepted."""
    return build_bundle(files_with_block()).data
