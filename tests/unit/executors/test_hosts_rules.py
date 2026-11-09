"""`HOSTS-BACKEND-01` (ADR-0028 decisions 2 to 4 and 16): the rules of a host that need no database.

Pure functions only: the report a host agent sends is validated and reduced to closed enumerations; what counts as a *change* of it; every
reason a model is unavailable on a host, each one on its own, and in the order the contract lists them; the state of a host and of a model
(busy is not unavailable); the cooldown (15 minutes, only for a refusal about the host's access); the slots in force; and the system connections a
report calls for (only what the catalogue serves, with that access). Each guard has a test that fails when the guard is removed -- the
"break it once" proof is in the assertion's own wording: the reason list is compared with ``==``, never with ``in``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from auditmanager.executors.catalogue import Catalogue, CatalogueEntry
from auditmanager.executors.hosts import (
    COOLDOWN_SECONDS,
    DEFAULT_SLOTS,
    HEARTBEAT_FRESH_SECONDS,
    REASON_ORDER,
    ModelFact,
    ProviderFact,
    Quadruple,
    access_of_billing,
    billing_of_access,
    cooldown_reason_of,
    cooldown_until_for,
    desired_quadruples,
    host_state,
    model_reasons,
    model_state,
    normalise_host_report,
    pair_group_name,
    pool_of,
    slots_in_force,
    split_pool,
)
from auditmanager.shared.errors import DomainError, ErrorCode

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
HOST = "exh_01M2545JSD15ETSNNV904X991K"
OPUS = "claude-opus-5-5"
SONNET = "claude-sonnet-5-5"


def _model(model_id: str = OPUS, state: str = "verified", code: str | None = None) -> dict[str, Any]:
    return {"model_id": model_id, "state": state, "checked_at": "2026-11-10T11:59:00Z",
            **({"failure_code": code} if code else {})}


def _provider(provider: str = "claude_code", access: str = "subscription", auth: str = "valid",
              models: list[dict[str, Any]] | None = None, **extra: Any) -> dict[str, Any]:
    return {"provider": provider, "access": access, "auth_state": auth,
            "models": [_model()] if models is None else models, **extra}


def _report(providers: list[dict[str, Any]] | None = None, slots: Any = None, **kw: Any):
    return normalise_host_report(
        agent_version="0.21.0", providers=[_provider()] if providers is None else providers,
        slots={"claude_code": 1} if slots is None else slots, **kw)


CATALOGUE = Catalogue(entries=(
    CatalogueEntry("claude_code", OPUS, ("subscription", "api"), ("medium", "high"), (OPUS,)),
    CatalogueEntry("claude_code", SONNET, ("subscription", "api"), ("low", "medium", "high"), (SONNET,)),
    CatalogueEntry("anthropic_api", OPUS, ("api",), ("medium", "high"), (OPUS,)),
))


# --- the report ---------------------------------------------------------------------------------------------


def test_a_valid_report_is_reduced_to_closed_values() -> None:
    report = _report([_provider(cli_version="2.1.310", accept_images=False, cli_path="/usr/bin/claude", secret="x")])
    (provider,) = report.providers
    assert (provider.provider, provider.access, provider.auth_state, provider.cli_version) == (
        "claude_code", "subscription", "valid", "2.1.310")
    rendered = repr(report.providers_json())
    assert "usr/bin" not in rendered and "secret" not in rendered, "an extra key is dropped by construction"


@pytest.mark.parametrize(("mutation", "constraint"), [
    (lambda p: p.update(provider="gemini"), "enum"),
    (lambda p: p.update(auth_state="maybe"), "auth_state"),
    (lambda p: p.update(access="free"), "access"),
    (lambda p: p.update(provider="openai_api", access="subscription"), "access"),  # a direct API key is api access only
    (lambda p: p.update(models=[_model(state="verified"), _model(state="verified")]), "models"),  # a model named once
    (lambda p: p.update(models=[_model(state="failed")]), "failure_code"),  # failed carries a code
    (lambda p: p.update(models=[_model(code="quota_exceeded")]), "failure_code"),  # a code only with failed
    (lambda p: p.update(auth_state="login_required"), "verified_without_login"),  # no verified model without a login
])
def test_a_report_that_is_not_acceptable_is_refused_naming_the_field(mutation: Any, constraint: str) -> None:
    provider = _provider()
    mutation(provider)
    with pytest.raises(DomainError) as refused:
        _report([provider])
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert refused.value.detail_fields["field"] == "providers" and refused.value.detail_fields["constraint"] == constraint


def test_a_provider_is_named_once_and_slots_name_only_reported_providers() -> None:
    with pytest.raises(DomainError):
        _report([_provider(), _provider()])
    with pytest.raises(DomainError) as refused:
        _report(slots={"codex": 1})
    assert refused.value.detail_fields["constraint"] == "provider_not_reported"
    with pytest.raises(DomainError) as refused:
        _report(slots={"claude_code": 0})
    assert refused.value.detail_fields["constraint"] == "range"


def test_the_change_key_ignores_the_instants_and_sees_every_fact() -> None:
    base = _report()
    later = _report([_provider(models=[{**_model(), "checked_at": "2026-11-10T18:00:00Z"}])])
    assert base.change_key() == later.change_key(), "a re-check at another time changes nothing"
    assert base.change_key() != _report([_provider(models=[_model(state="failed", code="quota_exceeded")])]).change_key()
    assert base.change_key() != _report([_provider(auth="login_required", models=[_model(state="not_verified")])]).change_key()
    assert base.change_key() != _report([_provider(cli_version="2.2.0")]).change_key()
    assert base.change_key() != _report(slots={"claude_code": 2}).change_key()
    assert base.change_key() != normalise_host_report(
        agent_version="0.21.1", providers=[_provider()], slots={"claude_code": 1}).change_key()


def test_the_stored_form_round_trips_and_carries_no_path_or_key() -> None:
    report = _report([_provider(cli_version="2.1.310")])
    again = type(report).from_stored(agent_version="0.21.0", providers=report.providers_json(), slots=report.slots)
    assert again.change_key() == report.change_key()
    assert again.providers == report.providers


# --- availability: every reason alone, and the order ---------------------------------------------------------


def _reasons(*, enabled: bool = True, age: float | None = 10.0, auth: str = "valid", state: str = "verified",
             cooldown: datetime | None = None, provider: bool = True, model: bool = True) -> list[str]:
    report = _report([_provider(auth=auth, models=[_model(state=state, code="quota_exceeded" if state == "failed" else None)]
                                if auth == "valid" or state != "verified" else [_model(state="not_verified")])])
    fact = report.providers[0] if provider else None
    return model_reasons(
        enabled=enabled, pulse_age_seconds=age, provider=fact, model=(fact.model(OPUS) if fact and model else None),
        cooldown_until=cooldown, now=NOW)


def test_an_available_model_has_no_reason() -> None:
    assert _reasons() == []


def test_host_disabled() -> None:
    assert _reasons(enabled=False) == ["host_disabled"]


@pytest.mark.parametrize("age", [None, HEARTBEAT_FRESH_SECONDS + 0.5, 3600])
def test_a_stale_or_missing_pulse_is_host_offline_without_any_write(age: float | None) -> None:
    assert _reasons(age=age) == ["host_offline"]


def test_the_pulse_window_is_inclusive_at_120_seconds() -> None:
    assert _reasons(age=float(HEARTBEAT_FRESH_SECONDS)) == []


def test_login_required_and_the_model_that_follows_from_it() -> None:
    assert _reasons(auth="login_required") == ["login_required", "model_not_verified"]


def test_model_not_verified_when_unchecked_failed_or_absent() -> None:
    assert _reasons(state="not_verified") == ["model_not_verified"]
    assert _reasons(state="failed") == ["model_not_verified"]
    assert _reasons(model=False) == ["model_not_verified"], "a model the report does not name is not assumed"
    assert _reasons(provider=False) == ["model_not_verified"]


def test_model_cooling_down_until_the_instant_and_not_after() -> None:
    assert _reasons(cooldown=NOW + timedelta(seconds=1)) == ["model_cooling_down"]
    assert _reasons(cooldown=NOW) == [], "a cooldown that ends now has ended"
    assert _reasons(cooldown=NOW - timedelta(minutes=1)) == []


def test_every_reason_together_come_in_the_contracts_order() -> None:
    reasons = _reasons(enabled=False, age=None, auth="login_required", cooldown=NOW + timedelta(minutes=5))
    assert reasons == ["host_disabled", "host_offline", "login_required", "model_not_verified", "model_cooling_down"]
    assert reasons == [item for item in REASON_ORDER if item in reasons]


def test_busy_is_not_unavailable() -> None:
    assert model_state([], pool_full=False) == "available"
    assert model_state([], pool_full=True) == "busy"
    assert model_state(["host_disabled"], pool_full=True) == "unavailable", "a reason beats a full pool"


@pytest.mark.parametrize(("age", "total", "used", "state"), [
    (None, 1, 0, "offline"), (500.0, 1, 0, "offline"), (5.0, 1, 0, "online"), (5.0, 2, 1, "online"),
    (5.0, 1, 1, "busy"), (5.0, 0, 0, "online"),
])
def test_the_state_of_a_host(age: float | None, total: int, used: int, state: str) -> None:
    assert host_state(pulse_age_seconds=age, slots_total=total, slots_in_use=used) == state


# --- the cooldown --------------------------------------------------------------------------------------------


def test_the_cooldown_is_fifteen_minutes() -> None:
    assert COOLDOWN_SECONDS == 900
    assert cooldown_until_for(NOW) == NOW + timedelta(minutes=15)
    assert _reasons(cooldown=cooldown_until_for(NOW)) == ["model_cooling_down"]
    assert _reasons(cooldown=cooldown_until_for(NOW - timedelta(minutes=15, seconds=1))) == []


@pytest.mark.parametrize(("failure", "reason"), [
    ("quota_exceeded: plan limit", "quota_exceeded"), ("rate_limited", "quota_exceeded"), ("auth_failed: 401", "access_denied"),
    ("login_required", "access_denied"), ("model_not_found", "model_not_found"), ("model_not_available: gpt", "model_not_found"),
])
def test_a_refusal_about_the_hosts_access_names_a_cooldown(failure: str, reason: str) -> None:
    assert cooldown_reason_of(failure) == reason


@pytest.mark.parametrize("failure", ["timeout", "codex_timeout", "answer_not_json", "claude_turn_failed", "image_input_unsupported",
                                     "reported_model_mismatch", "no reason given", ""])
def test_a_failure_that_is_not_about_access_takes_nothing_out_of_service(failure: str) -> None:
    assert cooldown_reason_of(failure) is None


# --- slots and pools -------------------------------------------------------------------------------------------


def test_the_default_slots_are_one_for_a_subscription_and_two_for_an_api_key() -> None:
    assert dict(DEFAULT_SLOTS) == {"subscription": 1, "api": 2}
    assert slots_in_force("subscription", None) == 1
    assert slots_in_force("api", None) == 2
    assert slots_in_force(None, None) == 1, "a provider the report no longer names has one slot, nothing more is assumed"


def test_the_administrators_event_beats_the_default_and_is_bounded() -> None:
    assert slots_in_force("subscription", 3) == 3
    for bad in (0, 17, -1):
        with pytest.raises(ValueError):
            slots_in_force("api", bad)


def test_the_pool_is_the_host_and_the_provider() -> None:
    assert pool_of(HOST, "codex") == f"{HOST}:codex"
    assert split_pool(pool_of(HOST, "claude_code")) == (HOST, "claude_code")
    with pytest.raises(ValueError):
        split_pool("not a pool")


def test_billing_follows_the_access_and_back() -> None:
    assert billing_of_access("subscription") == "not_metered" and billing_of_access("api") == "metered"
    assert access_of_billing("not_metered") == "subscription" and access_of_billing("metered") == "api"
    with pytest.raises(ValueError):
        billing_of_access("free")


# --- the system objects the report calls for -------------------------------------------------------------------


def test_the_report_calls_for_one_connection_per_catalogue_quadruple() -> None:
    report = _report([
        _provider(models=[_model(OPUS), _model(SONNET, state="failed", code="quota_exceeded"), _model("gpt-unknown")]),
        _provider("anthropic_api", "api", models=[_model(OPUS)]),
    ], slots={"claude_code": 1, "anthropic_api": 2})
    assert desired_quadruples(report, CATALOGUE) == sorted([
        Quadruple("claude_code", "subscription", OPUS), Quadruple("claude_code", "subscription", SONNET),
        Quadruple("anthropic_api", "api", OPUS)]), "composition is what is found, verified or not; a model outside the catalogue is not"


def test_an_access_the_catalogue_does_not_serve_calls_for_nothing() -> None:
    book = Catalogue(entries=(CatalogueEntry("claude_code", OPUS, ("api",), ("medium",), (OPUS,)),))
    assert desired_quadruples(_report(), book) == [], "a subscription Opus is not served by this catalogue"


def test_the_group_of_a_pair_is_named_by_model_and_access() -> None:
    assert pair_group_name(OPUS, "subscription") != pair_group_name(OPUS, "api")
    assert pair_group_name(OPUS, "api") == f"{OPUS} · api"


def test_provider_fact_lookup_is_by_provider_and_access() -> None:
    report = _report([_provider(access="subscription")])
    assert report.provider("claude_code", "subscription") is not None
    assert report.provider("claude_code", "api") is None, "the same CLI under another access is another fact"
    assert isinstance(report.providers[0], ProviderFact) and isinstance(report.providers[0].models[0], ModelFact)
