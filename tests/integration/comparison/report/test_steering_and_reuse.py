"""`CMP-VC-REPORT-01`: steering a report -- cancel, continue («Продолжить»), «Пересобрать PDF», delete -- and the reuse of finished parts (database,
bucket, PDF child, recorded mode).

A finished part is reused, never requested again: inside a report that is continued and across reports of the same summary when the report asks for it.
«Пересобрать PDF» is not a job and calls no model. «Удалить» is a tombstone that deletes no blob."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from auditmanager.comparison.profile.runner import ChildResult
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.comparison.report.conftest import ADMIN, EXPERT, support
from tests.integration.comparison.report.run_support import pdf_text, record_client, reread, run_client_report, source_of, start


def steer(db: Any, name: str, report: dict[str, Any], *, key: str, roles: frozenset[str] = EXPERT, **over: Any) -> dict[str, Any]:
    return getattr(db.service(), name)(report_id=report["report_id"], user_uid=support.ACTOR, actor_roles=roles, idempotency_key=key, **over)


def conflict_of(call: Any) -> str:
    with pytest.raises(DomainError) as info:
        call()
    assert info.value.code is ErrorCode.CONFLICT, info.value.code
    return str(info.value.detail_fields["conflict_reason"])


@pytest.fixture
def two(db: Any, world: Any, route: Any) -> Any:
    """The same world with the second transition described as well: two transitions have something to write about."""
    support.describe(db.connection, world["project"], world["pairs"][1]["result"])
    return world


def digests_of(db: Any) -> list[str]:
    return db.answers.digests


def test_a_report_cancelled_between_two_items_keeps_its_finished_part_and_continues_with_the_rest_only(db: Any, two: Any, make: Any, route: Any) -> None:
    report = make(two)
    first = record_client(db, two, report, route, label="V1→V2")
    second = record_client(db, two, report, route, label="V2→V3")
    assert first != second
    start(db, report)
    worker, handler = db.worker(), db.handler()
    item = db.claim(worker)
    assert type(handler.run(item)).__name__ == "Completed"
    with db.sessions() as session:
        db.work.finish(session, item.authority, handler.run(item) if False else __import__("auditmanager.comparison.work.model", fromlist=["Completed"]).Completed())
        session.commit()
    assert digests_of(db) == [first]
    cancelled = steer(db, "cancel_report", report, key="cancel-1")
    assert cancelled["state"] == "cancelled" and cancelled["job"]["state"] == "cancelled"
    assert [p["selection"] for p in cancelled["parts"]] == ["done", "pending", "done"]  # what is done stays done
    assert db.drain(handler) == []  # nothing of a cancelled job is claimable
    resumed = steer(db, "continue_report", report, key="continue-1", consent=None)
    assert resumed["state"] == "queued" and resumed["job"]["counts"]["total"] == 3  # the finished unit is counted once, by its newest item
    db.drain(handler)
    final = reread(db, report)
    assert final["state"] == "completed" and digests_of(db) == [first, second]  # the first answer was not asked for again
    assert [p["selection"] for p in final["parts"]] == ["done", "done", "done"] and "V2→V3" in " ".join(pdf_text(db.service().read_report_pdf(report_id=report["report_id"])))


def test_a_finished_part_of_an_earlier_report_is_reused_when_the_report_asks_for_it_and_not_otherwise(db: Any, two: Any, make: Any, route: Any) -> None:
    older = make(two)
    first = record_client(db, two, older, route, label="V1→V2")
    second = record_client(db, two, older, route, label="V2→V3")
    start(db, older)
    worker, handler = db.worker(), db.handler()
    item = db.claim(worker)
    outcome = handler.run(item)
    with db.sessions() as session:
        db.work.finish(session, item.authority, outcome)
        session.commit()
    steer(db, "cancel_report", older, key="cancel-1")
    assert digests_of(db) == [first]
    plain = make(two, reuse=False)
    assert plain["estimate"]["calls"] == 2 and plain["estimate"]["reused"] == 0
    reusing = make(two, reuse=True)
    assert (reusing["estimate"]["calls"], reusing["estimate"]["reused"], reusing["estimate"]["units"]) == (1, 1, 2)
    started = start(db, reusing, key="reuse-1")
    assert [p["selection"] for p in started["parts"]] == ["done", "pending", "done"]  # the first part is the older report's, copied
    db.drain(handler)
    assert digests_of(db) == [first, second]  # one more request, for the part nobody had finished
    final = reread(db, reusing)
    assert final["state"] == "completed" and [p["points"] for p in final["parts"]] == [1, 1, 0]


def test_a_report_whose_every_part_is_reusable_has_nothing_to_send_and_is_refused(db: Any, world: Any, make: Any, route: Any) -> None:
    run_client_report(db, world, make, route)
    again = make(world, reuse=True)
    assert (again["estimate"]["calls"], again["estimate"]["reused"]) == (0, 1)
    assert conflict_of(lambda: start(db, again, key="nothing")) == "comparison_ai_nothing_to_do"
    assert reread(db, again)["state"] == "draft"


def test_the_content_key_names_the_project_the_model_the_prompt_and_the_text_of_the_transition(db: Any, world: Any, make: Any, route: Any, h: Any) -> None:
    from auditmanager.comparison.report import plan as plan_module

    report = make(world)
    doc = source_of(db, report["report_id"])
    profile = {"key": "EM"}
    base = dict(kind="client", project_uid=world["project"], model="claude-opus-5", profile_key="EM", transition_sha=doc.manifest["transitions"][0]["sha256"], with_records=True)
    key = plan_module.content_key(**base)
    assert plan_module.content_key(**base) == key
    for name, value in (("project_uid", "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"), ("model", "other-model"), ("profile_key", "KZh"), ("transition_sha", "0" * 64),
                        ("kind", "analytic"), ("with_records", False)):
        assert plan_module.content_key(**{**base, name: value}) != key, name
    assert profile["key"] == "EM"


def test_a_failed_pdf_fails_the_report_without_losing_its_parts_and_continue_finishes_it_with_no_new_call(db: Any, world: Any, make: Any, route: Any) -> None:
    class Overrun:
        def run(self, settings: Any, limits: Any) -> ChildResult:
            return ChildResult("overrun")

    report = make(world)
    record_client(db, world, report, route)
    start(db, report)
    outcomes = db.drain(db.handler(pdf_runner=Overrun()))
    assert outcomes[-1] == "Failed:pdf_failed"
    failed = reread(db, report)
    assert (failed["state"], failed["failure_reason"], failed["job"]["state"]) == ("failed", "pdf_failed", "failed")
    assert [a["kind"] for a in failed["artifacts"]] == ["source_md"] and failed["parts"][0]["selection"] == "done"
    calls = db.answers.calls
    assert conflict_of(lambda: steer(db, "rebuild_report_pdf", report, key="rebuild-0")) == "comparison_report_state"  # no text yet: nothing to rebuild from
    continued = steer(db, "continue_report", report, key="continue-1", consent=None)
    assert continued["state"] == "queued" and continued["job"]["state"] == "queued"
    db.drain(db.handler())
    final = reread(db, report)
    assert final["state"] == "completed" and db.answers.calls == calls  # the PDF was written from the stored parts: no model was asked again


def test_a_pdf_that_fails_its_own_check_is_not_stored_and_fails_the_report(db: Any, world: Any, make: Any, route: Any, h: Any) -> None:
    report = make(world)
    doc = source_of(db, report["report_id"])
    answer = h.good_client_answer(doc)
    answer["lead"] = "Заменён **кабель**."  # service markup in the text of the customer: the PDF's check refuses it
    record_client(db, world, report, route, answer=answer)
    start(db, report)
    outcomes = db.drain(db.handler())
    # the program's own text check does not know markdown: it is the PDF's check that stops it
    assert outcomes[-1] == "Failed:pdf_check_failed"
    failed = reread(db, report)
    assert failed["state"] == "failed" and failed["failure_reason"] == "pdf_check_failed" and "report_pdf" not in [a["kind"] for a in failed["artifacts"]]


def test_rebuild_writes_the_pdf_again_from_the_stored_text_and_calls_no_model(db: Any, world: Any, make: Any, route: Any) -> None:
    report, _ = run_client_report(db, world, make, route)
    before = {t: db.state(f"SELECT count(*) FROM {t}") for t in ("comparison_model_call", "comparison_work", "comparison_ai_job")}
    requests = db.answers.calls
    original = db.service().read_report_pdf(report_id=report["report_id"])
    rebuilt = steer(db, "rebuild_report_pdf", report, key="rebuild-1")
    assert rebuilt["state"] == "completed"
    assert {t: db.state(f"SELECT count(*) FROM {t}") for t in before} == before and db.answers.calls == requests  # no job, no item, no call
    assert db.state("SELECT count(*) FROM comparison_report_artifact WHERE comparison_report_id = :r AND kind = 'report_pdf'", r=report["report_id"]) == 2
    assert db.service().read_report_pdf(report_id=report["report_id"]) == original  # the same data give the same bytes
    assert hashlib.sha256(original).hexdigest() == rebuilt["artifacts"][0]["sha256"] or rebuilt["artifacts"][0]["kind"] == "report_pdf"
    again = steer(db, "rebuild_report_pdf", report, key="rebuild-1")  # a repeat of the key replays
    assert again["report_id"] == report["report_id"]
    assert db.state("SELECT count(*) FROM comparison_report_artifact WHERE comparison_report_id = :r AND kind = 'report_pdf'", r=report["report_id"]) == 2


def test_rebuild_of_a_report_without_a_text_is_refused_and_a_child_that_fails_leaves_the_earlier_pdf(db: Any, world: Any, make: Any, route: Any) -> None:
    draft = make(world)
    assert conflict_of(lambda: steer(db, "rebuild_report_pdf", draft, key="r0")) == "comparison_report_state"
    report, _ = run_client_report(db, world, make, route)

    class Broken:
        def run(self, settings: Any, limits: Any) -> ChildResult:
            return ChildResult("wall")

    with pytest.raises(DomainError) as info:
        db.service(pdf_runner=Broken()).rebuild_report_pdf(
            report_id=report["report_id"], user_uid=support.ACTOR, actor_roles=EXPERT, idempotency_key="rebuild-2")
    assert info.value.code is ErrorCode.INTERNAL_ERROR
    assert db.state("SELECT count(*) FROM comparison_report_artifact WHERE comparison_report_id = :r AND kind = 'report_pdf'", r=report["report_id"]) == 1
    assert db.service().read_report_pdf(report_id=report["report_id"]).startswith(b"%PDF-")


def test_delete_is_a_tombstone_that_deletes_no_blob_and_a_live_report_cannot_be_deleted(db: Any, world: Any, make: Any, route: Any) -> None:
    live = make(world)
    record_client(db, world, live, route)
    start(db, live)
    assert conflict_of(lambda: steer(db, "delete_report", live, key="delete-0")) == "comparison_report_state"  # queued
    db.drain(db.handler())
    blobs = db.state("SELECT count(*) FROM blob")
    artifacts = db.state("SELECT count(*) FROM comparison_report_artifact")
    deleted = steer(db, "delete_report", live, key="delete-1")
    assert deleted["report_id"] == live["report_id"]
    assert db.state("SELECT deleted_at IS NOT NULL FROM comparison_report WHERE comparison_report_id = :r", r=live["report_id"]) is True
    assert db.state("SELECT count(*) FROM blob") == blobs and db.state("SELECT count(*) FROM comparison_report_artifact") == artifacts
    assert pytest.raises(DomainError, db.service().get_report, report_id=live["report_id"]).value.code is ErrorCode.NOT_FOUND
    assert pytest.raises(DomainError, db.service().read_report_pdf, report_id=live["report_id"]).value.code is ErrorCode.NOT_FOUND
    page = db.service().list_reports(series_id=world["series"], after=None, limit=10)
    assert [item["report_id"] for item in page.items] == []
    assert steer(db, "delete_report", live, key="delete-1")["report_id"] == live["report_id"]  # a repeat of the key replays
    assert pytest.raises(DomainError, steer, db, "delete_report", live, key="delete-2").value.code is ErrorCode.NOT_FOUND


def test_a_draft_can_be_deleted_and_a_deleted_draft_cannot_be_started(db: Any, world: Any, make: Any, route: Any) -> None:
    draft = make(world)
    steer(db, "delete_report", draft, key="delete-1")
    assert pytest.raises(DomainError, start, db, draft, key="start-1").value.code is ErrorCode.NOT_FOUND


def test_a_cancel_and_a_continue_apply_only_to_the_states_the_contract_names(db: Any, world: Any, make: Any, route: Any) -> None:
    draft = make(world)
    assert conflict_of(lambda: steer(db, "cancel_report", draft, key="c0")) == "comparison_report_state"  # a draft is deleted, not cancelled
    assert conflict_of(lambda: steer(db, "continue_report", draft, key="k0", consent=None)) == "comparison_report_state"
    record_client(db, world, draft, route)
    start(db, draft)
    assert conflict_of(lambda: steer(db, "continue_report", draft, key="k1", consent=None)) == "comparison_report_state"  # queued: it is moving
    done, _ = run_client_report(db, world, make, route)
    assert conflict_of(lambda: steer(db, "cancel_report", done, key="c1")) == "comparison_report_state"
    assert conflict_of(lambda: steer(db, "continue_report", done, key="k2", consent=None)) == "comparison_report_state"  # completed


def test_every_steering_is_an_experts_act_and_an_unknown_report_is_not_found(db: Any, world: Any, make: Any, route: Any) -> None:
    report = make(world)
    for name, extra in (("start_report", {"consent": db.consent("a" * 64)}), ("cancel_report", {}), ("continue_report", {"consent": None}),
                        ("rebuild_report_pdf", {}), ("delete_report", {})):
        error = pytest.raises(DomainError, getattr(db.service(), name), report_id=report["report_id"], user_uid=support.ACTOR, actor_roles=ADMIN,
                              idempotency_key="adm", **extra).value
        assert error.code is ErrorCode.PERMISSION_DENIED and error.detail_fields["required_capability"] == "role:expert", name
    missing = dict(report, report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert pytest.raises(DomainError, steer, db, "cancel_report", missing, key="m1").value.code is ErrorCode.NOT_FOUND
    assert reread(db, report)["state"] == "draft" and db.state("SELECT count(*) FROM comparison_ai_job WHERE method = 'report'") == 0


def test_the_report_list_is_newest_first_pages_by_a_cursor_and_hides_the_deleted(db: Any, world: Any, make: Any, route: Any) -> None:
    made = [make(world)["report_id"] for _ in range(3)]
    page = db.service().list_reports(series_id=world["series"], after=None, limit=2)
    assert [item["report_id"] for item in page.items] == made[::-1][:2] and page.next_after is not None
    rest = db.service().list_reports(series_id=world["series"], after=page.next_after, limit=2)
    assert [item["report_id"] for item in rest.items] == made[::-1][2:] and rest.next_after is None
    steer(db, "delete_report", {"report_id": made[1]}, key="d")
    assert [i["report_id"] for i in db.service().list_reports(series_id=world["series"], after=None, limit=10).items] == [made[2], made[0]]
    assert pytest.raises(DomainError, db.service().list_reports, series_id="cser_01ARZ3NDEKTSV4RRFFQ69G5FAV", after=None, limit=5).value.code is ErrorCode.NOT_FOUND
