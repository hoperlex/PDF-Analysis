"""The six «Оптимизация проекта» operations (`W60-PRICE-LIST-01`): price lists, vendor lists.

* ``uploadPriceList`` -- ``POST /projects/{project_uid}/price-lists``: one CSV or XLSX price
  list (at most 10 MiB, inside the transport's ordinary 26 MiB body cap), stored as the
  project's newest immutable revision bound to its file. ``Idempotency-Key`` required.
* ``listPriceListRevisions`` -- ``GET /projects/{project_uid}/price-lists``.
* ``listPriceListPositions`` -- ``GET /price-lists/{price_list_id}/positions``: one page, the
  revision and its parse report.
* ``getEffectiveVendorLists`` -- ``GET /projects/{project_uid}/vendor-lists``: all fifteen
  sections as they apply to the project.
* ``setGlobalVendorList`` -- ``PUT /vendor-lists/{section_code}`` (``admin``).
* ``setProjectVendorList`` -- ``PUT /projects/{project_uid}/vendor-lists/{section_code}``
  (``expert``; ``mode: inherit`` removes the override).

The routes parse, call one port method and render; the rules -- roles read in the writing
transaction, the parser, the exact repeats, the stale-writer check -- live in
``auditmanager.optimisation``. No operation here answers a total, a proposal or a price that
an uploaded price list does not state.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Path, Query
from pydantic import Field

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.multipart import (
    CheckedUpload,
    UploadRoute,
    require_a_strict_multipart_body,
)
from auditmanager.api.routers.ports import OptimisationPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_optimisation_routes"]

#: The contract declares the upload body as ``multipart/form-data`` and only that.
_MULTIPART = "multipart/form-data"

OffsetParam = Annotated[
    Annotated[int, Field(ge=0)],
    Query(description="Position in the revision's positions, in source-row order."),
]
LimitParam = Annotated[
    Annotated[int, Field(ge=1, le=500)],
    Query(description="Positions per answer."),
]
SectionCodeParam = Annotated[models.ProjectSection, Path()]


def build_optimisation_routes(router: APIRouter, optimisation: OptimisationPort) -> None:

    # Declared through ``add_api_route`` for ``route_class_override``: ``UploadRoute`` parses
    # the form under the upload's small part bounds, as it does for ``uploadDocument``.
    def upload_price_list(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        body: Annotated[models.UploadPriceListRequest, Form(media_type=_MULTIPART)],
        idempotency_key: RequiredIdempotencyKey,
        checked: Annotated[CheckedUpload, Depends(require_a_strict_multipart_body)],
    ) -> WireResponse:
        # `checked` refused a repeated, unnamed or filename-less part before this runs; the
        # closed model refused an undeclared one. The file handle goes to the port unread.
        del checked
        revision = optimisation.upload_price_list(
            project_uid=project_uid,
            content=body.file.file,
            source_filename=body.file.filename or "",
            default_currency=body.default_currency,
            idempotency_key=idempotency_key,
            user_uid=subject.user_uid,
        )
        return json_response(201, encode_json(revision.model_dump(mode="json")))

    router.add_api_route(
        "/projects/{project_uid}/price-lists",
        upload_price_list,
        methods=["POST"],
        operation_id="uploadPriceList",
        tags=["optimisation"],
        status_code=201,
        response_model=models.PriceListRevision,
        responses={
            **success(201, "The stored revision, new or an exact repeat replayed."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
        route_class_override=UploadRoute,
        description=(
            "Upload one price list of the project: a CSV (UTF-8 with or without a byte-order "
            "mark, UTF-16 with one, or Windows-1251; `;`, tab or `,` delimited) or an XLSX, "
            "whose first sheet is read; at most 10 MiB and 20 000 data rows. It becomes the "
            "project's newest immutable revision, bound to the stored file; earlier revisions "
            "stay readable. Every data row is accepted as a position or skipped with a reason "
            "in the revision's parse report; a price is read only from a plain number and is "
            "never guessed. `default_currency` applies to rows whose currency neither their "
            "own cell nor the price column's header names. A file that cannot be a price list "
            "is `422 validation_failed` with `field: content` and one `constraint`, and "
            "creates nothing. `expert` is required (`admin` alone is `permission_denied`); an "
            "unknown project is `404`. An exact repeat of the `Idempotency-Key` answers the "
            "stored revision; the same key with another file, file name, currency, project "
            "or caller is `409 idempotency_key_reuse`."
        ),
    )

    @router.get(
        "/projects/{project_uid}/price-lists",
        operation_id="listPriceListRevisions",
        tags=["optimisation"],
        status_code=200,
        response_model=models.PriceListRevisionList,
        responses={
            **success(200, "Every revision, newest first; the first is current."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "Every price-list revision of the project, newest first, the first flagged "
            "`is_current`. An unknown project is `404`. Any one role, `role:admin|expert`."
        ),
    )
    def list_price_list_revisions(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
    ) -> WireResponse:
        listing = optimisation.list_price_list_revisions(
            project_uid=project_uid, user_uid=subject.user_uid
        )
        return json_response(200, encode_json(listing.model_dump(mode="json")))

    @router.get(
        "/price-lists/{price_list_id}/positions",
        operation_id="listPriceListPositions",
        tags=["optimisation"],
        status_code=200,
        response_model=models.PriceListPositionPage,
        responses={
            **success(200, "One page of positions, the revision and its parse report."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "One page of a price-list revision's positions in source-row order (`offset`, "
            "`limit`, `next_offset`), with the revision and its parse report. Each unit "
            "price is its exact decimal text. An unknown revision is `404`. Any one role, "
            "`role:admin|expert`."
        ),
    )
    def list_price_list_positions(
        subject: CurrentSubject,
        price_list_id: Annotated[models.PriceListId, Path()],
        offset: OffsetParam = 0,
        limit: LimitParam = 100,
    ) -> WireResponse:
        page = optimisation.list_price_list_positions(
            price_list_id=price_list_id, offset=offset, limit=limit, user_uid=subject.user_uid
        )
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.get(
        "/projects/{project_uid}/vendor-lists",
        operation_id="getEffectiveVendorLists",
        tags=["optimisation"],
        status_code=200,
        response_model=models.EffectiveVendorLists,
        responses={
            **success(200, "All fifteen sections' vendor lists as they apply to the project."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "All fifteen sections' vendor lists as they apply to the project, in section "
            "order. For each: `source` `project` (the project's own latest revision, mode "
            "`list`), `global` (the administrator's latest) or `none`; the `effective` "
            "revision; and the latest revision of each scope. An unknown project is `404`. "
            "Any one role, `role:admin|expert`."
        ),
    )
    def get_effective_vendor_lists(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
    ) -> WireResponse:
        lists = optimisation.get_effective_vendor_lists(
            project_uid=project_uid, user_uid=subject.user_uid
        )
        return json_response(200, encode_json(lists.model_dump(mode="json")))

    @router.put(
        "/vendor-lists/{section_code}",
        operation_id="setGlobalVendorList",
        tags=["optimisation"],
        status_code=200,
        response_model=models.VendorListRevision,
        responses={
            **success(200, "The global revision now in force, new or an exact repeat."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "Set a section's global vendor list as a whole new immutable revision with its "
            "author and time; an empty list is an explicit \"no restriction\". An exact repeat "
            "of the latest revision writes nothing and answers it. With "
            "`expected_vendor_list_id` present (`null`: no revision was read), a different "
            "latest revision is `409 conflict` with `conflict_reason: vendor_list_changed` and "
            "nothing is written. A section code outside the fifteen addresses no vendor list "
            "and is `404`. `admin` is required (`required_capability: role:admin`)."
        ),
    )
    def set_global_vendor_list(
        subject: CurrentSubject,
        section_code: SectionCodeParam,
        body: models.SetGlobalVendorListRequest,
    ) -> WireResponse:
        revision = optimisation.set_global_vendor_list(
            section_code=section_code.value,
            entries=body.entries,
            expected_vendor_list_id=body.expected_vendor_list_id,
            expect_current="expected_vendor_list_id" in body.model_fields_set,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(revision.model_dump(mode="json")))

    @router.put(
        "/projects/{project_uid}/vendor-lists/{section_code}",
        operation_id="setProjectVendorList",
        tags=["optimisation"],
        status_code=200,
        response_model=models.SectionVendorList,
        responses={
            **success(200, "The section's vendor lists for the project after the change."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "Set the project's own vendor list for a section (`mode: list`, possibly empty: "
            "no restriction for this project) or remove it (`mode: inherit`, `entries: []`), "
            "as a new immutable revision with its author and time; the answer is the "
            "section's state for the project afterwards. An exact repeat writes nothing; an "
            "`inherit` with no override in force writes nothing. Entries with `inherit` are "
            "`422` (`constraint: inherit_has_no_entries`); a stale `expected_vendor_list_id` "
            "is `409` (`conflict_reason: vendor_list_changed`). `expert` is required (`admin` "
            "alone is `permission_denied`); an unknown project is `404`."
        ),
    )
    def set_project_vendor_list(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        section_code: SectionCodeParam,
        body: models.SetProjectVendorListRequest,
    ) -> WireResponse:
        state = optimisation.set_project_vendor_list(
            project_uid=project_uid,
            section_code=section_code.value,
            mode=body.mode.value,
            entries=body.entries,
            expected_vendor_list_id=body.expected_vendor_list_id,
            expect_current="expected_vendor_list_id" in body.model_fields_set,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(state.model_dump(mode="json")))
