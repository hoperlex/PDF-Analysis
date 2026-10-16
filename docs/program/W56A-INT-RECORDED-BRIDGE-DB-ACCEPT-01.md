# W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01 — preparation record

**Base:** published `origin/dev=c157ee0d4601f2bf81c68708ebf556b95b87acd5`.
**Status:** real PostgreSQL/MinIO acceptance pending until the integrator releases
the W55b full-gate service lane. This record makes no pass claim for that test.

## Prepared result

The new real-service test seeds a private source Blob and immutable version,
derives an exact temporary recording from the deterministic source stage,
persists a registered AR v2 recorded Run, then drives `execute_run`. A separate
database session checks five saved successful StageResults, one completed
recorded call with unknown cost, one finding/observation, a single terminal
Run/Job/Attempt and released Lease. It reads source, observation and merge
Blobs from MinIO by saved references and verifies hashes and sizes. A repeat
execution must refuse without allocating new rows.

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

## Checks before service release

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

## Contracts and limitations

No contract, migration, analysis, finding, job, composition, provider lock,
root dependency or global style changed. The bridge remains offline and
unserved, with explicit fixture parameters. The real DB/S3 assertions are
unverified until the integrator permits isolated service startup. Neither a
model/price pin nor a beta gate is claimed.

## Integrator instruction

Keep this candidate local while W55b runs its full gate. After lane release,
verify the three assigned ports are unused, start only this task's foundation,
migrate to `0022_findings_v2`, run the new test, then stop only this lane.
Investigate any failure through the actual persisted and Blob evidence before
amending the result. A green focused service test is required before this task
can be accepted or published on `origin/dev`.
