"""Release API declarations. The ReleasesPort implementation belongs to W52 Stage C."""

from __future__ import annotations

from fastapi import APIRouter

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import ReleasesPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_release_routes"]


def build_release_routes(router: APIRouter, releases: ReleasesPort) -> None:
    @router.get(
        "/system/version",
        operation_id="getProductVersion",
        tags=["releases"],
        status_code=200,
        response_model=models.ProductVersion,
        responses={
            **success(200, "The running product, build and contract versions."),
            **envelope_responses(401, 403, 500, 503),
        },
        summary="Read the running product version.",
    )
    def get_product_version(subject: CurrentSubject) -> WireResponse:
        return json_response(200, encode_json(releases.get_product_version().model_dump(mode="json")))

    @router.get(
        "/releases",
        operation_id="listReleases",
        tags=["releases"],
        status_code=200,
        response_model=models.ReleaseList,
        responses={
            **success(200, "Visible releases and unread versions for this account."),
            **envelope_responses(401, 403, 500, 503),
        },
        summary="List visible releases and what is new.",
    )
    def list_releases(subject: CurrentSubject) -> WireResponse:
        result = releases.list_releases(user_uid=subject.user_uid)
        return json_response(200, encode_json(result.model_dump(mode="json")))

    @router.put(
        "/me/release-notes",
        operation_id="markReleaseNotesRead",
        tags=["account"],
        status_code=204,
        response_model=None,
        responses={
            **success(204, "The account's read mark was raised or already covered this version."),
            **envelope_responses(401, 403, 422, 500, 503),
        },
        summary="Mark release notes read through a version.",
    )
    def mark_release_notes_read(
        subject: CurrentSubject, body: models.MarkReleaseNotesReadRequest
    ) -> WireResponse:
        releases.mark_read(user_uid=subject.user_uid, read_through=body.read_through)
        return WireResponse(204, ())
