"""``getVersionBlocks``, ``listVersionPortalBlocks``, ``listRunFindingBlocks`` and ``streamVersionPortalBlockCrop``.

`W45-BLOCKS` and `W55B-SEAL-01`. Grouped with the ``documents`` tag, and addressed off
``/versions/{version_uid}``, for the reason ``BlockPort.get_block_index`` states: the
geometry is a property of the version, not of any one run of it.

The two portal-block operations read what a portal bundle brought: its blocks, the text the
portal recognised in them and the descriptions it wrote for its images, plus the crops this
product cut itself from the PDF. **Nothing here fetches or serves a portal URL**: the
bundle's ``crop_url`` values are capability links and never leave the archive.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.ports import BlockPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.blocks import (
    PortalBlockView,
    portal_block_page_body,
    version_block_index_body,
)
from auditmanager.api.schemas.common import paginate

__all__ = ["build_block_routes"]

_PNG: Final[str] = "image/png"

#: How long a browser may keep a crop without asking again (`W55B-FIX`, X-4). ``private``: it
#: is behind the seam and no shared cache may hold it. An hour is the credential's own lifetime
#: (``security.TOKEN_LIFETIME_SECONDS``): a crop is the deterministic render of an immutable
#: version's block, content-addressed, and changes only when a later run renders it otherwise.
CROP_MAX_AGE_SECONDS: Final[int] = 3600

#: ``page, ordinal, id`` made comparable as text. The cursor carries a tuple of strings and
#: never a row number (``schemas.common.encode_cursor``), so the integers are zero-padded
#: and a null ordinal -- a stamp -- takes the widest value, which sorts it last on its page.
_NO_ORDINAL: Final[str] = "9" * 12


def _portal_sort_key(view: object) -> tuple[str, ...]:
    block: PortalBlockView = view  # type: ignore[assignment]
    ordinal = _NO_ORDINAL if block.ordinal is None else f"{block.ordinal:012d}"
    return (f"{block.page_number:012d}", ordinal, block.portal_block_id)


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

    @router.get(
        "/versions/{version_uid}/portal-blocks",
        operation_id="listVersionPortalBlocks",
        tags=["documents"],
        status_code=200,
        response_model=models.PortalBlockPage,
        responses={
            **success(
                200,
                "One page of the version's portal blocks, or its not-yet-produced status.",
            ),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def list_version_portal_blocks(
        version_uid: Annotated[models.VersionUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        index = blocks.list_portal_blocks(version_uid=version_uid)
        page = paginate(index.blocks, limit=limit, cursor=cursor, sort_key=_portal_sort_key)
        return json_response(
            200, encode_json(portal_block_page_body(index, page.items, page.next_cursor))
        )

    @router.get(
        "/versions/{version_uid}/sheet-labels",
        operation_id="listVersionSheetLabels",
        tags=["documents"],
        status_code=200,
        response_model=models.VersionSheetLabelList,
        responses={
            **success(200, "Each page of the version with its sheet label, or the not-yet-produced status."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "`UI-PARITY-P0O` (contract 1.30.0): the version's pages with the drawing sheet their portal blocks name "
            "(`page_label`) and how many blocks each holds, as the original's «Лист» beside a finding's page. Read from the "
            "same portal geometry as `listVersionPortalBlocks` (the most recent run whose `page_geometry_extraction` "
            "succeeded), one entry per page that has a block; a page whose blocks name different sheets carries no "
            "`page_label`, and a page number is never passed off as a sheet. A version no run of which has produced the "
            "geometry answers `status: \"not_produced\"` and no items. An unknown version is `404`. Any one role (`R-80`)."
        ),
    )
    def list_version_sheet_labels(version_uid: Annotated[models.VersionUid, Path()]) -> WireResponse:
        labels = blocks.list_sheet_labels(version_uid=version_uid)
        return json_response(200, encode_json(labels.model_dump(mode="json", exclude_none=True)))

    @router.get(
        "/runs/{run_id}/finding-blocks",
        operation_id="listRunFindingBlocks",
        tags=["findings"],
        status_code=200,
        response_model=models.RunFindingBlockLinks,
        responses={
            **success(200, "Each published finding of the run with the portal blocks that hold its evidence, or the not-yet-produced status."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "`UI-PARITY-C6` (contract 1.41.0): which portal blocks a finding's evidence sits in, for the original's block "
            "thumbnails under a finding and the number of findings on a block tile. Derived on read, nothing stored: the "
            "evidence's characters are located on their page by the run's text-layer block index (the line boxes) and the "
            "page inventory (the page sizes), and a portal block holds the evidence when it covers at least half of the "
            "evidence's box on that page. One item per published finding, `portal_block_ids` in the portal list's order and "
            "empty when no block holds the evidence; `unlinked_pages` are the pages where the portal's raster does not "
            "describe the PDF page and no link can be derived (their blocks are unknown, not free of findings). A run "
            "without text-layer geometry, or a version without portal geometry, answers `status: \"not_produced\"` and no "
            "items. An unknown run is `404`. Any one role (`R-80`)."
        ),
    )
    def list_run_finding_blocks(run_id: Annotated[models.RunId, Path()]) -> WireResponse:
        links = blocks.list_run_finding_blocks(run_id=run_id)
        return json_response(200, encode_json(links.model_dump(mode="json", exclude_none=True)))

    @router.get(
        "/versions/{version_uid}/portal-blocks/{portal_block_id}/crop",
        operation_id="streamVersionPortalBlockCrop",
        tags=["documents"],
        status_code=200,
        response_class=WireResponse,
        responses={
            **success(
                200,
                "The PNG this product cut for one IMAGE block.",
                content={_PNG: {"schema": {"type": "string", "format": "binary"}}},
            ),
            **envelope_responses(401, 403, 404, 500, 503),
        },
    )
    def stream_version_portal_block_crop(
        version_uid: Annotated[models.VersionUid, Path()],
        portal_block_id: Annotated[models.PortalBlockId, Path()],
    ) -> WireResponse:
        crop = blocks.read_portal_block_crop(
            version_uid=version_uid, portal_block_id=portal_block_id
        )
        # `W55B-FIX` (X-4): the PNG's own digest as its entity tag, and a private lifetime, so
        # the browser keeps the crops a reader scrolls back to instead of asking the API --
        # which re-reads and re-verifies the version's artifacts for every crop -- again. The
        # BFF forwards both (``credentialed-forward.ts``). No conditional ``304`` is answered:
        # the port reads the PNG to verify it before the digest could be compared, so it would
        # save the transfer and none of the work, and the contract declares no ``304``.
        return WireResponse(
            200,
            (
                ("Content-Type", crop.media_type),
                ("Content-Length", str(len(crop.content))),
                ("ETag", f'"{crop.sha256}"'),
                ("Cache-Control", f"private, max-age={CROP_MAX_AGE_SECONDS}"),
            ),
            crop.content,
        )
