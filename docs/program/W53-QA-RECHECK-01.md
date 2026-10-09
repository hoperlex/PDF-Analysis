# W53-QA-RECHECK-01 — independent repaired-candidate QA

Assigned branch `agent/w53-qa-recheck-01`, exact base
`30448b6ebbed2b78c5a91853ef37b89b64cef1d7`. This is evidence for the
integrator, not a complete gate, release, new-MinIO or working-stand verdict.

## Independent result

The **six original independent `qa_w53` regressions passed 6/6** on a fresh
private PostgreSQL database migrated to `0017_execution_queue` and the old
repository-owned MinIO image. The two real two-connection pause/reclaim
regressions passed 2/2 on another fresh database, including the coordinated
periodic/forced reclaim overlap without PostgreSQL `40P01`. The full W53
execution file passed 13/13 on a third fresh database; ALR-05 passed 2/2.
The original proxy-body/503, mutable queue anchor, pause claim, and both
provider-effect journal counterexamples were not reproduced on this tree.

An intentionally combined invocation of those four suites on one fresh
database was **red: 20 passed, 3 failed**. All three failures are existing
queue tests in `test_w53_execution.py`: `test_queue_cursor_follows_priority_order_after_new_insert`,
`test_queue_emitted_cursor_survives_anchor_state_edit_and_refuses_bad_fields`,
and `test_queued_tie_order_matches_dispatcher`. Earlier tests commit queued
Jobs; the independent pause race leaves
`job_01M4GFNY8NGV40NG3G5FG476C1` queued at priority 100. Each queue test
assumes its own Job is the first global queue row, so the committed Job appears
instead. Three separately migrated 0017 databases made the three failed
nodes pass 1/1 each. This is a **test-isolation defect and a full-battery gate
risk**; the green focused runs do not erase the red combined run. Repair needs
an exact test-path grant and a repeated combined run. No product-code repair is
inferred from this counterexample.

## Private live viewport

One exact-tree Next 15.5.25 production build passed. Chrome for Testing
`154.0.8037.92` then drove an isolated API on `127.0.0.1:57060` and web on
`127.0.0.1:31560`, backed only by this lane's fresh 0017 database and old
MinIO. A synthetic complete administrator changed one paused queued Job's
priority to 42; a synthetic complete expert cancelled that Run. The database
readback was `(job.state='cancelled', priority=42, run.state='cancelled')`,
with `job.priority_changed`, `job.transition`, and `audit_run.transition`
among its six events. No provider call was made.

At **780×900**, Chrome measured eight rendered states: administrator queue
before, confirmation and after the priority action; administrator journal;
expert queue before, confirmation and after cancellation; expert journal.
Every state had `scrollWidth <= innerWidth=780` and zero width offenders.
The journal displayed the fixture Run. The expert queue did not expose the
administrator's priority control. This is a private live result for these
screens and actions only; it is not the deferred W51/W52 journey or a
working-stand check. Log `/tmp/w53-qa-recheck-01/live-browser.log`, SHA-256
`a5effb8e4625e18cb9023d2ad12b46819a767c1e008d7d2e14d139e9cfa91832`.

## Checks and capacity evidence

Frozen OpenAPI SHA-256
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`,
domain state-machine SHA-256
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`,
API version `1.0.0-draft.1` and migration head
`0017_execution_queue` matched the grant. Private image IDs were PostgreSQL
`sha256:4c34fc74b2e596ec32e40006f009025895afc520b083635e969c3526c48827f6`
and **old** MinIO
`sha256:d06b201c2490dfe8e98e03d29c5ee1de070d8cebec89d6d89e12850024077a28`.

Before private services at 2026-10-09 14:03:24 UTC, `df -B1 .
/var/snap/docker/common/var-lib-docker` reported **10,695,348,224** available
bytes on the same `/dev/vda3`; all five assigned ports were unbound. Existing
image startup, migration and small fixtures were estimated below 1.5 GB plus
a 5 GB margin. Before the cold Next build at 14:07:57 UTC, the same filesystem
had **10,467,602,432** available bytes. The comparable W28 web-build record
(`docs/program/reviews/W28-LIVE.md` §10) bounded observed growth at about
3.4 GB; this run allowed a conservative 5 GB peak plus a 3 GB margin and a
supervisor that stopped the whole build below 3 GB free. The build exited 0
on its only attempt; minimum recorded free space was **10,314,727,424** bytes.
Build log `/tmp/w53-qa-recheck-01/next-build.log` SHA-256
`734ccd5ef1213189833f85ee2d615d17f727857addd84c4191048457d31d91d0`;
disk monitor log `/tmp/w53-qa-recheck-01/next-disk.log` SHA-256
`dcdf103c2def72f2dcb8a02af222951a830482d5c60f8fc622941cd526e26b6a`.

