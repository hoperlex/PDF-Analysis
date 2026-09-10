"""``exportRunCsv``.

The router adds **nothing** to what :class:`~auditmanager.api.routers.ports.CsvExportPort`
returns. No rendering, no column list, no quoting, no policy: ``P02_SEAMS.md`` section 6
freezes all of it and ``B5`` produces it. ``P2-API-01`` says so in its non-goals -- *no
CSV rendering logic in the router* -- and the reason is that a second producer of these
bytes is a second thing to keep byte-identical.

Nothing is created here. There is no export resource, no export identity and nothing to
poll, because a synchronous read creates nothing.
"""

from __future__ import annotations

from typing import Final, Sequence

from auditmanager.api.routers.http import Request, Response, Route
from auditmanager.api.routers.idempotency import require_path_identity
from auditmanager.api.routers.ports import CsvExportPort
from auditmanager.shared.identity import RunId

__all__ = ["build_export_routes"]

#: The BOM is inside the bytes `B5` produces (section 6), so the charset parameter
#: describes the encoding and does not add one.
_CSV: Final[str] = "text/csv; charset=utf-8"


def build_export_routes(exports: CsvExportPort) -> Sequence[Route]:
    def export_run_csv(request: Request) -> Response:
        run_id = require_path_identity(
            request.path_params["run_id"], parse=RunId, aggregate_type="AuditRun"
        )
        # A run whose terminal does not publish a result raises
        # `state_transition_not_allowed` from the port; the middleware renders it. The
        # router does not read the run's state to decide, because the discriminator is
        # the frozen `terminal_semantics.publishes_result` flag and a hand-written
        # state list here would be a second, drifting copy of it.
        content = exports.export_run_csv(run_id=str(run_id))
        return Response(
            200,
            (
                ("Content-Type", _CSV),
                ("Content-Length", str(len(content))),
                ("Content-Disposition", _disposition(str(run_id))),
            ),
            content,
        )

    return (
        Route("exportRunCsv", "GET", "/runs/{run_id}/export.csv", export_run_csv),
    )


def _disposition(run_id: str) -> str:
    """An attachment name built from the opaque run identity and nothing else.

    The frozen document allows a display file name here and says it "is presentation
    only and is never an identity". Building it from the ``run_id`` keeps that true:
    there is no source file name, no project label and no path in it, so the header
    reveals nothing the response body does not already carry.
    """
    return f'attachment; filename="{run_id}.csv"'
