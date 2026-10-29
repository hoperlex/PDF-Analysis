"""`CMP-VC-AIPAIR-01`: when an answer becomes an accepted AI link and when it stays a hint -- through the whole job, on a real database,
in recorded mode (ADR-0025 decisions 3, 14, 20; the wave brief's rules 4 and 5).

Each test is one refusal of the rule (``decide.py``): a sheet is linked only with a high answer **and** an agreeing high reverse
answer, never inside a multi-sheet specification, never over a B that is already paired (by the algorithm or by an expert), never
when two sheets chose one B; and the AI layer writes only its own rows.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.comparison.matrix.service import ComparisonMatrixService, EditInput
from auditmanager.comparison.public import AiConsentInput, MatrixPageRef
from auditmanager.shared.errors import DomainError

EXPERT = frozenset({"expert"})
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def start(rig, world, key="k-start"):
    digest = rig.service.estimate(project_uid=world.project, document_uid=world.document)["estimate_digest"]
    started = rig.service.start(
        project_uid=world.project, document_uid=world.document, consent=AiConsentInput(estimate_digest=digest, confirmed=True),
        user_uid=USER, actor_roles=EXPERT, idempotency_key=key,
    )
    return rig.job(started["job_id"])


def decisions(rig, job):
    return {
        (r["page_number"], r["kind"]): r for r in rig.rows(
            "SELECT page_number, kind, state, decision, hint_page_number, comparison_ai_link_id, failure_reason "
            "FROM comparison_ai_pair_question WHERE comparison_ai_job_id = :j", j=job.job_id)
    }


def links(rig, world):
    return rig.rows("SELECT page_number, other_page_number FROM comparison_ai_link WHERE document_uid = :d", d=world.document)


@pytest.fixture
def one(db, h):
    """Sheet 2 of version 1 has no pair; B pages 2 and 3 are offered; B page 3's own cell offers A page 2."""
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 1), h.matched(world, 2, 1, "high")],
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2, 3], ref=1)],
        [h.unmatched(world, 1, [2], ref=2), h.matched(world, 2, 3)],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    rig = db.rig(world)
    job = start(rig, world)
    (question,) = rig.questions(job)
    return world, rig, job, question


def test_a_high_answer_with_an_agreeing_high_reverse_is_the_one_way_to_a_link(one) -> None:
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    rig.drain()
    assert [(r["page_number"], r["other_page_number"]) for r in links(rig, world)] == [(2, 3)]
    assert decisions(rig, job)[(2, "no_pair")]["decision"] == "link_accepted"


@pytest.mark.parametrize("confidence", ["medium", "low"])
def test_a_forward_answer_that_is_not_high_is_a_hint_and_the_reverse_is_not_even_asked(one, confidence: str) -> None:
    """Mutation M1: the confidence test deleted -> the (recorded) reverse that follows would turn this into a link."""
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3, confidence)
    rig.drain()
    assert decisions(rig, job)[(2, "no_pair")]["decision"] == "hint_confidence"
    assert links(rig, world) == [] and rig.answers.calls == 1, "a reverse question is worth its money only for a high answer"
    assert decisions(rig, job)[(2, "no_pair")]["hint_page_number"] == 3, "the page stays visible as «вероятно стр. 3»"


@pytest.mark.parametrize(
    ("page", "confidence"), [(1, "high"), (3, "high"), (0, "high"), (2, "medium"), (2, "low")],
    ids=["another sheet", "the sheet B again", "none", "A but medium", "A but low"],
)
def test_a_reverse_answer_that_does_not_name_the_sheet_with_high_confidence_is_only_a_hint(one, page: int, confidence: str) -> None:
    """Mutation M2: the reverse test deleted -> every high forward answer becomes a link whatever the reverse says."""
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    reverse = rig.reverse(job, question, 3)
    rig.say(job, reverse, page, confidence)
    rig.drain()
    assert decisions(rig, job)[(2, "no_pair")]["decision"] == "hint_reverse"
    assert links(rig, world) == [] and rig.answers.calls == 2


