# W53-ALR05-REPAIR-01 — public boundary handback

Assigned base: `df5c21809c597393f76701029d41558378f2932b`.
Branch: `agent/w53-alr05-repair-01`. The integrator reads the exact HEAD after
this report is committed.
The private-lane port amendment is `2f423b9dcfe954e29da524207ab8469f8971b8b8`.

## 1. Changed files

- `src/auditmanager/api/app.py`
- `src/auditmanager/runs/public.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/jobs/public.py`
- `docs/program/W53-ALR05-REPAIR-01.md`

## 2. Checks and results

- The exact ALR-05 architecture guard passed 2/2:
  `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/architecture/test_alr05_boundaries.py`.
  Log `/tmp/w53-alr05-repair-01/alr05.log`, SHA-256
  `6ae60db2592ba5cbc3b7d38bd4c72e9df3688404ab51d9d4eb9b30c39d053fdd`.
- Fresh interpreter import orders `jobs → runs → api` and `runs → jobs → api`
  passed; the no-service documentation app constructed with five routes.
  A no-service serving-start probe confirmed that only `DurableCarrier` receives
  `start()`. `compileall` passed on the five changed Python files. Logs and hashes:
  `/tmp/w53-alr05-repair-01/pure-imports.log` (`47452376682779090b1da9d68b3214e5a9d43f75fa41319fa362b5d478f65676`),
  `/tmp/w53-alr05-repair-01/compileall.log` (`5975a18a61517e3d32f0e9dd18a7587545eb6a05ec29052f08f74ca55ce1bfb8`).
- The assigned disposable lane used PostgreSQL at `127.0.0.1:56930` and old
  MinIO at `127.0.0.1:60530/60531`, with a unique database and private bucket.
  The fresh database migrated to `0017_execution_queue`. `test_w53_execution.py`
  passed **11/11**; exact serving-lifespan, two-connection lease and watchdog
  nodes in `test_the_run_leaves_the_request_thread.py` passed **4/4**.
  Migration log `/tmp/w53-alr05-repair-01/migrate.log` has SHA-256
  `a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036`;
  test logs `/tmp/w53-alr05-repair-01/w53-execution.log` and
  `/tmp/w53-alr05-repair-01/composition.log` have SHA-256
  `3f039774d4c26caca6e1cf94d04e29bb95ad2635a27655a0273320c388fc6a74`
  and `d69c8bff2c8a68f6b08fe8e006209cd4775481dfd8d5f5421559724dfe27d3c4`.
  Both lane containers were removed after evidence; disposable credentials were
  removed from `/tmp`.
- Disk preflight at 2026-10-09 13:49:31 UTC measured 11,044,261,888 available
  bytes on both the worktree and Docker filesystem. Existing images avoided a
  build; private volumes/logs had a below-1-GiB estimate and 2-GiB safety margin.
  Log `/tmp/w53-alr05-repair-01/disk-preflight.log` has SHA-256
  `6feb753340363c05d025c2f6c9b424c149c9642d7c8b567bdd18406285c2dec6`.
- `git diff --check`: passed.

## 3. Contracts

No frozen contract or migration change. OpenAPI SHA-256 remains
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
state-machine SHA-256 remains
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
The Python cross-context surface adds two narrow Run operations and two Job
heartbeat operations. It does not change API shape, retry policy or durable state.

## 4. Risks and limitations

Y's separate journal/pagination findings, its confirmed concurrent reclaim
deadlock across two Runs, and the six independent `qa_w53` defects are outside
this boundary repair. The focused tests above do not establish a full gate or
resolve those independent defects.

## 5. Integrator instructions

Audit this branch against the assigned base, then cherry-pick the exact clean
HEAD. Repeat ALR-05 on the merged SHA. The shared `jobs/repository.py` hotspot
can then be granted to the separate behavior-repair lane. This report does not
claim full gate or wave acceptance.

## 6. Forbidden-hotspot proof

The exact base-to-HEAD path list is the six files in item 1, all granted by
`tasks/W53-ALR05-REPAIR-01.md`. No contract, migration, root dependency/lock,
other composition file, global style, generated client, test, proxy, release,
backup, deployment, ref or tag is changed. No working stand or shared cache
was touched.
