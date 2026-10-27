"""The page reads of a version, sealed as stubs (`CMP-SEAL-C0`, ADR-0025 decision 9).

A page is addressed by the identity of its profile (``cpr_``), never by its number: a page number is
an ordinal and the contract forbids addressing anything by one. ``listVersionPageProfiles`` returns
the profiles a version has, each with its ``page_number``; the profile, the stored preview and
thumbnail and one tile of the bounded pyramid are then read by that identity. The API never calls
PDFium: it reads what the worker stored (`CMP-PROFILE-01` wires the port). Roles: any one role. A
profile or tile that does not exist is ``404``. Every operation answers ``503
dependency_unavailable`` until then.
"""

from __future__ import annotations

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

__all__ = ["MAX_TILE_INDEX", "MAX_TILE_LEVEL", "build_version_page_routes"]

_PNG: Final[str] = "image/png"
_TAGS: Final[list[str]] = ["comparison"]
#: The pyramid is bounded (ADR-0025 decision 9); these are the structural bounds of the address.
MAX_TILE_LEVEL: Final[int] = 12
MAX_TILE_INDEX: Final[int] = 4095

_ProfileId = Annotated[models.ComparisonPageProfileId, Path()]
_PNG_CONTENT = {_PNG: {"schema": {"type": "string", "format": "binary"}}}


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
        return _png(
            pages.read_tile(
                page_profile_id=comparison_page_profile_id, level=level, column=column, row=row
            )
        )
