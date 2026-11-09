"""The durable runtime branch for windowed-v1 and windowed-global-v1: one provider call per consent window,
saved replies replayed, the run's own stored plan selected (never the environment, never the size), refusal
of a plan whose code changed. test_lifecycle.py pins the legacy four-call procedure; this is the same harness
for the two later plans. Synthetic answers only; no provider, no database.
"""
from __future__ import annotations

import copy
import dataclasses
import json
import sys
from types import SimpleNamespace

import pytest

from auditmanager.comparison.stage_v3 import bridge, consolidation as c, windowed as w
from auditmanager.comparison.stage_v3 import procedures as legacy
from auditmanager.comparison.stage_v3.mode import ENGINE
from auditmanager.comparison.stage_v3.policy import GLOBAL_LIMITS, GLOBAL_VERSION, LIMITS, VERSION, fresh_policy
from auditmanager.comparison.work.model import Failed
from tests.unit.comparison.stage_ai.test_runtime import scene, uid
from tests.unit.stage_v3.recorded_fixture import synthetic_response
from tests.unit.stage_v3.windowed_fixture import mapping_edit, numbered, region, snapshot_of

RUN = uid("crn", 1)


def plan_policy(monkeypatch, version):
    monkeypatch.setenv("AUDITMANAGER_STAGE_V3_PLAN", version)
    return fresh_policy()


def lifecycle(monkeypatch, source, policy, *, edit=None, raise_failures=True):
    runtime, item, repo, jobs, _caller = scene()
    repo.source = dict(source, project_uid=uid("prj", 1), document_uid=uid("doc", 1))
    runtime.test_run["engine"] = ENGINE
    runtime.test_run["project_uid"] = uid("prj", 1)           # the failure path checks the run against the work item
    runtime.test_run["stage_v3_policy"] = policy
    repo.run = lambda _session, _run: runtime.test_run
    jobs.record.consent_no = 1
    calls = []

    class Caller:
        def call(self, _item, _route, request, **_kwargs):
            response, payload = synthetic_response(request)
            if edit is not None:
                answer = json.loads(response.output_text)
                edit(payload["_experimental_procedure"], SimpleNamespace(payload=payload), answer)
                response = dataclasses.replace(response, output_text=json.dumps(answer, ensure_ascii=False))
            calls.append(payload["_experimental_procedure"])
            identity = uid("cmc", len(calls))
            repo.priors[request.request_sha256] = {"state": "completed", "comparison_model_call_id": identity}
            return SimpleNamespace(response=response, call_id=identity, pause=None)

    runtime._caller = Caller()
    lookups = []
    monkeypatch.setattr(bridge, "policy_for_run", lambda _session, run_id: (lookups.append(run_id), policy)[1])

    def saved(_session, _run, bundle=None):
        wanted = bundle or legacy.BUNDLE
        return {row["group_id"]: row["payload"]["v3_result"] for row in repo.units.values()
                if row["state"] == "completed" and "v3_result" in row["payload"]
                and row["payload"].get("prompt_bundle_version") == wanted}

    monkeypatch.setattr(bridge, "results", saved)
    if raise_failures:
        original = runtime._failed

        def fail(*args, **kwargs):
            error = sys.exception()
            if error is not None:
                raise error
            return original(*args, **kwargs)
        runtime._failed = fail
    return SimpleNamespace(runtime=runtime, item=item, repo=repo, jobs=jobs, calls=calls, lookups=lookups, pauses=0)


def run_to_the_end(scene_):
    """Advance the three phases the way the worker does; every provider call needs a fresh consent window."""
    for phase in ("review", "classify", "synthesize"):
        for _ in range(400):
            before = len(scene_.calls)
            result = scene_.runtime.advance(scene_.item, run_id=RUN, phase=phase)
            assert not isinstance(result, Failed), result
            assert len(scene_.calls) <= before + 1, "more than one provider call in a durable yield"
            if scene_.jobs.state == "paused":
                assert len(scene_.calls) == before
                scene_.pauses += 1
                scene_.jobs.record.consent_no += 1
                scene_.jobs.state = "running"
            if isinstance(result, dict):
                break
        else:
            raise AssertionError((phase, "did not finish"))
    return scene_


