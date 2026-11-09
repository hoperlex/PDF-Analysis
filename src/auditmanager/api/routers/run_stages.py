"""The stages of a run (`HOSTS-SEAL-2`, ADR-0028, contract 1.46.0): one route.

====================================  =====================================================================================
``getRunStages``                      any role that reads a run; each chip the run has with its plan and its facts. The server and
                                      the access of a cell are omitted for the viewer («Наблюдатель», `R-150w`)
====================================  =====================================================================================

A router decides nothing about roles (``api/security.py``) and nothing about stages: the three places the facts come from and the
omission for the viewer are ``runs/stage_facts.py``'s, reached through :class:`~auditmanager.api.routers.hosts_ports.RunStagePort`.

**Declared, and answerable only with a port.** ``build_router`` declares the route whatever the port; a router built with no port
answers none (``503 dependency_unavailable``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.hosts_ports import RunStagePort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_run_stage_routes"]


def build_run_stage_routes(router: APIRouter, run_stages: RunStagePort) -> None:
    @router.get(
        "/runs/{run_id}/stages", operation_id="getRunStages", tags=["runs"],
        response_model=models.RunStages,
        responses={**success(200, "Each chip the run has, in the order the rail draws them, with its plan and its facts."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
        description=(
            "`HOSTS-SEAL-2` (ADR-0028, plan section 9.4): the data of the window «Этапы анализа раздела». For each chip of the run -- "
            "`preparation`, `text`, `blocks`, `cross_check`, `merge`, `norms`, `review`, `correction` and, for the AR v3 profile, "
            "`ar_v3`, in that order, only those the run has -- the code stage ids it covers, its **plan** (the cells the run froze in its "
            "`stage_plan`: role, model, effort, answer limit, timeout, access and the server the cell is bound to; for a run that froze "
            "none, one line from its binding) and its **facts**: the state; the first and last call (or the stage result's times); the "
            "calls succeeded, failed and retried; the input and output tokens, the part of them served by a subscription and the cost; "
            "the last error code; and the batches planned and completed where the extended review keeps them. The facts come from "
            "the stage results, the extended review artifact and the call journal; a call journalled before migration `0062` has no "
            "`stage_key` and is placed by its extended phase. `role:admin|expert|viewer`: the viewer reads the run's stages but "
            "never the server or the access (`R-150w`), which are absent from the answer. `404 not_found` for an unknown run."
        ),
    )
    def get_run_stages(subject: CurrentSubject, run_id: Annotated[models.RunId, Path()]) -> WireResponse:
        view = run_stages.get_run_stages(run_id=run_id, user_uid=subject.user_uid)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))
