# W53-JUDGE-Y-RECHECK — independent final consistency verdict

Assigned exact base: `4f9db3af870b5a94fafec8bdba40f49456c86f44`.
Branch: `agent/w53-judge-y-recheck`. This report is the only granted tracked path;
the integrator reads back its committed HEAD separately.

## Verdict by original Y finding

| Finding | Verdict on this candidate | Evidence and boundary |
| --- | --- | --- |
| Y-01, S3 rollback source | **PASS for source correction; full runtime unverified.** | `scripts/rehearsal/w53/minio_upgrade.py` now calls `export_versions(upgraded)` through the upgraded server's S3 API, compares its manifest to the upgraded read, and calls `restore_export(restored, exported)` on the empty old-image restore volume. The pinned new image was unavailable in this lane; no `--full` result is inferred. |
| Y-02, effect journal totality | **PASS.** | A fresh private 0017 database changed two prepared effects to `outcome_unknown` and recorded two `provider.outcome_unknown` events with safe Run/Attempt and classifier fields. Repeat reclaim changed zero effects and emitted zero more events. Terminal settlement changed one response-received effect to `abandoned`, recorded one `provider.abandoned` event, and repeat settlement changed none. The code loops over SQL `RETURNING` rows in the same transaction, once per changed effect. |
| Y-03, queue cursor and order | **PASS for the recorded loss and tie defect.** | The emitted five-part `q1` cursor preserves its original position after A is reprioritized from 100 to 0. The private probe returned still-queued B on the next page and did not repeat A. Static SQL readback confirms queued equal-priority order is `created_at, job_id` ascending, matching `_NEXT_JOB`. This is live pagination: an unobserved third row moved before the issued boundary may be absent from later pages; no snapshot promise exists. |
| Y-04, global pause in public journal | **OPEN owner/contract decision.** | The pause event remains durable under `CommandRecord`; `_JOURNAL_ALL` still exposes only `AuditRun`, `Job`, and `Attempt`. The frozen public entry requires `RunId`, while global pause has no Run. Publishing that event would require an owner-authorized contract reseal with optional/other scope, API and client changes, or an explicit correction of the W53 plan/acceptance wording to define a Run-bound journal. No artificial Run identity is acceptable. |
| Y-05, ALR-05 deep imports | **PASS.** | Both architecture guards pass in both 23-test suite orders. The three original deep imports now use narrow public context modules. |
| Y-06, cross-Run reclaim deadlock | **PASS for the recorded inversion.** | Periodic candidates came in Run-ID order; forced candidates contained only their named Attempt. A coordinated two-connection probe after each first Run lock committed both periodic and forced transactions, each recovering one Run, with no `40P01` or live thread. This does not prove absence of every possible database deadlock. |

The pause-claim race is also covered by the unchanged independent QA guard and the two-connection jobs regression in both suite orders. `start_execution` ensures and locks the singleton control row before Run/Job authority. A committed pause refuses a later claim; a concurrent pause waits for an already-locking claim. No new hard consistency defect was found in these bounded checks.

## Reproducible evidence

The private `gate-w53judge-y2` lane used local PostgreSQL image ID
`sha256:4c34fc74b2e596ec32e40006f009025895afc520b083635e969c3526c48827f6`
and old MinIO image ID
`sha256:d06b201c2490dfe8e98e03d29c5ee1de070d8cebec89d6d89e12850024077a28`.
Ports 56980/60580/60581 were unbound before launch. At 2026-10-09 14:18:30 UTC,
both worktree and Docker data used `/dev/vda3`, with 10,412,548,096 bytes free.
The no-build estimate was below 1 GiB plus a 2 GiB margin. Three distinct
private databases migrated to `0017_execution_queue`; migration logs
`/tmp/w53-judge-y-recheck/migrate-{a,b,c}.log` each have SHA-256
`a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036`.

On database A, the command below passed **23/23** in 2.86 s:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/integration/qa_w53 \
  tests/integration/runs/test_w53_jobs_repair.py \
  tests/integration/runs/test_w53_execution.py \
  tests/contract/architecture/test_alr05_boundaries.py
```

Its log is `/tmp/w53-judge-y-recheck/qa-first.log`, SHA-256
`c60c39fcd4c8cf695a22c32c63a1c0cb589c06594ebebeedb535f872ac62d51c`.
On separate database B, the same four groups with jobs repair before QA
passed **23/23** in 2.71 s. Log `/tmp/w53-judge-y-recheck/jobs-first.log`,
SHA-256 `be5176f2fb4fd0c1e9ad6bbbc8b622c5f8f15cae0e82059854ff594b7498bc90`.
Both commands used the repository's pinned root `.venv/bin/python` and only
private service settings.

On fresh database C, direct independent probe
`/tmp/w53-judge-y-recheck/probe.py` (SHA-256
`23029abb55c3d5a73703baa87e639d1ff62bb30c4371c8321cc47c2e257c8af2`)
compiled and passed. Its output `/tmp/w53-judge-y-recheck/probe.log` (SHA-256
`98de44dfa61bf2407993a87296497c57397241d7627c79654e5829e5c5a0f15a`)
records `missing=false`, `duplicate_anchor=false`, two effect events for two
changed effects and no extra events on repeat, one abandonment event and no
repeat settlement, stable candidate order, and both reclaim transactions as
`committed:1` with both threads exited. Static readback checked the exact
queue SQL, frozen cursor encoding, effect `RETURNING` loops, global journal
projection, and the S3 export/restore source.

Frozen OpenAPI SHA-256 remains
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
state-machine SHA-256 remains
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
After tests, 10,324,717,568 bytes were free; after private cleanup,
10,406,752,256 bytes were free. The lane's two containers, two named volumes
and mode-0600 credential file were removed. Its three ports are clear; no
working-stand resource or shared cache/image was touched.

## AGENTS.md §5 handback

1. **Changed files:** only `docs/program/W53-JUDGE-Y-RECHECK.md`.
2. **Checks/results:** two fresh 0017 suite orders **23/23** each; third fresh
   0017 direct queue/effect/concurrency probe passed; static code/SQL review,
   frozen hashes, disk preflight and `git diff --check` passed. Exact logs and
   hashes are above. No full gate was run in this review lane.
3. **Contracts:** none changed or resealed.
4. **Risks/known limitations:** Y-04 remains an explicit owner/contract
   decision; a new-image MinIO full upgrade/restore run remains unverified;
   live queue pagination is not a snapshot. The frozen 503 discriminator and
   `validating` cancellation stops remain outside this review.
5. **Integrator:** audit and cherry-pick this report-only commit. Preserve
   Y-04 as open until the owner defines public-journal scope. Require the
   full new-image rehearsal when capacity/image availability permits; use
   the final clean-SHA `make gate` as a separate integration gate.
6. **Forbidden hotspots:** exact base-to-HEAD changed-path audit is this
   one report only. Product/test source, `contracts/**`, migrations, root
   dependencies/locks, composition root, global styles, release/backup/
   deployment paths, other reports, refs, tags and working stand are
   untouched. The branch is clean at handback.
