# W54-STAND-COPY-01 — the copy key, the test-data waiver, the real-data marker and the deploy.sh refusals

**Executor:** lane `agent/w54-stand-copy-01`, worktree `.local/worktrees/w54-stand-copy`.
**Base:** `80a157f` (`integration/w54`; TRANSPORT and WORKER merged, BUNDLE not yet). **Date:** 2026-10-12.
**Task:** `docs/program/tasks/W54-STAND-COPY-01.md`; grant `W54-PLAN.md` §4 Stage C; `W54-FREEZE-01`
amendments 1 and 2 (`R-109`, `R-110`); `R-88`, `R-92`, `R-93`, `R-104`.
**Checks:** `R-102` light acceptance, container-free (`docker` and `ssh` stubbed on `PATH`). No heavy
step was run. The one case that needs a real PostgreSQL is written, gated, and listed in §6.

## 0. What was built, against the required items

| Required (plan §4 Stage C, task file, amendment 2) | Where, and the case that proves it |
|---|---|
| copy verbs `capacity`, `dump-db`, `inventory-s3`, `fetch`, `attest`, `verify-objects`, `restore-db`, `resume`, `status` | `infra/deploy/copy-serve.sh`, registered through TRANSPORT's `fc_register`; grammar cases for every verb (`test_every_verb_has_grammar_violation_cases`) |
| a refusal per guard and verb | 60 marked guards in the four new scripts, each with a case that trips it and a mutant that deletes it (`test_each_guard_refuses_and_its_deletion_stops_the_refusal`, 60 cases; `test_every_guard_has_a_case_here`) |
| `attest --test-data` writes a `test_data_waiver` record | `attest_test_data`; `test_the_test_data_waiver_is_a_quiesced_import_record_without_a_copy` |
| a full copy writes the `real_data` marker; waivers are refused afterwards | `verb_attest`, guard `real-data-absent`; stand side `waiver-before-real-data` in `receive-bundle.sh`; `test_a_full_copy_writes_the_marker_and_every_waiver_is_refused_after_it` |
| `dump-db` stops exactly the writers present, the W54 `worker` included | `find_running_writers` (declared in the deployed compose file **and** running); `test_dump_db_stops_exactly_the_writers_present` (4 shapes, including the W53 rollback file without `worker`) |
| `resume` refused under `<staging>/import.lock` | guard `import-lock-free`; `test_resume_is_refused_under_the_import_lock_and_the_writers_stay_stopped` |
| `restore-db` re-quiesces and checks the digest | guards `dump-digest-matches-restore`, `writers-stopped`, `fingerprint-restored`; `test_restore_db_quiesces_again_checks_the_digest_and_leaves_the_writers_stopped` |
| `attest` binds both digests | `test_the_whole_copy_binds_both_digests_and_deploy_follows_the_record` |
| a dump restored here reproduces the fingerprint | `scripts/stand-copy/restore-test.sh` (stubbed path in the whole-copy test); the real PostgreSQL case `test_a_dump_restored_here_reproduces_the_fingerprint` is a heavy step (§6) |
| `verify-objects` detects a corrupted object | the read-back program run against a fake storage package: `test_the_read_back_program_detects_a_corrupted_object` (sha mismatch, size mismatch, unreadable, empty sample); guard `objects-match` |
| every `capacity` field | `test_capacity_prints_every_field` |
| the extracted script acts on `ALPHA_CHECKOUT` | every case installs the script apart from the checkout; `test_the_extracted_script_acts_on_alpha_checkout` |
| `deploy.sh` refuses with a typed word before any `docker` call, and accepts exactly the bound SHA | five marked guards; `TestNoDeployWhileACopyOrAnImportIsOpen` in `test_deploy_script_refusals.py`; end to end against records the real `copy-serve.sh` wrote: `test_the_whole_copy_…`, `test_an_import_record_and_a_waiver_both_stop_deploy` |
| `receive-bundle.sh` record pre-check | six new marked guards and the conversion to an import record; cases in `test_bundle_transport_refusals.py` |
| `shellcheck` | clean on every new and changed script (§2) |

