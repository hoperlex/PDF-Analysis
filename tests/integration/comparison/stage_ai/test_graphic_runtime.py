"""Real graphic receipts/crops and shared spend with a recorded image-only run."""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from auditmanager.comparison.ai_jobs.model import AiConsentInput
from auditmanager.comparison.ai_jobs.recorded import RecordedAnswers
from auditmanager.comparison.engine import PairResultRepository
from auditmanager.comparison.engine.key import content_key
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.comparison.stage_ai import StageAiRuntime
from auditmanager.comparison.stage_ai import graphic
from auditmanager.comparison.stage_ai.loop import next_step
from auditmanager.comparison.stage_ai.runtime import request_for_plan
from auditmanager.comparison.stage_graphic import StageGraphicService
from auditmanager.comparison.stage_graphic.evidence import project_result
from auditmanager.comparison.work.model import Completed, Failed, Yielded
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.ai_jobs.ai_jobs_support import recorded_route
from tests.integration.comparison.stage_ai.test_runtime import _answer, _id, _profiles
from tests.integration.comparison.stage_text.test_store import _command, _seed
from tests.support.accounts import complete_expert_account
from tests.unit.comparison.stage_ai.test_graphic import PNG


@pytest.mark.parametrize("repair", [False, True])
def test_graphic_only_windows_real_receipts_and_effective_source_consent(comparison_session, repair):
    store, pair, revision, _actor, left, right = _seed(comparison_session)
    actor = str(complete_expert_account(comparison_session, "stage-ai-graphic").user_uid)
    route = recorded_route(comparison_session.connection(), "comparison_stage_review")
    provider = StageGraphicService(store._sessions, blob_store=None,
        material=SimpleNamespace(crop=lambda *_args, **_kwargs: PNG))
    adapter = RecordedAnswers()
    runtime = StageAiRuntime(store._sessions, graphic_source=provider,
        profile_reader=_profiles(comparison_session, left, right, empty=True),
        routes=SimpleNamespace(route_for=lambda _session, job: CallRoute(adapter, job.pinned_model,
            connection_revision_id=job.connection_revision_id, expected_model=None, check_identity=False, unmetered=True)))
    estimate = runtime.estimate(revision_id=revision, user_uid=actor)
    assert estimate.totals.calls == 8 and estimate.totals.images == 32
    run_id = _id("crn")
    pins = comparison_session.execute(text("SELECT version_uid FROM comparison_page_profile "
        "WHERE comparison_page_profile_id=ANY(CAST(:ids AS text[]))"), {"ids": [left, right]}).scalars().all()
    work = ComparisonWorkRepository()
    with session_scope(store._sessions) as session:
        session.execute(text("INSERT INTO stage_chain_run(stage_chain_run_id,stage_pair_id,stage_link_revision_id,input_sha256,"
            "pinned_version_uids,state,actor_user_uid,command_id,kind,with_ai) VALUES(:run,:pair,:revision,:sha,"
            "CAST(:pins AS jsonb),'running',:actor,:command,'full',true)"),
            {"run": run_id, "pair": pair, "revision": revision, "sha": "f" * 64, "pins": json.dumps(pins),
             "actor": actor, "command": _command(session, "start_stage_chain_run")})
        job_id = runtime.prepare(session, run_id=run_id, user_uid=actor, consent=AiConsentInput(estimate.estimate_digest, True))
        session.execute(text("UPDATE stage_chain_run SET comparison_ai_job_id=:job WHERE stage_chain_run_id=:run"),
                        {"job": job_id, "run": run_id})
        work.enqueue(session, project_uid=estimate.scope.project_uid, module="stages", kind="stage_chain",
                     payload={"run_id": run_id}, comparison_ai_job_id=job_id, created_by_user_uid=actor)
        worker = WorkerRegistry().register(session, version="stage-ai-graphic", slots=1)
        if repair:
            effective = _id("slk")
            session.execute(text("INSERT INTO stage_link_revision(stage_link_revision_id,stage_pair_id,revision_no,source,base_revision_id,"
                "input_sha256,actor_user_uid,command_id) VALUES(:id,:pair,2,'automatic',:base,:sha,:actor,:command)"),
                {"id": effective, "pair": pair, "sha": "b" * 64, "actor": actor,
                 "base": revision,
                 "command": _command(session, "apply_stage_sheet_map")})
            session.execute(text("INSERT INTO stage_link_item(stage_link_item_id,stage_link_revision_id,row_no,left_profile_id,"
                "right_profile_id,relation,confidence) VALUES(:id,:revision,1,:left,:right,'paired','manual')"),
                {"id": _id("sli"), "revision": effective, "left": left, "right": right})
            session.execute(text("UPDATE stage_chain_run SET effective_link_revision_id=:revision,repair_cycle_count=1 "
                "WHERE stage_chain_run_id=:run"), {"revision": effective, "run": run_id})
            revision = effective
        item = work.claim(session, worker_id=worker, modules={"stages"}, kinds={"stage_chain"})
        reader = PageProfileReader(store._sessions, None)
        result_id = PairResultRepository().insert(session, project_uid=estimate.scope.project_uid,
            content_key=content_key(estimate.scope.project_uid, reader.get_profile(left), reader.get_profile(right)),
            algo_version="cmp-engine/1", status="different", reasons=[], mask_blob_id=None,
            page_a_profile_id=left, page_b_profile_id=right,
            channels={"geometry": {"state": "checked", "diffs": 5}, "color": {"state": "checked", "diffs": 0}},
            result={"how_compared": {"transform": [1, 0, 0, 1, 0, 0], "dpi": 200}, "differences": [
                {"region_class": "graphic_changed", "layer": "main", "box": {"x": 10 + n * 20, "y": 10, "width": 10, "height": 10}}
                for n in range(5)]})
        stored = PairResultRepository().get(session, result_id)
        status, reason, regions = project_result(stored, left_size=(200, 200), right_size=(200, 200))
        evidence_id = _id("sge")
        link = session.execute(text("SELECT stage_link_item_id FROM stage_link_item WHERE stage_link_revision_id=:revision"),
                               {"revision": revision}).scalar_one()
        session.execute(text("INSERT INTO stage_graphic_evidence(stage_graphic_evidence_id,stage_chain_run_id,stage_link_item_id,"
            "left_profile_id,right_profile_id,comparison_sheet_pair_result_id,status,reason,regions,content_key) "
            "VALUES(:id,:run,:link,:left,:right,:result,:status,:reason,CAST(:regions AS jsonb),:key)"),
            {"id": evidence_id, "run": run_id, "link": link, "left": left, "right": right, "result": result_id,
             "status": status, "reason": reason, "regions": json.dumps(regions), "key": "c" * 64})
    pauses = 0
    for phase in ("review", "classify", "synthesize"):
        for _attempt in range(15):
            with session_scope(store._sessions) as session:
                snapshot = runtime._repo.revision(session, revision)
                plans = runtime._bundles(session, run_id=run_id, snapshot=snapshot, phase=phase, model=route.pinned_model)
                saved = {row["group_id"]: row["progress"] for row in session.execute(text(
                    "SELECT group_id,progress FROM stage_ai_unit WHERE stage_chain_run_id=:run AND kind=:phase"
                ), {"run": run_id, "phase": phase}).mappings()}
            for group, requests, _sha, _key in plans:
                for plan in requests:
                    step = next_step(plan, saved.get(group.review.group_id, {}).get("responses", {}).get(plan.content_key), snapshot)
                    if step is None:
                        continue
                    request, _receipts = graphic.attach(provider, run_id=run_id, plan=step.plan, request=request_for_plan(step.plan))
                    answer = _answer(plan)
                    if phase == "classify":
                        answer["cards"] = [dict(card, **{"class": "REVIEW", "category": "uncertain", "system": "unknown",
                                                         "title": "Графические различия"}) for card in answer["cards"]]
                    adapter.record(request, json.dumps(answer, ensure_ascii=False))
            outcome = runtime.advance(item, run_id=run_id, phase=phase)
            assert not isinstance(outcome, Failed), outcome
            if isinstance(outcome, dict):
                break
            with session_scope(store._sessions) as session:
                job = runtime._jobs().job(session, job_id)
            if job.state == "paused":
                pauses += 1
                assert job.pause_reason == "overrun"
                assert comparison_session.execute(text("SELECT count(*) FROM stage_ai_classification WHERE stage_chain_run_id=:run"),
                                                  {"run": run_id}).scalar_one() == 0
                remaining = runtime.estimate_resume(run_id=run_id, user_uid=actor)
                with session_scope(store._sessions) as session:
                    runtime.resume(session, run_id=run_id, user_uid=actor, consent=AiConsentInput(remaining.estimate_digest, True))
                    session.execute(text("UPDATE stage_chain_run SET state='running',pause_reason=NULL WHERE stage_chain_run_id=:run"), {"run": run_id})
        else:
            raise AssertionError("graphic phase did not finish")
    assert pauses == 1 + int(repair) and adapter.calls == 3
    assert [len(request.images_bytes) for request in adapter.requests] == [8, 2, 0]
    assert comparison_session.execute(text("SELECT count(*) FROM stage_ai_review WHERE stage_chain_run_id=:run"), {"run": run_id}).scalar_one() == 0
    cards = runtime.page(run_id=run_id, kind="classify")[0][0]["cards"]
    assert cards[0]["evidence_ids"] == [evidence_id]
    assert runtime.graphic_window_info(revision_id=revision, run_id=run_id)["remaining_regions"] == 0
    for phase in ("review", "classify", "synthesize"):
        assert isinstance(runtime.advance(item, run_id=run_id, phase=phase), dict)
    assert adapter.calls == 3
    with session_scope(store._sessions) as session:
        assert runtime._jobs().job(session, job_id).state == "completed"
        assert work.finish(session, item.authority, Completed()) == "succeeded"
