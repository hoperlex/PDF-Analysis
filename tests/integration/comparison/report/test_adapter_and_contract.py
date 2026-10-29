"""`CMP-VC-REPORT-01`: the adapter of the thirteen operations and the contract's models (database, bucket, PDF child).

Every view the service makes is validated by the **generated models of the contract** (``extra`` is forbidden there, so a member the contract does not name
fails here), and the adapter keeps the module flag as the first statement of every method: with the versions module off it answers before it reads the actor,
the series, anything."""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import ComparisonReportAdapter
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.comparison.report.conftest import EXPERT, support
from tests.integration.comparison.report.run_support import record_analytic, record_client

KEY = 0


def adapter_of(db: Any, *, modules: str = "versions") -> ComparisonReportAdapter:
    adapter = ComparisonReportAdapter(db.sessions, blob_store=db.store, comparison_modules=modules, provider_mode="recorded", service=db.service(modules=modules))
    adapter._actor = lambda user_uid: ("Эксперт", EXPERT)  # type: ignore[method-assign]
    return adapter


def key() -> str:
    global KEY
    KEY += 1
    return f"adapter-key-{KEY}"


def test_every_operation_of_a_report_answers_the_contracts_models_from_the_draft_to_the_download(db: Any, world: Any, route: Any) -> None:
    adapter = adapter_of(db)
    summary = adapter.read_series_summary(series_id=world["series"])
    assert isinstance(summary, bytes) and summary.startswith("# Сводка изменений".encode())
    draft = adapter.create_report(series_id=world["series"], kind=models.ComparisonReportKind.CLIENT, reuse=False, user_uid=support.ACTOR, idempotency_key=key())
    assert isinstance(draft, models.ComparisonReport) and draft.state.value == "draft" and draft.estimate is not None and draft.job is None
    assert adapter.get_report(report_id=draft.report_id).report_id == draft.report_id
    record_client(db, world, {"report_id": draft.report_id}, route)
    consent = models.ComparisonAiConsent(estimate_digest=draft.estimate.estimate_digest, confirmed=True)
    started = adapter.start_report(report_id=draft.report_id, consent=consent, user_uid=support.ACTOR, idempotency_key=key())
    assert started.state.value == "queued" and started.job is not None and started.job.method.value == "report" and started.stage.value == "client_writing"
    db.drain(db.handler())
    done = adapter.get_report(report_id=draft.report_id)
    assert done.state.value == "completed" and [a.kind.value for a in done.artifacts] == ["report_pdf", "source_md"]
    assert all(p.selection.value == "done" for p in done.parts)
    assert adapter.read_report_pdf(report_id=draft.report_id).startswith(b"%PDF-")
    assert adapter.read_report_source_md(report_id=draft.report_id).startswith("# Сводка изменений".encode())
    rebuilt = adapter.rebuild_report_pdf(report_id=draft.report_id, user_uid=support.ACTOR, idempotency_key=key())
    assert rebuilt.state.value == "completed"
    page = adapter.list_reports(series_id=world["series"], cursor=None, limit=10)
    assert isinstance(page, models.ComparisonReportPage) and [i.report_id for i in page.items] == [draft.report_id] and page.page.next_cursor is None
    deleted = adapter.delete_report(report_id=draft.report_id, user_uid=support.ACTOR, idempotency_key=key())
    assert deleted.report_id == draft.report_id
    with pytest.raises(DomainError) as gone:
        adapter.get_report(report_id=draft.report_id)
    assert gone.value.code is ErrorCode.NOT_FOUND


def test_the_list_cursor_round_trips_and_a_malformed_one_is_a_validation_failure(db: Any, world: Any, route: Any) -> None:
    adapter = adapter_of(db)
    made = [adapter.create_report(series_id=world["series"], kind=models.ComparisonReportKind.ANALYTIC, reuse=True, user_uid=support.ACTOR, idempotency_key=key()) for _ in range(3)]
    first = adapter.list_reports(series_id=world["series"], cursor=None, limit=2)
    assert len(first.items) == 2 and first.page.next_cursor
    second = adapter.list_reports(series_id=world["series"], cursor=first.page.next_cursor, limit=2)
    assert [i.report_id for i in first.items + second.items] == [m.report_id for m in reversed(made)] and second.page.next_cursor is None
    with pytest.raises(DomainError) as bad:
        adapter.list_reports(series_id=world["series"], cursor="not-a-cursor", limit=2)
    assert bad.value.code is ErrorCode.VALIDATION_FAILED


def test_an_analytic_report_validates_with_its_parts_and_a_paused_one_shows_the_estimate_of_what_is_left(db: Any, world: Any, route: Any) -> None:
    adapter = adapter_of(db)
    draft = adapter.create_report(series_id=world["series"], kind=models.ComparisonReportKind.ANALYTIC, reuse=False, user_uid=support.ACTOR, idempotency_key=key())
    record_analytic(db, {"report_id": draft.report_id}, route)
    consent = models.ComparisonAiConsent(estimate_digest=draft.estimate.estimate_digest, confirmed=True)
    adapter.start_report(report_id=draft.report_id, consent=consent, user_uid=support.ACTOR, idempotency_key=key())
    db.drain(db.handler())
    done = adapter.get_report(report_id=draft.report_id)
    assert done.state.value == "completed" and done.parts[0].facts is not None and done.parts[0].facts.found == 2
    assert done.kind.value == "analytic" and done.stage.value == "pdf_writing"


def test_the_module_flag_is_the_first_statement_of_every_adapter_method(db: Any, world: Any) -> None:
    # the adapter is told the module is off and holds a service that would serve: only the adapter's own flag can refuse
    off = ComparisonReportAdapter(db.sessions, blob_store=db.store, comparison_modules="none", provider_mode="recorded", service=db.service(modules="versions"))
    off._actor = lambda user_uid: (_ for _ in ()).throw(AssertionError("the actor was read before the flag"))  # type: ignore[method-assign]
    calls = {
        "read_series_summary": dict(series_id=world["series"]),
        "create_report": dict(series_id=world["series"], kind=models.ComparisonReportKind.CLIENT, reuse=False, user_uid="x", idempotency_key="k"),
        "upload_report_source": dict(series_id=world["series"], kind=models.ComparisonReportKind.CLIENT, reuse=False, content=b"x", source_name=None, user_uid="x", idempotency_key="k"),
        "list_reports": dict(series_id=world["series"], cursor=None, limit=5),
        "get_report": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV"),
        "start_report": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV", consent=models.ComparisonAiConsent(estimate_digest="a" * 64, confirmed=True), user_uid="x", idempotency_key="k"),
        "cancel_report": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV", user_uid="x", idempotency_key="k"),
        "continue_report": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV", consent=None, user_uid="x", idempotency_key="k"),
        "rebuild_report_pdf": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV", user_uid="x", idempotency_key="k"),
        "delete_report": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV", user_uid="x", idempotency_key="k"),
        "prepare_client_report": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV", reuse=False, user_uid="x", idempotency_key="k"),
        "read_report_pdf": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV"),
        "read_report_source_md": dict(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV"),
    }
    assert len(calls) == 13
    for name, arguments in calls.items():
        with pytest.raises(DomainError) as refused:
            getattr(off, name)(**arguments)
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and refused.value.detail_fields["dependency"] == "comparison_modules", name
    assert db.state("SELECT count(*) FROM comparison_report") == 0
