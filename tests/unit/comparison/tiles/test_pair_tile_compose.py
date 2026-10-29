"""The overlay's pixels (`CMP-VIEWER-01`): the darker of the two pages, the layers in solid colour, the hatch."""

from __future__ import annotations

import struct

import numpy
import pytest

from auditmanager.comparison.tiles.compose import (
    DRAW_ORDER,
    PALETTE_RGB,
    TileUnreadable,
    decode_png,
    encode_png,
    min_composite,
    paint_layers,
)


def _white(h: int = 20, w: int = 30):
    return numpy.full((h, w, 3), 255, dtype=numpy.uint8)


def test_where_the_pages_agree_the_ink_keeps_its_own_colour_and_either_pages_ink_shows() -> None:
    a, b = _white(), _white()
    a[2:4, 2:4] = (10, 20, 30)
    b[2:4, 2:4] = (10, 20, 30)
    a[10:12, 5:7] = 0
    b[14:16, 8:10] = 77
    out = min_composite(a, b)
    assert (out[2:4, 2:4] == (10, 20, 30)).all() and (out[10:12, 5:7] == 0).all() and (out[14:16, 8:10] == 77).all()
    assert (out == 255).all(axis=2).sum() == 20 * 30 - 4 - 4 - 4


def test_each_layer_is_painted_solid_with_its_own_colour_and_the_later_layer_wins() -> None:
    image = _white()
    masks = {name: numpy.zeros((20, 30), dtype=bool) for name in PALETTE_RGB}
    masks["light_elements"][5:10, 5:10] = True
    masks["main"][7:12, 7:12] = True
    paint_layers(image, masks, (0, 0))
    assert tuple(image[5, 5]) == PALETTE_RGB["light_elements"][::-1]  # BGR in the array
    assert tuple(image[8, 8]) == PALETTE_RGB["main"][::-1]  # main is above light_elements
    assert tuple(image[11, 11]) == PALETTE_RGB["main"][::-1]
    assert (image[0, 0] == 255).all()
    assert DRAW_ORDER[-1] == "main" and len(set(PALETTE_RGB.values())) == len(PALETTE_RGB)


def test_a_layer_that_is_not_selected_is_not_painted() -> None:
    image = _white()
    paint_layers(image, {"noise": numpy.ones((20, 30), dtype=bool)}, (0, 0))
    assert tuple(image[3, 3]) == PALETTE_RGB["noise"][::-1]
    other = _white()
    paint_layers(other, {}, (0, 0))
    assert (other == 255).all()


def test_the_service_zone_hatch_is_a_tint_on_stripes_and_runs_unbroken_across_a_tile_seam() -> None:
    zone = numpy.ones((24, 24), dtype=bool)
    whole = paint_layers(_white(24, 24), {"service_zones": zone}, (0, 0))
    left = paint_layers(_white(24, 12), {"service_zones": zone[:, :12]}, (0, 0))
    right = paint_layers(_white(24, 12), {"service_zones": zone[:, 12:]}, (12, 0))
    assert numpy.array_equal(numpy.hstack([left, right]), whole)
    tinted = (whole != 255).any(axis=2)
    assert 0.3 < tinted.mean() < 0.7  # stripes, not a fill
    assert tuple(whole[0, 0]) == (int(255 * 0.82 + 160 * 0.18), int(255 * 0.82 + 230 * 0.18), int(255 * 0.82 + 255 * 0.18))


def test_a_png_round_trips_and_a_stored_tile_that_is_not_one_is_refused() -> None:
    image = numpy.random.default_rng(1).integers(0, 255, (40, 50, 3), dtype=numpy.uint8)
    data = encode_png(image)
    assert data.startswith(b"\x89PNG\r\n\x1a\n") and numpy.array_equal(decode_png(data), image)
    for bad in (b"", b"GIF89a" + b"\0" * 40, data[:20], b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 513, 10) + b"\0" * 20,
                b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 0, 10) + b"\0" * 20, data[:-30]):
        with pytest.raises(TileUnreadable):
            decode_png(bad)
