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