The task file names the deploy words `stand_copy_open` / `stand_import_locked`. The plan (§4 Stage C)
splits "a copy is open" into three words, and those are what is implemented: `stand_import_open`,
`stand_copy_unattested`, `stand_copy_other_target`, plus `stand_import_locked` and one more,
`stand_copy_unreadable`, for a record nobody can read (§3.6).

## 1. Changed files

`git diff --name-only 80a157f..HEAD`, 13 paths:

| Path | What |
|---|---|
| `infra/deploy/copy-serve.sh` (new, 0755) | the copy key's forced command (36 guards) |
| `infra/deploy/capacity-probe.sh` (new, 0755) | free disk per filesystem, RAM, swap, load; refuses below a stated need (4 guards) |
| `infra/deploy/pull-copy.sh` (new, 0755) | this host: fetch a copy and check every file against its record (9 guards) |
| `scripts/stand-copy/restore-test.sh` (new, 0755) | this host: restore into a disposable PostgreSQL, reproduce the fingerprint, write the report `attest` binds (11 guards) |
| `infra/deploy/lib/forced-command.sh` | the copy record's canonical layout: `fc_record_value/_string/_valid/_set`, `fc_json_member/_words`, `fc_lock_held`, `fc_now`, `fc_epoch`, `fc_fingerprint_lines_valid/_json`, `FC_STAMP_ERE`. No dispatcher change |
| `infra/deploy/receive-bundle.sh` | the record pre-check before `import`, the readable-record check before `receive` reads a byte and before `report`, and the conversion to an import record (16 → 22 guards). `requeue` was already present (TRANSPORT) and is unchanged |
| `infra/deploy/deploy.sh` | five guards right after `known-options` (15 → 20) |
| `tests/integration/composition/test_stand_copy_refusals.py` (new) | 141 cases (§2) |
| `tests/integration/composition/test_bundle_transport_refusals.py` | a valid open waiver as the default staged record; the `ps` answer in the docker stub; 6 guard cases and 7 behaviour cases (105 → 118) |
| `tests/integration/composition/test_deploy_script_refusals.py` | every case reads its own record and lock path, not the host's `/srv`; marker count 20; 14 cases (59 → 73) |
| `infra/deploy/README.md` | file-table rows only |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | §11's refusal table and "does not do"; new §13 (install and P2 bootstrap, verbs, the order with and without real data, `deploy.sh` words, refusals, the heavy-step floor) |
| `docs/program/W54-STAND-COPY-01.md` (new) | this report |

## 2. Checks run and their results

Commands run in the worktree on `7f3da61` (the implementation commit; `git status --porcelain -uall`
empty). This report's commit adds only this file.

