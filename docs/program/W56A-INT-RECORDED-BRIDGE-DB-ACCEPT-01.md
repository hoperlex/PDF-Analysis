# W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01 — acceptance result

**Base:** published `origin/dev=c157ee0d4601f2bf81c68708ebf556b95b87acd5`.
**Status:** accepted on the isolated PostgreSQL 17.11/MinIO lane at migration
head `0022_findings_v2`. The W56A containers were stopped after the run;
their namespaced volumes remain available for audit.

## Verified result

The new real-service test seeds a private source Blob and immutable version,
derives an exact temporary recording from the deterministic source stage,
persists a registered AR v2 recorded Run, then drives `execute_run`. A separate
database session checks five saved successful StageResults, one completed
recorded call with unknown cost, one finding/observation, a single terminal
Run/Job/Attempt and released Lease. It reads source, observation and merge
Blobs from MinIO by saved references and verifies hashes and sizes. A repeat
execution refused with `ANALYSIS_INPUT_INVALID` without allocating new rows.
The fresh observer found exactly five successful StageResults, one succeeded
recorded model call with `cost_micros IS NULL`, one finding and observation,
one Job and Attempt, a published Run and succeeded Job/Attempt, and a released
Lease. The Run's source, text observation and merge artifacts read back with
matching SHA-256 and byte sizes.

Static inspection found a D-141 ordering defect in the explicit bridge: the
final deterministic `_persist_and_bind` leaves its Lease lock uncommitted while
`run_recorded_v2_stage` reads source Blobs before its own first commit. The
v2-only executor branch now commits the StageResult and binding before that
external read. This preserves their transaction atomicity and frees the Lease
for the independent heartbeat. The v1 path is untouched. A focused ordering
test asserts the commit occurs between final bind and recorded source read.

## Changed files

- `src/auditmanager/runs/executor.py` — v2-only durability boundary;
- `tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py` —
  real-service acceptance and container-free ordering assertion;
- `docs/program/tasks/W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01.md` — exact grant;
- this report.

## Checks

- one real-service test collected without touching PostgreSQL/MinIO;
- 60 pre-existing focused container-free tests passed, then 13 focused
  bridge/order tests passed after the v2-only correction;
- final focused container-free suite passed 57 tests, including the ordering
  assertion; both tests in the new module collected successfully;
- pure local fixture preflight produced one accepted grounded proposal, zero
  rejected proposals and one merge group from the eight-page synthetic PDF;
- direct task governance `[]`, Python compilation and `git diff --check` passed;
- ignored isolated `.env` has the 15 frozen names and mode `0600`; credential
  values were copied locally without printing. Assigned lane is
  `auditmanager-w56a-bridge-accept-01` on ports 57470/61070/61071.
- before startup the three assigned ports were unused and W55b containers were
  down. `make up check-services migrate check-db check-storage` passed:
  PostgreSQL `17.11`, private MinIO bucket, migration head
  `0022_findings_v2`, storage byte readback and anonymous access refusal;
- the first acceptance run reached its terminal state and five stages but its
  assertion queried nonexistent `model_call.model_id`; the schema column is
  `model_identity`. Correcting that test query required no production change;
- rerunning the new test passed `2/2`. A combined real-service suite of the
  new bridge test, the existing publication gate test and the D-141 final
  transaction test passed `18/18` in 12.49 seconds;
- `make down` stopped and removed only the assigned W56A containers and
  network. Its namespaced PostgreSQL/MinIO volumes were retained.

## Contracts and limitations

No contract, migration, analysis, finding, job, composition, provider lock,
root dependency or global style changed. The bridge remains offline and
unserved, with explicit fixture parameters. Neither a model/price pin nor a
beta gate is claimed.

## Integrator instruction

Cherry-pick this candidate onto the expected development base after checking
the exact commit. It provides a proven explicit offline recorded executor
bridge and does not grant served activation. Composition selection and the
real model/price pin require their own integration ownership.
