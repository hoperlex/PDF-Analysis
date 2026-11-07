"""The «Предложения» operations (`W60-OPT-PROPOSALS-01`): optimisation passes, their
deterministic proposals and the experts' decisions on them.

* ``startOptimisationPass`` -- ``POST /projects/{project_uid}/documents/{document_uid}/
  optimisation-passes`` (``expert``, ``Idempotency-Key`` required): the pass over the set's
  current AR version.
* ``listOptimisationPasses`` -- ``GET /projects/{project_uid}/optimisation-passes``.
* ``listOptimisationProposals`` -- ``GET /optimisation-passes/{optimisation_pass_id}/
  proposals``: one page, the pass with its counts by decision, optionally filtered.
* ``decideOptimisationProposal`` -- ``POST /optimisation-proposals/{optimisation_proposal_id}/
  decisions`` (``expert``, ``Idempotency-Key`` required): accept, reject or revise, or revoke
  the standing decision (`UI-B-12`, contract 1.35.0).
* ``listAcceptedOptimisationProposals`` -- ``GET /optimisation-proposals/accepted`` (`UI-B-27`,
  contract 1.35.0): the proposals whose decision in force is an acceptance, by project and section.
* ``listProposalDecisions`` -- ``GET /optimisation-proposals/{optimisation_proposal_id}/
  decisions``: the append-only history.
* ``exportOptimisationProposalsCsv`` -- ``GET /optimisation-passes/{optimisation_pass_id}/
  export.csv``: the formula-escaped file, separate from the findings' CSV.
* ``exportOptimisationProposalsXlsx`` and ``importOptimisationProposalDecisions`` (`UI-B-15`,
  contract 1.35.0) -- ``GET /optimisation-passes/{optimisation_pass_id}/export.xlsx`` and ``POST
  /optimisation-passes/{optimisation_pass_id}/decision-imports``: the pass's workbook, and the
  decisions loaded back from it by proposal identity.

* ``carryOverProposalDecisions`` (`UI-B-14`, contract 1.37.0) -- ``POST /optimisation-passes/
  {optimisation_pass_id}/decision-carryovers`` (``expert``, ``Idempotency-Key`` required): the decisions in force of
  an earlier version's pass, carried into this pass where the content matches exactly once on both sides.

The routes parse, call one port method and render; the rules -- roles read in the writing
transaction, the preconditions of a pass, the generator, the exact repeats, the append-only
decisions, the CSV bytes -- live in ``auditmanager.optimisation.proposals``. A proposal is a
separate entity beside findings: nothing here reads or changes a finding, and no operation
answers a price or a saving that a price-list position and a numeric quantity do not state.
"""

from __future__ import annotations

from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, Form, Path, Query, Response
from pydantic import BeforeValidator, Field, WithJsonSchema

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    ProjectUidFilterParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.export import attachment_disposition
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.multipart import CheckedUpload, UploadRoute, require_a_strict_multipart_body
from auditmanager.api.routers.ports import OptimisationProposalPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate, timestamp
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.security import CurrentSubject

__all__ = ["build_optimisation_proposal_routes"]

_CSV: Final[str] = "text/csv; charset=utf-8"
_CSV_MEDIA_TYPE: Final[str] = "text/csv"
_XLSX_MEDIA_TYPE: Final[str] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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

