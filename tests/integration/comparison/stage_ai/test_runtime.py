"""Recorded C4 SQL/job/spend replay on a rolled-back isolated PostgreSQL fixture."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import text

from auditmanager.comparison.ai_jobs.model import AiConsentInput
from auditmanager.comparison.ai_jobs.recorded import RecordedAnswers
from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow, Word
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.comparison.stage_ai import StageAiRuntime
from auditmanager.comparison.stage_ai.runtime import request_for_plan
from auditmanager.comparison.work.model import Completed, Failed, Yielded
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import new_ulid
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.ai_jobs.ai_jobs_support import recorded_route
from tests.integration.comparison.stage_text.test_store import _batch, _command, _seed
from tests.support.accounts import complete_expert_account


def _id(prefix):
    return f"{prefix}_{new_ulid()}"


def _profiles(session, left, right, *, empty=False):
    values = {}
    for row in session.execute(text(
        "SELECT comparison_page_profile_id,version_uid,content_key FROM comparison_page_profile "
        "WHERE comparison_page_profile_id=ANY(CAST(:profiles AS text[]))"
    ), {"profiles": [left, right]}).all():
        words = () if empty else (Word(10, 10, 80, 18,
                    "Нагрузка 10 кВт" if row[0] == left else "Нагрузка 20 кВт"),)
        values[str(row[0])] = PageProfileData(
            PageProfileRow(str(row[0]), str(row[1]), 1, str(row[2]), "test", "ready", None,
                           {}, "profile-archive-test", None, None, datetime.now(timezone.utc)),
            100, 100, 0, not empty, empty, None, words=words,
        )
    return SimpleNamespace(read_page_profile=lambda profile_id: values[profile_id])


def _answer(plan):
    source = plan.payload
    if plan.phase == "review":
        return {"group_id": plan.group_id, "chunk_id": plan.unit_key, "source_sha256": plan.source_sha256,
                "decisions": [{"left_fragment_ids": item["left_fragment_ids"],
                    "right_fragment_ids": item["right_fragment_ids"], "status": "CHANGED", "confidence": "high",
                    "summary": "Нагрузка 10 кВт → 20 кВт", "reason": "Изменён исходный текст.",
                    "actual_right_profile_ids": []} for item in source["items"]]}
    if plan.phase == "classify":
        return {"group_id": plan.group_id, "source_sha256": plan.source_sha256,
                "cards": [{"class": "PROJECT_CHANGE", "category": "electrical_load",
                    "title": "Изменена нагрузка", "system": "electrical",
                    "evidence_ids": [item["evidence_id"]]} for item in source["atomic_evidence"]]}
    return {"group_id": plan.group_id, "source_sha256": plan.source_sha256,
            "evidence_ids": [item["evidence_id"] for item in source["atomic_evidence"]],
            "decision": "INSUFFICIENT_CONTEXT", "type": "UNRESOLVED_HIGH_LEVEL_CHANGE",
            "title": "Требуется проверка", "reason": "Контекста недостаточно."}


def test_recorded_runtime_uses_shared_job_and_spend_once(comparison_session):
    store, pair, revision, _actor, left, right = _seed(comparison_session)
    actor = str(complete_expert_account(comparison_session, "stage-ai-runtime").user_uid)
    route = recorded_route(comparison_session.connection(), "comparison_stage_review")
    adapter = RecordedAnswers()
    routes = SimpleNamespace(route_for=lambda _session, job: CallRoute(
        adapter, job.pinned_model, connection_revision_id=job.connection_revision_id,
        expected_model=None, check_identity=False, unmetered=True,
    ))
    runtime = StageAiRuntime(store._sessions, routes=routes, provider_mode="recorded",
                             profile_reader=_profiles(comparison_session, left, right))
    estimate = runtime.estimate(revision_id=revision, user_uid=actor)
    assert estimate.totals.calls == 3
    fragments, manifest, raw = _batch(left, right)
    store.write(pair_id=pair, revision_id=revision, fragments=fragments,
                expected_keys=manifest, raw=raw, hints=())
    run_id = _id("crn")
    pins = comparison_session.execute(text(
        "SELECT version_uid FROM comparison_page_profile WHERE comparison_page_profile_id=ANY(CAST(:ids AS text[]))"
    ), {"ids": [left, right]}).scalars().all()
    with session_scope(store._sessions) as session:
        session.execute(text(
            "INSERT INTO stage_chain_run(stage_chain_run_id,stage_pair_id,stage_link_revision_id,input_sha256, "
            "pinned_version_uids,state,actor_user_uid,command_id,kind,with_ai) "
            "VALUES(:run,:pair,:revision,:sha,CAST(:pins AS jsonb),'running',:actor,:command,'full',true)"
        ), {"run": run_id, "pair": pair, "revision": revision, "sha": "f" * 64,
            "pins": json.dumps(pins), "actor": actor, "command": _command(session, "start_stage_chain_run")})
        savepoint = session.begin_nested()
        rolled_back_job = runtime.prepare(session, run_id=run_id, user_uid=actor,
                                          consent=AiConsentInput(estimate.estimate_digest, True))
        savepoint.rollback()
        assert session.execute(text(
            "SELECT count(*) FROM comparison_ai_job WHERE comparison_ai_job_id=:job"
        ), {"job": rolled_back_job}).scalar_one() == 0
        job_id = runtime.prepare(session, run_id=run_id, user_uid=actor,
                                 consent=AiConsentInput(estimate.estimate_digest, True))
        assert job_id
        session.execute(text("UPDATE stage_chain_run SET comparison_ai_job_id=:job WHERE stage_chain_run_id=:run"),
                        {"job": job_id, "run": run_id})
        work = ComparisonWorkRepository()
        queued = work.enqueue(session, project_uid=estimate.scope.project_uid, module="stages", kind="stage_ai_test_chain",
                              payload={"run_id": run_id}, comparison_ai_job_id=job_id, created_by_user_uid=actor)
        worker_id = WorkerRegistry().register(session, version="stage-ai-test", slots=1)
    with session_scope(store._sessions) as session:
        item = work.claim(session, worker_id=worker_id, modules={"stages"}, kinds={"stage_ai_test_chain"})
    assert item is not None and item.work_id == queued.work_id
    for phase in ("review", "classify", "synthesize"):
        with session_scope(store._sessions) as session:
            run = runtime._repo.run(session, run_id)
            source = runtime._repo.revision(session, run["revision_id"])
            bundles = runtime._bundles(session, run_id=run_id, snapshot=source,
                                       phase=phase, model=route.pinned_model)
        for _group, plans, _sha, _key in bundles:
            for plan in plans:
                adapter.record(request_for_plan(plan), json.dumps(_answer(plan), ensure_ascii=False))
        for _attempt in range(4):
            outcome = runtime.advance(item, run_id=run_id, phase=phase)
            assert not isinstance(outcome, Failed), outcome
            if isinstance(outcome, dict):
                assert outcome["completed"] == 1
                break
            assert isinstance(outcome, Yielded)
        else:
            raise AssertionError("phase did not finish")
    assert adapter.calls == 3
    for phase in ("review", "classify", "synthesize"):
        assert isinstance(runtime.advance(item, run_id=run_id, phase=phase), dict)
    assert adapter.calls == 3
    for table in ("stage_ai_review", "stage_ai_classification", "stage_ai_synthesis"):
        assert comparison_session.execute(text(
            f"SELECT count(*) FROM {table} WHERE stage_chain_run_id=:run"
        ), {"run": run_id}).scalar_one() == 1
    assert comparison_session.execute(text(
        "SELECT count(*) FROM comparison_model_call c JOIN comparison_work w "
        "ON w.comparison_work_id=c.comparison_work_id WHERE w.comparison_ai_job_id=:job AND c.state='completed'"
    ), {"job": job_id}).scalar_one() == 3
    assert comparison_session.execute(text(
        "SELECT state FROM comparison_ai_job WHERE comparison_ai_job_id=:job"
    ), {"job": job_id}).scalar_one() == "completed"
    assert comparison_session.execute(text(
        "SELECT count(*) FROM stage_text_difference WHERE stage_link_revision_id=:revision"
    ), {"revision": revision}).scalar_one() == len(raw.differences)
    with session_scope(store._sessions) as session:
        assert work.finish(session, item.authority, Completed()) == "succeeded"


def test_no_text_records_source_pins_without_job_or_ai_verdict(comparison_session):
    store, pair, revision, _actor, left, right = _seed(comparison_session)
    actor = str(complete_expert_account(comparison_session, "stage-ai-no-text").user_uid)
    recorded_route(comparison_session.connection(), "comparison_stage_review")
    runtime = StageAiRuntime(store._sessions, profile_reader=_profiles(comparison_session, left, right, empty=True))
    estimate = runtime.estimate(revision_id=revision, user_uid=actor)
    assert estimate.totals.calls == 0
    run_id = _id("crn")
    pins = comparison_session.execute(text(
        "SELECT version_uid FROM comparison_page_profile WHERE comparison_page_profile_id=ANY(CAST(:ids AS text[]))"
    ), {"ids": [left, right]}).scalars().all()
    with session_scope(store._sessions) as session:
        session.execute(text(
            "INSERT INTO stage_chain_run(stage_chain_run_id,stage_pair_id,stage_link_revision_id,input_sha256, "
            "pinned_version_uids,state,actor_user_uid,command_id,kind,with_ai) "
            "VALUES(:run,:pair,:revision,:sha,CAST(:pins AS jsonb),'running',:actor,:command,'full',true)"
        ), {"run": run_id, "pair": pair, "revision": revision, "sha": "f" * 64,
            "pins": json.dumps(pins), "actor": actor, "command": _command(session, "start_stage_chain_run")})
        assert runtime.prepare(session, run_id=run_id, user_uid=actor, consent=None) is None
        assert runtime.prepare(session, run_id=run_id, user_uid=actor, consent=None) is None
        work = ComparisonWorkRepository()
        work.enqueue(session, project_uid=estimate.scope.project_uid, module="stages", kind="stage_ai_test_empty",
                     payload={"run_id": run_id}, created_by_user_uid=actor)
        worker_id = WorkerRegistry().register(session, version="stage-ai-test", slots=1)
    with session_scope(store._sessions) as session:
        item = work.claim(session, worker_id=worker_id, modules={"stages"}, kinds={"stage_ai_test_empty"})
    for phase in ("review", "classify", "synthesize"):
        result = runtime.advance(item, run_id=run_id, phase=phase)
        assert isinstance(result, dict) and result["text_not_checked"] == 1
    unit = comparison_session.execute(text(
        "SELECT payload,progress FROM stage_ai_unit WHERE stage_chain_run_id=:run"
    ), {"run": run_id}).mappings().one()
    assert len(unit["payload"]["profiles"]) == 2
    assert len(unit["progress"]["pinned_model"]) > 0
    assert all(profile["content_key"] for profile in unit["payload"]["profiles"])
    assert comparison_session.execute(text(
        "SELECT count(*) FROM stage_ai_review WHERE stage_chain_run_id=:run"
    ), {"run": run_id}).scalar_one() == 0
    assert comparison_session.execute(text(
        "SELECT count(*) FROM stage_graphic_evidence WHERE stage_chain_run_id=:run AND status='not_checked'"
    ), {"run": run_id}).scalar_one() == 1
    assert comparison_session.execute(text(
        "SELECT comparison_ai_job_id FROM stage_chain_run WHERE stage_chain_run_id=:run"
    ), {"run": run_id}).scalar_one() is None
    with session_scope(store._sessions) as session:
        assert work.finish(session, item.authority, Completed()) == "succeeded"
