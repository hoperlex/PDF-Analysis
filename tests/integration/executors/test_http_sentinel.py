"""`EXEC-HTTP-01`, plan section 4.2: the sentinel test extended to the probe and the call path.

`EXEC-SEAL-01` shows a key set through the API occurs in no response, event, ledger row, log or
dump. This extends it to what the worker does with the key: **open, probe, call, fail, journal**.
The gateway used here is the worst case -- its error body repeats the key it was sent -- so a
detail, an exception message or a stored stage error that copied a body would carry the sentinel.

Every scan is first shown able to find a planted sentinel, so a green result is not a scan that
looks nowhere.
"""

from __future__ import annotations

import base64
import importlib.util
import logging
import os
import re
import shutil
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors.public import ExecutorRepository, request_probe
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.executors.runtime import ProbeRunner, bind_connection
from tests.support.v1_reference_profile import resolve_reference_profile

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
blob_store = harness.blob_store

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
SENTINEL = f"sk-SENTINEL-HTTP-{uuid4().hex}-do-not-leak"


def leaks(haystack: str, needle: str = SENTINEL) -> bool:
    spellings = {needle, needle.encode().hex(), base64.b64encode(needle.encode()).decode(),
                 base64.urlsafe_b64encode(needle.encode()).decode()}
    return any(spelling in haystack for spelling in spellings)


def test_the_scan_can_find_a_planted_sentinel() -> None:
    assert leaks(f"Incorrect API key provided: {SENTINEL}")
    assert leaks(SENTINEL.encode().hex()) and leaks(base64.b64encode(SENTINEL.encode()).decode())
    assert not leaks("a probe detail with no key in it")


def _every_row(session: Any) -> list[str]:
    """``row_to_json`` of every row of every product and executor table, norm corpus excepted."""
    tables = session.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
        "AND tablename NOT LIKE 'norm\\_%' AND tablename NOT IN ('alembic_version', 'blob')"
    )).scalars().all()
    rows: list[str] = []
    for table in tables:
        rows.extend(session.execute(text(f'SELECT row_to_json(t)::text FROM "{table}" t')).scalars().all())
    return rows


def _is_planted(rows: list[str]) -> bool:
    return any(leaks(row) for row in rows)


def test_the_sentinel_never_leaves_the_probe_and_the_call_even_when_the_gateway_echoes_it(
    session, caplog, capsys  # type: ignore[no-untyped-def]
) -> None:
    caplog.set_level(logging.DEBUG)
    rings = support.make_rings()
    fake = FakeGateway(behaviour="echo401").start()
    try:
        seeded = support.seed_connection(
            session, rings, fake.base_url(), key=SENTINEL, probe=None, routed=False)
        probe = request_probe(
            session, connection_id=seeded.connection_id, roles=support.ADMIN_ROLES,
            idempotency_key=support.unique(), actor_uid=support.ACTOR)
        runner = ProbeRunner(lambda: nullcontext(session), ring=rings.private, policy=fake.policy())
        claimed = ExecutorRepository().claim_requested_probe(session)
        assert claimed is not None and claimed.probe_id == probe.probe_id
        runner._run(claimed)
        outcome = session.execute(text(
            "SELECT outcome FROM executor_probe WHERE probe_id = :p"), {"p": probe.probe_id}).scalar_one()
        assert outcome == "credential_refused"
        # The call path: the opened key goes out, the echoing body comes back, and what the
        # adapter raises names no key.
        bound = bind_connection(session, seeded.revision_id, ring=rings.private,
                                policy=fake.policy(), context=None)
        with pytest.raises(ProxyDispatchError) as failed:
            bound.adapter.complete(ModelRequest(model_id=support.PIN.model_id, body={
                "max_tokens": 4, "messages": [{"role": "user", "content": "x"}]}))
        rendered = " ".join([str(failed.value), repr(failed.value), repr(failed.value.detail_fields),
                             failed.value.custom_message or ""])
        assert not leaks(rendered), rendered
        assert fake.requests and fake.requests[0]["authorization"] == f"Bearer {SENTINEL}", \
            "the key really was sent, so the scans below are not vacuous"
    finally:
        fake.stop()
    rows = _every_row(session)
    assert any("executor_probe" in row or probe.probe_id in row for row in rows)
    assert not _is_planted(rows), "a stored row carries the key"
    printed = capsys.readouterr()
    assert not leaks(caplog.text + printed.out + printed.err)
    assert SENTINEL not in repr(rings.public) + repr(rings.private) + repr(bound)


