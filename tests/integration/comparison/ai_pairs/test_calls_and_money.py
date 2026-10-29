"""`CMP-VC-AIPAIR-01`: what a call looks like and what it costs -- the pictures, the journal, a stored answer shared by two questions,
a live-mode money pause and a route that changed, a retry of the questions that failed, and a handler that has nothing to call with.

Recorded mode throughout: the "live" tests use the core's scripted adapter, which says ``live`` so that the spend wrapper applies its
money rules, calls nothing and holds no credential.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from auditmanager.analysis.public import ModelRequest, ModelResponse, ProviderMode
from auditmanager.comparison.public import AiConsentInput, AiMode, CallRoute
from auditmanager.executors.public import image_load

EXPERT = frozenset({"expert"})
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def start(rig, world, key="k-start"):
    digest = rig.service.estimate(project_uid=world.project, document_uid=world.document)["estimate_digest"]
    started = rig.service.start(
        project_uid=world.project, document_uid=world.document, consent=AiConsentInput(estimate_digest=digest, confirmed=True),
        user_uid=USER, actor_roles=EXPERT, idempotency_key=key,
    )
    return rig.job(started["job_id"])


@pytest.fixture
def one(db, h):
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2, 3], ref=1)],
        [h.unmatched(world, 1, [2], ref=2), h.matched(world, 2, 3)],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    rig = db.rig(world)
    job = start(rig, world)
    (question,) = rig.questions(job)
    return world, rig, job, question


# -- the pictures --------------------------------------------------------------------------------------------------------------


def test_a_request_carries_the_stored_previews_in_the_order_the_prompt_names_them(one) -> None:
    """The pictures are blobs the page profiles already own: the descriptor of each is the preview's own blob, so the pull channel
    can fetch it by id; they travel in the C0 image channel, sheet first, with opaque crop references."""
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    rig.drain()
    forward, reverse = rig.answers.requests
    assert [d["blob_id"] for d in forward.body["images"]] == [world.blob_ids[(1, 2)], world.blob_ids[(2, 2)], world.blob_ids[(2, 3)]]
    assert [d["crop_id"] for d in forward.body["images"]] == ["sheet-a", "cand-1", "cand-2"]
    assert forward.images_bytes == (world.pngs[(1, 2)], world.pngs[(2, 2)], world.pngs[(2, 3)])
    assert (image_load(forward).count, image_load(forward).total_bytes) == (3, sum(len(world.pngs[k]) for k in ((1, 2), (2, 2), (2, 3))))
    assert [d["blob_id"] for d in reverse.body["images"]][0] == world.blob_ids[(2, 3)], "the reverse question starts from the sheet B chose"
    assert "Изображение 2 — кандидат 1" in forward.body["messages"][0]["content"]
    assert forward.body["model"] == job.pinned_model and forward.body["max_tokens"] > 0


def test_a_cell_with_many_candidates_sends_at_most_five_pictures(db, h) -> None:
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 1), h.unmatched(world, 2, [1, 2, 3, 4, 5, 6, 7, 8, 9], ref=1)],
        [h.absent(world, 1), h.matched(world, 2, 10)],
    ])
    rig = db.rig(world)
    shown = rig.service.estimate(project_uid=world.project, document_uid=world.document)
    # one forward call (the sheet and four candidates) and one possible reverse call (the sheet B chose, A and its neighbour)
    assert shown["questions"] == 1 and shown["images"] <= 5 + 5 and shown["calls"] == 2
    (question,) = rig.questions(start(rig, world))
    assert len(question.candidates) == 4


# -- the journal and a stored answer shared by two questions ---------------------------------------------------------------


def test_every_call_is_journaled_before_the_request_and_its_answer_points_at_its_row(one) -> None:
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    rig.drain()
    calls = rig.rows("SELECT state, provider_mode, work_kind, cost_basis, cost_micros FROM comparison_model_call ORDER BY prepared_at")
    assert [(c["state"], c["provider_mode"], c["work_kind"], c["cost_basis"], c["cost_micros"]) for c in calls] == [
        ("completed", "recorded", "comparison_pair_check", "unmetered", 0)] * 2
    answers = rig.rows("SELECT question_kind, model_identity, comparison_model_call_id, prompt_version, answer FROM comparison_ai_pair_answer "
                       "WHERE project_uid = :p ORDER BY created_at", p=world.project)
    assert [a["question_kind"] for a in answers] == ["no_pair", "reverse_check"]
    assert all(a["model_identity"] == "recorded" and a["comparison_model_call_id"] for a in answers), "labelled as a recorded answer"
    assert answers[0]["answer"] == {"choice": 2, "page": 3, "confidence": "high", "reason": "тот же лист", "cands": [2, 3]}


def test_two_questions_that_ask_the_same_reverse_question_send_it_once(db, h) -> None:
    """A stored answer is never asked again -- inside one job too: two sheets that choose the same B, whose own cell offers both of
    them, put the same question to the model."""
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [3], ref=1)],
        [h.matched(world, 1, 5), h.unmatched(world, 2, [3], ref=1)],
        [h.unmatched(world, 1, [2, 5], ref=2), h.matched(world, 2, 3)],
    ])
    rig = db.rig(world)
    job = start(rig, world)
    first, second = rig.questions(job)
    for question in (first, second):
        rig.say(job, rig.forward(job, question), 3)
    shared = rig.reverse(job, first, 3)
    assert shared is not None and shared.key == rig.reverse(job, second, 3).key and shared.cands == (2, 5)
    rig.say(job, shared, 2)
    rig.drain()
    assert rig.answers.calls == 3, "two forward questions and the reverse question once"
    assert rig.scalar("SELECT count(*) FROM comparison_ai_pair_answer WHERE project_uid = :p", p=world.project) == 3
    got = {r["page_number"]: r["decision"] for r in rig.rows(
        "SELECT page_number, decision FROM comparison_ai_pair_question WHERE comparison_ai_job_id = :j", j=job.job_id)}
    assert got == {2: "link_accepted", 5: "hint_reverse"}, "the one answer names sheet 2: it confirms 2 and not 5"


# -- live mode: the money rules reach the job ------------------------------------------------------------------------------------


@dataclass
class ScriptedLive:
    """Says ``live`` (the wrapper then applies its money rules), answers the scripted texts in order and calls nothing."""

    texts: list[str]
    cost: float
    requests: list[ModelRequest] = field(default_factory=list)

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            output_text=self.texts[len(self.requests) - 1], stop_reason="end_turn", input_tokens=1000, output_tokens=100,
            latency_ms=10, reported_cost_usd=self.cost, model="anthropic/claude-opus-5",
        )


def live_rig(db, h, world, adapter, *, revision: list[str] | None = None):
    from auditmanager.analysis.public import ModelPin

    pin = ModelPin(model_id="claude-opus-5", input_per_mtok_usd=5.0, output_per_mtok_usd=25.0)

    def binder(session, job):
        return CallRoute(
            adapter=adapter, model_identity=job.pinned_model, connection_revision_id=revision[0] if revision else job.connection_revision_id,
            expected_model="anthropic/claude-opus-5", check_identity=True, pin=pin,
        )

    return db.rig(world, live_binder=binder, provider_mode="live")


def answer(page: int, confidence: str = "high") -> str:
    return json.dumps({"choice": 1 if page == 2 else 2, "page": page, "confidence": confidence, "reason": "x"})


def test_a_live_call_that_overruns_its_estimate_pauses_the_job_keeps_the_answer_and_waits_for_a_new_consent(db, h) -> None:
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2, 3], ref=1)],
        [h.unmatched(world, 1, [2], ref=2), h.matched(world, 2, 3)],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    adapter = ScriptedLive([answer(3), json.dumps({"choice": 2, "page": 2, "confidence": "high", "reason": "x"})], cost=5.0)
    rig = live_rig(db, h, world, adapter)
    started = rig.service.start(
        project_uid=world.project, document_uid=world.document,
        consent=AiConsentInput(rig.service.estimate(project_uid=world.project, document_uid=world.document)["estimate_digest"], True),
        user_uid=USER, actor_roles=EXPERT, idempotency_key="k-live",
    )
    job = rig.job(started["job_id"])
    assert job.provider_mode == "live"
    ran = rig.run_next()
    assert ran is not None and type(ran[1]).__name__ == "Yielded", "the reverse question waits for the resume"
    assert len(adapter.requests) == 1, "no further call is made once the job is over its estimate"
    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "paused"
    assert rig.scalar("SELECT pause_reason FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "overrun"
    assert rig.scalar("SELECT count(*) FROM comparison_ai_pair_answer WHERE project_uid = :p", p=world.project) == 1, "the paid-for reply is kept"
    spent = rig.service.get(project_uid=world.project, document_uid=world.document)["job"]["spend"]
    assert spent["calls"] == 1 and spent["spent_micros"] == 5_000_000


def test_a_route_that_changed_since_the_consent_pauses_the_job_and_sends_nothing(db, h, core_support) -> None:
    route = db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2, 3], ref=1)],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    adapter = ScriptedLive([answer(3)], cost=0.01)
    revision: list[str] = []
    rig = live_rig(db, h, world, adapter, revision=revision)
    job = start(rig, world)
    revision.append(core_support.new_revision(db.connection, route))   # the connection is revised after the consent was given
    ran = rig.run_next()
    assert ran is not None and type(ran[1]).__name__ == "Failed" and ran[1].reason in {"consent_stale", "consent_required"}
    assert adapter.requests == []
    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "paused"
    assert rig.scalar("SELECT pause_reason FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "route_changed"


# -- a handler with nothing to call with, and a job that is not running ----------------------------------------------------------------


def test_without_a_model_binder_an_item_fails_loudly_and_calls_nothing(one) -> None:
    world, rig, job, question = one
    rig.handler._binder = None
    ran = rig.run_next()
    assert ran is not None and type(ran[1]).__name__ == "Failed" and ran[1].reason == "model_binder_missing"
    assert rig.answers.calls == 0


def test_an_item_of_a_job_that_is_not_running_sends_nothing_and_waits(one) -> None:
    world, rig, job, question = one
    rig.service.pause(job_id=job.job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-pause")
    rig.connection.exec_driver_sql("UPDATE comparison_work SET state = 'queued' WHERE comparison_ai_job_id = %s AND state = 'paused'", (job.job_id,))
    ran = rig.run_next()
    assert ran is not None and type(ran[1]).__name__ == "Yielded" and ran[1].delay_seconds > 0
    assert rig.answers.calls == 0


def test_an_item_with_a_payload_it_does_not_know_fails_without_a_retry(one) -> None:
    world, rig, job, question = one
    from auditmanager.comparison.public import WorkItem
    from auditmanager.comparison.work.model import ItemAuthority

    bad = WorkItem(work_id="cq_x", attempt_id="a", attempt_no=1, project_uid=world.project, module="versions", kind=rig.handler.kind,
                   payload={"step": "sideways"}, comparison_upload_id=None, created_by_user_uid=None, max_attempts=3,
                   authority=ItemAuthority("cq_x", "a", "t"))
    outcome = rig.handler.run(bad)
    assert type(outcome).__name__ == "Failed" and outcome.reason == "pair_check_payload_invalid" and not outcome.retry


# -- «Повторить»: the questions that failed ------------------------------------------------------------------------------------------


def test_the_questions_that_failed_are_asked_again_under_a_new_consent(one) -> None:
    from auditmanager.comparison.public import AiJobCommand

    world, rig, job, question = one
    rig.answers.record(rig.request_of(job, rig.forward(job, question)), '{"choice": "two"}')  # not the schema, three times
    rig.drain()
    assert rig.scalar("SELECT state FROM comparison_ai_pair_question WHERE comparison_ai_job_id = :j", j=job.job_id) == "failed"
    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "completed"
    with rig.sessions() as session:
        again = rig.service.jobs.estimate_in(session, job.scope, AiMode.FAILED, job=job)
    assert again.counts.units == 1 and again.totals.calls == 2
    rig.answers._answers.clear()
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    command = AiJobCommand("retry_comparison_ai_pair_check", "k-retry", USER, EXPERT)
    retried = rig.service.jobs.retry(job_id=job.job_id, method="pair_check", command=command, consent=AiConsentInput(again.estimate_digest, True))
    assert retried.record.state == "queued"
    rig.drain()
    assert rig.scalar("SELECT state FROM comparison_ai_pair_question WHERE comparison_ai_job_id = :j", j=job.job_id) == "answered"
    assert rig.scalar("SELECT count(*) FROM comparison_ai_link WHERE document_uid = :d", d=world.document) == 1
