# Task W56A-INT-RECORDED-PUBLICATION-GATE-01 — durable recorded finding gate

task_id: W56A-INT-RECORDED-PUBLICATION-GATE-01

## Outcome

An unactivated gate publishes a saved, validated recorded AR v2 finding plan and
transitions its Run, Job and Attempt in one caller-owned PostgreSQL transaction.
Zero findings still yields a durable published Run. Failed required stages finish
without finding writes. A real PostgreSQL/MinIO test proves commit and retry.

## Depends on

- `W56A-INT-DURABLE-RECORDED-STAGE-01` — completed text StageResult and call;
- `W56A-INT-RECORDED-MERGE-STAGE-01` — completed merge StageResult;
- `W56A-INT-V2-PUBLICATION-PREP-01` — completed savepoint finding writer;
- `W56A-INT-RECORDED-SAVED-PUBLICATION-PLAN-01` — completed saved-plan bridge at source commit `9bf35ca9a2d5bd9dfdbbd44028270d82ffe6bfbd`, cherry-picked locally as `ce9238c2`.

## Frozen inputs

- base `origin/dev`: `08055ca094a9c3e4676a5907a0b3020f0bee4fb8`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; StageResult v1, observation artifact v2, merge artifact v1.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the saved-plan bridge is read-only, v2 finding writer owns only a savepoint, and no recorded run terminal gate exists.

### P-01 — gate seam

- captured_at: 2026-10-16
- command: `git rev-parse --short HEAD && git ls-tree -r --name-only HEAD src/auditmanager/runs/recorded_v2_publication.py && rg -n 'def plan_recorded_saved_publication|def publish_v2_merge_plan|def finish_execution|def terminate' src/auditmanager/findings/recorded_saved_plan.py src/auditmanager/findings/v2_publication.py src/auditmanager/jobs/repository.py src/auditmanager/runs/repository.py`
- captured_output:
  ```text
  ce9238c2
  src/auditmanager/findings/recorded_saved_plan.py:93:def plan_recorded_saved_publication(
  src/auditmanager/findings/v2_publication.py:161:def publish_v2_merge_plan(
  src/auditmanager/jobs/repository.py:701:    def finish_execution(
  src/auditmanager/runs/repository.py:518:    def terminate(
  ```
- interpretation: this task adds the missing outer transaction gate and no schema change.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/recorded_v2_publication.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/findings/public.py`
- `tests/integration/jobs/test_recorded_v2_publication_gate.py`
- `docs/program/tasks/W56A-INT-RECORDED-PUBLICATION-GATE-01.md`
- `docs/program/W56A-INT-RECORDED-PUBLICATION-GATE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, saved-plan bridge files, executor,
run repository, composition root, API/router, root dependency/lock files, global
styles, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No active executor wiring, live provider, recording replay, normative citation,
expert decision, diagnostic DB row, new migration/contract, release or beta claim.

## Deliverables

One read-only completed-call repository method, public findings boundary,
recorded run gate, real-service focused test, and result report.

## Required tests

- focused real PostgreSQL/MinIO gate test with actual migration head 0022;
- focused saved-plan and v2 publication tests;
- Python compilation, direct task governance, frozen hashes, whitespace and exact owned-path proof.

## Integration contract

The later executor calls this gate only after all five registered AR v2 stages
have been attempted and their results committed. It passes the current
`AttemptAuthority`, a saved running Run and a Blob store. The gate reads and
verifies saved text and merge Blobs before acquiring the Run row lock. It
advances `running→validating`, rechecks the Run, stage references, source
references and sole completed recorded model call, rejects preexisting
publication rows, writes findings through the findings public boundary, then
selects the terminal from the registered five-stage plan. Run termination and
Job/Attempt finish share the same outer transaction. The caller commits once
after normal return; no intermediate commit is allowed. Failed or missing
required stages terminate failed with no finding write. A stage writer's
`record_stage_result` UPSERT may precede its Run lock. Its subsequent
`jobs.bind_artifacts` / `require_current` must share the UPSERT transaction,
and the writer must roll back the whole transaction if authority fails.
Then a writer delayed behind the gate's terminal Run cannot commit a late
StageResult. The gate rechecks committed StageResults under the Run lock.

## Failure/idempotency/security cases

Wrong profile, Blob bytes, model call, source binding, stale Attempt, changed
StageResult or preexisting finding/observation fails closed. The terminal Run
CAS plus Job/Attempt finish is the publication marker even for zero findings;
counting rows is not an idempotency key. A pre-commit crash rolls back findings,
transition and finish; a post-commit retry sees the terminal and writes nothing.
The Run lock serializes claim/reclaim and final publication; stage writer
atomicity is a separate caller obligation. The Lease is locked only in final
`finish_execution`, preserving heartbeat during publication (D-141).

## Rollback / feature flag

Revert the six owned paths before executor wiring. The gate is unactivated,
requires no data rollback and has no user-facing flag.

## Handoff

- changed paths/checks/limits: accompanying report;
- contracts: none;
- next: integrate this exact commit after saved-plan bridge, then separately
  grant runtime activation and full gate.
