"""Deterministic synthetic derivative of SP-1 R2: one visible graphic circle.

Original SP-1 bytes stay unchanged. This fixture makes an actual GRAPHIC/crop
request an explicit prerequisite rather than assuming every text edit yields one.
"""
from pathlib import Path
import io

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas


def main():
    root = Path(__file__).resolve().parents[5]
    source = PdfReader(root / "fixtures/comparison/sp1/new_r2.pdf")
    page = source.pages[0]
    overlay = io.BytesIO()
    canvas = Canvas(overlay, pagesize=(float(page.mediabox.width), float(page.mediabox.height)), invariant=1)
    canvas.setLineWidth(2)
    canvas.circle(200, 500, 8, stroke=1, fill=0)
    canvas.save()
    page.merge_page(PdfReader(overlay).pages[0])
    output = PdfWriter()
    output.add_page(page)
    output.add_metadata({"/Title": "SP-1 R2 synthetic graphic journey derivative"})
    with Path(__file__).with_name("sp1-new-r2-graphic.pdf").open("wb") as sink:
        output.write(sink)


if __name__ == "__main__":
    main()
