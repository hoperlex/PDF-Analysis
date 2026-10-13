"""`W55B-SEAL-01`: the two portal-block routes and their sealed stubs, without a database.

The routes are driven over a bare FastAPI application with a fake ``BlockPort``, so what is
asserted is the router's own work -- paging, the order the cursor carries, the body shape,
the PNG's headers -- and not any adapter's. The shipped ``BlockAdapter`` is then asked the
two questions directly: until `W55B-GEOMETRY-01` it refuses with ``dependency_unavailable``
and never answers ``not_produced``, which would be a true statement about a version and a false
one about a deployment that cannot yet produce anything.
"""

from __future__ import annotations

import io
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.blocks import build_block_routes
from auditmanager.api.routers.correlation import CorrelationMiddleware
from auditmanager.api.schemas.blocks import (
    PortalBlockIndexView,
    PortalBlockView,
    PortalCropContent,
)
from auditmanager.bootstrap.adapters import BlockAdapter, DocumentAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24


def _block(n: int, *, page: int, ordinal: int | None, kind: str = "text") -> PortalBlockView:
    return PortalBlockView(
        portal_block_id=f"blk_{n:032x}", page_number=page, page_label=page, ordinal=ordinal,
        block_type=kind, status="recognized", bbox_norm=(0.0, 0.0, 1.0, 1.0), geometry="ok",
    )


#: Deliberately returned in the order the port promises: page, ordinal, null ordinal last.
BLOCKS = (
    _block(1, page=1, ordinal=0),
    _block(2, page=1, ordinal=1, kind="image"),
    _block(3, page=1, ordinal=None, kind="stamp"),
    _block(4, page=2, ordinal=0),
    _block(5, page=2, ordinal=None, kind="stamp"),
)


class FakeBlocks:
    def __init__(self, status: str = "produced") -> None:
        self.status = status
        self.asked: list[tuple[str, ...]] = []

    def get_block_index(self, *, version_uid: str) -> Any:  # pragma: no cover - not under test
        raise AssertionError("not under test")

    def list_portal_blocks(self, *, version_uid: str) -> PortalBlockIndexView:
        self.asked.append(("list", version_uid))
        if self.status == "not_produced":
            return PortalBlockIndexView(version_uid, "not_produced", None, ())
        return PortalBlockIndexView(version_uid, "produced", RUN, BLOCKS)

    def read_portal_block_crop(self, *, version_uid: str, portal_block_id: str) -> PortalCropContent:
        self.asked.append(("crop", version_uid, portal_block_id))
        return PortalCropContent("image/png", "c" * 64, PNG)


@pytest.fixture
def client() -> tuple[TestClient, FakeBlocks]:
    fake = FakeBlocks()
    router = APIRouter()
    build_block_routes(router, fake)  # type: ignore[arg-type]
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(CorrelationMiddleware)
    return TestClient(app), fake


def test_the_listing_pages_in_the_ports_order_and_the_cursor_walks_every_block_once(client) -> None:
    http, _ = client
    seen: list[str] = []
    cursor = None
    for _ in range(10):
        params: dict[str, Any] = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        answer = http.get(f"/versions/{VERSION}/portal-blocks", params=params)
        assert answer.status_code == 200
        body = answer.json()
        assert body["status"] == "produced" and body["produced_by_run_id"] == RUN
        assert body["block_count"] == 5, "block_count is the version's, not the page's"
        seen += [item["portal_block_id"] for item in body["items"]]
        cursor = body["page"]["next_cursor"]
        if cursor is None:
            break
    assert seen == [b.portal_block_id for b in BLOCKS]
    assert len(seen) == len(set(seen))


def test_a_stamp_has_a_null_ordinal_and_sorts_after_the_numbered_blocks_of_its_page(client) -> None:
    http, _ = client
    items = http.get(f"/versions/{VERSION}/portal-blocks").json()["items"]
    assert [(i["page_number"], i["ordinal"]) for i in items] == [(1, 0), (1, 1), (1, None), (2, 0), (2, None)]


