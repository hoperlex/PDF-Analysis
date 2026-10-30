"""`CMP-VC-AIPAIR-01`: a pair check from the estimate to the accepted link, in recorded mode, on a real database.

One document set of two versions: sheet 1 is paired with high confidence; sheet 2 has no pair and its cell offers B pages 2 and 3
(a ``no_pair`` question; B page 3's own cell offers A page 2, so the reverse question exists); sheet 3 is paired with B page 4
at medium confidence (a ``medium_pair`` question). The model is :class:`RecordedAnswers`: an answer is filed under the digest of the
exact request, so a question that was not recorded fails loudly and is never a call to anything.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.comparison.matrix.service import ComparisonMatrixService
from auditmanager.shared.errors import DomainError


@pytest.fixture
def scene(db, h):
    db.route()
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [
        [h.matched(world, 1, 1), h.matched(world, 2, 1, "high")],
        [h.matched(world, 1, 2), h.unmatched(world, 2, [2, 3], ref=1)],
        [h.unmatched(world, 1, [2], ref=2), h.matched(world, 2, 3)],
        [h.matched(world, 1, 3), h.matched(world, 2, 4, "medium")],
        [h.absent(world, 1), h.matched(world, 2, 2)],
    ])
    return world, db.rig(world)


def consent(rig, world, confirmed=True):
    from auditmanager.comparison.public import AiConsentInput

    digest = rig.service.estimate(project_uid=world.project, document_uid=world.document)["estimate_digest"]
    return AiConsentInput(estimate_digest=digest, confirmed=confirmed)


def start(rig, world, key="k-start"):
    return rig.service.start(
        project_uid=world.project, document_uid=world.document, consent=consent(rig, world), user_uid="usr_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        actor_roles=frozenset({"expert"}), idempotency_key=key,
    )


def test_the_estimate_counts_the_questions_the_calls_the_pictures_and_the_money(scene) -> None:
    world, rig = scene
    estimate = rig.service.estimate(project_uid=world.project, document_uid=world.document)
    assert estimate["method"] == "pair_check"
    assert (estimate["units"], estimate["questions"], estimate["pairs"], estimate["reused"]) == (2, 2, 1, 0)
    # two forward calls (3 pictures for the no_pair question, 4 for the medium one) and one possible reverse call (4 pictures)
    assert estimate["calls"] == 3 and estimate["images"] == 3 + 4 + 4
    assert estimate["image_bytes"] > 0 and estimate["prompt_chars"] > 0 and estimate["estimate_micros"] > 0
    assert estimate["route"]["provider_mode"] == "recorded"
    assert len(estimate["estimate_digest"]) == 64


def test_a_check_asks_decides_and_writes_the_accepted_link(scene, h) -> None:
    world, rig = scene
    started = start(rig, world)
    job = rig.job(started["job_id"])
    assert started["state"] == "queued" and started["counts"]["total"] == 2
    q_none, q_medium = rig.questions(job)
    assert (q_none.kind, q_medium.kind) == ("no_pair", "medium_pair")

    forward = rig.forward(job, q_none)
    rig.say(job, forward, 3)                                # the model: B page 3 is the same sheet, with high confidence
    reverse = rig.reverse(job, q_none, 3)
    assert reverse is not None and reverse.cands == (1, 2, 3)
    rig.say(job, reverse, 2)                                # asked back, it names sheet A
    rig.say(job, rig.forward(job, q_medium), 4)             # the algorithm's pair is confirmed

    outcomes = rig.drain()
    assert [step for step, *_ in outcomes] == ["ask", "ask", "close"]
    assert all(type(outcome).__name__ == "Completed" for _step, outcome, _state in outcomes)
    assert rig.answers.calls == 3, "two forward questions and one reverse question, and nothing else"

    assert rig.scalar("SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job.job_id) == "completed"
    decisions = {r["kind"]: r for r in rig.rows(
        "SELECT kind, state, decision, hint_page_number, comparison_ai_link_id FROM comparison_ai_pair_question "
        "WHERE comparison_ai_job_id = :j", j=job.job_id)}
    assert decisions["no_pair"]["decision"] == "link_accepted" and decisions["no_pair"]["hint_page_number"] == 3
    assert decisions["medium_pair"]["decision"] == "medium_confirm" and decisions["medium_pair"]["comparison_ai_link_id"] is None
    link = rig.rows("SELECT * FROM comparison_ai_link WHERE document_uid = :d", d=world.document)
    assert len(link) == 1
    assert (link[0]["page_number"], link[0]["other_page_number"], link[0]["answered_state"], link[0]["confidence"]) == (2, 3, "unmatched", "high")
    assert link[0]["comparison_matrix_id"] == world.matrix_id and link[0]["comparison_model_call_id"] is not None
    assert decisions["no_pair"]["comparison_ai_link_id"] == link[0]["comparison_ai_link_id"]

    # the AI layer is read by the effective matrix, labelled «ИИ», and the stored build is untouched
    matrix = ComparisonMatrixService(session_factory=rig.sessions).get_matrix(project_uid=world.project, document_uid=world.document)
    ai_cells = [c for row in matrix["rows"] for c in row["cells"] if c.get("confidence") == "ai"]
    assert len(ai_cells) == 1 and ai_cells[0]["page"]["page_number"] == 3 and matrix["counts"]["ai"] == 1
    stored = rig.scalar("SELECT rows FROM comparison_matrix WHERE comparison_matrix_id = :m", m=world.matrix_id)
    assert json.dumps(stored, sort_keys=True).count('"ai"') == 0, "the raw matrix is never rewritten"


def test_the_counts_say_questions_pairs_hints_against(scene, h) -> None:
    world, rig = scene
    started = start(rig, world)
    job = rig.job(started["job_id"])
    q_none, q_medium = rig.questions(job)
    rig.say(job, rig.forward(job, q_none), 3)
    rig.say(job, rig.reverse(job, q_none, 3), 2)
    rig.say(job, rig.forward(job, q_medium), 0)             # none of the three is the same sheet: «против»
    rig.drain()
    got = rig.service.get(project_uid=world.project, document_uid=world.document)
    assert got["document_uid"] == world.document and got["job"]["state"] == "completed"
    assert got["counts"] == {"questions": 2, "answered": 2, "pairs": 1, "hints": 0, "against": 1, "failed": 0, "reused": 0}


def test_a_stored_answer_is_never_asked_again(scene, h) -> None:
    """The content key: a second check of the same sheets finds every answer stored, so nothing is left to send."""
    world, rig = scene
    first = start(rig, world)
    job = rig.job(first["job_id"])
    q_none, q_medium = rig.questions(job)
    rig.say(job, rig.forward(job, q_none), 2, confidence="medium")     # a hint: not high, so no reverse question
    rig.say(job, rig.forward(job, q_medium), 4)
    rig.drain()
    calls = rig.answers.calls
    assert calls == 2
    estimate = rig.service.estimate(project_uid=world.project, document_uid=world.document)
    assert estimate["reused"] == estimate["units"] == 2 and estimate["calls"] == 0 and estimate["estimate_micros"] == 0
    with pytest.raises(DomainError) as refused:
        start(rig, world, key="k-again")
    assert refused.value.detail_fields["conflict_reason"] == "comparison_ai_nothing_to_do"
    assert rig.answers.calls == calls
    assert rig.scalar("SELECT count(*) FROM comparison_ai_pair_answer WHERE project_uid = :p", p=world.project) == 2
