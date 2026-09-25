"""``getVersionBlocks``. `W45-BLOCKS`.

Grouped with the ``documents`` tag, and addressed off ``/versions/{version_uid}``, for the
reason ``BlockPort.get_block_index`` states: the geometry is a property of the version, not
of any one run of it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import BlockPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.blocks import version_block_index_body

__all__ = ["build_block_routes"]


def build_block_routes(router: APIRouter, blocks: BlockPort) -> None:

    @router.get(
        "/versions/{version_uid}/blocks",
        operation_id="getVersionBlocks",
        tags=["documents"],
        status_code=200,
        response_model=models.VersionBlockIndex,
        responses={
            **success(
                200, "The block index for this version, or its not-yet-produced status."
            ),
            **envelope_responses(401, 403, 404, 500, 503),
        },
    )
    def get_version_blocks(
        version_uid: Annotated[models.VersionUid, Path()],
    ) -> WireResponse:
        view = blocks.get_block_index(version_uid=version_uid)
        return json_response(200, encode_json(version_block_index_body(view)))
