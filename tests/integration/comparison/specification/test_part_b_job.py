"""Part B on the AI-job core (`CMP-VC-SPEC-01`, `CMP-AI-JOBS-01`): estimate, keyed start with consent, the lane's handler through the
spend wrapper in recorded mode, and cancel -- real PostgreSQL, the real work queue and spend journal, no provider.

Every test runs inside a transaction that is rolled back at its end (``iso``): a recorded request is journalled in the append-only
``comparison_model_call``, and a journalled call would stay in the lane database for the spend suite to find. The series and its
transitions are committed (the ``started`` fixture); the job, its item, the route, the journal and the extractions are the test's own.

The model is :class:`~auditmanager.comparison.public.RecordedAnswers`: an answer filed under the digest of the request it answers; a
request with no answer is never a call. The oracle is the answer key of the synthetic corpus (V4 to V5: one changed, one added, one
removed position).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import AiConsentInput, AiJobCommand, RecordedAnswers, SpecificationService, SpecMethod
from auditmanager.comparison.specification import prompt
from auditmanager.comparison.specification.method import build_request, spec_scope
from auditmanager.comparison.specification.repository import SpecificationRepository
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.comparison.work.model import Completed, Failed, Yielded
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import faithful_answer

EXPERT = frozenset({"expert"})


def _command(expert_uid: str, key: str, roles: frozenset[str] = EXPERT, kind: str = "start_comparison_specification") -> AiJobCommand:
    return AiJobCommand(command_type=kind, idempotency_key=key, user_uid=expert_uid, actor_roles=roles)


def _reason(failure: pytest.ExceptionInfo[DomainError]) -> str | None:
    return failure.value.detail_fields.get("conflict_reason")


class World:
    """A started series, its V4 -> V5 transition, the recorded answers a careful model would give, and the service."""

    def __init__(self, started, iso, blob_store, jobs, expert_uid) -> None:
        self.doc, self.series = started()
        self.sessions, self.jobs, self.expert = iso, jobs, expert_uid
        repository = SpecificationRepository()
        with session_scope(iso) as session:
            self.scope = repository.transition(session, next(t["transition_id"] for t in self.series["transitions"] if t["source_version_uid"] == self.doc.versions[1]))
        self.method = SpecMethod(iso, blob_store)
        self.answers = RecordedAnswers()
        self.job_scope = spec_scope(self.scope.project_uid, self.scope.document_uid, self.scope.transition_id)
        self.repository = repository

    def rows(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        with self.sessions() as session:
            return [dict(r) for r in session.execute(text(sql), params).mappings()]

    def whole(self):
        with session_scope(self.sessions) as session:
            return self.repository.whole(session, self.scope.transition_id)

    def state_of(self, job_id: str) -> str:
        with session_scope(self.sessions) as session:
            return self.jobs.state_of(session, job_id)

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
def world(started, iso, blob_store, jobs, expert_uid, route) -> World:
    return World(started, iso, blob_store, jobs, expert_uid)


def test_the_estimate_counts_one_request_a_side_that_is_not_stored_and_calls_no_model(world) -> None:
    document = world.jobs.estimate(world.job_scope).as_dict()
    assert document["method"] == "spec" and document["calls"] == 2 and document["reused"] == 0 and document["units"] == 2
    assert document["images"] == 0 and document["image_bytes"] == 0 and document["prompt_chars"] > 0 and document["output_tokens"] > 0
    assert document["route"]["pinned_model"] == "claude-opus-5" and document["versions"] == 2
    assert world.answers.calls == 0


def test_a_start_writes_the_job_the_row_of_the_transition_and_one_item_and_the_handler_does_the_rest(world, harness_of, worker_id) -> None:
    world.record_answers()
    _estimate, job = world.start()
    assert job.record.state == "queued" and job.record.transition_id == world.scope.transition_id
    whole = world.whole()
    assert whole is not None and whole.state == "queued" and whole.job_id == job.record.job_id and (whole.sheets_a, whole.sheets_b) == (1, 1)
    items = world.rows("SELECT kind, state, payload, comparison_ai_job_id FROM comparison_work WHERE comparison_ai_job_id = :j", j=job.record.job_id)
    assert [(i["kind"], i["state"]) for i in items] == [("comparison_spec", "queued")]
    assert items[0]["payload"]["transition_id"] == world.scope.transition_id and items[0]["payload"]["ai_job_id"] == job.record.job_id

    outcome = harness_of(world.binder).run_next(worker_id, world.scope.project_uid)
    assert isinstance(outcome, Completed), outcome
    assert world.answers.calls == 2

    whole = world.whole()
    assert world.state_of(job.record.job_id) == "completed" and whole.state == "completed"
    assert whole.totals == {"changed": 1, "added": 1, "removed": 1, "unclear": 0, "renumbered": 0, "moved": 0}
    assert [c["kind"] for c in whole.changes] == ["changed", "removed", "added"] and whole.extraction_a_id and whole.extraction_b_id
    calls = world.rows("SELECT c.state, c.provider_mode, c.cost_basis, c.cost_micros FROM comparison_model_call c "
                       "JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id WHERE w.comparison_ai_job_id = :j", j=job.record.job_id)
    assert len(calls) == 2 and {(c["state"], c["provider_mode"], c["cost_basis"], c["cost_micros"]) for c in calls} == {("completed", "recorded", "unmetered", 0)}


def test_a_stored_reading_is_not_sent_again_and_a_job_with_nothing_to_send_is_refused(world, harness_of, worker_id) -> None:
    world.record_answers()
    world.start()
    harness_of(world.binder).run_next(worker_id, world.scope.project_uid)
    again = world.jobs.estimate(world.job_scope).as_dict()
    assert again["calls"] == 0 and again["reused"] == 2
    with pytest.raises(DomainError) as failure:
        world.start("k2")
    assert _reason(failure) == "comparison_ai_nothing_to_do"


def test_the_consent_is_checked_before_anything_is_written(world) -> None:
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
    assert not world.rows("SELECT 1 FROM comparison_spec_comparison WHERE comparison_transition_id = :t", t=world.scope.transition_id)
    assert not world.rows("SELECT 1 FROM comparison_ai_job WHERE comparison_transition_id = :t", t=world.scope.transition_id)


def test_a_repeat_of_the_key_answers_the_first_job_and_a_live_job_holds_the_transition(world) -> None:
    world.record_answers()
    _estimate, first = world.start("same")
    _estimate, replay = world.start("same")
    assert replay.record.job_id == first.record.job_id
    with pytest.raises(DomainError) as failure:
        world.start("other")
    assert _reason(failure) == "comparison_ai_job_active"


def test_a_cancelled_job_sends_nothing_and_its_row_is_cancelled(world, harness_of, worker_id) -> None:
    world.record_answers()
    _estimate, job = world.start()
    world.jobs.cancel(job_id=job.record.job_id, method="spec", command=_command(world.expert, f"cancel-{world.scope.transition_id}", kind="cancel_comparison_specification"))
    SpecificationService(world.sessions, None).close_cancelled(job.record.job_id)
    assert harness_of(world.binder).run_next(worker_id, world.scope.project_uid) is None
    assert world.answers.calls == 0
    whole = world.whole()
    assert whole.state == "cancelled" and whole.changes == [] and whole.totals is None


def test_a_paused_job_sends_nothing(world, harness_of, worker_id) -> None:
    world.record_answers()
    _estimate, job = world.start()
    world.jobs.pause(job_id=job.record.job_id, method="spec", command=_command(world.expert, f"pause-{world.scope.transition_id}", kind="pause_comparison_specification"))
    assert harness_of(world.binder).run_next(worker_id, world.scope.project_uid) is None
    assert world.answers.calls == 0


def test_a_job_paused_after_the_item_was_claimed_sends_nothing(world, harness_of, worker_id) -> None:
    """The mutation proof of the guard at the door: the item is claimed, the job is paused before the handler starts, and the handler
    gives the item back without a request."""
    world.record_answers()
    _estimate, job = world.start()
    harness = harness_of(world.binder)
    item = harness.claim(worker_id, world.scope.project_uid)
    world.jobs.pause(job_id=job.record.job_id, method="spec", command=_command(world.expert, f"pause2-{world.scope.transition_id}", kind="pause_comparison_specification"))
    outcome = harness.handler.run(item)
    assert isinstance(outcome, Yielded) and world.answers.calls == 0


def test_a_forged_quote_makes_the_comparison_incomplete_and_the_job_still_completes(world, harness_of, worker_id) -> None:
    """The mutation proof of the rule at the job level: the model's reading of the newer version quotes a line that is not in the text; no
    row of that side exists, so the comparison is ``incomplete`` and publishes no addition, removal or "no change"."""
    def forge(answer, number):
        if number == 2:
            answer["blocks"][0]["rows"][2]["evidence"][0]["quote"] = "| 3 | СИНТ-АВ.63 | Выключатель автоматический 63 А | 30 | 0,45 | |"
        return answer

    world.record_answers(forge)
    _estimate, job = world.start()
    harness_of(world.binder).run_next(worker_id, world.scope.project_uid)
    whole = world.whole()
    assert world.state_of(job.record.job_id) == "completed" and whole.state == "incomplete"
    assert whole.reason == "SPEC_ANSWER_UNCONFIRMED" and whole.changes == [] and whole.totals is None
    # the unconfirmed answer is kept: the same side is not sent (and not paid for) again
    assert world.jobs.estimate(world.job_scope).as_dict()["calls"] == 0


def test_a_worker_that_cannot_bind_the_route_sends_nothing(world, harness_of, worker_id) -> None:
    """The shipped binder: the worker's bundle has no key ring, so a live route is not bound here and no request is ever made."""
    world.record_answers()
    world.start()
    outcome = harness_of(None, shipped=True).run_next(worker_id, world.scope.project_uid)
    assert isinstance(outcome, Failed) and outcome.retry and world.answers.calls == 0