def test_a_reverse_question_that_nobody_recorded_is_a_loud_failure_and_accepts_nothing(one) -> None:
    """Recorded mode has no fall back: an unrecorded request is never a call to anything. The question fails; no link."""
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    rig.drain()
    row = decisions(rig, job)[(2, "no_pair")]
    assert row["state"] == "failed" and row["decision"] == "failed" and row["failure_reason"]
    assert links(rig, world) == []
    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "completed", (
        "a job with a failed unit still completes; counts.failed says so")
    assert rig.service.get(project_uid=world.project, document_uid=world.document)["counts"]["failed"] == 1


def test_the_number_and_the_page_of_an_answer_must_agree(one) -> None:
    world, rig, job, question = one
    plan = rig.forward(job, question)
    rig.answers.record(rig.request_of(job, plan), json.dumps({"choice": 2, "page": 2, "confidence": "high", "reason": "x"}))
    rig.drain()
    row = decisions(rig, job)[(2, "no_pair")]
    assert row["decision"] == "answer_mismatch" and row["hint_page_number"] is None
    assert links(rig, world) == [] and rig.answers.calls == 1


def test_an_answer_of_none_is_a_decision_not_a_hint(one) -> None:
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 0, "high", "ни один")
    rig.drain()
    assert decisions(rig, job)[(2, "no_pair")]["decision"] == "none"
    got = rig.service.get(project_uid=world.project, document_uid=world.document)["counts"]
    assert (got["against"], got["hints"], got["pairs"]) == (1, 0, 0)


def test_a_reply_that_is_not_the_schema_is_paid_for_never_stored_and_retried_within_the_budget(one) -> None:
    world, rig, job, question = one
    rig.answers.record(rig.request_of(job, rig.forward(job, question)), '{"choice": "two"}')
    outcomes = rig.drain()
    asks = [outcome for step, outcome, _ in outcomes if step == "ask"]
    assert len(asks) == 3 and all(type(o).__name__ == "Failed" and o.reason == "pair_answer_invalid" for o in asks)
    assert rig.answers.calls == 3, "three attempts, then the item ends failed"
    assert rig.scalar("SELECT count(*) FROM comparison_ai_pair_answer WHERE project_uid = :p", p=world.project) == 0
    assert decisions(rig, job)[(2, "no_pair")]["state"] == "failed"
    assert links(rig, world) == []


# -- never over a B that is already paired -------------------------------------------------------------------------------------


@pytest.fixture
def taken(db, h):
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 1), h.matched(world, 2, 1, "high")],     # B page 1 is paired with A page 1 by the algorithm
        [h.matched(world, 1, 2), h.unmatched(world, 2, [1, 3], ref=1)],
        [h.absent(world, 1), h.matched(world, 2, 3)],
    ])
    rig = db.rig(world)
    job = start(rig, world)
    (question,) = rig.questions(job)
    return world, rig, job, question


def test_a_b_that_the_algorithm_already_paired_is_not_even_offered(taken) -> None:
    """The first layer of «never over a linked B»: the matrix drops the candidates that already stand in a row with the reference
    sheet (``lineage.py:612-640``), so the model is never asked to choose a page that belongs to another sheet."""
    world, rig, job, question = taken
    assert [page.page_number for page in question.candidates] == [3], "B page 1 is paired with A page 1"
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    rig.drain()
    assert [(r["page_number"], r["other_page_number"]) for r in links(rig, world)] == [(2, 3)]


def test_a_b_that_an_expert_pairs_while_the_job_runs_is_never_taken_over(db, h) -> None:
    """The second layer, and the one that matters: the decision reads the effective matrix as it is when the job closes, so a B
    an expert has paired meanwhile -- gone from the candidates of the cell, and still taken -- is only a hint.
    Mutation M4: the ``taken_b`` test of the rule deleted -> this turns into a link over the expert's pairing."""
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2, 3], ref=1)],
        [h.unmatched(world, 1, [2], ref=2), h.matched(world, 2, 3)],
        [h.matched(world, 1, 5), h.absent(world, 2)],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    rig = db.rig(world)
    job = start(rig, world)
    (question,) = rig.questions(job)
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    ran = rig.run_next()
    assert ran is not None and ran[0].payload["step"] == "ask"                    # the question is asked and answered
    # the expert pairs sheet 5 of version 1 with B page 3 before the closing item decides
    ComparisonMatrixService(session_factory=rig.sessions).apply_edits(
        project_uid=world.project, document_uid=world.document, base_matrix_id=world.matrix_id, base_edit_no=0,
        edits=[EditInput("link", MatrixPageRef(world.version(1), 5), MatrixPageRef(world.version(2), 3))],
        user_uid=USER, actor_label="Эксперт", actor_roles=EXPERT, idempotency_key="k-edit",
    )
    rig.drain()
    assert decisions(rig, job)[(2, "no_pair")]["decision"] == "hint_taken"
    assert links(rig, world) == []
    assert rig.answers.calls == 2, "both questions were paid for; the expert's link decided"


