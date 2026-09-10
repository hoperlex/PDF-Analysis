"""``startRun`` and ``getRunStatus``.

Both delegate to :class:`~auditmanager.api.routers.ports.RunPort`, which session ``B5``
satisfies. Neither router knows what a stage is, what schedules one, or what makes a
run terminal: it parses, calls, and renders the frozen ``RunStatus``.
"""

from __future__ import annotations

import json
from typing import Sequence

from auditmanager.api.routers.errors import decode_json_object
from auditmanager.api.routers.http import Request, Response, Route, json_response
from auditmanager.api.routers.idempotency import (
    require_idempotency_key,
    require_path_identity,
)
from auditmanager.api.routers.ports import RunPort
from auditmanager.api.schemas.runs import parse_start_run_request, run_status_body
from auditmanager.shared.identity import RunId

__all__ = ["build_run_routes"]


def build_run_routes(runs: RunPort) -> Sequence[Route]:
    def start_run(request: Request) -> Response:
        key = require_idempotency_key(request)
        command = parse_start_run_request(decode_json_object(request.body))
        view = runs.start_run(
            version_uid=command.version_uid,
            provider_mode=command.provider_mode,
            idempotency_key=key,
        )
        # 202, and the same 202 for a replay under the same key and payload: the run
        # exists either way, and the frozen document gives both the one status.
        return json_response(202, _encode(run_status_body(view)))

    def get_run_status(request: Request) -> Response:
        run_id = require_path_identity(
            request.path_params["run_id"], parse=RunId, aggregate_type="AuditRun"
        )
        view = runs.get_run_status(run_id=str(run_id))
        return json_response(200, _encode(run_status_body(view)))

    return (
        Route("startRun", "POST", "/runs", start_run),
        Route("getRunStatus", "GET", "/runs/{run_id}", get_run_status),
    )


def _encode(body: object) -> bytes:
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
