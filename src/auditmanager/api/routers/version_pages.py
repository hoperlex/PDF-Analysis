"""The page reads of a version (`CMP-SEAL-C0` sealed them; `CMP-PROFILE-01` serves them, ADR-0025 decision 9).

A page is addressed by the identity of its profile (``cpr_``), never by its number: a page number is
an ordinal and the contract forbids addressing anything by one. ``listVersionPageProfiles`` returns
the profiles a version has, each with its ``page_number``; the profile, the stored preview and
thumbnail and one tile of the bounded pyramid are then read by that identity. The API process never
loads PDFium: it reads what the worker stored, and the two tile levels that are not stored are
rendered in a ceilinged child process (addendum of 2026-10-27). Roles: any one role. A profile,
image or tile that does not exist is ``404``; a tile whose child ended without a result, or for which
no render slot was free, is ``503 dependency_unavailable``.
"""

from __future__ import annotations

import hashlib
from typing import Annotated, Final

from fastapi import APIRouter, Path, Query

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.ports import VersionPagePort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models

__all__ = [
    "MAX_TILE_INDEX",
    "MAX_TILE_LEVEL",
    "TILE_CACHE_CONTROL",
    "build_version_page_routes",
    "tile_response",
]

_PNG: Final[str] = "image/png"
_TAGS: Final[list[str]] = ["comparison"]
#: The pyramid is bounded (ADR-0025 decision 9); these are the structural bounds of the address.
MAX_TILE_LEVEL: Final[int] = 12
MAX_TILE_INDEX: Final[int] = 4095

_ProfileId = Annotated[models.ComparisonPageProfileId, Path()]
_PNG_CONTENT = {_PNG: {"schema": {"type": "string", "format": "binary"}}}

#: `CMP-C1-FIX-A` item 4 (`CMP-VIEWER-01` section 12 item 1). A tile of a page and a tile of a pair are immutable for their
#: inputs -- a page profile is a frozen row, a sheet pair that has an overlay is `done` and its result never changes -- so a
#: browser may keep one for the hour: the original sends the same (`private, max-age=3600`). `private`: the tile is a page of
#: a client's drawing, never for a shared cache.
TILE_CACHE_CONTROL: Final[str] = "private, max-age=3600"
#: Change this when the pixels of a tile change for the same inputs (the renderer, the palette of the overlay): the entity tag
#: of every tile changes with it.
_TILE_EPOCH: Final[str] = "1"


def tile_response(content: bytes, *identity: object) -> WireResponse:
    """A tile PNG with the headers of an immutable tile (`CMP-C1-FIX-A` item 4).

    ``identity`` is what names the bytes: the kind of tile, the id of the page profile or of the sheet pair, and the tile
    parameters. The entity tag is a hash of it, **weak** (``W/``): it says the tile is the same picture, not the same bytes
    (the renderer of a later release may encode otherwise). The contract of these operations declares no ``304`` and no
    ``If-None-Match``, so none is answered: the browser's copy is kept by ``Cache-Control`` and the tag only names it."""
    token = "\0".join(("cmp-tile", _TILE_EPOCH, *(str(part) for part in identity)))
    tag = 'W/"' + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32] + '"'
    return WireResponse(
        200,
        (
            ("Content-Type", _PNG),
            ("Content-Length", str(len(content))),
            ("ETag", tag),
            ("Cache-Control", TILE_CACHE_CONTROL),
        ),
        content,
    )


def _png(content: bytes) -> WireResponse:
    return WireResponse(
        200, (("Content-Type", _PNG), ("Content-Length", str(len(content)))), content
    )


def build_version_page_routes(router: APIRouter, pages: VersionPagePort) -> None:
    @router.get(
        "/versions/{version_uid}/page-profiles",
        operation_id="listVersionPageProfiles", tags=_TAGS, status_code=200,
        response_model=models.VersionPageProfilePage,
        responses={**success(200, "One page of the version's stored page profiles, by page number."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_version_page_profiles(
        version_uid: Annotated[models.VersionUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = pages.list_profiles(version_uid=version_uid, cursor=cursor, limit=limit)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/page-profiles/{comparison_page_profile_id}",
        operation_id="getVersionPageProfile", tags=_TAGS, status_code=200,
        response_model=models.VersionPageProfile,
        responses={**success(200, "The deterministic profile of the page."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_version_page_profile(comparison_page_profile_id: _ProfileId) -> WireResponse:
        view = pages.get_profile(page_profile_id=comparison_page_profile_id)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/page-profiles/{comparison_page_profile_id}/preview",
        operation_id="streamVersionPagePreview", tags=_TAGS, status_code=200,
        response_class=WireResponse,
        responses={**success(200, "The stored preview PNG of the page.", content=_PNG_CONTENT),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def stream_version_page_preview(comparison_page_profile_id: _ProfileId) -> WireResponse:
        return _png(pages.read_preview(page_profile_id=comparison_page_profile_id))

    @router.get(
        "/page-profiles/{comparison_page_profile_id}/thumbnail",
        operation_id="streamVersionPageThumbnail", tags=_TAGS, status_code=200,
        response_class=WireResponse,
        responses={**success(200, "The stored thumbnail PNG of the page.", content=_PNG_CONTENT),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def stream_version_page_thumbnail(comparison_page_profile_id: _ProfileId) -> WireResponse:
        return _png(pages.read_thumbnail(page_profile_id=comparison_page_profile_id))

    @router.get(
        "/page-profiles/{comparison_page_profile_id}/tile",
        operation_id="streamVersionPageTile", tags=_TAGS, status_code=200,
        response_class=WireResponse,
        responses={**success(200, "One tile PNG of the page's bounded pyramid.",
                             content=_PNG_CONTENT),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def stream_version_page_tile(
        comparison_page_profile_id: _ProfileId,
        level: Annotated[int, Query(ge=0, le=MAX_TILE_LEVEL)],
        column: Annotated[int, Query(ge=0, le=MAX_TILE_INDEX)],
        row: Annotated[int, Query(ge=0, le=MAX_TILE_INDEX)],
    ) -> WireResponse:
        content = pages.read_tile(
            page_profile_id=comparison_page_profile_id, level=level, column=column, row=row
        )
        return tile_response(content, "page", comparison_page_profile_id, level, column, row)
