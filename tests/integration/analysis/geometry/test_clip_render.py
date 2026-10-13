"""The clip render (`W55B-GEOMETRY-01`): PDFium on generated pages, no store.

* **Rotation, end to end.** For each ``/Rotate`` of 0, 90, 180 and 270 (and a CropBox that is
  not the MediaBox) a red rectangle is drawn at known user-space coordinates; the independent
  oracle (``geometry_support.displayed_rect``) says where it is displayed; that box, as
  ``bbox_norm``, is planned and rendered; the red pixels of the crop must land where the oracle
  put the rectangle, to a pixel.
* **A clip, not a page.** The bitmap PDFium is given is the crop's size; the crop equals the
  same region of a whole-page render at the same scale, pixel for pixel.
* **The budget,** measured on the decoded PNG: long side >= 800, pixels <= 4 000 000.
* **PNG:** the signature, Pillow decodes it, and two renders in one environment give the same
  bytes (never a recorded crop: bytes are stable within one environment only).
* **The lock:** ``PDFIUM_LOCK`` is held during every PDFium render and released between two
  crops -- another thread acquires it there.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

import auditmanager.ingest.envelope as ingest_envelope
from auditmanager.analysis.geometry import render as render_module
from auditmanager.analysis.geometry.crops import PNG_SIGNATURE, encode_png
from auditmanager.analysis.geometry.maths import MAX_PIXELS, MIN_LONG_SIDE_PX, plan_crop
from auditmanager.analysis.geometry.render import PdfiumDocument
from tests.integration.analysis.geometry.geometry_support import (
    BLUE,
    GREEN,
    RED,
    PageSpec,
    Rect,
    decode_png,
    displayed_rect,
    displayed_size,
    grown,
    make_pdf,
    normalised,
)

SQUARE = Rect(50.0, 250.0, 100.0, 80.0, RED)
DECOYS = (Rect(400.0, 40.0, 90.0, 60.0, BLUE), Rect(300.0, 300.0, 50.0, 50.0, GREEN))

PAGES = [
    PageSpec(600.0, 400.0, 0, (SQUARE, *DECOYS)),
    PageSpec(600.0, 400.0, 90, (SQUARE, *DECOYS)),
    PageSpec(600.0, 400.0, 180, (SQUARE, *DECOYS)),
    PageSpec(600.0, 400.0, 270, (SQUARE, *DECOYS)),
    PageSpec(600.0, 400.0, 90, (SQUARE, *DECOYS), cropbox=(20.0, 10.0, 580.0, 380.0)),
]
LABELS = ["rotate-0", "rotate-90", "rotate-180", "rotate-270", "rotate-90-cropbox"]


@pytest.fixture(scope="module")
def pdf_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("geometry") / "rotations.pdf"
    path.write_bytes(make_pdf(PAGES))
    return str(path)


def _red_box(image: Any) -> tuple[int, int, int, int] | None:
    """The bounding box of the strongly red pixels, ``(left, top, right, bottom)``."""
    rgb = image.convert("RGB")
    pixels = rgb.load()
    found = [(x, y) for y in range(rgb.height) for x in range(rgb.width)
             if pixels[x, y][0] > 200 and pixels[x, y][1] < 60 and pixels[x, y][2] < 60]
    if not found:
        return None
    xs = [p[0] for p in found]
    ys = [p[1] for p in found]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def test_the_lock_is_ingests_one_pdfium_lock() -> None:
    assert render_module.pdfium_lock() is ingest_envelope.PDFIUM_LOCK


def test_the_renderer_is_named_with_the_installed_version() -> None:
    from importlib.metadata import version

    assert render_module.renderer_name() == f"pypdfium2 {version('pypdfium2')}"


@pytest.mark.parametrize("index", range(len(PAGES)), ids=LABELS)
def test_the_displayed_page_is_the_oracles_and_pdfiums_own(pdf_path, index) -> None:
    import pypdfium2 as pdfium

    with PdfiumDocument(pdf_path, stage_id="test") as pdf:
        geometry = pdf.page_geometry(index + 1)
    assert (geometry.width_pt, geometry.height_pt) == pytest.approx(displayed_size(PAGES[index]))
    assert geometry.rotation_deg == PAGES[index].rotate
    with ingest_envelope.PDFIUM_LOCK:
        document = pdfium.PdfDocument(pdf_path)
        try:
            page = document[index]
            try:
                assert page.get_size() == pytest.approx((geometry.width_pt, geometry.height_pt))
            finally:
                page.close()
        finally:
            document.close()


@pytest.mark.parametrize("index", range(len(PAGES)), ids=LABELS)
def test_each_rotation_cuts_the_rectangle_the_oracle_displays(pdf_path, index) -> None:
    page = PAGES[index]
    target = normalised(page, displayed_rect(page, SQUARE))
    box = tuple(grown(target, 0.02))
    with PdfiumDocument(pdf_path, stage_id="test") as pdf:
        geometry = pdf.page_geometry(index + 1)
        plan = plan_crop(box, geometry.width_pt, geometry.height_pt, 2.0)
        image = pdf.render(index + 1, plan)
    red = _red_box(image)
    assert red is not None, "the crop does not hold the rectangle"
    # back to displayed points: the crop's pixels plus its origin, over the scale per axis
    sx = plan.canvas_width / geometry.width_pt
    sy = plan.canvas_height / geometry.height_pt
    measured = ((plan.left + red[0]) / sx, (plan.top + red[1]) / sy,
                (plan.left + red[2]) / sx, (plan.top + red[3]) / sy)
    expected = displayed_rect(page, SQUARE)
    assert measured == pytest.approx(expected, abs=1.5 / min(sx, sy)), (measured, expected)
    # nothing else of the page is in the crop: its border is white
    rgb = image.convert("RGB")
    corners = [rgb.getpixel((0, 0)), rgb.getpixel((rgb.width - 1, rgb.height - 1))]
    assert corners == [(255, 255, 255), (255, 255, 255)]


def test_a_box_where_a_wrong_rotation_would_put_the_rectangle_holds_no_red(pdf_path) -> None:
    """The rotated page's rectangle is not where an unrotated reading would place it."""
    rotated = PAGES[1]
    unrotated = PageSpec(rotated.width, rotated.height, 0, rotated.rects)
    wrong = normalised(unrotated, displayed_rect(unrotated, SQUARE))
    with PdfiumDocument(pdf_path, stage_id="test") as pdf:
        geometry = pdf.page_geometry(2)
        # the unrotated box in the rotated page's normalised space, clipped to it
        box = (wrong[0], wrong[1], min(wrong[2], 1.0), min(wrong[3], 1.0))
        image = pdf.render(2, plan_crop(box, geometry.width_pt, geometry.height_pt, 2.0))
    assert _red_box(image) is None


