"""The probe's outcome vocabulary, one case each (`EXEC-HTTP-01`, plan section 4.1).

Container-free: the worker's HTTP half, with the local gateway. The database half (picking up
``requested`` rows) is in ``tests/integration/executors``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.public import pinned_models
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.model import RevisionSettings
from auditmanager.executors.probes import ProbeResult, probe_http_api, scrub

KEY = "sk-sentinel-0123456789abcdef"
GATEWAY_MODEL = "anthropic/claude-opus-5"
PIN = pinned_models()[0]


def _settings(gateway: Any, **changes: Any) -> RevisionSettings:
    base: dict[str, Any] = dict(
        pin_id=PIN.model_id, gateway_model=GATEWAY_MODEL, billing="metered",
        allow_client_documents=False, timeout_seconds=3, api_flavour="openai_chat",
        base_url=gateway.base_url(), transport="direct",
    )
    base.update(changes)
    return RevisionSettings(**base)


def _probe(gateway: Any, *, policy: DestinationPolicy | None = None, **changes: Any) -> ProbeResult:
    return probe_http_api(
        _settings(gateway, **changes), KEY, policy=policy or gateway.policy(),
        input_per_mtok_usd=PIN.input_per_mtok_usd, output_per_mtok_usd=PIN.output_per_mtok_usd,
    )


def _rate_exact_cost(tokens_in: int = 1200, tokens_out: int = 340) -> float:
    return (tokens_in * PIN.input_per_mtok_usd + tokens_out * PIN.output_per_mtok_usd) / 1_000_000


def test_a_good_answer_is_ok_with_the_reported_model_latency_and_a_checked_rate(gateway_factory: Any) -> None:
    gateway = gateway_factory(cost=_rate_exact_cost())
    result = _probe(gateway)
    assert (result.outcome, result.reported_model, result.identity_basis) == (
        "ok", GATEWAY_MODEL, "reported")
    assert result.rate_check == "checked" and result.http_status == 200
    assert result.latency_ms is not None and result.latency_ms >= 0
    (seen,) = gateway.requests
    assert seen["body"]["max_tokens"] == 16, "the smallest completion"
    assert seen["body"]["model"] == GATEWAY_MODEL


def test_html_403_is_ip_refused_and_json_401_or_403_is_credential_refused(gateway_factory: Any) -> None:
    assert _probe(gateway_factory(behaviour="html403")).outcome == "ip_refused"
    assert _probe(gateway_factory(behaviour="json401")).outcome == "credential_refused"
    assert _probe(gateway_factory(behaviour="json403")).outcome == "credential_refused"


@pytest.mark.parametrize("behaviour", ["wrong_model", "no_model", "stub_model"])
def test_an_answer_from_another_model_or_none_is_a_model_mismatch(
    gateway_factory: Any, behaviour: str
) -> None:
    result = _probe(gateway_factory(behaviour=behaviour))
    assert result.outcome == "model_mismatch"


def test_a_placeholder_gateway_name_never_passes(gateway_factory: Any) -> None:
    result = _probe(gateway_factory(model="proxy"), gateway_model="proxy")
    assert result.outcome == "model_mismatch"


def test_a_reported_cost_off_the_pins_rates_is_a_rate_mismatch(gateway_factory: Any) -> None:
    result = _probe(gateway_factory(cost=_rate_exact_cost() * 3))
    assert (result.outcome, result.rate_check) == ("rate_mismatch", "mismatch")


def test_a_gateway_that_reports_no_cost_is_not_failed(gateway_factory: Any) -> None:
    result = _probe(gateway_factory(cost=None))
    assert (result.outcome, result.rate_check) == ("ok", "not_reported")


def test_a_not_metered_revision_has_no_rate_check(gateway_factory: Any) -> None:
    result = _probe(gateway_factory(cost=999.0), billing="not_metered")
    assert (result.outcome, result.rate_check) == ("ok", "not_metered")


def test_no_answer_in_time_is_a_timeout(gateway_factory: Any) -> None:
    result = _probe(gateway_factory(delay=2.5), timeout_seconds=1)
    assert result.outcome == "timeout"


def test_other_statuses_and_bodies_are_protocol_errors(gateway_factory: Any) -> None:
    assert _probe(gateway_factory(behaviour="http500")).outcome == "protocol_error"
    assert _probe(gateway_factory(behaviour="bad_json")).outcome == "protocol_error"
    assert _probe(gateway_factory(behaviour="redirect")).outcome == "protocol_error"


def test_a_name_that_does_not_resolve_or_a_closed_port_is_unreachable(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    from auditmanager.executors.destinations import DestinationUnresolvable

    def nxdomain(host: str, port: int) -> list[str]:
        raise DestinationUnresolvable()

    assert _probe(gateway, policy=gateway.policy(resolver=nxdomain)).outcome == "unreachable"
    closed = gateway.policy(dial=lambda address, port: ("127.0.0.1", 1))
    assert _probe(gateway, policy=closed).outcome == "unreachable"
    assert gateway.requests == []


def test_an_unpermitted_destination_is_refused_and_nothing_is_sent(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    for base_url in (f"http://127.0.0.1:{gateway.port}/v1", f"http://postgres:{gateway.port}/v1",
                     "http://169.254.169.254/latest"):
        result = _probe(gateway, policy=DestinationPolicy(), base_url=base_url)
        assert result.outcome == "destination_refused", base_url
        assert result.detail is not None and "127.0.0.1" not in result.detail
    assert gateway.requests == []


def test_a_private_range_is_probeable_only_over_a_vpn(gateway_factory: Any) -> None:
    gateway = gateway_factory(cost=_rate_exact_cost())
    private = gateway.policy(resolver=lambda host, port: ["10.8.0.5"])
    assert _probe(gateway, policy=private, transport="direct").outcome == "destination_refused"
    assert _probe(gateway, policy=private, transport="vpn").outcome == "ok"


def test_a_tunnel_or_an_unknown_flavour_is_kind_not_served(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    assert _probe(gateway, transport="ssh_tunnel", ssh_host="h", ssh_port=22, ssh_user="u").outcome == "kind_not_served"
    assert gateway.requests == []


def test_the_anthropic_flavour_is_probed_through_the_sdk(gateway_factory: Any) -> None:
    gateway = gateway_factory(model=GATEWAY_MODEL)
    good = _probe(gateway, api_flavour="anthropic_messages", base_url=gateway.base_url(""))
    assert (good.outcome, good.reported_model, good.rate_check) == ("ok", GATEWAY_MODEL, "not_reported")
    assert gateway.requests[0]["x_api_key"] == KEY
    bad_gateway = gateway_factory(behaviour="json401")
    refused = _probe(bad_gateway, api_flavour="anthropic_messages", base_url=bad_gateway.base_url(""))
    assert refused.outcome == "credential_refused"
    html = gateway_factory(behaviour="html403")
    assert _probe(html, api_flavour="anthropic_messages", base_url=html.base_url("")).outcome == "ip_refused"
    wrong = gateway_factory(behaviour="wrong_model")
    assert _probe(wrong, api_flavour="anthropic_messages", base_url=wrong.base_url("")).outcome == "model_mismatch"


def test_a_probe_result_never_carries_the_key_a_header_or_an_address(gateway_factory: Any) -> None:
    for behaviour in ("ok", "html403", "json401", "wrong_model", "http500", "bad_json"):
        gateway = gateway_factory(behaviour=behaviour)
        result = _probe(gateway)
        rendered = repr(result)
        assert KEY not in rendered and "Bearer" not in rendered and "127.0.0.1" not in rendered
        assert result.detail is None or len(result.detail) <= 500


def test_scrub_removes_every_given_secret_and_cuts_to_the_limit() -> None:
    assert scrub(f"failed with {KEY} inside", KEY) == "failed with [removed] inside"
    assert scrub("x" * 900) == "x" * 500
    assert scrub(None, KEY) is None
