"""``getSpecificationPrices`` (`W60-OPT-MATCH-01`).

«Спецификация и цены»: one read addressed through the document set and its project,
``/projects/{project_uid}/documents/{document_uid}/specification-prices``. The server takes
the set's **current** version, requires an expert's persisted classification (any of the fifteen
sections; the section is reported and changes nothing in how the rows are read or priced), reads
the project's current price-list revision and the version's newest **published** run's saved text, extracts the specification rows deterministically and matches
each to the price list as ``matched``, ``ambiguous`` or ``unmatched`` with its reason.

**The path is proved first**: an unknown project, or a set of another project, is
``404 not_found`` (`D-67`). **Then a precondition that does not hold is an answer, not an
error**: ``200`` with one ``state`` -- ``version_unclassified``, ``price_list_missing``,
``analysis_missing``, ``text_unavailable``, ``specification_too_large`` (``section_not_ar`` stays
in the enum and is no longer produced) -- and the facts read before it stopped, never an empty
table.
A malformed identity or paging value is ``422``; a stored fact that contradicts its own
constraints is ``500``.

**Money**: a price and an amount appear only on a row matched to exactly one position in the
same unit with a numeric quantity; ``amount = quantity × unit_price``, exact decimal text,
never rounded; totals are per currency over those rows only and every other row is counted by
its one exclusion reason. Nothing is written. Any one role, ``role:admin|expert``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import Field

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import SpecificationPricesPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_specification_price_routes"]

_DOCUMENT_PATH = "/projects/{project_uid}/documents/{document_uid}"

RowOffsetParam = Annotated[
    Annotated[int, Field(ge=0)],
    Query(description="Position in the list of specification rows."),
]
RowLimitParam = Annotated[
    Annotated[int, Field(ge=1, le=200)],
    Query(description="Specification rows per answer."),
]


def build_specification_price_routes(
    router: APIRouter, specification_prices: SpecificationPricesPort
) -> None:

    @router.get(
        f"{_DOCUMENT_PATH}/specification-prices",
        operation_id="getSpecificationPrices",
        tags=["optimisation"],
        status_code=200,
        response_model=models.SpecificationPrices,
        responses={
            **success(200, "The priced specification, or the state that stops it."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "«Спецификация и цены»: the specification rows of the document set's current "
            "version, read deterministically from its newest published run's saved text "
            "layer, each matched to the project's current price-list revision as `matched`, "
            "`ambiguous` or `unmatched` with its reason (code or mark first, then the "
            "normalised name, in the same unit; never a fuzzy guess). The version must be "
            "classified by an expert in one of the fifteen sections; the section is reported "
            "in the answer and does not change how the rows are read or priced. A "
            "precondition that does not hold is `state` (`version_unclassified`, "
            "`price_list_missing`, `analysis_missing`, `text_unavailable`, "
            "`specification_too_large`) with the facts read so far; the value "
            "`section_not_ar` stays in the enum so that no value is removed, and is no longer "
            "produced for a confirmed section; a path naming no such set is `404`. A price "
            "and an amount "
            "appear only on a matched row with a numeric quantity; totals are per currency "
            "over those rows only, with every other row counted by its reason. Rows are "
            "paged (`offset`, `limit`, `next_offset`); counts and totals cover every row. "
            "Nothing is written. Any one role, `role:admin|expert`."
        ),
    )
    def get_specification_prices(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        offset: RowOffsetParam = 0,
        limit: RowLimitParam = 50,
    ) -> WireResponse:
        answer = specification_prices.get_specification_prices(
            project_uid=project_uid,
            document_uid=document_uid,
            offset=offset,
            limit=limit,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(answer.model_dump(mode="json")))
