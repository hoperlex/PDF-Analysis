from __future__ import annotations

import base64
import hashlib
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.kinds import AdapterSecrets
from auditmanager.executors.model import (
    ConnectionRecord, ProbeRecord, RevisionRecord, RevisionSettings, SecretRecord,
)
from auditmanager.executors.resolver import bind_connection
from auditmanager.executors.probe_runner import ProbeRunner
from auditmanager.executors.probes import ProbeResult
from auditmanager.executors.public import SecretUnreadableError
from auditmanager.executors.ssh_probe import probe_ssh_tunnel
from auditmanager.executors.ssh_tunnel_adapter import SshTunnelAdapter, TunnelPolicy
from auditmanager.executors.ssh_transport import SshFailure
from auditmanager.executors.usability import is_probed_ok, is_served
from auditmanager.storage.public import derive_blob_id

NOW = datetime.now(timezone.utc)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL7WQAAAABJRU5ErkJggg==")
DIGEST = hashlib.sha256(PNG).hexdigest()
POLICY = DestinationPolicy(resolver=lambda host, port: ["93.184.216.34"], networks=lambda: ())
MODEL = "anthropic/claude-opus-5"


def revision(gateway: Any, flavour: str = "openai_chat", host_key: str | None = "pin", *,
             plain_loopback: bool = False) -> RevisionRecord:
    path = "/api/v1" if flavour == "openai_chat" else ""
    # `F-15`: a tunnel carries plain http only to the remote host's own loopback. The tests that
    # go through `destination_for` (the resolver, the probe worker) name it; the ones that call
    # the adapter itself keep the public name the remote host would be told to dial.
    base = f"http://localhost:{gateway.port}{path}" if plain_loopback else gateway.base_url(path)
    return RevisionRecord("excr_1", "exc_1", 1, NOW, "usr_1", RevisionSettings(
        pin_id="claude-opus-5", gateway_model=MODEL, billing="not_metered",
        allow_client_documents=True, timeout_seconds=60, api_flavour=flavour,
        base_url=base, transport="ssh_tunnel", ssh_host="ssh.example.test", ssh_port=22,
        ssh_user="runner", host_key=host_key,
    ))


def request(png: bytes = PNG) -> ModelRequest:
    return ModelRequest("claude-opus-5", {
        "system": "s", "max_tokens": 16, "messages": [{"role": "user", "content": "hello"}],
        "images": [{"blob_id": str(derive_blob_id(sha256=DIGEST, size=len(PNG))),
                    "portal_block_id": "blk_" + "a" * 32, "sha256": DIGEST,
                    "size_bytes": len(PNG), "media_type": "image/png"}],
    }, image_bytes=png)


@pytest.mark.parametrize("flavour", ["openai_chat", "anthropic_messages"])
def test_png_goes_through_the_tunnel_with_original_http_host(
    gateway_factory: Any, monkeypatch: pytest.MonkeyPatch, flavour: str,
) -> None:
    gateway = gateway_factory()
    captured = []

    @contextmanager
    def fake_tunnel(endpoint, ssh_key, host_key, host, port, **kwargs):
        captured.append((endpoint.host, ssh_key, host_key, host, port))
        yield gateway.port

    monkeypatch.setattr("auditmanager.executors.ssh_tunnel_adapter.open_tunnel", fake_tunnel)
    answer = SshTunnelAdapter(revision(gateway, flavour), "http-key", "ssh-key", POLICY, None).complete(request())
    assert answer.model == MODEL
    assert captured == [("93.184.216.34", "ssh-key", "pin", "gateway.example.test", gateway.port)]
    (seen,) = gateway.requests
    assert seen["host"] == f"gateway.example.test:{gateway.port}"
    content = seen["body"]["messages"][-1]["content"]
    encoded = (content[-1]["image_url"]["url"].split(",", 1)[1] if flavour == "openai_chat"
               else content[-1]["source"]["data"])
    assert base64.b64decode(encoded) == PNG


