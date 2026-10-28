"""The mask the job writes and the 40 Mpx cap it keeps (`CMP-ENGINE-01`, ADR-0025 decision 9)."""

from __future__ import annotations

import dataclasses
import os
import tempfile

import numpy as np
import pytest

from auditmanager.comparison.engine.child import job
from auditmanager.comparison.engine.child.geometry import Canvas
from auditmanager.comparison.engine.child.planes import PlaneStore
from auditmanager.comparison.engine.mask_codec import LAYERS, decode_mask

NAMES = ("a_only", "b_only", "light_a", "light_b", "color", "style", "noise", "within_tol", "moved", "zones")


def planes_with(**bits: tuple[int, int]) -> PlaneStore:
    store = PlaneStore(203, 77, NAMES)
    for name, (x, y) in bits.items():
        store.or_window(name, x, y, np.ones((3, 3), np.uint8))
    return store


def test_a_same_pair_gets_no_mask_even_when_a_plane_has_pixels() -> None:
    with tempfile.TemporaryDirectory() as out:
        assert job._write_mask(planes_with(zones=(10, 10)), out, Canvas(292.0, 111.0, 50), "same") is None
        assert os.listdir(out) == []


def test_a_pair_without_a_pixel_in_any_plane_has_no_mask() -> None:
    with tempfile.TemporaryDirectory() as out:
        assert job._write_mask(planes_with(), out, Canvas(292.0, 111.0, 50), "different") is None


def test_the_planes_of_the_blob_are_the_layers_of_the_contract_in_order() -> None:
    store = planes_with(a_only=(1, 1), b_only=(50, 2), light_a=(10, 10), light_b=(60, 12), color=(20, 20), style=(30, 30),
                        moved=(40, 40), within_tol=(70, 50), noise=(80, 60), zones=(150, 5))
    with tempfile.TemporaryDirectory() as out:
        info = job._write_mask(store, out, Canvas(292.0, 111.0, 50), "different")
        assert info == {"format": 1, "dpi": 50, "width_px": 203, "height_px": 77}
        decoded = decode_mask(open(os.path.join(out, "mask.bin"), "rb").read())
    where = {name: np.argwhere(decoded.plane(name)) for name in LAYERS}
    assert {name: len(points) for name, points in where.items()} == {name: 18 if name in ("main", "light_elements") else 9 for name in LAYERS}
    assert tuple(where["main"].min(axis=0)) == (1, 1) and tuple(where["main"].max(axis=0)) == (4, 52)       # a_only + b_only
    assert tuple(where["light_elements"].min(axis=0)) == (10, 10) and tuple(where["service_zones"].min(axis=0)) == (5, 150)
    assert tuple(where["color_change"].min(axis=0)) == (20, 20) and tuple(where["line_style"].min(axis=0)) == (30, 30)
    assert tuple(where["moved"].min(axis=0)) == (40, 40) and tuple(where["within_tolerance"].min(axis=0)) == (50, 70)
    assert tuple(where["noise"].min(axis=0)) == (60, 80)


def test_a_page_whose_canvas_passes_the_cap_is_refused_by_the_child_before_it_renders_anything(compare, corpus_page) -> None:
    """A3 at 600 dpi is 69 Mpx: the engine's canvas is the page of A at the dpi of its profile, and never passes 40 Mpx."""
    a, b = corpus_page("vs1/v1.pdf", 2), corpus_page("vs1/v2.pdf", 2)
    from auditmanager.comparison.engine.service import compute_pair

    too_big = dataclasses.replace(a.data, raster=(600, 9922, 7017))
    computed = compute_pair(too_big, b.data, path_a=str(a.path), path_b=str(b.path))
    assert computed.end == "refused" and computed.child.status == "refused" and not computed.child.facts.get("vm_peak_kib", 0) > 400_000
    assert computed.outcome["status"] == "needs_review" and "PAGE_TOO_LARGE" in computed.outcome["reasons"]
    assert computed.mask is None
