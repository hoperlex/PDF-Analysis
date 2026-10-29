"""`CMP-AI-JOBS-01`: the keyed start with consent -- the module flag, the stale digest, both ceilings, one live job per scope,
nothing to do, the job row, the work items and their link to the job. Real PostgreSQL; each rule shown failing."""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.public import (
    AiCallGroup,
    AiCounts,
    AiEstimate,
    AiMode,
    ComparisonSpendRepository,
)
from auditmanager.comparison.spend.model import DAY_CEILING_MICROS, JOB_CEILING_MICROS, Spend
from auditmanager.shared.errors import DomainError, ErrorCode

KIND = {"pair_check": "start_comparison_ai_pair_check", "sheet_changes": "start_comparison_ai_sheet_changes",
        "spec": "start_comparison_specification", "report": "start_comparison_report"}


def tables(db: Any) -> dict[str, int]:
    return {name: db.state(f"SELECT count(*) FROM {name}") for name in ("comparison_ai_job", "comparison_work", "command_record")}


@pytest.fixture
def pair_world(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> Any:
    from types import SimpleNamespace

    route = h.recorded_route(db.connection, "comparison_pair_check")
    method = h.FakeMethod(method="pair_check")
    service = db.service(method)
    return SimpleNamespace(route=route, method=method, service=service, scope=scope_of("pair_check"), world=world)


def test_a_start_writes_the_job_and_its_linked_work_items_in_one_transaction(db: Any, h: Any, pair_world: Any) -> None:
    w = pair_world
    digest = w.service.estimate(w.scope).estimate_digest
    view = w.service.start(scope=w.scope, consent=db.consent(digest), command=db.command())
    job = view.record
    assert (job.state, job.method, job.consent_no, job.estimate_digest) == ("queued", "pair_check", 1, digest)
    assert (job.connection_revision_id, job.pinned_model, job.provider_mode) == (w.route.revision_id, h.MODEL, "recorded")
    assert job.estimate["estimate_digest"] == digest and job.estimate_micros == 490_000 and job.ceiling_micros == JOB_CEILING_MICROS
    assert job.consented_by_user_uid == h.ACTOR and job.matrix_id == w.world["build"]
    items = db.rows(
        "SELECT comparison_work_id, kind, state, module, payload, comparison_ai_job_id, dedupe_key FROM comparison_work "
        "WHERE comparison_ai_job_id = :j ORDER BY dedupe_key", j=job.job_id)
    assert [i["dedupe_key"] for i in items] == [f"{job.job_id}:u0", f"{job.job_id}:u1", f"{job.job_id}:u2"]
    for item in items:
        assert item["kind"] == "comparison_pair_check" and item["module"] == "versions" and item["state"] == "queued"
        assert item["payload"]["ai_job_id"] == job.job_id and item["comparison_ai_job_id"] == job.job_id
    assert view.progress.total == 3 and view.progress.done == 0 and view.queue_position >= 1
    assert view.spend.calls == 0 and view.spend.spent_micros == 0


def test_the_hook_sees_the_job_row_that_exists_in_the_state_it_will_be_in(db: Any, h: Any, pair_world: Any) -> None:
    db_view = db.start(pair_world.service, pair_world.scope)
    (seen,) = pair_world.method.seen_jobs
    assert seen.job_id == db_view.record.job_id and seen.state == "queued"


def test_progress_and_spend_are_read_through_the_link_and_not_through_the_payload(db: Any, h: Any, pair_world: Any) -> None:
    """An item that carries ``ai_job_id`` in its payload and not the column is not the job's for its progress: the link is what
    the reads go through, which is why a start writes the item with it."""
    view = db.start(pair_world.service, pair_world.scope)
    job_id = view.record.job_id
    with db.sessions() as session:
        db.work.enqueue(session, project_uid=pair_world.world["project"], module="versions", kind="comparison_pair_check",
                        payload={"ai_job_id": job_id}, dedupe_key="unlinked")
        session.commit()
    assert pair_world.service.view(job_id).progress.total == 3


def test_the_module_flag_refuses_every_command_before_anything_is_read_or_written(db: Any, h: Any, pair_world: Any) -> None:
    service = db.service(pair_world.method, modules="none")
    before = tables(db)
    digest = pair_world.service.estimate(pair_world.scope).estimate_digest
    with pytest.raises(DomainError) as refused:
        service.start(scope=pair_world.scope, consent=db.consent(digest), command=db.command())
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.value.detail_fields["dependency"] == "comparison_modules"
    with pytest.raises(DomainError) as estimate_refused:
        service.estimate(pair_world.scope)
    assert estimate_refused.value.detail_fields["dependency"] == "comparison_modules"
    assert tables(db) == before
    assert pair_world.method.seen_jobs == []


def test_a_start_by_an_administrator_alone_is_refused(db: Any, h: Any, pair_world: Any) -> None:
    digest = pair_world.service.estimate(pair_world.scope).estimate_digest
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(digest), command=db.command(roles=frozenset({"admin"})))
    assert refused.value.code is ErrorCode.PERMISSION_DENIED


