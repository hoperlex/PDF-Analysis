"""`EXEC-SEAL-01`: the settings each connection kind takes, and the destination a key is bound to."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from auditmanager.analysis.public import pinned_models
from auditmanager.executors.model import (
    RevisionSettings,
    destination_for,
    host_key_fingerprint,
    normalise_origin,
    validate_settings,
)
from auditmanager.shared.errors import DomainError, ErrorCode

PINS = {pin.model_id for pin in pinned_models()}
BASE = dict(pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5", billing="metered",
            allow_client_documents=False, timeout_seconds=60)
HTTP = RevisionSettings(**BASE, api_flavour="openai_chat", base_url="https://Proxy.Test/agent/v1",
                        transport="direct")
TUNNEL = replace(HTTP, base_url="http://localhost:11434", transport="ssh_tunnel",
                 ssh_host="Gpu.Test", ssh_port=22, ssh_user="am")
SSH = RevisionSettings(**BASE, ssh_host="gpu.test", ssh_port=2222, ssh_user="am",
                       ssh_profile="claude_code_headless")
PULL = RevisionSettings(**BASE, pull_client="claude_code_session", answer_deadline_seconds=600,
                        max_claimed_tasks=1)


def _refusal(kind: str, settings: RevisionSettings) -> tuple[str, str]:
    with pytest.raises(DomainError) as refused:
        validate_settings(kind, settings, pinned_model_ids=PINS)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    return refused.value.detail_fields["field"], refused.value.detail_fields["constraint"]


def test_the_pins_are_the_lock_s_three_models() -> None:
    assert PINS == {"claude-opus-5", "claude-sonnet-5", "gpt-6-sol"}


def test_claude_subscription_can_be_a_not_metered_pull_revision() -> None:
    settings = replace(PULL, pin_id="claude-opus-5", gateway_model="claude-opus-5",
                       billing="not_metered", pull_client="agent")
    assert validate_settings("pull", settings, pinned_model_ids=PINS) == settings


def test_codex_subscription_can_be_a_not_metered_pull_revision() -> None:
    settings = replace(PULL, pin_id="gpt-6-sol", gateway_model="gpt-6-sol",
                       billing="not_metered", pull_client="agent")
    assert validate_settings("pull", settings, pinned_model_ids=PINS) == settings


@pytest.mark.parametrize(("kind", "settings"),
                         [("http_api", HTTP), ("http_api", TUNNEL), ("ssh_command", SSH),
                          ("pull", PULL)])
def test_a_complete_revision_of_each_kind_is_accepted(kind: str, settings: RevisionSettings) -> None:
    assert validate_settings(kind, settings, pinned_model_ids=PINS) == settings


def test_an_unpinned_model_is_refused_as_model_not_pinned() -> None:
    assert _refusal("http_api", replace(HTTP, pin_id="gpt-x")) == ("pin_id", "model_not_pinned")


def test_the_pin_and_the_gateway_name_are_two_fields_and_neither_is_derived() -> None:
    accepted = validate_settings(
        "http_api", replace(HTTP, gateway_model="vendor/some-other-name"), pinned_model_ids=PINS)
    assert accepted.pin_id == "claude-opus-5" and accepted.gateway_model == "vendor/some-other-name"


@pytest.mark.parametrize("url", [
    "https://proxy.test/v1?key=1", "https://proxy.test/v1#frag", "https://proxy.test/?",
    "ftp://proxy.test", "proxy.test", "https://user:pw@proxy.test/v1", "https:///v1",
    "https://proxy.test:99999/v1", "https://proxy .test",
])
def test_a_base_url_the_proxy_adapter_would_refuse_is_refused(url: str) -> None:
    assert _refusal("http_api", replace(HTTP, base_url=url)) == ("base_url", "base_url_invalid")


def test_a_setting_the_kind_does_not_use_or_lacks_is_refused() -> None:
    assert _refusal("http_api", replace(HTTP, ssh_profile="custom_command")) == (
        "ssh_profile", "field_not_for_kind")
    assert _refusal("http_api", replace(HTTP, base_url=None)) == ("base_url", "field_required_for_kind")
    assert _refusal("http_api", replace(HTTP, ssh_host="gpu.test")) == ("ssh_host", "field_not_for_kind")
    assert _refusal("http_api", replace(TUNNEL, ssh_user=None)) == ("ssh_user", "field_required_for_kind")
    assert _refusal("ssh_command", replace(SSH, base_url="https://x.test")) == (
        "base_url", "field_not_for_kind")
    assert _refusal("pull", replace(PULL, ssh_host="gpu.test")) == ("ssh_host", "field_not_for_kind")
    assert _refusal("pull", replace(PULL, max_claimed_tasks=None)) == (
        "max_claimed_tasks", "field_required_for_kind")


def test_a_refusal_never_carries_a_value() -> None:
    secret_looking = "https://proxy.test/v1?token=SENTINEL-VALUE"
    with pytest.raises(DomainError) as refused:
        validate_settings("http_api", replace(HTTP, base_url=secret_looking), pinned_model_ids=PINS)
    assert "SENTINEL" not in repr(refused.value.detail_fields) + str(refused.value)


def test_the_destination_is_transport_ssh_endpoint_origin() -> None:
    assert destination_for("http_api", HTTP, "api_key") == "direct||https://proxy.test:443"
    assert destination_for("http_api", replace(HTTP, transport="vpn", base_url="http://10.8.0.2"),
                           "api_key") == "vpn||http://10.8.0.2:80"
    assert destination_for("http_api", TUNNEL, "api_key") == (
        "ssh_tunnel|gpu.test:22|http://localhost:11434")
    assert destination_for("ssh_command", SSH, "ssh_private_key") == "ssh_command|gpu.test:2222|"
    assert destination_for("http_api", TUNNEL, "ssh_private_key") == "ssh_tunnel|gpu.test:22|"


def test_a_changed_address_changes_the_destination_and_a_changed_path_does_not() -> None:
    before = destination_for("http_api", HTTP, "api_key")
    assert destination_for("http_api", replace(HTTP, base_url="https://proxy.test/other/v2"),
                           "api_key") == before
    assert destination_for("http_api", replace(HTTP, base_url="https://proxy2.test/agent/v1"),
                           "api_key") != before
    assert destination_for("http_api", replace(HTTP, base_url="https://proxy.test:8443/agent/v1"),
                           "api_key") != before
    assert destination_for("http_api", replace(HTTP, transport="vpn"), "api_key") != before


def test_a_purpose_the_kind_cannot_hold_has_no_destination() -> None:
    for kind, settings, purpose in (("pull", PULL, "api_key"), ("ssh_command", SSH, "api_key"),
                                    ("http_api", HTTP, "ssh_private_key")):
        with pytest.raises(DomainError) as refused:
            destination_for(kind, settings, purpose)
        assert refused.value.detail_fields["constraint"] == "purpose_not_for_kind"


def test_the_origin_is_lower_cased_with_the_default_port_made_explicit() -> None:
    assert normalise_origin("https://Proxy.TEST/a/b") == "https://proxy.test:443"
    assert normalise_origin("http://[::1]/x") == "http://[::1]:80"


def test_the_fingerprint_is_derived_from_the_key_blob_the_way_ssh_keygen_prints_it() -> None:
    line = Ed25519PrivateKey.generate().public_key().public_bytes(
        Encoding.OpenSSH, PublicFormat.OpenSSH).decode()
    blob = base64.b64decode(line.split()[1])
    expected = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
    assert host_key_fingerprint(line) == expected
    assert host_key_fingerprint(line + " comment words") == expected
    for bad in ("", "ssh-ed25519", "ssh-ed25519 !!!!", "rsa AAAA"):
        with pytest.raises(DomainError) as refused:
            host_key_fingerprint(bad)
        assert refused.value.detail_fields["constraint"] == "host_key_invalid"