# -- never when two sheets chose one B ---------------------------------------------------------------------------------------------


def test_two_sheets_that_chose_the_same_b_are_both_only_hints(db, h) -> None:
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [3], ref=1)],
        [h.matched(world, 1, 5), h.unmatched(world, 2, [3], ref=1)],
        [h.absent(world, 1), h.matched(world, 2, 3)],
    ])
    rig = db.rig(world)
    job = start(rig, world)
    first, second = rig.questions(job)
    for question, own in ((first, 2), (second, 5)):
        rig.say(job, rig.forward(job, question), 3)
        reverse = rig.reverse(job, question, 3)
        assert reverse is not None
        rig.say(job, reverse, own)            # each reverse question names its own sheet with high confidence
    rig.drain()
    got = decisions(rig, job)
    assert got[(2, "no_pair")]["decision"] == got[(5, "no_pair")]["decision"] == "hint_shared"
    assert links(rig, world) == []


# -- never inside a multi-sheet specification ------------------------------------------------------------------------------------


def test_a_sheet_of_a_multi_sheet_specification_is_not_asked_at_all(db, h) -> None:
    """Mutation M3b: the specification skip removed -> the model is asked about a table sheet (the original found those answers
    unstable, ``sheet_match.py:3-4``) and the decision's own ``multi`` guard is the only thing between it and a link."""
    db.route()
    world = db.world(versions=2, titles={(1, 2): "Спецификация оборудования", (1, 3): "Спецификация оборудования"})
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2], ref=1)],
        [h.matched(world, 1, 3), h.unmatched(world, 2, [3], ref=1)],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    rig = db.rig(world)
    with pytest.raises(DomainError) as refused:
        start(rig, world)
    assert refused.value.detail_fields["conflict_reason"] == "comparison_ai_nothing_to_do"
    assert rig.answers.calls == 0 and links(rig, world) == []


# -- manual edits win ----------------------------------------------------------------------------------------------------------------


def test_an_accepted_link_is_labelled_ai_and_a_later_manual_edit_wins_over_it(one) -> None:
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    rig.drain()
    matrix = ComparisonMatrixService(session_factory=rig.sessions)
    before = matrix.get_matrix(project_uid=world.project, document_uid=world.document)
    row = next(r for r in before["rows"] if any(c.get("confidence") == "ai" for c in r["cells"]))
    assert [c["page"]["page_number"] for c in row["cells"]] == [2, 3] and before["counts"]["ai"] == 1
    # an expert links sheet 2 with B page 2 instead: the manual cell wins, the AI link reads superseded
    matrix.apply_edits(
        project_uid=world.project, document_uid=world.document, base_matrix_id=world.matrix_id,
        base_edit_no=before["revision"]["edit_no"],
        edits=[EditInput("link", MatrixPageRef(world.version(1), 2), MatrixPageRef(world.version(2), 2))],
        user_uid=USER, actor_label="Эксперт", actor_roles=EXPERT, idempotency_key="k-manual",
    )
    after = matrix.get_matrix(project_uid=world.project, document_uid=world.document)
    row = next(r for r in after["rows"] if r["cells"][0]["page"]["page_number"] == 2)
    assert row["cells"][1]["page"]["page_number"] == 2 and row["cells"][1]["confidence"] == "manual"
    assert after["counts"]["ai"] == 0 and after["counts"]["manual"] >= 1
    listed = matrix.list_ai_links(project_uid=world.project, document_uid=world.document, after=None, limit=10)
    assert [item["status"] for item in listed.items] == ["superseded"]
    assert [(r["page_number"], r["other_page_number"]) for r in links(rig, world)] == [(2, 3)], (
        "the AI row stays: the layers are separate rows and nothing rewrites another")


