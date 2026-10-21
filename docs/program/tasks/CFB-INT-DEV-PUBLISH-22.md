# Task CFB-INT-DEV-PUBLISH-22 — integrate real W56A recorded bridge acceptance

task_id: CFB-INT-DEV-PUBLISH-22

## Outcome

A clean fast-forward `origin/dev` candidate carries the corrected explicit
offline AR v2 executor bridge and its passing real PostgreSQL/MinIO
acceptance evidence. Normal served API/worker composition still selects v1.

## Depends on

- `CFB-INT-DEV-PUBLISH-21` — completed at `a292bd1ab614eec9f3e5356529c83d01578c7513`;
- `W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01` — completed at `8ff45de3fcecc545d7056c6877eb4f66bd5d67dc`.

## Frozen inputs

- integration base and directly read `origin/dev`: `a292bd1ab614eec9f3e5356529c83d01578c7513`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- source commits in order: `4172a6f5ce8cd7e298dff0d3e0717d17dd682637`, `8ff45de3fcecc545d7056c6877eb4f66bd5d67dc`;
- source base `c157ee0d4601f2bf81c68708ebf556b95b87acd5` is an ancestor of dev21;
- W56A source lane: isolated PostgreSQL 17.11/MinIO, migration `0022_findings_v2`, 18/18 real service checks; final source report is the acceptance evidence;
- API/domain/error/stage SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- R-135 defers the complete beta gate; W55b has a separate failed main-candidate gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed W56A source tip has exactly two commits and four
  changed paths on the published dev18 ancestor.

### P-01 — source lineage and path scope

- captured_at: 2026-10-16
- command: `git log --format='%H %s' c157ee0d4601f2bf81c68708ebf556b95b87acd5..8ff45de3fcecc545d7056c6877eb4f66bd5d67dc`
- captured_output:
  ```text
  8ff45de3fcecc545d7056c6877eb4f66bd5d67dc test(w56a): record passing DB bridge acceptance
  4172a6f5ce8cd7e298dff0d3e0717d17dd682637 test(w56a): prepare real recorded bridge DB acceptance
  ```
- interpretation: cherry-pick the commits in oldest-first order; validate
  the aggregate four-path diff and reread remote dev before publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-22.md`
- `docs/program/CFB-INT-DEV-PUBLISH-22.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01.md`
- `docs/program/tasks/W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01.md`
- `src/auditmanager/runs/executor.py`
- `tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
global styles, other application/tests, W55b main candidate, W57 citation
seal, production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No served v2 switch, live provider/paid model call, real model/price pin,
W57 citation seal, corpus publication, W55b deployment or beta acceptance.

## Deliverables

Exact W56A source payload, bounded current-state update, this task, report
and direct read-back of the published SHA.

## Required tests

- focused W56A container-free bridge/order tests and program governance;
- rely on the source task's exact isolated 18/18 real-service result for this
  unchanged payload; no competing service run while W55b D-142 owns the lane;
- frozen contracts/migration, exact-path, whitespace, clean-tree, fresh
  remote fast-forward and post-push read-back;
- complete beta `make gate` deferred by R-135; W55b's separate gate cannot
  be borrowed as W56A evidence.

## Integration contract

Only this task may publish its exact checked SHA to `origin/dev`. Cherry-pick
both completed source commits without payload edits. The v2 branch commits
the last deterministic StageResult and binding before reading recorded
source Blobs, then the existing recorded gate publishes one terminal Run.
It is explicit offline invocation only. A future sole-owner composition slot
must make v2 served and bind a reviewed model/price pin. A moved dev ref or
changed source stops publication; never force-push.

## Failure/idempotency/security cases

The real source test verified one saved recorded call with unknown cost,
exact Blob readback and refused duplicate execution. Do not include ignored
`.env`, credentials, Blob bytes or Docker volumes in Git. Retry reads remote
and no-ops if already equal.

## Rollback / feature flag

No served behavior is activated and no flag or deployment rollback applies.
Corrections use reviewed forward commits.

## Handoff

- integration files: this task, its report and bounded state update;
- source files: only the four exact W56A paths;
- contracts: none; next: served composition and model/price pin;
- forbidden hotspots and `origin/main` remain untouched.
