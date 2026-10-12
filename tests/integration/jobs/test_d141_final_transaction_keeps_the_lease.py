"""D-141 (`W54-WORKER-01`): a final transaction longer than the lease is not reclaimed.

HEAVY: real PostgreSQL and MinIO, committed rows, a second connection reclaiming.

Before the repair the text stage's artifact binding locked the Lease row (``require_current``)
and that lock was held through the evidence gate and the terminal writes. Every heartbeat
waited its 2 s lock timeout and failed, so a gate that ran past the lease margin let the
lease expire under a run that had already paid for its model call; ``finish_execution``
then found the lease stale and the run was lost as ``provider_outcome_unknown``.

The lease is shortened to 2 s and the heartbeat to 0.25 s, through the same two knobs the
production code reads, and the evidence gate is made to take 4 s -- twice the lease. A
reclaimer on another connection sweeps every 0.2 s throughout. The run must publish under
its one Attempt. Revert the commit in ``runs/executor.py`` and this fails: the heartbeat is
blocked, the lease expires, and ``finish_execution`` refuses the stale Attempt.
"""

from __future__ import annotations

import threading
import time
from typing import Any
from uuid import uuid4

from sqlalchemy import text

import auditmanager.jobs.lease as lease_module
import auditmanager.runs.executor as executor_module
from auditmanager.jobs.public import JobRepository
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.runs.commands import cancel_audit_run
from auditmanager.shared.identity import IdempotencyKey

GATE_SECONDS = 4.0
LEASE_SECONDS = 2.0


def test_a_final_transaction_longer_than_the_lease_is_not_reclaimed(
    sessions, blob_store, helpers, recorded_adapter, provider_config, monkeypatch,
    quiet_queue,
) -> None:
    monkeypatch.setattr(JobRepository, "lease_seconds", LEASE_SECONDS)
    monkeypatch.setattr(lease_module, "HEARTBEAT_SECONDS", 0.25)
    original_gate = executor_module._run_evidence_gate
    gate_ran = threading.Event()

    def slow_gate(*args: Any, **kwargs: Any) -> Any:
        gate_ran.set()
        time.sleep(GATE_SECONDS)
        return original_gate(*args, **kwargs)

    monkeypatch.setattr(executor_module, "_run_evidence_gate", slow_gate)

    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        started = start_audit_run(
            session,
            version_uid=seeded.version_uid,
            analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id,
            provider_mode="recorded",
            idempotency_key=IdempotencyKey(f"w54-d141-{uuid4().hex}"),
        )
        session.commit()
    run_id = str(started.run_id)

    stop = threading.Event()
    sweeps: list[str] = []

    def reclaimer() -> None:
        while not stop.is_set():
            try:
                with sessions() as sweep:
                    recovered = JobRepository().reclaim_expired(sweep)
                    sweep.commit()
                sweeps.append(f"recovered={recovered}")
            except Exception as failure:  # a lock timeout is what the defect produced
                sweeps.append(type(failure).__name__)
            stop.wait(0.2)

    thread = threading.Thread(target=reclaimer, name="d141-reclaimer", daemon=True)
    thread.start()
    try:
        with sessions() as session:
            result = execute_run(
                session, run_id, blob_store=blob_store, adapter=recorded_adapter,
                provider_config=provider_config,
            )
            session.commit()
    finally:
        stop.set()
        thread.join(timeout=10)
        with sessions() as cleanup:
            state = cleanup.execute(text(
                "SELECT state FROM audit_run WHERE run_id = :run_id"
            ), {"run_id": run_id}).scalar_one()
            if state in {"queued", "running"}:
                cancel_audit_run(
                    cleanup, run_id=run_id, roles=frozenset({"expert"}),
                    idempotency_key=f"w54-d141-cleanup-{uuid4().hex}",
                )
                cleanup.commit()

    assert gate_ran.is_set(), "the evidence gate never ran, so nothing was measured"
    assert result.terminal_state == "published", result
    assert sweeps and all(entry == "recovered=0" for entry in sweeps), sweeps
    with sessions() as observer:
        row = observer.execute(text(
            "SELECT r.state, j.state, "
            "(SELECT count(*) FROM attempt a WHERE a.job_id = j.job_id), "
            "(SELECT string_agg(DISTINCT e.state, ',') FROM provider_call_effect e "
            " WHERE e.run_id = r.run_id) "
            "FROM audit_run r JOIN job j ON j.run_id = r.run_id WHERE r.run_id = :run_id"
        ), {"run_id": run_id}).one()
    assert tuple(row) == ("published", "succeeded", 1, "completed"), row
