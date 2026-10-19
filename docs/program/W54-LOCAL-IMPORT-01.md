# W54-LOCAL-IMPORT-01 — the verified norms bundle imported into an isolated local stack

**Date:** 2026-10-19/20 (20:21-20:59 UTC). **Base:** `a1a25ebc` (`integration/night-1020`, on
`origin/dev` `9cf21cc0`). **Branch:** `agent/w54-local-import-01`.
**Task:** `tasks/W54-LOCAL-IMPORT-01.md`. **Rulings:** `R-110` (test-data waiver), `R-135`, `R-139`.

## Result

The verified W54 bundle was imported into this lane's own PostgreSQL and MinIO under a local
test-data waiver. `import` exited 0 with a full-match report, a second `import` of the same
bundle was a no-op that also exited 0, and an `import` under the closed waiver was refused. An
administrator then designated the snapshot through `setCurrentNormSnapshot`. The served API
answered `searchNorms`, `getNormDocument`, `listNormParagraphs` and a ranged
`streamNormDocumentContent` from the real corpus. No code defect showed up, so no code changed.

| Field | Value |
| --- | --- |
| bundle | `.local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307…5245` (read-only) |
| bundle digest / `manifest.json` SHA-256 | `7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245` / `cc0f5ee80ef4b2be43ff41789930ed8e5d14056cdfa6101f97ef582f138f21cf`, both re-read after the task |
| snapshot | `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff` |
| database | `auditmanager_w54_local_import` at `0023_norm_citations` (the bundle needs `0018_norm_custody`) |
| imported | 674 documents, 350,194 paragraphs (0 unreliable), 55,855 chunks, 61,573 windows |
| row / build / binding digest | `a3111764…f7ac` / `e7fac64c…c5df` / `d2de2a61…8398` — each `match` |
| custody | 28,920 admissions confirmed, 28,920 bindings, 28,920 Blobs `available` (5,055,102,708 bytes), 0 rejected, 28,920 objects point-checked by the reconciler, 0 incidents |
| client fingerprint | `83da8952…92bc6` before and after (the import wrote no client row) |
| designation | `evt_01M5AZ94J9QCSS3FXC88VSS94B`, from `null` to `ns_01M59N8Q…E74`, 2026-10-19T20:57:34Z |
| bundle directory | unchanged: a sorted `find -printf '%p %s %i %n %T@ %m'` listing of 29,240 entries is byte-equal before, between and after the runs |

## Commands and exit codes

