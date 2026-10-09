# W53-REHEARSAL-01 — disposable runtime evidence

Branch `agent/w53-rehearsal-01`; assigned base
`ce73910ac60a6d24867286ad8e25988ee925d333`. The exact handback HEAD is
read back by the integrator after this report is committed. No release, working
stand, published ref or tag is part of this lane.

## 1. Changed files

- `scripts/rehearsal/w53/proxy_faults.py` — local HTTP fault server and durable
  `execute_run` checks against isolated PostgreSQL/S3.
- `scripts/rehearsal/w53/process_recovery.py` — first serving process killed by
  SIGKILL after a committed response; second process recovers and tests refusal.
- `scripts/rehearsal/w53/minio_upgrade.py` — versioned-object baseline and
  future stopped-volume/new-image/S3-restore procedure.
- `docs/program/W53-REHEARSAL-01.md` — this evidence and handback.

## 2. Commands, observations and logs

The private lane used PostgreSQL image
`auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9` on `127.0.0.1:56880`
and old MinIO image
`auditmanager-minio:RELEASE.2025-09-07T16-13-09Z-07c3a42` on
`127.0.0.1:60480/60481`. Both databases were migrated to
`0017_execution_queue` with `python -m alembic --config
db/migrations/alembic.ini upgrade head`; the S3 bucket was private and
disposable. A fresh second database isolated the exact one-lease crash count
from prior scenario rows. No real provider credential or paid endpoint was
used. Temporary credentials were held in mode-0600 files under
`/tmp/w53-rehearsal-01/` and removed after the tests.

| Scenario | Runtime observation | Result |
| --- | --- | --- |
| No bytes written / refused TCP connect | Zero proxy requests; three bounded `not_sent` attempts, each `not_processed`; terminal Run failed, zero `model_call` rows | PASS |
| HTTP 429 with `Retry-After: 2` | Three bounded requests and `rate_limited` / `not_processed` effects; adapter reported two seconds; no paid call | PASS |
| Reset after complete request body | One request only, `outcome_unknown`, no automatic repeat | PASS |
| Foreign HTTP 503 | One request only, `outcome_unknown`, no automatic repeat | PASS |
| HTTP 400 | One request only, `definite_refusal` / `not_processed` | PASS |
| Real process death after response checkpoint | First process saved `provider.response_received`, then parent sent SIGKILL, exit `-9`. Second process observed Run/Job `running` and effect `response_received`; after expiry of only that dead lease, it reclaimed one Attempt and reconciled Run/Job to `failed`, Attempt to `lost`, Lease to released and effect to `abandoned`. One provider dispatch marker remained; a second `execute_run` was typed refused. The 21 journal events ordered `provider.prepared` before `provider.response_received`; no token sentinel or `Authorization` appeared in event payloads. | PASS |
| Own-proxy HTTP 503 safe retry | No genuine source-backed envelope supplied; arbitrary 503 was exercised as unknown above | BLOCKED — `W53-EXEC-STOP-01` |
| Old MinIO versioned objects | Four versions across three keys: two `alpha.txt` generations, 32,768-byte binary and empty object. Each version's key, bytes, digest and metadata read back from old image. | PASS — old baseline only |
| New image opens stopped-volume copy | New pinned image does not exist locally; build was stopped before launch by disk rule | BLOCKED — capacity, `D-119` / `D-123` |
| S3-level restore and rollback to old image | Needs successful new-image read first; not run | BLOCKED — capacity, `D-119` / `D-123` |

`/root/projects/PDF-Analysis/.venv/bin/pytest -q
tests/integration/analysis_text/test_proxy_adapter.py
tests/integration/runs/test_w53_execution.py
tests/integration/runs/test_durable_effect_boundaries.py` passed **110 tests in
9.34 s** on the private services. The proxy script's full execution runs
failed closed as expected: five terminal failed Runs, 0 `model_call` rows,
23–27 journal events each. The simulated provider cost was **$0**; no
external provider was contacted. The process script's only provider-dispatch
marker remained **1** after recovery. Both scripts exited zero.

Evidence logs and SHA-256:

