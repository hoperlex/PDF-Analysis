"""Explicit, rolled-back PostgreSQL smoke: python -m tests.unit.stage_v3.db_smoke [plan ...].

`plan` is one of legacy, windowed-v1, windowed-global-v1 (default: legacy). Each plan is walked on its own connection
that is rolled back at the end: the run is started under that plan exactly as a start command freezes it (the switch is
set, `fresh_policy()` is written into the command outcome as `stage_v3_policy`), then estimated, consented window by
window, advanced call by call through durable units, reviewed into cards and read back as progress.
Uses existing lane DATABASE_URL, durable job/spend/units, synthetic responses only.
This is not collected as a unit test and never starts infrastructure.
"""
import json
import os
import sys
import traceback
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.comparison.ai_jobs.model import AiConsentInput
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.comparison.stage_ai.runtime import StageAiRuntime
from auditmanager.comparison.stage_review.service import StageReviewService
from auditmanager.comparison.stage_v3.mode import ENGINE, experimental_progress
from auditmanager.comparison.stage_v3.policy import bundle_for, fresh_policy, policy_for_run
from auditmanager.comparison.work.model import Failed
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.stage_text.test_store import _seed, _command, _id
from tests.integration.comparison.stage_ai.test_runtime import _profiles
from tests.integration.comparison.ai_jobs.ai_jobs_support import recorded_route
from tests.support.accounts import complete_expert_account
from auditmanager.comparison.stage_text.fragments import extract_fragments
from auditmanager.comparison.stage_text import SheetLink, build_raw_differences
from auditmanager.analysis.public import ProviderMode
from tests.unit.stage_v3.recorded_fixture import synthetic_response


PLANS = ("legacy", "windowed-v1", "windowed-global-v1")
#: The first group of the plan: the legacy Mapper sees whole pages, the windowed plans a bounded catalogue.
MAPPER_GROUP = {"legacy": "v3:mapper:all", "windowed-v1": "v3:mapper:catalogue", "windowed-global-v1": "v3:mapper:catalogue"}
#: One page per side, one changed parameter: every plan needs Mapper, one Miner pack, Dedupe and one Verification.
EXPECTED_CALLS = {"legacy": ["mapper", "miner", "dedupe", "verify"], "windowed-v1": ["mapper", "miner", "dedupe", "verify"],
                  "windowed-global-v1": ["mapper", "miner", "dedupe", "verify"]}


