"""An IMAGE block the run cannot cut is refused at the upload (`RUN-ROBUSTNESS-01`, D-159).

`R-121`: the geometry stage fails the *whole run* ``portal_block_degenerate`` on an IMAGE block
whose crop it cannot position on its page, and the owner kept that, registering a debt to move
the refusal to the upload "if such a block is ever met". Until then a version holding such a
block was accepted, immutable, and failed every run. Ingest now answers it with the bundle's
own ``blocks_json_invalid``.

Three things are shown, none with a database:

* the **restatement is the stage's rule**: ``crop_geometry.cannot_cut`` and ``page_agrees``
  answer exactly what ``analysis.geometry.maths.plan_crop`` and ``check_page`` answer, over a
  seeded sweep of boxes, pages and rasters and at every boundary the rule has -- ingest may not
  import ``analysis``, so a copy that drifted would otherwise go unseen;
* the **reader's page size is the stage's**: the displayed size and rotation
  ``pdf_reader`` reports are those ``PdfiumDocument.page_geometry`` reports, for a CropBox
  inside the MediaBox, a MediaBox that does not start at the origin, and every ``/Rotate``;
* the **bundle**: a sub-pixel IMAGE block is refused, one a hair above the bound is not, a
  block on a page whose box disagrees with the raster (which cuts no crop) is not, and the
  committed baseline is still admitted.
"""

from __future__ import annotations

import io
import json
import math
import random
import zipfile
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.geometry import maths
from auditmanager.analysis.geometry.render import PdfiumDocument
from auditmanager.ingest import crop_geometry
from auditmanager.ingest.envelope import inspect_pdf
from tests.integration.ingest.bundle_support import committed, judge


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


# ---------------------------------------------------------------------------------------
# The restatement is the stage's rule
# ---------------------------------------------------------------------------------------


def _stage_cannot_cut(bbox: tuple[float, ...], width_pt: float, height_pt: float, width_px: int) -> bool:
    try:
        maths.plan_crop(bbox, width_pt, height_pt, maths.base_scale(width_px, width_pt))
    except (maths.DegenerateCrop, ArithmeticError):
        return True
    return False


def _ingest_cannot_cut(bbox: tuple[float, ...], width_pt: float, height_pt: float, width_px: int) -> bool:
    return crop_geometry.cannot_cut(bbox, width_pt, height_pt, width_px)


def _box(rng: random.Random) -> tuple[float, float, float, float]:
    """A positive box in [0, 1] whose sides run from a hair to the whole page."""
    width = 10 ** rng.uniform(-9.5, 0)
    height = 10 ** rng.uniform(-9.5, 0)
    if rng.random() < 0.15:
        height = width
    x0 = rng.uniform(0, 1 - min(width, 1.0))
    y0 = rng.uniform(0, 1 - min(height, 1.0))
    return (x0, y0, min(1.0, x0 + width), min(1.0, y0 + height))


def test_cannot_cut_answers_what_plan_crop_answers_over_a_seeded_sweep() -> None:
    rng = random.Random(121)
    refused = accepted = 0
    for _ in range(25_000):
        bbox = _box(rng)
        width_pt = rng.choice([595.28, 841.89, 612.0, 792.0, 10 ** rng.uniform(0, 4.2), 14_400.0])
        height_pt = rng.choice([841.89, 595.28, 792.0, 10 ** rng.uniform(0, 4.2), 14_400.0])
        width_px = rng.choice([2480, 1000, 800, 1, 10 ** rng.randint(0, 9), rng.randint(1, 9000)])
        stage = _stage_cannot_cut(bbox, width_pt, height_pt, width_px)
        mine = _ingest_cannot_cut(bbox, width_pt, height_pt, width_px)
        assert mine == stage, (bbox, width_pt, height_pt, width_px, "stage", stage)
        refused += stage
        accepted += not stage
    # Both answers occur many times, so the sweep cannot agree by never reaching the rule.
    assert refused > 1_000 and accepted > 1_000, (refused, accepted)


