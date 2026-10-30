"""Explicit generation recovery preserves paid replies and refuses unsafe resends."""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from auditmanager.comparison.ai_jobs.model import AiConsentInput
from auditmanager.comparison.ai_jobs.recorded import RecordedAnswers
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.comparison.stage_ai import StageAiRuntime
from auditmanager.comparison.stage_ai.runtime import request_for_plan
from auditmanager.comparison.work.model import Completed, Failed, Yielded
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.ai_jobs.ai_jobs_support import recorded_route
from tests.integration.comparison.stage_ai.test_runtime import _answer, _id, _profiles
from tests.integration.comparison.stage_text.test_store import _batch, _command, _seed
from tests.support.accounts import complete_expert_account


def started(session, adapter=None):
    store, pair, revision, _actor, left, right = _seed(session)
    actor = str(complete_expert_account(session, "stage-ai-recovery").user_uid)
    route = recorded_route(session.connection(), "comparison_stage_review")
    adapter = adapter or RecordedAnswers()
    runtime = StageAiRuntime(store._sessions, profile_reader=_profiles(session, left, right),
        routes=SimpleNamespace(route_for=lambda _session, job: CallRoute(adapter, job.pinned_model,
            connection_revision_id=job.connection_revision_id, expected_model=None, check_identity=False, unmetered=True)))
    estimate = runtime.estimate(revision_id=revision, user_uid=actor)
    fragments, manifest, raw = _batch(left, right)
    store.write(pair_id=pair, revision_id=revision, fragments=fragments, expected_keys=manifest, raw=raw, hints=())
    run = _id("crn")
    pins = session.execute(text("SELECT version_uid FROM comparison_page_profile WHERE comparison_page_profile_id=ANY(CAST(:ids AS text[]))"),
                           {"ids": [left, right]}).scalars().all()
    with session_scope(store._sessions) as opened:
        opened.execute(text("INSERT INTO stage_chain_run(stage_chain_run_id,stage_pair_id,stage_link_revision_id,input_sha256,"
            "pinned_version_uids,state,actor_user_uid,command_id,kind,with_ai) VALUES(:run,:pair,:revision,:sha,CAST(:pins AS jsonb),"
            "'running',:actor,:command,'full',true)"), {"run": run, "pair": pair, "revision": revision, "sha": "f" * 64,
            "pins": json.dumps(pins), "actor": actor, "command": _command(opened, "start_stage_chain_run")})
        for step in range(1, 8):
            opened.execute(text("INSERT INTO stage_chain_step(stage_chain_step_id,stage_chain_run_id,step_no) VALUES(:id,:run,:step)"),
                           {"id": _id("cst"), "run": run, "step": step})
        job = runtime.prepare(opened, run_id=run, user_uid=actor, consent=AiConsentInput(estimate.estimate_digest, True))
        opened.execute(text("UPDATE stage_chain_run SET comparison_ai_job_id=:job WHERE stage_chain_run_id=:run"), {"job": job, "run": run})
        worker = WorkerRegistry().register(opened, version="stage-ai-recovery", slots=1)
    scene = SimpleNamespace(runtime=runtime, adapter=adapter, store=store, pair=pair, revision=revision,
                            actor=actor, run=run, job=job, worker=worker, left=left, right=right, model=route.pinned_model)
    scene.item = enqueue(scene)
    return scene


def enqueue(scene):
    with session_scope(scene.store._sessions) as session:
        scope = scene.runtime._repo.run(session, scene.run)
        job = scope["comparison_ai_job_id"]
        ComparisonWorkRepository().enqueue(session, project_uid=scope["project_uid"], module="stages", kind="stage_chain",
            payload={"run_id": scene.run}, comparison_ai_job_id=job, created_by_user_uid=scene.actor)
        return ComparisonWorkRepository().claim(session, worker_id=scene.worker, modules={"stages"}, kinds={"stage_chain"})


