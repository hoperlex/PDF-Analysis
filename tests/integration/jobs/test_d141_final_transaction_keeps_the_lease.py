"""D-141 (`W54-WORKER-01`): a final transaction longer than the lease is not reclaimed.

HEAVY: real PostgreSQL and MinIO, committed rows, a second connection reclaiming.

Before the repair the text stage's artifact binding locked the Lease row (``require_current``)
and that lock was held through the evidence gate and the terminal writes. Every heartbeat
waited its 2 s lock timeout and failed, so a gate that ran past the lease margin let the
lease expire under a run that had already paid for its model call; ``finish_execution``
then found the lease stale and the run was lost as ``provider_outcome_unknown``.

The lease is shortened to 8 s and the heartbeat to 0.25 s, through the same two knobs the
production code reads, and the evidence gate is made to take 12 s -- half as long again as the
lease. A reclaimer on another connection sweeps every 0.2 s throughout. The run must publish
under its one Attempt. Revert the commit in ``runs/executor.py`` and this fails: the heartbeat
is blocked, the lease expires, and ``finish_execution`` refuses the stale Attempt.

**The collector (`GATE-REPAIR-02`).** The margin was not what failed the complete gate. The
text stage's ``extraction._release`` runs a full ``gc.collect()`` after every page, and a full
collection holds the GIL for as long as the whole process heap takes to traverse. In this file
alone the heap is small and a collection costs milliseconds. After the eight directories that
precede ``jobs`` in the battery the one pytest process holds about 2.25 million tracked objects
(measured: 0.4 M after ``analysis``, 2.25 M after ``api``) and a collection costs seconds; the
heartbeat thread needs the GIL several times per beat, so it did not beat once in 16 s
(``lease.heartbeat_at == acquired_at``), the lease ended at 8 s, the reclaimer took it and
``bind_artifacts`` found the Attempt stale. The proof here is about the heartbeat and the final
transaction, not about the collector, so the test freezes what the process already holds
(``gc.freeze``) for its duration: a collection then walks only what the test itself allocates,
whatever ran before it. ``gc.unfreeze`` gives the objects back afterwards.

**The margin (`D-190`).** The lease is stamped on PostgreSQL's clock (``statement_timestamp()``
at the claim and at every extension), so there is no clock to drive from here: the two knobs are
the whole of the margin. A host stall that keeps the heartbeat thread from running for longer
than ``LEASE_SECONDS - HEARTBEAT_SECONDS`` lets the lease expire under the run, and the reclaimer
takes it. At 2 s and 0.25 s that tolerance was 1.75 s, and one stall of that size in a 2.5 h
battery (gate `59a1be91`) failed this file once; three isolated reruns and the whole
``tests/integration/jobs`` directory passed. At 8 s it is 7.75 s, more than four times as long,
and the gate is still long enough that a heartbeat that never ran shows: the lease would end
4 s before the gate does.

The reclaimer counts **only this run's lease** (`W55A-FIX`; `W55A-FIX-DB.md` §4.1). Other
suites leave runs ``running`` under a 60 s lease (the W48 crash cases), and one expiring
inside this window was recovered and counted as if it were this run's. Every lease that is
unreleased when the test starts is parked past the test and given back its expiry after;
``quiet_queue`` has already recovered the ones that had expired.
"""

from __future__ import annotations

import gc
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

import auditmanager.jobs.lease as lease_module
import auditmanager.runs.executor as executor_module
from auditmanager.jobs.public import JobRepository
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.runs.commands import cancel_audit_run
from auditmanager.shared.identity import IdempotencyKey

GATE_SECONDS = 12.0
LEASE_SECONDS = 8.0
HEARTBEAT_SECONDS = 0.25
#: How long the heartbeat thread may be kept from running before the lease ends under the run.
STALL_TOLERANCE_SECONDS = LEASE_SECONDS - HEARTBEAT_SECONDS
#: The stall that failed the complete battery: it was longer than the old 1.75 s tolerance.
OBSERVED_STALL_SECONDS = 1.75


@contextmanager
def _foreign_leases_parked(sessions) -> Iterator[None]:
    """Every lease unreleased now expires after the test, and gets its own expiry back."""
    with sessions() as setup:
        parked = setup.execute(text(
            "SELECT lease_id, expires_at FROM lease WHERE released_at IS NULL FOR UPDATE"
        )).all()
        setup.execute(text(
            "UPDATE lease SET expires_at = timestamptz '2099-01-01' WHERE released_at IS NULL"
        ))
        setup.commit()
    try:
        yield
    finally:
        with sessions() as cleanup:
            for lease_id, expires_at in parked:
                cleanup.execute(text(
                    "UPDATE lease SET expires_at = :expires_at "
                    "WHERE lease_id = :lease_id AND released_at IS NULL"
                ), {"lease_id": lease_id, "expires_at": expires_at})
            cleanup.commit()


#: A full collection after the freeze must cost far less than the lease margin; see the docstring.
COLLECTION_BUDGET_SECONDS = LEASE_SECONDS / 4


@pytest.fixture
def collector_frozen() -> Iterator[None]:
    """Freeze the process heap for one test, and say so loudly if collections are still slow."""
    gc.collect()  # the expensive one: here, before any lease exists
    gc.freeze()
    try:
        started = time.monotonic()
        gc.collect()
        took = time.monotonic() - started
        assert took < COLLECTION_BUDGET_SECONDS, (
            f"a full gc.collect() still takes {took:.2f} s with the heap frozen; the text stage "
            "runs one per page and holds the GIL for that long, which starves the lease heartbeat"
        )
        yield
    finally:
        gc.unfreeze()


def test_the_margin_outlasts_the_stall_that_failed_the_battery_and_the_gate_outlasts_the_lease() -> None:
    """`D-190`: the two numbers above cannot be narrowed back without this reddening.

    A tolerance of three times the observed stall, and a gate that runs at least two seconds past
    the lease, so a heartbeat that does not run is still seen by the reclaimer before the gate
    ends. Both are about the parameters, not about the code under test; the test below is what
    the code answers.
    """
    assert STALL_TOLERANCE_SECONDS >= 3 * OBSERVED_STALL_SECONDS, STALL_TOLERANCE_SECONDS
    assert GATE_SECONDS >= LEASE_SECONDS + 2.0, (GATE_SECONDS, LEASE_SECONDS)


def test_a_final_transaction_longer_than_the_lease_is_not_reclaimed(
    sessions, blob_store, helpers, recorded_adapter, provider_config, monkeypatch,
    quiet_queue, collector_frozen,
) -> None:
    monkeypatch.setattr(JobRepository, "lease_seconds", LEASE_SECONDS)
    monkeypatch.setattr(lease_module, "HEARTBEAT_SECONDS", HEARTBEAT_SECONDS)
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
    with _foreign_leases_parked(sessions):
        thread.start()
        try:
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
        finally:
            # Also when `execute_run` raised (`GATE-REPAIR-02`): a failed run left its Job queued
            # and runnable in the shared database, and the next suite's claimant took it.
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
