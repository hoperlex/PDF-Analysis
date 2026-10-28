"""The two tile operations send the headers of an immutable tile (`CMP-C1-FIX-A` item 4, `CMP-VIEWER-01` section 12 item 1).

The original sends ``private, max-age=3600`` with its tiles. The contract of ``streamVersionPageTile`` and
``streamComparisonPairTile`` declares no ``304`` and no ``If-None-Match``, so the routes send the headers and nothing more:
a request that carries ``If-None-Match`` is answered ``200`` with the tile, as before.
"""

from __future__ import annotations

import re

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.comparison_pair_tiles import build_comparison_pair_tile_routes
from auditmanager.api.routers.version_pages import TILE_CACHE_CONTROL, build_version_page_routes

PROFILE = "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PROFILE = "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAW"
PAIR = "ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PAIR = "ctp_01ARZ3NDEKTSV4RRFFQ69G5FAW"
PNG = b"\x89PNG\r\n\x1a\n" + b"tile"
TAG = re.compile(r'^W/"[0-9a-f]{32}"$')


class PagePort:
    def read_tile(self, **kwargs: object) -> bytes:
        return PNG


class PairPort:
    def read_tile(self, **kwargs: object) -> bytes:
        return PNG


@pytest.fixture(scope="module")
def client() -> TestClient:
    router = APIRouter()
    build_version_page_routes(router, PagePort())  # type: ignore[arg-type]
    build_comparison_pair_tile_routes(router, PairPort())  # type: ignore[arg-type]
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def page(client: TestClient, profile: str = PROFILE, level: int = 2, column: int = 1, row: int = 3, **headers: str):
    return client.get(f"/page-profiles/{profile}/tile", params={"level": level, "column": column, "row": row}, headers=headers)


def pair(client: TestClient, pair_id: str = PAIR, **query: object):
    params = {"mode": "overlay", "level": 2, "column": 1, "row": 3, **query}
    return client.get(f"/comparison-sheet-pairs/{pair_id}/tile", params=params)


@pytest.mark.parametrize("response", [lambda c: page(c), lambda c: pair(c)], ids=["page tile", "pair tile"])
def test_a_tile_is_kept_by_the_browser_for_an_hour_and_has_a_name(client: TestClient, response) -> None:
    got = response(client)
    assert got.status_code == 200 and got.content == PNG
    assert got.headers["cache-control"] == TILE_CACHE_CONTROL == "private, max-age=3600"
    assert TAG.match(got.headers["etag"]), got.headers["etag"]
    assert got.headers["content-type"] == "image/png" and got.headers["content-length"] == str(len(PNG))


@pytest.mark.parametrize("response", [lambda c: page(c), lambda c: pair(c)], ids=["page tile", "pair tile"])
def test_the_same_request_has_the_same_tag(client: TestClient, response) -> None:
    assert response(client).headers["etag"] == response(client).headers["etag"]


def test_every_parameter_of_a_page_tile_is_in_its_tag(client: TestClient) -> None:
    base = page(client).headers["etag"]
    others = [page(client, OTHER_PROFILE), page(client, level=3), page(client, column=2), page(client, row=4)]
    tags = {base, *(o.headers["etag"] for o in others)}
    assert len(tags) == 5


def test_every_parameter_of_a_pair_tile_is_in_its_tag(client: TestClient) -> None:
    base = pair(client).headers["etag"]
    variants = [
        pair(client, OTHER_PAIR), pair(client, mode="a"), pair(client, mode="b"), pair(client, level=3), pair(client, column=2),
        pair(client, row=4), pair(client, layers="main"), pair(client, layers="main,noise"), pair(client, align_blocks="true"),
    ]
    tags = {base, *(v.headers["etag"] for v in variants)}
    assert len(tags) == 10


def test_a_page_tile_and_a_pair_tile_never_share_a_tag(client: TestClient) -> None:
    assert page(client).headers["etag"] != pair(client).headers["etag"]


def test_no_conditional_answer_is_given_because_the_contract_declares_none(client: TestClient) -> None:
    """``If-None-Match`` with the tile's own tag is answered ``200`` with the bytes: a ``304`` the contract does not list
    would be an undeclared answer."""
    tag = page(client).headers["etag"]
    again = page(client, **{"If-None-Match": tag})
    assert again.status_code == 200 and again.content == PNG
    assert pair(client).status_code == 200
    import json
    from pathlib import Path

    document = json.loads((Path(__file__).resolve().parents[4] / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
    for path in ("/page-profiles/{comparison_page_profile_id}/tile", "/comparison-sheet-pairs/{comparison_sheet_pair_id}/tile"):
        operation = document["paths"][path]["get"]
        assert "304" not in operation["responses"]
        assert "If-None-Match" not in {p.get("name") for p in operation.get("parameters", [])}