def test_the_bitmap_is_the_clip_and_never_the_page(pdf_path, monkeypatch) -> None:
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_raw

    sizes: list[tuple[int, int]] = []
    canvases: list[tuple[int, int, int, int]] = []
    original_new = pdfium.PdfBitmap.new_native
    original_render = pdfium_raw.FPDF_RenderPageBitmap

    def new_native(width, height, *args, **kwargs):
        sizes.append((width, height))
        return original_new(width, height, *args, **kwargs)

    def render(bitmap, page, start_x, start_y, size_x, size_y, rotate, flags):
        canvases.append((start_x, start_y, size_x, size_y))
        return original_render(bitmap, page, start_x, start_y, size_x, size_y, rotate, flags)

    monkeypatch.setattr(pdfium.PdfBitmap, "new_native", staticmethod(new_native))
    monkeypatch.setattr(pdfium_raw, "FPDF_RenderPageBitmap", render)
    box = (0.25, 0.25, 0.5, 0.5)
    with PdfiumDocument(pdf_path, stage_id="test") as pdf:
        geometry = pdf.page_geometry(1)
        plan = plan_crop(box, geometry.width_pt, geometry.height_pt, 3.0)
        image = pdf.render(1, plan)
    assert sizes == [(plan.width, plan.height)], "one bitmap, of the clip's size"
    assert (plan.width, plan.height) != (plan.canvas_width, plan.canvas_height)
    assert plan.width * plan.height < plan.canvas_width * plan.canvas_height / 10
    assert canvases == [(-plan.left, -plan.top, plan.canvas_width, plan.canvas_height)]
    assert image.size == (plan.width, plan.height)


def test_the_clip_equals_the_same_region_of_a_whole_page_render(tmp_path) -> None:
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_raw
    from PIL import ImageChops

    shapes = PageSpec(612.0, 792.0, 90, (SQUARE, *DECOYS, Rect(10.0, 600.0, 580.0, 30.0, BLUE)), text=None)
    path = tmp_path / "shapes.pdf"
    path.write_bytes(make_pdf([shapes]))
    box = (0.1, 0.05, 0.7, 0.45)
    with PdfiumDocument(str(path), stage_id="test") as pdf:
        geometry = pdf.page_geometry(1)
        plan = plan_crop(box, geometry.width_pt, geometry.height_pt, 1.7)
        clip = pdf.render(1, plan)
    with ingest_envelope.PDFIUM_LOCK:
        document = pdfium.PdfDocument(str(path))
        page = document[0]
        bitmap = pdfium.PdfBitmap.new_native(
            plan.canvas_width, plan.canvas_height, pdfium_raw.FPDFBitmap_BGR
        )
        bitmap.fill_rect((255, 255, 255, 255), 0, 0, plan.canvas_width, plan.canvas_height)
        pdfium_raw.FPDF_RenderPageBitmap(
            bitmap, page, 0, 0, plan.canvas_width, plan.canvas_height, 0, pdfium_raw.FPDF_ANNOT
        )
        whole = bitmap.to_pil().copy()
        bitmap.close()
        page.close()
        document.close()
    region = whole.crop((plan.left, plan.top, plan.left + plan.width, plan.top + plan.height))
    assert ImageChops.difference(clip.convert("RGB"), region.convert("RGB")).getbbox() is None


