"""Routing, `import-env` and `rewrap` (`EXEC-HTTP-01`), against real PostgreSQL and a local gateway."""

from __future__ import annotations

import importlib.util
import base64
import hashlib
import sys
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.analysis.public import ModelRequest
from auditmanager.executors import kinds
from auditmanager.executors.operations import (
    IMPORT_DISPLAY_NAME,
    OperationRefused,
    import_env,
    reach,
    rewrap,
)
from auditmanager.executors.public import (
    ExecutorRepository,
    RevisionSettings,
    create_connection,
    load_private_ring,
    pinned_models,
    resolve_route,
    revise_connection,
    set_route,
    record_probe_started,
    record_probe_result,
)
from auditmanager.executors.runtime import DestinationPolicy, bind_connection, freeze_connection, is_probed_ok
from auditmanager.shared.errors import DomainError
from auditmanager.storage.public import derive_blob_id

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)
engine = harness.engine
session = harness.session

_SUPPORT_NAME = "am_exec_http_support"
_SUPPORT_PATH = Path(__file__).resolve().parent / "http_support.py"
if _SUPPORT_NAME in sys.modules:
    support = sys.modules[_SUPPORT_NAME]
else:
    _s = importlib.util.spec_from_file_location(_SUPPORT_NAME, _SUPPORT_PATH)
    assert _s is not None and _s.loader is not None
    support = importlib.util.module_from_spec(_s)
    sys.modules[_SUPPORT_NAME] = support
    _s.loader.exec_module(support)

FakeGateway = support.fake_gateway.FakeGateway


@pytest.fixture
def fake():  # type: ignore[no-untyped-def]
    gateway = FakeGateway(cost=None).start()  # reports no cost: the rate check is not_reported
    yield gateway
    gateway.stop()


def _factory(session: Any) -> Any:
    return lambda: nullcontext(session)


