# Task W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01 — real recorded executor acceptance

task_id: W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01

## Outcome

One real PostgreSQL 17.11 and private MinIO test drives a persisted AR v2 Run
through `execute_run` with an exact offline recording, proves five saved
StageResults, one completed recorded call, source/observation/merge Blob
readback, a single terminal Run/Job/Attempt, and a refused duplicate execution.
Any proven executor defect is repaired within this task's owned path.

## Depends on

- `W56A-INT-RECORDED-ACTIVATION-01` — completed explicit bridge;
- `W56A-INT-RECORDED-PUBLICATION-GATE-01` — completed gate and service tests;
- `CFB-INT-DEV-PUBLISH-18` — published and read back at base SHA.

## Frozen inputs

- base commit: `c157ee0d4601f2bf81c68708ebf556b95b87acd5` (`origin/dev` at task start);
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the new recorded bridge has only fake-port routing checks; the
  existing real service test begins after all five stages have been inserted.

### P-01 — acceptance seam

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && rg -n '^def (execute_run|_execute_run_body|run_recorded_v2_stage|run_recorded_v2_merge_stage|publish_recorded_v2_run|seed_version|run_stage)' src/auditmanager/runs/executor.py src/auditmanager/runs/recorded_v2_stage.py src/auditmanager/runs/recorded_v2_merge.py src/auditmanager/runs/recorded_v2_publication.py tests/integration/runs/harness.py src/auditmanager/analysis/engine/runner.py && git ls-tree -r --name-only HEAD tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py && git status --short`
- captured_output:
  ```text
  c157ee0d4601f2bf81c68708ebf556b95b87acd5
  tests/integration/runs/harness.py:255:def seed_version(session: Session, blob_store: S3BlobStore) -> SeededVersion:
  src/auditmanager/analysis/engine/runner.py:95:def run_stage(
  src/auditmanager/runs/recorded_v2_merge.py:95:def run_recorded_v2_merge_stage(
  src/auditmanager/runs/executor.py:720:def _execute_run_body(
  src/auditmanager/runs/executor.py:1133:def execute_run(*args: Any, **kwargs: Any) -> ExecutionResult:
  src/auditmanager/runs/recorded_v2_stage.py:54:def run_recorded_v2_stage(
  src/auditmanager/runs/recorded_v2_publication.py:107:def publish_recorded_v2_run(
  ```
- interpretation: the bridge and independent real-service fixture seam exist;
  the new acceptance test path was absent at base.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/executor.py`
- `tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py`
- `docs/program/tasks/W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01.md`
- `docs/program/W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01.md`

## Lane resources

- foundation_instance: `auditmanager-w56a-bridge-accept-01`
- postgres_port: `57470`
- s3_api_port: `61070`
- s3_console_port: `61071`
- postgres_db: `auditmanager_w56a_bridge_accept_01`
- s3_bucket: `auditmanager-w56a-bridge-accept-01`

## Forbidden hotspots

`contracts/**`, migrations, analysis/findings/jobs/stage ports, other tests,
composition root, provider lock, root dependencies/locks, global styles,
`CURRENT_STATE.md`, `origin/dev`, `origin/main`, tags.

## Non-goals

No served API/worker activation, live/paid model call, generated baseline,
contract or migration change, W54 corpus promotion, full beta gate or release.
This test generates a local recording only for its exact temporary request.

## Deliverables

Focused real-service test, any strictly proven executor correction, and a
result report. The service lane stays down until the integrator confirms the
W55b full gate has released its services and rechecks the assigned ports.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py` on the assigned isolated lane at `0022_findings_v2`;
- existing recorded bridge, publication gate and v1 characterization checks
  appropriate to any executor fix;
- direct task governance, frozen hashes, Python compilation,
  `git diff --check` and exact owned-path check.

## Integration contract

The test uses a real seeded source Blob and immutable version, computes the
fixture request from the same deterministic source stage, persists a v2 Run,
then lets `execute_run` perform the actual five stages, call journal and
publication. It observes the final transaction through a new DB session, and
reads the saved Blob references through the real MinIO adapter. Re-execution
of the terminal Run must refuse without new rows. A test failure is a real
acceptance defect to investigate, not a reason to mock the failing port.

## Failure/idempotency/security cases

Only `fixture/<id>` with explicit settings and concrete recorded adapter is
supplied. The test expects one completed call with `cost_micros IS NULL`,
recorded provenance and no retry effect. A second execution refuses before a
new Attempt; all observed row counts remain unchanged. Test cleanup affects
only its isolated generated lane.

## Rollback / feature flag

If no executor fix is needed, remove the test and task/report. If corrected,
revert only this task's executor diff; no schema or data migration is involved.
The preexisting bridge remains explicit and unserved.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrator may cherry-pick only after the focused real-service test
  passes and the isolated lane is stopped; composition/model pin remains separate.
