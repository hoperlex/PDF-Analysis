"""Part B on the AI-job core (`CMP-VC-SPEC-01`, `CMP-AI-JOBS-01`): estimate, keyed start with consent, the lane's handler through the
spend wrapper in recorded mode, and cancel -- real PostgreSQL, the real work queue and spend journal, no provider.

The model is :class:`~auditmanager.comparison.public.RecordedAnswers`: an answer filed under the digest of the request it answers; a
request with no answer is never a call. The oracle is the answer key of the synthetic corpus (V4 to V5: one changed, one added, one
removed position).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.analysis.public import ProviderMode
from auditmanager.comparison.public import AiConsentInput, AiJobCommand, RecordedAnswers, SpecMethod, TransitionRun
from auditmanager.comparison.specification import prompt
from auditmanager.comparison.specification.method import build_request, spec_scope
from auditmanager.comparison.specification.repository import SpecificationRepository
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import faithful_answer, run_items

EXPERT = frozenset({"expert"})


def _command(expert_uid: str, key: str, roles: frozenset[str] = EXPERT, kind: str = "start_comparison_specification") -> AiJobCommand:
    return AiJobCommand(command_type=kind, idempotency_key=key, user_uid=expert_uid, actor_roles=roles)


def _reason(failure: pytest.ExceptionInfo[DomainError]) -> str | None:
    return failure.value.detail_fields.get("conflict_reason")


class World:
    """A started series, its V4 -> V5 transition, the recorded answers a careful model would give, and the service."""

    def __init__(self, started, sessions, blob_store, jobs, expert_uid) -> None:
        self.doc, self.series = started()
        self.sessions, self.jobs, self.expert = sessions, jobs, expert_uid
        repository = SpecificationRepository()
        with session_scope(sessions) as session:
            self.scope = repository.transition(session, next(t["transition_id"] for t in self.series["transitions"] if t["source_version_uid"] == self.doc.versions[1]))
        self.method = SpecMethod(sessions, blob_store)
        self.answers = RecordedAnswers()
        self.job_scope = spec_scope(self.scope.project_uid, self.scope.document_uid, self.scope.transition_id)

    def record_answers(self, forge: Any = None) -> None:
        """File the faithful answer to the request of every side the store does not hold yet."""
        for number, side in enumerate(self.method.prepared(self.scope), start=1):
            if side.sendable:
                request = build_request("claude-opus-5", prompt.prompt_for(side.source), idempotency_scope="x")
                answer = faithful_answer(side.source)
                if forge is not None:
                    answer = forge(answer, number)
                self.answers.record(request, json.dumps(answer, ensure_ascii=False))

    def binder(self, session, job):
        return CallRoute(adapter=self.answers, model_identity=job.pinned_model, connection_revision_id=job.connection_revision_id,
                         expected_model=None, check_identity=False)

    def start(self, key: str = "k1", *, confirmed: bool = True):
        estimate = self.jobs.estimate(self.job_scope)
        return estimate, self.jobs.start(
            scope=self.job_scope, consent=AiConsentInput(estimate_digest=estimate.estimate_digest, confirmed=confirmed),
            command=_command(self.expert, f"{key}-{self.scope.transition_id}"))


@pytest.fixture
def world(started, sessions, blob_store, jobs, expert_uid, route) -> World:
    return World(started, sessions, blob_store, jobs, expert_uid)


def _rows(lab, sql: str, **params: Any) -> list[dict[str, Any]]:
    return lab.rows(sql, **params)


def test_the_estimate_counts_one_request_a_side_that_is_not_stored_and_calls_no_model(world, route) -> None:
    estimate = world.jobs.estimate(world.job_scope)
    document = estimate.as_dict()
    assert document["method"] == "spec" and document["calls"] == 2 and document["reused"] == 0 and document["units"] == 2
    assert document["images"] == 0 and document["image_bytes"] == 0 and document["prompt_chars"] > 0 and document["output_tokens"] > 0
    assert document["route"]["pinned_model"] == "claude-opus-5" and document["versions"] == 2
    assert world.answers.calls == 0


def test_a_start_writes_the_job_the_row_of_the_transition_and_one_item_and_the_handler_does_the_rest(world, lab, runner_of, worker_id, engine) -> None:
    world.record_answers()
    _estimate, job = world.start()
    assert job.record.state == "queued" and job.record.transition_id == world.scope.transition_id
    row = SpecificationRepository()
    with session_scope(world.sessions) as session:
        whole = row.whole(session, world.scope.transition_id)
    assert whole is not None and whole.state == "queued" and whole.job_id == job.record.job_id and (whole.sheets_a, whole.sheets_b) == (1, 1)
    items = _rows(lab, "SELECT kind, state, payload, comparison_ai_job_id FROM comparison_work WHERE comparison_ai_job_id = :j", j=job.record.job_id)
    assert [(i["kind"], i["state"]) for i in items] == [("comparison_spec", "queued")]
    assert items[0]["payload"]["transition_id"] == world.scope.transition_id and items[0]["payload"]["ai_job_id"] == job.record.job_id

    ran = run_items(runner_of(world.binder), worker_id, engine, world.scope.project_uid)
    assert ran == [("comparison_spec", "succeeded")], ran
    assert world.answers.calls == 2

    with session_scope(world.sessions) as session:
        whole = row.whole(session, world.scope.transition_id)
        state = world.jobs.state_of(session, job.record.job_id)
    assert state == "completed" and whole.state == "completed" and whole.totals == {"changed": 1, "added": 1, "removed": 1, "unclear": 0, "renumbered": 0, "moved": 0}
    assert [c["kind"] for c in whole.changes] == ["changed", "removed", "added"] and whole.extraction_a_id and whole.extraction_b_id
    calls = _rows(lab, "SELECT c.state, c.provider_mode, c.cost_basis, c.cost_micros FROM comparison_model_call c "
                       "JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id WHERE w.comparison_ai_job_id = :j", j=job.record.job_id)
    assert len(calls) == 2 and {(c["state"], c["provider_mode"], c["cost_basis"], c["cost_micros"]) for c in calls} == {("completed", "recorded", "unmetered", 0)}


def test_a_stored_reading_is_not_sent_again_and_a_job_with_nothing_to_send_is_refused(world, runner_of, worker_id, engine) -> None:
    world.record_answers()
    world.start()
    run_items(runner_of(world.binder), worker_id, engine, world.scope.project_uid)
    again = world.jobs.estimate(world.job_scope).as_dict()
    assert again["calls"] == 0 and again["reused"] == 2
    with pytest.raises(DomainError) as failure:
        world.start("k2")
    assert _reason(failure) == "comparison_ai_nothing_to_do"


def test_the_consent_is_checked_before_anything_is_written(world, lab) -> None:
    estimate = world.jobs.estimate(world.job_scope)
    with pytest.raises(DomainError) as unconfirmed:
        world.jobs.start(scope=world.job_scope, consent=AiConsentInput(estimate_digest=estimate.estimate_digest, confirmed=False),
                         command=_command(world.expert, "unconfirmed"))
    assert unconfirmed.value.code is ErrorCode.VALIDATION_FAILED and unconfirmed.value.detail_fields["field"] == "consent"
    assert unconfirmed.value.detail_fields["constraint"] == "comparison_consent_required"
    with pytest.raises(DomainError) as stale:
        world.jobs.start(scope=world.job_scope, consent=AiConsentInput(estimate_digest="b" * 64, confirmed=True), command=_command(world.expert, "stale"))
    assert _reason(stale) == "comparison_estimate_stale"
    with pytest.raises(DomainError) as admin:
        world.jobs.start(scope=world.job_scope, consent=AiConsentInput(estimate_digest=estimate.estimate_digest, confirmed=True),
                         command=_command(world.expert, "admin", roles=frozenset({"admin"})))
    assert admin.value.code is ErrorCode.PERMISSION_DENIED
    assert not _rows(lab, "SELECT 1 FROM comparison_spec_comparison WHERE comparison_transition_id = :t", t=world.scope.transition_id)
    assert not _rows(lab, "SELECT 1 FROM comparison_ai_job WHERE comparison_transition_id = :t", t=world.scope.transition_id)


def test_a_repeat_of_the_key_answers_the_first_job_and_a_live_job_holds_the_transition(world) -> None:
    world.record_answers()
    _estimate, first = world.start("same")
    _estimate, replay = world.start("same")
    assert replay.record.job_id == first.record.job_id
    with pytest.raises(DomainError) as failure:
        world.start("other")
    assert _reason(failure) == "comparison_ai_job_active"


def test_a_cancelled_job_sends_nothing_and_its_row_is_cancelled(world, runner_of, worker_id, engine) -> None:
    world.record_answers()
    _estimate, job = world.start()
    world.jobs.cancel(job_id=job.record.job_id, method="spec", command=_command(world.expert, f"cancel-{world.scope.transition_id}", kind="cancel_comparison_specification"))
    from auditmanager.comparison.public import SpecificationService

    SpecificationService(world.sessions, None).close_cancelled(job.record.job_id)
    assert run_items(runner_of(world.binder), worker_id, engine, world.scope.project_uid) == []
    assert world.answers.calls == 0
    with session_scope(world.sessions) as session:
        whole = SpecificationRepository().whole(session, world.scope.transition_id)
    assert whole.state == "cancelled" and whole.changes == [] and whole.totals is None


def test_a_paused_job_sends_nothing(world, runner_of, worker_id, engine) -> None:
    world.record_answers()
    _estimate, job = world.start()
    world.jobs.pause(job_id=job.record.job_id, method="spec", command=_command(world.expert, f"pause-{world.scope.transition_id}", kind="pause_comparison_specification"))
    assert run_items(runner_of(world.binder), worker_id, engine, world.scope.project_uid) == []
    assert world.answers.calls == 0


def test_a_forged_quote_makes_the_comparison_incomplete_and_the_job_still_completes(world, runner_of, worker_id, engine) -> None:
    """The mutation proof of the rule at the job level: the model's reading of the newer version quotes a line that is not in the text; no
    row of that side exists, so the comparison is ``incomplete`` and publishes no addition, removal or "no change"."""
    def forge(answer, number):
        if number == 2:
            answer["blocks"][0]["rows"][2]["evidence"][0]["quote"] = "| 3 | СИНТ-АВ.63 | Выключатель автоматический 63 А | 30 | 0,45 | |"
        return answer

    world.record_answers(forge)
    _estimate, job = world.start()
    run_items(runner_of(world.binder), worker_id, engine, world.scope.project_uid)
    with session_scope(world.sessions) as session:
        whole = SpecificationRepository().whole(session, world.scope.transition_id)
        state = world.jobs.state_of(session, job.record.job_id)
    assert state == "completed" and whole.state == "incomplete" and whole.reason == "SPEC_ANSWER_UNCONFIRMED" and whole.changes == [] and whole.totals is None
    # the unconfirmed answer is kept: the same side is not sent (and not paid for) again
    assert world.jobs.estimate(world.job_scope).as_dict()["calls"] == 0


def test_a_worker_that_cannot_bind_the_route_sends_nothing(world, sessions, blob_store, engine, worker_id) -> None:
    """The shipped binder: the worker's bundle has no key ring, so a live route is not bound here and no request is ever made."""
    from auditmanager.comparison.public import ClaimGates, ComparisonWorkRepository, ComparisonWorkRunner, HandlerRegistry, WorkDependencies, default_gates, spec_handler

    world.record_answers()
    world.start()
    work = ComparisonWorkRepository()
    registry = HandlerRegistry.build((spec_handler,), WorkDependencies(engine=engine, session_factory=sessions, blob_store=blob_store, work=work))
    runner = ComparisonWorkRunner(sessions, registry=registry, modules=frozenset({"versions"}), repository=work,
                                  gates=ClaimGates(paused=default_gates().paused, run_claimable=lambda session: False))
    ran = run_items(runner, worker_id, engine, world.scope.project_uid, limit=1)
    assert ran and ran[0][1] != "succeeded" and world.answers.calls == 0
