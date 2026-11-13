"""``exportRunCsv`` and ``exportRunXlsx``.

The handler adds **nothing** to what :class:`~auditmanager.api.routers.ports.CsvExportPort`
returns. No rendering, no column list, no quoting, no policy: ``P02_SEAMS.md`` section 6
freezes all of it. ``P2-API-01`` says so in its non-goals -- *no CSV rendering logic in the
router* -- and the reason is that a second producer of these bytes is a second thing to keep
byte-identical. The BOM and the CRLF line endings are inside the bytes the port produces,
and ``records/12-exportRunCsv.success.json`` compares them as bytes.

Nothing is created here. There is no export resource, no export identity and nothing to
poll, because a synchronous read creates nothing.

``exportRunXlsx`` (`W57B-NORMS-CATALOGUE-XLSX-01`) is the same bargain for the W57b
workbook: :class:`~auditmanager.api.routers.ports.XlsxExportPort` returns the bytes and
every refusal, and this file adds the media type and the download name -- built by
:func:`_disposition`, the one place a download name is spelled.

``importRunDecisions`` (`R-151d`, contract 1.27.0) is the way back: the same workbook, edited,
uploaded for the same run. The file handle goes to the port unread; the reading, every refusal
and the per-row report are ``auditmanager.exports.import_run_decisions``'s.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal

from fastapi import APIRouter, Depends, Form, Path, Response, Query

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.multipart import CheckedUpload, UploadRoute, require_a_strict_multipart_body
from auditmanager.api.routers.ports import CsvExportPort, XlsxExportPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_export_routes"]

#: The BOM is inside the bytes the port produces (section 6), so the charset parameter
#: describes the encoding and does not add one.
_CSV: Final[str] = "text/csv; charset=utf-8"

#: The contract's media type, without the charset parameter: a media *type* and its
#: parameters are different things, and the document declares the type.
_CSV_MEDIA_TYPE: Final[str] = "text/csv"

#: The workbook's media type; the bytes carry no charset parameter.
_XLSX_MEDIA_TYPE: Final[str] = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

_DISPOSITION_HEADER: Final[dict[str, object]] = {
    "schema": {"type": "string"},
    "description": "Attachment with a display file name built from "
    "opaque identifiers. The file name is presentation only and is "
    "never an identity.",
}


def build_export_routes(
    router: APIRouter, exports: CsvExportPort, xlsx: XlsxExportPort | None = None
) -> None:

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
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
    )
    def export_run_csv(run_id: Annotated[models.RunId, Path()],
                       verdict: Annotated[Literal["active", "all", "unreviewed", "accepted", "rejected"], Query()] = "all") -> WireResponse:
        # A run whose terminal does not publish a result raises
        # `state_transition_not_allowed` from the port; the handlers render it. This
        # handler does not read the run's state to decide, because the discriminator is
        # the frozen `terminal_semantics.publishes_result` flag and a hand-written state
        # list here would be a second, drifting copy of it.
        content = exports.export_run_csv(run_id=run_id, **({"verdict": verdict} if verdict != "all" else {}))
        return WireResponse(
            200,
            (
                ("Content-Type", _CSV),
                ("Content-Length", str(len(content))),
                ("Content-Disposition", _disposition(run_id)),
            ),
            content,
        )

    @router.get(
        "/runs/{run_id}/export.xlsx",
        operation_id="exportRunXlsx",
        tags=["export"],
        status_code=200,
        response_class=Response,
        responses={
            **success(
                200,
                "The workbook for this exact run: «Сводка» and «Замечания».",
                content={_XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
                headers={"Content-Disposition": _DISPOSITION_HEADER},
            ),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
    )
    def export_run_xlsx(
        subject: CurrentSubject, run_id: Annotated[models.RunId, Path()],
        verdict: Annotated[Literal["active", "all", "unreviewed", "accepted", "rejected"], Query()] = "all",
    ) -> WireResponse:
        # Every refusal is the port's -- the run's state, its sheet labels, its citations;
        # this handler reads nothing and decides nothing.
        content = xlsx.export_run_xlsx(  # type: ignore[union-attr]
            run_id=run_id, principal_id=subject.user_uid, **({"verdict": verdict} if verdict != "all" else {})
        )
        return WireResponse(
            200,
            (
                ("Content-Type", _XLSX_MEDIA_TYPE),
                ("Content-Length", str(len(content))),
                ("Content-Disposition", _disposition(run_id, suffix="xlsx")),
            ),
            content,
        )

    # Declared through ``add_api_route`` for ``route_class_override``: ``UploadRoute`` parses the
    # form under the upload's small part bounds, as it does for ``uploadPriceList``.
    def import_run_decisions(
        subject: CurrentSubject,
        run_id: Annotated[models.RunId, Path()],
        body: Annotated[models.ImportRunDecisionsRequest, Form(media_type="multipart/form-data")],
        idempotency_key: RequiredIdempotencyKey,
        checked: Annotated[CheckedUpload, Depends(require_a_strict_multipart_body)],
    ) -> WireResponse:
        del checked  # a repeated, unnamed or filename-less part was refused before this runs
        report = xlsx.import_run_decisions(  # type: ignore[union-attr]
            run_id=run_id, content=body.file.file, idempotency_key=idempotency_key,
            author_label=subject.display_label, author_user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(report.model_dump(mode="json", exclude_none=True)))

    router.add_api_route(
        "/runs/{run_id}/decision-imports",
        import_run_decisions,
        methods=["POST"],
        operation_id="importRunDecisions",
        tags=["export"],
        status_code=200,
        response_model=models.DecisionImportReport,
        responses={
            **success(200, "What the import did with each row that names an ID or a decision."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
        route_class_override=UploadRoute,
        description=(
            "`UI-PARITY-P0L` (contract 1.27.0, ruling `R-151d`): load back the run's workbook as "
            "`exportRunXlsx` produced it, with «Решение эксперта» and «Комментарий» edited, at most 10 MiB. "
            "Only our export is read: a workbook without a «Замечания» sheet naming the columns «ID замечания», "
            "«Решение эксперта» and «Комментарий» is `422 validation_failed` (`field: file`, `constraint: "
            "not_our_export`), as is a file that is not a readable XLSX (`unreadable`), is larger (`too_large`) "
            "or has more than 20 000 rows (`too_many_rows`); nothing is recorded then. Rows are matched by "
            "`finding_uid`, never by «№». A row whose decision changes appends an `accept` or `reject` event "
            "carrying the row's comment, a row whose comment alone changes appends a `comment` event, both "
            "authored by the caller exactly as `appendDecision` would; the severity columns are not read and "
            "nothing is revoked. Every row naming an ID or a decision is reported, in sheet order, as "
            "`recorded`, `unchanged` or `refused` with a `reason`: `no_finding_uid`, `duplicate_finding`, "
            "`unknown_finding`, `finding_not_in_run`, `unknown_decision` (not one of the four labels the "
            "export writes) or `not_importable` («не решено» or «нужен ручной разбор» over another verdict). "
            "`finding_uid` is reported only for a published finding. An unknown run is `404`. An exact repeat "
            "of the `Idempotency-Key` answers the stored report and appends nothing; the same key with another "
            "file, run or caller is `409 idempotency_key_reuse`. `expert` only."
        ),
    )


def _disposition(run_id: str, *, suffix: str = "csv") -> str:
    """An attachment name built from the opaque run identity and nothing else.

    The frozen document allows a display file name here and says it "is presentation only
    and is never an identity". Building it from the ``run_id`` keeps that true: there is no
    source file name, no project label and no path in it, so the header reveals nothing the
    response body does not already carry. The CSV is ``attachment; filename="{run_id}.csv"``
    and the workbook the same name with ``.xlsx``.
    """
    return f'attachment; filename="{run_id}.{suffix}"'


def attachment_disposition(opaque_id: str, *, suffix: str) -> str:
    """The same single spelling for another download named by an opaque identity.

    ``_disposition`` stays the one place that writes ``attachment;``; a second router that
    serves a download (the optimisation proposals' CSV) asks it here instead of spelling
    the header again, so the download-name guard keeps pointing at one file.
    """
    return _disposition(opaque_id, suffix=suffix)
