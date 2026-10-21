# CFB-INT-DEV-PUBLISH-22 — recorded W56A bridge acceptance

The candidate builds on directly read
`origin/dev=a292bd1ab614eec9f3e5356529c83d01578c7513`.
Completed W56A source commits `4172a6f5` and `8ff45de3` were cherry-picked
as `dea25edc` and `be95354f` without payload edits. They add a v2-only
commit boundary before external Blob reads, a real-service acceptance test,
and the source task and report. Normal served API/worker composition still
selects v1; the bridge requires explicit offline invocation.

## Checks and scope

- The W56A source lane passed 18/18 real PostgreSQL 17.11/MinIO tests at
  migration head `0022_findings_v2`, including five persisted stage results,
  a recorded call, source and output Blob readback, terminal Run/Job/Attempt,
  released Lease and refused duplicate execution. The lane was stopped.
- The integrated candidate passed 27 container-free W56A focused tests with
  one real-service test deselected, and 28 program tests. Direct governance
  for this integration task returned `[]`.
- The four cherry-picked paths are exactly the W56A source report, source
  task, `src/auditmanager/runs/executor.py` and its new real-service test.
  The integration commit changes only this report, its task and bounded
  `CURRENT_STATE.md` edits.
- The API/domain/error/stage frozen digests and migration head remain as
  pinned in the task. `VERSION=0.6.0`; the development API surface is 47
  paths / 54 operations / 124 schemas, with 25 error codes.

No shared contract, migration, root dependency or lock, composition root,
global style, production DB/S3, `origin/main`, tag or deployment input was
changed. The separate W55b `d3acd511` full gate failed at a D-142 test
selector after 4,168 passes. A test-only repair has passed its focused
real-service check, but the next exact main candidate still needs a complete
`make gate`. R-135 defers the complete W56–W63 beta gate.

## Publication and next step

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority. A future
sole-owner composition task must serve v2 and bind a reviewed model/price
identity. The present result proves only the explicit recorded offline path.
