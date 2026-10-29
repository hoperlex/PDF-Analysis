"""Helpers of the report lane's run tests: start a report, ask which request the handler will make and record its answer by digest."""

from __future__ import annotations

import io
import json
from typing import Any

from pypdf import PdfReader

from auditmanager.comparison.report import analytic, plan as plan_module
from auditmanager.comparison.report.model import UNCONFIRMED_LABEL
from auditmanager.comparison.report.repository import ReportRepository
from tests.integration.comparison.report.conftest import EXPERT, support


def start(db: Any, report: dict[str, Any], *, key: str = "start-1", service: Any = None, digest: str | None = None) -> dict[str, Any]:
    return (service or db.service()).start_report(
        report_id=report["report_id"], consent=db.consent(digest or report["estimate"]["estimate_digest"]), user_uid=support.ACTOR,
        actor_roles=EXPERT, idempotency_key=key,
    )


def source_of(db: Any, report_id: str) -> Any:
    with db.sessions() as session:
        row = ReportRepository().get(session, report_id)
        assert row is not None
        return db.service().source_doc(session, row)


def record_client(db: Any, world: dict[str, Any], report: dict[str, Any], route: Any, *, label: str = "V1→V2", answer: dict[str, Any] | None = None) -> str:
    """Record the answer to the request the handler will make for the client kind's transition ``label``; answers its digest."""
    doc = source_of(db, report["report_id"])
    request, *_ = support.client_request(doc, label, route.pinned_model, world["project"])
    return db.answers.record(request, json.dumps(answer or support.good_client_answer(doc, label), ensure_ascii=False))


def pdf_text(content: bytes) -> list[str]:
    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages]


def reread(db: Any, report: dict[str, Any]) -> dict[str, Any]:
    return db.service().get_report(report_id=report["report_id"])


def run_client_report(db: Any, world: dict[str, Any], make: Any, route: Any, *, answer: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """A client report started and run to its end with one good answer for the transition that has a description."""
    report = make(world)
    record_client(db, world, report, route, answer=answer)
    started = start(db, report)
    db.drain(db.handler())
    return report, started


__all__ = ["UNCONFIRMED_LABEL", "analytic", "pdf_text", "plan_module", "reread", "record_client", "run_client_report", "source_of", "start"]