| Log | SHA-256 |
| --- | --- |
| `/tmp/w53-rehearsal-01/focused.log` | `45bcfab213e968dffd36ad95814033dc809f7fd6f135aa4e14d5a3e2b15c10d7` |
| `/tmp/w53-rehearsal-01/proxy-faults.log` | `6d09ba2902b74291f4bb55c9d4420359ab555b7f3f68fc35da2ab432989a712c` |
| `/tmp/w53-rehearsal-01/process-recovery.log` | `028b5f0509739aeb8387edcf7f6e4012d6bf06ff14ce4d910b86aa2f4cee7396` |
| `/tmp/w53-rehearsal-01/old-minio-versions.log` | `4687cdb53cc0244feccae40277e45c5128ecd381e7a86a61480df9f1890e626b` |
| `/tmp/w53-rehearsal-01/migrate.log` and `kill-migrate.log` | `a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036` each |

Python compilation of all three scripts passed; the live API prose/surface
guard passed **33 tests in 3.72 s**; `git diff --check` passed. The guard log
`/tmp/w53-rehearsal-01/prose-guard.log` has SHA-256
`df03758e0f394ef3946741f088c3593ae7b1ed2c82dea9d71ec5c9a6405388ac`.
The first draft of the proxy harness queried a nonexistent `created_at`
column and was corrected to `prepared_at` before the passing run. The first
crash run reused a database containing old scenario leases; a fresh private
database then gave the exact one-lease result above. Neither was an
application defect or a passing observation used for acceptance.

### Disk preflight and image stop

`date -u; df -B1 . /var/snap/docker/common/var-lib-docker` on
2026-10-09 13:29:18 UTC reported **11,930,836,992 available bytes** on the
same `/dev/vda3` filesystem for worktree and Docker root. Earlier in this
lane the available count was **11,972,038,656 bytes**. The prior MINIO lane's
build had already consumed more than 3 GB and stopped amid Go module
download/compilation before either server/client binary finished. The
remaining peak plus margin has no credible bound. Under AGENTS.md §8, **no
new image build was launched** and no shared BuildKit cache was pruned.
Read-only `docker image inspect` returned old image ID
`sha256:d06b201c2490dfe8e98e03d29c5ee1de070d8cebec89d6d89e12850024077a28`
and `No such image` for
`auditmanager-minio:RELEASE.2025-10-15T17-29-55Z-9e49d5e`. Executable
version and labels of the new image, compatibility and rollback cannot be
claimed. The old-image baseline is not upgrade acceptance. In a sufficient
private build slot, first repeat the disk preflight with a measured growth
bound and margin, build and inspect the exact pinned image, then run
`minio_upgrade.py --full` against only this lane's empty port 60480. On a
stopped-volume copy it compares exact VersionIds, keys, bytes and metadata;
S3-level restore compares logical version history and bytes because a fresh
S3 restore necessarily issues new VersionIds. That full path remains unrun.

## 3. Contracts

No API, domain, migration, image pin, UI or release contract changed. The
OpenAPI SHA-256 remains
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
the state-machine SHA-256 remains
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
The `validating` cancellation refusal stays under `W53-EXEC-STOP-02`.

## 4. Risks and known limits

MinIO new-image build/compatibility/rollback are blocked by unbounded peak
disk demand and remain open as `D-119` / `D-123`. The actual own-proxy 503
case requires the owner-supplied envelope/source in `W53-EXEC-STOP-01`.
The runtime fault server used synthetic error bodies on loopback; its 503 is
deliberately foreign/ambiguous. The process-loss rehearsal used a recorded
response through a live-mode test adapter, so it proved durable checkpoint,
lease and at-most-once handling without spending money, not a real provider's
availability. No live browser, working-stand upgrade, backup or full gate was
attempted. All lane containers and volumes were removed; reserved ports
56880, 60480, 60481, 56980 and 31480 were free at cleanup readback.

## 5. Integrator instructions

Read the logs and path audit on this clean branch. Accept the measured fault
classification and process recovery only as disposable runtime evidence;
retain both stop records. Do not accept the new MinIO image or rollback until
its full procedure completes under a safe disk preflight. Keep database
backup in the separate beta wave and working-stand S3 untouched. Continue
independent QA and the final exact-SHA gate only on a clean integration tree.

## 6. Allowed paths and forbidden hotspots

The base-to-HEAD diff contains only this report and three **new** files under
`scripts/rehearsal/w53/`, exactly the task's `allowed_paths`. No
`contracts/**`, migration, root dependency/lock, composition root, global
style, VERSION, notes, deployment or working-stand file changed. No refs or
tags were created or published. The only Docker resources created or
removed carried the `gate-w53rehearsal` lane name/label; no shared cache,
image tag, unrelated container, volume or agent worktree was changed.
