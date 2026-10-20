"""The six «Предложения» operations (`W60-OPT-PROPOSALS-01`): optimisation passes, their
deterministic proposals and the experts' decisions on them.

* ``startOptimisationPass`` -- ``POST /projects/{project_uid}/documents/{document_uid}/
  optimisation-passes`` (``expert``, ``Idempotency-Key`` required): the pass over the set's
  current AR version.
* ``listOptimisationPasses`` -- ``GET /projects/{project_uid}/optimisation-passes``.
* ``listOptimisationProposals`` -- ``GET /optimisation-passes/{optimisation_pass_id}/
  proposals``: one page, the pass with its counts by decision, optionally filtered.
* ``decideOptimisationProposal`` -- ``POST /optimisation-proposals/{optimisation_proposal_id}/
  decisions`` (``expert``, ``Idempotency-Key`` required): accept, reject or revise.
* ``listProposalDecisions`` -- ``GET /optimisation-proposals/{optimisation_proposal_id}/
  decisions``: the append-only history.
* ``exportOptimisationProposalsCsv`` -- ``GET /optimisation-passes/{optimisation_pass_id}/
  export.csv``: the formula-escaped file, separate from the findings' CSV.

The routes parse, call one port method and render; the rules -- roles read in the writing
transaction, the preconditions of a pass, the generator, the exact repeats, the append-only
decisions, the CSV bytes -- live in ``auditmanager.optimisation.proposals``. A proposal is a
separate entity beside findings: nothing here reads or changes a finding, and no operation
answers a price or a saving that a price-list position and a numeric quantity do not state.
"""

from __future__ import annotations

from typing import Annotated, Any, Final

from fastapi import APIRouter, Path, Query, Response
from pydantic import BeforeValidator, Field, WithJsonSchema

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import OptimisationProposalPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.security import CurrentSubject

__all__ = ["build_optimisation_proposal_routes"]

_CSV: Final[str] = "text/csv; charset=utf-8"
_CSV_MEDIA_TYPE: Final[str] = "text/csv"


def _absent(value: Any) -> Any:
    """An empty query value is the absent parameter, as for every other filter."""
    return None if value == "" else value


OffsetParam = Annotated[
    Annotated[int, Field(ge=0)],
    Query(description="Position in the pass's proposals, in ordinal order."),
]
ProposalLimitParam = Annotated[
    Annotated[int, Field(ge=1, le=200)],
    Query(description="Proposals per answer."),
]
PassLimitParam = Annotated[
    Annotated[int, Field(ge=1, le=100)],
    Query(description="Passes per answer."),
]
DecisionFilterParam = Annotated[
    models.ProposalDecisionState | None,
    BeforeValidator(_absent),
    WithJsonSchema({"$ref": "#/components/schemas/ProposalDecisionState"}),
    Query(json_schema_extra=optional_property),
]
DocumentFilterParam = Annotated[
    models.DocumentUid | None,
    BeforeValidator(_absent),
    WithJsonSchema({"$ref": "#/components/schemas/DocumentUid"}),
    Query(json_schema_extra=optional_property),
]

PassIdPath = Annotated[models.OptimisationPassId, Path()]
ProposalIdPath = Annotated[models.OptimisationProposalId, Path()]


