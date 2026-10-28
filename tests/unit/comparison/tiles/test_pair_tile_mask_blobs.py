"""The masks the tile path reads (`CMP-VIEWER-01`, ADR-0025 decision 9).

The codec is the engine's (`comparison/engine/mask_codec.py`, `CMP-ENGINE-01` owns format 1). These tests hold what the
VIEWER depends on: a blob written **per the text of wave brief C1 section 4 item 1** (without the engine's encoder) is the
blob the tile path decodes, the engine's own `encode_mask` gives the same planes, the store uses the engine's decoder, and
what the decoder refuses reaches the viewer as `storage_integrity_error` after a **bounded** inflation.
"""

from __future__ import annotations

import struct
import tracemalloc
import zlib

import numpy
import pytest

from auditmanager.comparison.engine.mask_codec import LAYERS, MaskFormatError, decode_mask, encode_mask, encode_packed_planes
from auditmanager.comparison.tiles.masks import MaskStore
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id

MIB = 1024 * 1024


class _Store:
    def __init__(self, data: bytes) -> None:
        import hashlib

        self.id = str(derive_blob_id(sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
        self.data = data

    def read(self, blob_id, *, verify: bool = True) -> bytes:
        assert str(blob_id) == self.id and verify
        return self.data


def test_a_blob_written_per_the_briefs_text_decodes_to_the_same_planes_as_the_engines_encoding(support) -> None:
    rng = numpy.random.default_rng(3)
    planes = rng.random((8, 37, 61)) < 0.1
    per_text = decode_mask(support.mask_blob(planes))
    per_codec = decode_mask(encode_mask(planes))
    assert (per_text.width_px, per_text.height_px) == (61, 37) and per_text.packed.shape == (8, 37, 8)
    assert numpy.array_equal(per_text.packed, per_codec.packed)
    assert numpy.array_equal(per_text.planes(), planes)
    assert LAYERS == ("main", "light_elements", "color_change", "line_style", "moved", "within_tolerance", "noise", "service_zones")


def test_the_worker_writer_for_packed_planes_gives_a_blob_the_tile_path_reads(support) -> None:
    planes = support.planes_with(70, 20, {"moved": [(69, 19), (0, 0)], "noise": [(33, 5)]})
    packed = numpy.packbits(planes, axis=-1, bitorder="big")
    blob = encode_packed_planes(packed, 70, 20)
    mask = MaskStore(_Store(blob)).planes(_Store(blob).id)
    assert numpy.array_equal(mask.packed, packed)


def test_the_store_decodes_with_the_engines_codec_and_nothing_else() -> None:
    store = MaskStore(object())
    assert store._decode is decode_mask  # the one seam of wave brief C1 section 4 item 2


@pytest.mark.parametrize("case", ["short", "magic", "format", "layers", "reserved", "zero_width", "zero_height", "over_cap"])
def test_a_blob_the_codec_refuses_reaches_the_viewer_as_an_integrity_error(support, case: str) -> None:
    good = support.mask_blob(support.planes_with(8, 1, {}))
    blobs = {
        "short": b"AMCM",
        "magic": b"XMCM" + good[4:],
        "format": good[:4] + bytes([2]) + good[5:],
        "layers": good[:5] + bytes([7]) + good[6:],
        "reserved": good[:6] + bytes([1, 0]) + good[8:],
        "zero_width": struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 0, 5) + zlib.compress(b""),
        "zero_height": struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 5, 0) + zlib.compress(b""),
        # 6325 x 6325 = 40 005 625 pixels, 5 625 over the cap of ADR-0025 decision 9 (written out so a changed cap is a changed test)
        "over_cap": struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 6325, 6325) + zlib.compress(b"\0" * 1000),
    }
    reasons = {"short": "header_short", "magic": "magic", "format": "format", "layers": "layer_count", "reserved": "reserved",
               "zero_width": "grid_empty", "zero_height": "grid_empty", "over_cap": "plane_over_cap"}
    store = _Store(blobs[case])
    with pytest.raises(DomainError) as refused:
        MaskStore(store).planes(store.id)
    assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    with pytest.raises(MaskFormatError) as why:
        decode_mask(blobs[case])
    assert why.value.args[0] == reasons[case]  # each header field refuses for its own reason, not for a later check


def test_exactly_forty_megapixels_is_inside_the_cap() -> None:
    blob = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 8000, 5000) + zlib.compress(b"\0" * 10)
    with pytest.raises(MaskFormatError) as refused:
        decode_mask(blob)
    assert refused.value.args[0] == "body_length"  # the grid passed the cap; the stream is too short for it


def test_a_body_that_inflates_to_more_or_less_than_declared_is_refused() -> None:
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 4)
    expected = 8 * 4 * 2
    for size in (expected - 1, expected + 1, expected * 100):
        with pytest.raises(MaskFormatError):
            decode_mask(header + zlib.compress(b"\0" * size))
    assert decode_mask(header + zlib.compress(b"\0" * expected)).packed.shape == (8, 4, 2)


def test_trailing_bytes_garbage_and_a_truncated_stream_are_refused() -> None:
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 4)
    good = zlib.compress(b"\0" * 64)
    for body in (good + b"trailing", b"not a deflate stream at all", good[:-6]):
        with pytest.raises(MaskFormatError):
            decode_mask(header + body)


def test_a_hostile_body_is_never_inflated_beyond_what_the_header_declares() -> None:
    """Sixty-four megabytes of zeros in about sixty kilobytes, behind a header that declares sixty-four bytes: the
    inflation is stopped at the declared length plus one byte, through the store the tile path uses."""
    bomb = zlib.compress(b"\0" * (64 * MIB), 9)
    assert len(bomb) < 100_000
    blob = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 4) + bomb
    store = _Store(blob)
    tracemalloc.start()
    try:
        with pytest.raises(DomainError) as refused:
            MaskStore(store).planes(store.id)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert peak < 4 * MIB, peak
