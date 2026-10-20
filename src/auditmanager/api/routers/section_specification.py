"""``getSectionSpecification`` (`W63-SECTION-FORM7-01`).

«Оптимизация разделов»: one read addressed by a section code,
``/sections/{section_code}/specification``. For that section the server takes every document
set whose **current** version an expert confirmed in it, across projects, reads each such
version's newest published run's saved text, extracts the Form-7 rows and matches every row
against **its own project's** current price list.

**The section code is a filter, not an identity.** Every row names its project, document set,
version, page, sheet and line span; rows are never merged across projects; totals exist per
project and per currency (each project's ``matching``) and there is no section total. A project
without a price list serves its rows with no match and no figure. A current version nobody
classified is listed in ``excluded``; one confirmed in another section never appears.

``project_uid`` narrows the answer to one project (an unknown one is ``404``); ``q`` keeps the
rows whose own Form-7 text contains it, without changing any project's state or totals.
Rows are paged. A section code outside the fifteen addresses no section and is ``404``. A bound
(projects scanned, member sets read, rows held) is an answer, not an error: ``200`` with
``state: section_too_large`` and the bound's name. Nothing is written. Any one role,
``role:admin|expert``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import BeforeValidator, Field, WithJsonSchema

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import SectionSpecificationPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.security import CurrentSubject

__all__ = ["build_section_specification_routes"]


def _absent(value: object) -> object:
    """An empty query value is the absent parameter, as for every other filter."""
    return None if value == "" else value


RowOffsetParam = Annotated[
    Annotated[int, Field(ge=0)],
    Query(description="Position in the list of rows that survive the search."),
]
RowLimitParam = Annotated[
    Annotated[int, Field(ge=1, le=200)],
    Query(description="Specification rows per answer."),
]
ProjectFilterParam = Annotated[
    models.ProjectUid | None,
    BeforeValidator(_absent),
    WithJsonSchema({"$ref": "#/components/schemas/ProjectUid"}),
    Query(json_schema_extra=optional_property),
]
RowQueryParam = Annotated[
    Annotated[str, Field(min_length=1, max_length=200)] | None,
    BeforeValidator(_absent),
    WithJsonSchema({"type": "string", "minLength": 1, "maxLength": 200}),
    Query(
        description=(
            "Text a row's position, description, group, unit or note contains, ignoring "
            "case, `ё` and runs of spaces. Narrows the rows only, never a project's totals."
        ),
        json_schema_extra=optional_property,
    ),
]


def build_section_specification_routes(
    router: APIRouter, section_specifications: SectionSpecificationPort
) -> None:

    @router.get(
        "/sections/{section_code}/specification",
        operation_id="getSectionSpecification",
        tags=["optimisation"],
        status_code=200,
        response_model=models.SectionSpecification,
        responses={
            **success(200, "The section's combined specification, project by project."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "«Оптимизация разделов»: the Form-7 rows of every project whose document set's "
            "current version an expert confirmed in the section, each row priced from its "
            "own project's current price list as `matched`, `ambiguous` or `unmatched` with "
            "its reason (or `price_list_missing` when the project has none). The section code "
            "is a filter, not an identity: every row carries its project, document set, "
            "version, page, sheet and line span, rows are never merged across projects, and "
            "totals exist per project and per currency only -- there is no section total. A "
            "current version nobody classified is listed in `excluded`; one confirmed in "
            "another section never appears. `project_uid` narrows the answer to one project "
            "(an unknown one is `404`); `q` keeps the rows whose own text contains it and "
            "never changes a total; rows are paged (`offset`, `limit`, `next_offset`). A set "
            "without a published run or a saved text layer is its own `state`. Over a bound "
            "(projects scanned, member sets read, rows held) the answer is `200` with "
            "`state: section_too_large`, the bound in `limit_reason`, the membership listed "
            "and no rows; narrow to one project. A section code outside the fifteen is `404`. "
            "Nothing is written. Any one role, `role:admin|expert`."
        ),
    )
    def get_section_specification(
        subject: CurrentSubject,
        section_code: Annotated[models.ProjectSection, Path()],
        project_uid: ProjectFilterParam = None,
        q: RowQueryParam = None,
        offset: RowOffsetParam = 0,
        limit: RowLimitParam = 50,
    ) -> WireResponse:
        answer = section_specifications.get_section_specification(
            section_code=section_code.value,
            project_uid=project_uid,
            query=q,
            offset=offset,
            limit=limit,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(answer.model_dump(mode="json")))
