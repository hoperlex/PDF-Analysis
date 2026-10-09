"""Kill a W53 executor after a durable provider response, then recover in a new process.

Run as the parent only. It starts two independent Python serving processes. The first
blocks after committing provider.response_received; the parent sends SIGKILL. The
second expires only that dead lane lease to avoid a sixty-second wait, runs startup
reconciliation and verifies that the paid boundary is never dispatched again.
"""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import ProviderConfig, ProviderMode, RecordedAdapter
from auditmanager.jobs.public import JobRepository
from auditmanager.runs import execute_run, reconcile, start_audit_run
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage import S3BlobStore, S3StorageSettings


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(os.environ.get("W53_REHEARSAL_EVIDENCE_DIR", "/tmp/w53-rehearsal-01"))
HARNESS = ROOT / "tests/integration/runs/harness.py"
SPEC = importlib.util.spec_from_file_location("w53_recovery_harness", HARNESS)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = harness
SPEC.loader.exec_module(harness)


class CountedLiveRecorded:
    provider_mode = ProviderMode.LIVE

    def __init__(self) -> None:
        self.inner = RecordedAdapter(harness.RECORDINGS)

    def complete(self, request):
        with (EVIDENCE / "provider-dispatch.count").open("a") as marker:
            marker.write("one\n")
            marker.flush()
            os.fsync(marker.fileno())
        return self.inner.complete(request)


def _engine():
    return create_database_engine(
        DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"]))
    )


def _config() -> ProviderConfig:
    return ProviderConfig(
        mode=ProviderMode.LIVE, model_id="claude-opus-5",
        run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=True,
    )


def crash_process() -> None:
    engine = _engine()
    store = S3BlobStore(S3StorageSettings.from_env())
    store.check_access()
    with Session(engine, expire_on_commit=False) as session:
        seeded = harness.seed_version(session, store)
        started = start_audit_run(
            session, version_uid=seeded.version_uid,
            analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id,
            provider_mode="live",
            idempotency_key=IdempotencyKey(f"w53-kill-{uuid4().hex}"),
        )
        session.commit()

        def block_after_response(boundary: str) -> None:
            if boundary != "provider_response_committed":
                return
            (EVIDENCE / "crash-ready.json").write_text(json.dumps({
                "run_id": started.run_id, "boundary": boundary,
            }))
            print(f"first process reached {boundary} for {started.run_id}", flush=True)
            while True:
                signal.pause()

        execute_run(
            session, started.run_id, blob_store=store,
            adapter=CountedLiveRecorded(), provider_config=_config(),
            effect_checkpoint=block_after_response,
        )
        raise AssertionError("executor returned before SIGKILL")


def recover_process() -> None:
    run_id = json.loads((EVIDENCE / "crash-ready.json").read_text())["run_id"]
    engine = _engine()
    with Session(engine, expire_on_commit=False) as session:
        before = session.execute(text(
            "SELECT r.state AS run_state, j.state AS job_state, e.state AS effect_state "
            "FROM audit_run r JOIN job j ON j.run_id=r.run_id "
            "JOIN provider_call_effect e ON e.run_id=r.run_id WHERE r.run_id=:run_id"
        ), {"run_id": run_id}).mappings().one()
        assert dict(before) == {
            "run_state": "running", "job_state": "running",
            "effect_state": "response_received",
        }, dict(before)
        session.execute(text(
            "UPDATE lease SET expires_at=statement_timestamp()-interval '1 second' "
            "WHERE attempt_id=(SELECT current_attempt_id FROM job WHERE run_id=:run_id)"
        ), {"run_id": run_id})
        session.commit()
        recovered = JobRepository().reclaim_expired(session)
        assert recovered == 1, recovered
        session.commit()
        report = reconcile(session, older_than="0 seconds")
        session.commit()
        after = session.execute(text(
            "SELECT r.state AS run_state, j.state AS job_state, a.state AS attempt_state, "
            "l.released_at IS NOT NULL AS lease_released, e.state AS effect_state "
            "FROM audit_run r JOIN job j ON j.run_id=r.run_id "
            "JOIN attempt a ON a.attempt_id=j.current_attempt_id "
            "JOIN lease l ON l.attempt_id=a.attempt_id "
            "JOIN provider_call_effect e ON e.run_id=r.run_id WHERE r.run_id=:run_id"
        ), {"run_id": run_id}).mappings().one()
        assert after["run_state"] == "failed", dict(after)
        assert after["job_state"] == "failed", dict(after)
        assert after["attempt_state"] == "lost", dict(after)
        assert after["lease_released"] is True, dict(after)
        assert after["effect_state"] in {"response_received", "abandoned"}, dict(after)
        assert session.execute(text(
            "SELECT count(*) FROM model_call WHERE run_id=:run_id"
        ), {"run_id": run_id}).scalar_one() == 0
        events = session.execute(text(
            "SELECT event_type, occurred_at, payload::text FROM audit_event "
            "WHERE payload->>'run_id'=:run_id ORDER BY occurred_at, audit_event_id"
        ), {"run_id": run_id}).all()
        names = [row.event_type for row in events]
        assert names.index("provider.prepared") < names.index("provider.response_received")
        serialized = json.dumps(events, default=str)
        assert "w53-disposable-secret-never-log" not in serialized
        assert "Authorization" not in serialized
        assert (EVIDENCE / "provider-dispatch.count").read_text().splitlines() == ["one"]
        try:
            execute_run(session, run_id, blob_store=None, adapter=CountedLiveRecorded(),
                        provider_config=_config())
        except DomainError as error:
            assert error.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED, error.code
        else:
            raise AssertionError("terminal run accepted a second executor")
        assert (EVIDENCE / "provider-dispatch.count").read_text().splitlines() == ["one"]
        print(
            f"second process: run={run_id}, before={dict(before)}, after={dict(after)}, "
            f"reclaimed={recovered}, settled={len(report.settled_provider_effects)}, "
            f"journal_events={len(events)}, provider_dispatches=1, replay_refused=True"
        )
    engine.dispose()


def parent() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in ("crash-ready.json", "provider-dispatch.count"):
        (EVIDENCE / name).unlink(missing_ok=True)
    child = subprocess.Popen([sys.executable, __file__, "--crash"])
    try:
        deadline = time.monotonic() + 45
        while not (EVIDENCE / "crash-ready.json").is_file():
            if child.poll() is not None:
                raise RuntimeError(f"first process exited early with {child.returncode}")
            if time.monotonic() >= deadline:
                raise TimeoutError("first process never committed provider response")
            time.sleep(0.1)
        child.kill()  # Real SIGKILL, after a committed response boundary.
        code = child.wait(timeout=10)
        assert code == -signal.SIGKILL, code
        print(f"first process exit={code} (SIGKILL)", flush=True)
        subprocess.run([sys.executable, __file__, "--recover"], check=True)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)


if __name__ == "__main__":
    match sys.argv[1:]:
        case []:
            parent()
        case ["--crash"]:
            crash_process()
        case ["--recover"]:
            recover_process()
        case _:
            raise SystemExit("usage: process_recovery.py [--crash|--recover]")
