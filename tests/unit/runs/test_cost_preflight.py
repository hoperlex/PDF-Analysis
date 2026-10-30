"""Source-bound monetary consent, all ordinary sections and provider pre-call caps."""
from dataclasses import replace
from types import SimpleNamespace as NS

import json
import pytest

from auditmanager.analysis.public import ProviderConfig, ProviderMode, ModelPin, model_rate_sha256
from auditmanager.analysis.text.cost import CostMeter, request_cost_upper_usd, require_approved_model
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.runs import preflight
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
MODEL = "claude-opus-5"


@pytest.fixture
def registry():
    return load_text_profile_registry()


def version(section="AI", count=300_000, pages=100):
    return NS(version_uid=VERSION, sha256="a"*64, text_character_count=count,
        recognised_character_count=0, page_count=pages, upload_kind="portal_bundle",
        classification=NS(version_uid=VERSION, confirmed_by_user_uid="usr_01M2545JSD15ETSNNV904X991J",
            section_code=section, project_stage="P", revision=1),
        manifest=(NS(role="source.document", blob_id="blob_sha256_"+"b"*64),))


def service(registry, **kwargs):
    return preflight.RunCostPreflight(section_profiles=registry.section_profiles(), text_profiles=registry,
        provider_config=ProviderConfig(ProviderMode.RECORDED, MODEL, 1.0, None, False),
        provider_mode="recorded", **kwargs)


def estimate(service, source, **kwargs):
    return service.estimate_run(None, version_uid=VERSION, version_record=source, **kwargs)


def consent(value, cap=None):
    return {"estimate_digest": value.estimate_digest, "ceiling_micros": value.as_dict()["recommended_ceiling_micros"] if cap is None else cap, "confirmed": True}


def test_all_fourteen_sections_price_before_start_and_large_normal_inputs_get_explicit_windows(registry):
    policy = service(registry)
    for section in registry.entries:
        small = estimate(policy, version(section, 500, 1))
        large = estimate(policy, version(section, 20_000_000, 500))
        assert small.as_dict()["calls"] == 5
        assert json.loads(small.authority_json)["extended_review"]["max_blocks"] == 16
        assert large.as_dict()["calls"] > 12
        assert large.as_dict()["estimated_cost_micros"] > small.as_dict()["estimated_cost_micros"] > 0
        accepted = large.approve(consent(large), actor_user_uid="expert")
        assert accepted["extended_review"]["plan_version"] == "extended-review-v2"
        assert accepted["max_windows"] >= large.as_dict()["windows"]
        assert accepted["approved_by_user_uid"] == "expert"


def test_exact_micro_cost_does_not_round_fractions_down():
    assert preflight.estimated_micros(ModelPin("m", .1, .3), 1, 1) == 1
    assert preflight.estimated_micros(ModelPin("m", 3., 15.), 10, 20) == 330


@pytest.mark.parametrize("mutate", [lambda v: setattr(v, "sha256", "d"*64),
    lambda v: setattr(v, "recognised_character_count", 1),
    lambda v: setattr(v.classification, "revision", 2),
    lambda v: setattr(v.classification, "section_code", "EOM")])
def test_changed_source_or_classification_refuses_old_consent(registry, mutate):
    policy, source = service(registry), version()
    old = estimate(policy, source)
    mutate(source)
    with pytest.raises(DomainError) as failure:
        estimate(policy, source).approve(consent(old))
    assert failure.value.code is ErrorCode.CONFLICT
    assert failure.value.detail_fields["conflict_reason"] == "run_cost_estimate_stale"


def test_raised_output_price_and_route_rate_preset_changes_are_bound(registry):
    revision = NS(revision_id="erev1", model_id=MODEL, input_budget_characters=1, billing="metered", chosen_connection_id="exec1")
    chosen = NS(revision_id="prev1", executor_connection_id="exec1")
    policy = service(registry, connection_route=lambda *_args, **_kw: revision,
                     preset_resolver=lambda *_args: chosen)
    source = version()
    old = estimate(policy, source, preset_id="preset1")
    raised = estimate(policy, source, preset_id="preset1", relaxed_limits=True)
    assert raised.as_dict()["output_tokens"] - 48_000 == (old.as_dict()["output_tokens"] - 48_000) * 4
    assert raised.estimate_digest != old.estimate_digest
    revision.revision_id = "erev2"
    assert estimate(policy, source, preset_id="preset1").estimate_digest != old.estimate_digest
    revision.revision_id = "erev1"
    chosen.revision_id = "prev2"
    assert estimate(policy, source, preset_id="preset1").estimate_digest != old.estimate_digest
    policy.prices = lambda: (ModelPin(MODEL, 300., 1500.),)
    assert estimate(policy, source, preset_id="preset1").estimate_digest != old.estimate_digest


