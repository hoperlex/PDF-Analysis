"""The mask blob, format 1 (`CMP-ENGINE-01`, wave brief `CMP-WAVE-C1` section 4 item 1).

The bytes are checked against the text of the brief, written out here independently of the module: the header
``struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width_px, height_px)`` and ``zlib.compress(numpy.packbits(planes, axis=-1,
bitorder="big").tobytes(), 6)``. The viewer lane builds its blobs from that text; a module that drifted from it would
pass its own tests and fail the viewer's.
"""

from __future__ import annotations

import struct
import tracemalloc
import zlib

import numpy
import pytest

from auditmanager.comparison.engine import mask_codec
from auditmanager.comparison.engine.mask_codec import (
    LAYERS,
    MASK_FORMAT,
    MAX_PLANE_PIXELS,
    MaskFormatError,
    decode_mask,
    encode_mask,
    encode_packed_planes,
)


def _planes(width: int, height: int, seed: int = 7, density: float = 0.1) -> numpy.ndarray:
    rng = numpy.random.default_rng(seed)
    return rng.random((8, height, width)) < density


def _brief_blob(planes: numpy.ndarray) -> bytes:
    """The blob exactly as the brief writes it, with no help from the module under test."""
    _, height, width = planes.shape
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width, height)
    return header + zlib.compress(numpy.packbits(planes, axis=-1, bitorder="big").tobytes(), 6)


def _blob(width: int, height: int, body: bytes, *, magic: bytes = b"AMCM", version: int = 1, layers: int = 8,
          reserved: int = 0) -> bytes:
    return struct.pack("<4sBBHII", magic, version, layers, reserved, width, height) + zlib.compress(body, 6)


def test_the_format_and_the_layers_are_those_of_the_brief() -> None:
    assert MASK_FORMAT == 1
    assert LAYERS == ("main", "light_elements", "color_change", "line_style", "moved", "within_tolerance", "noise",
                      "service_zones")
    assert MAX_PLANE_PIXELS == 40_000_000
    assert mask_codec.HEADER_BYTES == 16


def test_the_layers_are_the_members_of_the_contract_enum_in_order() -> None:
    from auditmanager.api.schemas.models import ComparisonLayer

    assert tuple(member.value for member in ComparisonLayer) == LAYERS


def test_the_plane_cap_is_the_working_raster_cap_of_the_page_profile() -> None:
    from auditmanager.comparison.profile.limits import PIXEL_CAP

    assert MAX_PLANE_PIXELS == PIXEL_CAP


@pytest.mark.parametrize("width,height", [(1, 1), (7, 3), (8, 5), (9, 4), (16, 16), (37, 21), (200, 100)])
def test_the_blob_is_the_bytes_of_the_brief(width: int, height: int) -> None:
    planes = _planes(width, height)
    assert encode_mask(planes) == _brief_blob(planes)


