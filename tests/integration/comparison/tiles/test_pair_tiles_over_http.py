"""``streamComparisonPairTile`` through the composed application (`CMP-VIEWER-01`).

The real composition root, the lane's PostgreSQL and object store, the page profiles of VS-1 v1 and v2 built by the real
children, and pairs and results inserted directly (SERIES and ENGINE write them later). The oracle of every pixel is the
page-profile tile of the same page, read through its own endpoint: ``mode=a`` is that tile byte for byte, ``mode=b`` is
the newer page's tile laid on the older page's canvas, and the overlay is the darker of the two with the mask's layers
painted over it.
"""

from __future__ import annotations

import json
import os
from typing import Any

import cv2
import numpy
import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.tiles.compose import PALETTE_RGB

SECRET = "pair-tiles-static-token"
PNG = b"\x89PNG\r\n\x1a\n"
A1_W, A1_H = 6623, 4678
PPP3 = 72.0 * 8 / 200  # points in one pixel of level 3 of the A1 plan


@pytest.fixture(scope="module")
def http(session_factory) -> TestClient:
    assert os.environ.get("DATABASE_URL"), "the lane's .env must be loaded"
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: SECRET}
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(SECRET, "pair-tiles-suite")


def _get(http: TestClient, token: str, path: str, **query: Any):
    return http.get(path, params=query or None, headers={"Authorization": f"Bearer {token}"})


def _tile(http, token, pair, mode, level, column, row, layers=None, align=None):
    query: dict[str, Any] = {"mode": mode, "level": level, "column": column, "row": row}
    if layers is not None:
        query["layers"] = layers
    if align is not None:
        query["align_blocks"] = "true" if align else "false"
    return _get(http, token, f"/comparison-sheet-pairs/{pair}/tile", **query)


def _decode(response) -> "numpy.ndarray":
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png" and response.content.startswith(PNG)
    return cv2.imdecode(numpy.frombuffer(response.content, numpy.uint8), cv2.IMREAD_COLOR)


def _profile_tile(http, token, profile, level, column, row):
    return _get(http, token, f"/page-profiles/{profile}/tile", level=level, column=column, row=row)


def _error(response) -> dict:
    return json.loads(response.content)


def test_mode_a_is_the_page_profile_tile_of_the_older_page_byte_for_byte(http, token, world, make_pair) -> None:
    pair = make_pair()
    for level, column, row in ((0, 3, 2), (1, 1, 1), (2, 1, 1), (4, 0, 0)):
        got = _tile(http, token, pair, "a", level, column, row)
        expected = _profile_tile(http, token, world.older_pages[5], level, column, row)
        assert got.status_code == 200 and got.content == expected.content, (level, column, row)
        assert int(got.headers["content-length"]) == len(got.content)


def test_mode_b_with_an_identity_transform_is_the_newer_page_tile_itself(http, token, world, make_pair) -> None:
    pair = make_pair()
    for level, column, row in ((0, 2, 1), (3, 1, 1), (4, 0, 0)):
        got = _decode(_tile(http, token, pair, "b", level, column, row))
        expected = _decode(_profile_tile(http, token, world.newer_pages[5], level, column, row))
        assert numpy.array_equal(got, expected), (level, column, row)


def test_mode_b_follows_the_transform_to_the_pixel(http, token, world, make_pair) -> None:
    """B moved 288 points (100 pixels of level 3) left by the transform: output(x, y) = B(x + 100, y) at level 3."""
    pair = make_pair(result={"how_compared": {"algo_version": "t", "dpi": 200, "tolerance_pt": 0.5,
                                              "transform": [1, 0, 0, 1, -100 * PPP3, 0]}})
    page = world.newer_pages[5]
    whole = numpy.hstack([_decode(_profile_tile(http, token, page, 3, c, 0)) for c in (0, 1)])  # level 3 is 828 x 585
    top = numpy.vstack([whole] + [numpy.hstack([_decode(_profile_tile(http, token, page, 3, c, 1)) for c in (0, 1)])])
    assert top.shape[:2] == (585, 828)
    first = _decode(_tile(http, token, pair, "b", 3, 0, 0))
    assert numpy.array_equal(first, top[0:512, 100:612])
    second = _decode(_tile(http, token, pair, "b", 3, 1, 0))
    assert second.shape[:2] == (512, 316)
    assert numpy.array_equal(second[:, :216], top[0:512, 612:828]) and (second[:, 216:] == 255).all()