@pytest.mark.parametrize("payload", [None, {}, {"confirmed": False}, {"confirmed": "true"}])
def test_missing_or_unconfirmed_consent_refuses(registry, payload):
    with pytest.raises(DomainError) as failure:
        estimate(service(registry), version()).approve(payload)
    assert failure.value.code is ErrorCode.VALIDATION_FAILED


def test_too_small_limit_refuses_and_unmetered_zero_is_explicit(registry):
    priced = estimate(service(registry), version())
    with pytest.raises(DomainError):
        priced.approve(consent(priced, priced.as_dict()["estimated_cost_micros"]-1))
    revision = NS(revision_id="rev", model_id=MODEL, input_budget_characters=1, billing="unmetered")
    unmetered = estimate(service(registry, connection_route=lambda _: revision), version())
    assert unmetered.as_dict()["billing"] == "unmetered"
    assert unmetered.as_dict()["estimated_cost_micros"] == unmetered.as_dict()["recommended_ceiling_micros"] == 0
    assert unmetered.approve(consent(unmetered, 0))["ceiling_micros"] == 0


def test_next_full_request_must_fit_accepted_limit_and_model_rate_revision_are_pinned():
    pin = ModelPin(MODEL, 3., 15.)
    request = ModelRequest(MODEL, {"system": "x"*5000, "max_tokens": 16000})
    pending = request_cost_upper_usd(pin, request)
    meter = CostMeter(ceiling_usd=pending, spent_usd=0)
    meter.check_before_call(pending_cost_usd=pending)
    with pytest.raises(DomainError) as failure:
        CostMeter(ceiling_usd=pending/2).check_before_call(pending_cost_usd=pending)
    assert failure.value.code is ErrorCode.COST_BUDGET_EXCEEDED
    # Explicit unmetered sources never acquire a monetary charge.
    CostMeter(ceiling_usd=0, enforce_ceiling=False).check_before_call(pending_cost_usd=pending)
    config = ProviderConfig(ProviderMode.RECORDED, MODEL, 1., None, False,
        approved_cost_ceiling=True, approved_model_id=MODEL,
        approved_rate_sha256=model_rate_sha256(pin), approved_connection_revision_id="rev1")
    require_approved_model(config, pin, NS(connection_revision_id="rev1"))
    with pytest.raises(DomainError):
        require_approved_model(config, ModelPin(MODEL, 30., 15.), NS(connection_revision_id="rev1"))
    with pytest.raises(DomainError):
        require_approved_model(config, pin, NS(connection_revision_id="rev2"))


def test_six_scope_group_prices_all_calls_and_pins_each_verified_set(monkeypatch, registry):
    from auditmanager.runs import v3_group
    scopes = tuple(NS(scope_id=scope, identity=scope, chunking_profile="chunk-v1",
        set_id="set-"+scope, set_sha256=str(index)*64) for index, scope in enumerate(v3_group.SCOPES, 1))
    pack = NS(scopes=scopes, sha256="e"*64)
    profile = NS(snapshot_id="snapshot", content_sha256="p"*64,
                 system_prompt="rules", response_schema_json="{}")
    monkeypatch.setattr(v3_group, "_validate_pack", lambda _: profile)
    monkeypatch.setattr(preflight, "current_snapshot", lambda _: NS(norms_snapshot_id="snapshot"))
    monkeypatch.setattr(preflight, "qualification", lambda *_: NS(build_complete=True, sources_confirmed=True))
    refs = {scope.scope_id: NS(set_id=scope.set_id, set_sha256=scope.set_sha256,
                              set_size_bytes=10_000 + index) for index, scope in enumerate(scopes)}
    monkeypatch.setattr(preflight, "select_verified_retrieval_set", lambda _s, *, identity, **_: refs[identity])
    route = NS(revision_id="rev", model_id=MODEL, billing="metered", input_budget_characters=1)
    policy = service(registry, pack_registry=NS(select_beta=lambda: pack), connection_route=lambda _: route)
    value = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"))
    view, authority = value.as_dict(), value.approve(consent(value))
    assert view["calls"] == view["windows"] == 6
    assert view["output_tokens"] == 6*16_000
    assert view["estimated_cost_micros"] == sum(authority["scope_costs_micros"].values())
    raised = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"), relaxed_limits=True)
    assert raised.as_dict()["output_tokens"] == 6*64_000
    assert raised.as_dict()["estimated_cost_micros"] > view["estimated_cost_micros"]
    refs[scopes[0].scope_id].set_size_bytes += 1
    changed = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"))
    assert changed.estimate_digest != value.estimate_digest
    route.billing = "unmetered"
    free = policy.estimate_group(None, version_uid=VERSION, version_record=version("AR"))
    assert free.as_dict()["estimated_cost_micros"] == 0 and free.approve(consent(free))["billing"] == "unmetered"
