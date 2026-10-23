# Task AR-V3-BETA-LEASE-PEEK-01 — inspect Attempt without lease row locks

## Outcome
The AR v3 saved-Blob readers can ask whether an Attempt is current before an external read without taking Run/Job/Attempt/Lease row locks; the existing locked `require_current` remains the mandatory final side-effect fence.

## Depends on
- `AR-V3-BETA-CITE-WRITER-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `a559f9653212f56e2d9e5b659f5c55b392ae051f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: `require_current` takes four row locks, including the lease updated by the independent heartbeat
### P-01 — locked authority read
- captured_at: 2026-10-23
- command: `sed -n '797,818p' src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
    def require_current(self, session: Session, authority: AttemptAuthority) -> None:
        session.execute(_LOCK_RUN, {"run_id": authority.run_id}).scalar_one_or_none()
        row = session.execute(
            _LOCK_AUTHORITY_JOB, {"job_id": authority.job_id}
        ).mappings().first()
        if row is None or row["run_id"] != authority.run_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        if row["current_attempt_id"] != authority.attempt_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")
        attempt = session.execute(
            _LOCK_AUTHORITY_ATTEMPT, {"attempt_id": authority.attempt_id}
        ).mappings().first()
        lease = session.execute(
            _LOCK_AUTHORITY_LEASE, {"attempt_id": authority.attempt_id}
        ).mappings().first()
  ```
- interpretation: this is the correct effect fence but cannot be held while BlobStore stalls. A lock-free check is only an early read; it never authorizes publication.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/jobs/repository.py`
- `tests/integration/jobs/test_unlocked_attempt_read.py`
- `docs/program/tasks/AR-V3-BETA-LEASE-PEEK-01.md`
- `docs/program/AR-V3-BETA-LEASE-PEEK-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Replacing `require_current` for provider, outbox, StageResult or terminal writes.
- Changing source/set readers or claiming the lease hazard closed in this slice.
- Adding a generic authorization fallback.

## Deliverables
- A narrowly named read-only Attempt check and matching/stale/missing-token tests.
- Result note and queue update.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/jobs/test_unlocked_attempt_read.py tests/integration/jobs/test_v3_completed_call.py -x --tb=short`
- expected: all passed; SQL contains no `FOR UPDATE`/`FOR SHARE`, governance and exact changed-path check clear.

## Integration contract
Saved-Blob readers may call `check_current_unlocked(session, authority)` before an external read only when they will later call `require_current` and recheck saved DB facts before any provider or publication effect. It does not reserve authority and must not be used for a write decision. The next task will move request reads onto this pattern and prove heartbeat progress during delayed Blob reads.

## Failure/idempotency/security cases
- Wrong Job/Run/current Attempt/lease, nonrunning states or expired/released lease refuse as stale; missing or wrong token refuses with the existing execution-token code.
- The check issues one nonlocking SELECT and writes nothing.

## Rollback / feature flag
Unserved additive method; revert without migration. Locked final gates stay intact.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: caller still needs lock-free Blob reader refactor and final locked fence
- integration notes: never use this method as effect authority
