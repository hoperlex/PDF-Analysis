"""`M7-NORM-PNG`: the renderer of one norm page and the rules of its service that need no database.

A PNG is judged by its header bytes and its size; the picture is never opened.
"""

from __future__ import annotations

import io
import struct

import pytest
from PIL import Image, ImageDraw

from auditmanager.norms.page_images import (
    CROP_ID_PREFIX,
    MAX_IMAGES_PER_TASK,
    MAX_PARAGRAPHS_EXAMINED,
    RENDER_DPI,
    RENDER_PROFILE,
    NormPageImage,
    NormPageImages,
    NormPageRender,
    PageImageSelection,
    PageRenderRefused,
    render_pdf_page,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _pdf(*, pages: int = 1, size=(420, 594)) -> bytes:
    images = []
    for page in range(pages):
        image = Image.new("RGB", size, "white")
        ImageDraw.Draw(image).rectangle((20, 30 + page, 200, 120), fill="black")
        images.append(image)
    buffer = io.BytesIO()
    images[0].save(buffer, format="PDF", save_all=pages > 1, append_images=images[1:], resolution=72.0)
    return buffer.getvalue()


def _ihdr(png: bytes) -> tuple[int, int]:
    assert png[12:16] == b"IHDR"
    return struct.unpack(">II", png[16:24])


def test_the_profile_is_the_one_the_migration_comment_names_and_the_limits_are_the_plans():
    assert RENDER_PROFILE == "png-150dpi-v1" and RENDER_DPI == 150
    assert MAX_IMAGES_PER_TASK == 2 and MAX_PARAGRAPHS_EXAMINED == 12 and CROP_ID_PREFIX == "norm."


def test_one_page_becomes_a_png_at_150_dpi():
    rendered = render_pdf_page(_pdf())
    assert rendered.png.startswith(PNG_SIGNATURE) and len(rendered.png) > 100
    # 420 x 594 pt at 150 dpi is about 875 x 1237 px (PDFium rounds each side up; Pillow writes the MediaBox a hair wider)
    assert _ihdr(rendered.png) == (rendered.width_px, rendered.height_px)
    assert 874 <= rendered.width_px <= 877 and 1236 <= rendered.height_px <= 1239


def test_a_source_of_two_pages_is_refused_and_not_cut_to_the_first():
    with pytest.raises(PageRenderRefused) as refused:
        render_pdf_page(_pdf(pages=2))
    assert refused.value.reason == "source_not_one_page"


def test_bytes_that_are_not_a_pdf_are_refused_with_a_fixed_reason():
    with pytest.raises(PageRenderRefused) as refused:
        render_pdf_page(b"%PDF-1.7\nnot a document\n")
    assert refused.value.reason == "source_unreadable"


def test_a_page_over_the_pixel_cap_is_refused_and_not_rendered_smaller():
    with pytest.raises(PageRenderRefused) as refused:
        render_pdf_page(_pdf(), max_pixels=1000)
    assert refused.value.reason == "page_too_large"
    # the same page under the product's cap is drawn: the refusal is the cap's, not the page's
    assert render_pdf_page(_pdf()).png.startswith(PNG_SIGNATURE)


def test_the_temporary_file_is_removed_whatever_happened(tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    render_pdf_page(_pdf())
    with pytest.raises(PageRenderRefused):
        render_pdf_page(b"%PDF-1.7\nnot a document\n")
    with pytest.raises(PageRenderRefused):
        render_pdf_page(_pdf(pages=2))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("limit", [-1, 3, 8, True, 1.0, "2", None])
def test_a_limit_the_service_does_not_allow_is_refused_before_anything_is_read(limit):
    service = NormPageImages(store=None, session_factory=None)  # nothing is touched: the refusal comes first
    with pytest.raises(ValueError, match="norm_page_image_limit_invalid"):
        service.select([], limit=limit)


def test_the_crop_id_is_the_custody_binding_behind_the_prefix():
    render = NormPageRender(norm_custody_binding_id="nbd_01HZZZZZZZZZZZZZZZZZZZZZZ1", render_profile=RENDER_PROFILE, blob_id="blob_x",
        sha256="0" * 64, size_bytes=1, media_type="image/png", width_px=1, height_px=1)
    image = NormPageImage(render=render, paragraph_ids=("npar_a", "npar_b"), data=b"")
    assert render.crop_id == image.crop_id == "norm.nbd_01HZZZZZZZZZZZZZZZZZZZZZZ1"
    assert PageImageSelection(images=(image,)).paragraph_ids == {"npar_a", "npar_b"}