def test_invalid_png_never_opens_tunnel(gateway_factory: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = gateway_factory()
    monkeypatch.setattr("auditmanager.executors.ssh_tunnel_adapter.open_tunnel",
                        lambda *args, **kwargs: pytest.fail("tunnel must not open"))
    with pytest.raises(ProxyDispatchError) as refusal:
        SshTunnelAdapter(revision(gateway), "http-key", "ssh-key", POLICY, None).complete(request(PNG + b"x"))
    assert refusal.value.dispatch_class == "not_sent" and gateway.requests == []


def test_changed_ssh_host_key_sends_no_http_key(gateway_factory: Any,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = gateway_factory()

    @contextmanager
    def changed(*args, **kwargs):
        raise SshFailure("host_key_changed", "changed", sent=False)
        yield 0

    monkeypatch.setattr("auditmanager.executors.ssh_tunnel_adapter.open_tunnel", changed)
    with pytest.raises(ProxyDispatchError) as refusal:
        SshTunnelAdapter(revision(gateway), "http-sentinel", "ssh-key", POLICY, None).complete(request())
    assert refusal.value.dispatch_class == "not_sent" and refusal.value.retry_safe is False
    assert "http-sentinel" not in str(refusal.value) and gateway.requests == []


def test_tunnel_policy_rejects_any_other_http_origin() -> None:
    policy = TunnelPolicy("https://model.example.test:9443/v1", 10000)
    assert policy.check("model.example.test", 9443, transport="direct") == ("127.0.0.1",)
    with pytest.raises(ConnectionRefusedError):
        policy.check("other.example.test", 9443, transport="direct")


def test_opened_secret_bundle_has_no_renderable_credentials() -> None:
    rendered = repr(AdapterSecrets("http-sentinel", {"ssh_private_key": "ssh-sentinel"}))
    assert "http-sentinel" not in rendered and "ssh-sentinel" not in rendered


def test_tunnel_probe_checks_ssh_pin_then_http_model(
    gateway_factory: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = gateway_factory()
    from tests.unit.executors.test_ssh_adapter import HOST_KEY

    monkeypatch.setattr("auditmanager.executors.ssh_probe.scan_host_key", lambda *args, **kwargs: HOST_KEY)

    @contextmanager
    def fake_tunnel(*args, **kwargs):
        yield gateway.port

    monkeypatch.setattr("auditmanager.executors.ssh_probe.open_tunnel", fake_tunnel)
    unpinned = probe_ssh_tunnel(revision(gateway, host_key=None).settings, "http-key", "ssh-key",
                                policy=POLICY)
    assert unpinned.outcome == "host_key_unpinned" and unpinned.observed_host_key == HOST_KEY
    checked = probe_ssh_tunnel(revision(gateway, host_key=HOST_KEY).settings, "http-key", "ssh-key",
                               policy=POLICY)
    assert checked.outcome == "ok" and checked.reported_model == MODEL


def secret(purpose: str, *, set_at: datetime = NOW, secret_id: str | None = None) -> SecretRecord:
    return SecretRecord(secret_id or ("exs_http" if purpose == "api_key" else "exs_ssh"),
                        "exc_1", purpose, "kid", "dest", "last4", None, set_at, "usr_1")


def probe(requested_at: datetime = NOW + timedelta(seconds=1)) -> ProbeRecord:
    return ProbeRecord("epb_1", "exc_1", "excr_1", "exs_http", "finished", "ok", MODEL,
                       "reported", 1, 200, "not_metered", None, None, requested_at, "usr_1",
                       requested_at, requested_at)


class Store:
    def __init__(self, revision: RevisionRecord, keys: list[SecretRecord], result: ProbeRecord) -> None:
        self.revision, self.keys, self.result = revision, keys, result

    def current_secrets(self, session, ids):
        return {"exc_1": self.keys}

    def latest_finished_probe(self, session, revision_id, secret_id):
        return self.result if secret_id == "exs_http" else None

    def get_revision(self, session, revision_id):
        return self.revision

    def get_connection(self, session, connection_id):
        return ConnectionRecord("exc_1", "http_api", "HTTP tunnel", NOW, "usr_1")


def test_probe_before_either_current_secret_is_not_routable(gateway_factory: Any) -> None:
    gateway = gateway_factory()
    connection = ConnectionRecord("exc_1", "http_api", "HTTP tunnel", NOW, "usr_1")
    saved = revision(gateway)
    assert is_served(connection, saved)
    current = [secret("api_key"), secret("ssh_private_key")]
    assert is_probed_ok(None, Store(saved, current, probe()), connection, saved)
    rotated = [secret("api_key"), secret("ssh_private_key", set_at=NOW + timedelta(seconds=2))]
    assert not is_probed_ok(None, Store(saved, rotated, probe()), connection, saved)
    api_rotated = [secret("api_key", set_at=NOW + timedelta(seconds=2), secret_id="exs_new"),
                   secret("ssh_private_key")]
    assert not is_probed_ok(None, Store(saved, api_rotated, probe()), connection, saved)
    assert not is_probed_ok(None, Store(saved, current[:1], probe()), connection, saved)


def test_resolver_opens_both_bound_secrets(gateway_factory: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = gateway_factory()
    saved = revision(gateway, plain_loopback=True)
    opened = []

    def fake_open(session, ring, *, secret_id, destination, repository):
        opened.append((secret_id, destination))
        return "http-key" if secret_id == "exs_http" else "ssh-key"

    monkeypatch.setattr("auditmanager.executors.resolver.open_secret", fake_open)
    bound = bind_connection(None, "excr_1", ring=None, policy=POLICY, context=None,
                            repository=Store(saved, [secret("api_key"), secret("ssh_private_key")], probe()))
    assert isinstance(bound.adapter, SshTunnelAdapter)
    assert opened[0][0] == "exs_http" and opened[1][0] == "exs_ssh"
    assert opened[0][1].startswith("ssh_tunnel|") and opened[1][1] == "ssh_tunnel|ssh.example.test:22|"


def test_resolver_refuses_a_tunnel_without_current_ssh_key(gateway_factory: Any,
                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = gateway_factory()
    saved = revision(gateway, plain_loopback=True)
    monkeypatch.setattr("auditmanager.executors.resolver.open_secret",
                        lambda *args, **kwargs: "http-key")
    with pytest.raises(SecretUnreadableError):
        bind_connection(None, "excr_1", ring=None, policy=POLICY, context=None,
                        repository=Store(saved, [secret("api_key")], probe()))


def test_worker_probe_opens_both_secrets(gateway_factory: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = gateway_factory()
    saved = revision(gateway, plain_loopback=True)
    store = Store(saved, [secret("api_key"), secret("ssh_private_key")], probe())
    opened = []
    delivered = []

    def fake_open(session, ring, *, secret_id, destination, repository):
        opened.append((secret_id, destination))
        return "http-key" if secret_id == "exs_http" else "ssh-key"

    def fake_probe(settings, api_key, ssh_key, **kwargs):
        delivered.append((api_key, ssh_key))
        return ProbeResult("ok")

    monkeypatch.setattr("auditmanager.executors.probe_runner.open_secret", fake_open)
    monkeypatch.setattr("auditmanager.executors.probe_runner.probe_ssh_tunnel", fake_probe)
    runner = ProbeRunner(lambda: nullcontext(None), ring=None, policy=POLICY, repository=store)
    result = runner._evaluate(probe())
    assert result.outcome == "ok" and delivered == [("http-key", "ssh-key")]
    assert [item[0] for item in opened] == ["exs_http", "exs_ssh"]


def test_several_pngs_go_through_the_tunnel_in_order(
    gateway_factory: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from auditmanager.executors.image_input import attach_images
    from tests.unit.executors.crop_support import crop

    gateway = gateway_factory()

    @contextmanager
    def fake_tunnel(endpoint, ssh_key, host_key, host, port, **kwargs):
        yield gateway.port

    monkeypatch.setattr("auditmanager.executors.ssh_tunnel_adapter.open_tunnel", fake_tunnel)
    crops = [crop(label) for label in ("a", "b", "c")]
    multi = attach_images(ModelRequest("claude-opus-5", {
        "system": "s", "max_tokens": 16, "messages": [{"role": "user", "content": "hello"}]}), crops)
    SshTunnelAdapter(revision(gateway), "http-key", "ssh-key", POLICY, None).complete(multi)
    (seen,) = gateway.requests
    content = seen["body"]["messages"][-1]["content"]
    sent = [base64.b64decode(block["image_url"]["url"].split(",", 1)[1]) for block in content[1:]]
    assert sent == [item.data for item in crops]
    # and a list that does not match its bytes never opens the tunnel
    monkeypatch.setattr("auditmanager.executors.ssh_tunnel_adapter.open_tunnel",
                        lambda *args, **kwargs: pytest.fail("the tunnel must not open"))
    mismatched = ModelRequest(multi.model_id, multi.body, images_bytes=multi.images_bytes[:2])
    with pytest.raises(ProxyDispatchError) as refused:
        SshTunnelAdapter(revision(gateway), "http-key", "ssh-key", POLICY, None).complete(mismatched)
    assert refused.value.dispatch_class == "not_sent"