@pytest.mark.parametrize("width,height", [(1, 1), (7, 3), (8, 5), (9, 4), (37, 21), (200, 100)])
def test_a_blob_decodes_to_the_planes_it_was_made_from(width: int, height: int) -> None:
    planes = _planes(width, height, seed=width * 1000 + height)
    decoded = decode_mask(encode_mask(planes))
    assert (decoded.width_px, decoded.height_px) == (width, height)
    assert decoded.packed.shape == (8, height, (width + 7) // 8)
    assert numpy.array_equal(decoded.planes(), planes)
    for index, name in enumerate(LAYERS):
        assert numpy.array_equal(decoded.plane(name), planes[index])
        assert numpy.array_equal(decoded.plane(index), planes[index])


def test_a_blob_built_from_the_briefs_text_alone_decodes() -> None:
    planes = _planes(41, 17, seed=3)
    assert numpy.array_equal(decode_mask(_brief_blob(planes)).planes(), planes)


def test_planes_packed_a_band_at_a_time_give_the_same_bytes() -> None:
    planes = _planes(203, 90, seed=11)
    bands = [planes[:, a:b] for a, b in ((0, 33), (33, 64), (64, 90))]
    packed = numpy.concatenate([numpy.packbits(band, axis=-1, bitorder="big") for band in bands], axis=1)
    assert encode_packed_planes(packed, 203, 90) == encode_mask(planes)


def test_padding_bits_left_in_packed_rows_do_not_change_the_bytes() -> None:
    planes = _planes(13, 6, seed=5)
    packed = numpy.packbits(planes, axis=-1, bitorder="big")
    dirty = packed.copy()
    dirty[:, :, -1] |= 0x07
    assert encode_packed_planes(dirty, 13, 6) == encode_mask(planes)
    assert not numpy.array_equal(dirty, packed)  # the caller's array is not changed by the encoder
    assert dirty[0, 0, -1] & 0x07 == 0x07


def test_packed_planes_of_the_wrong_shape_or_type_are_refused() -> None:
    packed = numpy.zeros((8, 4, 2), dtype=numpy.uint8)
    with pytest.raises(MaskFormatError, match="planes_shape"):
        encode_packed_planes(packed, 40, 4)  # 40 px need 5 bytes
    with pytest.raises(MaskFormatError, match="planes_shape"):
        encode_packed_planes(packed.astype(numpy.uint16), 16, 4)


@pytest.mark.parametrize("shape", [(7, 4, 4), (9, 4, 4), (8, 4), (4, 4)])
def test_planes_that_are_not_eight_by_height_by_width_are_refused(shape: tuple[int, ...]) -> None:
    with pytest.raises(MaskFormatError, match="planes_shape"):
        encode_mask(numpy.zeros(shape, dtype=bool))


def test_a_grid_of_no_pixels_is_refused_by_the_encoder_and_the_decoder() -> None:
    with pytest.raises(MaskFormatError, match="grid_empty"):
        encode_mask(numpy.zeros((8, 0, 5), dtype=bool))
    blob = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 0, 5) + zlib.compress(b"", 6)
    with pytest.raises(MaskFormatError, match="grid_empty"):
        decode_mask(blob)


# -- the refusals of the decoder ------------------------------------------------------------------


def test_a_wrong_magic_is_refused() -> None:
    body = bytes(8 * 4 * 1)
    with pytest.raises(MaskFormatError, match="magic"):
        decode_mask(_blob(8, 4, body, magic=b"AMCN"))


def test_a_wrong_format_is_refused() -> None:
    body = bytes(8 * 4 * 1)
    for version in (0, 2, 255):
        with pytest.raises(MaskFormatError, match="format"):
            decode_mask(_blob(8, 4, body, version=version))


def test_a_wrong_layer_count_is_refused() -> None:
    body = bytes(8 * 4 * 1)
    for layers in (0, 1, 7, 9):
        with pytest.raises(MaskFormatError, match="layer_count"):
            decode_mask(_blob(8, 4, body, layers=layers))


def test_a_reserved_word_that_is_not_zero_is_refused() -> None:
    with pytest.raises(MaskFormatError, match="reserved"):
        decode_mask(_blob(8, 4, bytes(32), reserved=1))


def test_a_header_that_is_too_short_is_refused() -> None:
    for size in (0, 3, 15):
        with pytest.raises(MaskFormatError, match="header_short"):
            decode_mask(b"A" * size)


def test_a_plane_over_forty_megapixels_is_refused_before_anything_is_decompressed() -> None:
    wide = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 8001, 5000) + b"\x00"  # 40 005 000 px; the body is not even read
    with pytest.raises(MaskFormatError, match="plane_over_cap"):
        decode_mask(wide)
    exactly = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 8000, 5000) + b"\x00"  # at the cap: passes it, fails on the body
    with pytest.raises(MaskFormatError, match="body_length"):
        decode_mask(exactly)


def test_a_grid_whose_rows_pad_to_a_huge_body_is_refused() -> None:
    thin = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 1, 20_000_000) + b"\x00"  # 160 MB once every row is padded
    with pytest.raises(MaskFormatError, match="body_over_cap"):
        decode_mask(thin)