def test_cannot_cut_agrees_on_the_boundary_of_the_degenerate_bound() -> None:
    """A box whose long side is `800 / 2**24` of the page's, to a part in a million either way."""
    width_pt, height_pt, width_px = 595.28, 841.89, 2480
    bound = maths.MIN_LONG_SIDE_PX / maths.MAX_CANVAS_SIDE
    seen = set()
    for factor in (0.5, 0.9, 0.99, 0.999, 0.99999, 0.999999, 1.0, 1.000001, 1.00001, 1.001, 1.01, 1.1, 2.0, 10.0):
        long_side_pt = bound * max(width_pt, height_pt) * factor
        # A box that is `long_side_pt` tall, as wide as it is tall in points.
        bbox = (0.4, 0.4, 0.4 + long_side_pt / width_pt, 0.4 + long_side_pt / height_pt)
        stage = _stage_cannot_cut(bbox, width_pt, height_pt, width_px)
        assert _ingest_cannot_cut(bbox, width_pt, height_pt, width_px) == stage, factor
        seen.add(stage)
    assert seen == {True, False}, "the sweep must cross the bound"


def test_cannot_cut_flips_at_the_very_same_box_as_plan_crop() -> None:
    """Found by bisection on the stage's own answer, then compared at a part in 10**12 either
    side: a restatement whose rounding differs by one step of the scale (``10**-6``, about
    5 * 10**-11 of a degenerate scale) is caught here and by no coarser sweep."""
    width_pt, height_pt, width_px = 595.28, 841.89, 2480
    bound = maths.MIN_LONG_SIDE_PX / maths.MAX_CANVAS_SIDE

    def box(factor: float) -> tuple[float, float, float, float]:
        long_side = bound * max(width_pt, height_pt) * factor
        return (0.4, 0.4, 0.4 + long_side / width_pt, 0.4 + long_side / height_pt)

    low, high = 0.5, 2.0  # cannot cut at `low`, can at `high`
    assert _stage_cannot_cut(box(low), width_pt, height_pt, width_px)
    assert not _stage_cannot_cut(box(high), width_pt, height_pt, width_px)
    for _ in range(200):
        middle = (low + high) / 2
        if _stage_cannot_cut(box(middle), width_pt, height_pt, width_px):
            low = middle
        else:
            high = middle
    flip = high
    seen = set()
    for step in range(-600, 601, 7):
        factor = flip * (1 + step * 1e-12)
        stage = _stage_cannot_cut(box(factor), width_pt, height_pt, width_px)
        assert _ingest_cannot_cut(box(factor), width_pt, height_pt, width_px) == stage, step
        seen.add(stage)
    assert seen == {True, False}, "the sample must straddle the flip"


@pytest.mark.parametrize(
    "bbox",
    [
        (0.0, 0.0, 5e-324, 5e-324),
        (0.0, 0.0, 1e-300, 1e-300),
        (0.5, 0.5, 0.5, 0.9),
        (0.5, 0.9, 0.9, 0.5),
        (-0.1, 0.0, 0.5, 0.5),
        (0.0, 0.0, 1.1, 0.5),
        (0.0, 0.0, math.nan, 0.5),
        (0.0, 0.0, 0.5),
        (0.0, 0.0, 1.0, 1.0),
        (0.0, 0.0, 1.0, 1e-9),
        (0.0, 0.0, 1e-9, 1.0),
    ],
)
def test_a_box_the_schema_would_have_refused_or_cannot_be_placed_is_the_stages_answer_too(
    bbox: tuple[float, ...],
) -> None:
    stage = _stage_cannot_cut(bbox, 595.28, 841.89, 2480)  # type: ignore[arg-type]
    assert _ingest_cannot_cut(bbox, 595.28, 841.89, 2480) == stage


