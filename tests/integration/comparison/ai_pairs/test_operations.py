"""`CMP-VC-AIPAIR-01`: the seven operations of the AI pair check at the service the adapter calls, on a real database, in recorded mode:
the module gate, the role, the consent, the typed conflicts, the 404s, the key, the one live job, the steering, and the shapes the
contract's models accept.

The HTTP edge (roles by credential, the keys, the shipped routers) is in ``test_http.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.comparison.public import AiConsentInput
from auditmanager.shared.errors import DomainError, ErrorCode

EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SEVEN = ("estimate", "start", "get", "pause", "resume", "cancel", "hints")


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


def estimate(rig, world) -> dict[str, Any]:
    return rig.service.estimate(project_uid=world.project, document_uid=world.document)


def start(rig, world, *, key: str = "k1", digest: str | None = None, confirmed: bool = True, roles: frozenset[str] = EXPERT) -> dict[str, Any]:
    return rig.service.start(
        project_uid=world.project, document_uid=world.document,
        consent=AiConsentInput(estimate_digest=digest or estimate(rig, world)["estimate_digest"], confirmed=confirmed),
        user_uid=USER, actor_roles=roles, idempotency_key=key,
    )


def reason(refused) -> str:
    assert refused.value.code is ErrorCode.CONFLICT, refused.value.code
    return str(refused.value.detail_fields["conflict_reason"])


# -- the module gate ---------------------------------------------------------------------------------------------------------


def test_every_operation_refuses_naming_the_module_before_anything_is_read_or_written(db, h) -> None:
    """Mutation M8: ``_require_versions_module`` never raises -> the operations go on to read and write."""
    world = db.world(versions=2)
    rig = db.rig(world, modules="none")
    ghost = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    calls = {
        "estimate": lambda: rig.service.estimate(project_uid=world.project, document_uid=ghost),
        "start": lambda: rig.service.start(project_uid=world.project, document_uid=ghost, consent=AiConsentInput("a" * 64, True),
                                           user_uid=USER, actor_roles=EXPERT, idempotency_key="k"),
        "get": lambda: rig.service.get(project_uid=world.project, document_uid=ghost),
        "pause": lambda: rig.service.pause(job_id="cai_01ARZ3NDEKTSV4RRFFQ69G5FAV", user_uid=USER, actor_roles=EXPERT, idempotency_key="k"),
        "resume": lambda: rig.service.resume(job_id="cai_01ARZ3NDEKTSV4RRFFQ69G5FAV", consent=None, user_uid=USER, actor_roles=EXPERT, idempotency_key="k"),
        "cancel": lambda: rig.service.cancel(job_id="cai_01ARZ3NDEKTSV4RRFFQ69G5FAV", user_uid=USER, actor_roles=EXPERT, idempotency_key="k"),
        "hints": lambda: rig.service.hints(project_uid=world.project, document_uid=ghost, after=None, limit=10),
    }
    assert set(calls) == set(SEVEN)
    before = rig.scalar("SELECT count(*) FROM command_record") + rig.scalar("SELECT count(*) FROM comparison_ai_job")
    for name, call in calls.items():
        with pytest.raises(DomainError) as refused:
            call()
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE, name
        assert refused.value.detail_fields["dependency"] == "comparison_modules", name
    assert rig.scalar("SELECT count(*) FROM command_record") + rig.scalar("SELECT count(*) FROM comparison_ai_job") == before


# -- the role, the consent and the typed conflicts ---------------------------------------------------------------------------------


def test_a_start_is_an_experts_act(scene) -> None:
    """Mutation M9: the role test removed from the service (and, in the core, ``_require_expert``) -> an administrator starts."""
    world, rig = scene
    digest = estimate(rig, world)["estimate_digest"]
    with pytest.raises(DomainError) as refused:
        start(rig, world, digest=digest, roles=ADMIN)
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    assert rig.scalar("SELECT count(*) FROM comparison_ai_job WHERE document_uid = :d", d=world.document) == 0


def test_the_steering_is_an_experts_act_too(scene) -> None:
    world, rig = scene
    job_id = start(rig, world)["job_id"]
    for name in ("pause", "cancel"):
        with pytest.raises(DomainError) as refused:
            getattr(rig.service, name)(job_id=job_id, user_uid=USER, actor_roles=ADMIN, idempotency_key=f"k-{name}")
        assert refused.value.code is ErrorCode.PERMISSION_DENIED, name
    with pytest.raises(DomainError) as refused:
        rig.service.resume(job_id=job_id, consent=None, user_uid=USER, actor_roles=ADMIN, idempotency_key="k-resume")
    assert refused.value.code is ErrorCode.PERMISSION_DENIED


def test_nothing_is_sent_before_the_consent_and_the_estimate_agree(scene) -> None:
    world, rig = scene
    with pytest.raises(DomainError) as refused:
        start(rig, world, confirmed=False)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED and refused.value.detail_fields["constraint"] == "comparison_consent_required"
    with pytest.raises(DomainError) as stale:
        start(rig, world, digest="0" * 64)
    assert reason(stale) == "comparison_estimate_stale"
    assert rig.scalar("SELECT count(*) FROM comparison_ai_job WHERE document_uid = :d", d=world.document) == 0
    assert rig.scalar("SELECT count(*) FROM comparison_work WHERE kind = 'comparison_pair_check'") == 0
    assert rig.answers.calls == 0


def test_a_matrix_that_is_not_ready_is_comparison_matrix_stale(db, h) -> None:
    db.route()
    absent = db.world(versions=2)
    rig = db.rig(absent)
    for call in (lambda: estimate(rig, absent), lambda: start(rig, absent, digest="a" * 64)):
        with pytest.raises(DomainError) as refused:
            call()
        assert reason(refused) == "comparison_matrix_stale"
    built = db.world(versions=2)
    h.place_matrix(db.connection, built, [[h.matched(built, 1, 2), h.unmatched(built, 2, [2], ref=1)], [h.absent(built, 1), h.matched(built, 2, 2)]])
    rig = db.rig(built)
    assert estimate(rig, built)["questions"] == 1
    # a build made of other profiles than the ones stored now is stale, and so is any estimate of it
    h.place_matrix(db.connection, built, [[h.matched(built, 1, 2), h.unmatched(built, 2, [2], ref=1)]], signature="f" * 64)
    with pytest.raises(DomainError) as refused:
        estimate(rig, built)
    assert reason(refused) == "comparison_matrix_stale"


def test_no_route_in_the_assignments_is_executor_route_missing(db, h) -> None:
    world = db.world(versions=2)
    h.place_matrix(db.connection, world, [[h.matched(world, 1, 2), h.unmatched(world, 2, [2], ref=1)], [h.absent(world, 1), h.matched(world, 2, 2)]])
    rig = db.rig(world)
    with pytest.raises(DomainError) as refused:
        estimate(rig, world)
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and refused.value.detail_fields["dependency"] == "executor_route_missing"


def test_an_unknown_project_or_a_document_of_another_project_is_not_found(scene, db, h) -> None:
    world, rig = scene
    other = db.world(versions=2)
    ghost = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    reads = (
        lambda p, d: rig.service.estimate(project_uid=p, document_uid=d), lambda p, d: rig.service.get(project_uid=p, document_uid=d),
        lambda p, d: rig.service.hints(project_uid=p, document_uid=d, after=None, limit=5),
        lambda p, d: start(rig, type("W", (), {"project": p, "document": d})(), digest="a" * 64),
    )
    for read in reads:
        for project, document in ((ghost, world.document), (world.project, other.document), (other.project, world.document)):
            with pytest.raises(DomainError) as refused:
                read(project, document)
            assert refused.value.code is ErrorCode.NOT_FOUND, (project, document)


# -- the key, the one live job ---------------------------------------------------------------------------------------------------------


def test_a_start_with_the_same_key_and_the_same_consent_replays_the_job(scene) -> None:
    """Mutation M10: the replay branch of the core's start deleted -> the repeat creates a second job (or is refused)."""
    world, rig = scene
    digest = estimate(rig, world)["estimate_digest"]
    first = start(rig, world, key="k-same", digest=digest)
    items = rig.scalar("SELECT count(*) FROM comparison_work WHERE kind = 'comparison_pair_check'")
    again = start(rig, world, key="k-same", digest=digest)
    assert again["job_id"] == first["job_id"]
    assert rig.scalar("SELECT count(*) FROM comparison_ai_job WHERE document_uid = :d", d=world.document) == 1
    assert rig.scalar("SELECT count(*) FROM comparison_work WHERE kind = 'comparison_pair_check'") == items == 3, "two questions and the closing item"
    with pytest.raises(DomainError) as reused:
        rig.service.start(
            project_uid=world.project, document_uid=world.document, consent=AiConsentInput("b" * 64, True), user_uid=USER,
            actor_roles=EXPERT, idempotency_key="k-same",
        )
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_one_live_check_holds_a_document(scene) -> None:
    world, rig = scene
    start(rig, world, key="k-first")
    with pytest.raises(DomainError) as refused:
        start(rig, world, key="k-second")
    assert reason(refused) == "comparison_ai_job_active"


