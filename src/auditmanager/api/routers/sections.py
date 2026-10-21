"""``classifyDocumentVersion``, ``correctVersionClassification`` and ``getVersionSectionReview``.

`W59-SECTION-SEAL-01` and `CLASSIFICATION-CORRECTION-01`. Every operation addresses one version
**through its document and project**:
``/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/...``. The design
decision (`W59-SECTION-IDENTITY-DECISION-01`) requires exact project/version membership and
the refusal of a foreign version, so the path names the whole chain and the port proves it;
a version of another document, or a document of another project, is ``not_found``.

The classification is the expert's explicit choice of project stage (``P``/``R``) and one of
the fifteen sections. It is persisted outside the immutable ``document_version`` row
(``0024_version_classification``) and is what run start routes on. The review is display
input only: every suggestion it carries is evidence for a reviewer, never a confirmation and
never a route. A correction appends a numbered revision to the history (``0028``); nothing
the first confirmation stored is ever changed.
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
            "`conflict_reason: version_already_classified` and changes nothing -- to change an "
            "existing classification an expert uses `correctVersionClassification`, with a "
            "reason. A suggestion, a file name or the legacy document `section` is never a "
            "classification."
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

    @router.post(
        f"{_VERSION_PATH}/classification/corrections",
        operation_id="correctVersionClassification",
        tags=["documents"],
        status_code=201,
        response_model=models.VersionClassification,
        responses={
            **success(
                201,
                "The revision this correction wrote, or the stored revision an exact repeat created.",
            ),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "Correct one version's classification: append a new revision with the full target "
            "`project_stage` and `section_code`, a `reason` (1 to 2000 characters, with a "
            "letter or a digit) and the `expected_revision` the caller was looking at. `expert` "
            "is required; `admin` alone is refused with `permission_denied` "
            "(`required_capability: role:expert`). The version must belong to the named "
            "document and the document to the named project, otherwise `not_found`. Revision 1 "
            "is the original confirmation and is never changed; the current classification is "
            "the latest revision. An unclassified version is `conflict` with `conflict_reason: "
            "version_not_classified` -- classify it first. An `expected_revision` behind the "
            "current one is `conflict` with `conflict_reason: classification_revision_stale` "
            "and writes nothing, unless the request is an exact repeat (same expert, same "
            "values, same reason) of the revision after it, which answers that stored revision "
            "with `201` and writes nothing; one ahead of the current revision, a pair equal to "
            "the current classification (`constraint: differs_from_current`) and a blank, "
            "over-long or unprintable reason are `validation_failed`. Runs already started keep "
            "the analysis profile they pinned; a re-audit routes from the corrected "
            "classification. No `Idempotency-Key`: `expected_revision` is what makes a retry safe."
        ),
    )
    def correct_version_classification(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
        body: models.CorrectVersionClassificationRequest,
    ) -> WireResponse:
        stored = sections.correct_classification(
            project_uid=project_uid,
            document_uid=document_uid,
            version_uid=version_uid,
            project_stage=body.project_stage.value,
            section_code=body.section_code.value,
            reason=body.reason,
            expected_revision=body.expected_revision,
            user_uid=subject.user_uid,
        )
        return json_response(201, encode_json(stored.model_dump(mode="json")))

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
            "`null`, and the classification's history (`revisions`, oldest first: the original "
            "confirmation, then each correction with its expert, time and reason). Display "
            "input only: nothing here confirms a section or starts a run. "
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
