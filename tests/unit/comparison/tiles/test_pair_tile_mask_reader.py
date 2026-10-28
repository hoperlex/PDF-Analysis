"""The mask reader refuses what it must and reads what the brief's text writes (`CMP-VIEWER-01`, ADR-0025 decision 9)."""

from __future__ import annotations

import struct
import zlib

import numpy
import pytest
from auditmanager.comparison.tiles.limits import MAX_PLANE_PIXELS
from auditmanager.comparison.tiles.mask import LAYER_NAMES, MaskRefused, read_mask


def test_a_blob_written_per_the_brief_reads_back_plane_for_plane(support) -> None:
    rng = numpy.random.default_rng(3)
    planes = rng.random((8, 37, 61)) < 0.1
    mask = read_mask(support.mask_blob(planes))
    assert (mask.width_px, mask.height_px, mask.row_bytes) == (61, 37, 8)
    assert mask.data.shape == (8, 37, 8)
    unpacked = numpy.unpackbits(mask.data, axis=-1, bitorder="big")[:, :, :61].astype(bool)
    assert numpy.array_equal(unpacked, planes)


def test_the_planes_are_in_the_order_of_the_layer_enum(support) -> None:
    assert LAYER_NAMES == ("main", "light_elements", "color_change", "line_style", "moved", "within_tolerance",
                           "noise", "service_zones")
    planes = support.planes_with(16, 4, {"noise": [(3, 2)]})
    mask = read_mask(support.mask_blob(planes))
    assert mask.plane("noise")[2, 0] == 0b00010000 and not mask.plane("main").any()


def test_the_reserved_field_is_not_read(support) -> None:
    assert read_mask(support.mask_blob(support.planes_with(8, 1, {}), reserved=7)).width_px == 8


@pytest.mark.parametrize("case", ["short_header", "magic", "format", "layer_count", "zero_width", "zero_height"])
def test_a_wrong_header_is_refused(support, case: str) -> None:
    blobs = {
        "short_header": (b"AMCM", "short_header"),
        "magic": (support.mask_blob(support.planes_with(8, 1, {}), magic=b"XMCM"), "magic"),
        "format": (support.mask_blob(support.planes_with(8, 1, {}), fmt=2), "format"),
        "layer_count": (support.mask_blob(support.planes_with(8, 1, {}), layers=7), "layer_count"),
        "zero_width": (struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 0, 5) + zlib.compress(b""), "empty_plane"),
        "zero_height": (struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 5, 0) + zlib.compress(b""), "empty_plane"),
    }
    blob, reason = blobs[case]
    with pytest.raises(MaskRefused) as refused:
        read_mask(blob)
    assert refused.value.reason == reason


def test_a_plane_over_forty_megapixels_is_refused_before_anything_is_inflated(support) -> None:
    assert MAX_PLANE_PIXELS == 40_000_000  # ADR-0025 decision 9, written out so a changed cap is a changed test
    side = 6325  # 6325 x 6325 = 40 005 625 pixels, 5 625 over the cap
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, side, side)
    # A deflate stream that would inflate to far more than it declares: never touched, the cap answers first.
    with pytest.raises(MaskRefused) as refused:
        read_mask(header + zlib.compress(b"\0" * 1000))
    assert refused.value.reason == "plane_over_cap"
    exactly = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 8000, 5000)  # 40 Mpx: allowed by the cap
    with pytest.raises(MaskRefused) as refused:
        read_mask(exactly + zlib.compress(b"\0" * 10))
    assert refused.value.reason == "length"


def test_a_body_that_inflates_to_more_or_less_than_declared_is_refused(support) -> None:
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 4)
    expected = 8 * 4 * 2
    for size in (expected - 1, expected + 1, expected * 100):
        with pytest.raises(MaskRefused) as refused:
            read_mask(header + zlib.compress(b"\0" * size))
        assert refused.value.reason == "length", size
    assert read_mask(header + zlib.compress(b"\0" * expected)).data.shape == (8, 4, 2)


def test_the_inflation_is_limited_a_small_blob_cannot_become_a_large_buffer(support) -> None:
    """A stored body that expands a thousandfold is stopped at the declared length plus one byte."""
    bomb = zlib.compress(b"\0" * (64 * 1024 * 1024), 9)
    assert len(bomb) < 100_000
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 4)
    with pytest.raises(MaskRefused) as refused:
        read_mask(header + bomb)
    assert refused.value.reason == "length"


def test_trailing_bytes_after_the_stream_and_a_stream_that_is_not_deflate_are_refused(support) -> None:
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 4)
    good = zlib.compress(b"\0" * 64)
    with pytest.raises(MaskRefused):
        read_mask(header + good + b"trailing")
    with pytest.raises(MaskRefused) as refused:
        read_mask(header + b"not a deflate stream at all")
    assert refused.value.reason == "not_deflate"
    with pytest.raises(MaskRefused):
        read_mask(header + good[:-6])  # truncated