| Command | Result |
|---|---|
| `git diff --check 80a157f..HEAD` | clean |
| `bash -n` on the 8 scripts (4 new, `receive-bundle.sh`, `push-bundle.sh`, `deploy.sh`, the lib) | OK ×8 |
| `shellcheck -x infra/deploy/{copy-serve,capacity-probe,pull-copy,receive-bundle,push-bundle}.sh infra/deploy/lib/forced-command.sh scripts/stand-copy/restore-test.sh` (ShellCheck 0.9.0) | no findings |
| `shellcheck -x infra/deploy/deploy.sh` | 1 finding (SC2016, info), identical to base `80a157f`; none new |
| `.venv/bin/python -m pytest -q -rs tests/integration/composition/test_stand_copy_refusals.py tests/integration/composition/test_bundle_transport_refusals.py tests/integration/composition/test_deploy_script_refusals.py` (2026-10-12 11:24–11:30 UTC) | **331 passed, 1 skipped** in 338.9 s: 140 + 1 skipped (the heavy step), 118, 73 |
| `.venv/bin/python -m pytest -q -rs tests/integration/composition/{test_deploy_image_identity,test_deployed_stack_probe,test_reset_script_refusals,test_session_register_volume,test_proxy_config_follows_checkout,test_every_port_implementation_is_whole,test_minio_image_contract,test_pgvector_image_contract,test_proxy_tls_path}.py tests/integration/workers/test_worker_composition.py tests/contract/test_deploy_auto_workflow.py tests/contract/api_v1/test_surface_counts_in_prose.py` (they stage `deploy.sh` alone, so they show the new guards are inert with no record) | 233 passed, 1 skipped (the opt-in proxy stand) |
| `.venv/bin/python -m pytest -q tests/integration/releases/test_deployment_flow.py` | 2 passed |
| `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | 558 passed, 50 subtests (as at WORKER's hand-back) |

**Shown able to fail.** Every guard in the four new scripts, the six new ones in `receive-bundle.sh`
and the five in `deploy.sh` is run against a copy with exactly that block deleted, and the
refusal disappears (60 + 6 + 5 mutant cases). Every mutant of every guarded script was also
checked to still parse (`bash -n`), so no mutant "passes" by a syntax error. That check found
that TRANSPORT's `copy-record-present` mutant left an empty function, a syntax error. A one-line
`local` keeps it parsing now, so that existing case tests its guard again. The behaviour
cases (conversion to an import record, writer selection, digest binding, marker, read-back) fail
without the code they name. Their names say what each asserts.

## 3. Contracts (new; no API, domain, event or migration contract changed)

### 3.1 The copy key's grammar (`copy-serve.sh`, anchored EREs; `<STAMP>` = `[0-9]{8}T[0-9]{6}Z`)

```
^capacity$
^dump-db$
^inventory-s3 <STAMP>$
^fetch <STAMP> (db|inventory|record)$
^attest (<STAMP> [0-9a-f]{64} [0-9a-f]{64} (publish [0-9a-f]{40}|import)|--test-data)$
^verify-objects [1-9][0-9]{0,3}( [0-9a-z]{1,32})?$          # optional seed
^restore-db <STAMP> [0-9a-f]{64}$
^resume <STAMP>$
^status$
```

Configuration comes only from the `command=` string: `ALPHA_CHECKOUT` (default `/srv/auditmanager`),
`ALPHA_ENV_FILE`, `STAND_COPY_DIR` (default `/srv/auditmanager-copy`), `BUNDLE_STAGING` (its
`import.lock`), `STAND_COPY_MARGIN_BYTES` (2 GiB), `STAND_COPY_WINDOW_SECONDS` (43200). Exit 3 is
a refusal and prints `copy-serve.sh: REFUSED [<guard>]`.

### 3.2 The copy record — `<STAND_COPY_DIR>/record.json`, `record_version 1`

**Layout.** JSON in one canonical layout: `{` on its own line, then one top-level key per line,
indented exactly two spaces, with its whole value on that line (objects and arrays included),
then `}`. No string contains `"` or `\`. `lib/forced-command.sh` reads and rewrites it line by
line (`fc_record_valid` defines it), because the stand promises no `jq` or `python3`. **The
importer reads it as ordinary JSON and must never rewrite it.** It is mounted read-only.