def test_the_row_scan_can_fail(session) -> None:  # type: ignore[no-untyped-def]
    """A sentinel planted in a stored probe detail is found by the very scan above."""
    rings = support.make_rings()
    seeded = support.seed_connection(session, rings, "http://gateway.example.test/v1", probe=None,
                                     routed=False)
    probe = request_probe(
        session, connection_id=seeded.connection_id, roles=support.ADMIN_ROLES,
        idempotency_key=support.unique(), actor_uid=support.ACTOR)
    session.execute(text(
        "UPDATE executor_probe SET detail = :d WHERE probe_id = :p"),
        {"d": f"planted {SENTINEL}", "p": probe.probe_id})
    assert _is_planted(_every_row(session))


def test_a_failed_run_stores_no_key_in_its_stage_error_or_call_rows(
    session, blob_store  # type: ignore[no-untyped-def]
) -> None:
    """A whole run against the echoing gateway fails; nothing it stored carries the key."""
    from auditmanager.bootstrap.providers import DatabaseProviders, UnboundAdapter
    from auditmanager.analysis.text import ProviderConfig, ProviderMode
    from auditmanager.runs import execute_run, start_audit_run

    seeded = harness.seed_version(session, blob_store)
    rings = support.make_rings()
    fake = FakeGateway(behaviour="echo401").start()
    config = ProviderConfig(mode=ProviderMode.LIVE, model_id=support.PIN.model_id,
                            run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=True)
    try:
        support.seed_connection(session, rings, fake.base_url(), key=SENTINEL)
        providers = DatabaseProviders(ring=rings.private, policy=fake.policy(), base_config=config,
                                      ceiling_usd=1.0)
        started = start_audit_run(
            session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="live",
            idempotency_key=IdempotencyKey(f"sentinel-{uuid4().hex[:24]}"),
            connection_route=providers.freeze)
        result = execute_run(session, started.run_id, blob_store=blob_store,
                             adapter=UnboundAdapter(), provider_config=config,
                             providers=providers.resolve, text_profiles=resolve_reference_profile)
    finally:
        fake.stop()
    assert result.terminal_state == "failed"
    assert not _is_planted(_every_row(session))


def _pg_dump(server_major: int) -> str:
    for candidate in (shutil.which("pg_dump"), f"/usr/lib/postgresql/{server_major}/bin/pg_dump"):
        if candidate and os.path.exists(candidate):
            out = subprocess.run([candidate, "--version"], capture_output=True, text=True).stdout
            found = re.search(r"(\d+)(?:\.\d+)?\s*(?:\(|$)", out)
            if found and int(found.group(1)) >= server_major:
                return candidate
    pytest.fail(f"no pg_dump of major {server_major} or newer is available; this check never skips")


def test_a_dump_after_a_probe_against_an_echoing_gateway_carries_no_key(engine) -> None:  # type: ignore[no-untyped-def]
    """Committed on purpose: ``pg_dump`` reads its own snapshot. The rows stay (append-only and
    harmless: ciphertext no key here opens), and every assertion is keyed to ids this test made."""
    rings = support.make_rings()
    fake = FakeGateway(behaviour="echo401").start()
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    try:
        with factory() as work:
            seeded = support.seed_connection(
                work, rings, fake.base_url(), key=SENTINEL, probe=None, routed=False,
                name="dump-sentinel-http")
            probe = request_probe(
                work, connection_id=seeded.connection_id, roles=support.ADMIN_ROLES,
                idempotency_key=support.unique(), actor_uid=support.ACTOR)
            work.commit()
            ProbeRunner(lambda: nullcontext(work), ring=rings.private, policy=fake.policy())._run(
                ExecutorRepository().claim_requested_probe(work))
            work.commit()
    finally:
        fake.stop()
    with engine.connect() as probe_connection:
        server_major = int(probe_connection.execute(text("SHOW server_version_num")).scalar_one()) // 10000
    url = engine.url
    dump = subprocess.run(
        [_pg_dump(server_major), "--data-only", "--no-owner", "-h", url.host or "localhost",
         "-p", str(url.port or 5432), "-U", url.username or "", "-d", url.database or "",
         "-t", "public.executor_*", "-t", "public.audit_event", "-t", "public.command_record",
         "-t", "public.provider_call_effect", "-t", "public.model_call", "-t", "public.stage_result"],
        capture_output=True, text=True, env=dict(os.environ, PGPASSWORD=url.password or ""),
        timeout=120,
    )
    assert dump.returncode == 0, dump.stderr
    assert seeded.connection_id in dump.stdout and probe.probe_id in dump.stdout
    assert "credential_refused" in dump.stdout, "the probe's outcome is in the dump"
    assert not leaks(dump.stdout)
