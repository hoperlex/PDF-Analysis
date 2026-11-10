"""`CTX-STAND` (ADR-0029 decision 3): the consent carries ``executor_context_policy`` only while the «контекст критику» switch is on.

The real estimate over a stand-in version record (the one database read it makes of the programme is the settings' journal, answered by
``SettingsSession``). What each case would let through if its rule were missing:

* with the switch off or absent -- and for a flag that is not exactly ``true`` -- the consent is the one it was: same members, same digest;
* a run that is not on the stage layout (the legacy route) and a plan-v2 run never carry the policy, whatever the switch says, and the estimate does
  not even read the switch for them;
* with the switch on, under plan v3 on the stage layout, the policy is in the consent, the calls do not grow and the input tokens grow by the
  reservation of every critic call;
* the consent that carries it reads back as a run that may be offered reference data, and one that does not as a run that may not.
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from auditmanager.executors import task_context
from auditmanager.runs import cost_policy
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.stage_plan import start_readiness

from .critic_context_fakes import SettingsSession
from .test_stage_plan_consent import (  # noqa: F401  (registry is a fixture used by name)
    PLAN_ENV, SONNET, Preflight, confirm, draft, estimate, registry, service, source_version,
)

ON = {"enabled": True}
ACTOR = "usr_01M2545JSD15ETSNNV904X991J"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("AUDITMANAGER_EXTENDED_ANALYSIS", PLAN_ENV, "AUDITMANAGER_EXTENDED_COVERAGE"):
        monkeypatch.delenv(name, raising=False)
    Preflight.version = source_version()


def priced(registry, session, *, plan=draft, version_plan="v3", monkeypatch):
    monkeypatch.setenv(PLAN_ENV, version_plan)
    value = service(registry).estimate_run(session, version_uid="ver_01M2545JSD15ETSNNV904X991J", stage_plan=plan() if plan else None)
    return value


def test_with_the_switch_off_or_absent_the_consent_is_the_one_it_was(registry, monkeypatch):
    absent = SettingsSession()
    off = SettingsSession({"critic_context": {"enabled": False}})
    first, second = (priced(registry, session, monkeypatch=monkeypatch) for session in (absent, off))
    assert absent.asked == ["critic_context"] and off.asked == ["critic_context"], "the estimate reads the switch, and only it"
    assert first.estimate_digest == second.estimate_digest and first.as_dict() == second.as_dict()
    assert "executor_context_policy" not in first.approve(confirm(first, 0))["extended_review"]


@pytest.mark.parametrize("flag", [{"enabled": "true"}, {"enabled": 1}, {"enabled": None}, {}, {"on": True}])
def test_a_flag_that_is_not_exactly_true_is_off(registry, monkeypatch, flag):
    session = SettingsSession({"critic_context": flag})
    value = priced(registry, session, monkeypatch=monkeypatch)
    baseline = priced(registry, SettingsSession(), monkeypatch=monkeypatch)
    assert value.estimate_digest == baseline.estimate_digest
    assert "executor_context_policy" not in value.approve(confirm(value, 0))["extended_review"]


def test_with_the_switch_on_the_policy_joins_the_consent_the_calls_do_not_grow_and_the_critics_tokens_are_reserved(registry, monkeypatch):
    off = priced(registry, SettingsSession(), monkeypatch=monkeypatch)
    on = priced(registry, SettingsSession({"critic_context": ON}), monkeypatch=monkeypatch)
    consent = on.approve(confirm(on, 0))["extended_review"]
    assert consent["executor_context_policy"] == task_context.executor_context_policy()
    assert on.estimate_digest != off.estimate_digest, "another consent, because it holds another policy"
    off_total, on_total = off.as_dict(), on.as_dict()
    assert on_total["calls"] == off_total["calls"] and on_total["output_tokens"] == off_total["output_tokens"]
    review_calls = consent["max_windows"] * consent["phase_call_limits"]["finding_review"]
    review_calls += consent.get("global_cross_window_policy", {}).get("call_limits", {}).get("finding_review", 0)
    assert review_calls > 0
    assert on_total["input_tokens"] - off_total["input_tokens"] == review_calls * 5_000
    # and the same reservation sits on the review row's model: the plan prices by model, and the lines add up to the total
    assert sum(line["input_tokens"] for line in on_total["models"]) == on_total["input_tokens"]


def test_the_critic_row_alone_carries_the_reservation(registry, monkeypatch):
    off = priced(registry, SettingsSession(), monkeypatch=monkeypatch)
    on = priced(registry, SettingsSession({"critic_context": ON}), monkeypatch=monkeypatch)
    review_model = on.stage_plan.cell("review:main").model_id
    delta = {line["model_id"]: line["input_tokens"] for line in on.as_dict()["models"]}
    base = {line["model_id"]: line["input_tokens"] for line in off.as_dict()["models"]}
    changed = {model for model in delta if delta[model] != base[model]}
    assert changed == {review_model}


def test_a_plan_v2_run_never_carries_the_policy_and_the_switch_is_not_even_read(registry, monkeypatch):
    session = SettingsSession({"critic_context": ON})
    value = priced(registry, session, version_plan="v2", monkeypatch=monkeypatch)
    assert "executor_context_policy" not in value.approve(confirm(value, 0)).get("extended_review", {}) and session.asked == []


def test_a_legacy_run_never_carries_the_policy_and_the_switch_is_not_even_read(registry, monkeypatch):
    session = SettingsSession({"critic_context": ON})
    value = priced(registry, session, plan=None, monkeypatch=monkeypatch)
    assert "executor_context_policy" not in value.approve(confirm(value, value.as_dict()["recommended_ceiling_micros"])).get("extended_review", {})
    assert session.asked == [], "a legacy run is offered no reference data (temporary decision 1), so its estimate asks no question of it"


def test_the_readiness_of_a_start_reads_through_the_same_estimate(registry, monkeypatch):
    monkeypatch.setenv(PLAN_ENV, "v3")
    session = SettingsSession({"critic_context": ON})
    answer = start_readiness(service(registry), session, draft(), version_uid="ver_01M2545JSD15ETSNNV904X991J")
    assert answer["extended_plan"] == "v3" and session.asked == ["critic_context"]


# -- the consent, read back by the stand -----------------------------------------------------------------------------


class Command:
    def __init__(self, outcome):
        self.state, self.outcome = "succeeded", outcome


def facts_of(monkeypatch, value):
    """What the stand reads of the run that the estimate ``value`` was accepted for: the real ``read_run_cost_policy`` over its real consent."""
    approved = value.approve(confirm(value, 0), actor_user_uid=ACTOR)
    run = NS(run_id="run_01M2545JSD15ETSNNV904X991K", command_id="cmd_01M2545JSD15ETSNNV904X991C", binding_state="pending",
             connection_revision_id=None, executor_group_revision_id=None, stage_plan=value.stage_plan.to_json())
    monkeypatch.setattr(cost_policy, "CommandRepository", lambda: NS(get=lambda session, command_id: Command({"run_id": run.run_id, "cost_consent": approved})))
    monkeypatch.setattr(cost_policy, "RunRepository", lambda: NS(get=lambda session, run_id: run))
    return task_context.read_run_context_facts(None, run.run_id)


def test_the_consent_that_carries_the_policy_reads_back_as_a_run_that_may_be_offered_reference_data(registry, monkeypatch):
    on = priced(registry, SettingsSession({"critic_context": ON}), monkeypatch=monkeypatch)
    facts = facts_of(monkeypatch, on)
    assert (facts.stage_plan, facts.plan_version, facts.section) == (True, "extended-review-v3", "AI")
    assert facts.policy == task_context.executor_context_policy() and task_context.context_eligible(facts)


def test_the_consent_without_it_reads_back_as_a_run_that_may_not(registry, monkeypatch):
    off = priced(registry, SettingsSession(), monkeypatch=monkeypatch)
    facts = facts_of(monkeypatch, off)
    assert facts.stage_plan and facts.plan_version == "extended-review-v3" and facts.policy is None
    assert not task_context.context_eligible(facts)


def test_a_consent_that_cannot_be_read_states_nothing_and_grants_nothing(monkeypatch):
    run = NS(run_id="run_01M2545JSD15ETSNNV904X991K", command_id=None, binding_state="pending", connection_revision_id=None,
             executor_group_revision_id=None, stage_plan=draft().freeze(layout.STAGE_ROWS).to_json())
    monkeypatch.setattr(cost_policy, "RunRepository", lambda: NS(get=lambda session, run_id: run))
    facts = task_context.read_run_context_facts(None, run.run_id)  # a planned run with no consent: the reader refuses it
    assert facts == task_context.NO_FACTS and not task_context.context_eligible(facts)