def test_a_body_shorter_or_longer_than_the_header_says_is_refused() -> None:
    expected = 8 * 4 * 2
    for size in (0, 1, expected - 1, expected + 1, expected * 2):
        with pytest.raises(MaskFormatError, match="body_length"):
            decode_mask(_blob(16, 4, bytes(size)))


def test_a_truncated_or_damaged_body_is_refused() -> None:
    good = encode_mask(_planes(40, 40, seed=2))
    with pytest.raises(MaskFormatError):
        decode_mask(good[:-6])
    damaged = bytearray(good)
    damaged[20] ^= 0xFF
    damaged[21] ^= 0xFF
    with pytest.raises(MaskFormatError):
        decode_mask(bytes(damaged))


def test_bytes_after_the_end_of_the_stream_are_refused() -> None:
    with pytest.raises(MaskFormatError, match="body_length"):
        decode_mask(encode_mask(_planes(16, 4)) + b"trailing")


def test_anything_that_is_not_bytes_is_refused() -> None:
    with pytest.raises(MaskFormatError, match="not_bytes"):
        decode_mask("AMCM")  # type: ignore[arg-type]


def test_a_blob_that_claims_a_small_grid_and_expands_to_hundreds_of_megabytes_is_not_inflated() -> None:
    """The bounded decompression: a zlib bomb is refused after one small allocation (ADR-0025 decision 9)."""
    compressor = zlib.compressobj(9)
    chunk = bytes(1 << 20)
    parts = [compressor.compress(chunk) for _ in range(300)] + [compressor.flush()]
    bomb = b"".join(parts)  # 300 MiB of zeros in about 300 KiB
    assert len(bomb) < 1 << 20
    blob = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 16) + bomb  # the header allows 8 * 16 * 2 = 256 bytes
    tracemalloc.start()
    try:
        with pytest.raises(MaskFormatError, match="body_length"):
            decode_mask(blob)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 4 << 20, f"the decoder allocated {peak} bytes for a blob whose header allows 256"


def test_an_encoder_output_is_deterministic() -> None:
    planes = _planes(64, 64, seed=9)
    assert encode_mask(planes) == encode_mask(planes.copy())


def test_an_empty_mask_is_small() -> None:
    planes = numpy.zeros((8, 4678, 6623), dtype=bool)  # an A1 canvas at 200 dpi
    blob = encode_mask(planes)
    assert len(blob) < 100_000
    assert not decode_mask(blob).plane("main").any()


# -- the decoder inflates a piece at a time into one buffer (`CMP-C1-FIX-A` item 6) ----------------------------------

def _blob_of_body(width: int, height: int, body: bytes, level: int = 6) -> bytes:
    return struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width, height) + zlib.compress(body, level)


@pytest.mark.parametrize("width,height", [
    (1024, 1024),  # the body is exactly one output piece (1 MiB)
    (1024, 2048),  # exactly two
    (1024, 1025),  # one byte row over
    (1000, 1111),  # no multiple of anything
    (4096, 700),   # several pieces
])
def test_a_body_spanning_several_pieces_decodes_to_the_same_planes(width: int, height: int) -> None:
    """The piece is `OUT_CHUNK_BYTES` (1 MiB): bodies at, around and well over it round-trip bit for bit."""
    rng = numpy.random.default_rng(width + height)
    planes = rng.random((8, height, width)) < 0.05
    decoded = decode_mask(encode_mask(planes))
    assert mask_codec.body_bytes(width, height) >= mask_codec.OUT_CHUNK_BYTES
    assert numpy.array_equal(decoded.planes(), planes)


def test_a_body_that_does_not_compress_is_fed_in_slices() -> None:
    """Random bytes compress to about their own size, so the compressed stream is many `IN_CHUNK_BYTES` slices long."""
    width, height = 2048, 700
    body = numpy.random.default_rng(3).integers(0, 256, mask_codec.body_bytes(width, height), dtype=numpy.uint8).tobytes()
    blob = _blob_of_body(width, height, body)
    assert len(blob) > 4 * mask_codec.IN_CHUNK_BYTES
    assert decode_mask(blob).packed.tobytes() == body


