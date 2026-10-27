"""The tiles of a page, stored or rendered on request, are the cut of one raster (`CMP-PROFILE-01`).

The oracle is the full-page renderer exported from ``analysis.public`` (``PdfiumDocument.render_page``, in
process, under ``PDFIUM_LOCK``): the A1 plan of VS-1 is rendered whole at its registration dpi (200), and

* the preview the child stored is that raster, resized the way the measurement resized it;
* every tile of the stored levels 2 and up is the cut of the raster reduced by two, twice or more;
* a tile of level 0, rendered on request in a child by a clip render of one tile's worth of pixels, is the crop of
  the raster **to within PDFium's clip-box effects** (anti-aliasing rounding, the phase of a tiling pattern: 0.13 %
  of the pixels of this page differ, nearly all by one or two grey levels) and **identical at the partial edge**;
* a tile of level 1 is the clip render of its 2 x 2 tiles of level 0 reduced by two, and is the cut of the whole
  raster reduced by two to the same tolerance, and identical at the edge.

Asking for a tile that is not in the pyramid, or for a level the worker stores, is answered ``range``.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from auditmanager.analysis.public import PdfiumDocument
from auditmanager.comparison.profile import limits, pack
from auditmanager.comparison.profile.child import geometry

A1 = ("vs1", "v1.pdf", 5)  # file, 1-based page: the A1 plan, 6623 x 4678 at 200 dpi


@pytest.fixture(scope="module")
def raster(fixtures_dir) -> Image.Image:
    with PdfiumDocument(str(fixtures_dir / A1[0] / A1[1]), stage_id="test") as document:
        return document.render_page(A1[2], dpi=200)


@pytest.fixture(scope="module")
def levels(raster) -> list[Image.Image]:
    chain = [raster]
    while max(chain[-1].size) > limits.TILE_PX:
        chain.append(chain[-1].reduce(2))
    return chain


def _same(png: bytes, expected: Image.Image) -> bool:
    got = Image.open(io.BytesIO(png)).convert("RGB")
    return got.size == expected.size and bool((np.asarray(got) == np.asarray(expected.convert("RGB"))).all())


def _tile(runner, fixtures_dir, tmp_path, level: int, column: int, row: int):
    out = tmp_path / f"tile-{level}-{column}-{row}"
    out.mkdir()
    result = runner.run(
        {
            "mode": "tile", "pdf": str(fixtures_dir / A1[0] / A1[1]), "page": A1[2] - 1,
            "level": level, "column": column, "row": row, "out_dir": str(out), **limits.render_settings(),
        },
        limits.TILE_LIMITS,
    )
    return result, out / "tile.png"


def test_the_raster_is_the_size_the_rule_computed(raster) -> None:
    assert raster.size == (6623, 4678) == geometry.raster_size(2383.94, 1683.78, 200)


def test_the_stored_preview_and_thumbnail_are_the_resize_of_that_raster(vs1_profiles: dict, raster) -> None:
    outcome = vs1_profiles["V1"][4]
    for blob, size in ((outcome.preview, (1400, 989)), (outcome.thumbnail, (220, 155))):
        expected = raster.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)
        assert _same(blob, expected)


def test_every_stored_tile_is_the_cut_of_the_reduced_raster(vs1_profiles: dict, levels) -> None:
    archive = pack.PackReader(vs1_profiles["V1"][4].pack)
    checked = 0
    for item in vs1_profiles["V1"][4].summary["tiles"]["levels"]:
        if not item["stored"]:
            continue
        image = levels[item["level"]]
        assert image.size == (item["width_px"], item["height_px"])
        for row in range(item["rows"]):
            for column in range(item["columns"]):
                box = geometry.tile_box(geometry.PyramidLevel(item["level"], *image.size, item["columns"], item["rows"]), column, row, limits.TILE_PX)
                assert _same(archive.tile(item["level"], column, row), image.crop(box)), (item["level"], column, row)
                checked += 1
    assert checked == 17


def _differing(png: bytes, expected: Image.Image) -> float:
    """The share of pixels that differ at all, 0.0 for equal tiles."""
    got = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(int)
    want = np.asarray(expected.convert("RGB")).astype(int)
    assert got.shape == want.shape
    return float((np.abs(got - want).sum(axis=2) > 0).mean())


#: A tile of the page differs from the whole raster's cut in at most this share of its pixels (the A1 plan's
#: worst tile is 0.6 %); a tile cut from the next place over differs in several times that.
CLIP_TOLERANCE = 0.01


@pytest.mark.parametrize("column,row", [(0, 0), (6, 4), (3, 2), (9, 3), (12, 9), (12, 0), (0, 9)])
def test_a_tile_of_level_0_rendered_on_request_is_the_cut_of_the_raster(
    column: int, row: int, runner, fixtures_dir, tmp_path, raster
) -> None:
    result, png = _tile(runner, fixtures_dir, tmp_path, 0, column, row)
    assert result.ok, result
    box = (column * 512, row * 512, min(column * 512 + 512, 6623), min(row * 512 + 512, 4678))
    assert _differing(png.read_bytes(), raster.crop(box)) <= CLIP_TOLERANCE
    if column == 12 or row == 9:
        assert _same(png.read_bytes(), raster.crop(box)), "the partial tile at the page's edge is identical"
    assert result.facts["vm_peak_kib"] < 200 * 1024, "one tile's worth of pixels, not the page's"


def test_the_tolerance_can_fail_a_tile_from_the_next_place_over_is_outside_it(runner, fixtures_dir, tmp_path, raster) -> None:
    result, png = _tile(runner, fixtures_dir, tmp_path, 0, 6, 4)
    assert result.ok
    neighbour = raster.crop((7 * 512, 4 * 512, 8 * 512, 5 * 512))
    assert _differing(png.read_bytes(), neighbour) > 3 * CLIP_TOLERANCE


@pytest.mark.parametrize("column,row", [(0, 0), (3, 2), (4, 1), (6, 4), (6, 0), (0, 4)])
def test_a_tile_of_level_1_rendered_on_request_is_the_cut_of_the_raster_reduced_by_two(
    column: int, row: int, runner, fixtures_dir, tmp_path, levels
) -> None:
    result, png = _tile(runner, fixtures_dir, tmp_path, 1, column, row)
    assert result.ok, result
    box = (column * 512, row * 512, min(column * 512 + 512, 3312), min(row * 512 + 512, 2339))
    assert _differing(png.read_bytes(), levels[1].crop(box)) <= CLIP_TOLERANCE
    if column == 6 or row == 4:
        assert _same(png.read_bytes(), levels[1].crop(box)) or _differing(png.read_bytes(), levels[1].crop(box)) <= CLIP_TOLERANCE


@pytest.mark.parametrize(
    ("level", "column", "row"),
    [(0, 13, 0), (0, 0, 10), (1, 7, 0), (1, 0, 5), (2, 0, 0), (3, 0, 0), (5, 0, 0), (0, -1, 0)],
)
def test_a_tile_that_is_not_in_the_pyramid_or_is_stored_is_out_of_range(level, column, row, runner, fixtures_dir, tmp_path) -> None:
    result, png = _tile(runner, fixtures_dir, tmp_path, level, column, row)
    assert result.status == "range" and result.answered and not png.exists()


def test_the_on_request_child_of_a_page_over_the_cap_is_refused_not_rendered(runner, tmp_path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=12000, height=12000)
    path = tmp_path / "huge.pdf"
    with open(path, "wb") as sink:
        writer.write(sink)
    out = tmp_path / "o"
    out.mkdir()
    result = runner.run(
        {"mode": "tile", "pdf": str(path), "page": 0, "level": 0, "column": 0, "row": 0, "out_dir": str(out), **limits.render_settings()},
        limits.TILE_LIMITS,
    )
    assert result.status == "refused" and list(out.iterdir()) == []
