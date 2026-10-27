"""`SEC-RUNNER-CAP-01` (`F-15`): a plain ``http://`` model destination is refused unless the key
does not cross the open internet.

``model.py`` used to accept ``http://`` and ``https://`` alike, and ``destinations.py`` classifies
addresses only, so an administrator (or a stolen administrator session) could route the prompts
and the bearer key to a public host in clear text. The rule now lives beside the one the module
already has: ``refuse_plain_http`` asks ``DestinationPolicy`` about the host -- with no resolver,
so nothing is looked up -- and admits ``http://`` for a loopback name or address, and for a
private literal on ``transport: vpn``, the one transport that module admits a private range for.

The refusal is the existing one (`validation_failed`, field ``base_url``, constraint
``base_url_invalid``), is raised when a revision is written and again when its key is bound
for a call, and carries no part of the address.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.analysis.public import pinned_models
from auditmanager.executors import model as model_module
from auditmanager.executors.model import (
    RevisionSettings,
    destination_for,
    refuse_plain_http,
    validate_settings,
)
from auditmanager.shared.errors import DomainError, ErrorCode

PINS = {pin.model_id for pin in pinned_models()}
BASE = dict(pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5", billing="metered",
            allow_client_documents=False, timeout_seconds=60)
HTTP = RevisionSettings(**BASE, api_flavour="openai_chat", base_url="https://proxy.test/agent/v1",
                        transport="direct")
TUNNEL = dict(transport="ssh_tunnel", ssh_host="gpu.test", ssh_port=22, ssh_user="am")
REFUSED = ("base_url", "base_url_invalid")


def _settings(base_url: str, transport: str = "direct") -> RevisionSettings:
    if transport == "ssh_tunnel":
        return replace(HTTP, base_url=base_url, **TUNNEL)
    return replace(HTTP, base_url=base_url, transport=transport)


def _refusal(base_url: str, transport: str = "direct") -> tuple[str, str]:
    with pytest.raises(DomainError) as refused:
        validate_settings("http_api", _settings(base_url, transport), pinned_model_ids=PINS)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    return refused.value.detail_fields["field"], refused.value.detail_fields["constraint"]


def _accepted(base_url: str, transport: str = "direct") -> None:
    settings = _settings(base_url, transport)
    assert validate_settings("http_api", settings, pinned_model_ids=PINS) == settings
    assert destination_for("http_api", settings, "api_key")


# -- accepted -------------------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "https://proxy.test/agent/v1", "https://203.0.113.9/v1", "https://openrouter.ai/api/v1",
    "https://[2606:4700::1]/v1", "https://127.0.0.1:8443/v1", "https://10.8.0.2/v1",
])
@pytest.mark.parametrize("transport", ["direct", "vpn"])
def test_https_is_accepted_for_every_host_as_before(url: str, transport: str) -> None:
    _accepted(url, transport)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:11434", "http://127.1.2.3/v1", "http://localhost:11434/v1",
    "http://LOCALHOST", "http://[::1]:8080/v1", "http://[::ffff:127.0.0.1]/v1",
    "http://gpu.localhost:8080",
])
@pytest.mark.parametrize("transport", ["direct", "vpn", "ssh_tunnel"])
def test_http_to_a_loopback_name_or_address_is_accepted(url: str, transport: str) -> None:
    _accepted(url, transport)


@pytest.mark.parametrize("url", [
    "http://10.8.0.2", "http://10.8.0.2:11434/v1", "http://192.168.1.20:8080",
    "http://172.16.0.5/v1", "http://[fd00::5]:8080/v1", "http://100.64.0.7/v1",
])
def test_http_to_a_private_literal_is_accepted_on_a_vpn_route(url: str) -> None:
    _accepted(url, "vpn")


# -- refused --------------------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "http://proxy.test/agent/v1", "http://openrouter.ai/api/v1", "http://93.184.216.34/v1",
    "http://[2606:4700::1]/v1", "http://8.8.8.8:8080",
])
@pytest.mark.parametrize("transport", ["direct", "vpn", "ssh_tunnel"])
def test_http_to_a_public_host_is_refused_on_every_transport(url: str, transport: str) -> None:
    assert _refusal(url, transport) == REFUSED


@pytest.mark.parametrize("url", ["http://10.8.0.2", "http://192.168.1.20:8080", "http://[fd00::5]/v1"])
@pytest.mark.parametrize("transport", ["direct", "ssh_tunnel"])
def test_http_to_a_private_literal_is_refused_off_a_vpn_route(url: str, transport: str) -> None:
    """``destinations.py`` admits a private range for ``vpn`` alone, and so does this rule."""
    assert _refusal(url, transport) == REFUSED


@pytest.mark.parametrize("url", [
    "http://169.254.169.254/latest/meta-data", "http://0.0.0.0:80", "http://224.0.0.1",
    "http://240.0.0.1", "http://[fe80::1]/v1",
])
@pytest.mark.parametrize("transport", ["direct", "vpn", "ssh_tunnel"])
def test_http_to_link_local_or_reserved_addresses_is_refused(url: str, transport: str) -> None:
    assert _refusal(url, transport) == REFUSED


@pytest.mark.parametrize("url", ["http://gpu.corp.internal/v1", "http://ollama:11434", "http://postgres"])
def test_http_to_a_name_that_is_not_a_loopback_name_is_refused_even_on_a_vpn(url: str) -> None:
    """A name cannot be classified without resolving it and this module never resolves: it
    would be accepted on a guess. The administrator names the VPN address, or uses https."""
    assert _refusal(url, "vpn") == REFUSED
    assert _refusal(url, "direct") == REFUSED


@pytest.mark.parametrize("url", [
    "http://user:secret@127.0.0.1:8080/v1", "http://user@localhost/v1",
    "https://user:secret@proxy.test/v1", "http://:secret@10.8.0.2/v1",
])
def test_credentials_in_the_url_stay_refused(url: str) -> None:
    assert _refusal(url, "vpn") == REFUSED


def test_the_refusal_carries_no_part_of_the_address() -> None:
    sentinel = "SENTINEL-HOST.example.org"
    with pytest.raises(DomainError) as refused:
        validate_settings("http_api", _settings(f"http://{sentinel}/v1"), pinned_model_ids=PINS)
    text = " ".join([str(refused.value), repr(refused.value), repr(refused.value.detail_fields)])
    assert sentinel.lower() not in text.lower()
    assert set(refused.value.detail_fields) == {"field", "constraint"}


def test_the_module_does_not_resolve_a_name(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("refuse_plain_http looked a name up")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(DomainError):
        refuse_plain_http("http://resolves.example.org/v1", "direct")
    refuse_plain_http("https://resolves.example.org/v1", "direct")


# -- the stored revision ----------------------------------------------------------------------------


def test_a_stored_http_public_revision_is_refused_where_its_key_is_bound_for_a_call() -> None:
    """A revision written before this slice is still a row, so it can be read; the key is bound
    to a destination at every call and every probe, and there the same refusal stops it before
    the key is opened (the resolver builds the destination as an argument of ``open_secret``)."""
    stored = _settings("http://proxy.test/agent/v1")  # a record, never passed through validate
    with pytest.raises(DomainError) as refused:
        destination_for("http_api", stored, "api_key")
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert (refused.value.detail_fields["field"], refused.value.detail_fields["constraint"]) == REFUSED


def test_the_ssh_key_destinations_are_not_touched() -> None:
    """Only the bearer key travels over the plain connection; the tunnel's SSH key does not."""
    stored = _settings("http://gpu.corp.internal/v1", "ssh_tunnel")
    assert destination_for("http_api", stored, "ssh_private_key") == "ssh_tunnel|gpu.test:22|"


def test_the_destination_of_a_vpn_or_tunnel_revision_is_what_it_was() -> None:
    assert destination_for("http_api", _settings("http://10.8.0.2", "vpn"), "api_key") == (
        "vpn||http://10.8.0.2:80")
    assert destination_for("http_api", _settings("http://localhost:11434", "ssh_tunnel"),
                           "api_key") == "ssh_tunnel|gpu.test:22|http://localhost:11434"


def test_the_rule_is_the_destination_modules_not_a_second_classification() -> None:
    """The module imports the policy it asks and holds no list of its own."""
    assert model_module._LITERAL_POLICY.__class__.__name__ == "DestinationPolicy"
    assert model_module._LITERAL_POLICY.allowed_hosts == (), "the operator's host list is not consulted"
