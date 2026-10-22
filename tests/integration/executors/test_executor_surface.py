"""`EXEC-SEAL-01`: the ten operations over the served application, behind the real seam.

Drives ``build_router(executors=ExecutorAdapter(...))`` through the real middlewares and the
role register (``tests/integration/api/driver.py``), so the statuses, the envelope and the
absence of every secret are what a caller sees. The role sweep over every operation is
``tests/integration/api/test_role_register.py``; this file drives the behaviour behind it.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest

from auditmanager.analysis.public import pinned_models
from tests.integration.executors.conftest import build_surface, driver

Request, dispatch = driver.Request, driver.dispatch

HTTP_SETTINGS = {
    "pin_id": "claude-opus-5", "gateway_model": "anthropic/claude-opus-5", "billing": "metered",
    "allow_client_documents": False, "timeout_seconds": 60, "api_flavour": "openai_chat",
    "base_url": "https://proxy.test/agent/v1", "transport": "direct",
}
SSH_SETTINGS = {
    "pin_id": "claude-sonnet-5", "gateway_model": "claude-sonnet-5", "billing": "metered",
    "allow_client_documents": False, "timeout_seconds": 120, "ssh_host": "gpu.test",
    "ssh_port": 22, "ssh_user": "am", "ssh_profile": "claude_code_headless",
}


def call(surface, method: str, path: str, body: Any = None, *, keyed: bool = True):
    headers = {"Content-Type": "application/json"}
    if keyed:
        headers["Idempotency-Key"] = f"exec-{uuid4().hex}"
    payload = b"" if body is None else json.dumps(body).encode()
    return dispatch(surface, Request.build(method, path, headers=headers, body=payload))


def walk(node: Any):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def serve(surface, session, connection_id: str) -> None:
    """A key and a finished ``ok`` probe through the API and the worker's act: what `EXEC-HTTP-01`
    requires before a connection can be routed."""
    from auditmanager.executors.public import record_probe_result, record_probe_started

    keyed = call(surface, "POST", f"/executor-connections/{connection_id}/secrets",
                 {"purpose": "api_key", "value": f"sk-served-{uuid4().hex}"})
    assert keyed.status == 201, keyed.body
    probe = call(surface, "POST", f"/executor-connections/{connection_id}/probes")
    assert probe.status == 202, probe.body
    assert record_probe_started(session, probe.json()["probe_id"])
    assert record_probe_result(session, probe.json()["probe_id"], outcome="ok",
                               reported_model="anthropic/claude-opus-5",
                               identity_basis="reported", rate_check="not_reported")


def made(surface, kind: str = "http_api", settings: dict[str, Any] | None = None) -> str:
    created = call(surface, "POST", "/executor-connections", {"kind": kind, "display_name": "n"})
    assert created.status == 201, created.body
    connection_id = created.json()["connection_id"]
    revised = call(surface, "POST", f"/executor-connections/{connection_id}/revisions",
                   settings or HTTP_SETTINGS)
    assert revised.status == 201, revised.body
    return connection_id


def test_the_journey_has_the_ruled_statuses_and_no_null_and_no_secret(surface, session) -> None:
    bodies = []
    created = call(surface, "POST", "/executor-connections", {"kind": "http_api", "display_name": "Прокси"})
    assert created.status == 201
    connection = created.json()
    assert connection["kind"] == "http_api" and connection["secrets"] == []
    assert "current_revision_id" not in connection and "archived_at" not in connection
    cid = connection["connection_id"]
    bodies.append(connection)

    revised = call(surface, "POST", f"/executor-connections/{cid}/revisions", HTTP_SETTINGS)
    assert revised.status == 201
    revision = revised.json()
    assert (revision["revision_no"], revision["pin_id"], revision["gateway_model"]) == (
        1, "claude-opus-5", "anthropic/claude-opus-5")
    assert "latest_probe" not in revision and "host_key_fingerprint" not in revision
    bodies.append(revision)

    sealed = call(surface, "POST", f"/executor-connections/{cid}/secrets",
                  {"purpose": "api_key", "value": "sk-journey-0123456789abcdef"})
    assert sealed.status == 201
    metadata = sealed.json()
    assert set(metadata) == {"secret_id", "connection_id", "purpose", "last4", "kid",
                             "bound_to_current_revision", "set_at", "set_by"}
    assert metadata["last4"] == "cdef" and metadata["bound_to_current_revision"] is True
    bodies.append(metadata)

    probe = call(surface, "POST", f"/executor-connections/{cid}/probes")
    assert probe.status == 202
    assert probe.json()["state"] == "requested" and probe.json()["secret_id"] == metadata["secret_id"]
    bodies.append(probe.json())
    from auditmanager.executors.public import record_probe_result, record_probe_started

    # The worker takes the probe and it passes (`EXEC-HTTP-01`): only then can it be routed.
    assert record_probe_started(session, probe.json()["probe_id"])
    assert record_probe_result(session, probe.json()["probe_id"], outcome="ok",
                               reported_model="anthropic/claude-opus-5",
                               identity_basis="reported", rate_check="not_reported")

    route = call(surface, "PUT", "/executor-routes",
                 {"work_kind": "text_analysis", "primary_connection_id": cid})
    assert route.status == 200 and "standby_connection_id" not in route.json()
    bodies.append(route.json())

    detail = call(surface, "GET", f"/executor-connections/{cid}", keyed=False)
    assert detail.status == 200
    shown = detail.json()
    assert shown["connection"]["routed_work_kinds"] == ["text_analysis"]
    assert shown["revisions"][0]["latest_probe"]["probe_id"] == probe.json()["probe_id"]
    assert [p["probe_id"] for p in shown["probes"]] == [probe.json()["probe_id"]]
    bodies.append(shown)

    listed = call(surface, "GET", "/executor-connections", keyed=False)
    assert listed.status == 200
    assert [pin["pin_id"] for pin in listed.json()["pinned_models"]] == [
        pin.model_id for pin in pinned_models()]
    assert {"pin_id", "input_per_mtok_usd", "output_per_mtok_usd"} == set(
        listed.json()["pinned_models"][0])
    assert any(item["connection_id"] == cid for item in listed.json()["items"])
    routes = call(surface, "GET", "/executor-routes", keyed=False)
    assert routes.status == 200 and routes.json()["items"][0]["work_kind"] == "text_analysis"
    bodies.extend([listed.json(), routes.json()])

    for body in bodies:
        assert not [n for n in walk(body) if n is None], "an optional property is absent, never null"
    assert "sk-journey" not in json.dumps(bodies)


def test_a_generated_ssh_key_answers_its_public_half_only(surface) -> None:
    cid = made(surface, "ssh_command", SSH_SETTINGS)
    generated = call(surface, "POST", f"/executor-connections/{cid}/ssh-key")
    assert generated.status == 201
    body = generated.json()
    assert set(body) == {"sealed_private_key", "public_key", "authorized_keys_line"}
    assert body["public_key"].startswith("ssh-ed25519 ")
    assert body["authorized_keys_line"] == f"restrict {body['public_key']} auditmanager:{cid}"
    assert body["sealed_private_key"]["public_key"] == body["public_key"]
    assert "PRIVATE KEY" not in generated.body.decode()
    detail = call(surface, "GET", f"/executor-connections/{cid}", keyed=False).json()
    assert [s["purpose"] for s in detail["connection"]["secrets"]] == ["ssh_private_key"]


def test_a_secret_has_no_read_counterpart(surface) -> None:
    cid = made(surface)
    call(surface, "POST", f"/executor-connections/{cid}/secrets",
         {"purpose": "api_key", "value": "sk-write-only-0123456789"})
    for path in (f"/executor-connections/{cid}/secrets",
                 f"/executor-connections/{cid}/secrets/api_key",
                 f"/executor-connections/{cid}/ssh-key"):
        answer = call(surface, "GET", path, keyed=False)
        assert answer.status in (404, 405), (path, answer.status)
        assert b"sk-write-only" not in answer.body


def test_an_expert_reads_and_is_refused_every_write(session, admin_account, rings) -> None:
    expert = build_surface(session, rings.public, roles=frozenset({"expert"}))
    assert call(expert, "GET", "/executor-connections", keyed=False).status == 200
    assert call(expert, "GET", "/executor-routes", keyed=False).status == 200
    refused = call(expert, "POST", "/executor-connections", {"kind": "pull", "display_name": "n"})
    assert refused.status == 403
    assert refused.json()["error_code"] == "permission_denied"
    assert refused.json()["details"] == {"required_capability": "role:admin"}


def test_without_a_public_key_the_secret_is_a_503_and_nothing_is_stored(session, admin_account) -> None:
    bare = build_surface(session, None, roles=frozenset({"admin"}))
    cid = made(bare)
    answer = call(bare, "POST", f"/executor-connections/{cid}/secrets",
                  {"purpose": "api_key", "value": "sk-no-ring-0123456789"})
    assert answer.status == 503
    assert answer.json()["error_code"] == "dependency_unavailable"
    assert answer.json()["details"] == {"dependency": "secrets_public_key_missing"}
    assert b"sk-no-ring" not in answer.body
    assert call(bare, "GET", f"/executor-connections/{cid}", keyed=False).json()[
        "connection"]["secrets"] == []


@pytest.mark.parametrize(("settings", "details"), [
    ({**HTTP_SETTINGS, "pin_id": "gpt-x"}, {"field": "pin_id", "constraint": "model_not_pinned"}),
    ({**HTTP_SETTINGS, "base_url": "https://proxy.test/v1?k=1"},
     {"field": "base_url", "constraint": "base_url_invalid"}),
    ({**HTTP_SETTINGS, "ssh_user": "am"}, {"field": "ssh_user", "constraint": "field_not_for_kind"}),
])
def test_a_refused_revision_is_a_422_with_a_field_and_a_constraint(surface, settings, details) -> None:
    cid = call(surface, "POST", "/executor-connections",
               {"kind": "http_api", "display_name": "n"}).json()["connection_id"]
    answer = call(surface, "POST", f"/executor-connections/{cid}/revisions", settings)
    assert answer.status == 422
    assert answer.json()["error_code"] == "validation_failed"
    assert answer.json()["details"] == details


def test_conflicts_and_unknown_identities_use_the_catalogue(surface, session) -> None:
    bare = call(surface, "POST", "/executor-connections",
                {"kind": "http_api", "display_name": "n"}).json()["connection_id"]
    answer = call(surface, "POST", f"/executor-connections/{bare}/secrets",
                  {"purpose": "api_key", "value": "sk-no-revision-0123456789"})
    assert (answer.status, answer.json()["details"]) == (409, {"conflict_reason": "no_revision"})
    assert call(surface, "GET", f"/executor-connections/exc_{'0' * 26}", keyed=False).status == 404
    assert call(surface, "GET", "/executor-connections/not-an-id", keyed=False).status in (404, 422)
    routed = made(surface)
    refused = call(surface, "PUT", "/executor-routes",
                   {"work_kind": "text_analysis", "primary_connection_id": routed})
    assert (refused.status, refused.json()["details"]) == (
        409, {"conflict_reason": "connection_not_probed"}), "`EXEC-HTTP-01`: not probed, not routed"
    serve(surface, session, routed)
    assert call(surface, "PUT", "/executor-routes",
                {"work_kind": "text_analysis", "primary_connection_id": routed}).status == 200
    archived = call(surface, "POST", f"/executor-connections/{routed}/archive")
    assert (archived.status, archived.json()["details"]) == (409, {"conflict_reason": "connection_routed"})


def test_a_replay_with_the_same_key_answers_the_same_connection(surface) -> None:
    headers = {"Content-Type": "application/json", "Idempotency-Key": f"exec-{uuid4().hex}"}
    body = json.dumps({"kind": "pull", "display_name": "replayed"}).encode()
    first = dispatch(surface, Request.build("POST", "/executor-connections", headers=headers, body=body))
    again = dispatch(surface, Request.build("POST", "/executor-connections", headers=headers, body=body))
    assert (first.status, again.status) == (201, 201)
    assert first.json()["connection_id"] == again.json()["connection_id"]
    changed = dispatch(surface, Request.build(
        "POST", "/executor-connections", headers=headers,
        body=json.dumps({"kind": "pull", "display_name": "changed"}).encode()))
    assert changed.status == 409