def test_a_cell_an_expert_has_already_edited_is_not_asked(db, h) -> None:
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2, 3], ref=1)],
        [h.unmatched(world, 1, [2], ref=2), h.matched(world, 2, 3)],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    rig = db.rig(world)
    ComparisonMatrixService(session_factory=rig.sessions).apply_edits(
        project_uid=world.project, document_uid=world.document, base_matrix_id=world.matrix_id, base_edit_no=0,
        edits=[EditInput("link", MatrixPageRef(world.version(1), 2), MatrixPageRef(world.version(2), 2))],
        user_uid=USER, actor_label="Эксперт", actor_roles=EXPERT, idempotency_key="k-manual",
    )
    with pytest.raises(DomainError) as refused:
        rig.service.estimate(project_uid=world.project, document_uid=world.document)
        start(rig, world)
    assert refused.value.detail_fields["conflict_reason"] == "comparison_ai_nothing_to_do"


# -- the steering -----------------------------------------------------------------------------------------------------------------------


def test_a_cancelled_job_decides_and_writes_nothing_and_its_questions_end_cancelled(one) -> None:
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    rig.service.cancel(job_id=job.job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-cancel")
    rig.drain()
    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "cancelled"
    assert decisions(rig, job)[(2, "no_pair")]["state"] == "cancelled" and links(rig, world) == []
    assert rig.answers.calls == 0


def test_a_paused_job_asks_nothing_until_it_is_resumed(one) -> None:
    world, rig, job, question = one
    rig.say(job, rig.forward(job, question), 3)
    rig.say(job, rig.reverse(job, question, 3), 2)
    rig.service.pause(job_id=job.job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-pause")
    assert [step for step, *_ in rig.drain(limit=5) if step == "ask"] == [] and rig.answers.calls == 0
    resumed = rig.service.resume(job_id=job.job_id, consent=None, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-resume")
    assert resumed["state"] == "queued"
    rig.drain()
    assert [(r["page_number"], r["other_page_number"]) for r in links(rig, world)] == [(2, 3)]


def test_the_closing_item_decides_nothing_while_a_question_is_still_live(db, h) -> None:
    """Mutation M15: the wait for the questions deleted -> the decisions are made on the answers that happen to be there, and a
    question asked a minute later is lost (the job is completed without it)."""
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 2), h.unmatched(world, 2, [3], ref=1)],
        [h.matched(world, 1, 5), h.unmatched(world, 2, [4], ref=1)],
        [h.absent(world, 1), h.matched(world, 2, 3)],
        [h.absent(world, 1), h.matched(world, 2, 4)],
    ])
    rig = db.rig(world)
    job = start(rig, world)
    first, second = rig.questions(job)
    for question in (first, second):
        rig.say(job, rig.forward(job, question), question.candidates[0].page_number, "medium")
    ran = rig.run_next()                                     # one question is asked: the job runs
    assert ran is not None and ran[0].payload["step"] == "ask"
    rig.connection.exec_driver_sql(                        # the other waits; the closing item is due
        "UPDATE comparison_work SET not_before = clock_timestamp() + interval '1 hour' WHERE project_uid = %s AND state = 'queued' "
        "AND payload ->> 'step' = 'ask'", (world.project,))
    rig.connection.exec_driver_sql(
        "UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' WHERE project_uid = %s AND payload ->> 'step' = 'close'",
        (world.project,))
    closing = rig.run_next()
    assert closing is not None and closing[0].payload["step"] == "close" and type(closing[1]).__name__ == "Yielded"
    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "running"
    assert rig.scalar("SELECT count(*) FROM comparison_ai_pair_question WHERE comparison_ai_job_id = :j AND state = 'queued'", j=job.job_id) == 2
    rig.connection.exec_driver_sql(
        "UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' WHERE project_uid = %s", (world.project,))
    rig.drain()
    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "completed"
    assert rig.scalar("SELECT count(*) FROM comparison_ai_pair_question WHERE comparison_ai_job_id = :j AND state = 'answered'", j=job.job_id) == 2