def final_unit(scene_):
    return next(row for row in scene_.repo.units.values() if row["group_id"] == "v3:final:cards")


def final_cards(scene_):
    return next(row["cards"] for row in scene_.repo.answers.values() if row["group_id"] == "v3:final:cards")


SMALL = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])
TWO_PACKS = snapshot_of([numbered(65, "узел {n} диаметр {n} мм")], [["узел новый диаметр 250 мм"]])
NINE = snapshot_of([["ширина прохода 100 мм"]] * 9, [["ширина прохода 120 мм"]] * 9)
NINE_MAPPING = mapping_edit([region(f"R{n:03d}", [n], [n]) for n in range(1, 10)])


# --- windowed-v1 -----------------------------------------------------------------------------------------------

def test_windowed_run_makes_one_call_per_consent_window_and_publishes_cards_under_its_own_bundle(monkeypatch):
    policy = plan_policy(monkeypatch, VERSION)
    done = run_to_the_end(lifecycle(monkeypatch, SMALL, policy))
    assert done.calls == ["mapper", "miner", "dedupe", "verify"]
    assert done.pauses == 3
    assert done.lookups and set(done.lookups) == {RUN}
    bundles = {row["payload"]["prompt_bundle_version"] for row in done.repo.units.values() if "prompt_bundle_version" in row["payload"]}
    assert bundles == {w.BUNDLE} == {policy["bundle"]}
    cards = final_cards(done)
    assert len(cards) == 1 and cards[0]["experimental"]["plan_version"] == VERSION
    assert cards[0]["experimental"]["parameters"][0]["verification"]["verdict"] == "CONFIRMED"
    report = final_unit(done)["payload"]["source_report"]
    assert report["plan_version"] == VERSION and report["limits"] == LIMITS
    assert "global_consolidation" not in report                              # that is the next revision's block
    assert final_unit(done)["payload"]["coverage"]["semantic_comparison_complete"] is False


def test_windowed_run_over_two_source_packs_pays_for_every_pack_and_every_parameter(monkeypatch):
    policy = plan_policy(monkeypatch, VERSION)
    done = run_to_the_end(lifecycle(monkeypatch, TWO_PACKS, policy))
    assert done.calls == ["mapper", "miner", "miner", "dedupe", "verify", "verify"]
    assert done.pauses == len(done.calls) - 1                                 # each request after the first waits for its own consent
    assert len(final_cards(done)) == 1


def test_a_finished_windowed_run_replays_from_its_saved_replies_without_another_call(monkeypatch):
    policy = plan_policy(monkeypatch, VERSION)
    done = run_to_the_end(lifecycle(monkeypatch, TWO_PACKS, policy))
    before, differences = len(done.calls), copy.deepcopy(done.repo.source["differences"])
    for phase in ("review", "classify", "synthesize"):
        assert isinstance(done.runtime.advance(done.item, run_id=RUN, phase=phase), dict)
    assert len(done.calls) == before == 6 and done.repo.source["differences"] == differences


def test_a_windowed_run_with_unmatched_pages_pays_for_them(monkeypatch):
    policy = plan_policy(monkeypatch, VERSION)
    source = snapshot_of([["ширина прохода 100 мм"], ["ширина прохода 100 мм прочее"]],
                         [["ширина прохода 120 мм"], ["ширина прохода 120 мм иное"]])
    mapping = mapping_edit([region("R001", [1], [1])], unmatched_old=[2], unmatched_new=[2])
    done = run_to_the_end(lifecycle(monkeypatch, source, policy, edit=mapping))
    assert done.calls.count("unmatched") == 2 and done.calls[0] == "mapper"
    assert final_unit(done)["payload"]["coverage"]["unmatched_candidate_search_complete"] is False


# --- the stored plan selects the implementation: not the environment, not the size ---------------------------------------