def test_an_unconfirmed_consent_is_a_validation_error_and_writes_nothing(db: Any, h: Any, pair_world: Any) -> None:
    digest = pair_world.service.estimate(pair_world.scope).estimate_digest
    before = tables(db)
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(digest, confirmed=False), command=db.command())
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(refused.value.detail_fields) == {"field": "consent", "constraint": "comparison_consent_required"}
    assert tables(db) == before


def test_a_digest_that_is_not_the_estimate_now_is_stale_and_writes_nothing(db: Any, h: Any, pair_world: Any) -> None:
    shown = pair_world.service.estimate(pair_world.scope).estimate_digest
    before = tables(db)
    pair_world.method.counts_default = h.counts_for(11)  # the work changed since the estimate was shown
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(shown), command=db.command())
    assert h.conflict_reason(refused) == "comparison_estimate_stale"
    assert tables(db) == before


def test_a_new_revision_of_the_routed_connection_makes_a_consent_to_the_old_estimate_stale(db: Any, h: Any, pair_world: Any) -> None:
    shown = pair_world.service.estimate(pair_world.scope).estimate_digest
    h.new_revision(db.connection, pair_world.route)
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(shown), command=db.command())
    assert h.conflict_reason(refused) == "comparison_estimate_stale"


def test_nothing_to_send_is_nothing_to_do(db: Any, h: Any, pair_world: Any) -> None:
    pair_world.method.counts_default = AiCounts(groups=(), units=4, reused=4)  # every unit has a stored answer
    before = tables(db)
    digest = pair_world.service.estimate(pair_world.scope).estimate_digest
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(digest), command=db.command())
    assert h.conflict_reason(refused) == "comparison_ai_nothing_to_do"
    assert tables(db) == before


def test_a_method_that_supplies_no_work_item_is_nothing_to_do_and_leaves_no_job(db: Any, h: Any, pair_world: Any) -> None:
    pair_world.method.units[AiMode.START] = []
    before = tables(db)
    digest = pair_world.service.estimate(pair_world.scope).estimate_digest
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(digest), command=db.command())
    assert h.conflict_reason(refused) == "comparison_ai_nothing_to_do"
    assert tables(db) == before


def test_an_estimate_over_the_job_ceiling_is_refused(db: Any, h: Any, pair_world: Any) -> None:
    pair_world.method.counts_default = h.counts_for(250)  # 250 x USD 0.049 = USD 12.25
    shown = pair_world.service.estimate(pair_world.scope)
    assert shown.estimate_micros == 12_250_000 and shown.blocked_by == "job"
    before = tables(db)
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(shown.estimate_digest), command=db.command())
    assert h.conflict_reason(refused) == "comparison_ceiling_job"
    assert tables(db) == before


def test_an_estimate_that_reaches_the_job_ceiling_exactly_is_allowed(db: Any, h: Any, pair_world: Any) -> None:
    # 6 400 000 input tokens at USD 5 per million is USD 32; pick figures that land on exactly USD 10: 1 call of
    # 2 000 000 input tokens (USD 10.00) and no output.
    pair_world.method.counts_default = AiCounts(
        groups=(AiCallGroup(calls=1, prompt_chars=5_000_000, output_tokens=0, prompt_tokens=2_000_000),), units=1)
    shown = pair_world.service.estimate(pair_world.scope)
    assert shown.estimate_micros == JOB_CEILING_MICROS and shown.blocked_by is None
    assert db.start(pair_world.service, pair_world.scope).record.estimate_micros == JOB_CEILING_MICROS