def prepare_answer(scene, phase):
    with session_scope(scene.store._sessions) as session:
        snapshot = scene.runtime._repo.revision(session, scene.revision)
        bundles = scene.runtime._bundles(session, run_id=scene.run, snapshot=snapshot, phase=phase, model=scene.model)
    for _group, plans, _sha, _key in bundles:
        for plan in plans:
            scene.adapter.record(request_for_plan(plan), json.dumps(_answer(plan), ensure_ascii=False))


def drive(scene):
    for phase in ("review", "classify", "synthesize"):
        prepare_answer(scene, phase)
        for _ in range(8):
            outcome = scene.runtime.advance(scene.item, run_id=scene.run, phase=phase)
            assert not isinstance(outcome, Failed), outcome
            if isinstance(outcome, dict):
                break
        else:
            raise AssertionError("recovery phase did not finish")


def renew(scene):
    estimate = scene.runtime.estimate_resume(run_id=scene.run, user_uid=scene.actor)
    with session_scope(scene.store._sessions) as session:
        job = scene.runtime.resume(session, run_id=scene.run, user_uid=scene.actor,
                                   consent=AiConsentInput(estimate.estimate_digest, True))
        session.execute(text("UPDATE stage_chain_run SET state='running',failure_reason=NULL,pause_reason=NULL WHERE stage_chain_run_id=:run"),
                        {"run": scene.run})
    return job


def test_cancel_resume_reuses_saved_paid_reply_in_new_generation(comparison_session):
    scene = started(comparison_session)
    prepare_answer(scene, "review")
    assert isinstance(scene.runtime.advance(scene.item, run_id=scene.run, phase="review"), Yielded)
    assert scene.adapter.calls == 1
    with session_scope(scene.store._sessions) as session:
        scene.runtime.cancel(session, run_id=scene.run, user_uid=scene.actor)
        session.execute(text("UPDATE stage_chain_run SET state='cancelled' WHERE stage_chain_run_id=:run"), {"run": scene.run})
        assert ComparisonWorkRepository().finish(session, scene.item.authority, Yielded()) == "cancelled"
    new_job = renew(scene)
    assert new_job != scene.job
    scene.item = enqueue(scene)
    drive(scene)
    assert scene.adapter.calls == 3
    with session_scope(scene.store._sessions) as session:
        answer = session.execute(text("SELECT model_identity FROM stage_ai_review WHERE stage_chain_run_id=:run"), {"run": scene.run}).scalar_one()
        assert answer["call_identities"][0]["job_id"] == scene.job
        assert session.execute(text("SELECT count(DISTINCT generation) FROM stage_ai_unit WHERE stage_chain_run_id=:run"), {"run": scene.run}).scalar_one() == 2
        ComparisonWorkRepository().finish(session, scene.item.authority, Completed())


def test_completed_job_new_effective_source_gets_new_left_consented_generation(comparison_session):
    scene = started(comparison_session)
    drive(scene)
    with session_scope(scene.store._sessions) as session:
        ComparisonWorkRepository().finish(session, scene.item.authority, Completed())
        revision = _id("slk")
        session.execute(text("INSERT INTO stage_link_revision(stage_link_revision_id,stage_pair_id,revision_no,base_revision_id,source,"
            "input_sha256,actor_user_uid,command_id) VALUES(:revision,:pair,2,:base,'expert',:sha,:actor,:command)"),
            {"revision": revision, "pair": scene.pair, "base": scene.revision, "sha": "b" * 64, "actor": scene.actor,
             "command": _command(session, "apply_stage_sheet_map")})
        session.execute(text("INSERT INTO stage_link_item(stage_link_item_id,stage_link_revision_id,row_no,left_profile_id,right_profile_id,relation,confidence) "
            "VALUES(:id,:revision,1,:left,:right,'paired','manual')"), {"id": _id("sli"), "revision": revision, "left": scene.left, "right": scene.right})
        session.execute(text("UPDATE stage_chain_run SET effective_link_revision_id=:revision,state='paused',pause_reason='comparison_consent_required' "
            "WHERE stage_chain_run_id=:run"), {"revision": revision, "run": scene.run})
    scene.revision = revision
    fragments, manifest, raw = _batch(scene.left, scene.right)
    scene.store.write(pair_id=scene.pair, revision_id=revision, fragments=fragments, expected_keys=manifest, raw=raw, hints=())
    assert renew(scene) != scene.job
    scene.item = enqueue(scene)
    drive(scene)
    assert scene.adapter.calls == 6
    with session_scope(scene.store._sessions) as session:
        assert scene.runtime._jobs().job(session, scene.job).state == "completed"
        ComparisonWorkRepository().finish(session, scene.item.authority, Completed())