@pytest.mark.parametrize(
    ("box", "base", "bound"),
    [
        ((0.45, 0.45, 0.5, 0.48), 1.0, "floor"),          # a small block, raised to 800 px
        ((0.0, 0.0, 1.0, 1.0), 600 / 72, "cap"),           # a whole A1 sheet at 600 dpi
    ],
)
def test_the_decoded_png_meets_the_budget(tmp_path, box, base, bound) -> None:
    path = tmp_path / "a1.pdf"
    path.write_bytes(make_pdf([PageSpec(2384.0, 1684.0, 0, (Rect(100.0, 100.0, 2000.0, 1400.0, BLUE),))]))
    with PdfiumDocument(str(path), stage_id="test") as pdf:
        geometry = pdf.page_geometry(1)
        plan = plan_crop(box, geometry.width_pt, geometry.height_pt, base)
        png = encode_png(pdf.render(1, plan))
    assert png.startswith(PNG_SIGNATURE)
    image = decode_png(png)
    assert image.format == "PNG" and image.mode == "RGB"
    assert image.size == (plan.width, plan.height)
    assert max(image.size) >= MIN_LONG_SIDE_PX
    assert image.size[0] * image.size[1] <= MAX_PIXELS
    if bound == "floor":
        assert max(image.size) <= MIN_LONG_SIDE_PX + 2
    else:
        assert image.size[0] * image.size[1] >= MAX_PIXELS * 0.99


def test_two_renders_in_one_environment_give_the_same_png_bytes(pdf_path) -> None:
    box = (0.05, 0.05, 0.6, 0.7)
    outputs = []
    for _ in range(2):
        with PdfiumDocument(pdf_path, stage_id="test") as pdf:
            geometry = pdf.page_geometry(2)
            outputs.append(encode_png(pdf.render(2, plan_crop(box, geometry.width_pt, geometry.height_pt, 2.0))))
    assert outputs[0] == outputs[1]
    assert decode_png(outputs[0]).info.get("dpi") is None, "no metadata chunk is written"


# -- the lock --------------------------------------------------------------------------------


class _ProbedLock:
    """The real lock; each time it is released, another thread must be able to take it."""

    def __init__(self, real: threading.Lock, events: list[Any]) -> None:
        self._real = real
        self._events = events

    def acquire(self, *args: Any, **kwargs: Any) -> bool:
        return self._real.acquire(*args, **kwargs)

    def release(self) -> None:
        self._real.release()

    def __enter__(self) -> "_ProbedLock":
        self._real.acquire()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._real.release()
        taken: list[bool] = []

        def probe() -> None:
            got = self._real.acquire(timeout=5)
            taken.append(got)
            if got:
                self._real.release()

        thread = threading.Thread(target=probe)
        thread.start()
        thread.join()
        self._events.append(("probe", taken == [True]))


def test_the_lock_is_held_during_every_render_and_another_thread_takes_it_between_crops(
    pdf_path, monkeypatch
) -> None:
    import pypdfium2.raw as pdfium_raw

    events: list[Any] = []
    original = pdfium_raw.FPDF_RenderPageBitmap

    def render(*args: Any) -> Any:
        events.append(("render", ingest_envelope.PDFIUM_LOCK.locked()))
        return original(*args)

    monkeypatch.setattr(pdfium_raw, "FPDF_RenderPageBitmap", render)
    monkeypatch.setattr(
        render_module, "pdfium_lock", lambda: _ProbedLock(ingest_envelope.PDFIUM_LOCK, events)
    )
    failures: list[BaseException] = []

    def two_crops() -> None:
        try:
            with PdfiumDocument(pdf_path, stage_id="test") as pdf:
                for page_number in (1, 3):
                    geometry = pdf.page_geometry(page_number)
                    pdf.render(page_number, plan_crop((0.1, 0.1, 0.4, 0.4), geometry.width_pt, geometry.height_pt, 2.0))
        except BaseException as exc:  # noqa: BLE001 - reported below
            failures.append(exc)

    worker = threading.Thread(target=two_crops, daemon=True)
    worker.start()
    worker.join(timeout=60)
    assert not worker.is_alive(), "the renders never finished: the lock was not released"
    assert failures == []
    renders = [i for i, event in enumerate(events) if event[0] == "render"]
    assert len(renders) == 2
    assert all(events[i][1] for i in renders), "PDFIUM_LOCK must be held while PDFium renders"
    between = events[renders[0] + 1 : renders[1]]
    assert ("probe", True) in between, "another thread could not take the lock between two crops"
    assert all(ok for kind, ok in events if kind == "probe")
    assert not ingest_envelope.PDFIUM_LOCK.locked()


def test_the_document_is_opened_from_the_path_it_is_given(pdf_path, monkeypatch) -> None:
    import pypdfium2 as pdfium

    opened: list[Any] = []
    original = pdfium.PdfDocument

    def document(source: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(source)
        return original(source, *args, **kwargs)

    monkeypatch.setattr(pdfium, "PdfDocument", document)
    with PdfiumDocument(pdf_path, stage_id="test") as pdf:
        assert pdf.page_count == len(PAGES)
    assert opened == [pdf_path]
    assert isinstance(opened[0], str) and Path(opened[0]).is_file()
