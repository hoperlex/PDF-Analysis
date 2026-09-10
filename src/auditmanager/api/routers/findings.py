"""``listRunFindings`` and ``getFinding``."""

from __future__ import annotations

import json
from typing import Sequence

from auditmanager.api.routers.http import Request, Response, Route, json_response
from auditmanager.api.routers.idempotency import require_path_identity
from auditmanager.api.routers.ports import FindingPort
from auditmanager.api.schemas.common import page_body, paginate, parse_limit
from auditmanager.api.schemas.findings import (
    FINDING_CATEGORIES,
    VERDICTS,
    finding_body,
    finding_detail_body,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import FindingUid, RunId

__all__ = ["build_finding_routes"]


def build_finding_routes(findings: FindingPort) -> Sequence[Route]:
    def list_run_findings(request: Request) -> Response:
        run_id = require_path_identity(
            request.path_params["run_id"], parse=RunId, aggregate_type="AuditRun"
        )
        limit = parse_limit(request.query_one("limit"))
        cursor = request.query_one("cursor")
        category = _enum_filter(request.query_one("category"), FINDING_CATEGORIES, "category")
        verdict = _enum_filter(request.query_one("verdict"), VERDICTS, "verdict")

        rows = findings.list_run_findings(
            run_id=str(run_id), category=category, verdict=verdict
        )
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_finding_sort_key)
        body = page_body([finding_body(view) for view in page.items], page.next_cursor)
        return json_response(200, _encode(body))

    def get_finding(request: Request) -> Response:
        finding_uid = require_path_identity(
            request.path_params["finding_uid"],
            parse=FindingUid,
            aggregate_type="Finding",
        )
        view = findings.get_finding(finding_uid=str(finding_uid))
        return json_response(200, _encode(finding_detail_body(view)))

    return (
        Route("listRunFindings", "GET", "/runs/{run_id}/findings", list_run_findings),
        Route("getFinding", "GET", "/findings/{finding_uid}", get_finding),
    )


def _enum_filter(raw: str | None, allowed: frozenset[str], field: str) -> str | None:
    """Validate a closed-enum query filter.

    A value outside the enum is ``validation_failed`` rather than an empty page. An
    empty page would read as "this run has no findings of that kind", which is a
    different and wrong answer to "that kind does not exist".
    """
    if raw is None or raw == "":
        return None
    if raw not in allowed:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"The {field} filter must be one of: {', '.join(sorted(allowed))}.",
            field=field,
            constraint="enum",
        )
    return raw


def _finding_sort_key(view: object) -> tuple[str, ...]:
    """``(finding_uid, finding_observation_id)`` -- opaque identifiers, a total order.

    The same key family the CSV sorts on (``P02_SEAMS.md`` section 6), so a page
    boundary and a CSV row order cannot disagree about what "next" means.
    """
    return (
        getattr(view, "finding_uid"),
        getattr(getattr(view, "observation"), "finding_observation_id"),
    )


def _encode(body: object) -> bytes:
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