def test_completed_ai_can_resume_remaining_deterministic_step_without_new_consent_or_calls(comparison_session):
    scene = started(comparison_session)
    drive(scene)
    with session_scope(scene.store._sessions) as session:
        ComparisonWorkRepository().finish(session, scene.item.authority, Completed())
        session.execute(text("UPDATE stage_chain_run SET state='failed',failure_reason='review_materialization_failed' WHERE stage_chain_run_id=:run"), {"run": scene.run})
        assert scene.runtime.resume(session, run_id=scene.run, user_uid=scene.actor, consent=None) == scene.job
        session.execute(text("UPDATE stage_chain_run SET state='running',failure_reason=NULL WHERE stage_chain_run_id=:run"), {"run": scene.run})
    scene.item = enqueue(scene)
    for phase in ("review", "classify", "synthesize"):
        assert isinstance(scene.runtime.advance(scene.item, run_id=scene.run, phase=phase), dict)
    assert scene.adapter.calls == 3
    with session_scope(scene.store._sessions) as session:
        ComparisonWorkRepository().finish(session, scene.item.authority, Completed())


class Refusal(DomainError):
    dispatch_class = "definite_refusal"
    provider_failure_kind = "request"


@pytest.mark.parametrize("kind", ["safe", "unknown", "lost"])
def test_failed_recovery_only_allows_proven_unprocessed_request(comparison_session, kind):
    class Answers(RecordedAnswers):
        refused = False

        def complete(self, request):
            if not self.refused and kind != "lost":
                self.refused = True
                if kind == "safe":
                    raise Refusal(ErrorCode.ANALYSIS_INPUT_INVALID)
                raise RuntimeError("transport outcome unknown")
            return super().complete(request)

    scene = started(comparison_session, Answers())
    prepare_answer(scene, "review")
    result = scene.runtime.advance(scene.item, run_id=scene.run, phase="review")
    with session_scope(scene.store._sessions) as session:
        if kind == "lost":
            assert isinstance(result, Yielded)
            session.execute(text("UPDATE stage_ai_unit SET progress=progress-'responses' WHERE stage_chain_run_id=:run AND group_id<>'source-consent'"), {"run": scene.run})
            scene.runtime.cancel(session, run_id=scene.run, user_uid=scene.actor)
            session.execute(text("UPDATE stage_chain_run SET state='cancelled' WHERE stage_chain_run_id=:run"), {"run": scene.run})
        else:
            assert isinstance(result, Failed)
            assert scene.runtime._repo.run(session, scene.run)["state"] == "failed"
            assert session.execute(text("SELECT state FROM stage_chain_step WHERE stage_chain_run_id=:run AND step_no=4"), {"run": scene.run}).scalar_one() == "failed"
        ComparisonWorkRepository().finish(session, scene.item.authority, Yielded())
    if kind == "safe":
        assert renew(scene) != scene.job
        scene.item = enqueue(scene)
        drive(scene)
        assert scene.adapter.calls == 3
        with session_scope(scene.store._sessions) as session:
            ComparisonWorkRepository().finish(session, scene.item.authority, Completed())
    else:
        with pytest.raises(DomainError) as error:
            renew(scene)
        assert error.value.code is ErrorCode.CONFLICT
        assert comparison_session.execute(text("SELECT count(*) FROM comparison_ai_job WHERE stage_chain_run_id=:run"), {"run": scene.run}).scalar_one() == 1
