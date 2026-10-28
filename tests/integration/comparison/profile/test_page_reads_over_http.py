"""The five sealed page reads, driven through the composed application (`CMP-PROFILE-01`).

``create_app`` builds the real composition root, so this is the proof that ``VersionPageAdapter`` is wired with the
lane's session factory and object store and that the router, the role seam and the error envelope carry what the
reader returns: the listing by page number with an opaque cursor, the profile, the stored preview and thumbnail,
a stored tile, a tile rendered on request, and every refusal (an absent profile, a tile outside the pyramid, a
query outside its bounds). The 503 of a tile whose child ended without a result is asserted at the reader, with a
real child under a ceiling too low to start (``test_build_and_read_profiles.py``): the composed application owns
its own renderer.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.limits import ChildLimits

SECRET = "page-reads-static-token"
PNG = b"\x89PNG\r\n\x1a\n"
MIB = 1024 * 1024


@pytest.fixture(scope="module")
def http(session_factory) -> TestClient:  # session_factory makes sure the lane's environment is loaded
    assert os.environ.get("DATABASE_URL"), "the lane's .env must be loaded"
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: SECRET}
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def token() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(SECRET, "page-reads-suite")


def _get(http: TestClient, token: str, path: str, **query: Any):
    return http.get(path, params=query or None, headers={"Authorization": f"Bearer {token}"})


def _json(response) -> Any:
    return json.loads(response.content)


@pytest.fixture(scope="module")
def built(session_factory, blob_store, fixtures_dir, seed_version) -> dict[str, Any]:
    """A version of VS-1 v1 (an A1 plan and five smaller sheets) with its profiles built, and one more whose
    A1 page ended without a result."""
    good = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6)
    build_version_page_profiles(session_factory, blob_store, good)
    failed = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6)
    build_version_page_profiles(session_factory, blob_store, failed, render_limits=ChildLimits(144 * MIB, 300, 600.0))
    return {"good": good, "failed": failed}


@pytest.fixture(scope="module")
def seed_version(session_factory, blob_store):  # module-scoped twin of the function-scoped fixture
    import hashlib
    from pathlib import Path

    from sqlalchemy import text

    from auditmanager.comparison.profile.publish import ProfileBlobPublisher
    from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT
    from auditmanager.shared.db import session_scope
    from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid

    def seed(pdf_path: Path, page_count: int) -> str:
        data = pdf_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        project, document, version = str(ProjectUid.new()), str(DocumentUid.new()), str(VersionUid.new())
        blob_id = ProfileBlobPublisher(session_factory, blob_store).publish(data, role="source_document", media_type="application/pdf")
        with session_scope(session_factory) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'HTTP')"), {"p": project})
            session.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'K')"), {"d": document, "p": project})
            session.execute(
                text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
                     "VALUES (:v, :d, 1, 'application/pdf', :n, :s, :c)"),
                {"v": version, "d": document, "n": len(data), "s": digest, "c": page_count},
            )
            session.execute(
                text("INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                     "VALUES (:v, :r, :b, :s, :n, 'application/pdf')"),
                {"v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": digest, "n": len(data)},
            )
        return version

    return seed


def test_the_listing_pages_by_page_number_with_an_opaque_cursor(http, token, built) -> None:
    first = _get(http, token, f"/versions/{built['good']}/page-profiles", limit=4)
    assert first.status_code == 200, first.text
    body = _json(first)
    assert [item["page_number"] for item in body["items"]] == [1, 2, 3, 4]
    assert body["page"]["next_cursor"] and "page_number" not in body["page"]["next_cursor"]
    second = _json(_get(http, token, f"/versions/{built['good']}/page-profiles", limit=4, cursor=body["page"]["next_cursor"]))
    assert [item["page_number"] for item in second["items"]] == [5, 6] and second["page"].get("next_cursor") is None
    item = body["items"][1]
    assert item["status"] == "ready" and item["algo_version"] == limits.ALGO_VERSION and len(item["content_key"]) == 64
    assert item["page_profile_id"].startswith("cpr_") and item["version_uid"] == built["good"]
    assert (item["has_text_layer"], item["preview_available"], item["thumbnail_available"]) == (True, True, True)
    assert item["word_count"] > 0 and item["vector_line_count"] > 0 and item["annotation_count"] == 0
    assert item["stamp"] == {
        "designation": "СИНТ-01-ЭМ", "sheet_number": "2", "sheet_name": "План освещения. Корпус 1, этаж 1",
        "revision_number": "0", "release_date": "2026-01-15",
    }
    assert (item["width_pt"], item["height_pt"], item["raster_width_px"]) == (1190.55, 841.89, 3308)
    assert "reason" not in item


def test_a_malformed_cursor_and_an_unknown_version_are_refused_not_an_empty_page(http, token, built) -> None:
    bad = _get(http, token, f"/versions/{built['good']}/page-profiles", cursor="not-a-cursor")
    assert bad.status_code == 422 and _json(bad)["error_code"] == "validation_failed"
    unknown = _get(http, token, "/versions/ver_01ARZ3NDEKTSV4RRFFQ69G5FAV/page-profiles")
    assert unknown.status_code == 404 and _json(unknown)["error_code"] == "not_found"


def test_the_profile_the_preview_the_thumbnail_and_the_stored_tile(http, token, built) -> None:
    listing = _json(_get(http, token, f"/versions/{built['good']}/page-profiles"))["items"]
    a1 = listing[4]
    profile = _get(http, token, f"/page-profiles/{a1['page_profile_id']}")
    assert profile.status_code == 200 and _json(profile) == a1
    preview = _get(http, token, f"/page-profiles/{a1['page_profile_id']}/preview")
    assert (preview.status_code, preview.headers["content-type"]) == (200, "image/png")
    assert preview.content.startswith(PNG) and len(preview.content) == 187156
    assert int(preview.headers["content-length"]) == len(preview.content)
    thumbnail = _get(http, token, f"/page-profiles/{a1['page_profile_id']}/thumbnail")
    assert thumbnail.status_code == 200 and len(thumbnail.content) == 11933
    tile = _get(http, token, f"/page-profiles/{a1['page_profile_id']}/tile", level=3, column=1, row=1)
    assert tile.status_code == 200 and tile.headers["content-type"] == "image/png" and tile.content.startswith(PNG)


def test_a_tile_of_level_0_and_1_is_rendered_on_request_and_the_edge_tile_is_the_page_edge(http, token, built) -> None:
    from io import BytesIO

    from PIL import Image

    a1 = _json(_get(http, token, f"/versions/{built['good']}/page-profiles"))["items"][4]
    base = f"/page-profiles/{a1['page_profile_id']}/tile"
    full = _get(http, token, base, level=0, column=6, row=4)
    assert full.status_code == 200 and Image.open(BytesIO(full.content)).size == (512, 512)
    edge = _get(http, token, base, level=0, column=12, row=9)
    assert edge.status_code == 200 and Image.open(BytesIO(edge.content)).size == (6623 - 12 * 512, 4678 - 9 * 512)
    half = _get(http, token, base, level=1, column=6, row=4)
    assert half.status_code == 200 and Image.open(BytesIO(half.content)).size == (3312 - 6 * 512, 2339 - 4 * 512)


def test_a_tile_outside_the_pyramid_or_the_bounds_and_an_absent_profile_are_refused(http, token, built) -> None:
    a1 = _json(_get(http, token, f"/versions/{built['good']}/page-profiles"))["items"][4]
    base = f"/page-profiles/{a1['page_profile_id']}/tile"
    for query in ({"level": 0, "column": 13, "row": 0}, {"level": 5, "column": 0, "row": 0}, {"level": 2, "column": 9, "row": 9}):
        response = _get(http, token, base, **query)
        assert response.status_code == 404 and _json(response)["error_code"] == "not_found", query
    for query in ({"level": 13, "column": 0, "row": 0}, {"level": 0, "column": 4096, "row": 0}, {"level": -1, "column": 0, "row": 0}, {}):
        assert _get(http, token, base, **query).status_code == 422, query
    absent = "/page-profiles/cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    for suffix in ("", "/preview", "/thumbnail"):
        response = _get(http, token, absent + suffix)
        assert response.status_code == 404 and _json(response)["error_code"] == "not_found"
    assert _get(http, token, absent + "/tile", level=0, column=0, row=0).status_code == 404


def test_a_page_that_ended_without_a_result_says_so_and_has_no_image(http, token, built) -> None:
    items = _json(_get(http, token, f"/versions/{built['failed']}/page-profiles"))["items"]
    failed = items[4]
    assert (failed["status"], failed["reason"]) == ("needs_review", "RENDER_FAILED")
    assert (failed["preview_available"], failed["thumbnail_available"], failed["has_text_layer"]) == (False, False, False)
    assert "stamp" not in failed and "raster_width_px" not in failed
    for suffix in ("/preview", "/thumbnail"):
        assert _get(http, token, f"/page-profiles/{failed['page_profile_id']}{suffix}").status_code == 404
    assert _get(http, token, f"/page-profiles/{failed['page_profile_id']}/tile", level=0, column=0, row=0).status_code == 404
    assert [item["status"] for item in items] == ["ready"] * 4 + ["needs_review", "ready"]


def test_without_a_credential_the_reads_are_refused(http, built) -> None:
    for path in (f"/versions/{built['good']}/page-profiles", "/page-profiles/cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"):
        assert http.get(path).status_code == 401
