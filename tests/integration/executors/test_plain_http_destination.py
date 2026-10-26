"""`SEC-RUNNER-CAP-01` (`F-15`): a plain ``http://`` model destination over the served application
and real rows.

Two things are shown here that the unit file cannot: the refusal is what an administrator
receives over the wire, and a connection stored by an earlier build with an ``http://`` public
destination is still readable but is not used. The unit rules are in
``tests/unit/executors/test_model_plain_http.py``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.executors import resolver
from auditmanager.executors.public import (
    ExecutorRepository,
    create_connection,
    request_probe,
)
from auditmanager.executors.runtime import DestinationPolicy, ProbeRunner, bind_connection
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorSecretId
from tests.integration.executors.conftest import driver

Request, dispatch = driver.Request, driver.dispatch

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
SECRET = "sk-legacy-SENTINEL-0001"
LEGACY_URL = "http://legacy-gateway.example.org:8080/v1"

HTTP_SETTINGS = {
    "pin_id": "claude-opus-5", "gateway_model": "anthropic/claude-opus-5", "billing": "metered",
    "allow_client_documents": False, "timeout_seconds": 60, "api_flavour": "openai_chat",
    "base_url": "https://proxy.test/agent/v1", "transport": "direct",
}


def call(surface, method: str, path: str, body: Any = None):
    headers = {"Content-Type": "application/json", "Idempotency-Key": f"plain-{uuid4().hex}"}
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def _connection(surface) -> str:
    created = call(surface, "POST", "/executor-connections",
                   {"kind": "http_api", "display_name": f"plain-{uuid4().hex[:8]}"})
    assert created.status == 201, created.body
    return created.json()["connection_id"]


def _revise(surface, connection_id: str, **changes: Any):
    return call(surface, "POST", f"/executor-connections/{connection_id}/revisions",
                {**HTTP_SETTINGS, **changes})


# -- over the wire ------------------------------------------------------------------------------------


@pytest.mark.parametrize("changes", [
    {"base_url": "http://openrouter.ai/api/v1"},
    {"base_url": "http://93.184.216.34:8080/v1"},
    {"base_url": "http://10.8.0.2:8080/v1"},  # private, but the route is `direct`
    {"base_url": "http://user:secret@127.0.0.1:8080/v1"},
])
def test_an_administrator_who_names_plain_http_to_the_open_internet_gets_the_typed_refusal(
    surface, changes  # type: ignore[no-untyped-def]
) -> None:
    refused = _revise(surface, _connection(surface), **changes)
    assert refused.status == 422, refused.body
    body = refused.json()
    assert body["error_code"] == "validation_failed"
    assert (body["details"]["field"], body["details"]["constraint"]) == ("base_url", "base_url_invalid")
    assert changes["base_url"].split("/")[2] not in refused.body.decode("utf-8", "replace"), \
        "the refusal must not echo the address"


@pytest.mark.parametrize("changes", [
    {},  # https stays what it was
    {"base_url": "http://10.8.0.2:11434/v1", "transport": "vpn"},
    {"base_url": "http://127.0.0.1:11434/v1"},
    {"base_url": "http://localhost:11434/v1", "transport": "ssh_tunnel", "ssh_host": "gpu.test",
     "ssh_port": 22, "ssh_user": "am"},
])
def test_https_and_the_sanctioned_plain_http_routes_are_still_accepted(
    surface, changes  # type: ignore[no-untyped-def]
) -> None:
    accepted = _revise(surface, _connection(surface), **changes)
    assert accepted.status == 201, accepted.body


# -- a connection stored before this slice --------------------------------------------------------------


def _legacy(session, rings) -> tuple[str, str, str]:  # type: ignore[no-untyped-def]
    """``(connection_id, revision_id, secret_id)`` as an earlier build stored them: a revision
    with a plain ``http://`` public destination (it never passed today's validation) and a key
    sealed to the destination of that day."""
    store = ExecutorRepository()
    connection = create_connection(
        session, kind="http_api", display_name=f"legacy-{uuid4().hex[:8]}",
        roles=support.ADMIN_ROLES, idempotency_key=support.unique(), actor_uid=support.ACTOR)
    revision = store.insert_revision(
        session, connection.connection_id, support.settings(LEGACY_URL, transport="direct"),
        actor_uid=support.ACTOR)
    secret_id = str(ExecutorSecretId.new())
    destination = "direct||http://legacy-gateway.example.org:8080"
    kid, envelope = rings.public.seal(SECRET.encode("utf-8"), {
        "secret_id": secret_id, "connection_id": connection.connection_id,
        "purpose": "api_key", "destination": destination})
    store.replace_secret(
        session, secret_id=secret_id, connection_id=connection.connection_id, purpose="api_key",
        kid=kid, destination=destination, ciphertext=envelope, last4=SECRET[-4:],
        public_material=None, actor_uid=support.ACTOR)
    return connection.connection_id, revision.revision_id, secret_id


def test_a_stored_plain_http_connection_is_still_read(session, surface, rings) -> None:  # type: ignore[no-untyped-def]
    connection_id, revision_id, secret_id = _legacy(session, rings)

    listed = call(surface, "GET", "/executor-connections")
    assert listed.status == 200, listed.body
    row = next(item for item in listed.json()["items"] if item["connection_id"] == connection_id)
    assert row["current_revision_id"] == revision_id

    detail = call(surface, "GET", f"/executor-connections/{connection_id}")
    assert detail.status == 200, detail.body
    document = detail.json()
    assert [item["revision_id"] for item in document["revisions"]] == [revision_id]
    assert document["revisions"][0]["base_url"] == LEGACY_URL
    secrets = document["connection"]["secrets"]
    assert [item["secret_id"] for item in secrets] == [secret_id]
    assert secrets[0]["bound_to_current_revision"] is False, \
        "the key is not bound to a destination the rules still allow, and the screen says so"
    assert SECRET not in listed.body.decode("utf-8", "replace") + detail.body.decode("utf-8", "replace")


def test_a_new_run_through_it_is_refused_before_the_key_is_opened(
    session, rings, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    _, revision_id, _ = _legacy(session, rings)
    opened: list[str] = []

    def spy(*args: Any, **kwargs: Any) -> str:
        opened.append(kwargs.get("destination", ""))
        raise AssertionError("the key was opened for a destination the rules refuse")

    monkeypatch.setattr(resolver, "open_secret", spy)
    policy = DestinationPolicy(networks=lambda: ())
    with pytest.raises(DomainError) as refused:
        bind_connection(session, revision_id, ring=rings.private, policy=policy, context=None)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert (refused.value.detail_fields["field"], refused.value.detail_fields["constraint"]) == (
        "base_url", "base_url_invalid")
    assert opened == []


def test_the_run_stage_binding_gets_the_same_refusal(session, rings) -> None:  # type: ignore[no-untyped-def]
    """``DatabaseProviders.resolve`` is what every stage of a Run calls for its frozen revision."""
    from auditmanager.analysis.text import ProviderConfig, ProviderMode
    from auditmanager.bootstrap.providers import DatabaseProviders

    _, revision_id, _ = _legacy(session, rings)
    config = ProviderConfig(mode=ProviderMode.LIVE, model_id=support.PIN.model_id,
                            run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=True)
    providers = DatabaseProviders(ring=rings.private, policy=DestinationPolicy(networks=lambda: ()),
                                  base_config=config, ceiling_usd=1.0)
    with pytest.raises(DomainError) as refused:
        providers.resolve(session, SimpleNamespace(connection_revision_id=revision_id), None)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert refused.value.detail_fields["constraint"] == "base_url_invalid"


def test_the_key_of_a_stored_plain_http_connection_cannot_be_replaced_without_a_new_revision(
    session, surface, rings  # type: ignore[no-untyped-def]
) -> None:
    connection_id, _, _ = _legacy(session, rings)
    refused = call(surface, "POST", f"/executor-connections/{connection_id}/secrets",
                   {"purpose": "api_key", "value": "sk-replacement-0002"})
    assert refused.status == 422, refused.body
    assert refused.json()["details"]["constraint"] == "base_url_invalid"
    corrected = _revise(surface, connection_id)  # the administrator moves it to https
    assert corrected.status == 201, corrected.body


def test_a_probe_of_a_stored_plain_http_connection_sends_nothing_and_does_not_pass(
    session, rings
) -> None:  # type: ignore[no-untyped-def]
    connection_id, _, _ = _legacy(session, rings)
    fake = FakeGateway(behaviour="ok").start()
    try:
        probe = request_probe(
            session, connection_id=connection_id, roles=support.ADMIN_ROLES,
            idempotency_key=support.unique(), actor_uid=support.ACTOR)
        runner = ProbeRunner(lambda: nullcontext(session), ring=rings.private, policy=fake.policy())
        claimed = ExecutorRepository().claim_requested_probe(session)
        assert claimed is not None and claimed.probe_id == probe.probe_id
        runner._run(claimed)
        row = session.execute(text(
            "SELECT outcome, detail FROM executor_probe WHERE probe_id = :id"),
            {"id": probe.probe_id}).mappings().one()
    finally:
        fake.stop()
    assert fake.requests == [], "nothing was sent"
    assert row["outcome"] != "ok"
    # Known limit, recorded in docs/program/SEC-RUNNER-CAP-01.md: the probe worker does not map
    # the refusal to `destination_refused` (probe_runner.py is outside this slice).
    assert row["outcome"] == "protocol_error"
    assert SECRET not in (row["detail"] or "")