def main(plan="legacy"):
    assert plan in PLANS, plan
    os.environ["AUDITMANAGER_STAGE_V3_PLAN"] = plan          # the fresh-start switch the estimate and the start command read
    selected = fresh_policy()                                # None for legacy
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
    with engine.connect() as connection:
        transaction = connection.begin()
        sessions = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        with sessions() as session:
            store, pair, revision, _actor, left, right = _seed(session)
            actor = str(complete_expert_account(session, "v3-recorded-smoke").user_uid)
            route = recorded_route(session.connection(), "comparison_stage_review")
            reader = _profiles(session, left, right)
            fragments = tuple(f for pid, side in ((left, "left"), (right, "right"))
                              for f in extract_fragments(reader.read_page_profile(pid), side=side))
            manifest = {pid: frozenset(f.content_key for f in fragments if f.profile_id == pid) for pid in (left, right)}
            raw = build_raw_differences([SheetLink(left, right)], fragments, {left: (100, 100), right: (100, 100)}, manifest)
            session.commit()
        store.write(pair_id=pair, revision_id=revision, fragments=fragments, expected_keys=manifest, raw=raw, hints=())

        class Adapter:
            provider_mode = ProviderMode.RECORDED
            calls = []

            def complete(self, request):
                response, payload = synthetic_response(request)
                self.calls.append(payload["_experimental_procedure"])
                return response

        adapter = Adapter()
        routes = SimpleNamespace(route_for=lambda _s, job: CallRoute(adapter, job.pinned_model,
            connection_revision_id=job.connection_revision_id, expected_model=None, check_identity=False, unmetered=True))
        runtime = StageAiRuntime(sessions, routes=routes, provider_mode="recorded", profile_reader=reader)
        with sessions() as session:
            run_id, command_id = _id("crn"), _command(session, "start_stage_chain_run")
            session.execute(text("UPDATE command_record SET outcome=CAST(:outcome AS jsonb) WHERE command_id=:id"),
                            {"outcome": json.dumps({"engine": ENGINE, **({"stage_v3_policy": selected} if selected else {})}), "id": command_id})
            pins = session.execute(text("SELECT version_uid FROM comparison_page_profile WHERE comparison_page_profile_id=ANY(CAST(:ids AS text[]))"), {"ids": [left, right]}).scalars().all()
            session.execute(text("INSERT INTO stage_chain_run(stage_chain_run_id,stage_pair_id,stage_link_revision_id,input_sha256,pinned_version_uids,state,actor_user_uid,command_id,kind,with_ai) VALUES(:run,:pair,:revision,:sha,CAST(:pins AS jsonb),'running',:actor,:command,'full',true)"),
                {"run": run_id, "pair": pair, "revision": revision, "sha": "f" * 64,
                 "pins": json.dumps(pins), "actor": actor, "command": command_id})
            session.commit()
        estimate = runtime.estimate(revision_id=revision, user_uid=actor, engine=ENGINE)
        assert estimate.totals.calls == 1
        with sessions() as session:
            job_id = runtime.prepare(session, run_id=run_id, user_uid=actor,
                                    consent=AiConsentInput(estimate.estimate_digest, True), engine=ENGINE)
            session.execute(text("UPDATE stage_chain_run SET comparison_ai_job_id=:job WHERE stage_chain_run_id=:run"), {"job": job_id, "run": run_id})
            work = ComparisonWorkRepository()
            work.enqueue(session, project_uid=estimate.scope.project_uid, module="stages", kind="stage_chain", payload={"run_id": run_id}, comparison_ai_job_id=job_id, created_by_user_uid=actor)
            worker_id = WorkerRegistry().register(session, version="v3-recorded-smoke", slots=1)
            session.commit()
        with sessions() as session:
            item = work.claim(session, worker_id=worker_id, modules={"stages"}, kinds={"stage_chain"})
            session.commit()
        pauses = 0
        for phase in ("review", "classify", "synthesize"):
            for _ in range(60):
                before = len(adapter.calls)
                outcome = runtime.advance(item, run_id=run_id, phase=phase)
                assert len(adapter.calls) <= before + 1, "more than one call in a durable yield"
                assert not isinstance(outcome, Failed), (phase, outcome)
                with sessions() as session:
                    job = runtime._jobs(runtime._method(ENGINE)).job(session, job_id)
                    if job.state == "paused":
                        assert job.pause_reason == "overrun", job.pause_reason
                        pauses += 1
                        remaining = runtime.estimate_resume(run_id=run_id, user_uid=actor)
                        assert remaining.totals.calls == 1
                        runtime.resume(session, run_id=run_id, user_uid=actor,
                                       consent=AiConsentInput(remaining.estimate_digest, True))
                        session.execute(text("UPDATE stage_chain_run SET state='running',pause_reason=NULL WHERE stage_chain_run_id=:run"), {"run": run_id})
                        session.commit()
                if isinstance(outcome, dict):
                    break
            else:
                raise AssertionError((phase, "did not terminate"))
        assert adapter.calls == EXPECTED_CALLS[plan], adapter.calls
        assert pauses == len(adapter.calls) - 1, pauses
        review = StageReviewService(sessions)
        outcome = review.advance(item, run_id)
        with sessions() as session:
            # The durable record of the plan: stored with the start command, and every unit saved under its bundle.
            assert policy_for_run(session, run_id) == selected, (plan, policy_for_run(session, run_id))
            bundle = bundle_for(selected)
            units = session.execute(text("SELECT group_id,state,progress->>'prompt_bundle_version' AS bundle FROM stage_ai_unit "
                                         "WHERE stage_chain_run_id=:run AND group_id LIKE 'v3:%'"), {"run": run_id}).mappings().all()
            assert all(row["state"] == "completed" for row in units), (plan, units)
            plans = [row for row in units if row["group_id"] != "v3:window:consent"]     # the consent window is bookkeeping, no bundle
            assert any(row["group_id"] == "v3:window:consent" for row in units), (plan, units)
            assert all(row["bundle"] == bundle for row in plans), (plan, units)
            groups = {row["group_id"] for row in plans}
            assert MAPPER_GROUP[plan] in groups and "v3:final:cards" in groups, (plan, groups)
            assert len([g for g in groups if g.startswith("v3:miner:")]) == 1, (plan, groups)
            progress = experimental_progress(session, run_id)
            assert progress["status"] == "completed", progress
            assert progress["plan_version"] == (selected["plan_version"] if selected else "native-text-v3/1"), progress
            assert progress["limits"] == (selected["limits"] if selected else progress["limits"]), progress
            assert progress["completed_units"] == progress["planned_units"] and progress["pending_units"] == 0, progress
            assert ("Consolidator" in [p["name"] for p in progress["procedures"]]) == (plan == "windowed-global-v1"), progress
        cards, _, _ = review.page(run_id)
        assert len(cards) == 1, cards
        assert cards[0]["experimental"]["parameters"][0]["verification"]["verdict"] == "CONFIRMED"
        print(f"V3 DB smoke PASS [{plan}]: {len(adapter.calls)} synthetic calls {adapter.calls}, {pauses} fresh consents, "
              f"{len(plans)} plan units under bundle {bundle[:12]}, 1 typed REVIEW card; source transaction rolls back")
        transaction.rollback()
    engine.dispose()


if __name__ == "__main__":
    failed = []
    for chosen in sys.argv[1:] or ["legacy"]:       # every plan runs even after a failure, so one run reports them all
        try:
            main(chosen)
        except Exception:
            traceback.print_exc()
            print(f"V3 DB smoke FAIL [{chosen}]")
            failed.append(chosen)
    sys.exit(1 if failed else 0)
