"""The worker's probe (`EXEC-HTTP-01`, plan section 4.1) against real PostgreSQL and a local gateway.

``ProbeRunner`` is what the worker's probe thread calls. Each test records a probe the way the
``api`` does (``request_probe``), lets the runner take it, and reads the stored row back. No
network beyond the local fake gateway, and no paid call.
"""

from __future__ import annotations

import importlib.util
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.executors.public import (
    ExecutorRepository,
    create_connection,
    request_probe,
)
from auditmanager.executors.runtime import DestinationPolicy, ProbeRunner

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
def gateway():  # type: ignore[no-untyped-def]
    started: list[Any] = []

    def make(**options: Any) -> Any:
        started.append(FakeGateway(**options).start())
        return started[-1]

    yield make
    for item in started:
        item.stop()


def _run_probe(session: Any, rings: Any, connection_id: str, policy: DestinationPolicy,
               ring: Any = "same") -> dict[str, Any]:
    probe = request_probe(
        session, connection_id=connection_id, roles=support.ADMIN_ROLES,
        idempotency_key=support.unique(), actor_uid=support.ACTOR,
    )
    runner = ProbeRunner(
        lambda: nullcontext(session), ring=rings.private if ring == "same" else ring,
        policy=policy,
    )
    claimed = ExecutorRepository().claim_requested_probe(session)
    assert claimed is not None and claimed.probe_id == probe.probe_id
    runner._run(claimed)
    return dict(session.execute(text(
        "SELECT * FROM executor_probe WHERE probe_id = :id"), {"id": probe.probe_id}).mappings().one())


def _seed(session: Any, rings: Any, gateway: Any, **changes: Any) -> Any:
    return support.seed_connection(
        session, rings, gateway.base_url(), probe=None, routed=False, **changes)


def test_a_good_gateway_is_ok_and_the_row_carries_what_the_screen_shows(session, gateway) -> None:  # type: ignore[no-untyped-def]
    rings = support.make_rings()
    fake = gateway(cost=(1200 * support.PIN.input_per_mtok_usd + 340 * support.PIN.output_per_mtok_usd) / 1e6)
    seeded = _seed(session, rings, fake)
    row = _run_probe(session, rings, seeded.connection_id, fake.policy())
    assert (row["state"], row["outcome"], row["reported_model"], row["identity_basis"]) == (
        "finished", "ok", support.GATEWAY_MODEL, "reported")
    assert row["rate_check"] == "checked" and row["http_status"] == 200 and row["latency_ms"] >= 0
    assert row["secret_id"] == seeded.secret_id and row["started_at"] and row["finished_at"]
    assert fake.requests[0]["authorization"] == f"Bearer {support.KEY}", "the opened key was sent"


def test_ip_refused_and_credential_refused_are_told_apart(session, gateway) -> None:  # type: ignore[no-untyped-def]
    rings = support.make_rings()
    html = gateway(behaviour="html403")
    seeded = _seed(session, rings, html)
    assert _run_probe(session, rings, seeded.connection_id, html.policy())["outcome"] == "ip_refused"
    json_401 = gateway(behaviour="json401")
    other = _seed(session, rings, json_401, name="second")
    row = _run_probe(session, rings, other.connection_id, json_401.policy())
    assert row["outcome"] == "credential_refused" and row["http_status"] == 401


def test_another_model_is_a_model_mismatch_and_stores_no_body(session, gateway) -> None:  # type: ignore[no-untyped-def]
    rings = support.make_rings()
    fake = gateway(behaviour="wrong_model")
    row = _run_probe(session, rings, _seed(session, rings, fake).connection_id, fake.policy())
    assert row["outcome"] == "model_mismatch" and row["reported_model"] == "openai/gpt-5-mini"
    assert len(row["detail"]) <= 500 and support.KEY not in str(row)


def test_a_connection_without_a_key_or_with_a_key_for_another_address_is_secret_unreadable(
    session, gateway  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway()
    bare = create_connection(
        session, kind="http_api", display_name="no key", roles=support.ADMIN_ROLES,
        idempotency_key=support.unique(), actor_uid=support.ACTOR)
    support.revise(session, bare.connection_id, fake.base_url())
    assert _run_probe(session, rings, bare.connection_id, fake.policy())["outcome"] == "secret_unreadable"
    # A key entered for one address does not open for the next revision's.
    moved = _seed(session, rings, fake, name="moved")
    # (A new path on the same origin keeps the key readable; another host unbinds it.)
    support.revise(session, moved.connection_id,
                   fake.base_url().replace("gateway.example.test", "other.example.test"))
    row = _run_probe(session, rings, moved.connection_id, fake.policy())
    assert row["outcome"] == "secret_unreadable" and fake.requests == []
    # ... and a worker without the ring opens nothing.
    again = _seed(session, rings, fake, name="no-ring")
    assert _run_probe(session, rings, again.connection_id, fake.policy(), ring=None)["outcome"] == "secret_unreadable"


def test_an_unpermitted_address_is_destination_refused_by_default(session, gateway) -> None:  # type: ignore[no-untyped-def]
    rings = support.make_rings()
    fake = gateway()
    seeded = support.seed_connection(
        session, rings, f"http://127.0.0.1:{fake.port}/v1", probe=None, routed=False)
    row = _run_probe(session, rings, seeded.connection_id, DestinationPolicy(networks=lambda: ()))
    assert row["outcome"] == "destination_refused" and fake.requests == []


def test_kinds_this_release_does_not_serve_end_as_kind_not_served(session, gateway) -> None:  # type: ignore[no-untyped-def]
    rings = support.make_rings()
    fake = gateway()
    pull = create_connection(
        session, kind="pull", display_name="session", roles=support.ADMIN_ROLES,
        idempotency_key=support.unique(), actor_uid=support.ACTOR)
    from auditmanager.executors.public import RevisionSettings, revise_connection, pinned_models

    revise_connection(
        session, connection_id=pull.connection_id,
        settings=RevisionSettings(
            pin_id=support.PIN.model_id, gateway_model=support.PIN.model_id, billing="not_metered",
            allow_client_documents=False, timeout_seconds=60, pull_client="agent",
            answer_deadline_seconds=300, max_claimed_tasks=1),
        pinned_model_ids={pin.model_id for pin in pinned_models()}, roles=support.ADMIN_ROLES,
        idempotency_key=support.unique(), actor_uid=support.ACTOR)
    assert _run_probe(session, rings, pull.connection_id, fake.policy())["outcome"] == "kind_not_served"
    tunnel = _seed(session, rings, fake, name="tunnel")
    support.revise(session, tunnel.connection_id, "http://localhost:11434/v1", transport="ssh_tunnel",
                   ssh_host="gpu.example.test", ssh_port=22, ssh_user="am")
    assert _run_probe(session, rings, tunnel.connection_id, fake.policy())["outcome"] == "kind_not_served"