# -- the reads -----------------------------------------------------------------------------------------------------------------------------


def test_get_is_empty_until_a_check_was_started_and_then_carries_the_job_and_its_counts(scene) -> None:
    world, rig = scene
    assert rig.service.get(project_uid=world.project, document_uid=world.document) == {"document_uid": world.document}
    started = start(rig, world)
    got = rig.service.get(project_uid=world.project, document_uid=world.document)
    assert got["job"]["job_id"] == started["job_id"] and got["job"]["state"] == "queued"
    assert got["counts"] == {"questions": 2, "answered": 0, "pairs": 0, "hints": 0, "against": 0, "failed": 0, "reused": 0}


def test_the_contracts_models_accept_what_the_service_answers(scene) -> None:
    world, rig = scene
    shown = models.ComparisonAiEstimate.model_validate(estimate(rig, world))
    assert shown.questions == 2 and shown.route.provider_mode.value == "recorded"
    started = models.ComparisonAiJob.model_validate(start(rig, world))
    assert started.method.value == "pair_check" and started.state.value == "queued" and started.estimate.units == 2
    assert models.ComparisonAiPairCheck.model_validate(rig.service.get(project_uid=world.project, document_uid=world.document)).counts.questions == 2
    assert models.ComparisonAiPairCheck.model_validate({"document_uid": world.document}).job is None
    paused = models.ComparisonAiJob.model_validate(rig.service.pause(
        job_id=started.job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-p"))
    assert paused.state.value == "paused" and paused.pause_reason.value == "user"


def test_pause_resume_and_cancel_move_the_job_along_its_edges(scene) -> None:
    world, rig = scene
    job_id = start(rig, world)["job_id"]
    assert rig.service.pause(job_id=job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-p")["state"] == "paused"
    with pytest.raises(DomainError) as twice:
        rig.service.pause(job_id=job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-p2")
    assert reason(twice) == "comparison_ai_job_state"
    assert rig.service.resume(job_id=job_id, consent=None, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-r")["state"] == "queued"
    assert rig.service.cancel(job_id=job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-c")["state"] == "cancelled"
    with pytest.raises(DomainError) as over:
        rig.service.cancel(job_id=job_id, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-c2")
    assert reason(over) == "comparison_ai_job_state"
    with pytest.raises(DomainError) as missing:
        rig.service.pause(job_id="cai_01ARZ3NDEKTSV4RRFFQ69G5FAV", user_uid=USER, actor_roles=EXPERT, idempotency_key="k-x")
    assert missing.value.code is ErrorCode.NOT_FOUND


def test_a_resume_after_an_overrun_needs_a_new_consent_for_what_is_left(scene) -> None:
    """The estimate of a resume is for what the job still has to ask (``AiMode.LEFT``): the questions whose items are still live."""
    world, rig = scene
    job = rig.job(start(rig, world)["job_id"])
    first, second = rig.questions(job)
    rig.say(job, rig.forward(job, first), 3, "medium")        # the first question is asked and settles as a hint
    ran = rig.run_next()
    assert ran is not None and ran[0].payload["question"]["kind"] == "no_pair"
    with rig.sessions() as session:
        assert rig.service.jobs.pause_system(session, job.job_id, "overrun")
        session.commit()
    with pytest.raises(DomainError) as unconsented:
        rig.service.resume(job_id=job.job_id, consent=None, user_uid=USER, actor_roles=EXPERT, idempotency_key="k-r1")
    assert unconsented.value.code is ErrorCode.VALIDATION_FAILED
    with rig.sessions() as session:
        left = rig.service.jobs.estimate_in(session, job.scope, __import__("auditmanager.comparison.public", fromlist=["AiMode"]).AiMode.LEFT, job=job)
    assert left.counts.units == 1 and left.totals.calls == 1, "only the medium question is left: one forward call"
    resumed = rig.service.resume(
        job_id=job.job_id, consent=AiConsentInput(left.estimate_digest, True), user_uid=USER, actor_roles=EXPERT, idempotency_key="k-r2")
    assert resumed["state"] == "queued"


# -- the hints ------------------------------------------------------------------------------------------------------------------------------


def test_the_hints_list_the_decided_questions_newest_first_with_a_cursor_and_the_stale_flag(scene, h) -> None:
    world, rig = scene
    job = rig.job(start(rig, world)["job_id"])
    q_none, q_medium = rig.questions(job)
    rig.say(job, rig.forward(job, q_none), 3, "medium", "похоже на кровлю")
    rig.say(job, rig.forward(job, q_medium), 4)
    rig.drain()
    first = rig.service.hints(project_uid=world.project, document_uid=world.document, after=None, limit=1)
    assert len(first.items) == 1 and first.next_after is not None
    second = rig.service.hints(project_uid=world.project, document_uid=world.document, after=first.next_after, limit=1)
    assert len(second.items) == 1 and second.next_after is None
    items = first.items + second.items
    page = models.ComparisonAiPairHintPage.model_validate({"items": items, "page": {"next_cursor": None}})
    by_kind = {item.kind.value: item for item in page.items}
    hint = by_kind["no_pair"]
    assert hint.decision.value == "hint_confidence" and hint.hint_page.page_number == 3 and hint.confidence.value == "medium"
    assert hint.reason == "похоже на кровлю" and hint.page.page_number == 2 and not hint.stale and hint.link_id is None
    assert [c.page_number for c in hint.candidates] == [2, 3] and all(str(c.version_uid) == world.version(2) for c in hint.candidates)
    matrix_id = str(hint.matrix_id)
    assert str(hint.job_id) == job.job_id
    assert by_kind["medium_pair"].decision.value == "medium_confirm"
    assert [item.created_at for item in page.items] == sorted((item.created_at for item in page.items), reverse=True)
    # a build made since: the hints were asked of a matrix that is no longer the latest
    h.place_matrix(rig.connection, world, [[h.matched(world, 1, 2), h.absent(world, 2)]], signature="e" * 64)
    assert matrix_id != world.matrix_id
    later = rig.service.hints(project_uid=world.project, document_uid=world.document, after=None, limit=10)
    assert [item["stale"] for item in later.items] == [True, True]


def test_the_hints_are_empty_before_any_check(scene) -> None:
    world, rig = scene
    page = rig.service.hints(project_uid=world.project, document_uid=world.document, after=None, limit=10)
    assert page.items == [] and page.next_after is None
