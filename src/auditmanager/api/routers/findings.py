"""``listRunFindings`` and ``getFinding``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import (
    CategoryFilterParam,
    CursorParam,
    LimitParam,
    VerdictFilterParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.ports import FindingPort, RunPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate
from auditmanager.api.schemas.findings import finding_body, finding_detail_body

__all__ = ["build_finding_routes"]


def build_finding_routes(
    router: APIRouter, findings: FindingPort, runs: RunPort
) -> None:
    """`D-67`. ``runs`` is here for one reason: ``listRunFindings`` addresses a run.

    The port is not used to list anything. It is used to answer the question the path
    asks before the collection is read -- *is there such a run* -- because an empty page
    and a missing parent are different facts and this operation answered both with the
    same bytes. See the note on ``list_run_findings``.
    """

    @router.get(
        "/runs/{run_id}/findings",
        operation_id="listRunFindings",
        tags=["findings"],
        status_code=200,
        response_model=models.FindingPage,
        responses={
            **success(200, "One page of this run's published findings."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def list_run_findings(
        run_id: Annotated[models.RunId, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
        category: CategoryFilterParam = None,  # type: ignore[assignment]
        verdict: VerdictFilterParam = None,  # type: ignore[assignment]
    ) -> WireResponse:
        # The filters reach the port as the contract's own values or as `None`. A value
        # outside either enum never gets here: the parameter is typed with the frozen enum,
        # so FastAPI refuses it and `on_request_validation_error` renders `constraint:
        # enum`. An empty page would read as "this run has no findings of that kind",
        # which is a different and wrong answer to "that kind does not exist".
        # `D-67`. The parent is proved to exist before its collection is read, so an
        # unknown run is `not_found` rather than an empty page.
        #
        # **Why here and not in the adapter**, which is where `listRuns` proves its own
        # parent. What is being honoured is a statement the *frozen contract* makes about
        # this operation -- `listRunFindings` declares `404` and has never produced one --
        # and the operation is this function. Put in the adapter, the rule holds for
        # whichever implementation happens to be wired; put here, it holds for the surface,
        # which is the thing the contract describes and the thing a client talks to. The
        # three test wirings of this router are three implementations, and `W37-CERT4`
        # found this defect through none of them.
        #
        # The cost is one extra read of the run on every listing, and it is real: the
        # shipped `RunAdapter.get_run_status` builds the whole `RunStatus`, stages and cost
        # included, to answer a yes/no. A narrower `RunPort` method would be the cheaper
        # shape and it is not this task's to add -- the port's implementations are outside
        # this stream's paths, and a port method nobody implements is a red gate.
        runs.get_run_status(run_id=run_id)
        rows = findings.list_run_findings(
            run_id=run_id,
            category=category.value if category else None,
            verdict=verdict.value if verdict else None,
        )
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_finding_sort_key)
        body = page_body([finding_body(view) for view in page.items], page.next_cursor)
        return json_response(200, encode_json(body))

    @router.get(
        "/findings/{finding_uid}",
        operation_id="getFinding",
        tags=["findings"],
        status_code=200,
        response_model=models.FindingDetail,
        responses={
            **success(200, "One finding with its observation, evidence and provenance."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
    )
    def get_finding(finding_uid: Annotated[models.FindingUid, Path()]) -> WireResponse:
        view = findings.get_finding(finding_uid=finding_uid)
        return json_response(200, encode_json(finding_detail_body(view)))



def _finding_sort_key(view: object) -> tuple[str, ...]:
    """``(finding_uid, finding_observation_id)`` -- opaque identifiers, a total order.

    The same key family the CSV sorts on (``P02_SEAMS.md`` section 6), so a page boundary
    and a CSV row order cannot disagree about what "next" means.
    """
    return (
        getattr(view, "finding_uid"),
        getattr(getattr(view, "observation"), "finding_observation_id"),
    )