| Exact check | Result | Log SHA-256 under `/tmp/w53-qa-recheck-01/` |
| --- | --- | --- |
| `PYTHONPATH=src .../python -m alembic --config db/migrations/alembic.ini upgrade head` on the first empty DB | 0017 | `migrate.log` `a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036` |
| `PYTHONPATH=src .../python -m pytest -q tests/integration/qa_w53 tests/integration/runs/test_w53_jobs_repair.py tests/integration/runs/test_w53_execution.py tests/contract/architecture/test_alr05_boundaries.py` | **3 failed / 20 passed**, cross-suite queue contamination | `required-tests.log` `2c9613990e02a73627a4789ba38dd864cbf6a282beb655adb20f1a6af073ac1d` |
| The three failed queue nodes, each on its own new migrated DB | 1/1 each | `queue-q1.log` `acb50bc88917f57929611d63c707e0ccd387dae970fefba6e9100a81f12eba7b`; `queue-q2.log` `0c33791aa03cbc8826ba04efd1b062adb3baa875c47625e4de7090bd753d7635`; `queue-q3.log` `866432d567eb30f716ad0380ad29e9453b6fd80645780de4fbe94565dc3eab20` |
| `.../python -m pytest -q tests/integration/qa_w53` on a fresh DB | **6 passed** | `qa-six.log` `29fe33603395be7dd07a4febbd5aa11392a8d6b257cded3e92de8342a7d585f2` |
| `.../python -m pytest -q tests/integration/runs/test_w53_jobs_repair.py` on a fresh DB | **2 passed** | `jobs-two.log` `8d0874d56aff5efde82c3c15c74030ec4fe6fa3cc7b9d57d49178bc2f48dfcee` |
| `.../python -m pytest -q tests/integration/runs/test_w53_execution.py` on a fresh DB | **13 passed** | `execution.log` `3d93fc0ff85dad89e4671f365f219fd3d8a51dcc2d37b7eef4dfa11ee7bc9ee3` |
| `.../python -m pytest -q tests/contract/architecture/test_alr05_boundaries.py` | **2 passed** | `alr05.log` `d2e19278f2acef7cfe468afa87fbba8925315ff38a8d23649526ec4f7bbe6521` |

The separate queue databases' migration logs each matched the first migration
log's SHA-256 above. The API/web startup logs are
`api-live.log` `1dac697f1582f20fa7bbbcfc28c68630e571d0a0c31872dd40224bb70d334d7d`
and `web-live.log` `f05d5aa521b9559ce1605568e948a05d7fbc983bfb1844b3e3e54ea507b30535`.
`git diff --check` passed. No full `make gate` was attempted.

## AGENTS.md §5 handback

1. **Changed files:** this report only.
2. **Checks/results:** the table above; frozen digests and private 0017 head
   matched; live eight-state viewport passed; the combined-battery
   test-isolation failure remains red and its traceback is preserved.
3. **Contracts:** no API, domain, migration, event schema, generated client or
   other contract changed.
4. **Risks/limits:** the combined-run failure needs a test-isolation repair
   before a full-battery gate. Global pause's public-journal scope, own-proxy
   503 and `validating` cancellation are separate owner decisions. The new
   MinIO image, working stand, release lineage, final X/Y review and complete
   gate remain outside this report.
5. **Integrator:** audit the one report path; issue a narrow grant for the
   cross-suite committed queue-row contamination, repeat the combined command
   after repair, and personally recheck QA on the final exact SHA. Do not infer
   a green full gate or publication authority from these focused checks.
6. **Forbidden hotspots:** the base-to-handback diff is only
   `docs/program/W53-QA-RECHECK-01.md`. No product/test source, contract,
   migration, lock, composition root, global style, release, backup or deploy
   path, ref/tag or working stand was changed. This lane's two containers,
   volumes, Next/API processes, generated `.next`, dependency symlink and
   disposable credential files were removed. At 14:14:58 UTC all assigned
   ports were unbound and no `gate-w53qare` Docker resource remained.
