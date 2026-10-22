# STAND-NORMS-IMPORT-RUNBOOK-01 — importing the verified norms bundle into the deployed stand

**Date:** 2026-10-21. **Base:** `origin/dev` `06591a52`. Operator runbook for an owner window; it serves beta
criterion B2 (corpus snapshot loaded, every PDF and crop in S3 with a confirmed binding, embedding build
complete, search answers with citations). **Nothing here has run on the stand**: each command was read from the
tree, and what could not be read is marked UNVERIFIED (section 9). **Authority:** a direct owner instruction
naming the bundle's content key and digest (`W55-PLAN.md` §A7). **Premise:** the stand holds only generated test
data (`R-109`, `R-140`; `R-141c`: the first beta is closed, on test data, with no real client document), so the
test-data waiver of `R-110` stands in for the one-off copy (no dump, no `restore-db`). If a real client document was
uploaded anyway, stop and use `DEPLOYMENT_RUNBOOK.md` §13 "with real client data".

| Bundle (read-only, development host) | |
| --- | --- |
| directory `B` (its name is `KEY`) | `/root/projects/PDF-Analysis/.local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245` |
| digests | `SHA256SUMS` `7792e307…5245` (re-read 2026-10-21, equals the name's tail); `manifest.json` `cc0f5ee8…21cf` |
| content | snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`: 674 documents, 350,194 paragraphs (0 unreliable), 55,855 chunks, 61,573 windows (build `e7fac64c…c5df`), 28,920 objects (5,055,102,708 bytes) |
| size | `du -sb` 5,641,048,705 bytes in 28,979 files; the tar is a few tens of MB more (exact count: step 1.2) |
| schema | needs the database at the image's head and at least `0018_norm_custody`; the tree's head is `0029_routing_refusal_codes` (`tests/support/expected_facts.json` `migration_head`; this runbook first named `0027`, the head of the cancelled `59a1be91` publication) |

## Do NOT

- Import before the 0.7.0 deployment is verified (section 0). The rehearsal ran the 0.7.0 line at head `0023`; v0.6.0's image
  at `0021` was never tried, and 0.7.0's forward migrations would then run over imported custody rows. The importer also
  refuses a database not at head (`database_not_at_head`).
- Run `attest --test-data` where real client data may exist, or start `web`/`api`/`worker` by hand between the attest and
  `resume` (`writers-still-stopped` voids the waiver).
- Push to `origin/main` or run `deploy.sh` from the attest to `resume`: it refuses (`stand_import_open`); an open record
  blocks every later deploy.
- Run `reset.sh` or `down --volumes` after the import: they drop the schema and purge the bucket, corpus included. A wipe
  comes before the deploy and import (`R-141b`, `RELEASE-0-7-0-DEPLOY-STEPS-01.md`).
- Delete `B` (the corpus's recovery copy), hand-edit `record.json`, or kill anything by pattern (stop the importer
  container by its confirmed name).
- Use «СП 54 п. 7.1.4» as the check: the corpus holds only the 2022 edition (clauses 7, 7.1 … 7.37), so 0 items is
  correct. Use «СП 54 п. 7.1» (`W54-LOCAL-IMPORT-01` finding 1).

## Conventions

`STAND` is `user@host`. The owner installs the two forced-command keys (`DEPLOYMENT_RUNBOOK.md` §11 steps 1-3, §13 steps
1-4); `R-110` deferred the copy key, so check it in 0.3. A refusal exits 3 as `REFUSED [<guard>]` (guard tables: §11, §13).

```
# From the development host (each key's `from=` must name it):
inbound() { ssh -i "$IN_KEY" -o IdentitiesOnly=yes "$STAND" "$@"; }   # receive-bundle.sh
copy()    { ssh -i "$CP_KEY" -o IdentitiesOnly=yes "$STAND" "$@"; }   # copy-serve.sh
# Or on the stand host as the key account (the scripts read only SSH_ORIGINAL_COMMAND; UNVERIFIED that way):
inbound() { SSH_ORIGINAL_COMMAND="$*" BUNDLE_STAGING=/srv/auditmanager-bundles /srv/auditmanager/infra/deploy/receive-bundle.sh; }
copy()    { SSH_ORIGINAL_COMMAND="$*" ALPHA_CHECKOUT=/srv/auditmanager STAND_COPY_DIR=/srv/auditmanager-copy /srv/auditmanager/copy-serve/copy-serve.sh; }
API=https://audit.135.106.164.147.sslip.io/api/v1   # the alpha address in MAIN_AUTODEPLOY_POLICY.md; confirm it
```

## 0. Preconditions (read-only; stop on any miss)

1. **The release the owner designated is deployed after the wipe** (`R-141b`; `R-141e` cancelled the `59a1be91` publication, and the owner's own pull
   requests moved `origin/main` instead: `44962e8d` at head 0029, then `a5b83f64` on 2026-10-22; take the SHA from the owner's message, not from this
   line). In `/srv/auditmanager`: `infra/deploy/verify-deployed.sh` exits 0, `git rev-parse HEAD` is that SHA, and `docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml exec -T postgres
   psql -U <POSTGRES_USER> -d <POSTGRES_DB> -tAc 'select version_num from alembic_version'` prints the tree's head, `0029_routing_refusal_codes` at the time of writing (read it from `tests/support/expected_facts.json` `migration_head`).
2. No publication in flight or planned in the window; no run executing (pause «Очередь» and wait: the worker drains for up to 300 s).
3. **Keys answer and run the published scripts.** `inbound status`: `import_lock: free`, no `bundle: $KEY`. `copy status`:
   `record: none` (or `state: closed`), `real_data_marker: absent`, `import_lock: free`, `deployed_tree` = release SHA. Each
   `script:`/`lib:` hash equals `git show <release sha>:infra/deploy/<file> | sha256sum`.
4. **Capacity.** `copy capacity` prints, and does not refuse. Needed (`W55-PLAN.md` §C6, no dump): staging 2 x 5.66 GB + 2 GiB
   during `receive` (the script refuses below it), 5.7 GB after; Docker root +5.06 GB objects, +2.5 GB PostgreSQL with WAL
   (rehearsal), +2 GiB, each +25 %: about 12 GB there and 10 GB for staging, about 22 GB if one filesystem. RAM available
   >= 2 GiB (importer peak 0.79 GiB + 1 GiB), swap excluded.
5. The owner names the **designating administrator** and has its password. After the wipe only the seeded `admin` exists: it
   must `changePassword` and `updateMyProfile` first, or every norms call is `403 permission_denied` (rehearsal finding 2).
6. `B` here: `sha256sum "$B/SHA256SUMS"` equals the name's tail; optionally `PYTHONPATH=src python -m auditmanager.norms.bundle
   verify "$B"` (exit 0, `verified: … (28979 files, every byte re-hashed)`, 8 s warm).

## 1. Transfer (the stand keeps running)

1. `inbound status` and `copy status` again.
2. `infra/deploy/push-bundle.sh --dry-run "$B"` (release tree): re-hashes and prints `would send <N> bytes as: receive <KEY> <N>`;
   `N` must be under 12 GiB.
3. `infra/deploy/push-bundle.sh --host "$STAND" --identity "$IN_KEY" [--known-hosts <file>] "$B"` (reads `B` three times, writes
   no copy). The stand refuses before reading a byte on size, free space, a running receive or copy verb, or an existing
   bundle; then lists the tar, extracts into `incoming/`, requires `SHA256SUMS` to digest to the name, the files to be exactly
   the listed ones and every file to re-hash, and only then moves it to `bundles/$KEY`. Success: `the stand kept <KEY>`.
4. `inbound status` shows `bundle: $KEY bytes: ~5.64e9 import: not imported`. Independent check on the stand host: `cd
   /srv/auditmanager-bundles/bundles/$KEY && sha256sum --quiet -c SHA256SUMS && sha256sum SHA256SUMS manifest.json`.
5. Without the key path (UNVERIFIED): stream the same tar (`bundle_tar` in `push-bundle.sh`) into the local `inbound receive $KEY <N>`.
   Do not write the tar to disk here: this host had 4.8 GB free on 2026-10-21.

## 2. Quiesce and import (downtime starts)

1. Announce the stand-down; `copy capacity` once more.
2. `copy attest --test-data`: stops exactly the running writers, takes the `stand-fingerprint-v1` fingerprint, opens a
   `test_data_waiver` valid 12 h. Output: `stamp:`, `writers_stopped: web api worker`, `fingerprint_sha256:`, `expires_at:`.
   Keep `STAMP`. This record is the "copy record" the importer takes read-only and re-checks.
3. `inbound import $KEY` returns at once (`import of <KEY> started (detached, pid <n>)`); a one-shot `api` container works
   under the import lock. Poll `inbound status` every 5 min: its last 5 log lines are live (the api image sets
   `PYTHONUNBUFFERED=1`) and end in `import: exited <n>`. Plan the window to end within 10 h of the attest (12 h minus 2 h).
4. Expected log (rehearsal): `bundle: <content key> verified (28978 files)`; `copy record: test_data_waiver <STAMP> admits the
   import until …; fingerprint … unchanged`; `admissions: 28920 new, 0 already held`; `dispatch: 28920 tries`; `admissions:
   confirmed 28920, pending 0, poisoned 0, rejected 0`; `rows: inserted ns_01M59N8QNBVN91ACA2HCE6VE74; bindings: 28920 new`;
   `build: loaded e7fac64c…`; the report block; `report: full match`.
5. Exit 0 go on; 1 imported but the report differs; 2 `bundle: REFUSED [<reason>]`; 75 unfinished (pending or poisoned
   admission). Meanings: `DEPLOYMENT_RUNBOOK.md` §11 "The importer". Re-running `import` is safe.

## 3. Report (still quiesced) and 4. Resume

`inbound report $KEY` is synchronous: it prints the comparison, `HEAD`-checks every object in MinIO and compares each client
table with the open record. It must exit 0 (`report: full match`, `custody_incidents: 0`). After a matched report that follows
a successful import the verb deletes `bundles/$KEY/objects/` (about 5 GB; manifest, rows, build and `logs/$KEY.report` stay).
It needs the record open, so it comes **before** `copy resume $STAMP`, which starts `web api worker`, checks each runs and
closes the record (`resumed: <STAMP>`). Then `infra/deploy/verify-deployed.sh` (0), `infra/deploy/reload-proxy.sh` if the proxy
answers 502 (`D-27`), `copy status` shows `state: closed`, `inbound status` `import_lock: free`; un-pause «Очередь».

## 5. Designation of the current snapshot (the administrator)

Until now nothing is current: `searchNorms` is `422 required_norm_unavailable` and new runs pin NULL. In the UI: «Нормы» ->
«Снимки нормативной базы» (administrator only) -> «Сделать текущим» on the `qualified` snapshot. Or by API
(`setCurrentNormSnapshot`, `PUT /norms/snapshots/current`, role `admin`):

```
read -rs PW; TOKEN=$(curl -fsS -X POST "$API/auth/token" -H 'Content-Type: application/json' \
  -d "$(jq -n --arg l "$LOGIN" --arg p "$PW" '{login:$l,password:$p}')" | jq -r .token); H=(-H "Authorization: Bearer $TOKEN")
curl -fsS "${H[@]}" "$API/norms/snapshots" | jq .items      # expect build_state complete, qualified true, current false
curl -fsS "${H[@]}" -X PUT "$API/norms/snapshots/current" -H 'Content-Type: application/json' \
  -d '{"norms_snapshot_id":"ns_01M59N8QNBVN91ACA2HCE6VE74","expected_current":null}'
curl -fsS "${H[@]}" "$API/norms/snapshots/events" | jq .items   # one event, from_norms_snapshot_id null
```

Expected `200 {"norms_snapshot_id":"ns_01M59N8Q…","designated_at":"…Z","designated_by":"usr_…"}`; repeating it is a `200` replay
with no new event. `409` `stale_current_snapshot`: someone designated first, re-read, never force. `422 required_norm_unavailable`
(`reference_kind` `norm_embedding_build` or `norm_source`): the import is not whole, go to section 8. `403` with
`required_capability`: finish the account. There is no unset; a wrong snapshot is replaced only by another qualifying one.

## 6. Verification probes (the B2 record: statuses and times)

Ids travel in the bundle, so they must match the rehearsal verbatim (ranking is expected, not guaranteed). Search:
`curl -fsS "${H[@]}" -G "$API/norms/search" --data-urlencode 'q=<query>' --data-urlencode limit=50`.

| Probe | Expected (rehearsal: local, idle) |
| --- | --- |
| `listNormSnapshots` | 1 item, 674 / 350,194 / 0 unreliable, `complete`, `qualified true`, `current true` |
| `listNormDocuments?limit=1` | 200, `total` 674 (UNVERIFIED: not rehearsed, contract shape only) |
| «огнестойкость» | 200, 50 items, `next_cursor` set; first `ndoc_01M59N9H4XWGGX6AS4RY6QF3F3` / `npar_01M59N9H50RPD7SJR9VF8FR1W4`, `page_label` 26 (МЧС № 288), 34 ms |
| «СП 54.13330», «ГОСТ 10140», «эвакуационные выходы» | 200, 50 items; first: СП 54.13330.2022 p. 1 (`ndoc_01M59N9WF2B93HJQ3GYNR5FCWS`); ГОСТ 10140-2003 p. 1; ГОСТ 12.4.026-2015 p. 72 |
| «СП 54 п. 7.1» / «СП 54 п. 7.1.4» | 1 item (clause 7.1, `page_label` 30, `npar_01M59N9WF5XKY0W3W8SXACBHC1`) / **0 items**, both 200 |
| `getNormDocument ndoc_01M59N9H4XWGGX6AS4RY6QF3F3` | 153 pages, 1,719 paragraphs, 0 unreliable, `content_available true`, `consultant_plus` |
| `listNormParagraphs` (`limit=50`) | 50 items, `next_cursor` set; ordinals 0, 1, 2 on page 1, `reliable` |
| `…/norm-documents/<id>/content` with `Range: bytes=0-1023` | **206**, 1,024 bytes, `Content-Range: bytes 0-1023/1422741`, `application/pdf`, starts `%PDF-1.7` |
| the same without `Range`; any norms call without a token | 200, 1,422,741 bytes = `Content-Length`; 401 `authentication_required` |
| `copy verify-objects 100` | `verified 100 mismatched 0` (random `available` Blobs read back through the api image) |

A hit is the citation: `{norms_snapshot_id, norm_document_id, norm_paragraph_id, designation, title, doc_type, clause_number (null
or "7.1"), page_label (true 1-based PDF page), block_ref, fragment:{text, highlights:[{char_start, char_end}]}, source_attribution:
"consultant_plus"|"unattributed"}`; «открыть» is `…/content` at `#page=<page_label>`. `designation` comes from the file name and is
sometimes cut («…N 288 (ред», finding 3). Repeat the ranged read through the public proxy (UNVERIFIED there) and open «Нормы» in the browser.
Optional (§A7 step 8, not rehearsed): a role-less account gets 403; an expert's new run reports the designated `norms_snapshot_id`.

## 7. Timings (`W54-LOCAL-IMPORT-01`: local MinIO, bundle in page cache)

verify 25 s; admit 28,920 slots 18 s; dispatch of 5.06 GB 14 min 3 s (34 objects/s, 6 MB/s); rows, bindings, build 11 min 38 s;
reconciler and report 50 s: **`import` 27 min 14 s**, second `import` (no-op) 109 s, `report` 54 s, import under a closed record
refused in 18 s, designation and probes about 2 min. Peaks: importer 0.79 GiB, PostgreSQL 538 MiB, MinIO 1.13 GiB; volumes +7.57 GB
(s3 5.074, postgres 2.50 of which WAL 1.06). Stand-down estimate about 35-40 min on an equally fast disk (dispatch scales with it,
finding 4); not measured: the transfer (5.66 GB at 10 MB/s is 10 min, at 1 MB/s over 90), the stand's own import, the stand-side check.

## 8. Failure modes and safe stop

Until section 5 the import is inert (search refuses, runs pin NULL, client tables unchanged by construction), so the safe stop is
`copy resume $STAMP` once no importer runs. The waiver has no dump, so `restore-db` is refused; the only undo of the corpus is the
owner's `reset.sh` (dump first, then wipe) and a fresh import from `B`.

| Step | Symptom | State left | Do |
| --- | --- | --- | --- |
| 1 | `size-within-limit`, `staging-has-room`, `bundle-not-received`, `receive-lock-free`, `copy-lock-free`, `tar-*`, `sums-*`, `files-match-sums` | nothing kept, `incoming/<KEY>/` removed | free space, wait, resend; a dropped link leaves `incoming: <KEY>` in `status`, a new `receive` clears it |
| 2.2 | `real-data-absent`, `record-closed`, `import-lock-free`, `writers-stopped`, `docker-answers`, `fingerprint-read` | writers possibly stopped, record open | `copy resume $STAMP` (stamp from `copy status`) |
| 2.3 | `copy-record-*`, `waiver-before-real-data`, `writers-still-stopped`, `import-lock-free` | nothing started | `resume`, then a new `attest --test-data`; a waiver older than 12 h is dead |
| import 2 | `copy_record_*`, `fingerprint_drifted`: new waiver. `bundle_*`, `manifest_invalid`, `build_absent`: send `B` again. `database_not_at_head`/`_below_minimum`: deploy not done, stop. `manifest_blob_rejected`, `manifest_blob_held_outside_custody`, `snapshot_conflict`: owner decision | nothing written by the refused step | `resume` if the owner abandons the window |
| import 75 | pending (store outage) or poisoned admissions | objects partly in MinIO, no rows, bundle kept | `inbound requeue $KEY` if poisoned, then `import` again |
| import 1 or `report` not 0 | counts or client tables differ | rows may be stored, not designated | do not designate; keep `logs/$KEY.import.log` and `.report`; the owner decides before `resume` |
| import killed, host restarted | `status`: `running or ended without an exit status` | lock may be free while the container runs | `docker ps`, stop the one-shot container by confirmed name (a hung lock is an owner act), re-run `import` |
| 4 | `writers-resumed` | record stays open | read the writer's log, `resume` again |
| 5 / 6 | 403, 409, 422 (section 5); 502, 503, `422 validation_failed` `norms_search_too_broad` (3,000 ms default) | nothing designated / none | `reload-proxy.sh`; retry a minute later (fresh tables may await autoanalyze, UNVERIFIED); ten broad searches can starve the API pool (`D-158`) |

## 9. UNVERIFIED

- That either key is installed, the account, `/srv/...` paths, `from=` addresses, the route from the development host, GNU tar >= 1.28,
  `flock`/`setsid`, and `docker compose ps --quiet` on a restarting container (`W54-TRANSPORT-01` §4, `W54-STAND-COPY-01` §5). No
  document records `receive`, `import`, `report` or `attest --test-data` on a deployed or disposable stand; the tests stub `docker` and
  `ssh`. Treat sections 1-4 as first runs.
- The bundle at the current head (first written for `0027`; rehearsal `0023_norm_citations`); `mc ls --json` fields behind `capacity`'s bucket figures (non-blocking);
  ranged PDF and search through nginx; `listNormDocuments`; the stand's import time.

## 10. Open questions for the owner

1. Transfer: may the integrator push from the development host through the inbound key (key pair, host key, `from=`), or will the owner
   move the bytes another way? Is the copy key installed?
2. Window: date and length. Proposal: 2 h of stand-down (about 40 min expected), transfer done beforehand.
3. Order and clock: wipe, the owner's push of the designated release (`R-141e` cancelled `59a1be91`), `verify-deployed.sh`, then this window the same day or the next?
4. Who designates: the owner as the seeded `admin`, or an account the owner registers and approves first?