def _refusal(call: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


# -- routing -----------------------------------------------------------------------------------


def test_only_a_revision_probed_ok_on_its_current_key_can_be_routed(session, fake) -> None:  # type: ignore[no-untyped-def]
    rings = support.make_rings()
    connection = support.seed_connection(session, rings, fake.vpn_url(), probe=None, routed=False)
    refused = _refusal(lambda: support.route(session, connection.connection_id))
    assert refused.code.value == "conflict"
    assert refused.detail_fields == {"conflict_reason": "connection_not_probed"}
    # A probe that did not pass is no pass.
    support.mark_probe(session, connection.connection_id, "credential_refused")
    assert _refusal(lambda: support.route(session, connection.connection_id)).code.value == "conflict"
    support.mark_probe(session, connection.connection_id, "ok")
    support.route(session, connection.connection_id)
    assert resolve_route(session, "text_analysis").primary.revision_id == connection.revision_id
    # A new key, or a new revision, needs a new probe before it can be routed or started on.
    support.set_key(session, rings, connection.connection_id, "sk-second-0123456789abcdef")
    store = ExecutorRepository()
    record = store.get_connection(session, connection.connection_id)
    revision = store.current_revisions(session, [connection.connection_id])[connection.connection_id]
    assert not is_probed_ok(session, store, record, revision)
    support.mark_probe(session, connection.connection_id)
    assert is_probed_ok(session, store, record, revision)
    new_revision = support.revise(session, connection.connection_id, fake.vpn_url("/v2"))
    assert new_revision != connection.revision_id
    assert freeze_connection_error(session) == "executor_route_missing"


def freeze_connection_error(session: Any) -> str:
    return str(_refusal(lambda: freeze_connection(session, "text_analysis")).detail_fields["dependency"])


def test_a_kind_or_transport_the_registry_does_not_serve_is_refused_at_route_time(
    session, fake, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    # This release registers all three kinds (`http_api`, `ssh_command`, `pull`) and the three
    # transports, so "not served" is no longer a state a real connection can be in. The refusal is
    # kept by taking the registration away for the test: the command over SSH with no adapter
    # factory, and the SSH tunnel with an `http_api` entry that does not serve it.
    ssh = create_connection(
        session, kind="ssh_command", display_name="machine", roles=support.ADMIN_ROLES,
        idempotency_key=support.unique(), actor_uid=support.ACTOR)
    revise_connection(
        session, connection_id=ssh.connection_id,
        settings=RevisionSettings(
            pin_id=support.PIN.model_id, gateway_model=support.PIN.model_id, billing="metered",
            allow_client_documents=False, timeout_seconds=60, ssh_host="gpu.example.test",
            ssh_port=22, ssh_user="am", ssh_profile="claude_code_headless"),
        pinned_model_ids={pin.model_id for pin in pinned_models()}, roles=support.ADMIN_ROLES,
        idempotency_key=support.unique(), actor_uid=support.ACTOR)
    rings = support.make_rings()
    tunnel = support.seed_connection(session, rings, "http://localhost:11434/v1", probe="ok",
                                     routed=False, transport="ssh_tunnel", ssh_host="gpu.example.test",
                                     ssh_port=22, ssh_user="am")
    # The negative half: while the registry serves them, neither is refused as a kind. The command
    # has no probe yet, the tunnel has no SSH key yet, so each ends on its own, different refusal.
    assert _refusal(lambda: support.route(session, ssh.connection_id)).detail_fields == {
        "conflict_reason": "connection_not_probed"}
    assert _refusal(lambda: support.route(session, tunnel.connection_id)).detail_fields == {
        "conflict_reason": "connection_not_probed"}

    monkeypatch.delitem(kinds._REGISTRY, "ssh_command")
    refused = _refusal(lambda: support.route(session, ssh.connection_id))
    assert (refused.code.value, refused.detail_fields) == (
        "validation_failed", {"field": "kind", "constraint": "kind_not_served"})
    http_api = kinds.adapter_for("http_api")
    assert http_api is not None
    monkeypatch.setitem(kinds._REGISTRY, "http_api", replace(
        http_api, serves=lambda revision: revision.settings.transport in ("direct", "vpn")))
    assert _refusal(lambda: support.route(session, tunnel.connection_id)).detail_fields[
        "constraint"] == "kind_not_served"


def test_a_key_opens_only_for_the_destination_of_the_revision_it_is_bound_for(
    session, fake  # type: ignore[no-untyped-def]
) -> None:
    """The caller recomputes the destination from the revision it is about to call: a revision on
    another host cannot open the key, one on the same origin can, and so does the old one."""
    from auditmanager.executors.public import SecretUnreadableError

    rings = support.make_rings()
    connection = support.seed_connection(session, rings, fake.vpn_url())
    same_origin = support.revise(session, connection.connection_id, fake.vpn_url("/v2"))
    moved = support.revise(session, connection.connection_id,
                           fake.vpn_url().replace("10.8.0.2", "10.8.0.3"))
    for revision_id in (connection.revision_id, same_origin):
        bind_connection(session, revision_id, ring=rings.private, policy=fake.policy(), context=None)
    with pytest.raises(SecretUnreadableError):
        bind_connection(session, moved, ring=rings.private, policy=fake.policy(), context=None)


# -- import-env ----------------------------------------------------------------------------------


class _LoopbackAllowed(DestinationPolicy):
    """The harness' own server listens on loopback. ``import_env`` always names ``transport:
    direct`` and `F-15` admits plain ``http://`` there for a loopback name alone, so this suite
    names the server by its loopback address and lets the destination rules treat that one
    class as public. Every other class (private, link-local, the compose network) still refuses."""

    def classify(self, address: Any) -> str:
        found = super().classify(address)
        return "public" if found == "loopback" else found


def _loopback_policy(fake: Any) -> DestinationPolicy:
    inner = fake.policy()
    return _LoopbackAllowed(
        allowed_hosts=inner.allowed_hosts, resolver=inner.resolver, dial=inner.dial,
        networks=inner.networks)


def _loopback_url(fake: Any) -> str:
    return f"http://127.0.0.1:{fake.port}/agent/v1"


def _environ(fake: Any, **changes: str) -> dict[str, str]:
    values = {"PROXY_LLM_BASE_URL": _loopback_url(fake), "PROXY_LLM_TOKEN": support.KEY,
              "PROXY_LLM_MODEL": support.GATEWAY_MODEL}
    values.update(changes)
    return values


def test_import_env_makes_the_first_connection_probes_routes_and_is_idempotent(
    session, fake  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    first = import_env(_factory(session), _environ(fake), ring=rings.private, policy=_loopback_policy(fake))
    assert first.created and first.probe_outcome == "ok" and first.routed
    store = ExecutorRepository()
    connection = store.get_connection(session, first.connection_id)
    assert connection.display_name == IMPORT_DISPLAY_NAME and connection.kind == "http_api"
    route = resolve_route(session, "text_analysis")
    assert route.route.primary_connection_id == first.connection_id
    assert route.primary.settings.gateway_model == support.GATEWAY_MODEL
    assert route.primary.settings.base_url == _loopback_url(fake)
    # The key is sealed, and the worker opens it for the revision's address.
    bound = bind_connection(session, route.primary.revision_id, ring=rings.private,
                            policy=_loopback_policy(fake), context=None)
    bound.adapter.complete(ModelRequest(model_id=support.PIN.model_id, body={
        "max_tokens": 4, "messages": [{"role": "user", "content": "x"}]}))
    assert fake.requests[-1]["authorization"] == f"Bearer {support.KEY}"
    # A second run is a no-op that names the existing connection.
    count = session.execute(text("SELECT count(*) FROM executor_connection")).scalar_one()
    second = import_env(_factory(session), _environ(fake), ring=rings.private, policy=_loopback_policy(fake))
    assert (second.created, second.connection_id) == (False, first.connection_id)
    assert session.execute(text("SELECT count(*) FROM executor_connection")).scalar_one() == count


def test_worker_bootstrap_lists_openrouter_and_preserves_codex_route_with_image_input(
    session, fake  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    store = ExecutorRepository()
    # The suite rolls each test back, but a committed connection of another suite (the dump
    # tests commit theirs) stays in the shared database: count what this test adds, not the table.
    before = len(store.list_connections(session))
    codex = support.seed_connection(session, rings, fake.vpn_url(), name="Codex")
    first = import_env(
        _factory(session), _environ(fake), ring=rings.private, policy=_loopback_policy(fake),
        queue_only=True,
    )
    assert first.created and first.probe_outcome is None and not first.routed
    assert resolve_route(session, "text_analysis").route.primary_connection_id == codex.connection_id
    connection = store.get_connection(session, first.connection_id)
    revision = store.current_revisions(session, [first.connection_id])[first.connection_id]
    assert connection.display_name == IMPORT_DISPLAY_NAME and revision.settings.api_flavour == "openai_chat"
    assert not is_probed_ok(session, store, connection, revision)
    probe = store.list_probes(session, first.connection_id)[0]
    assert probe.state == "requested" and record_probe_started(session, probe.probe_id)
    assert record_probe_result(session, probe.probe_id, outcome="ok",
                               reported_model=support.GATEWAY_MODEL, identity_basis="reported",
                               rate_check="not_reported")
    assert is_probed_ok(session, store, connection, revision)
    second = import_env(
        _factory(session), _environ(fake), ring=rings.private, policy=_loopback_policy(fake),
        queue_only=True,
    )
    assert not second.created and second.connection_id == first.connection_id
    assert len(store.list_connections(session)) == before + 2

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL7WQAAAABJRU5ErkJggg=="
    )
    digest = hashlib.sha256(png).hexdigest()
    descriptor = {"blob_id": str(derive_blob_id(sha256=digest, size=len(png))),
                  "portal_block_id": "blk_" + "a" * 32, "sha256": digest,
                  "size_bytes": len(png), "media_type": "image/png"}
    bound = bind_connection(session, revision.revision_id, ring=rings.private,
                            policy=_loopback_policy(fake), context=None)
    bound.adapter.complete(ModelRequest(model_id=support.PIN.model_id, body={
        "max_tokens": 4, "messages": [{"role": "user", "content": "view"}],
        "images": [descriptor],
    }, image_bytes=png))
    content = fake.requests[-1]["body"]["messages"][-1]["content"]
    assert content[0] == {"type": "text", "text": "view"}
    assert base64.b64decode(content[1]["image_url"]["url"].split(",", 1)[1]) == png
    assert resolve_route(session, "text_analysis").route.primary_connection_id == codex.connection_id


def test_import_env_refuses_a_stub_model_and_does_not_route_a_refused_probe(session) -> None:  # type: ignore[no-untyped-def]
    rings = support.make_rings()
    html = FakeGateway(behaviour="html403").start()
    try:
        assert "gateway stub" in str(_refusal_op(lambda: import_env(
            _factory(session), _environ(html, PROXY_LLM_MODEL="proxy"), ring=rings.private,
            policy=_loopback_policy(html))))
        assert "AUDITMANAGER_SECRETS_KEYS" in str(_refusal_op(lambda: import_env(
            _factory(session), _environ(html), ring=None, policy=_loopback_policy(html))))
        report = import_env(_factory(session), _environ(html), ring=rings.private, policy=_loopback_policy(html))
    finally:
        html.stop()
    assert (report.created, report.probe_outcome, report.routed) == (True, "ip_refused", False)
    assert resolve_route(session, "text_analysis") is None


def _refusal_op(call: Any) -> OperationRefused:
    with pytest.raises(OperationRefused) as caught:
        call()
    return caught.value


# -- rewrap -------------------------------------------------------------------------------------


def test_rewrap_reseals_to_the_active_key_keeps_the_destination_and_the_call_still_opens(
    session, fake  # type: ignore[no-untyped-def]
) -> None:
    old, new = support.make_rings("k1"), support.make_rings("k2")
    connection = support.seed_connection(session, old, fake.vpn_url())
    both = load_private_ring(f"k1:{old.private_text},k2:{new.private_text}", "k2")
    store = ExecutorRepository()
    before = store.current_secrets(session, [connection.connection_id])[connection.connection_id][0]
    assert before.kid == "k1"
    # (The lane database may hold secrets other suites committed under rings this one does not
    # have: `rewrap` is database-wide, so the claims below are about this connection's secret.)
    report = rewrap(_factory(session), ring=both)
    assert report.rewrapped >= 1 and before.secret_id not in report.unreadable
    after = store.current_secrets(session, [connection.connection_id])[connection.connection_id][0]
    assert after.kid == "k2" and after.secret_id != before.secret_id
    assert after.destination == before.destination and after.last4 == before.last4
    assert store.get_secret(session, before.secret_id).replaced_at is not None
    # The master key rotates: the old pair is removed, and the call still opens.
    only_new = load_private_ring(f"k2:{new.private_text}", "k2")
    bound = bind_connection(session, connection.revision_id, ring=only_new, policy=fake.policy(),
                            context=None)
    bound.adapter.complete(ModelRequest(model_id=support.PIN.model_id, body={
        "max_tokens": 4, "messages": [{"role": "user", "content": "x"}]}))
    assert fake.requests[-1]["authorization"] == f"Bearer {support.KEY}"
    # A connection that was probed ok stays usable: the same key under a new envelope.
    record = store.get_connection(session, connection.connection_id)
    revision = store.current_revisions(session, [connection.connection_id])[connection.connection_id]
    assert is_probed_ok(session, store, record, revision)
    # A second run has nothing left to do for it.
    assert rewrap(_factory(session), ring=both).rewrapped == 0
    assert store.current_secrets(session, [connection.connection_id])[
        connection.connection_id][0].secret_id == after.secret_id


def test_rewrap_names_a_secret_whose_key_id_is_not_in_the_ring_and_never_skips_it_silently(
    session, fake  # type: ignore[no-untyped-def]
) -> None:
    lost, active = support.make_rings("k0"), support.make_rings("k2")
    connection = support.seed_connection(session, lost, fake.vpn_url())
    report = rewrap(_factory(session), ring=load_private_ring(f"k2:{active.private_text}", "k2"))
    secret = ExecutorRepository().current_secrets(
        session, [connection.connection_id])[connection.connection_id][0]
    assert secret.secret_id in report.unreadable and secret.kid == "k0", "named, never skipped"


# -- reach ---------------------------------------------------------------------------------------


def test_reach_says_refused_unresolvable_unreachable_or_reachable(fake) -> None:  # type: ignore[no-untyped-def]
    assert reach(f"http://127.0.0.1:{fake.port}", transport="direct",
                 policy=DestinationPolicy(networks=lambda: ())).category == "loopback"
    assert reach(fake.base_url(), transport="direct", policy=fake.policy()).outcome == "reachable"
    closed = fake.policy(dial=lambda address, port: ("127.0.0.1", 1))
    assert reach(fake.base_url(), transport="direct", policy=closed).outcome == "unreachable"
