"""The seven bundles committed under `fixtures/synthetic/ar/bundles/`, and what each means.

Every synthetic PDF in the corpus has a bundle, and the PDF member is the committed PDF's
bytes. The `expect` of each is the oracle INGEST and the judges use: `None` means the
bundle must be accepted; a name is the registered constraint it must be refused with.

The scanned and encrypted PDFs are refused for what is wrong with the PDF, not with the
archive -- their bundles are well-formed, which is exactly why they are worth having.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ar_corpus import document

from . import portal_format as fmt
from .blocklist import Block, ImageNote
from .bundle import (
    STAMP_CONTEXT, PortalFiles, make_files, seed_text_defects, text_blocks,
)
from .pdffacts import PageFacts, read_pages

BASELINE_PDF = "fixtures/synthetic/ar/ar_baseline.pdf"
IMAGE_ONLY_PDF = "fixtures/synthetic/ar/negative/image_only.pdf"
ENCRYPTED_PDF = "fixtures/synthetic/ar/negative/encrypted.pdf"
# The 31-page PDF is not a committed file any more: it was `negative/too_many_pages.pdf` while 31
# pages were over the limit. The corpus generator still builds it (`negatives.build_pages_31`),
# and this digest -- the deleted file's -- pins that it builds the very same bytes.
PAGES_31_PDF = "tools/fixtures/ar_corpus/negatives.py:build_pages_31"
PAGES_31_PDF_SHA256 = "acb3c347dbfe4b38efbc7e56f4389e97725b529966defa2a39c21e34f74da12a"

# The encrypted PDF's text layer cannot be read without its password, so the recognised
# text of its bundle is authored here instead of extracted.
ENCRYPTED_PAGES = tuple(
    PageFacts(document.PAGE_WIDTH, document.PAGE_HEIGHT, 0, text) for text in (
        "Синтетическая негативная фикстура: зашифрованный документ.\n"
        "Файл защищён паролем и должен быть отклонён явно.",
        "Страница 2. Текстовый слой присутствует, но недоступен без пароля.\n"
        "Нарушено единственное правило: файл зашифрован.",
    )
)

# What the portal "recognised" on the two scanned pages of the image-only PDF.
SCANNED_RECOGNISED = {
    0: "Синтетический распознанный текст страницы 1.\n"
       "Страница не имеет текстового слоя; текст получен только из блока портала.",
    1: "Синтетический распознанный текст страницы 2.\n"
       "Страница не имеет текстового слоя; текст получен только из блока портала.",
}

PLAN_IMAGE = ImageNote(
    drawing_type="План",
    axes=("1.A", "1.B", "2.A"),
    summary="Синтетический фрагмент плана этажа: контур здания в осях 1-2 и А-В.",
    description="Иллюстрация создана генератором и не имеет проектного содержания: "
                "прямоугольный контур, четыре оси и подпись «Синтетический план».",
    entities=("ось 1", "ось 2", "ось А", "ось В"),
)
SCHEME_IMAGE = ImageNote(
    drawing_type="Схема",
    axes=("П.1", "П.2"),
    summary="Синтетическая схема участка с ломаным контуром.",
    description="Иллюстрация создана генератором: шестиугольный контур без проектного "
                "содержания.",
    entities=("контур участка",),
)
# Six vertices, inside the page, nothing like a real drawing's outline.
SCHEME_POLYGON = ((0.12, 0.60), (0.55, 0.60), (0.55, 0.70), (0.88, 0.70), (0.88, 0.82),
                  (0.12, 0.82))


def _stamp(page_index: int) -> Block:
    sheet = "" if page_index == 0 else str(page_index + 1)
    return Block(
        fmt.KIND_STAMP, page_index, (0.50, 0.86, 0.905, 0.945),
        fields=(("code", STAMP_CONTEXT.code), ("stage", STAMP_CONTEXT.stage),
                ("sheet", sheet), ("object", STAMP_CONTEXT.obj),
                ("organization", STAMP_CONTEXT.organization)),
    )


def baseline_full(pdf: bytes) -> PortalFiles:
    """All five members: eight TEXT blocks, a rectangle and a polygon IMAGE block, two
    STAMP blocks, the HTML and a stamp audit with an entry per stamp."""
    extra = [
        Block(fmt.KIND_IMAGE, 2, (0.12, 0.62, 0.88, 0.80), image=PLAN_IMAGE),
        # The polygon block's box is derived from its vertices; the one given is ignored.
        Block(fmt.KIND_IMAGE, 4, (0, 0, 0, 0), polygon=SCHEME_POLYGON, image=SCHEME_IMAGE),
        _stamp(0), _stamp(7),
    ]
    return make_files(pdf, "ar_baseline", extra_blocks=extra, stamp=STAMP_CONTEXT,
                      html=True, stamp_audit=True)


def baseline_minimal(pdf: bytes) -> PortalFiles:
    return make_files(pdf, "ar_baseline_minimal")


def baseline_ocr_defects(pdf: bytes) -> PortalFiles:
    pages = read_pages(pdf)
    bodies, seeded = seed_text_defects(pages)
    return make_files(pdf, "ar_baseline_ocr_defects", pages=pages,
                      blocks=text_blocks(pages, bodies=bodies), defects=seeded)


def image_only(pdf: bytes) -> PortalFiles:
    """No block on any page, and no text layer: the text-layer rule refuses it."""
    return make_files(pdf, "image_only")


def image_only_with_block(pdf: bytes) -> PortalFiles:
    """A TEXT block on each scanned page makes the rule hold; the text is recognised text."""
    pages = read_pages(pdf)
    blocks = text_blocks(pages, only=range(len(pages)), bodies=SCANNED_RECOGNISED)
    return make_files(pdf, "image_only_with_block", pages=pages, blocks=blocks)


def encrypted(pdf: bytes) -> PortalFiles:
    return make_files(pdf, "encrypted", pages=ENCRYPTED_PAGES)


def pages_31(pdf: bytes) -> PortalFiles:
    """Thirty-one pages: over the old limit, inside the new one."""
    return make_files(pdf, "pages_31")


@dataclass(frozen=True)
class CommittedBundle:
    file: str
    source_pdf: str
    description: str
    make: Callable[[bytes], PortalFiles]
    expect: str | None = None


COMMITTED = (
    CommittedBundle(
        "ar_baseline.zip", BASELINE_PDF,
        "The baseline, complete: 8 TEXT blocks (the text layer), 2 IMAGE blocks (one a "
        "polygon), 2 STAMP blocks, the portal HTML and a stamp audit.",
        baseline_full),
    CommittedBundle(
        "ar_baseline_minimal.zip", BASELINE_PDF,
        "The baseline with the three required members only and TEXT blocks only.",
        baseline_minimal),
    CommittedBundle(
        "ar_baseline_ocr_defects.zip", BASELINE_PDF,
        "The baseline's three required members; the recognised text of six pages carries "
        "seeded flaws (Latin homoglyphs, a CJK character, doubled list markers, a "
        "mixed-script word) and engineering designations that must not be flagged.",
        baseline_ocr_defects),
    CommittedBundle(
        "image_only.zip", IMAGE_ONLY_PDF,
        "The scanned PDF with a block list holding no block: neither page has a text layer "
        "or a portal block, so it is refused.",
        image_only, expect="every_page_has_extractable_text"),
    CommittedBundle(
        "image_only_with_block.zip", IMAGE_ONLY_PDF,
        "The scanned PDF with one TEXT block on each of its two pages: the text-layer rule "
        "holds and the text is recognised text only.",
        image_only_with_block),
    CommittedBundle(
        "encrypted.zip", ENCRYPTED_PDF,
        "The password-protected PDF in a well-formed bundle: refused for the PDF.",
        encrypted, expect="not_encrypted"),
    CommittedBundle(
        "pages_31.zip", PAGES_31_PDF,
        "Thirty-one pages with a TEXT block each: over the old 30-page limit, inside the "
        "500-page one.",
        pages_31),
)