def test_a_run_keeps_its_stored_plan_when_the_rollback_switch_is_later_set_to_legacy(monkeypatch):
    policy = plan_policy(monkeypatch, VERSION)
    monkeypatch.setenv("AUDITMANAGER_STAGE_V3_PLAN", "legacy")             # a later fresh start would be legacy ...
    done = run_to_the_end(lifecycle(monkeypatch, TWO_PACKS, policy))
    assert done.calls.count("miner") == 2                                   # ... but this run is still windowed
    assert final_cards(done)[0]["experimental"]["plan_version"] == VERSION


def test_a_run_without_stored_authority_is_legacy_whatever_the_environment_says(monkeypatch):
    monkeypatch.setenv("AUDITMANAGER_STAGE_V3_PLAN", GLOBAL_VERSION)
    done = run_to_the_end(lifecycle(monkeypatch, TWO_PACKS, None))
    assert done.calls == ["mapper", "miner", "dedupe", "verify"]
    assert done.calls.count("miner") == 1                                   # the legacy plan sends the whole region at once
    cards = final_cards(done)
    assert "plan_version" not in cards[0]["experimental"]
    assert {row["payload"]["prompt_bundle_version"] for row in done.repo.units.values()
            if "prompt_bundle_version" in row["payload"]} == {legacy.BUNDLE}


def test_a_stored_plan_whose_code_has_changed_is_refused_before_any_paid_call(monkeypatch):
    policy = dict(plan_policy(monkeypatch, VERSION), bundle="0" * 64)
    scene_ = lifecycle(monkeypatch, SMALL, policy, raise_failures=False)
    result = scene_.runtime.advance(scene_.item, run_id=RUN, phase="review")
    assert isinstance(result, Failed) and result.reason == "v3_windowed_policy_changed_requires_fresh_run"
    assert scene_.calls == []


def test_an_unknown_stored_plan_is_refused_before_any_paid_call(monkeypatch):
    policy = dict(plan_policy(monkeypatch, VERSION), plan_version="windowed-v9")
    scene_ = lifecycle(monkeypatch, SMALL, policy, raise_failures=False)
    result = scene_.runtime.advance(scene_.item, run_id=RUN, phase="review")
    assert isinstance(result, Failed)
    assert scene_.calls == []


# --- windowed-global-v1 ----------------------------------------------------------------------------------------------------

def test_global_run_adds_the_consolidator_calls_after_the_local_stages_and_reports_its_coverage(monkeypatch):
    policy = plan_policy(monkeypatch, GLOBAL_VERSION)
    assert policy["plan_version"] == GLOBAL_VERSION and policy["bundle"] == c.BUNDLE and policy["limits"] == GLOBAL_LIMITS
    done = run_to_the_end(lifecycle(monkeypatch, NINE, policy, edit=NINE_MAPPING))
    assert done.calls[0] == "mapper" and done.calls[-2:] == ["consolidate", "consolidate"]
    assert (done.calls.count("miner"), done.calls.count("dedupe"), done.calls.count("verify")) == (9, 2, 9)
    assert done.pauses == len(done.calls) - 1
    bundles = {row["payload"]["prompt_bundle_version"] for row in done.repo.units.values() if "prompt_bundle_version" in row["payload"]}
    assert bundles == {c.BUNDLE}
    report = final_unit(done)["payload"]["source_report"]
    assert report["plan_version"] == GLOBAL_VERSION and report["limits"] == GLOBAL_LIMITS
    manifest = report["global_consolidation"]
    assert manifest["coverage"]["planned_pairs"] == manifest["coverage"]["compared_pairs"] == 8
    assert manifest["groups"] == []                                           # the synthetic Consolidator keeps every pair apart
    cards = final_cards(done)
    assert len(cards) == 9 and {card["experimental"]["plan_version"] for card in cards} == {GLOBAL_VERSION}


def test_global_run_without_candidates_makes_the_same_four_calls_as_windowed(monkeypatch):
    policy = plan_policy(monkeypatch, GLOBAL_VERSION)
    done = run_to_the_end(lifecycle(monkeypatch, SMALL, policy))
    assert done.calls == ["mapper", "miner", "dedupe", "verify"]
    assert final_unit(done)["payload"]["source_report"]["global_consolidation"]["coverage"]["candidate_pairs"] == 0