From the worktree, with the lane's `.env` exported (`set -a; . ./.env; set +a`),
`PYTHONPATH=src` and the lock-matched interpreter
`/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python` (linked as the
worktree's ignored `.venv`). `<B>` is the bundle directory above. Records, ignored by Git:
`.local/worktrees/w54-local-import/.local/records/`.

| # | Command | Exit | Time (UTC) |
| --- | --- | --- | --- |
| 1 | `date -u; df -B1 /; free -b; uptime` | 0 | 20:21:04: 20,422,057,984 B free on `/`, 8,273,424,384 B RAM available, load 0.22 |
| 2 | `.env` from `.env.example` by `scripts/lane_prepare.py`'s `example_env()` with the task's six lane resources, after its `_check_other_lanes` and `_check_free_ports` (the script itself targets `.local/worktrees/W54-LOCAL-IMPORT-01`, so it was not run as a whole) | 0 | 20:22 |
| 3 | `make up` | 0 | 20:23, 9 s |
| 4 | `make migrate` (`0001` … `0023_norm_citations`) | 0 | 20:23, 1 s |
| 5 | open the local waiver (below) | 0 | 20:24:09 |
| 6 | `python -m auditmanager.norms.bundle import <B> --copy-record .local/copy/record.json`, detached (`nohup setsid`, pid/rc files) | **0** | 20:24:45-20:51:59 (27 min 14 s) |
| 7 | the same `import` again | **0** | 20:52:42-20:54:31 (109 s) |
| 8 | `python -m auditmanager.norms.bundle report <B> --copy-record .local/copy/record.json` | **0** | 54 s |
| 9 | close the waiver (`state: closed`, `closed_at`), the local stand-in for `resume` | 0 | 20:55:52 |
| 10 | the same `import` under the closed record | **2** `REFUSED [copy_record_closed]` | 18 s |
| 11 | serve the API (below) | running | from 20:56 |
| 12 | `changePassword`, `updateMyProfile` for the seeded administrator, then `setCurrentNormSnapshot` | 200 | 20:57:34 |
| 13 | the probes (below) | — | 20:57-20:58 |

**The waiver.** The test-data waiver is opened with the copy key's `copy-serve.sh attest
--test-data` on a deployed stand. That script needs `compose.server.yml` and the stand's
environment, so here a short script (`.local/records/make-waiver.py`) wrote a record with
exactly that verb's fields: `kind: test_data_waiver`, `state: open`, `purpose: import`,
`writers_present` and `writers_stopped` both empty (no web, API or worker was running), the
migration head read from `alembic_version`, `rejected_blob_count`, a 12 h `waiver.expires_at`,
`real_data_marker: false`, and the `stand-fingerprint-v1` fingerprint computed by
`copy_record.compute_fingerprint`. Its `instance` is `auditmanager-w54-local-import`, and the
script refuses unless the environment names this lane and `127.0.0.1:57490`. The record lives
only in this worktree's ignored `.local/copy/` (open copy kept as
`record.open-20261019T202409Z.json`) and was closed after the import. It never named, read or
reached the stand.

## Import, as measured

Phase times come from the row timestamps (`norm_custody_admission.created_at` and
`confirmed_at`, `norms_snapshot.created_at`, `norm_embedding_build.built_at`). Under redirection
the first run's step lines were block-buffered, so its log has no timestamps; the second run
used `PYTHONUNBUFFERED=1`.

| Phase | Interval | Duration |
| --- | --- | --- |
| verify: every byte, the manifest, the rows, the streamed build digest, the record | 20:24:45-20:25:10 | 25 s (bundle in page cache) |
| admit 28,920 slots, one transaction | 20:25:10-20:25:28 | 18 s |
| dispatch to MinIO, 5.06 GB | 20:25:28-20:39:31 | 14 min 3 s (about 34 objects/s, 6 MB/s) |
| rows, bindings, then the build | 20:39:31-20:51:09 | 11 min 38 s |
| reconciler (28,920 `HEAD`s) and report | 20:51:09-20:51:59 | 50 s |

The idempotent re-run printed `admissions: 0 new, 28920 already held`, `dispatch: 0 tries`,
`rows: already stored …; bindings: 0 new, 28920 already bound`, `build: already stored e7fac64c…`
and `report: full match`.

**Resources.** Sampled every 15-20 s by the supervisor:

- the importer's `VmHWM` reached 828,184 kB (0.79 GiB); the second run's reached 573,512 kB;
- the lowest host RAM available during the import was 7,075,012,608 B, with peaks of 538 MiB
  for the PostgreSQL container and 1.13 GiB for the MinIO container;
- the lane's volumes hold 7.57 GB after the import: `s3-data` 5.074 GB and `postgres-data`
  2.50 GB. Of the latter, `pg_database_size` is 1,418,999,475 B and `pg_wal` is
  1,056,964,608 B. The manifest's `db_growth_bytes` estimate is 1,352,054,572; the measured
  database size also includes the empty migrated schema, which was not measured separately;
- free disk on `/` fell from 20,417,155,072 B (20:23) to 10,718,334,976 B (20:58), 9.70 GB.
  The lane's volumes account for 7.57 GB of that; the rest is not attributable to this lane
  on a shared host;
- the API process holds 140,532 kB RSS once it has served the probes.

## Designation and the served API

The API is `infra/deploy/serve.py` on this stack: `127.0.0.1:57590` (operations) and `57591`
(health), `AUDITMANAGER_PROVIDER_MODE=recorded`, default `EXECUTION_ROLE` and default search
timeout (3,000 ms), and a random signing secret in the ignored `.local/api/api.env`. The
application serves its operations **at the root**. On the stand, the proxy maps the contract's
`/api/v1`, so `POST /api/v1/auth/token` against this port answers `404`.

The seeded `admin` / `password` account signs in, but every norms operation answers `403
permission_denied` until the password is changed (`required_capability: password_changed`) and
then the profile is completed (`profile_completed`, which turns the login into an e-mail
address). Both were done through the API; the login and password are in `.local/api/admin.login`
and `.local/api/admin.secret` (mode 600). The account holds `admin` and `expert`.

| Probe | Status | Latency | Answer |
| --- | --- | --- | --- |
| `listNormSnapshots` before designation | 200 | 16 ms | one snapshot: `build_state complete`, `qualified true`, `current false` |
| `searchNorms` «огнестойкость» before designation | 422 | 7 ms | `required_norm_unavailable`, as §A7 says: nothing is current yet |
| `setCurrentNormSnapshot` `{ns_01M59N8Q…E74, expected_current: null}` | 200 | 13 ms | `designated_by usr_01M5AXB7TPRKFEKPV49RXE24A2`, `designated_at 2026-10-19T20:57:34.026821Z` |
| the same request again | 200 | 8 ms | replay: the same designation, no new history row |
| `listNormSnapshotEvents` | 200 | 4 ms | one event `null → ns_01M59N8Q…E74` |
| `searchNorms` «огнестойкость» | 200 | 34 ms | 50 items, `next_cursor` set; first: Приказ МЧС России № 288 (СП 4.13130), p. 26, `ndoc_01M59N9H4XWGGX6AS4RY6QF3F3` / `npar_01M59N9H50RPD7SJR9VF8FR1W4` «Степень огнестойкости и класс конструктивной пожарной опасности…» |
| `searchNorms` «СП 54.13330» | 200 | 12 ms | 50 items; first: СП 54.13330.2022, p. 1, `ndoc_01M59N9WF2B93HJQ3GYNR5FCWS` / `npar_01M59N9WF3ZDRQCM8YY0WGM3XW`, the document's title paragraph |
| `searchNorms` «эвакуационные выходы» | 200 | 21 ms | 50 items; first: ГОСТ 12.4.026-2015, p. 72, `ndoc_01M59N8RM69NE7VN6MRSF04C8E` / `npar_01M59N8RMAPZFJ126ZX608XBXW` (sign E06, «Направление к эвакуационному выходу…»); third: СП 439.1325800.2018 clause 9.13.9, p. 42 |
| `searchNorms` «ГОСТ 10140» | 200 | 9 ms | 50 items; first: ГОСТ 10140-2003, p. 1 |
| `searchNorms` «СП 54 п. 7.1.4» | 200 | 9 ms | **0 items** (see below) |
| `searchNorms` «СП 54 п. 7.1» | 200 | 10 ms | 1 item: СП 54.13330.2022 clause 7.1, p. 30, `npar_01M59N9WF5XKY0W3W8SXACBHC1` |
| `getNormDocument ndoc_01M59N9H4XWGGX6AS4RY6QF3F3` | 200 | 8 ms | 153 PDF pages, 1,719 paragraphs, 0 unreliable, `content_available true`, `source_attribution consultant_plus` |
| `listNormParagraphs` (limit 50) | 200 | 9 ms | 50 items, `next_cursor` set; ordinals 0, 1, 2 on page 1, `reliable` |
| `streamNormDocumentContent` with `Range: bytes=0-1023` | **206** | 14 ms | 1,024 bytes, `Content-Range: bytes 0-1023/1422741`, `application/pdf`, starts `%PDF-1.7` |
| the same without `Range` | 200 | 14 ms | 1,422,741 bytes, equal to `Content-Length` |
| `searchNorms` without a credential | 401 | — | `authentication_required` |

Probe script: `.local/records/probe.py`; outputs: `probe-before-designation.txt`,
`designate.txt`, `probe-after-designation.txt`, `probe-clause.txt`.

## Findings

1. **«СП 54 п. 7.1.4» finds nothing in this corpus, and that is correct.** The corpus holds
   only the 2022 edition of СП 54.13330. Its clause numbers in section 7 are 7, 7.1 … 7.37,
   with no 7.1.4, and no paragraph text contains `7.1.4`. The designation-plus-clause filter
   works: «СП 54 п. 7.1» returns exactly clause 7.1. The live check that `W55-PLAN.md` §A7
   step 8 names («СП 54 п. 7.1.4» with attribution) will therefore return an empty page on the
   stand. It needs a clause that exists, for example «СП 54 п. 7.1».
2. **The designating administrator needs two steps before any norms operation**: change the
   seeded password, then complete the profile. Until then the account gets `403` with
   `required_capability`. This applies to the stand's designating administrator in §A7 step 7.
3. **Designations are derived from file names**, and some are cut short, for example
   `Приказ МЧС России от 24 04 2013 N 288 (ред`; `title` carries the PDF file name. This is
   the corpus projection's behaviour, outside this task, and is recorded for the norms UI
   slices.
4. **Dispatch dominates the import** (14 of 27 minutes on a local MinIO). On the stand, the
   network and disk path will set that figure; this rehearsal gives no stand estimate.
5. **The importer's step lines are block-buffered when stdout is redirected.** An operator who
   watches a log, or loses the process mid-way, sees nothing until it ends. Running with
   `PYTHONUNBUFFERED=1` avoids it. Whether `receive-bundle.sh` on the stand is affected was not
   checked; this is not treated as a defect here.

## What this does not prove

- Nothing was imported into the stand, reported to it, or copied from it. No production copy
  record exists; the waiver is a local file that mirrors the copy key's shape for a lane that
  holds only freshly migrated data.
- The stand's own path (`receive-bundle.sh`, the inbound and copy keys, `copy-serve.sh`, the
  api image, the import lock, `deploy.sh`'s `stand_import_open` refusal) was not exercised.
- Search quality, ranking and latency under load were not measured; the latencies above are
  single requests on an idle lane.
- No role-less refusal, run pinning or re-audit pinning was tried (§A7 step 8's other checks).
- No full gate was run (`R-135`), and none of the repository's test suites was run, because no
  code changed.

## The stack, left running

| | |
| --- | --- |
| compose project | `auditmanager-w54-local-import` (`make up` / `make down` in the worktree) |
| PostgreSQL | `127.0.0.1:57490`, database `auditmanager_w54_local_import`; credentials in the worktree's `.env` |
| MinIO | API `127.0.0.1:61090`, console `61091`, bucket `auditmanager-w54-local-import` |
| volumes | `auditmanager-w54-local-import-postgres-data`, `auditmanager-w54-local-import-s3-data` |
| API | `http://127.0.0.1:57590` (operations at the root), health `http://127.0.0.1:57591/healthz`; pid in `.local/records/api.pid`; log `.local/api/api.log` |
| restart the API | `nohup setsid .local/records/run-api.sh >/dev/null 2>&1 </dev/null &` |
| stop the API | `kill <pid>`, after checking that `/proc/<pid>/cmdline` is `…/.venv/bin/python infra/deploy/serve.py` |
| sign in | `POST /auth/token` with `.local/api/admin.login` / `.local/api/admin.secret` |
| web (Next.js) | not started: the lane's `.env` has no web key and the task asks for API probes only |

A new import into this database needs a new waiver: `make-waiver.py` refuses while
`.local/copy/record.json` exists, so move the closed record aside first. The waiver's
fingerprint now differs from the closed record's, because signing in and the profile change
wrote client rows.

**Rollback** (from the task): stop the API by its pid, `make down`, then remove only the two
volumes above.

## Integrator instruction

Merge this report; no code, contract, migration or dependency file changed. The stack stays up
as this window's local norms development stand. Free disk was 10.7 GB at the end, above the
task's 4 GiB stop line; if it falls below that, stop the API and run `make down`. Finding 1
belongs with whoever writes the stand-import checks of `W55-PLAN.md` §A7. Nothing here asks for
`origin/main`.
