"""`CMP-VC-REPORT-01`: the analytic report -- an analyst, a verifier and a composer, each answer checked by the program -- from the start to its PDF,
and «Подготовить отчёт для заказчика» from it (database, bucket, PDF child, recorded mode)."""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.report.model import UNCONFIRMED_LABEL
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.comparison.report.conftest import EXPERT, support
from tests.integration.comparison.report.run_support import pdf_text, record_analytic, record_client, record_composer_retry, reread, start


def run_analytic(db: Any, world: Any, make: Any, route: Any, **record: Any) -> dict[str, Any]:
    report = make(world, "analytic")
    record_analytic(db, report, route, **record)
    start(db, report)
    db.drain(db.handler())
    return report


def test_an_analytic_report_runs_analyst_verifier_and_composer_to_a_pdf(db: Any, world: Any, make: Any, route: Any) -> None:
    report = run_analytic(db, world, make, route)
    final = reread(db, report)
    assert (final["state"], final["stage"], final["job"]["state"]) == ("completed", "pdf_writing", "completed")
    assert db.answers.calls == 3 * 2 + 1  # an analyst and a verifier for each of three transitions, then one composer
    assert [(p["analysis"], p["verification"]) for p in final["parts"]] == [("done", "done")] * 3
    first = final["parts"][0]
    assert first["facts"] == {"found": 2, "confirmed": 2, "contradicted": 0, "unconfirmed": 0} and first["warnings"] == 0  # the assessment and the fact ...
    assert final["parts"][1]["facts"]["found"] == 1  # ... the assessment alone for a transition with no fact
    text = " ".join(pdf_text(db.service().read_report_pdf(report_id=report["report_id"]))).replace("\n", " ")
    assert "Как менялась документация" in text and "Реестр источников" in text and "Замена кабеля" in text
    assert UNCONFIRMED_LABEL.replace(" ", "") in text.replace(" ", "")
    assert db.state("SELECT count(*) FROM comparison_report_artifact WHERE comparison_report_id = :r AND kind = 'report_text'", r=report["report_id"]) == 1


def test_the_composer_is_asked_again_with_the_programs_remarks_and_a_number_no_fact_holds_is_printed_as_unconfirmed(db: Any, world: Any, make: Any, route: Any) -> None:
    bad = {"significant_changes": [{"priority": "P2", "title": "Замена кабеля", "version_range": "V1→V2", "before_after": "3×2,5 → 3×16",
                                    "consequence": "потребуется проверка", "claim_ids": ["G01.T01.F1"], "fact_ids": ["Ф0002"]}]}
    report = make(world, "analytic")
    verified, answer = record_analytic(db, report, route, composer=bad)
    start(db, report)
    outcomes = db.drain(db.handler())
    assert outcomes[-1] == "Failed:analysis_input_invalid"  # the first answer failed the check, so a second request was made: nobody recorded it
    assert db.answers.calls == 6 + 1 + 1
    record_composer_retry(db, report, route, verified, answer)
    steered = db.service().continue_report(report_id=report["report_id"], consent=None, user_uid=support.ACTOR, actor_roles=EXPERT, idempotency_key="k1")
    assert steered["state"] == "queued"
    db.drain(db.handler())
    final = reread(db, report)
    assert final["state"] == "completed"  # only fixable remarks were left after the last attempt: accepted with warnings, as the original does
    text = " ".join(pdf_text(db.service().read_report_pdf(report_id=report["report_id"]))).replace("\n", " ")
    assert "Проверка программы не подтвердила" in text and "16" in text  # the number is there, and so is the program's word that nothing confirms it


def test_a_verifier_that_gives_no_fit_answer_leaves_a_failed_part_and_a_partial_report(db: Any, world: Any, make: Any, route: Any) -> None:
    report = make(world, "analytic")
    record_analytic(db, report, route, skip_verifier=("T02",))
    start(db, report)
    db.drain(db.handler())
    final = reread(db, report)
    assert final["state"] == "partial" and [p["verification"] for p in final["parts"]] == ["done", "failed", "done"]
    assert final["parts"][1]["analysis"] == "done"  # the analyst's answer of that transition is kept: a continue goes on with the verifier
    assert [a["kind"] for a in final["artifacts"]] == ["source_md"]
    requests = db.answers.calls
    record_analytic(db, report, route)  # the missing verifier answer is recorded now
    steer = db.service().continue_report(report_id=report["report_id"], consent=None, user_uid=support.ACTOR, actor_roles=EXPERT, idempotency_key="continue-1")
    assert steer["state"] == "queued"
    db.drain(db.handler())
    done = reread(db, report)
    assert done["state"] == "completed" and [p["verification"] for p in done["parts"]] == ["done"] * 3
    # the two finished transitions were not asked again (3 earlier verifier/analyst pairs minus the one unfinished): analyst of T02 is not repeated
    assert db.answers.calls - requests == 2  # the verifier of T02 and the composer


def test_a_client_report_is_prepared_from_a_finished_analytic_one_and_reads_its_verified_scale(db: Any, world: Any, make: Any, route: Any) -> None:
    analytic_report = run_analytic(db, world, make, route)
    before = db.answers.calls
    prepared = db.service().prepare_client_report(
        report_id=analytic_report["report_id"], reuse=False, user_uid=support.ACTOR, actor_label="Эксперт", actor_roles=EXPERT, idempotency_key="prep-1")
    assert (prepared["kind"], prepared["state"], prepared["prepared_from_id"]) == ("client", "draft", analytic_report["report_id"])
    assert prepared["source"] == "series_summary" and prepared["estimate"]["calls"] == 1  # only the transition with something to write about
    assert db.answers.calls == before  # no model is called by the preparation
    again = db.service().prepare_client_report(
        report_id=analytic_report["report_id"], reuse=False, user_uid=support.ACTOR, actor_label="Эксперт", actor_roles=EXPERT, idempotency_key="prep-1")
    assert again["report_id"] == prepared["report_id"]
    record_client(db, world, prepared, route)
    start(db, prepared, key="start-prepared")
    db.drain(db.handler())
    done = reread(db, prepared)
    assert done["state"] == "completed" and done["prepared_from_id"] == analytic_report["report_id"]
    assert "Изменения проектных решений" in " ".join(pdf_text(db.service().read_report_pdf(report_id=prepared["report_id"])))


def test_a_client_report_cannot_be_prepared_from_a_draft_a_client_report_or_an_unfinished_one(db: Any, world: Any, make: Any, route: Any) -> None:
    draft = make(world, "analytic")
    client_draft = make(world, "client")
    for report in (draft, client_draft):
        error = pytest.raises(DomainError, db.service().prepare_client_report, report_id=report["report_id"], reuse=False, user_uid=support.ACTOR,
                              actor_label="Э", actor_roles=EXPERT, idempotency_key="p-" + report["kind"]).value
        assert error.code is ErrorCode.CONFLICT and error.detail_fields["conflict_reason"] == "comparison_report_state"
    assert db.state("SELECT count(*) FROM comparison_report") == 2
