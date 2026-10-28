"""Every committed PDF opens in three independent readers and they agree on its shape."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pdfplumber
import pypdf
import pypdfium2 as pdfium
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cmp_fixtures_support as support  # noqa: E402

PDFS = sorted(name for name in support.load_files() if name.endswith(".pdf"))


def test_the_corpus_holds_the_expected_pdfs() -> None:
    assert PDFS == [
        "sp1/new_r1.pdf", "sp1/new_r2.pdf", "sp1/new_r3.pdf", "sp1/old_p.pdf",
        "vs1/v1.pdf", "vs1/v2.pdf", "vs1/v3.pdf", "vs1/v4.pdf", "vs1/v5.pdf",
    ]


@pytest.mark.parametrize("name", PDFS)
def test_three_readers_open_it_and_agree_on_pages_and_sizes(name: str) -> None:
    data = support.load_files()[name]
    reader = pypdf.PdfReader(io.BytesIO(data))
    with pdfplumber.open(io.BytesIO(data)) as plumber:
        document = pdfium.PdfDocument(data)
        try:
            assert len(reader.pages) == len(plumber.pages) == len(document) > 0
            for index, page in enumerate(reader.pages):
                width, height = float(page.mediabox.width), float(page.mediabox.height)
                assert abs(float(plumber.pages[index].width) - width) < 0.02
                assert abs(float(plumber.pages[index].height) - height) < 0.02
                fium_w, fium_h = document[index].get_size()
                assert abs(fium_w - width) < 0.02 and abs(fium_h - height) < 0.02
                assert page.rotation == 0 and "/CropBox" not in page, "the committed sets use neither /Rotate nor a CropBox"
        finally:
            document.close()


@pytest.mark.parametrize("name", PDFS)
def test_every_page_renders_and_has_ink(name: str) -> None:
    document = pdfium.PdfDocument(support.load_files()[name])
    try:
        for index in range(len(document)):
            page = document[index]
            width, height = page.get_size()
            image = page.render(scale=300.0 / max(width, height)).to_pil().convert("L")
            low, high = image.getextrema()
            assert low < 128 <= high, f"{name} page {index + 1} renders blank"
    finally:
        document.close()
