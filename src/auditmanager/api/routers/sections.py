"""``classifyDocumentVersion`` and ``getVersionSectionReview`` (`W59-SECTION-SEAL-01`).

Both operations address one version **through its document and project**:
``/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/...``. The design
decision (`W59-SECTION-IDENTITY-DECISION-01`) requires exact project/version membership and
the refusal of a foreign version, so the path names the whole chain and the port proves it;
a version of another document, or a document of another project, is ``not_found``.

The classification is the expert's explicit choice of project stage (``P``/``R``) and one of
the fifteen sections. It is persisted outside the immutable ``document_version`` row
(``0024_version_classification``) and is what run start routes on. The review is display
input only: every suggestion it carries is evidence for a reviewer, never a confirmation and
never a route.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    envelope_responses,
    success,
)
from auditmanager.api.routers.ports import SectionPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_section_routes"]

_VERSION_PATH = "/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}"


def build_section_routes(router: APIRouter, sections: SectionPort) -> None:

    @router.put(
        f"{_VERSION_PATH}/classification",
        operation_id="classifyDocumentVersion",
        tags=["documents"],
        status_code=200,
        response_model=models.VersionClassification,
        responses={
            **success(200, "The persisted classification, new or an exact repeat."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "Classify one version: its project stage (`P` or `R`) and one of the fifteen "
            "sections, confirmed by the calling expert. `expert` is required; `admin` alone "
            "is refused with `permission_denied` (`required_capability: role:expert`). The "
            "version must belong to the named document and the document to the named "
            "project, otherwise `not_found`. An exact repeat answers the stored row and keeps "
            "the first confirmer; a different stage or section is `conflict` with "
            "`conflict_reason: version_already_classified` and changes nothing -- there is no "
            "correction workflow yet. A suggestion, a file name or the legacy document "
            "`section` is never a classification."
        ),
    )
    def classify_document_version(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
        body: models.ClassifyDocumentVersionRequest,
    ) -> WireResponse:
        stored = sections.classify_version(
            project_uid=project_uid,
            document_uid=document_uid,
            version_uid=version_uid,
            project_stage=body.project_stage.value,
            section_code=body.section_code.value,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(stored.model_dump(mode="json")))

    @router.get(
        f"{_VERSION_PATH}/section-review",
        operation_id="getVersionSectionReview",
        tags=["documents"],
        status_code=200,
        response_model=models.SectionReview,
        responses={
            **success(200, "All fifteen choices, their evidence and the current classification."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
        description=(
            "The fifteen section choices for one version, each with the suggestion evidence "
            "its file name and recognised text carry (or `null`) and whether a text profile "
            "is registered for it (`executable`), plus the persisted classification or "
            "`null`. Display input only: nothing here confirms a section or starts a run. "
            "Any one role, `role:admin|expert`."
        ),
    )
    def get_version_section_review(
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
    ) -> WireResponse:
        review = sections.get_section_review(
            project_uid=project_uid, document_uid=document_uid, version_uid=version_uid
        )
        return json_response(200, encode_json(review.model_dump(mode="json")))