def test_the_cursor_key_is_strictly_increasing_along_the_ports_order() -> None:
    """The cursor locates a key, so a key that ties or runs backwards loses or repeats a block.

    A null ordinal must take a key above every numbered block of its page: that is the only
    reason a stamp is not paged before block zero.
    """
    from auditmanager.api.routers.blocks import _portal_sort_key

    keys = [_portal_sort_key(block) for block in BLOCKS]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert _portal_sort_key(_block(9, page=1, ordinal=None)) > _portal_sort_key(_block(8, page=1, ordinal=10**9))
    assert _portal_sort_key(_block(9, page=1, ordinal=None)) < _portal_sort_key(_block(8, page=2, ordinal=0))


def test_not_produced_is_a_200_with_no_items_and_no_run(client) -> None:
    http, fake = client
    fake.status = "not_produced"
    body = http.get(f"/versions/{VERSION}/portal-blocks").json()
    assert body == {
        "version_uid": VERSION, "status": "not_produced", "produced_by_run_id": None,
        "block_count": 0, "items": [], "page": {"next_cursor": None},
    }


def test_a_malformed_identity_never_reaches_the_port(client) -> None:
    http, fake = client
    assert http.get("/versions/not-a-version/portal-blocks").status_code == 422
    # a ULID is not a portal block id: the external pattern is 32 hexadecimal digits
    assert http.get(f"/versions/{VERSION}/portal-blocks/blk_01ARZ3NDEKTSV4RRFFQ69G5FAV/crop").status_code == 422
    assert http.get(f"/versions/{VERSION}/portal-blocks/blk_{'A' * 32}/crop").status_code == 422
    assert fake.asked == []


def test_the_crop_is_streamed_as_a_png_with_the_wire_header_order(client) -> None:
    http, fake = client
    block = f"blk_{3:032x}"
    answer = http.get(f"/versions/{VERSION}/portal-blocks/{block}/crop")
    assert answer.status_code == 200 and answer.content == PNG
    assert answer.headers["content-type"] == "image/png"
    assert answer.headers["content-length"] == str(len(PNG))
    assert fake.asked == [("crop", VERSION, block)]
    assert list(answer.headers)[:2] == ["content-type", "content-length"]


# --- the shipped adapters until their lanes -----------------------------------------------


def test_the_shipped_block_adapter_refuses_both_reads_until_geometry_serves_them() -> None:
    adapter = BlockAdapter(session_factory=None, blob_store=None)  # type: ignore[arg-type]
    for call in (
        lambda: adapter.list_portal_blocks(version_uid=VERSION),
        lambda: adapter.read_portal_block_crop(version_uid=VERSION, portal_block_id=f"blk_{0:032x}"),
    ):
        with pytest.raises(DomainError) as refused:
            call()
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert dict(refused.value.detail_fields) == {"dependency": "portal_blocks"}


def test_the_document_adapter_hands_the_service_the_handle_it_was_given_unread() -> None:
    """`W55B-STREAM-01` retired the whole-body read `W55B-SEAL-01` left in this adapter: the
    port takes a file handle and the service takes the same handle, positioned where it was
    given -- nothing between the router and the envelope reads the upload."""
    seen: dict[str, Any] = {}

    class Service:
        def upload_single_pdf(self, **kwargs: Any) -> Any:
            seen.update(kwargs)
            raise RuntimeError("stop after the call; the outcome is not under test")

    adapter = DocumentAdapter(Service())
    handle = io.BytesIO(b"PK\x03\x04 a bundle")
    with pytest.raises(RuntimeError):
        adapter.upload_document(
            project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", content=handle,
            source_filename="bundle.zip", display_title=None, idempotency_key="k" * 8,
        )
    assert seen["content"] is handle and handle.tell() == 0