class _CancelsDuringTheSecondRequest(RecordedAnswers):
    """A recorded model during whose second request the expert cancels the job."""

    def __init__(self, on_second: Any) -> None:
        super().__init__()
        self._on_second = on_second

    def complete(self, request):
        response = super().complete(request)
        if self.calls == 2:
            self._on_second()
        return response


def test_a_job_cancelled_while_the_last_request_is_in_flight_records_nothing(world, harness_of, worker_id) -> None:
    """The mutation proof of the fence: the reply of the second side is paid for and kept, but the handler proves, in the transaction that
    would write the comparison, that the job still runs -- it does not, so the comparison is not recorded."""
    world.answers = _CancelsDuringTheSecondRequest(
        lambda: world.jobs.cancel(job_id=job.record.job_id, method="spec",
                                  command=_command(world.expert, f"cancel-mid-{world.scope.transition_id}", kind="cancel_comparison_specification")))
    world.record_answers()
    _estimate, job = world.start()
    outcome = harness_of(world.binder).run_next(worker_id, world.scope.project_uid)
    assert isinstance(outcome, Yielded) and world.answers.calls == 2
    whole = world.whole()
    assert world.state_of(job.record.job_id) == "cancelled" and whole.state == "running" and whole.totals is None and whole.changes == []
