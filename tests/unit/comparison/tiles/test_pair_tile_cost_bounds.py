"""Structural bounds on the work of one tile request (`CMP-VIEWER-01`; the timings are in
``measure_pair_tile_cost.py`` and the report -- a time on a loaded host is not an assertion, an allocation is)."""

from __future__ import annotations

import struct
import tracemalloc
import zlib

import numpy

from auditmanager.comparison.tiles.mask import read_mask
from auditmanager.comparison.tiles.reduction import axis_starts, reduce_max

MIB = 1024 * 1024
#: 2A0 (1682 x 1189 mm) at the 113 dpi of the registration rule.
WIDTH, HEIGHT = 7483, 5290


def test_a_hostile_body_allocates_no_more_than_a_chunk_beyond_what_the_header_declares(support) -> None:
    """Sixty-four megabytes of zeros in about sixty kilobytes, behind a header that declares sixty-four bytes."""
    bomb = zlib.compress(b"\0" * (64 * MIB), 9)
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 16, 4)
    tracemalloc.start()
    try:
        try:
            read_mask(header + bomb)
        except Exception:  # the refusal is asserted in the reader's own tests
            pass
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 4 * MIB, peak  # two chunks (the inflated chunk and its resize), never the 64 MiB the stream holds


def test_a_whole_sheet_tile_of_a_2a0_plane_is_reduced_on_packed_bytes_not_on_an_unpacked_plane() -> None:
    """An unpacked plane is 39.6 MB; reducing it by its rows as bytes first keeps the work to a few megabytes."""
    plane = numpy.zeros((HEIGHT, (WIDTH + 7) // 8), dtype=numpy.uint8)
    plane[2000, 3000 // 8] = 0x80 >> (3000 % 8)
    level = 4
    f = 1 << level
    tw, th = -(-WIDTH // f), -(-HEIGHT // f)
    xs, x_end = axis_starts(0, tw, f, 1, WIDTH)
    ys, y_end = axis_starts(0, th, f, 1, HEIGHT)
    tracemalloc.start()
    try:
        tile = reduce_max(plane, xs, x_end, ys, y_end)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert tile.sum() == 1 and tile[2000 // f, 3000 // f]
    assert peak < 8 * MIB, peak


def test_a_tile_at_level_zero_reads_a_window_of_the_plane_not_the_plane() -> None:
    plane = numpy.zeros((HEIGHT, (WIDTH + 7) // 8), dtype=numpy.uint8)
    plane[700, 700 // 8] = 0x80 >> (700 % 8)
    xs, x_end = axis_starts(512, 512, 1, 1, WIDTH)
    ys, y_end = axis_starts(512, 512, 1, 1, HEIGHT)
    tracemalloc.start()
    try:
        tile = reduce_max(plane, xs, x_end, ys, y_end)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert tile.sum() == 1 and tile[700 - 512, 700 - 512]
    assert peak < 2 * MIB, peak
