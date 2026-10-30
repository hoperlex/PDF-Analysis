"""The MD summary of a series and the PDF reports built from it, sealed as stubs (`CMP-SEAL-C2`,
ADR-0025 decisions 3, 17, 19 and 20).

``streamComparisonSeriesSummary`` is the deterministic MD summary (the same bytes for the same data).
A report is made in two steps so that an estimate precedes every spend: ``createComparisonReport`` (from
the series' summary) or ``uploadComparisonReportSource`` (from an uploaded MD file) makes a ``draft`` with
its estimate and calls no model; ``startComparisonReport`` consents to that estimate. ``getComparisonReport``
and ``listComparisonReports`` read the state, the per-transition progress, the usage and the history;
``cancelComparisonReport``, ``continueComparisonReport``, ``rebuildComparisonReportPdf`` («Пересобрать
PDF», no model call), ``deleteComparisonReport`` and ``prepareComparisonClientReport`` steer them;
``streamComparisonReportPdf`` and ``streamComparisonReportSourceMd`` download. Reads are any one role; every
write is an expert's act (`R-60`) and keyed. All thirteen answer ``503 dependency_unavailable`` until
`CMP-VC-REPORT-01` wires the port, and ``comparison_modules`` first while the versions module is off.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel, WithJsonSchema

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonReportPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["MAX_REPORT_SOURCE_BYTES", "build_comparison_report_routes"]

#: The original's limit for an uploaded summary (`MAX_UPLOAD_BYTES`, 20 MiB); under the proxy's 32 MiB.
MAX_REPORT_SOURCE_BYTES: Final[int] = 20 * 1024 * 1024
_TAGS: Final[list[str]] = ["comparison"]
_MARKDOWN: Final[str] = "text/markdown; charset=utf-8"
_PDF: Final[str] = "application/pdf"
_MARKDOWN_CONTENT = {"text/markdown": {"schema": {"type": "string"}}}
_PDF_CONTENT = {_PDF: {"schema": {"type": "string", "format": "binary"}}}
_REPORT: Final[str] = "/comparison-reports/{comparison_report_id}"

_SeriesId = Annotated[models.ComparisonSeriesId, Path()]
_ReportId = Annotated[models.ComparisonReportId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def _download(content: bytes, media_type: str) -> WireResponse:
    return WireResponse(
        200, (("Content-Type", media_type), ("Content-Length", str(len(content)))), content
    )


def build_comparison_report_routes(router: APIRouter, reports: ComparisonReportPort) -> None:
    @router.get('/comparison-series/{comparison_series_id}/technical-report', operation_id='streamComparisonTechnicalReport', tags=_TAGS, status_code=200, response_class=WireResponse,
        responses={**success(200, 'Technical comparison workbook or HTML source bundle.', content={'application/octet-stream':{'schema':{'type':'string','format':'binary'}}}), **envelope_responses(401,403,404,409,422,500,503)})
    def stream_technical_report(comparison_series_id: _SeriesId, format: Annotated[Literal['xlsx','html'], Query()] = 'xlsx') -> WireResponse:
        view = reports.technical_report(series_id=comparison_series_id, format=format)
        return WireResponse(200, (('Content-Type','application/octet-stream'),('Content-Length',str(len(view.content))),('Content-Disposition',f'attachment; filename="{view.filename}"')), view.content)

    @router.get(
        "/comparison-series/{comparison_series_id}/summary-md",
        operation_id="streamComparisonSeriesSummary", tags=_TAGS, status_code=200,
        response_class=WireResponse,
        responses={**success(200, "The MD summary of the series.", content=_MARKDOWN_CONTENT),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def stream_comparison_series_summary(comparison_series_id: _SeriesId) -> WireResponse:
        content = reports.read_series_summary(series_id=comparison_series_id)
        return _download(content, _MARKDOWN)

    @router.post(
        "/comparison-series/{comparison_series_id}/reports", operation_id="createComparisonReport",
        tags=_TAGS, status_code=201, response_model=models.ComparisonReport,
        responses={**success(201, "The draft report with its estimate, or the recorded outcome of an "
                                  "identical earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def create_comparison_report(
        subject: CurrentSubject, comparison_series_id: _SeriesId,
        body: models.CreateComparisonReportRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = reports.create_report(
            series_id=comparison_series_id,
            kind=body.kind or models.ComparisonReportKind.CLIENT, reuse=bool(body.reuse),
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.post(
        "/comparison-series/{comparison_series_id}/reports/upload",
        operation_id="uploadComparisonReportSource", tags=_TAGS, status_code=201,
        response_model=models.ComparisonReport,
        responses={**success(201, "The draft report made from the uploaded MD file, with its "
                                  "estimate."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def upload_comparison_report_source(
        subject: CurrentSubject, comparison_series_id: _SeriesId,
        content: Annotated[
            bytes,
            Body(media_type="text/markdown", max_length=MAX_REPORT_SOURCE_BYTES),
            WithJsonSchema(
                {"type": "string", "format": "binary", "maxLength": MAX_REPORT_SOURCE_BYTES}
            ),
        ],
        idempotency_key: RequiredIdempotencyKey,
        kind: Annotated[models.ComparisonReportKind, Query()] = None,  # type: ignore[assignment]
        reuse: Annotated[bool, Query()] = False,
        source_name: Annotated[str, Query(min_length=1, max_length=200)] = None,  # type: ignore[assignment]
    ) -> WireResponse:
        view = reports.upload_report_source(
            series_id=comparison_series_id, kind=kind or models.ComparisonReportKind.CLIENT,
            reuse=reuse, content=content,
            source_name=source_name, user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.get(
        "/comparison-series/{comparison_series_id}/reports", operation_id="listComparisonReports",
        tags=_TAGS, status_code=200, response_model=models.ComparisonReportPage,
        responses={**success(200, "One page of the report history of the series, newest first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_reports(
        comparison_series_id: _SeriesId,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = reports.list_reports(series_id=comparison_series_id, cursor=cursor, limit=limit)
        return json_response(200, _body(view))

    @router.get(
        _REPORT, operation_id="getComparisonReport", tags=_TAGS, status_code=200,
        response_model=models.ComparisonReport,
        responses={**success(200, "The report with its progress and downloads."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_report(comparison_report_id: _ReportId) -> WireResponse:
        return json_response(200, _body(reports.get_report(report_id=comparison_report_id)))

    @router.post(
        f"{_REPORT}/start", operation_id="startComparisonReport", tags=_TAGS, status_code=200,
        response_model=models.ComparisonReport,
        responses={**success(200, "The report, started under the estimate it consented to."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def start_comparison_report(
        subject: CurrentSubject, comparison_report_id: _ReportId,
        body: models.StartComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = reports.start_report(
            report_id=comparison_report_id, consent=body.consent, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_REPORT}/cancellation", operation_id="cancelComparisonReport", tags=_TAGS,
        status_code=200, response_model=models.ComparisonReport,
        responses={**success(200, "The report, cancelled."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_comparison_report(
        subject: CurrentSubject, comparison_report_id: _ReportId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = reports.cancel_report(
            report_id=comparison_report_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_REPORT}/continuation", operation_id="continueComparisonReport", tags=_TAGS,
        status_code=200, response_model=models.ComparisonReport,
        responses={**success(200, "The report, continued with its finished parts reused."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def continue_comparison_report(
        subject: CurrentSubject, comparison_report_id: _ReportId,
        body: models.ResumeComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = reports.continue_report(
            report_id=comparison_report_id, consent=body.consent, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_REPORT}/pdf-rebuild", operation_id="rebuildComparisonReportPdf", tags=_TAGS,
        status_code=200, response_model=models.ComparisonReport,
        responses={**success(200, "The report, with its PDF written again from the stored text. No "
                                  "model is called."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def rebuild_comparison_report_pdf(
        subject: CurrentSubject, comparison_report_id: _ReportId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = reports.rebuild_report_pdf(
            report_id=comparison_report_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_REPORT}/deletion", operation_id="deleteComparisonReport", tags=_TAGS, status_code=200,
        response_model=models.ComparisonReport,
        responses={**success(200, "The report, removed from the history. Its stored bytes stay."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def delete_comparison_report(
        subject: CurrentSubject, comparison_report_id: _ReportId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = reports.delete_report(
            report_id=comparison_report_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_REPORT}/client-report", operation_id="prepareComparisonClientReport", tags=_TAGS,
        status_code=201, response_model=models.ComparisonReport,
        responses={**success(201, "The client report prepared from the analytic report, as a "
                                  "draft with its estimate."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def prepare_comparison_client_report(
        subject: CurrentSubject, comparison_report_id: _ReportId,
        body: models.PrepareComparisonClientReportRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = reports.prepare_client_report(
            report_id=comparison_report_id, reuse=bool(body.reuse), user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.get(
        f"{_REPORT}/pdf", operation_id="streamComparisonReportPdf", tags=_TAGS, status_code=200,
        response_class=WireResponse,
        responses={**success(200, "The report's PDF.", content=_PDF_CONTENT),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def stream_comparison_report_pdf(comparison_report_id: _ReportId) -> WireResponse:
        return _download(reports.read_report_pdf(report_id=comparison_report_id), _PDF)

    @router.get(
        f"{_REPORT}/source-md", operation_id="streamComparisonReportSourceMd", tags=_TAGS,
        status_code=200, response_class=WireResponse,
        responses={**success(200, "The exact MD the report was built from.",
                             content=_MARKDOWN_CONTENT),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def stream_comparison_report_source_md(comparison_report_id: _ReportId) -> WireResponse:
        return _download(reports.read_report_source_md(report_id=comparison_report_id), _MARKDOWN)
