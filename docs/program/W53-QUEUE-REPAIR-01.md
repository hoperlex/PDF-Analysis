# W53-QUEUE-REPAIR-01 — stable queue continuation

Branch: `agent/w53-queue-repair-01`; assigned exact base:
`9b6698fada6b7ad78acb7f7548aca4800fb37d21`. This report is committed
with the repair; the exact handback HEAD is supplied separately because a
commit cannot name itself.

## 1. Changed files

- `src/auditmanager/execution/public.py` — queue reads use the coordinates
  captured in an emitted page, and queued equal-priority Jobs display in
  dispatch order (`created_at ASC, job_id ASC`). Other state groups retain
  their prior newest-first order. The anchor Job itself is excluded from its
  continuation after a priority or state edit.
- `src/auditmanager/bootstrap/adapters.py` — the queue adapter alone encodes
  and validates a versioned five-part opaque cursor containing rank, priority,
  creation time and Job ID. Journal cursor decoding is unchanged.
- `tests/integration/runs/test_w53_execution.py` — updates the existing queue
  repository test and adds emitted-cursor state, malformed-field and dispatch
  order regressions.
- `tests/integration/qa_w53/test_queue_and_effect_journal.py` — only the
  independent first queue test and its required imports changed. It now feeds
  the continuation string emitted by `ExecutionAdapter` back through that
  public adapter seam; the original unseen-B assertion is intact and it also
  checks the already-seen A is not duplicated.
- `docs/program/W53-QUEUE-REPAIR-01.md` — this handback.

## 2. Checks and results

The original independent QA log, `/tmp/w53-qa-01/queue-effect-counterexamples.log`
(SHA-256 `73839e55c2ffc1dc092f8c14e1affa02af2b9c34017c286fa3fa201f45be0c00`),
contains the red A=100/B=90 counterexample before the repair. The final
private-DB run on this tree is
`/tmp/w53-queue-repair-01/final-tree-focused.log` (SHA-256
`9affa1602c8d7d3f77957cfc411e60099e5457e5aa39360f117c33ef7fb0d091`):

```text
PYTHONPATH=src .../pytest -q tests/integration/runs/test_w53_execution.py \
  tests/integration/api/test_role_register.py \
  tests/integration/qa_w53/test_queue_and_effect_journal.py::test_priority_edit_does_not_hide_an_unseen_queue_job
37 passed, 1 upstream Starlette deprecation warning, 10.97 s
```

The four direct queue checks also passed together. They assert page 1/page 2
have no repeated anchor, unseen B remains after A's priority or state changes,
malformed tokens are `validation_failed`, and equal-priority queued order
matches the dispatcher's query. The first wider attempt had one test setup
failure because `job.created_at` is frozen by the database trigger; the test
ceased trying to rewrite that column, and the final complete run above is
green. An intermediate SQL parenthesis typo was corrected before that final
run. Neither failed attempt was treated as acceptance.

The private lane `gate-w53queue` used PostgreSQL port 56940 and old MinIO
60540/60541, no image build and no working stand. Its private database was
migrated to `0017_execution_queue`; the migration log is
`/tmp/w53-queue-repair-01/migrate.log` (SHA-256
`a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036`).
Preflight at 2026-10-09 13:55:18 UTC measured 10,788,622,336 available bytes
for both worktree and Docker data filesystem (`/dev/vda3`); the short private
run was estimated below 1.5 GB with a 5 GB margin. The later preflight at
13:57:54 UTC measured 10,670,518,272 bytes. Logs:
`/tmp/w53-queue-repair-01/preflight.log` and `final-preflight.log`.

`git diff --check` and Python compilation of all four edited code/test files
passed. The frozen OpenAPI digest remained
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
domain state-machine digest remained
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.

## 3. Contracts

No sealed API/domain contract, migration or generated client changed.
`next_cursor` remains an opaque string to callers. Its queue-only payload is
now version `q1` plus the emitted sort tuple. Old one-part queue cursors are
rejected as `validation_failed`; callers can reload page one.

## 4. Risks and known limitations

This is live keyset pagination, not a snapshot. Priority/state changes to
other already-seen Jobs can still reorder them, and a Job moved before an
issued boundary can be absent from later pages. The immediate anchor is
excluded to avoid a duplicate after its own edit. These limits need no new
contract promise; UI command success refreshes the first page. The full
`make gate` is still owed on the integrated candidate: this lane's task
forbids an image build, and host capacity for the new MinIO image has no
credible safe peak estimate.

## 5. Integrator instructions

Audit the exact five changed paths against the assigned base, cherry-pick
only this branch HEAD, and independently repeat the first QA queue test plus
the W53 execution queue tests on the merged exact SHA. Keep the other five
independent QA guards unchanged. Include this bootstrap-adapter change in the
final clean-SHA gate when the image/disk stop is resolved. Do not treat this
handback as QA acceptance, release or publication authority.

## 6. Allowed-path and forbidden-hotspot proof

`git diff --name-only 9b6698fada6b7ad78acb7f7548aca4800fb37d21`
listed exactly the four code/test paths above before this report was added;
the final five-path audit accompanies the branch HEAD. The only QA diff is
the first test and its imports. `contracts/**`, `db/migrations/**`,
`src/auditmanager/jobs/repository.py`, routers/schema/common cursor codec,
other QA tests, dependencies/locks, composition root outside the granted
adapter mapping, UI/global styles, release/backup/deployment paths, refs and
tags were not edited. Private containers, volumes and network are removed at
handback.