| Key | Type | Written by / when |
|---|---|---|
| `record_version` | `1` | open |
| `kind` | `"copy"` \| `"test_data_waiver"` | open |
| `stamp` | `"YYYYMMDDTHHMMSSZ"` | open; also the name of `<STAND_COPY_DIR>/<stamp>/` for a copy |
| `state` | `"open"` \| `"closed"` | open → `resume` closes; `restore-db` reopens |
| `purpose` | `"none"` \| `"publish"` \| `"import"` | open (`none` for a copy, `import` for a waiver); `attest`; set to `import` by the inbound key's `receive` or `import` while open |
| `target_sha` | 40-hex string \| `null` | `attest … publish <sha>`; `null` for an import |
| `instance` | string | open (`ALPHA_INSTANCE`) |
| `deployed_tree` | 40-hex | open (`git -C $ALPHA_CHECKOUT rev-parse HEAD`) |
| `migration_head` | string \| `null` | after quiesce (`alembic_version`, comma-joined) |
| `opened_at` | UTC `YYYY-MM-DDTHH:MM:SSZ` | open (before anything is stopped) |
| `quiesced_at` | UTC time \| `null` | after the writers are proven stopped |
| `writers_present` | array of `web`/`api`/`worker` | open: declared in the deployed compose file **and** running |
| `writers_stopped` | same | open; `restore-db` adds any writer it had to stop again |
| `dump` | `{"file": "db.dump", "size_bytes": N, "sha256": "…"}` \| `null` | `dump-db`, after `pg_restore --list` reads it; always `null` for a waiver |
| `fingerprint` | `{"algorithm": "stand-fingerprint-v1", "sha256": "…", "tables": {"<table>": {"rows": N, "sha256": "…"}, …}}` \| `null` | after quiesce (§3.5) |
| `rejected_blob_count` | integer \| `null` | after quiesce (`blob.state = 'rejected'`) |
| `inventory` | `{"file": "inventory.tsv", "count": N, "bytes": N, "sha256": "…"}` \| `null` | `inventory-s3`; always `null` for a waiver |
| `attestation` | `{"dump_sha256": "…", "restore_report_sha256": "…", "attested_at": "…"}` \| `null` | `attest` (a copy only); re-attesting a publication rewrites it |
| `waiver` | `{"statement": "…", "attested_at": "…", "expires_at": "…"}` \| `null` | `attest --test-data` (a waiver only) |
| `real_data_marker` | `true` \| `false` | open (whether the marker file existed); `true` after a full copy's attestation |
| `restored_at` | UTC time \| `null` | `restore-db` |
| `closed_at` | UTC time \| `null` | `resume`; reset to `null` by `restore-db` |

`inventory.tsv` is one line per object, `<key>\t<size>\t<etag>`, sorted by key in byte order. The
inventory's `sha256` is that file's SHA-256. Only the latest copy is kept: a successful `dump-db`
removes older `<stamp>/` directories.

### 3.3 The `test_data_waiver` (`W54-FREEZE-01` amendment 2)

