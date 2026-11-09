"""`HOSTS-LAYOUT-01`: consent v2 and the readiness of a start -- priced by model, bound to the plan, the models and the access.

The estimate is the real :class:`~auditmanager.runs.preflight.RunCostPreflight`; only the version record is a stand-in. What it prices is
compared with the legacy estimate of the same version (the totals must agree when every cell keeps today's constants) and with itself under
another access, another limit and another set of rows.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace as NS

import pytest

from auditmanager.analysis.public import (
    ProviderConfig, ProviderMode, model_rate_sha256, pinned_models, project_parameters_policy, require_approved_model,
)
from auditmanager.analysis.text.binding import CallBinding
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.api.schemas import models
from auditmanager.bootstrap.stage_plan_service import StagePlanService
from auditmanager.runs import cost_policy, preflight
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.cost_policy import read_run_cost_policy
from auditmanager.runs.stage_plan import ModelAvailability, StagePlanDraft, start_readiness
from auditmanager.shared.errors import DomainError, ErrorCode

from .stage_layout_fakes import ADMIN, API_ONLY, NOWHERE, SUBSCRIPTION, FakeSessions, MemoryCommands, MemoryStore, everything, with_revision

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
REVISION = "slr_01M2545JSD15ETSNNV904X991J"
PLAN_ENV = "AUDITMANAGER_EXTENDED_ANALYSIS_PLAN"
SONNET, OPUS = "claude-sonnet-5-5", "claude-opus-5-5"


@pytest.fixture
def registry():
    return load_text_profile_registry()


def source_version(section="AI", count=300_000, pages=100):
    return NS(version_uid=VERSION, sha256="a" * 64, text_character_count=count, recognised_character_count=0, page_count=pages,
              upload_kind="portal_bundle",
              classification=NS(version_uid=VERSION, confirmed_by_user_uid="usr_01M2545JSD15ETSNNV904X991J", section_code=section,
                                project_stage="P", revision=1),
              manifest=(NS(role="source.document", blob_id="blob_sha256_" + "b" * 64),))


class Preflight(preflight.RunCostPreflight):
    """The real estimate over a stand-in version record (the database read is the one thing replaced)."""

    version = source_version()

    def _source(self, session, version_uid, version=None, *, parse_native_text=True):
        return super()._source(session, version_uid, self.version, parse_native_text=parse_native_text)


def service(registry, **kwargs) -> Preflight:
    return Preflight(section_profiles=registry.section_profiles(), text_profiles=registry,
                     provider_config=ProviderConfig(ProviderMode.RECORDED, SONNET, 1.0, None, False), provider_mode="recorded", **kwargs)


def draft(served: dict[str, ModelAvailability] | None = None, kit: str = "claude_only") -> StagePlanDraft:
    cells = layout.preset_cells(kit)
    served = served if served is not None else {c.model_id: SUBSCRIPTION for c in cells}
    return StagePlanDraft(REVISION, kit, cells, served)


def with_limits(base: StagePlanDraft, **limits: int) -> StagePlanDraft:
    return replace(base, cells=tuple(replace(c, max_output_tokens=limits.get(c.row, c.max_output_tokens)) for c in base.cells))


def estimate(policy, plan=None, **kwargs):
    return policy.estimate_run(None, version_uid=VERSION, stage_plan=plan, **kwargs)


def totals(value):
    d = value.as_dict()
    return d["calls"], d["input_tokens"], d["output_tokens"]


def confirm(value, cap=0):
    return {"estimate_digest": value.estimate_digest, "ceiling_micros": cap, "confirmed": True}


@pytest.fixture(autouse=True)
def default_environment(monkeypatch):
    for name in ("AUDITMANAGER_EXTENDED_ANALYSIS", PLAN_ENV, "AUDITMANAGER_EXTENDED_COVERAGE"):
        monkeypatch.delenv(name, raising=False)
    Preflight.version = source_version()


# --- the estimate by model -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("plan_env", ["v3", "v2"])
@pytest.mark.parametrize(("section", "count", "pages"), [("AI", 500, 1), ("AR", 300_000, 100), ("AI", 5_000_000, 400)])
def test_with_todays_constants_the_plan_prices_the_same_work_as_the_legacy_estimate(registry, monkeypatch, plan_env, section, count, pages):
    monkeypatch.setenv(PLAN_ENV, plan_env)
    policy = service(registry)
    Preflight.version = source_version(section, count, pages)
    legacy, planned = estimate(policy, None), estimate(policy, draft())
    # One difference, by design: the parameter passport's calls carry the cross-check cell's answer limit (6000) and not the consented
    # policy's 8000, so the plan prices what the request will carry. Everything else is the legacy estimate's, call for call.
    parameters = project_parameters_policy(section, full_coverage=True, candidate_refusals=True)
    passport_difference = 0 if plan_env == "v2" else parameters["max_calls"] * (parameters["output_tokens"] - 6000)
    assert totals(planned) == (totals(legacy)[0], totals(legacy)[1], totals(legacy)[2] - passport_difference)
    assert planned.stage_plan is not None and legacy.stage_plan is None
    # the work is split over the models of the cells: every line is a model of the plan and the lines add up to the total
    lines = planned.as_dict()["models"]
    assert {line["model_id"] for line in lines} == set(planned.stage_plan.models)
    assert (sum(l["calls"] for l in lines), sum(l["input_tokens"] for l in lines), sum(l["output_tokens"] for l in lines)) == totals(planned)


def test_the_rows_a_run_calls_are_the_rows_of_its_plan(registry, monkeypatch):
    policy = service(registry)
    assert estimate(policy, draft()).stage_plan.rows == layout.STAGE_ROWS
    monkeypatch.setenv(PLAN_ENV, "v2")
    assert estimate(policy, draft()).stage_plan.rows == ("text", "blocks", "cross_check", "norms")
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS", "0")
    only_text = estimate(policy, draft())
    assert only_text.stage_plan.rows == ("text",) and [l["model_id"] for l in only_text.as_dict()["models"]] == [SONNET]
    assert policy.stage_rows_in_use() == ("text",)


def test_a_model_is_priced_at_its_own_rates_and_a_subscription_costs_nothing(registry):
    policy = service(registry)
    prices = {pin.model_id: pin for pin in pinned_models()}
    everywhere_api = estimate(policy, draft({m: API_ONLY for m in prices}))
    by_model = {line["model_id"]: line for line in everywhere_api.as_dict()["models"]}
    assert set(by_model) == {SONNET, OPUS}
    for model, line in by_model.items():
        assert line["access"] == "api" and line["rate_sha256"] == model_rate_sha256(prices[model])
        assert line["estimated_cost_micros"] == preflight.estimated_micros(prices[model], line["input_tokens"], line["output_tokens"]) > 0
    assert everywhere_api.as_dict()["estimated_cost_micros"] == sum(l["estimated_cost_micros"] for l in by_model.values())
    assert everywhere_api.as_dict()["billing"] == "metered" and everywhere_api.stage_plan.access == "api"
    free = estimate(policy, draft({SONNET: SUBSCRIPTION, OPUS: SUBSCRIPTION}))
    assert free.as_dict()["estimated_cost_micros"] == 0 and free.as_dict()["recommended_ceiling_micros"] == 0
    assert free.as_dict()["billing"] == "unmetered" and {l["estimated_cost_micros"] for l in free.as_dict()["models"]} == {0}
    mixed = estimate(policy, draft({SONNET: SUBSCRIPTION, OPUS: API_ONLY}))
    lines = {l["model_id"]: l for l in mixed.as_dict()["models"]}
    assert mixed.as_dict()["billing"] == "mixed" and lines[SONNET]["estimated_cost_micros"] == 0
    assert mixed.as_dict()["estimated_cost_micros"] == lines[OPUS]["estimated_cost_micros"] == by_model[OPUS]["estimated_cost_micros"]
    assert mixed.as_dict()["recommended_ceiling_micros"] > 0
    models.RunCostEstimate.model_validate(mixed.as_dict())


def test_a_cell_limit_moves_the_estimate_and_its_digest(registry):
    policy = service(registry)
    base, wider = estimate(policy, draft()), estimate(policy, with_limits(draft(), norms=20_000))
    assert wider.as_dict()["output_tokens"] > base.as_dict()["output_tokens"]
    assert wider.estimate_digest != base.estimate_digest and wider.stage_plan.digest != base.stage_plan.digest
    assert estimate(policy, draft()).estimate_digest == base.estimate_digest, "the same plan prices to the same digest"


def test_a_plan_with_a_model_no_server_serves_is_refused_before_anything_is_priced(registry):
    with pytest.raises(DomainError) as caught:
        estimate(service(registry), draft({SONNET: SUBSCRIPTION}))
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_the_legacy_coverage_cannot_be_priced_by_model(registry, monkeypatch):
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_COVERAGE", "legacy")
    with pytest.raises(DomainError) as caught:
        estimate(service(registry), draft())
    assert caught.value.code is ErrorCode.VALIDATION_FAILED and caught.value.detail_fields["constraint"] == "unsupported_for_stage_plan"
    assert estimate(service(registry), None).stage_plan is None, "the legacy route still prices it as before"


@pytest.mark.parametrize("named", [{"executor_connection_id": "exc_01M2545JSD15ETSNNV904X991K"},
                                   {"preset_id": "evt_01M2545JSD15ETSNNV904X991K"},
                                   {"executor_group_id": "exg_01M2545JSD15ETSNNV904X991K"}])
def test_an_explicit_selector_under_the_layout_is_validation_failed_for_the_estimate_too(registry, named):
    with pytest.raises(DomainError) as caught:
        estimate(service(registry), draft(), **named)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED and caught.value.detail_fields["constraint"] == "stage_layout_enabled"


def test_the_preflight_reads_the_seam_it_was_built_with_unless_told_the_answer(registry):
    asked = []
    seam = lambda session: asked.append(session) or draft()
    policy = service(registry, stage_plans=seam)
    assert estimate(policy, plan=preflight._UNSET).stage_plan is not None and len(asked) == 1
    assert estimate(policy, plan=None).stage_plan is None and len(asked) == 1, "None is an answer: the seam is not asked again"


def test_a_repeat_under_the_layout_asks_nothing_of_the_sources_executor(registry, monkeypatch):
    asked = []

    class Runs:
        def get(self, session, run_id):
            return NS(analysis_profile_id="ap_01M5M28ZCDD8VPSP1BTAEW92YF", prompt_bundle_id="pb_01M5M28ZCDVCR37BX1884JGSPN",
                      version_uid=VERSION)

        def chosen_executor_connection(self, session, run_id):
            asked.append(run_id)
            return "exc_01M2545JSD15ETSNNV904X991K"

    monkeypatch.setattr("auditmanager.runs.repository.RunRepository", Runs)
    policy = service(registry)
    planned = policy.estimate_reaudit(None, run_id="run_01M2545JSD15ETSNNV904X991K", stage_plan=draft())
    assert planned.stage_plan is not None and asked == [], "the stand chooses the servers: the source's named connection is not read"
    assert planned.as_dict()["version_uid"] == VERSION and "reaudit_of_run_id" in json.loads(planned.authority_json)
    with pytest.raises(DomainError):
        policy.estimate_reaudit(None, run_id="run_01M2545JSD15ETSNNV904X991K", stage_plan=None)
    assert asked == ["run_01M2545JSD15ETSNNV904X991K"], "with the layout off the source's executor is read, as it always was"


# --- consent v2 -----------------------------------------------------------------------------------------------------------------


def test_the_press_of_the_button_is_the_consent_when_every_cell_is_a_subscription(registry):
    value = estimate(service(registry), draft())
    approved = value.approve(confirm(value, 0), actor_user_uid="usr_01M2545JSD15ETSNNV904X991J")
    assert approved["billing"] == "unmetered" and approved["ceiling_micros"] == 0
    assert approved["stage_plan_digest"] == value.stage_plan.digest
    prices = {pin.model_id: pin for pin in pinned_models()}
    assert approved["models"] == {m: {"rate_sha256": model_rate_sha256(prices[m]), "access": "subscription"} for m in (SONNET, OPUS)}
    assert approved["model_id"] == SONNET and approved["rate_sha256"] == model_rate_sha256(prices[SONNET]), "the text cell's, as before"
    with pytest.raises(DomainError) as caught:
        value.approve({"estimate_digest": value.estimate_digest, "ceiling_micros": 0, "confirmed": False})
    assert caught.value.detail_fields["constraint"] == "confirmation_required", "a subscription still needs the press"


def test_a_ceiling_is_required_as_soon_as_one_cell_is_paid_by_the_token(registry):
    policy = service(registry)
    for served in ({SONNET: API_ONLY, OPUS: API_ONLY}, {SONNET: SUBSCRIPTION, OPUS: API_ONLY}):
        value = estimate(policy, draft(served))
        for cap in (0, value.as_dict()["estimated_cost_micros"] - 1):
            with pytest.raises(DomainError) as caught:
                value.approve(confirm(value, cap))
            assert caught.value.detail_fields["constraint"] == "below_estimate"
        approved = value.approve(confirm(value, value.as_dict()["recommended_ceiling_micros"]))
        assert approved["billing"] == ("metered" if served[SONNET] is API_ONLY else "mixed")
        assert {m: e["access"] for m, e in approved["models"].items()} == {m: ("api" if a is API_ONLY else "subscription") for m, a in served.items()}


def test_a_changed_access_refuses_the_consent_with_the_cost_preflight_refusal(registry):
    """The person read a subscription estimate; before the start the agent went off line and the model is served by an API key."""
    policy = service(registry)
    read = estimate(policy, draft({SONNET: SUBSCRIPTION, OPUS: SUBSCRIPTION}))
    at_start = estimate(policy, draft({SONNET: API_ONLY, OPUS: SUBSCRIPTION}))
    with pytest.raises(DomainError) as caught:
        at_start.approve(confirm(read, 0))
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert dict(caught.value.detail_fields) == {"stage_id": "text_analysis", "reason": "cost_estimate_binding_changed"}
    # a rate that moved binds the same way
    pins = [replace(pin, input_per_mtok_usd=pin.input_per_mtok_usd * 2) if pin.model_id == OPUS else pin for pin in pinned_models()]
    repriced = Preflight(section_profiles=policy.sections, text_profiles=policy.profiles, provider_config=policy.config,
                         provider_mode="recorded", prices=lambda: pins)
    with pytest.raises(DomainError) as caught:
        estimate(repriced, draft({SONNET: API_ONLY, OPUS: API_ONLY})).approve(confirm(estimate(policy, draft({SONNET: API_ONLY, OPUS: API_ONLY})), 10**9))
    assert caught.value.detail_fields["reason"] == "cost_estimate_binding_changed"


def test_a_stale_digest_of_a_legacy_estimate_is_what_it_always_was(registry):
    policy = service(registry)
    value = estimate(policy, None)
    with pytest.raises(DomainError) as caught:
        value.approve({"estimate_digest": "0" * 64, "ceiling_micros": 10**9, "confirmed": True})
    assert caught.value.code is ErrorCode.CONFLICT and caught.value.detail_fields["conflict_reason"] == "run_cost_estimate_stale"
    assert "models" not in value.approve(confirm(value, value.as_dict()["recommended_ceiling_micros"]))


# --- the call-time guard: membership --------------------------------------------------------------------------------------------


def approved_config(models_map, **more) -> ProviderConfig:
    return ProviderConfig(ProviderMode.LIVE, SONNET, 1.0, None, True, approved_cost_ceiling=True, approved_models=models_map,
                          approved_stage_plan_digest="d" * 64, **more)


def entry_of(model_id: str, access: str = "subscription", rate: str | None = None) -> dict:
    pin = next(pin for pin in pinned_models() if pin.model_id == model_id)
    return {"rate_sha256": rate or model_rate_sha256(pin), "access": access}


def call_for(access: str = "subscription", model: str = SONNET) -> CallBinding:
    return CallBinding(expected_model=model, check_identity=True, cell_key="text:main", access=access)


def pin_of(model_id: str):
    return next(pin for pin in pinned_models() if pin.model_id == model_id)


def refused(config, model_id, call):
    with pytest.raises(DomainError) as caught:
        require_approved_model(config, pin_of(model_id), call)
    assert dict(caught.value.detail_fields) == {"stage_id": "text_analysis", "reason": "cost_estimate_binding_changed"}


def test_a_call_must_be_to_an_approved_model_at_the_approved_rate_and_access():
    config = approved_config({SONNET: entry_of(SONNET), OPUS: entry_of(OPUS, "api")})
    require_approved_model(config, pin_of(SONNET), call_for())
    require_approved_model(config, pin_of(OPUS), call_for("api", OPUS))
    refused(config, "gpt-6-sol", call_for(model="gpt-6-sol"))      # a model outside the consent
    refused(config, OPUS, call_for("subscription", OPUS))          # the access moved from the one that was priced
    refused(config, SONNET, call_for("api"))                       # an API call where a subscription was approved
    refused(config, SONNET, None)                                  # no binding is a member of nothing
    refused(approved_config({SONNET: entry_of(SONNET, rate="f" * 64)}), SONNET, call_for())


def test_a_run_whose_consent_names_one_model_is_held_to_it_as_before():
    legacy = ProviderConfig(ProviderMode.LIVE, "claude-opus-5", 1.0, None, True, approved_cost_ceiling=True,
                            approved_model_id="claude-opus-5", approved_rate_sha256=model_rate_sha256(pin_of("claude-opus-5")))
    require_approved_model(legacy, pin_of("claude-opus-5"))
    refused(legacy, SONNET, None)
    require_approved_model(ProviderConfig(ProviderMode.LIVE, SONNET, 1.0, None, False), pin_of("gpt-6-sol"), None)  # nothing approved


# --- the Run's cost authority --------------------------------------------------------------------------------------------------


class Command:
    def __init__(self, outcome):
        self.state, self.outcome = "succeeded", outcome


def authority(monkeypatch, *, run_plan, consent_extra=None, consent=True, billing="unmetered", stage_plan=None):
    plan = stage_plan or draft().freeze(layout.STAGE_ROWS)
    approved = {"estimate_digest": "e" * 64, "ceiling_micros": 0, "billing": billing, "model_id": SONNET,
                "rate_sha256": entry_of(SONNET)["rate_sha256"], "connection_revision_id": None, "window_characters": 1000, "max_windows": 12,
                "source_sha256": "s" * 64, "format": "analysis-cost-preflight/1", "stage_plan_digest": plan.digest,
                "models": {m: entry_of(m, plan.access_of(m)) for m in plan.models}}
    approved.update(consent_extra or {})
    run = NS(run_id="run_01M2545JSD15ETSNNV904X991K", command_id="cmd_01M2545JSD15ETSNNV904X991C", binding_state="pending",
             connection_revision_id=None, executor_group_revision_id=None, stage_plan=plan.to_json() if run_plan else None)
    outcome = {"run_id": run.run_id, **({"cost_consent": approved} if consent else {})}
    monkeypatch.setattr(cost_policy, "CommandRepository", lambda: NS(get=lambda session, command_id: Command(outcome)))
    return read_run_cost_policy(None, run_id=run.run_id, default_ceiling_usd=1.0, runs=NS(get=lambda s, r: run)), plan


def binding_changed(monkeypatch, **kw):
    with pytest.raises(DomainError) as caught:
        authority(monkeypatch, **kw)
    assert dict(caught.value.detail_fields) == {"stage_id": "text_analysis", "reason": "cost_estimate_binding_changed"}


def test_the_cost_authority_of_a_planned_run_carries_the_models_and_the_digest(monkeypatch):
    policy, plan = authority(monkeypatch, run_plan=True)
    assert policy.approved and policy.stage_plan_digest == plan.digest and set(policy.models) == set(plan.models)
    assert policy.enforce_ceiling is False and policy.connection_revision_id is None and policy.executor_group_revision_id is None
    mixed, _ = authority(monkeypatch, run_plan=True, billing="mixed", consent_extra={"ceiling_micros": 5_000_000})
    assert mixed.enforce_ceiling is True and mixed.ceiling_usd == 5.0


def test_a_consent_that_does_not_bind_the_plan_of_the_run_is_refused(monkeypatch):
    other = draft({SONNET: API_ONLY, OPUS: API_ONLY}).freeze(layout.STAGE_ROWS)
    binding_changed(monkeypatch, run_plan=True, consent_extra={"stage_plan_digest": other.digest})          # another plan
    binding_changed(monkeypatch, run_plan=True, consent_extra={"stage_plan_digest": None})                   # no digest: a v1 consent
    binding_changed(monkeypatch, run_plan=False)                                                              # a v2 consent, a run with no plan
    binding_changed(monkeypatch, run_plan=True, consent=False)                                               # a plan and no consent
    plan = draft().freeze(layout.STAGE_ROWS)
    binding_changed(monkeypatch, run_plan=True, consent_extra={"models": {SONNET: entry_of(SONNET)}})        # a model of the plan missing
    binding_changed(monkeypatch, run_plan=True, consent_extra={"models": {**{m: entry_of(m) for m in plan.models}, "gpt-6-sol": entry_of(SONNET)}})
    binding_changed(monkeypatch, run_plan=True, consent_extra={"models": {m: entry_of(m, "api") for m in plan.models}})   # another access
    binding_changed(monkeypatch, run_plan=True, consent_extra={"model_id": OPUS})                              # the text cell's model moved
    binding_changed(monkeypatch, run_plan=True, consent_extra={"connection_revision_id": "excr_01M2545JSD15ETSNNV904X991K"})


def test_the_mixed_billing_is_for_a_planned_consent_only(monkeypatch):
    with pytest.raises(DomainError) as caught:
        authority(monkeypatch, run_plan=False, billing="mixed", consent_extra={"stage_plan_digest": None, "models": None})
    assert caught.value.code is ErrorCode.INTERNAL_ERROR


# --- the readiness of a start ---------------------------------------------------------------------------------------------------


def test_with_the_layout_off_the_readiness_is_the_legacy_estimate(registry):
    policy = service(registry)
    answer = start_readiness(policy, None, None, version_uid=VERSION)
    legacy = estimate(policy, None).as_dict()
    assert answer == {"route": "legacy", "ready": True, "cells": [], "estimate_digest": legacy["estimate_digest"],
                      "estimated_cost_micros": legacy["estimated_cost_micros"],
                      "recommended_ceiling_micros": legacy["recommended_ceiling_micros"]}
    models.RunStartReadiness.model_validate(answer)


def test_the_readiness_names_the_set_the_access_of_each_cell_and_the_digest_to_confirm(registry):
    policy = service(registry)
    answer = start_readiness(policy, None, draft({SONNET: SUBSCRIPTION, OPUS: API_ONLY}), version_uid=VERSION)
    parsed = models.RunStartReadiness.model_validate(answer)
    assert answer["route"] == "stage_plan" and answer["ready"] is True and answer["kit"] == "claude_only" and answer["access"] == "mixed"
    cells = {c["cell_key"]: c for c in answer["cells"]}
    assert list(cells) == [f"{row}:main" for row in layout.STAGE_ROWS]
    assert {k: c["access"] for k, c in cells.items()} == {k: ("api" if k == "blocks:main" else "subscription") for k in cells}
    assert all(c["available"] and c["reasons"] == [] for c in cells.values())
    value = estimate(policy, draft({SONNET: SUBSCRIPTION, OPUS: API_ONLY}))
    assert answer["estimate_digest"] == value.estimate_digest and answer["stage_plan_digest"] == value.stage_plan.digest
    assert answer["estimated_cost_micros"] > 0 and parsed.recommended_ceiling_micros >= answer["estimated_cost_micros"]
    # the digest read here is the one the start's consent is held against
    value.approve(confirm(value, answer["recommended_ceiling_micros"]))


def test_all_subscription_is_a_zero_estimate_whose_confirmation_is_the_press(registry):
    answer = start_readiness(service(registry), None, draft(), version_uid=VERSION)
    assert answer["access"] == "subscription" and answer["estimated_cost_micros"] == 0 and answer["recommended_ceiling_micros"] == 0


def test_a_cell_with_no_model_on_any_server_makes_the_start_not_ready_and_prices_nothing(registry):
    policy = service(registry)
    answer = start_readiness(policy, None, draft({SONNET: SUBSCRIPTION, OPUS: NOWHERE}), version_uid=VERSION)
    models.RunStartReadiness.model_validate(answer)
    assert answer["ready"] is False and answer["kit"] == "claude_only"
    for key in ("estimate_digest", "stage_plan_digest", "estimated_cost_micros", "access"):
        assert key not in answer
    blocked = [c for c in answer["cells"] if not c["available"]]
    assert [c["cell_key"] for c in blocked] == ["blocks:main"] and blocked[0]["reasons"] == ["host_offline"] and "access" not in blocked[0]
    absent = start_readiness(policy, None, draft({SONNET: SUBSCRIPTION}), version_uid=VERSION)
    assert [c["reasons"] for c in absent["cells"] if not c["available"]] == [["not_on_any_server"]]


def test_a_row_the_run_will_not_call_does_not_block_it(registry, monkeypatch):
    monkeypatch.setenv(PLAN_ENV, "v2")
    served = {SONNET: SUBSCRIPTION, OPUS: SUBSCRIPTION}
    answer = start_readiness(service(registry), None, replace(draft(served), cells=tuple(
        replace(c, model_id="gpt-6-sol", effort="medium") if c.row in {"review", "correction"} else c for c in draft().cells)),
        version_uid=VERSION)
    assert answer["ready"] is True and [c["cell_key"] for c in answer["cells"]] == [
        "text:main", "blocks:main", "cross_check:main", "norms:main"]


def test_the_readiness_refuses_an_explicit_selector_under_the_layout(registry):
    with pytest.raises(DomainError) as caught:
        start_readiness(service(registry), None, draft(), version_uid=VERSION, preset_id="evt_01M2545JSD15ETSNNV904X991K")
    assert caught.value.detail_fields == {"field": "preset_id", "constraint": "stage_layout_enabled"}


def test_the_service_answers_the_readiness_over_the_stored_layout(registry, monkeypatch):
    store = MemoryStore()
    with_revision(store, layout.preset_cells("claude_only"))
    store.append_switch(None, enabled=True, set_by=ADMIN)
    served = everything(SUBSCRIPTION)
    api = StagePlanService(session_factory=FakeSessions(), store=store, commands=MemoryCommands(), provider_source="database",
                           availability=served, cost_preflight=service(registry))
    request = models.RunCostEstimateRequest.model_validate({"version_uid": VERSION})
    answer = models.RunStartReadiness.model_validate(api.get_start_readiness(body=request))
    assert answer.route.value == "stage_plan" and answer.ready and answer.access == "subscription"
    served.served[OPUS] = NOWHERE
    assert api.get_start_readiness(body=request)["ready"] is False, "read afresh every time: availability is never cached"
    bare = StagePlanService(session_factory=FakeSessions(), store=store, commands=MemoryCommands(), provider_source="database",
                            availability=served)
    with pytest.raises(DomainError) as caught:
        bare.get_start_readiness(body=request)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    environment = StagePlanService(session_factory=FakeSessions(), store=store, commands=MemoryCommands(), provider_source="environment",
                                   availability=served, cost_preflight=service(registry))
    with pytest.raises(DomainError) as caught:
        environment.get_start_readiness(body=request)
    assert caught.value.detail_fields["conflict_reason"] == "provider_source_not_database"