def test_a_decoded_mask_is_read_only_like_the_view_the_one_call_decoder_returned() -> None:
    decoded = decode_mask(encode_mask(_planes(32, 16)))
    assert decoded.packed.flags.writeable is False
    with pytest.raises(ValueError):
        decoded.packed[0, 0, 0] = 1


def test_the_body_is_held_once_while_it_is_inflated() -> None:
    """`CMP-VIEWER-01` section 12 item 3: the one-call decoder held the 40 MB of a 2A0 mask twice for a moment (+75 MiB of
    resident set); the traced peak of the decode is now the body and a few pieces, not two bodies."""
    width, height = 6000, 4000  # 24 Mpx a plane: a body of 24 MB (the planes are built packed, never unpacked)
    row = mask_codec.packed_width(width)
    planes = []
    for index in range(8):
        plane = numpy.zeros((height, row), dtype=numpy.uint8)
        plane[index::7, ::5] = 0xA5
        planes.append(plane)
    blob = encode_packed_planes(planes, width, height)
    body = mask_codec.body_bytes(width, height)
    del planes, plane
    tracemalloc.start()
    try:
        decoded = decode_mask(blob)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert decoded.packed.nbytes == body
    assert peak < body + 4 * mask_codec.OUT_CHUNK_BYTES, f"peak {peak} for a body of {body}: the body was held more than once"


def test_a_stream_that_is_one_byte_too_long_or_too_short_is_refused_in_every_piece_position() -> None:
    """Bodies that end exactly on, one before and one after a piece boundary are refused with the same reason."""
    width, height = 1024, 1024
    expected = mask_codec.body_bytes(width, height)
    for size in (expected - 1, expected + 1, expected + mask_codec.OUT_CHUNK_BYTES):
        with pytest.raises(MaskFormatError, match="body_length"):
            decode_mask(_blob_of_body(width, height, bytes(size)))
    assert decode_mask(_blob_of_body(width, height, bytes(expected))).packed.nbytes == expected


def test_a_stream_cut_off_inside_a_piece_or_followed_by_a_second_stream_is_refused() -> None:
    width, height = 1024, 2048
    good = _blob_of_body(width, height, numpy.random.default_rng(1).integers(0, 256, mask_codec.body_bytes(width, height), dtype=numpy.uint8).tobytes())
    for cut in (len(good) // 2, len(good) - 1, mask_codec.HEADER_BYTES + 3):
        with pytest.raises(MaskFormatError):
            decode_mask(good[:cut])
    with pytest.raises(MaskFormatError, match="body_length"):
        decode_mask(good + zlib.compress(b"more"))
    # trailing bytes that never reach the decompressor (whole slices past the end of the stream) are refused as well
    with pytest.raises(MaskFormatError, match="body_length"):
        decode_mask(good + bytes(3 * mask_codec.IN_CHUNK_BYTES))


def test_a_blob_that_claims_a_large_grid_and_holds_nothing_allocates_nothing_large() -> None:
    """The buffer is allocated when the first piece proves that the stream produces anything: a header of 40 Mpx over no
    body, or over bytes that are not a stream, costs no 40 MB."""
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 8000, 5000)
    tracemalloc.start()
    try:
        for tail in (b"", b"\x00" * 64, zlib.compress(b"", 6)):
            with pytest.raises(MaskFormatError):
                decode_mask(header + tail)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 1 << 20, peak


def test_a_bytearray_and_a_memoryview_decode_like_bytes() -> None:
    blob = encode_mask(_planes(40, 40, seed=4))
    reference = decode_mask(blob).packed
    assert numpy.array_equal(decode_mask(bytearray(blob)).packed, reference)
    assert numpy.array_equal(decode_mask(memoryview(blob)).packed, reference)
