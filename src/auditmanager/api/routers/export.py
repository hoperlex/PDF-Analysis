"""``exportRunCsv``.

The handler adds **nothing** to what :class:`~auditmanager.api.routers.ports.CsvExportPort`
returns. No rendering, no column list, no quoting, no policy: ``P02_SEAMS.md`` section 6
freezes all of it. ``P2-API-01`` says so in its non-goals -- *no CSV rendering logic in the
router* -- and the reason is that a second producer of these bytes is a second thing to keep
byte-identical. The BOM and the CRLF line endings are inside the bytes the port produces,
and ``records/12-exportRunCsv.success.json`` compares them as bytes.

Nothing is created here. There is no export resource, no export identity and nothing to
poll, because a synchronous read creates nothing.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path, Response

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import CsvExportPort
from auditmanager.api.routers.wire import WireResponse
from auditmanager.api.schemas import models

__all__ = ["build_export_routes"]

#: The BOM is inside the bytes the port produces (section 6), so the charset parameter
#: describes the encoding and does not add one.
_CSV: Final[str] = "text/csv; charset=utf-8"

#: The contract's media type, without the charset parameter: a media *type* and its
#: parameters are different things, and the document declares the type.
_CSV_MEDIA_TYPE: Final[str] = "text/csv"


def build_export_routes(router: APIRouter, exports: CsvExportPort) -> None:

    @router.get(
        "/runs/{run_id}/export.csv",
        operation_id="exportRunCsv",
        tags=["export"],
        status_code=200,
        response_class=Response,
        responses={
            **success(
                200,
                "The CSV for this exact project, version and run.",
                content={_CSV_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
                headers={
                    "Content-Disposition": {
                        "schema": {"type": "string"},
                        "description": "Attachment with a display file name built from "
                        "opaque identifiers. The file name is presentation only and is "
                        "never an identity.",
                    }
                },
            ),
            **envelope_responses(401, 403, 404, 409, 500, 503),
        },
    )
    def export_run_csv(run_id: Annotated[models.RunId, Path()]) -> WireResponse:
        # A run whose terminal does not publish a result raises
        # `state_transition_not_allowed` from the port; the handlers render it. This
        # handler does not read the run's state to decide, because the discriminator is
        # the frozen `terminal_semantics.publishes_result` flag and a hand-written state
        # list here would be a second, drifting copy of it.
        content = exports.export_run_csv(run_id=run_id)
        return WireResponse(
            200,
            (
                ("Content-Type", _CSV),
                ("Content-Length", str(len(content))),
                ("Content-Disposition", _disposition(run_id)),
            ),
            content,
        )



def _disposition(run_id: str) -> str:
    """An attachment name built from the opaque run identity and nothing else.

    The frozen document allows a display file name here and says it "is presentation only
    and is never an identity". Building it from the ``run_id`` keeps that true: there is no
    source file name, no project label and no path in it, so the header reveals nothing the
    response body does not already carry.
    """
    return f'attachment; filename="{run_id}.csv"'
