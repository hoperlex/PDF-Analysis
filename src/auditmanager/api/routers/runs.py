"""``startRun``, ``getRunStatus`` and ``listRuns``.

Both delegate to :class:`~auditmanager.api.routers.ports.RunPort`. Neither handler knows
what a stage is, what schedules one, or what makes a run terminal: it takes a validated
model, calls one port method, and renders the frozen ``RunStatus``.

**One behaviour a Pydantic model can move without noticing.** ``startRun`` with the same
idempotency key and a payload differing only by ``provider_mode`` is a **replay**, not a
conflict -- 202 with the original run, byte for byte. At the command layer a different
payload raises ``idempotency_key_reuse``; at this transport the property is normalised away
before the fingerprint, because ``RunAdapter.start_run`` refuses a disagreeing mode and
otherwise forwards the configured one. `W13-BASE` section 7 captured it as baseline case
``05``, beside ``04`` (a plain replay) and ``05b`` (a genuine conflict). A model that
defaulted ``provider_mode`` to a value, or forwarded one where the parser forwarded
``None``, would move a request between those three -- which is why
``StartRunRequest.provider_mode`` is declared with ``Field(default=None, ...)`` and no
``default_factory``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import RunPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate
from auditmanager.api.schemas.runs import run_status_body

__all__ = ["build_run_routes"]


def build_run_routes(router: APIRouter, runs: RunPort) -> None:

    @router.post(
        "/runs",
        operation_id="startRun",
        tags=["runs"],
        status_code=202,
        response_model=models.RunStatus,
        responses={
            **success(202, "The run was accepted, or an identical earlier one replayed."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
    )
    def start_run(
        body: models.StartRunRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = runs.start_run(
            version_uid=body.version_uid,
            provider_mode=body.provider_mode.value if body.provider_mode else None,
            idempotency_key=idempotency_key,
        )
        # 202, and the same 202 for a replay under the same key and payload: the run
        # exists either way, and the frozen document gives both the one status.
        return json_response(202, encode_json(run_status_body(view)))

    @router.get(
        "/runs/{run_id}",
        operation_id="getRunStatus",
        tags=["runs"],
        status_code=200,
        response_model=models.RunStatus,
        responses={
            **success(200, "The run's current state and its per-stage state."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
    )
    def get_run_status(run_id: Annotated[models.RunId, Path()]) -> WireResponse:
        view = runs.get_run_status(run_id=run_id)
        return json_response(200, encode_json(run_status_body(view)))

    @router.get(
        "/runs/{run_id}/norm-verification",
        operation_id="getRunNormVerification",
        tags=["runs"],
        status_code=200,
        response_model=models.NormVerificationReport,
        responses={
            **success(200, "The verified v3 report, including certified citation partitions and deterministic withholding counts."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
        description=(
            "Read a verified v3 normative report for a run. R-80: any one active "
            "expert or admin role; an empty role set is refused. A v1/v2 run answers "
            "not_found. Until the CITE verified reader is implemented, this endpoint "
            "answers typed 503 dependency_unavailable and exposes no unverified "
            "citation data (D-151)."
        ),
    )
    def get_run_norm_verification(run_id: Annotated[models.RunId, Path()]) -> WireResponse:
        report = runs.get_norm_verification(run_id=run_id)
        return json_response(200, encode_json(report.model_dump(mode="json")))

    @router.get(
        "/runs/{run_id}/norm-references",
        operation_id="getRunNormReferences",
        tags=["runs"],
        status_code=200,
        response_model=models.RunNormReferences,
        responses={
            **success(200, "The norms the run's saved text cites, or the state that stops it."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
        description=(
            "«Нормативные ссылки»: the normative documents (СП, ГОСТ, СНиП, СанПиН, ВСН, "
            "federal laws and government acts) cited in the run's saved text, each resolved "
            "against the norms snapshot the run pinned as `in_corpus`, `newer_edition`, "
            "`older_edition_only` (the corpus holds only an earlier edition than the one "
            "cited), `not_in_corpus` or `not_recognised`, with the pages each occurs on and "
            "the corpus document it points at. Computed per request by the same resolver the "
            "W57b rule uses; publishes no finding, proposes no severity and calls no model. "
            "A precondition that does not hold is `state` (`snapshot_not_pinned`, "
            "`text_unavailable`, `too_many_citations`), never an empty list; the corpus "
            "documents whose designation the parser cannot read are listed as `unrecognised`; "
            "pages without a text layer are `unread_pages`. An unknown run is `404`. Any one "
            "role, `role:admin|expert`."
        ),
    )
    def get_run_norm_references(run_id: Annotated[models.RunId, Path()]) -> WireResponse:
        answer = runs.get_run_norm_references(run_id=run_id)
        # `exclude_unset`: an answer that is not `ready` omits the list's properties, as the
        # contract declares them optional and not nullable.
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/versions/{version_uid}/runs",
        operation_id="listRuns",
        tags=["runs"],
        status_code=200,
        response_model=models.RunStatusPage,
        responses={
            **success(200, "One page of this version's runs, newest first."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def list_runs(
        version_uid: Annotated[models.VersionUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        # Each item is the whole `RunStatus`, byte for byte what `getRunStatus` answers
        # for that run: `RunAdapter.list_runs` builds every item through the same
        # `_run_status_view` the single read uses, so a run cannot say two things.
        rows = runs.list_runs(version_uid=version_uid)
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_run_sort_key)
        body = page_body(
            [run_status_body(view) for view in page.items], page.next_cursor
        )
        return json_response(200, encode_json(body))


def _run_sort_key(view: object) -> tuple[str, ...]:
    """The opaque identity, which is also the listing's total order."""
    return (getattr(view, "run_id"),)
