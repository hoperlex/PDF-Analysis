"""``compareDocumentVersions`` (`W59-VERSION-COMPARE-01`).

One read addressed through the version's document and project, like the section
operations beside it: ``/projects/{project_uid}/documents/{document_uid}/versions/
{version_uid}/comparison?target_version_uid=...``. The path version is the older
(source) version and ``target_version_uid`` the newer one of the same set.

**The path is proved first.** An unknown project, a document of another project or a
source version of another document is ``404 not_found``, as for every addressed read
(`D-67`). **Then a refusal is an answer, not an error.** A target that cannot be compared
-- another set, the same version twice, an unclassified version, a stage or section the
``mode`` does not admit, no published analysis -- answers ``200`` with ``outcome: refused``
and one closed ``refusal.reason``, because a reviewer is shown why, and the same
request with the same stored facts always refuses the same way. A malformed
identity or paging value is ``422``; a stored fact that contradicts its own
constraints is ``500``. Nothing is written: every pairing and finding label in the
answer is a proposal, and no AI layer produces or edits any value in it.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query
from pydantic import Field, WithJsonSchema

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import ComparisonPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import optional_property

__all__ = ["build_comparison_routes"]

_VERSION_PATH = "/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}"

TargetVersionParam = Annotated[
    models.VersionUid,
    Query(description="The newer version of the same set; the path names the older one."),
]
RunFilterParam = Annotated[
    models.RunId | None,
    WithJsonSchema({"$ref": "#/components/schemas/RunId"}),
    Query(json_schema_extra=optional_property),
]
ModeParam = Annotated[
    Literal["version", "stage"],
    Query(description=(
        "`version`: both versions carry the same project stage and section. `stage`: the "
        "source is classified `P`, the target `R`, with the same section."
    )),
]
DiffOffsetParam = Annotated[
    Annotated[int, Field(ge=0)],
    Query(description="Position in the list of sheets with text differences."),
]
DiffLimitParam = Annotated[
    Annotated[int, Field(ge=1, le=25)],
    Query(description="Sheets with text differences per answer."),
]


def build_comparison_routes(router: APIRouter, comparisons: ComparisonPort) -> None:

    @router.get(
        f"{_VERSION_PATH}/comparison",
        operation_id="compareDocumentVersions",
        tags=["documents"],
        status_code=200,
        response_model=models.VersionComparison,
        responses={
            **success(200, "The comparison of the two versions, or why they are not compared."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "Compare two versions of one document set: the path names the older (source) "
            "version and `target_version_uid` the newer one. Both must be published "
            "versions of the named document in the named project with the same confirmed "
            "section and, with `mode=version` (the default), the same explicit project "
            "stage; with `mode=stage` the source must be classified `P` and the target `R` "
            "(design to working documentation of one set). Each needs a published run "
            "(the newest one, or the one `source_run_id` / `target_run_id` names). "
            "A path that names no such version is `404`; otherwise a pair the rule does not "
            "admit is `outcome: refused` with one `refusal.reason`, never relabelled. The "
            "answer carries proposed sheet pairs with their "
            "evidence, one page of raw line differences (`diff_offset`, `diff_limit`, "
            "`next_offset`) and proposed matches between the two runs' findings. Every "
            "pairing and match is a proposal; nothing is written. Any one role, "
            "`role:admin|expert`."
        ),
    )
    def compare_document_versions(
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
        target_version_uid: TargetVersionParam,
        source_run_id: RunFilterParam = None,
        target_run_id: RunFilterParam = None,
        mode: ModeParam = "version",
        diff_offset: DiffOffsetParam = 0,
        diff_limit: DiffLimitParam = 10,
    ) -> WireResponse:
        comparison = comparisons.compare_versions(
            project_uid=project_uid,
            document_uid=document_uid,
            source_version_uid=version_uid,
            target_version_uid=target_version_uid,
            source_run_id=source_run_id,
            target_run_id=target_run_id,
            mode=mode,
            diff_offset=diff_offset,
            diff_limit=diff_limit,
        )
        return json_response(200, encode_json(comparison.model_dump(mode="json")))