def test_page_agrees_answers_what_check_page_answers() -> None:
    rng = random.Random(1210)
    verdicts = set()
    for _ in range(20_000):
        width_pt = rng.choice([595.28, 841.89, 612.0, 10 ** rng.uniform(-1, 4)])
        height_pt = rng.choice([841.89, 595.28, 792.0, 10 ** rng.uniform(-1, 4), 0.0, -3.0])
        ratio = width_pt / height_pt if height_pt > 0 else 1.0
        # Rasters at the page's own aspect, a hair either side of the tolerance, and wild ones.
        height_px = rng.choice([3508, 1000, rng.randint(1, 9000)])
        drift = rng.choice([1.0, 1.0 + maths.PAGE_BOX_TOLERANCE, 1.0 + maths.PAGE_BOX_TOLERANCE * 1.0001,
                            1.0 - maths.PAGE_BOX_TOLERANCE * 0.9999, 1.02, rng.uniform(0.5, 2.0)])
        width_px = max(1, round(height_px * ratio * drift))
        portal_rotation = rng.choice(maths.ROTATIONS)
        page_rotation = portal_rotation if rng.random() < 0.8 else rng.choice(maths.ROTATIONS)
        stage = maths.check_page(
            portal_width_px=width_px, portal_height_px=height_px, portal_rotation=portal_rotation,
            page_width_pt=width_pt, page_height_pt=height_pt, page_rotation=page_rotation,
        ) == maths.GEOMETRY_OK
        mine = crop_geometry.page_agrees(
            portal_width_px=width_px, portal_height_px=height_px, portal_rotation=portal_rotation,
            page_width_pt=width_pt, page_height_pt=height_pt, page_rotation=page_rotation,
        )
        assert mine == stage, (width_px, height_px, width_pt, height_pt, portal_rotation, page_rotation)
        verdicts.add(stage)
    assert verdicts == {True, False}


def test_the_restated_constants_are_the_stages() -> None:
    assert crop_geometry.MIN_LONG_SIDE_PX == maths.MIN_LONG_SIDE_PX
    assert crop_geometry.MAX_PIXELS == maths.MAX_PIXELS
    assert crop_geometry.PAGE_BOX_TOLERANCE == maths.PAGE_BOX_TOLERANCE
    assert crop_geometry.MAX_CANVAS_SIDE == maths.MAX_CANVAS_SIDE
    assert crop_geometry.SCALE_DIGITS == maths.SCALE_DIGITS


# ---------------------------------------------------------------------------------------
# The reader's page size is the stage's
# ---------------------------------------------------------------------------------------


def _page_pdf(boxes: str, rotate: int) -> bytes:
    """One page with the given ``/MediaBox`` ... ``/CropBox`` text and ``/Rotate``."""
    stream = b"BT /F1 12 Tf 72 700 Td (A line of text long enough to be a text layer) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            f"<< /Type /Page /Parent 2 0 R {boxes} /Rotate {rotate} "
            "/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>"
        ).encode(),
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


BOXES = {
    "a MediaBox alone": "/MediaBox [0 0 612 792]",
    "a CropBox inside the MediaBox": "/MediaBox [0 0 612 792] /CropBox [36 72 500 700]",
    "a CropBox that sticks out of the MediaBox": "/MediaBox [0 0 612 792] /CropBox [-50 -50 700 900]",
    "a MediaBox away from the origin": "/MediaBox [100 200 500 800]",
    "a MediaBox with swapped corners": "/MediaBox [612 792 0 0]",
    "a CropBox that misses the MediaBox": "/MediaBox [0 0 100 100] /CropBox [500 500 600 600]",
}


@pytest.mark.parametrize("rotate", [0, 90, 180, 270, 360, -90])
@pytest.mark.parametrize("label", sorted(BOXES))
def test_the_page_size_the_reader_reports_is_the_one_the_stage_reads(
    label: str, rotate: int, tmp_path: Path
) -> None:
    pdf = _page_pdf(BOXES[label], rotate)
    facts = inspect_pdf(pdf, require_text=False)
    path = tmp_path / "page.pdf"
    path.write_bytes(pdf)
    with PdfiumDocument(str(path), stage_id="probe") as document:
        stage = document.page_geometry(1)
    width, height, rotation = facts.page_geometry[0]
    assert (width, height, rotation) == (stage.width_pt, stage.height_pt, stage.rotation_deg), label


# ---------------------------------------------------------------------------------------
# The bundle
# ---------------------------------------------------------------------------------------


def _baseline() -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(committed("ar_baseline.zip"))) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _bundle_with(edit: Any) -> bytes:
    members = _baseline()
    name = next(n for n in members if n.endswith("_blocks.json"))
    document = json.loads(members[name])
    edit(document)
    members[name] = json.dumps(document).encode("utf-8")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for member, data in members.items():
            archive.writestr(member, data)
    return out.getvalue()


def _first_image(document: dict[str, Any]) -> dict[str, Any]:
    return next(b for b in document["blocks"] if b["block_type"] == "image")