`attest --test-data` is refused while any record is open, while the importer holds its lock, and
once the marker exists. Otherwise it stops the writers present exactly as `dump-db` does, takes
the fingerprint, and writes a record with `kind "test_data_waiver"`, `state "open"`,
`purpose "import"`, `dump`/`inventory`/`attestation` `null`, `real_data_marker false`, and
`waiver {statement, attested_at, expires_at}`. The statement is the fixed text "The stand holds
only generated test data (R-109); no copy is taken (R-110)."; `expires_at = attested_at +
STAND_COPY_WINDOW_SECONDS` (12 h). `resume <STAMP>` closes it like a copy. `fetch` and `attest`
refuse it (`artifact-present`, `record-has-dump`).

### 3.4 The `real_data` marker

The file `<STAND_COPY_DIR>/real_data` is written by the **first attestation of a full copy**
(`attest <STAMP> … publish|import`), with the content `stamp=<STAMP>\nwritten_at=<UTC>\n`. The
record gets `real_data_marker: true`. Nothing in the scripts removes it. Removing it is an owner
act, for example at the beta purge (`D-156`). From then on `attest --test-data` refuses
(`real-data-absent`), and the inbound key refuses an import under any waiver
(`waiver-before-real-data`, checked against both the file beside the record and the record's
field).

### 3.5 The fingerprint, `stand-fingerprint-v1`

One SQL text, kept once, in `copy-serve.sh` between `-- >>> stand-fingerprint-v1` and
`-- <<< stand-fingerprint-v1`. `restore-test.sh` extracts it from there, and no second copy exists
(`test_the_fingerprint_query_has_one_source`). In one `REPEATABLE READ READ ONLY` transaction,
with `TimeZone=UTC`, `DateStyle=ISO, YMD`, `IntervalStyle=postgres`, `extra_float_digits=1`,
`bytea_output=hex`, it covers every non-partition base table of `current_schema()` whose name
does not start with `norm` (so the `norm*` and `norm_custody_*` families are excluded). For each,
in byte order of the name, it prints `<table>|<count>|<sha256>`, where the digest is
`sha256(string_agg(row::text, E'\n' ORDER BY row::text COLLATE "C"))` over:

* `audit_event`: rows whose `event_type NOT LIKE 'norm\_custody.%'`;
* `command_record`: rows whose `command_type NOT LIKE 'norm\_custody.%'`;
* `blob`: rows no `norm_custody_admission.blob_id` names (no filter if that table does not exist,
  as on a pre-`0018` stand);
* every other table: every row.

The record's `fingerprint.sha256` is the SHA-256 of those lines, each ending in `\n`
(`fc_fingerprint_json`).

### 3.6 What `deploy.sh` refuses (exit 3, before any `docker` call, right after `known-options`)

It reads `STAND_COPY_RECORD` (default `/srv/auditmanager-copy/record.json`) and
`BUNDLE_STAGING/import.lock` (default `/srv/auditmanager-bundles`). deploy-auto passes no
environment, so on the stand the defaults are what is read.

| Guard | Word (in `deploy.sh: REFUSED: [<word>] …`) | When |
|---|---|---|
| `stand-import-locked` | `stand_import_locked` | `flock --nonblock <lock> true` fails |
| `stand-copy-readable` | `stand_copy_unreadable` | a record exists without a readable `record_version 1`, `state`, `kind`, `purpose`, `attestation`, `target_sha` |
| `stand-import-open` | `stand_import_open` | open, and `purpose` is `import` or `kind` is `test_data_waiver` |
| `stand-copy-unattested` | `stand_copy_unattested` | open, and `attestation` is `null` |
| `stand-copy-other-target` | `stand_copy_other_target` | open, and `purpose` is not `publish`, or the checkout's `HEAD` cannot be read, or `target_sha` ≠ `HEAD` |

No record, or a closed one, changes nothing (`R-110`). An open publication record attested for
exactly `HEAD` is accepted and printed. `deploy.sh` reads the record with its own six-line reader,
because four suites stage `deploy.sh` alone. The end-to-end cases drive it with records the real
`copy-serve.sh` wrote, so the two cannot drift unnoticed.

### 3.7 The inbound key's record pre-check (`receive-bundle.sh`)

* `receive`: if a record exists, it must be readable (`copy-record-readable`) **before a byte is
  read**. After the bundle is kept, an open record that is not yet an import record becomes one
  (`purpose "import"`, `target_sha null`).
* `import`, in this order: `copy-record-present` (TRANSPORT), `copy-record-readable`,
  `copy-record-open`, `copy-record-attested` (copy → `attestation` set; waiver → `waiver` set),
  `waiver-before-real-data`, `copy-record-in-window` (copy: now ≤ `quiesced_at` + 12 h; waiver:
  now ≤ `expires_at`), `writers-still-stopped` (`docker compose ps --quiet` for each of
  `web`/`api`/`worker` the deployed file declares; a failing `ps` counts as running). Then the
  import lock, then the conversion to an import record, then the detached importer.
* `report`: `copy-record-readable`.

### 3.8 What `W54-BUNDLE-01`'s importer should accept and refuse (proposal; the rule is BUNDLE's)

The importer receives the record at `/run/copy-record.json`. By the time it runs, the inbound key
has already applied §3.7, and the record's `purpose` is `import`. It should **accept** exactly:

* `kind "copy"`, `state "open"`, `purpose "import"`, `attestation` not `null`,
  `attestation.dump_sha256 == dump.sha256`, `now ≤ quiesced_at + 12 h`, and the fingerprint
  recomputed by §3.5's query equal to `fingerprint` (string-equal `sha256`; `tables` for the
  message); or
* `kind "test_data_waiver"`, `state "open"`, `purpose "import"`, `waiver` not `null`,
  `now ≤ waiver.expires_at`, `real_data_marker == false`, `dump == null`, and the recomputed
  fingerprint equal.

It should **refuse**: anything else, a `record_version` other than 1, a closed record, an
unattested copy, an expired copy or waiver, a waiver with `real_data_marker` true, and a drifted
fingerprint. The importer cannot see the marker *file*: only the record's field reaches the
container, and the stand-side check covers the file. "An import alone leaves the fingerprint
unchanged" holds by construction if every row the import writes is in a `norm*` table, an
`audit_event`/`command_record` row of type `norm_custody.*`, or a `blob` row a
`norm_custody_admission` names. Any other table the importer writes (for example `job`, or an
`audit_event` of another type) must be added to §3.5 in the same change, or that BUNDLE test
reddens. The query is computed in SQL, so the importer can run the same text. It can be read out
of `copy-serve.sh` between its markers, or the two can be made one file in a later lane.

## 4. The delete step (importer step 5) — proposal, not implemented

The bundle is mounted read-only into a container running as uid 10001, and the staged files
belong to the inbound key's account. The importer therefore cannot delete the objects, and it
should not get a writable mount: "delete" would then be decided inside the container on bytes the
boundary has stopped watching. Proposed instead, a sixth inbound verb, added as one
`fc_register` line in a later lane (`W55A-STAND-IMPORT-01` or a BUNDLE follow-up):

```
^discard (<KEY>)$
```

It runs under the import lock and takes no client data but the `<KEY>`. It requires
`logs/<KEY>.import.exit` = `0` and a fresh `report <KEY>` exit 0, recorded by `verb_report` as
`logs/<KEY>.report.ok`, holding the report output's SHA-256 and the time. Then it deletes
`bundles/<KEY>/objects/` only, which is inside staging and named by a key the grammar admitted.
It keeps `manifest.json`, `SHA256SUMS` and the report, and writes `logs/<KEY>.discarded`. Its
guards would be `bundle-imported`, `report-matched` and `import-lock-free`. Until that verb
exists, the owner removes `bundles/<KEY>/objects/` by hand after `report` exits 0 (runbook §11).

## 5. Risks and known limitations

* **Unproven against the real stand tools; for `W54-REHEARSAL-01`:**
  * the JSON field names of `mc ls --recursive --json` (`status`, `type`, `key`, `size`, `etag`)
    in the pinned mc release;
  * busybox `df -P -k` and `du -s -k` in the MinIO server image;
  * whether `docker compose ps --quiet <svc>` lists a container in `restarting`. A crash-looping
    writer must count as running. If it does not, `--status` filters are the fix;
  * `flock` (util-linux) on the stand host for `deploy.sh`. Without it, `deploy.sh` refuses
    `stand_import_locked` whenever the lock file merely exists, which fails closed;
  * git's `safe.directory` when the key's account is not the checkout's owner. `checkout-present`
    then refuses with a hint.
* `dump-db` stops the worker with `docker compose stop`. Its `stop_grace_period` is 300 s, so a
  copy during a live run can wait up to five minutes (pause «Очередь» first, runbook §12).
* `restore-db` drops and recreates `public`, then restores in one transaction. A failed restore
  leaves the schema empty until `restore-db` is run again. The writers stay stopped throughout.
* The record is rewritten line by line. Any writer other than these scripts must keep §3.2's
  layout, or every reader refuses (`record-readable`, `copy-record-readable`,
  `stand_copy_unreadable`). That is the safe direction, but it is loud.
* `verify-objects` runs the read-back program with `docker compose run --no-deps api python -c …`,
  so the api image must have the storage adapter's public surface (`S3BlobStore`,
  `S3StorageSettings`, `BlobId`), which W53's and W54's images do. It reads with `verify=False`
  and hashes the bytes itself. An empty sample is a refusal, not a pass.
* `restore-test.sh` needs the local stack's PostgreSQL image
  (`auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9`, built by `make up`) to match the stand's
  PostgreSQL 17.11 and pgvector 0.8.6. Another version may render rows differently, and the
  fingerprint would then mismatch, which fails loudly.
* The P2 bootstrap of the copy key is deferred to the first real upload (`R-110`, amendment 1).
  Runbook §13 documents the install, including `.git/info/exclude` for
  `/srv/auditmanager/copy-serve/`.
* `capacity` reports `unknown` for a value the stack did not answer. It is a measurement and does
  not refuse.

## 6. Instructions for the integrator

1. Merge after BUNDLE (§5 of the plan). The shared paths, in §6's writer order:
   * `DEPLOYMENT_RUNBOOK.md`: BUNDLE adds import and report text. This lane changed §11's refusal
     table and its "does not do" bullets, and appended §13. A conflict, if any, is in §11.
   * `receive-bundle.sh`, `lib/forced-command.sh`, `test_bundle_transport_refusals.py`: not in
     BUNDLE's grant, so there should be no conflict.
2. Re-run after the merge, one at a time:

   ```
   .venv/bin/python -m pytest -q -rs tests/integration/composition/test_stand_copy_refusals.py \
       tests/integration/composition/test_bundle_transport_refusals.py \
       tests/integration/composition/test_deploy_script_refusals.py
   ```

   Expect 331 passed and 1 skipped, plus whatever BUNDLE adds. If BUNDLE's importer changes
   `auditmanager.norms.bundle`'s argv, `test_bundle_transport_refusals.py::_fixed` pins it.
3. **The heavy step, in an owner-designated window only.** It runs alone, after the floor is
   measured just before it starts. It starts two containers of its own, named
   `stand-copy-source-<pid>` and `stand-copy-restore-20200101T000000Z-<pid>`, and removes both by
   those names. Increment: well under 1 GB.

   ```
   cd .local/worktrees/w54-stand-copy        # or the merged tree
   infra/deploy/capacity-probe.sh --path docker_root="$(docker info --format '{{.DockerRootDir}}')" \
       --need docker_root=$(( 4 * 1073741824 )) --need-ram $(( 6 * 1073741824 ))
   docker image inspect auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9 >/dev/null   # built by make up
   W54_STAND_COPY_WINDOW=1 .venv/bin/python -m pytest -q -rs \
       tests/integration/composition/test_stand_copy_refusals.py::test_a_dump_restored_here_reproduces_the_fingerprint
   ```

   Expected: 1 passed. It proves three things against a real PostgreSQL: a custom dump restored
   by `restore-test.sh` reproduces the fingerprint, custody and `norm*` rows leave it unchanged,
   and a client row changes it.
4. Confirm or rule on §3.2–§3.8 for BUNDLE (especially §3.8's acceptance rule and the
   fingerprint's exclusions), and on §4's `discard` verb.
5. `W54-REHEARSAL-01` should cover §5's first bullet: every copy verb on a disposable stand, the
   waiver path, the full path, a waiver refused after the marker, and `deploy.sh` accepted under
   a publication record for its SHA and refused under an import record.

## 7. Containment

* `git diff --name-only 80a157f..HEAD` on the commit that adds this report lists exactly §1's 13
  paths, each inside the `W54-STAND-COPY-01` grant (plan §4 Stage C plus this report).
  `git status --porcelain -uall` prints nothing.
* Not touched: `contracts/**`, `db/migrations/**`, `src/**` (the importer, `norms/bundle/**`, is
  BUNDLE's), `compose.server.yml`, `reset.sh`, `verify-deployed.sh`, `push-bundle.sh`,
  `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `CURRENT_STATE.md`, lock and
  dependency files, other worktrees, refs and tags.
* No container was started, and there was no network, SSH or stand access. Nothing was pushed,
  merged or tagged. There was no stash, and no process was killed.