def build_optimisation_proposal_routes(
    router: APIRouter, proposals: OptimisationProposalPort
) -> None:

    @router.post(
        "/projects/{project_uid}/documents/{document_uid}/optimisation-passes",
        operation_id="startOptimisationPass",
        tags=["optimisation"],
        status_code=201,
        response_model=models.OptimisationPass,
        responses={
            **success(201, "The pass, new or an exact repeat answered."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={
                    409: "An unmet precondition (`conflict` with `details.conflict_reason`) or "
                    "an idempotency key already used with a different payload.",
                },
            ),
        },
        description=(
            "Start the optimisation pass of the document set's current AR version. The pass "
            "pins the version, its newest published run and that run's saved text layer, the "
            "project's current price-list revision and the effective AR vendor list (the "
            "project's own, else the administrator's), reads the specification, matches it "
            "against the price list and stores the deterministic proposals `cheaper_analog`: "
            "for a row matched to exactly one position, another position of the same "
            "revision in the same unit and currency, with a lower unit price, from a vendor "
            "on the list, of the same kind of product (at most three per row). The saving is "
            "`(current − proposed) × quantity` and is absent when the row's quantity is not a "
            "plain number. `expert` is required (`admin` alone is `permission_denied`). A "
            "precondition that is not met is `409 conflict` with `conflict_reason` "
            "`version_unclassified`, `section_not_ar`, `price_list_missing`, "
            "`analysis_missing`, `text_unavailable`, `specification_too_large` or "
            "`vendor_list_missing` and nothing is written, not even the key; an unknown "
            "project or a set of another project is `404`. An exact repeat of the "
            "`Idempotency-Key` answers the stored pass, the same key for another set or "
            "caller is `409 idempotency_key_reuse`, and a new key over exactly the same "
            "inputs answers the pass already stored instead of writing a second one."
        ),
    )
    def start_optimisation_pass(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        started = proposals.start_optimisation_pass(
            project_uid=project_uid,
            document_uid=document_uid,
            idempotency_key=idempotency_key,
            user_uid=subject.user_uid,
        )
        return json_response(201, encode_json(started.model_dump(mode="json")))

    @router.get(
        "/projects/{project_uid}/optimisation-passes",
        operation_id="listOptimisationPasses",
        tags=["optimisation"],
        status_code=200,
        response_model=models.OptimisationPassList,
        responses={
            **success(200, "The project's passes, newest first."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "The project's optimisation passes, newest first (at most `limit`, 100 by "
            "default), each with its counts by decision; `document_uid` narrows to one "
            "document set of the project. An unknown project or a set of another project is "
            "`404`. Any one role, `role:admin|expert`."
        ),
    )
    def list_optimisation_passes(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: DocumentFilterParam = None,
        limit: PassLimitParam = 100,
    ) -> WireResponse:
        listing = proposals.list_optimisation_passes(
            project_uid=project_uid,
            document_uid=document_uid,
            limit=limit,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(listing.model_dump(mode="json")))

    @router.get(
        "/optimisation-passes/{optimisation_pass_id}/proposals",
        operation_id="listOptimisationProposals",
        tags=["optimisation"],
        status_code=200,
        response_model=models.OptimisationProposalPage,
        responses={
            **success(200, "One page of the pass's proposals and the pass with its counts."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        description=(
            "One page of a pass's proposals in ordinal order (`offset`, `limit`, "
            "`next_offset`), each with its provenance in the specification, the matched and "
            "the proposed position, both exact unit prices, the saving where it is "
            "computable and its current decision. `decision` narrows to the proposals in "
            "one decision state (`pending` for none yet); the pass's `decision_counts` "
            "always count every proposal. An unknown pass is `404`. Any one role, "
            "`role:admin|expert`."
        ),
    )
    def list_optimisation_proposals(
        subject: CurrentSubject,
        optimisation_pass_id: PassIdPath,
        decision: DecisionFilterParam = None,
        offset: OffsetParam = 0,
        limit: ProposalLimitParam = 50,
    ) -> WireResponse:
        page = proposals.list_optimisation_proposals(
            optimisation_pass_id=optimisation_pass_id,
            decision=None if decision is None else decision.value,
            offset=offset,
            limit=limit,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.post(
        "/optimisation-proposals/{optimisation_proposal_id}/decisions",
        operation_id="decideOptimisationProposal",
        tags=["optimisation"],
        status_code=201,
        response_model=models.ProposalDecisionResult,
        responses={
            **success(201, "The decision appended, or the one stored under the key."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
        description=(
            "Append an expert's decision on a proposal: `accept`, `reject` or `revise` (the "
            "comment is required for `revise`, at most 2000 characters). Decisions are only "
            "appended, never changed; the latest one is current, and any number may follow. "
            "`expert` is required (`admin` alone is `permission_denied`); an unknown "
            "proposal is `404`. An exact repeat of the `Idempotency-Key` answers the stored "
            "decision; the same key with another verdict, comment, proposal or caller is "
            "`409 idempotency_key_reuse`. The decision belongs to the proposal alone: no "
            "finding is read or changed."
        ),
    )
    def decide_optimisation_proposal(
        subject: CurrentSubject,
        optimisation_proposal_id: ProposalIdPath,
        body: models.DecideOptimisationProposalRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        result = proposals.decide_optimisation_proposal(
            optimisation_proposal_id=optimisation_proposal_id,
            verdict=body.verdict.value,
            comment=body.comment,
            idempotency_key=idempotency_key,
            user_uid=subject.user_uid,
        )
        return json_response(201, encode_json(result.model_dump(mode="json")))

    @router.get(
        "/optimisation-proposals/{optimisation_proposal_id}/decisions",
        operation_id="listProposalDecisions",
        tags=["optimisation"],
        status_code=200,
        response_model=models.ProposalDecisionList,
        responses={
            **success(200, "Every decision of the proposal, oldest first."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
        description=(
            "The proposal's whole append-only decision history, oldest first, each with its "
            "verdict, comment, author and time; the last one is current. An unknown "
            "proposal is `404`. Any one role, `role:admin|expert`."
        ),
    )
    def list_proposal_decisions(
        subject: CurrentSubject, optimisation_proposal_id: ProposalIdPath
    ) -> WireResponse:
        listing = proposals.list_proposal_decisions(
            optimisation_proposal_id=optimisation_proposal_id, user_uid=subject.user_uid
        )
        return json_response(200, encode_json(listing.model_dump(mode="json")))

    @router.get(
        "/optimisation-passes/{optimisation_pass_id}/export.csv",
        operation_id="exportOptimisationProposalsCsv",
        tags=["optimisation"],
        status_code=200,
        response_class=Response,
        responses={
            **success(
                200,
                "The CSV of this pass's proposals.",
                content={_CSV_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
                headers={
                    "Content-Disposition": {
                        "schema": {"type": "string"},
                        "description": "Attachment with a display file name built from the "
                        "opaque pass identity. The file name is presentation only and is "
                        "never an identity.",
                    }
                },
            ),
            **envelope_responses(401, 403, 404, 500, 503),
        },
        description=(
            "Every proposal of the pass as a CSV file, one row each in ordinal order: the "
            "pass, the specification row's provenance, both positions, both exact unit "
            "prices, the saving (an empty cell when it is absent, never `0`) and the current "
            "decision. UTF-8 with a byte-order mark, CRLF line endings, RFC 4180 quoting; "
            "every cell that a spreadsheet would read as a formula is prefixed with an "
            "apostrophe. Computed on request from the stored rows; separate from the "
            "findings' CSV. An unknown pass is `404`. Any one role, `role:admin|expert`."
        ),
    )
    def export_optimisation_proposals_csv(
        subject: CurrentSubject, optimisation_pass_id: PassIdPath
    ) -> WireResponse:
        content = proposals.export_optimisation_proposals_csv(
            optimisation_pass_id=optimisation_pass_id, user_uid=subject.user_uid
        )
        return WireResponse(
            200,
            (
                ("Content-Type", _CSV),
                ("Content-Length", str(len(content))),
                ("Content-Disposition", f'attachment; filename="{optimisation_pass_id}.csv"'),
            ),
            content,
        )
