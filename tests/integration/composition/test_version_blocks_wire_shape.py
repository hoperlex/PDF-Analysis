"""`getVersionBlocks`, at the wire. `W45-BLOCKS`.

Three states, and the point of this file is that the middle one is not the other two
wearing an empty array:

* an unknown ``version_uid`` -- ``404 not_found``, the same answer every other parented
  ``GET`` gives (``tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py``
  now sweeps this operation too, since it addresses ``version_uid`` in its path);
* a version that exists but that no run has carried through
  ``page_geometry_extraction`` -- ``200`` with ``status: "not_produced"`` and
  ``blocks: []``;
* a version whose run reached ``published`` -- ``200`` with ``status: "produced"`` and
  real geometry, driven the same way
  ``test_a_published_run_reports_itself.py`` drives a run to a terminal: over HTTP, to
  the carrier's own completion.

``tests/integration/runs/test_w45_blocks_version_block_index.py`` covers the "produced"
shape in more depth, directly against the adapter; this file is the one that proves the
distinction is visible on the wire, which is the thing a browser actually reads.

`W55B-GEOMETRY-01` adds the same three states for ``listVersionPortalBlocks`` and its crop,
``streamVersionPortalBlockCrop``, on the same uploaded bundle: ``404`` for an unknown
version, ``not_produced`` before a run (and no crop), and after a published run the blocks
joined with the recognised text, the portal's descriptions and the crops this product cut,
whose bytes the crop operation streams under the listed SHA-256.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE

DEPLOYMENT_SECRET = "version-blocks-wire-shape-token"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_PDF = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "ar_baseline.pdf"
#: `W55B-INGEST-01`: an upload is a portal bundle; this is the one around the baseline PDF.
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"
ABSENT_VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
#: Two blocks of ``ar_baseline.zip``'s list: an IMAGE block (a rectangle) and a TEXT block.
IMAGE_BLOCK = "blk_91bef18c38cab738e6446aaa100fbd33"
TEXT_BLOCK = "blk_285e293c6614ba032cb547f00c83b5f6"

_STATIC_TOKEN_CACHE: str | None = None


def static_token() -> str:
    global _STATIC_TOKEN_CACHE
    if _STATIC_TOKEN_CACHE is None:
        from am_test_accounts import provisioned_credential

        _STATIC_TOKEN_CACHE = provisioned_credential(
            DEPLOYMENT_SECRET, "version-blocks-wire-shape"
        )
    return _STATIC_TOKEN_CACHE


@pytest.fixture(scope="module")
def app() -> Any:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    from auditmanager.api.app import create_asgi_app

    environ = dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    }
    asgi_app = create_asgi_app(environ=environ)
    return TestClient(asgi_app, raise_server_exceptions=False)


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {static_token()}"}


def _publish_a_version(app: TestClient, tag: str) -> str:
    """One project, one uploaded document, no run. Returns the version_uid."""
    answer = app.post(
        "/projects",
        headers=_auth() | {IDEMPOTENCY_HEADER: f"{tag}-prj", "Content-Type": "application/json"},
        content=json.dumps({"name": f"W45-BLOCKS wire {tag}"}).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    project_uid = answer.json()["project_uid"]

    boundary = "w45blockswireboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    tail = (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; "
        f'name="display_title"\r\n\r\nW45-BLOCKS wire {tag}\r\n--{boundary}--\r\n'
    ).encode("utf-8")
    answer = app.post(
        f"/projects/{project_uid}/documents",
        headers=_auth()
        | {
            IDEMPOTENCY_HEADER: f"{tag}-doc",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + tail,
    )
    assert answer.status_code == 201, answer.content
    return answer.json()["version_uid"]


def test_an_unknown_version_is_refused_not_answered_empty(app: TestClient) -> None:
    answer = app.get(f"/versions/{ABSENT_VERSION}/blocks", headers=_auth())
    assert answer.status_code == 404, answer.content
    body = answer.json()
    assert body["error_code"] == "not_found", body


def test_a_version_with_no_run_answers_not_produced_not_an_empty_blocks_array(
    app: TestClient,
) -> None:
    version_uid = _publish_a_version(app, f"notprod-{uuid.uuid4().hex[:8]}")

    answer = app.get(f"/versions/{version_uid}/blocks", headers=_auth())
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert body["version_uid"] == version_uid
    assert body["status"] == "not_produced", body
    assert body["blocks"] == []
    assert body["block_count"] == 0
    assert body["produced_by_run_id"] is None
    assert body["text_layer_sha256"] is None
    assert "crops" not in body and "page_crops" not in body, (
        "this operation does not carry crops at all -- not even an empty one"
    )

    portal = app.get(f"/versions/{version_uid}/portal-blocks", headers=_auth())
    assert portal.status_code == 200, portal.content
    assert portal.json() == {
        "version_uid": version_uid, "status": "not_produced", "produced_by_run_id": None,
        "block_count": 0, "items": [], "page": {"next_cursor": None},
    }
    crop = app.get(f"/versions/{version_uid}/portal-blocks/{IMAGE_BLOCK}/crop", headers=_auth())
    assert crop.status_code == 404 and crop.json()["error_code"] == "not_found", crop.content


def test_an_unknown_version_is_refused_by_both_portal_reads(app: TestClient) -> None:
    for path in (
        f"/versions/{ABSENT_VERSION}/portal-blocks",
        f"/versions/{ABSENT_VERSION}/portal-blocks/{IMAGE_BLOCK}/crop",
    ):
        answer = app.get(path, headers=_auth())
        assert answer.status_code == 404, (path, answer.content)
        assert answer.json()["error_code"] == "not_found"


def test_a_published_run_flips_the_status_and_fills_the_blocks(app: TestClient) -> None:
    tag = f"prod-{uuid.uuid4().hex[:8]}"
    version_uid = _publish_a_version(app, tag)

    answer = app.post(
        "/runs",
        headers=_auth() | {IDEMPOTENCY_HEADER: f"{tag}-run", "Content-Type": "application/json"},
        content=json.dumps({"version_uid": version_uid}).encode("utf-8"),
    )
    assert answer.status_code == 202, answer.content
    started = answer.json()
    assert started["state"] == "queued", started
    assert app.app.state.run_carrier.drain(timeout=300), "the run never finished"

    status_answer = app.get(f"/runs/{started['run_id']}", headers=_auth())
    assert status_answer.json()["state"] == "published", status_answer.content

    answer = app.get(f"/versions/{version_uid}/blocks", headers=_auth())
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert body["status"] == "produced", body
    assert body["produced_by_run_id"] == started["run_id"]
    assert body["block_count"] == len(body["blocks"]) > 0
    assert body["text_layer_sha256"] is not None
    first = body["blocks"][0]
    assert set(first["bbox"]) == {"x0", "y0", "x1", "y1"}
    assert first["bbox_unit"] == "pt"
    assert first["bbox_origin"] == "top_left"


def test_a_published_run_serves_the_portal_blocks_and_their_crops(app: TestClient) -> None:
    import hashlib

    tag = f"portal-{uuid.uuid4().hex[:8]}"
    version_uid = _publish_a_version(app, tag)
    answer = app.post(
        "/runs",
        headers=_auth() | {IDEMPOTENCY_HEADER: f"{tag}-run", "Content-Type": "application/json"},
        content=json.dumps({"version_uid": version_uid}).encode("utf-8"),
    )
    assert answer.status_code == 202, answer.content
    run_id = answer.json()["run_id"]
    assert app.app.state.run_carrier.drain(timeout=300), "the run never finished"

    answer = app.get(f"/versions/{version_uid}/portal-blocks", headers=_auth())
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert (body["status"], body["produced_by_run_id"], body["block_count"]) == ("produced", run_id, 12)
    assert len(body["items"]) == 12 and body["page"]["next_cursor"] is None
    assert b"crop_url" not in answer.content and b"://" not in answer.content
    items = {item["portal_block_id"]: item for item in body["items"]}
    text_block, image_block = items[TEXT_BLOCK], items[IMAGE_BLOCK]
    assert text_block["recognised_text"]["quote_source"] == "recognised"
    assert text_block["recognised_text"]["text"] and "crop" not in text_block
    assert "portal_description" not in text_block and "polygon_points" not in text_block
    assert image_block["portal_description"] and "recognised_text" not in image_block
    assert image_block["geometry"] == "ok" and image_block["crop"]["media_type"] == "image/png"
    assert sum(1 for item in body["items"] if "polygon_points" in item) == 1
    assert sum(1 for item in body["items"] if "crop" in item) == 2

    crop = app.get(f"/versions/{version_uid}/portal-blocks/{IMAGE_BLOCK}/crop", headers=_auth())
    assert crop.status_code == 200, crop.content
    assert crop.headers["content-type"] == "image/png"
    assert crop.headers["content-length"] == str(len(crop.content))
    assert hashlib.sha256(crop.content).hexdigest() == image_block["crop"]["sha256"]
    missing = app.get(f"/versions/{version_uid}/portal-blocks/{TEXT_BLOCK}/crop", headers=_auth())
    assert missing.status_code == 404 and missing.json()["error_code"] == "not_found"
