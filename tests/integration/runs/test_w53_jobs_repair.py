"""Real PostgreSQL overlap between periodic and forced lease recovery."""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.jobs.repository import JobRepository, _EXPIRED_LEASES, _LOCK_RUN
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import RunId


class _CoordinatedSession(Session):
    def __init__(self, *, barrier, first_periodic_lock, label, **kwargs):
        super().__init__(**kwargs)
        self.barrier = barrier
        self.first_periodic_lock = first_periodic_lock
        self.label = label
        self.first_run_seen = False

    def execute(self, statement, params=None, **kwargs):
        result = super().execute(statement, params, **kwargs)
        if statement is _LOCK_RUN and not self.first_run_seen:
            self.first_run_seen = True
            if self.label == "periodic":
                self.first_periodic_lock.set()
            self.barrier.wait(timeout=10)
        return result


def _queued_run(session, seeded):
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64,
        command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    jobs = JobRepository()
    jobs.enqueue(session, run_id=run_id)
    return run_id


def _running_run(session, seeded):
    run_id = _queued_run(session, seeded)
    jobs = JobRepository()
    authority = jobs.start_execution(session, run_id=run_id)
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
    return run_id, authority


def test_empty_control_row_serializes_claim_with_committing_pause(
    engine, blob_store, helpers, monkeypatch
):
    # Two local database connections are needed; this test never calls a provider.
    monkeypatch.undo()
    jobs = JobRepository()
    with Session(engine) as seed:
        seeded = helpers.seed_version(seed, blob_store)
        first_run = _queued_run(seed, seeded)
        second_run = _queued_run(seed, seeded)
        seed.execute(text("DELETE FROM execution_control WHERE singleton"))
        seed.commit()

    started = threading.Event()
    finished = threading.Event()
    errors = []

    def pause():
        with Session(engine) as administrator:
            started.set()
            try:
                jobs.set_paused(administrator, paused=True)
                administrator.commit()
            except Exception as exc:
                administrator.rollback()
                errors.append(exc)
            finally:
                finished.set()

    with Session(engine) as claimant:
        authority = jobs.start_execution(claimant, run_id=first_run)
        assert authority.run_id == first_run
        assert claimant.execute(text(
            "SELECT paused FROM execution_control WHERE singleton"
        )).scalar_one() is False
        administrator = threading.Thread(target=pause)
        administrator.start()
        assert started.wait(timeout=5)
        # The administrator's upsert waits on the claim's control-row lock.
        assert not finished.wait(timeout=0.2)
        claimant.commit()

    administrator.join(timeout=10)
    assert not administrator.is_alive() and not errors
    assert finished.is_set()
    with Session(engine) as later_claim:
        assert later_claim.execute(text(
            "SELECT paused FROM execution_control WHERE singleton"
        )).scalar_one() is True
        with pytest.raises(DomainError):
            jobs.start_execution(later_claim, run_id=second_run)
        assert later_claim.execute(text(
            "SELECT count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id "
            "WHERE j.run_id = :run_id"
        ), {"run_id": second_run}).scalar_one() == 0
    with Session(engine) as cleanup:
        jobs.set_paused(cleanup, paused=False)
        cleanup.commit()


def test_periodic_and_forced_reclaim_two_runs_never_invert_locks(
    engine, blob_store, helpers, monkeypatch
):
    # This case opens two new local PostgreSQL sockets. The suite's recorded-only
    # socket guard can be removed for this test: it makes no provider call.
    monkeypatch.undo()
    with Session(engine) as seed:
        seeded = helpers.seed_version(seed, blob_store)
        first = _running_run(seed, seeded)
        second = _running_run(seed, seeded)
        seed.commit()
        for _, authority in (first, second):
            seed.execute(text(
                "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
                "WHERE lease_id = :lease_id"
            ), {"lease_id": authority.lease_id})
        seed.commit()
        ordered = sorted((first, second), key=lambda item: item[0])
        forced_attempt = ordered[1][1].attempt_id
        periodic_candidates = [str(row["run_id"]) for row in seed.execute(
            _EXPIRED_LEASES, {"force_attempt_id": None}
        ).mappings() if str(row["run_id"]) in {first[0], second[0]}]
        forced_candidates = [str(row["run_id"]) for row in seed.execute(
            _EXPIRED_LEASES, {"force_attempt_id": forced_attempt}
        ).mappings()]
        assert periodic_candidates == [ordered[0][0], ordered[1][0]]
        assert forced_candidates == [ordered[1][0]]

    barrier = threading.Barrier(2)
    first_periodic_lock = threading.Event()
    results = {}

    def sweep(label, force_attempt_id):
        with _CoordinatedSession(
            bind=engine, barrier=barrier,
            first_periodic_lock=first_periodic_lock, label=label,
        ) as session:
            try:
                count = JobRepository().reclaim_expired(
                    session, force_attempt_id=force_attempt_id,
                )
                session.commit()
                results[label] = ("committed", count)
            except Exception as exc:
                session.rollback()
                results[label] = (type(exc).__name__, getattr(
                    getattr(exc, "orig", None), "sqlstate", None,
                ))

    periodic = threading.Thread(target=sweep, args=("periodic", None))
    forced = threading.Thread(target=sweep, args=("forced", forced_attempt))
    periodic.start()
    assert first_periodic_lock.wait(timeout=10)
    forced.start()
    periodic.join(timeout=15)
    forced.join(timeout=15)
    assert not periodic.is_alive() and not forced.is_alive()
    assert results == {"periodic": ("committed", 1), "forced": ("committed", 1)}
    with Session(engine) as observer:
        states = observer.execute(text(
            "SELECT r.run_id, r.state, j.state, l.released_at IS NOT NULL "
            "FROM audit_run r JOIN job j ON j.run_id = r.run_id "
            "JOIN lease l ON l.job_id = j.job_id WHERE r.run_id IN (:a, :b)"
        ), {"a": first[0], "b": second[0]}).all()
        assert sorted(states) == sorted((
            (first[0], "running", "queued", True),
            (second[0], "running", "queued", True),
        ))