def _shrink_first_image(document: dict[str, Any], long_side: float) -> None:
    """The first IMAGE block as a square-ish box whose long side is ``long_side`` of its page."""
    block = _first_image(document)
    page = document["pages"][block["page_index"]]
    width_pt, height_pt = 595.28, 841.89  # the baseline PDF's A4 pages
    assert abs(page["width_px"] / page["height_px"] - width_pt / height_pt) < 0.005
    block["coords_norm"] = [0.4, 0.4, 0.4 + long_side, 0.4 + long_side * width_pt / height_pt]


BOUND = maths.MIN_LONG_SIDE_PX / maths.MAX_CANVAS_SIDE


def test_the_committed_baseline_is_still_admitted() -> None:
    assert judge(committed("ar_baseline.zip"))[:2] == (None, None)


def test_a_subpixel_image_block_is_refused_at_the_upload() -> None:
    """A long side of a hundredth of the bound: the stage would fail every run on it."""
    found = judge(_bundle_with(lambda d: _shrink_first_image(d, BOUND / 100)))
    assert found[:2] == ("file", "blocks_json_invalid")


def test_the_refusal_says_what_cannot_be_cut_and_echoes_nothing_the_caller_wrote() -> None:
    from auditmanager.ingest.bundle_archive import extract_bundle
    from auditmanager.ingest.bundle_envelope import admit_bundle
    from auditmanager.shared.errors import DomainError

    data = _bundle_with(lambda d: _shrink_first_image(d, BOUND / 100))
    with pytest.raises(DomainError) as refused:
        with extract_bundle(io.BytesIO(data)) as bundle:
            admit_bundle(bundle)
    assert "cannot be placed" in str(refused.value)
    assert dict(refused.value.detail_fields) == {"field": "file", "constraint": "blocks_json_invalid"}


def test_the_stage_would_have_failed_the_run_on_the_block_ingest_refuses() -> None:
    """The same box and page through the stage's own arithmetic: ``DegenerateCrop``."""
    with pytest.raises(maths.DegenerateCrop):
        width_pt, height_pt = 595.28, 841.89
        long_side = BOUND / 100
        maths.plan_crop(
            (0.4, 0.4, 0.4 + long_side, 0.4 + long_side * width_pt / height_pt),
            width_pt, height_pt, maths.base_scale(2480, width_pt),
        )


def test_a_block_a_hair_above_the_bound_is_cut_and_so_admitted() -> None:
    found = judge(_bundle_with(lambda d: _shrink_first_image(d, BOUND * 1.5)))
    assert found[:2] == (None, None)


def test_a_block_that_is_tiny_on_a_page_that_cuts_no_crop_is_admitted() -> None:
    """A page whose box disagrees with the raster is marked and cut nowhere (`W55B-GEOMETRY-01`),
    so a sub-pixel block on it cannot fail the run."""

    def edit(document: dict[str, Any]) -> None:
        _shrink_first_image(document, BOUND / 100)
        block = _first_image(document)
        document["pages"][block["page_index"]]["width_px"] = 1000  # a different aspect

    assert judge(_bundle_with(edit))[:2] == (None, None)


def test_only_an_image_block_is_judged() -> None:
    """A TEXT or STAMP block of the same size is never cut."""

    def edit(document: dict[str, Any]) -> None:
        block = next(b for b in document["blocks"] if b["block_type"] == "text")
        block["coords_norm"] = [0.4, 0.4, 0.4 + BOUND / 100, 0.4 + BOUND / 100]

    assert judge(_bundle_with(edit))[:2] == (None, None)


def test_a_raster_so_large_that_the_stages_page_check_overflows_is_refused() -> None:
    """``check_page`` divides the raster's sides: past a float the stage fails the run on the
    page, with no block on it at all."""

    def edit(document: dict[str, Any]) -> None:
        document["pages"][0]["width_px"] = 10**400

    with pytest.raises(OverflowError):
        maths.check_page(
            portal_width_px=10**400, portal_height_px=3508, portal_rotation=0,
            page_width_pt=595.28, page_height_pt=841.89, page_rotation=0,
        )
    assert judge(_bundle_with(edit))[:2] == ("file", "blocks_json_invalid")