def test_an_estimate_over_the_day_ceiling_is_refused_and_one_that_reaches_it_is_not(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> None:
    class Day(ComparisonSpendRepository):
        committed = 0

        def day_spend(self, session: Any) -> Spend:  # what the installation has spent or reserved today
            return Spend(actual_micros=self.committed, reserved_micros=0)

    h.recorded_route(db.connection, "comparison_pair_check")
    method = h.FakeMethod(method="pair_check")
    day = Day()
    service = db.service(method, spend=day)
    scope = scope_of("pair_check")
    estimate = service.estimate(scope).estimate_micros
    day.committed = DAY_CEILING_MICROS - estimate  # the estimate reaches the ceiling exactly
    shown = service.estimate(scope)
    assert shown.blocked_by is None and shown.day_remaining_micros == estimate
    day.committed = DAY_CEILING_MICROS - estimate + 1  # one micro-dollar over
    over = service.estimate(scope)
    assert over.blocked_by == "day" and over.day_remaining_micros == estimate - 1
    assert over.estimate_digest == shown.estimate_digest  # the day is not in the digest
    before = tables(db)
    with pytest.raises(DomainError) as refused:
        service.start(scope=scope, consent=db.consent(over.estimate_digest), command=db.command())
    assert h.conflict_reason(refused) == "comparison_ceiling_day"
    assert tables(db) == before
    day.committed = DAY_CEILING_MICROS - estimate
    service.start(scope=scope, consent=db.consent(shown.estimate_digest), command=db.command())


def test_a_connection_that_is_not_metered_has_no_money_and_no_ceiling(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> None:
    h.recorded_route(db.connection, "comparison_pair_check", billing="not_metered")
    method = h.FakeMethod(method="pair_check", counts_default=h.counts_for(5000))
    service = db.service(method)
    scope = scope_of("pair_check")
    shown = service.estimate(scope)
    assert (shown.estimate_micros, shown.ceiling_micros, shown.blocked_by, shown.day_remaining_micros) == (0, 0, None, None)
    view = db.start(service, scope)
    assert view.record.estimate_micros == 0 and view.record.ceiling_micros == 0
    consent = service.consent_for_calls(db.sessions(), view.record.job_id)
    assert consent.estimate_usd == 0 and consent.ceiling_usd == 10


def test_a_second_live_job_on_the_scope_is_refused_and_a_finished_one_makes_room(db: Any, h: Any, pair_world: Any) -> None:
    first = db.start(pair_world.service, pair_world.scope)
    before = tables(db)
    digest = pair_world.service.estimate(pair_world.scope).estimate_digest
    with pytest.raises(DomainError) as refused:
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(digest), command=db.command())
    assert h.conflict_reason(refused) == "comparison_ai_job_active"
    assert tables(db) == before
    pair_world.service.cancel(job_id=first.record.job_id, method="pair_check", command=db.command("cancel_comparison_ai_pair_check"))
    again = db.start(pair_world.service, pair_world.scope)
    assert again.record.job_id != first.record.job_id


def test_the_database_index_holds_the_scope_when_the_look_before_insert_is_lost(db: Any, h: Any, pair_world: Any) -> None:
    """The race of two starts: the first one is not visible to the second's look, so the insert meets the unique index."""
    db.start(pair_world.service, pair_world.scope)
    service = pair_world.service
    lost = type(service._repo).live_on_scope
    type(service._repo).live_on_scope = lambda self, session, scope: None  # type: ignore[method-assign]
    try:
        digest = service.estimate(pair_world.scope).estimate_digest
        with pytest.raises(DomainError) as refused:
            service.start(scope=pair_world.scope, consent=db.consent(digest), command=db.command())
    finally:
        type(service._repo).live_on_scope = lost  # type: ignore[method-assign]
    assert h.conflict_reason(refused) == "comparison_ai_job_active"


@pytest.mark.parametrize("method", ["pair_check", "sheet_changes", "spec"])
def test_every_method_holds_its_own_scope(db: Any, h: Any, world: dict[str, Any], scope_of: Any, method: str) -> None:
    h.recorded_route(db.connection, f"comparison_{method}")
    service = db.service(h.FakeMethod(method=method))
    scope = scope_of(method)
    db.start(service, scope, command=db.command(KIND[method]))
    digest = service.estimate(scope).estimate_digest
    with pytest.raises(DomainError) as refused:
        service.start(scope=scope, consent=db.consent(digest), command=db.command(KIND[method]))
    assert h.conflict_reason(refused) == "comparison_ai_job_active"


def test_a_series_run_and_a_single_sheet_run_are_two_scopes_and_a_report_holds_none(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> None:
    h.recorded_route(db.connection, "comparison_sheet_changes")
    h.recorded_route(db.connection, "comparison_report")
    sheets = db.service(h.FakeMethod(method="sheet_changes"))
    db.start(sheets, scope_of("sheet_changes"), command=db.command(KIND["sheet_changes"]))
    db.start(sheets, scope_of("sheet_changes", pair=True), command=db.command(KIND["sheet_changes"]))  # another scope
    reports = db.service(h.FakeMethod(method="report"))
    db.start(reports, scope_of("report"), command=db.command(KIND["report"]))
    db.start(reports, scope_of("report"), command=db.command(KIND["report"]))  # a series has several reports


def test_a_repeat_of_the_same_key_and_payload_replays_the_job_and_another_payload_is_refused(db: Any, h: Any, pair_world: Any) -> None:
    w = pair_world
    digest = w.service.estimate(w.scope).estimate_digest
    command = db.command(key="one-key-for-two-calls")
    first = w.service.start(scope=w.scope, consent=db.consent(digest), command=command)
    before = tables(db)
    second = w.service.start(scope=w.scope, consent=db.consent(digest), command=command)
    assert second.record.job_id == first.record.job_id and tables(db) == before
    w.method.counts_default = h.counts_for(11)
    with pytest.raises(DomainError) as reused:
        w.service.start(scope=w.scope, consent=db.consent(w.service.estimate(w.scope).estimate_digest), command=command)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_the_unit_of_a_start_is_all_or_nothing(db: Any, h: Any, pair_world: Any) -> None:
    """A method that fails after the job row was written leaves neither the job nor the key behind."""
    def broken(session: Any, job: Any, mode: Any) -> list[Any]:
        raise RuntimeError("the method failed")

    pair_world.method.work_items = broken  # type: ignore[method-assign]
    before = tables(db)
    digest = pair_world.service.estimate(pair_world.scope).estimate_digest
    with pytest.raises(RuntimeError):
        pair_world.service.start(scope=pair_world.scope, consent=db.consent(digest), command=db.command())
    assert tables(db) == before


def test_a_route_that_is_not_there_is_dependency_unavailable(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> None:
    from auditmanager.comparison.public import AiRoute

    def missing(session: Any, work_kind: str, provider_mode: str) -> AiRoute:
        from auditmanager.comparison.public import ai_route_missing

        raise ai_route_missing()

    service = db.service(h.FakeMethod(method="pair_check"), route_reader=missing)
    with pytest.raises(DomainError) as refused:
        service.estimate(scope_of("pair_check"))
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.value.detail_fields["dependency"] == "executor_route_missing"


def test_the_default_route_reader_prices_the_routed_connection_of_the_work_kind(db: Any, h: Any, world: dict[str, Any], scope_of: Any) -> None:
    route = h.recorded_route(db.connection, "comparison_spec")
    service = db.service(h.FakeMethod(method="spec"))
    estimate: AiEstimate = service.estimate(scope_of("spec"))
    assert estimate.route.connection_id == route.connection_id and estimate.route.revision_id == route.revision_id
    assert estimate.route.pinned_model == h.MODEL and estimate.route.billing == "metered"
    assert estimate.route.provider_mode == "recorded"
    document = estimate.as_dict()
    assert document["route"] == {"connection_id": route.connection_id, "revision_id": route.revision_id,
                                 "pinned_model": h.MODEL, "billing": "metered", "provider_mode": "recorded"}
    assert document["estimate_micros"] == 490_000 and document["calls"] == 10 and document["images"] == 20
    assert document["input_tokens"] == 48_000 and document["output_tokens"] == 10_000
    # a second route for the kind (the latest wins) moves the digest
    h.recorded_route(db.connection, "comparison_spec")
    assert service.estimate(scope_of("spec")).estimate_digest != estimate.estimate_digest
