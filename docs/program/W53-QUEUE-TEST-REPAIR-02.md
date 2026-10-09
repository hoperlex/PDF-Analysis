# W53-QUEUE-TEST-REPAIR-02 — queue tests on a live global queue

Branch `agent/w53-queue-test-repair-02`; exact assigned base
`1685f5676b9e106dcb5a97fc98957506860b32d5`. The integrator reads the
committed HEAD separately because this file cannot name its own commit.

## 1. Changed files

- `tests/integration/runs/test_w53_execution.py`: only the three granted queue
  tests and a helper for locating their own emitted one-item page changed.
  A preceding committed priority-100 Job no longer displaces their own anchor
  assertions. The tie test now compares the whole eligible global order to
  the dispatcher's SQL order and still checks its own equal-priority subset.
- `tests/integration/qa_w53/test_queue_and_effect_journal.py`: only the first
  independent A/B queue test locates A's emitted page. Its unseen-B and
  no-duplicate-A assertions remain word-for-word intact. The other five QA
  checks were not edited.
- `docs/program/W53-QUEUE-TEST-REPAIR-02.md`: this report.

## 2. Checks and results

The independent combined run before this grant had **20 passed, 3 failed**:
`/tmp/w53-qa-recheck-01/required-tests.log`, SHA-256
`2c9613990e02a73627a4789ba38dd864cbf6a282beb655adb20f1a6af073ac1d`.
The three failures were assumptions that each newly created Job was globally
first after a prior test committed a priority-100 Job.

The requested reverse-order probe proved the first QA A/B test had the same
assumption. On this lane's private database, running its committing pause
guard before A/B gave **1 passed, 1 failed** at the old first-page assertion:
`/tmp/w53-queue-test-repair-02/reversed-before.log` (SHA-256
`b19583cf97eec4724d6fd24cdd654017685a759743b9c078ba983b03edc7b5ad`).
The committed priority-100 queued Job remained in the database. After the
narrow A/B edit, the same database and Job yielded **1 passed**:
`reversed-after.log` (SHA-256
`b336bfbb42d8a55315e2f7350d4a6528e0fd95453f81c1e21f96f9ae7c5d2932`).

Two new, separate migrated `0017_execution_queue` databases then ran the
exact combined battery on the final test tree:

```text
pytest -q tests/integration/qa_w53 \
  tests/integration/runs/test_w53_jobs_repair.py \
  tests/integration/runs/test_w53_execution.py \
  tests/contract/architecture/test_alr05_boundaries.py
23 passed in 2.86 s

pytest -q tests/integration/runs/test_w53_jobs_repair.py \
  tests/integration/qa_w53 \
  tests/integration/runs/test_w53_execution.py \
  tests/contract/architecture/test_alr05_boundaries.py
23 passed in 2.94 s
```

Both commands used `PYTHONPATH=src`, the root pinned `.venv/bin/pytest`, and
only this lane's disposable PG/S3 settings. Logs are
`/tmp/w53-queue-test-repair-02/verified-qa-first.log` (SHA-256
`c60c39fcd4c8cf695a22c32c63a1c0cb589c06594ebebeedb535f872ac62d51c`)
and `verified-jobs-first.log` (SHA-256
`cd9f3293cfbe864926b41b6dfe69be33503f3a4fd80cecaba98e4adaba043d26`).
All six independent QA guards, both real concurrency checks and two ALR-05
guards are included in each run.

The corrected assertions remain sensitive to the product defects. Two
temporary pytest plugins under `/tmp/w53-queue-test-repair-02/` changed only
the SQL object in test-process memory: `mutate_anchor.py` resolves the
emitted cursor's priority from the mutable Job row; the A/B test fails at
`assert unseen in ...` (`mutation-anchor.log`, SHA-256
`c74d61c151fddb58f35a2c635e69bf2043ca209356e1e277b00393991c6442f4`).
`mutate_tie.py` restores queued newest-first ordering and matching keyset
comparisons; the dispatcher-order test fails at its global order assertion
(`mutation-tie-final.log`, SHA-256
`d0d0d923e2e86ecd4e6df619b28e2e26fc3bf4dcc73f410c950df7a2ca52230c`).
No mutation was written to the repository.

Before services, 2026-10-09 14:08:08 UTC `df -B1 .
/var/snap/docker/common/var-lib-docker` measured 10,371,559,424 bytes free
on the same `/dev/vda3` filesystem; ports 56970/60570/60571 were free. At
14:12:12 UTC, before the final exact runs, both filesystems had
10,128,359,424 bytes free. The already-local PostgreSQL and old MinIO images
were used with an expected incremental peak below 1 GB plus a 2 GiB margin;
no image was built. Preflight logs are `preflight.log` and
`verified-preflight.log` under the same `/tmp` directory. `git diff --check`
and Python compilation of the two edited tests passed. The frozen OpenAPI
SHA-256 remained
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
the domain state-machine SHA-256 remained
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.

## 3. Contracts

No product source, API/domain contract, migration, event shape or generated
client changed. This is test isolation only.

## 4. Risks and known limitations

The tests traverse the live global queue until their own anchor, so they may
read more pages when other committed Jobs exist. That work is confined to
tests. It does not assert a snapshot of concurrent queue mutations. The full
`make gate` remains an integration obligation and was not run in this
test-only lane; the new MinIO image and host capacity remain separately open.

## 5. Integrator instructions

Audit the exact three changed paths against the assigned base, especially
the A/B and dispatcher assertions, and cherry-pick this branch HEAD. Repeat
the two exact 23-test orders on the merged SHA using a fresh database for
each order. The lane's private containers, volumes and network are removed
at handback. No ref or tag publication is authorized here.

## 6. Allowed-path and forbidden-hotspot proof

The final `git diff --name-only <assigned base> HEAD` must list exactly the
three paths in section 1. The QA diff touches only its first test; every
other QA test stays byte-identical. Production source, `contracts/**`,
`db/migrations/**`, root dependencies/locks, composition root, global
styles, release/backup/deployment paths, refs, tags and the working stand
were untouched. The mutation plugins and all logs live only under `/tmp`.
