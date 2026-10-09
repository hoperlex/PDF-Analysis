"""Exercise the W53 proxy and durable execution on disposable local services.

The caller supplies DATABASE_URL and the five S3_* variables for an isolated,
migrated 0017 database and a private bucket. No provider credential is used.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import socket
import struct
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import ProviderConfig, ProviderMode
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.proxy import ProxyAdapter, ProxyDispatchError, ProxySettings
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage import S3BlobStore, S3StorageSettings


ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "tests/integration/runs/harness.py"
SPEC = importlib.util.spec_from_file_location("w53_rehearsal_harness", HARNESS)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = harness
SPEC.loader.exec_module(harness)


class FaultProxy(BaseHTTPRequestHandler):
    counts: dict[str, int] = {}
    bodies: dict[str, list[str]] = {}

    def log_message(self, *_args: object) -> None:
        return  # Do not log Authorization, body or transport detail.

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        scenario = self.path.split("/", 2)[1]
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.counts[scenario] = self.counts.get(scenario, 0) + 1
        self.bodies.setdefault(scenario, []).append(hashlib.sha256(body).hexdigest())
        if scenario == "reset":
            self.connection.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
            )
            self.connection.close()
            return
        status = {"rate": 429, "foreign": 503, "refusal": 400}[scenario]
        payload = b'{"error":{"code":"upstream_unavailable"}}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if scenario == "rate":
            self.send_header("Retry-After", "2")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _request() -> ModelRequest:
    return ModelRequest(
        model_id="claude-opus-5",
        idempotency_scope="run_w53_rehearsal",
        body={
            "max_tokens": 32,
            "system": "Only a disposable W53 probe",
            "messages": [{"role": "user", "content": "probe"}],
        },
    )


def _adapter(scenario: str, port: int) -> ProxyAdapter:
    return ProxyAdapter(
        ProxySettings(
            base_url=f"http://127.0.0.1:{port}/{scenario}",
            token="w53-disposable-secret-never-log",
            model="proxy",
        )
    )


def _direct_classes(port: int) -> None:
    expected = {
        "nosend": ("not_sent", True, 0.0),
        "rate": ("rate_limited", True, 2.0),
        "reset": ("outcome_unknown", False, 0.0),
        "foreign": ("outcome_unknown", False, 0.0),
        "refusal": ("definite_refusal", False, 0.0),
    }
    for scenario, wanted in expected.items():
        target = port + 1 if scenario == "nosend" else port
        try:
            _adapter(scenario, target).complete(_request())
        except ProxyDispatchError as error:
            observed = (error.dispatch_class, error.retry_safe,
                        error.retry_after_seconds)
            assert observed == wanted, (scenario, observed, wanted)
        else:
            raise AssertionError(f"{scenario}: expected typed proxy failure")
        print(f"adapter {scenario}: {wanted[0]}, safe={wanted[1]}, after={wanted[2]}")


def _durable_runs(port: int) -> None:
    import os

    engine = create_database_engine(
        DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"]))
    )
    store = S3BlobStore(S3StorageSettings.from_env())
    store.check_access()
    config = ProviderConfig(
        mode=ProviderMode.LIVE, model_id="claude-opus-5",
        run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=True,
    )
    try:
        for scenario in ("nosend", "rate", "reset", "foreign", "refusal"):
            target = port + 1 if scenario == "nosend" else port
            before = FaultProxy.counts.get(scenario, 0)
            with Session(engine, expire_on_commit=False) as session:
                seeded = harness.seed_version(session, store)
                started = start_audit_run(
                    session, version_uid=seeded.version_uid,
                    analysis_profile_id=seeded.analysis_profile_id,
                    prompt_bundle_id=seeded.prompt_bundle_id,
                    provider_mode="live",
                    idempotency_key=IdempotencyKey(f"w53-rehearsal-{uuid4().hex}"),
                )
                session.commit()
                result = execute_run(
                    session, started.run_id, blob_store=store,
                    adapter=_adapter(scenario, target), provider_config=config,
                    sleep=lambda _seconds: None,
                )
                effects = session.execute(text(
                    "SELECT state, dispatch_class, error_code FROM provider_call_effect "
                    "WHERE run_id=:run_id ORDER BY prepared_at, model_call_id"
                ), {"run_id": started.run_id}).all()
                calls = session.execute(text(
                    "SELECT count(*) FROM model_call WHERE run_id=:run_id"
                ), {"run_id": started.run_id}).scalar_one()
                events = session.execute(text(
                    "SELECT event_type, payload::text FROM audit_event "
                    "WHERE aggregate_id=:run_id OR payload->>'run_id'=:run_id "
                    "ORDER BY occurred_at, audit_event_id"
                ), {"run_id": started.run_id}).all()
                assert effects, scenario
                assert calls == 0, (scenario, calls)
                assert result.terminal_state == "failed", (scenario, result.terminal_state)
                serialized = json.dumps(events, default=str)
                assert "w53-disposable-secret-never-log" not in serialized
                assert "Authorization" not in serialized
                observed = FaultProxy.counts.get(scenario, 0) - before
                if scenario == "nosend":
                    assert observed == 0
                    assert all(row.dispatch_class == "not_sent" for row in effects)
                elif scenario == "rate":
                    assert observed >= 1
                    assert all(row.dispatch_class == "rate_limited" for row in effects)
                else:
                    assert observed == 1, (scenario, observed)
                    wanted = ("definite_refusal" if scenario == "refusal"
                              else "outcome_unknown")
                    assert effects[-1].dispatch_class == wanted
                print(
                    f"run {scenario}: {result.terminal_state}, requests={observed}, "
                    f"effects={[(row.state, row.dispatch_class) for row in effects]}, "
                    f"journal_events={len(events)}, model_calls={calls}"
                )
    finally:
        engine.dispose()


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 56980), FaultProxy)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        _direct_classes(56980)
        _durable_runs(56980)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    main()
