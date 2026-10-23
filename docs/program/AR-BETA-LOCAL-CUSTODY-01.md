# AR beta local corpus custody and qualification

**Task:** [AR-BETA-LOCAL-CUSTODY-01](tasks/AR-BETA-LOCAL-CUSTODY-01.md). **Date:** 2026-10-23 UTC. **Development base:** `8eaaa8470146546d7aebaefe81becb422c2673fa`. This is an isolated local import, not a production stand change or a served AR v3 profile.

## Result

The complete repaired W54 bundle was imported into a new local PostgreSQL and MinIO lane. The importer exited **0** with `report: full match`. A separate `report` command exited **0** with the same result. The application's qualification predicate returned `build_complete=True, sources_confirmed=True` for `ns_01M59N8QNBVN91ACA2HCE6VE74`; all 674 source PDFs have the required custody binding. The test-data waiver was closed after the independent report.

| Evidence | Observed value |
| --- | --- |
| Source bundle | `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`; `SHA256SUMS` SHA-256 `7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245` |
| Bundle verification | 28,979 files verified byte-for-byte before import |
| Rows | 674 documents, 350,194 paragraphs, 0 unreliable paragraphs, 55,855 chunks, 61,573 embedding windows, one complete embedding build |
| Digests | row `a3111764c9fb01796444880a979fa50530948f93d9fedde194cecb3c873ff7ac`; build `e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df`; binding `d2de2a610b340d447e5cb86311823b0bab106969ec9f933b7c88c7a475398485` — all `match` |
| Custody | 28,920 confirmed admissions, 28,920 bindings and available Blobs, 5,055,102,708 manifest Blob bytes, 0 pending/poisoned/rejected admissions, 0 custody incidents, 0 other Blobs |
| Reconciler | All 28,920 objects checked; `report: full match` on both importer and independent report |
| Application predicate | `Qualification(build_complete=True, sources_confirmed=True)`; exact PDF binding query returned 674 of 674 |
| Client isolation | Seeded client fingerprint `63b1382badcbe53ee7a45c3f455472ff21fe9b3b346dafb521b262c7aa0821a6` matched after import; no client Blob, Run, document or finding rows appeared |

The local lane is `auditmanager-ar-beta-custody`, database `auditmanager_ar_beta_custody` on `127.0.0.1:58490`, MinIO API `127.0.0.1:62090`, console `62091`, bucket `auditmanager-ar-beta-custody`. It has its own named PostgreSQL and S3 volumes. The schema is at `0031_executor_pull_channel` and the contract remains `1.1.0`. The source bundle, promotion database, other lanes and stand were not modified.

## Capacity, commands and waiver

The owner explicitly approved deleting **Docker build cache only**. `docker builder prune -af` reclaimed 9.792 GB; `docker system df` then showed `Build Cache 0B`. Free filesystem bytes rose from 3,185,438,720 to 12,867,813,376. Images and container-data volumes were retained. After import and the independent report, free space was 4,685,897,728 bytes (97% filesystem use). Do not start another full corpus copy on this host without a fresh capacity check.

The lane's `.env` was generated from `.env.example` after instance/port isolation checks. `make up`, `make migrate`, `make check-services`, `make check-db` and `make check-storage` all passed. The bundle's official `verify`, `import <bundle> --copy-record .local/copy/record.json`, and a later independent `report <bundle> --copy-record .local/copy/record.json` each exited **0**. The import took approximately 34 minutes, including all object uploads and embedding rows. The independent report took about 49 seconds. The full report matched every corpus count and digest and checked all 28,920 custody objects.

The ignored local test-data waiver recorded the lane identity, `0031` migration head, no application writers, no real-data marker, 0 rejected Blobs, the seeded client fingerprint, and a 12-hour expiry. It was open only for this import and report. After the successful report, `.local/copy/record.json` was changed to `state: closed` at `2026-10-23T09:07:20Z`; the open version is kept in the ignored `.local/copy/record.open.json` for audit. No waiver was sent to the stand.

## Integration and limits

This qualifies the repaired snapshot **in this local lane** for later retrieval-set work. It does not designate it current, approve legal editions or C01–C22 map bytes, create reviewed query vectors or `nrs_` sets, send six model Runs, or activate v3. The [beta review gate](AR-BETA-CITATION-REVIEW-GATE-01.md) remains unserved. The map/set owner can now use this exact snapshot and bundle identity, but must resolve each source/branch decision and produce verified six-group sets before runtime integration. In the accepted Ф1.3 beta policy, any unresolved item stays `требует проверки эксперта` with no numeric conclusion. The BGE-M3 query-vector runtime and weights are absent locally, so this task makes no vector or set claim.

The lane may be removed with `make down` using its own `.env`, followed by removal of **only** `auditmanager-ar-beta-custody-postgres-data` and `auditmanager-ar-beta-custody-s3-data` if this evidence is no longer needed. Keep the immutable bundle. Cache pruning is reversible through subsequent builds.

## Checks and ownership proof

`git diff --check` passed. Before fast-forwarding from `8eaaa847` to the newly published development base `d855ebbc`, `tests/contract/program/test_wave_governance.py` passed (**16 tests**). On `d855ebbc` it yielded **15 passed, 1 failed**: the new `EXEC-ENV-OPENROUTER-01`, `EXEC-SSH-CROPS-01` and `EXEC-SSH-TUNNEL-CROPS-01` task files on that base lack mandatory governance fields; this task file was not in the finding set. The full `make gate` is deferred by R-135 for this report-only slice; the base also has a `CURRENT_STATE.md` length guard issue (139 lines versus a 120-line limit). No contracts, migrations, dependency or lock files, composition root, global styles, code runtime, other lane volumes, `origin/main`, tag or deployment host were changed. The only tracked changes in this task are this report and its task file; all local environment, copy records and Docker volumes are outside Git.
