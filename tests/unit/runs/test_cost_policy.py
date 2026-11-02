"""Accepted cap authority survives worker restart and keeps historical policy."""

from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ModelPin, model_rate_sha256
from auditmanager.runs import cost_policy
from auditmanager.shared.errors import DomainError


def read(monkeypatch, outcome, *, revision=None):
    run = SimpleNamespace(command_id="cmd_01M2545JSD15ETSNNV904X991J", connection_revision_id=revision)
    commands = SimpleNamespace(get=lambda *_args: SimpleNamespace(state="succeeded", outcome=outcome))
    monkeypatch.setattr(cost_policy, "CommandRepository", lambda: commands)
    return cost_policy.read_run_cost_policy(None, run_id="run", default_ceiling_usd=1.0,
                                            runs=SimpleNamespace(get=lambda *_args: run))


def consent():
    pin = ModelPin("selected-model", 3.0, 15.0)
    return {"estimate_digest": "a" * 64, "ceiling_micros": 4_500_000, "billing": "metered",
            "window_characters": 100_000, "max_windows": 24, "model_id": pin.model_id,
            "rate_sha256": model_rate_sha256(pin)}


def test_historical_raised_and_normal_commands_keep_their_policy(monkeypatch):
    assert read(monkeypatch, {}).enforce_ceiling is True
    policy = read(monkeypatch, {"relaxed_limits": True})
    assert policy.approved is False and policy.enforce_ceiling is False and policy.ceiling_usd == 1.0


def test_new_approved_cap_is_enforced_even_with_raised_output_choice(monkeypatch):
    policy = read(monkeypatch, {"relaxed_limits": True, "cost_consent": consent()})
    assert policy.approved and policy.enforce_ceiling and policy.ceiling_usd == 4.5
    assert policy.window_characters == 100_000 and policy.max_windows == 24
    assert policy.model_id == "selected-model"


def test_new_section_statistics_consent_tracks_cost_without_monetary_halt(monkeypatch):
    data = consent() | {"ceiling_micros": 0, "uncapped_stats": True}
    policy = read(monkeypatch, {"relaxed_limits": True, "cost_consent": data})
    assert policy.approved and not policy.enforce_ceiling
    assert policy.max_windows == 24
    with pytest.raises(DomainError):
        read(monkeypatch, {"cost_consent": data})


def test_group_member_gets_only_its_share_of_approved_group_limit(monkeypatch):
    data = consent() | {"run_limits_micros": {"run": 750_000}}
    assert read(monkeypatch, {"cost_consent": data}).ceiling_usd == 0.75


def test_unmetered_zero_cap_is_explicit_not_a_monetary_halt(monkeypatch):
    policy = read(monkeypatch, {"cost_consent": consent() | {"billing": "unmetered", "ceiling_micros": 0}})
    assert policy.approved and not policy.enforce_ceiling


@pytest.mark.parametrize("change", [{"ceiling_micros": True}, {"ceiling_micros": -1},
    {"ceiling_micros": 0}, {"billing": "free-ish"}, {"estimate_digest": "bad"}, {"max_windows": 0}])
def test_invalid_accepted_cost_authority_fails_closed(monkeypatch, change):
    with pytest.raises(DomainError):
        read(monkeypatch, {"cost_consent": consent() | change})


def test_changed_frozen_connection_refuses_before_provider_binding(monkeypatch):
    with pytest.raises(DomainError):
        read(monkeypatch, {"cost_consent": consent() | {"connection_revision_id": "old"}}, revision="new")


@pytest.mark.parametrize("version", ["extended-review-v1", "extended-review-v2"])
def test_accepted_workflow_version_survives_worker_upgrade(monkeypatch, version):
    frozen = {"enabled": True, "max_blocks": 16, "plan_version": version}
    policy = read(monkeypatch, {"cost_consent": consent() | {"extended_review": frozen}})
    assert policy.extended_review == frozen


def test_fresh_full_document_authority_is_explicit_and_legacy_v1_cannot_gain_it(monkeypatch):
    frozen = {"enabled": True, "max_blocks": "all", "plan_version": "extended-review-v2"}
    assert read(monkeypatch, {"cost_consent": consent() | {"extended_review": frozen}}).extended_review == frozen
    with pytest.raises(DomainError):
        read(monkeypatch, {"cost_consent": consent() | {"extended_review": frozen | {"plan_version": "extended-review-v1"}}})


@pytest.mark.parametrize("maximum", [1, 15, 17])
def test_unsupported_frozen_visual_window_refuses_instead_of_silently_disabling(monkeypatch, maximum):
    frozen = {"enabled": True, "max_blocks": maximum, "plan_version": "extended-review-v2"}
    with pytest.raises(DomainError):
        read(monkeypatch, {"cost_consent": consent() | {"extended_review": frozen}})


def v3_frozen(blocks, pages, **extra):
    return {"enabled": True, "plan_version": "extended-review-v3", "max_blocks": blocks, "window_size": 16,
            "max_windows": max((blocks + 15) // 16, (pages + 15) // 16), "text_page_limit": pages,
            "review": True, "rules_sha256": "0" * 64, "section_code": "AR", **extra}


@pytest.mark.parametrize("blocks, pages", [(1001, 16), (16, 501), (1001, 501)])
def test_section_run_bounds_hold_unless_the_run_asked_for_relaxed_limits(monkeypatch, blocks, pages):
    data = consent() | {"extended_review": v3_frozen(blocks, pages)}
    with pytest.raises(DomainError):
        read(monkeypatch, {"cost_consent": data})
    with pytest.raises(DomainError):
        read(monkeypatch, {"relaxed_limits": False, "cost_consent": data})
    assert read(monkeypatch, {"relaxed_limits": True, "cost_consent": data}).extended_review["max_blocks"] == blocks


def test_the_bounds_themselves_are_accepted_for_every_run(monkeypatch):
    frozen = v3_frozen(1000, 500)
    assert read(monkeypatch, {"cost_consent": consent() | {"extended_review": frozen}}).extended_review == frozen


def test_the_lift_stamp_without_relaxed_limits_is_refused(monkeypatch):
    stamped = v3_frozen(16, 16, unbounded_stats=True)
    with pytest.raises(DomainError):
        read(monkeypatch, {"cost_consent": consent() | {"extended_review": stamped}})
    assert read(monkeypatch, {"relaxed_limits": True,
                              "cost_consent": consent() | {"extended_review": stamped}}).extended_review == stamped