# `UI-B-27`: the accepted list reads one section's proposals; absent, every section.
SectionCodeFilterParam = Annotated[
    models.ProjectSection | None,
    WithJsonSchema({"$ref": "#/components/schemas/ProjectSection"}),
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
            "Start the optimisation pass of the document set's current version, classified by "
            "an expert in any of the fifteen sections. The pass "
            "pins the version, its newest published run and that run's saved text layer, the "
            "project's current price-list revision and the effective vendor list of the "
            "version's own section (the "
            "project's own, else the administrator's), reads the specification, matches it "
            "against the price list and stores the deterministic proposals `cheaper_analog`: "
            "for a row matched to exactly one position, another position of the same "
            "revision in the same unit and currency, with a lower unit price, from a vendor "
            "on the list, of the same kind of product (at most three per row). The saving is "
            "`(current − proposed) × quantity` and is absent when the row's quantity is not a "
            "plain number. `expert` is required (`admin` alone is `permission_denied`). A "
            "precondition that is not met is `409 conflict` with `conflict_reason` "
            "`version_unclassified`, `price_list_missing`, "
            "`analysis_missing`, `text_unavailable`, `specification_too_large` or "
            "`vendor_list_missing` (neither the project nor the administrator keeps a vendor "
            "list for the version's section) and nothing is written, not even the key; "
            "`section_not_ar` stays among the registered reasons and is no longer produced for "
            "a confirmed section; an unknown "
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
            "`404`. Any one role, `role:admin|expert|viewer`."
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
            "`role:admin|expert|viewer`."
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
            "comment is required for `revise`, at most 2000 characters), or `revoke` -- the "
            "withdrawal of the decision in force («Снять решение»), an event like any other that "
            "takes the proposal back to `pending`, with an optional comment, refused with "
            "`409 conflict` and `conflict_reason` `no_decision_to_revoke` when the proposal has "
            "no decision in force. Decisions are only "
            "appended, never changed; the latest one is current (unless it is a `revoke`), and "
            "any number may follow. "
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

    @router.post(
        "/optimisation-passes/{optimisation_pass_id}/decision-carryovers",
        operation_id="carryOverProposalDecisions",
        tags=["optimisation"],
        status_code=200,
        response_model=models.ProposalDecisionCarryoverReport,
        responses={
            **success(200, "What the carryover did: the source's decisions in force, counted by what each came to."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={
                    409: "The source pass cannot be used (`conflict` with `details.conflict_reason`: "
                    "`carryover_source_unknown`, `carryover_source_is_target`, `carryover_source_other_document` or "
                    "`carryover_source_not_earlier`) or an idempotency key already used with a different payload.",
                },
            ),
        },
        description=(
            "`UI-B-14` (contract 1.37.0), «Перенести решения из V#»: carry the decisions in force of "
            "`source_optimisation_pass_id` -- a pass of the same document set started over an earlier version -- into "
            "the pass of the path. A source decision (an `accept`, a `reject` or a `revise`; a proposal nobody decided or "
            "whose decision was withdrawn carries nothing) is appended to a proposal of this pass only where exactly one "
            "proposal of each pass has the same content -- the type, the specification row's text, the unit, the currency, "
            "both positions by code, mark, name and supplier, and both unit prices; never a display number, a name alone "
            "or a position in the drawing -- and only when that proposal has no event at all. Each carried decision is an "
            "ordinary appended event, authored by the caller, with the source's verdict and comment and `carried_from` "
            "naming the source decision and its version; a later decision on the proposal supersedes it. The report counts "
            "every decision in force of the source in exactly one of `carried`, `target_decided` (the proposal already "
            "has an event, which stands), `ambiguous` (more than one proposal of either pass has that content) and "
            "`unmatched` (no proposal of this pass has it). An unknown target pass is `404`; a source that names no pass, "
            "is the target, belongs to another document set or was not started over an earlier version is `409 conflict` "
            "with `conflict_reason` `carryover_source_unknown`, `carryover_source_is_target`, "
            "`carryover_source_other_document` or `carryover_source_not_earlier`, and nothing is written. An exact repeat "
            "of the `Idempotency-Key` answers the stored report and appends nothing; the same key with another source "
            "or caller is `409 idempotency_key_reuse`; a new key repeats the matching and carries nothing more once the "
            "targets are decided. `expert` only (`admin` alone is `permission_denied`)."
        ),
    )
    def carry_over_proposal_decisions(
        subject: CurrentSubject,
        optimisation_pass_id: PassIdPath,
        body: models.CarryOverProposalDecisionsRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        report = proposals.carry_over_proposal_decisions(
            optimisation_pass_id=optimisation_pass_id,
            source_optimisation_pass_id=body.source_optimisation_pass_id,
            idempotency_key=idempotency_key,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(report.model_dump(mode="json")))

    @router.get(
        "/optimisation-proposals/accepted",
        operation_id="listAcceptedOptimisationProposals",
        tags=["optimisation"],
        status_code=200,
        response_model=models.AcceptedOptimisationProposalPage,
        responses={
            **success(
                200, "One page of the accepted proposals, newest acceptance first, and the number that match."
            ),
            # No 404: `project_uid` and `section_code` are filters, not parents -- a project or a section nothing was
            # accepted in matches no row, and that is an empty page.
            **envelope_responses(401, 403, 422, 500, 503),
        },
        description=(
            "The optimisation proposals whose decision in force is an acceptance, across every pass, newest "
            "acceptance first (`cursor`, `limit`), each with where it belongs -- project, document set, version and "
            "the version's section -- and the acceptance itself (who, when, the comment). A proposal whose latest "
            "decision is a rejection, a revision request or a withdrawal, or that nobody decided, is not listed. "
            "`project_uid` narrows to one project and `section_code` to the versions an expert confirmed in that "
            "section; neither is a parent, so an empty result is a `200` with no rows. `total` is the number of "
            "proposals the filters match, on every page. Any one role, `role:admin|expert|viewer`."
        ),
    )
    def list_accepted_optimisation_proposals(
        subject: CurrentSubject,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
        project_uid: ProjectUidFilterParam = None,  # type: ignore[assignment]
        section_code: SectionCodeFilterParam = None,  # type: ignore[assignment]
    ) -> WireResponse:
        rows = proposals.list_accepted_optimisation_proposals(
            project_uid=project_uid,
            section_code=None if section_code is None else section_code.value,
            user_uid=subject.user_uid,
        )
        page = paginate(
            rows,
            limit=limit,
            cursor=cursor,
            sort_key=lambda row: (timestamp(row.decided_at), row.proposal_decision_id),
        )
        items = []
        for row in page.items:
            item = row.model_dump(mode="json")
            if item.get("section") is None:
                item.pop("section", None)
            items.append(item)
        body = page_body(items, page.next_cursor)
        body["total"] = len(rows)
        return json_response(200, encode_json(body))

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
            "proposal is `404`. Any one role, `role:admin|expert|viewer`."
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
            "findings' CSV. An unknown pass is `404`. Any one role, `role:admin|expert|viewer`."
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
                ("Content-Disposition", attachment_disposition(optimisation_pass_id, suffix="csv")),
            ),
            content,
        )

    @router.get(
        "/optimisation-passes/{optimisation_pass_id}/export.xlsx",
        operation_id="exportOptimisationProposalsXlsx",
        tags=["optimisation"],
        status_code=200,
        response_class=Response,
        responses={
            **success(
                200,
                "The workbook of this pass's proposals.",
                content={_XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
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
            "`UI-B-15` (contract 1.35.0): every proposal of the pass as a workbook with one sheet, «Предложения», one "
            "row each in ordinal order. The first column, «ID предложения», is the proposal's own identity -- the key by "
            "which `importOptimisationProposalDecisions` reads the file back, never the display number «№»; then the "
            "specification row, both positions, the exact prices and the saving (an empty cell when it is absent, never "
            "`0`), and the two columns an expert edits, «Решение эксперта» (`не решено`, `принято`, `отклонено` or `на "
            "доработку`) and «Комментарий», filled with the decision in force. Every cell is text, so one that begins "
            "with `=` is shown and not evaluated. Computed on request from the stored rows. An unknown pass is `404`. "
            "Any one role, `role:admin|expert|viewer`."
        ),
    )
    def export_optimisation_proposals_xlsx(
        subject: CurrentSubject, optimisation_pass_id: PassIdPath
    ) -> WireResponse:
        content = proposals.export_optimisation_proposals_xlsx(
            optimisation_pass_id=optimisation_pass_id, user_uid=subject.user_uid
        )
        return WireResponse(
            200,
            (
                ("Content-Type", _XLSX_MEDIA_TYPE),
                ("Content-Length", str(len(content))),
                ("Content-Disposition", attachment_disposition(optimisation_pass_id, suffix="xlsx")),
            ),
            content,
        )

    # Declared through ``add_api_route`` for ``route_class_override``: ``UploadRoute`` parses the
    # form under the upload's small part bounds, as it does for ``importRunDecisions``.
    def import_optimisation_proposal_decisions(
        subject: CurrentSubject,
        optimisation_pass_id: PassIdPath,
        body: Annotated[models.ImportProposalDecisionsRequest, Form(media_type="multipart/form-data")],
        idempotency_key: RequiredIdempotencyKey,
        checked: Annotated[CheckedUpload, Depends(require_a_strict_multipart_body)],
    ) -> WireResponse:
        del checked  # a repeated, unnamed or filename-less part was refused before this runs
        report = proposals.import_optimisation_proposal_decisions(
            optimisation_pass_id=optimisation_pass_id,
            content=body.file.file,
            idempotency_key=idempotency_key,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(report.model_dump(mode="json", exclude_none=True)))

    router.add_api_route(
        "/optimisation-passes/{optimisation_pass_id}/decision-imports",
        import_optimisation_proposal_decisions,
        methods=["POST"],
        operation_id="importOptimisationProposalDecisions",
        tags=["optimisation"],
        status_code=200,
        response_model=models.ProposalDecisionImportReport,
        responses={
            **success(200, "What the import did with each row that names an ID or a decision."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
        route_class_override=UploadRoute,
        description=(
            "`UI-B-15` (contract 1.35.0): load back the pass's workbook as `exportOptimisationProposalsXlsx` produced it, "
            "with «Решение эксперта» and «Комментарий» edited, at most 10 MiB. Only our export is read: a workbook "
            "without a «Предложения» sheet naming the columns «ID предложения», «Решение эксперта» and «Комментарий» is "
            "`422 validation_failed` (`field: file`, `constraint: not_our_export`), as is a file that is not a readable "
            "XLSX (`unreadable`), is larger (`too_large`) or has more than 20 000 rows (`too_many_rows`); nothing is "
            "recorded then. Rows are matched by the proposal's identity, never by «№», and only proposals of this pass. "
            "A row whose decision differs from the one in force appends an `accept`, `reject` or `revise` event carrying "
            "the row's comment (`revise` requires one), authored by the caller exactly as `decideOptimisationProposal` "
            "would; «не решено» over a decision in force appends its withdrawal (`revoke`); the same decision with a "
            "new comment appends a new event; a blank decision cell keeps the decision in force. Every row naming an ID "
            "or a decision is reported, in sheet order, as `recorded`, `unchanged` or `refused` with a `reason`: "
            "`no_proposal_id`, `duplicate_proposal`, `unknown_proposal`, `unknown_decision` (not one of the four "
            "labels the export writes), `comment_required` or `comment_too_long`. The proposal's identity is reported "
            "only for a proposal of the pass. An unknown pass is `404`. An exact repeat of the `Idempotency-Key` answers "
            "the stored report and appends nothing; the same key with another file, pass or caller is `409 "
            "idempotency_key_reuse`. `expert` only (`admin` alone is `permission_denied`)."
        ),
    )