def test_the_overlay_without_layers_is_the_darker_of_the_two_pages(http, token, world, make_pair) -> None:
    pair = make_pair()
    for level, column, row in ((2, 0, 1), (0, 5, 4)):
        got = _decode(_tile(http, token, pair, "overlay", level, column, row))
        a = _decode(_profile_tile(http, token, world.older_pages[5], level, column, row))
        b = _decode(_profile_tile(http, token, world.newer_pages[5], level, column, row))
        assert numpy.array_equal(got, numpy.minimum(a, b)), (level, column, row)


def test_one_changed_pixel_is_drawn_at_every_level_and_only_in_the_layer_asked_for(http, token, world, make_pair, support) -> None:
    x, y = 3001, 2003
    blob = support.packed_mask_blob(A1_W, A1_H, {"main": [(x, y)], "line_style": [(100, 4000)]})
    pair = make_pair(
        mask=blob,
        result={"mask": {"format": 1, "dpi": 200, "width_px": A1_W, "height_px": A1_H}},
    )
    main_bgr = PALETTE_RGB["main"][::-1]
    for level in range(5):
        column, row = (x >> level) // 512, (y >> level) // 512
        painted = _decode(_tile(http, token, pair, "overlay", level, column, row, layers="main,line_style"))
        plain = _decode(_tile(http, token, pair, "overlay", level, column, row))
        hits = numpy.all(painted == main_bgr, axis=2)
        assert hits.sum() == 1, level
        assert hits[(y >> level) - row * 512, (x >> level) - column * 512], level
        other = numpy.all(painted == PALETTE_RGB["line_style"][::-1], axis=2)  # the other pixel, when it shares the tile
        assert other.sum() == (1 if (4000 >> level) // 512 == row and (100 >> level) // 512 == column else 0), level
        assert numpy.array_equal(painted[~hits & ~other], plain[~hits & ~other]), level  # nothing else changed
        only_other = _decode(_tile(http, token, pair, "overlay", level, column, row, layers="line_style"))
        assert not numpy.all(only_other == main_bgr, axis=2).any(), level  # the main layer was not asked for
        assert numpy.array_equal(only_other[~other], plain[~other]), level
    # the line_style pixel sits in another tile of level 0 and is drawn there
    line = _decode(_tile(http, token, pair, "overlay", 0, 0, 7, layers="line_style"))
    assert numpy.all(line == PALETTE_RGB["line_style"][::-1], axis=2).sum() == 1


def test_align_blocks_moves_a_block_of_the_newer_page_back_and_withholds_the_layers_over_it(http, token, world, make_pair, support) -> None:
    box = [200 * PPP3, 0.0, 300 * PPP3, 100 * PPP3]  # x 200..300, y 0..100 of level 3
    blocks = [{"box_a": box, "dx_pt": 100 * PPP3, "dy_pt": 0.0}]
    inside, outside = (2000, 400), (4000, 3000)  # raster pixels: (250, 50) and (500, 375) of level 3
    blob = support.packed_mask_blob(A1_W, A1_H, {"main": [inside, outside]})
    pair = make_pair(mask=blob, result={"aligned_blocks": blocks, "mask": {"format": 1, "dpi": 200, "width_px": A1_W, "height_px": A1_H}})
    page = world.newer_pages[5]
    whole = numpy.vstack([numpy.hstack([_decode(_profile_tile(http, token, page, 3, c, r)) for c in (0, 1)]) for r in (0, 1)])
    expected = whole.copy()
    expected[0:100, 200:300] = 255
    expected[0:100, 100:200] = numpy.minimum(expected[0:100, 100:200], whole[0:100, 200:300])
    got = _decode(_tile(http, token, pair, "b", 3, 0, 0, align=True))
    assert numpy.array_equal(got[:, :512], expected[0:512, 0:512])
    plain = _decode(_tile(http, token, pair, "b", 3, 0, 0))
    assert not numpy.array_equal(got, plain)
    # the layers: painted without alignment, withheld over the block's old and new place with it
    main_bgr = PALETTE_RGB["main"][::-1]
    unaligned = _decode(_tile(http, token, pair, "overlay", 3, 0, 0, layers="main"))
    aligned = _decode(_tile(http, token, pair, "overlay", 3, 0, 0, layers="main", align=True))
    assert numpy.all(unaligned == main_bgr, axis=2).sum() == 2  # (250, 50) and (500, 375)
    assert numpy.all(aligned == main_bgr, axis=2).sum() == 1 and numpy.all(aligned[375, 500] == main_bgr)


def test_what_does_not_exist_is_not_found(http, token, world, make_pair, support) -> None:
    pair = make_pair()
    absent = "ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    for mode in ("overlay", "a", "b"):
        response = _tile(http, token, absent, mode, 0, 0, 0)
        assert response.status_code == 404 and _error(response)["error_code"] == "not_found", mode
    # outside the pyramid of the A1 plan: five levels, 13 x 10 tiles at level 0
    for query in ((5, 0, 0), (0, 13, 0), (0, 0, 10), (4, 1, 0), (4, 0, 1), (12, 0, 0), (0, 4095, 4095)):
        for mode in ("overlay", "a", "b"):
            response = _tile(http, token, pair, mode, *query)
            assert response.status_code == 404 and _error(response)["error_code"] == "not_found", (mode, query)
    # the last tile of the pyramid exists and has the size of the partial edge
    assert _decode(_tile(http, token, pair, "a", 0, 12, 9)).shape[:2] == (4678 - 9 * 512, 6623 - 12 * 512)
    # a pair that was never compared has no overlay, but its pages are there
    queued = make_pair(status="queued")
    assert _tile(http, token, queued, "overlay", 2, 0, 0).status_code == 404
    assert _tile(http, token, queued, "a", 2, 0, 0).status_code == 200 and _tile(http, token, queued, "b", 2, 0, 0).status_code == 200
    # an added sheet has no older page; a removed one has no newer page
    added = make_pair(page_a=None, status="added")
    assert _tile(http, token, added, "a", 2, 0, 0).status_code == 404 and _tile(http, token, added, "overlay", 2, 0, 0).status_code == 404
    own = _tile(http, token, added, "b", 2, 0, 0)
    assert own.content == _profile_tile(http, token, world.newer_pages[5], 2, 0, 0).content
    removed = make_pair(page_b=None, status="removed")
    assert _tile(http, token, removed, "b", 2, 0, 0).status_code == 404 and _tile(http, token, removed, "overlay", 2, 0, 0).status_code == 404
    assert _tile(http, token, removed, "a", 2, 0, 0).status_code == 200
    # a result that was never registered has no transform: no overlay, and B is shown as it is
    unregistered = make_pair(status="needs_review", result={"how_compared": {"algo_version": "t", "dpi": 200, "tolerance_pt": 0.5}})
    assert _tile(http, token, unregistered, "overlay", 2, 0, 0).status_code == 404
    assert _tile(http, token, unregistered, "b", 2, 0, 0).content == _profile_tile(http, token, world.newer_pages[5], 2, 0, 0).content
    # a different pair whose mask is missing: the layers cannot be drawn (404), the bare overlay still can
    no_mask = make_pair()
    assert _tile(http, token, no_mask, "overlay", 2, 0, 0, layers="main").status_code == 404
    assert _tile(http, token, no_mask, "overlay", 2, 0, 0).status_code == 200
    # a same pair has no mask and nothing to draw
    same = make_pair(status="same")
    assert _tile(http, token, same, "overlay", 2, 0, 0, layers="main,noise").status_code == 200
    # a page that has no pyramid (a profile that ended without a result) is not a tile
    refused = make_pair(page_a=1)
    assert _tile(http, token, refused, "a", 0, 9, 9).status_code == 404


def test_a_damaged_result_or_mask_is_an_integrity_error_not_a_picture(http, token, world, make_pair, support) -> None:
    def pair_with(blob: bytes | None, **result: Any) -> str:
        return make_pair(mask=blob, result={"mask": {"format": 1, "dpi": 200, "width_px": A1_W, "height_px": A1_H}, **result})

    good = support.packed_mask_blob(A1_W, A1_H, {"main": [(1, 1)]})
    cases = {
        # one header field wrong in a mask that is otherwise the A1 sheet's, so only that field can refuse it
        "magic": pair_with(b"XXXX" + good[4:]),
        "format": pair_with(good[:4] + bytes([9]) + good[5:]),
        "layers": pair_with(good[:5] + bytes([3]) + good[6:]),
        "size": pair_with(support.mask_blob(numpy.zeros((8, 4, 16), bool))),  # a 16 x 4 mask for an A1 sheet
        "truncated": pair_with(good[: len(good) // 2]),
        "over_cap": pair_with(good[:16].replace(good[8:16], (50000).to_bytes(4, "little") + (50000).to_bytes(4, "little")) + good[16:]),
        "transform": make_pair(result={"how_compared": {"algo_version": "t", "dpi": 200, "tolerance_pt": 0.5, "transform": [0, 0, 0, 0, 1, 1]}}),
        "blocks": make_pair(result={"aligned_blocks": [{"box_a": [3, 3, 1, 1], "dx_pt": 0, "dy_pt": 0}]}),
        "canvas": make_pair(result={"canvas": {"width_pt": 100.0, "height_pt": 100.0}}),
    }
    for name, pair in cases.items():
        response = _tile(http, token, pair, "overlay", 3, 0, 0, layers="main", align=True)
        assert response.status_code == 422 and _error(response)["error_code"] == "storage_integrity_error", (name, response.status_code, response.text)
        assert response.content.startswith(b"{") and b"Traceback" not in response.content
    # a mask for another grid than the canvas is refused even when it is well formed
    wrong_grid = make_pair(mask=support.packed_mask_blob(3000, 2000, {"main": [(1, 1)]}),
                           result={"mask": {"format": 1, "dpi": 200, "width_px": 3000, "height_px": 2000}})
    response = _tile(http, token, wrong_grid, "overlay", 3, 0, 0, layers="main")
    assert response.status_code == 422 and _error(response)["error_code"] == "storage_integrity_error"


def test_a_transform_that_needs_too_much_of_the_newer_page_is_refused_not_degraded(http, token, world, make_pair) -> None:
    """A tenfold squeeze in one direction and a stretch in the other: one output tile covers a long strip of B (about
    twenty tiles), and a request may read sixteen."""
    wild = make_pair(result={"how_compared": {"algo_version": "t", "dpi": 200, "tolerance_pt": 0.5,
                                              "transform": [0.1, 0.0, 0.0, 10.0, 0.0, -1836.0]}})
    response = _tile(http, token, wild, "overlay", 0, 0, 0)
    assert response.status_code == 503 and _error(response)["error_code"] == "dependency_unavailable"
    assert _error(response)["details"]["dependency"] == "comparison_pair_tiles"


def test_the_request_is_bounded_by_the_contract_before_it_reaches_the_reader(http, token, make_pair) -> None:
    pair = make_pair()
    for query in ({"mode": "sideways", "level": 0, "column": 0, "row": 0}, {"mode": "a", "level": 13, "column": 0, "row": 0},
                  {"mode": "a", "level": 0, "column": 4096, "row": 0}, {"mode": "a", "level": 0, "column": 0},
                  {"mode": "overlay", "level": 0, "column": 0, "row": 0, "layers": "main,hidden"}):
        assert _get(http, token, f"/comparison-sheet-pairs/{pair}/tile", **query).status_code == 422, query
    assert http.get(f"/comparison-sheet-pairs/{pair}/tile?mode=a&level=0&column=0&row=0").status_code == 401
