"""``compareDocumentVersions`` (`W59-VERSION-COMPARE-01`) and ``carryOverDecision``
(`W59-DECISION-CARRYOVER-01`).

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

**The writes beside it.** ``carryOverDecision``: an expert confirms carrying one source
decision to the target finding of an ``unchanged`` proposal. The comparison is recomputed in
the confirming transaction, and the decision ledger appends one event on the target, authored
by the caller; ``findings.carryover_candidates`` in the read lists what could be carried.
`COMPARE-PERSISTED-SUMMARY-01` adds ``approveSheetPairing`` and ``withdrawSheetPairing``: an
expert's approval of a proposed sheet pair is stored (an append-only history; a withdrawal is a
new row), and ``approved_pairs`` in the read serves, for approved pairs only, their deterministic
differences sealed against the version bytes. A proposal is never promoted to an approval by a
read.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query
from pydantic import Field, WithJsonSchema

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.security import CurrentSubject

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
            "pairing and match in `sheets`, `sheet_diffs` and `findings` is a proposal; this "
            "read writes nothing. `approved_pairs` (null for a refused comparison) lists the "
            "sheet pairs an expert approved for exactly this pair of versions "
            "(`approveSheetPairing`) and, for approved pairs only, their deterministic line "
            "differences, recomputed from the immutable text and bound to the version bytes by "
            "a seal; when a page's text is no longer the approved one (`text_changed`), the "
            "seal differs (`seal_changed`) or the set exceeds the response budget "
            "(`too_large`) the differences are withheld, never truncated. Any one role, "
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

    @router.post(
        f"{_VERSION_PATH}/comparison/carryovers",
        operation_id="carryOverDecision",
        tags=["decisions"],
        status_code=201,
        response_model=models.CarryOverDecisionResponse,
        responses={
            **success(
                201, "The carried decision event on the target finding, new or an exact repeat.",
            ),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "Carry one expert decision from a finding of the path's (older) version to the "
            "finding of `target_version_uid` that the comparison proposes as `unchanged`, on "
            "the calling expert's confirmation. The comparison is recomputed with the body's "
            "`mode` and runs when the confirmation arrives, and must still propose exactly "
            "this pair; the source finding's current verdict must still be the "
            "`source_decision_id` the expert was shown (`accepted` or `rejected`), and the "
            "target finding must have no decision event yet. The target receives one new "
            "`accept` or `reject` event authored by the caller, whose `comment` records the "
            "carried-from finding, decision and versions; a severity is carried with an "
            "accept or the carryover is refused, never dropped. Nothing else is written: the "
            "source finding and its decisions stay as they were. An exact repeat answers the "
            "event already carried, `replayed: true`, and keeps its first expert. A refusal "
            "is `conflict` with `conflict_reason` `carryover_pair_not_proposed`, "
            "`carryover_source_decision_not_current`, `carryover_target_already_decided` or "
            "`carryover_severity_not_carryable`. `expert` is required; `admin` alone is "
            "refused (`required_capability: role:expert`)."
        ),
    )
    def carry_over_decision(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
        body: models.CarryOverDecisionRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        # The author is the verified subject, never the body (`D-78`, `R-37`, `W49-SEAL-01`),
        # exactly as `appendDecision` records it.
        carried = comparisons.carry_over_decision(
            project_uid=project_uid,
            document_uid=document_uid,
            source_version_uid=version_uid,
            target_version_uid=body.target_version_uid,
            mode=body.mode,
            source_finding_uid=body.source_finding_uid,
            target_finding_uid=body.target_finding_uid,
            source_decision_id=body.source_decision_id,
            source_run_id=body.source_run_id,
            target_run_id=body.target_run_id,
            idempotency_key=idempotency_key,
            author_label=subject.display_label,
            author_user_uid=subject.user_uid,
        )
        # `exclude_unset`: an event without a severity omits the property, as `appendDecision`
        # renders it -- `DecisionEvent.severity` is optional, never null.
        return json_response(
            201, encode_json(carried.model_dump(mode="json", exclude_unset=True)),
        )

    @router.post(
        f"{_VERSION_PATH}/comparison/sheet-pairings",
        operation_id="approveSheetPairing",
        tags=["documents"],
        status_code=201,
        response_model=models.SheetPairingEvent,
        responses={
            **success(201, "The stored approval of the sheet pair, new or an exact repeat."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "Store the calling expert's approval of one sheet pair that the comparison of the "
            "path's (older) version with `target_version_uid` proposes: a source page and a "
            "target page of the two immutable versions, identified by the SHA-256 of their text "
            "and by `suggestion_sha256`, never by a display number. The comparison is "
            "recomputed with the body's `mode` and runs when the confirmation arrives and must "
            "still propose exactly this pair under this digest. The approval is one new row of "
            "an append-only history, with the actor, the time and the seal of the raw evidence "
            "of the approved set, and one audit event, in one transaction; it is never updated. "
            "An exact repeat of an active approval answers it, `replayed: true`. A refusal is "
            "`conflict` with `conflict_reason` `sheet_pair_not_proposed`, "
            "`sheet_page_already_paired`, `sheet_pair_limit_reached` (at most 32 active "
            "approvals), `approved_text_changed` (an earlier approval's page text is no longer "
            "the approved one; withdraw it first) or `sheet_pair_too_large`. `expert` is "
            "required; `admin` alone is refused (`required_capability: role:expert`)."
        ),
    )
    def approve_sheet_pairing(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
        body: models.ApproveSheetPairingRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        # The actor is the verified subject, never the body (`D-78`, `R-37`, `W49-SEAL-01`).
        approved = comparisons.approve_sheet_pairing(
            project_uid=project_uid,
            document_uid=document_uid,
            source_version_uid=version_uid,
            target_version_uid=body.target_version_uid,
            mode=body.mode,
            source_page_number=body.source_page_number,
            target_page_number=body.target_page_number,
            suggestion_sha256=body.suggestion_sha256,
            source_run_id=body.source_run_id,
            target_run_id=body.target_run_id,
            idempotency_key=idempotency_key,
            author_label=subject.display_label,
            author_user_uid=subject.user_uid,
        )
        return json_response(201, encode_json(approved.model_dump(mode="json")))

    @router.post(
        f"{_VERSION_PATH}/comparison/sheet-pairings/{{sheet_link_id}}/withdrawals",
        operation_id="withdrawSheetPairing",
        tags=["documents"],
        status_code=201,
        response_model=models.SheetPairingEvent,
        responses={
            **success(201, "The stored withdrawal of the sheet link, new or a replay."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "End one active sheet link of the path's (older) version with a new row of the "
            "append-only history: nothing is updated or deleted, and the approval stays in the "
            "history. The body names the comparison view the expert was looking at (`mode` and "
            "runs): the approved set that remains is sealed over that view's text. A link that "
            "is not of this path is `404`; a link already withdrawn is `conflict` with "
            "`conflict_reason` `sheet_link_not_active`; a view that cannot be recomputed is "
            "`conflict` with `comparison_not_available`. The same key repeated answers the "
            "first withdrawal, `replayed: true`. `expert` is required; `admin` alone is "
            "refused (`required_capability: role:expert`)."
        ),
    )
    def withdraw_sheet_pairing(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
        sheet_link_id: Annotated[models.SheetLinkId, Path()],
        body: models.WithdrawSheetPairingRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        withdrawn = comparisons.withdraw_sheet_pairing(
            project_uid=project_uid,
            document_uid=document_uid,
            source_version_uid=version_uid,
            sheet_link_id=sheet_link_id,
            mode=body.mode,
            source_run_id=body.source_run_id,
            target_run_id=body.target_run_id,
            idempotency_key=idempotency_key,
            author_label=subject.display_label,
            author_user_uid=subject.user_uid,
        )
        return json_response(201, encode_json(withdrawn.model_dump(mode="json")))

    @router.post(
        f"{_VERSION_PATH}/comparison/summaries",
        operation_id="generateComparisonSummary",
        tags=["documents"],
        status_code=201,
        response_model=models.GenerateComparisonSummaryResponse,
        responses={
            **success(201, "The stored summary of the approved pairs, new or an exact repeat."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        description=(
            "Ask the model once, on purpose, for a summary of the approved sheet pairs of the "
            "path's (older) version and `target_version_uid`, and store the answer. This is the "
            "only operation that calls a model about a comparison; reading the comparison never "
            "does. The command recomputes the approved pairs' raw differences and their seal in its "
            "own transaction and needs them `sealed`; it builds the bounded input from the changed "
            "lines only (an input beyond the bound is refused, never shortened) and takes nothing "
            "from the client but the view. The reply is checked: every change it cites must exist; "
            "a reply that cites one that does not is stored as `rejected` (it was paid for) and "
            "returned as an answer, with no statements. The summary is stored append-only with the "
            "input digest, the prompt version, the provider mode and model identity, its statements "
            "and the span identities each cites; it never alters the raw differences, which the "
            "comparison returns exactly as computed, and it carries a fixed label saying no human "
            "reviewed it. The cost goes through the cost meter; in this release only the recorded "
            "implementation exists (`provider_mode: recorded`, `cost_basis: unmetered`), and a "
            "process in any other mode answers `503 dependency_unavailable` "
            "(`dependency: comparison_summary_model`). A missing recording is `422 "
            "analysis_input_invalid` and stores nothing. An exact repeat (same sealed input and prompt "
            "version, any key) answers the stored summary, `replayed: true`. A refusal before any "
            "call is `conflict` with `conflict_reason` `summary_evidence_not_sealed`, "
            "`summary_input_empty` or `summary_input_too_large`, or `comparison_not_available`. "
            "`expert` is required; `admin` alone is refused (`required_capability: role:expert`)."
        ),
    )
    def generate_comparison_summary(
        subject: CurrentSubject,
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        version_uid: Annotated[models.VersionUid, Path()],
        body: models.GenerateComparisonSummaryRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        generated = comparisons.generate_comparison_summary(
            project_uid=project_uid,
            document_uid=document_uid,
            source_version_uid=version_uid,
            target_version_uid=body.target_version_uid,
            mode=body.mode,
            source_run_id=body.source_run_id,
            target_run_id=body.target_run_id,
            idempotency_key=idempotency_key,
            author_label=subject.display_label,
            author_user_uid=subject.user_uid,
        )
        return json_response(201, encode_json(generated.model_dump(mode="json")))
