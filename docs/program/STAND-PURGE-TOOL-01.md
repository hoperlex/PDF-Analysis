# STAND-PURGE-TOOL-01 — delete the stand's product data, keep its accounts and its norm corpus

**Status:** code and tests done on a lane stack (PostgreSQL 16 + pgvector 0.8.6, MinIO); **nothing has run on the deployed
stand.** The owner or operator runs it after reading the dry run (section 2). **Base:** `origin/dev` `ef3c348a` (migration head
`0029_routing_refusal_codes`, contract `1.0.0` sealed). **Premise:** the stand holds only generated test data (`R-109`, `R-110`,
`R-140`, `R-141`); the corpus (snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`: 674 documents, 350,194 paragraphs, 55,855 chunks) and the
accounts (the administrator's changed password) must survive. `D-156` ("purge the generated data at the transition to beta, keep
the corpus") is what this serves; it does not close it, the operator run does.

## 1. Why a script, and why not the other two ways

* `infra/deploy/reset.sh` drops schema `public` and empties the bucket. The corpus and the accounts go with the test data: out.
* A purge baked into a migration (`STAND-PURGE-0022-01`, `R-141d`, `D-194`) was rejected: a permanent revision must never be able to
  empty a database, and a restored older backup upgraded later would be purged.
* This is an **operator tool**: `infra/deploy/purge-product-data.sh` (bash, in `reset.sh`'s style) driving
  `scripts/recovery/product_purge.py` inside the `api` image. It changes no migration, no contract, no `src/`.

## 2. The operator commands

Always from the checkout on the stand, with the same `env/alpha.env` the stack runs on. The typed names must equal the configured
ones (`POSTGRES_DB`, `S3_BUCKET`), as for `reset.sh`.

```
# 1. rehearse: reads, counts, touches nothing; refuses exactly as the real run would
infra/deploy/purge-product-data.sh --database <db> --bucket <bucket> --dry-run

# 2. do it (stops the worker, dumps, verifies, purges in one transaction, deletes objects, restarts the worker)
infra/deploy/purge-product-data.sh --database <db> --bucket <bucket> --yes-purge-product-data

# 3. only if step 2 said "THE DATABASE PART IS COMMITTED" and exited 4: finish the objects from that run's own list
infra/deploy/purge-product-data.sh --database <db> --bucket <bucket> --finish-objects infra/deploy/dumps/<instance>-purge-<stamp>
```

Other flags: `--env-file <path>` (default `infra/deploy/env/alpha.env`), `--allow-running` (purge although a run or job is executing).
`ALPHA_DUMP_ROOT` moves the dump root (default `infra/deploy/dumps/`). No flag, an unknown flag, two modes, a missing name: refused,
exit 3, nothing read.

**Exit codes:** `0` done or nothing to do; `2` usage; `3` REFUSED (nothing was changed); `4` FAILED (the message says what state that
leaves; after a COMMIT it is `--finish-objects`).

### What the dry run prints (abridged; from the lane rehearsal, `purge-product-data.sh ... --dry-run`)

```
purge-product-data: database <db> (migration head 0029_routing_refusal_codes), bucket <bucket>

-- PRODUCT tables: every row goes (TRUNCATE) --
  analysis_artifact_publication  (10 rows)
  ...
  project  (5 rows)
  total: 115 rows in 29 tables

-- MIXED tables: product rows go, keep rows stay --
  audit_event  (delete 24 rows, keep 3 rows)
  command_record  (delete 10 rows, keep 1 rows)
  blob  (delete 23 rows, keep 2 rows)

-- KEEP tables: never written --
  app_user  (4 rows)
  norm_paragraph  (1 rows)
  ...
  total: 78 rows in 23 tables

-- objects in the bucket --
  product objects to delete, by exact key: 24 objects, 271448 bytes (9 more keys are named by rows but not in the bucket)
  norm-owned objects (the custody ledger's, never touched): 2
  other objects (named by no row; never touched): 1 (blobs/ 1)
  objects in the bucket: 27

-- work in flight --
  running now: nothing
  queued, discarded with the rest: 1 runs, 0 jobs

--dry-run: NOTHING ABOVE WAS CHANGED.
nothing-to-purge: no
database-bytes: 13326003
product-object-bytes: 271448
plan-sha256: 05a12771b58115fab70a4391821d55c5055906474bfff74b029fab9316da6d55
```

Counts are `count(*)`, never `pg_stat` estimates (`D-24`). On the stand the corpus figures appear under KEEP (350,194 paragraphs,
55,855 chunks, 28,920 norm-owned objects): **if they do not, stop and do not run step 2.**

### What a real run prints (same rehearsal, 9.5 s on test-size data)

`dumping into infra/deploy/dumps/<instance>-purge-<stamp>` → `stopping the worker service` → `snapshot-objects: 24 objects, 271448
bytes copied` → `dump verified -- database.dump listed and expanded, objects copied` → `purging in one transaction` → a table
`PRODUCT project  5 -> 0 ... KEEP app_user  4 -> 4 ...` for all 55 tables and `KEEP tables and keep rows verified unchanged inside
the transaction: 26 fingerprints equal` → `the database part is committed; deleting the product objects` → `objects deleted by exact key:
24 deleted (271448 bytes), 9 already absent` → `done. The dump is at ...` → `starting the worker service again`.
A second run prints the preflight, then `nothing to purge. Nothing was dumped and nothing was changed.` and exits 0.

## 3. The classification (derived from `schema_coverage.py`, closed, refuses on the unknown)

`scripts/recovery/product_purge.py` classifies **every base table of `schema_coverage.TABLES`** (55 at head `0029`) and refuses,
naming the table, before it touches anything, if a live table is in none of the three groups, a declared one is missing, the
declaration differs from `schema_coverage.TABLES`, a view is not `schema_coverage.VIEWS`, or a relation lives outside `public`.
The norm half of KEEP **is** `schema_coverage.EXEMPT_FROM_FINGERPRINT` (imported, not retyped); `tests/.../test_product_purge.py` fails
when the declaration and `schema_coverage.TABLES` stop being a partition.

| Group | Tables | Treatment |
| --- | --- | --- |
| **PRODUCT (29)** | `project`, `document`, `document_version`, `input_manifest_entry`, `analysis_artifact_publication`, `audit_run`, `stage_result`, `model_call`, `provider_call_effect`, `job`, `attempt`, `lease`, `worker`, `finding`, `finding_observation`, `finding_observation_norm_citation`, `finding_evidence`, `expert_decision_event`, `document_version_classification`, `document_version_classification_correction`, `work_assignment`, `work_assignment_event`, `price_list_revision`, `price_list_position`, `vendor_list_revision`, `vendor_list_entry`, `optimisation_pass`, `optimisation_proposal`, `optimisation_proposal_decision` | one `TRUNCATE` (no `CASCADE`) |
| **KEEP, accounts (4)** | `app_user` (the sign-in throttle is its columns), `app_user_role`, `registration_request`, `account_release_mark` | never written |
| **KEEP, release and lookup (5)** | `release`, `release_revision`, `alembic_version`, `contract_state_transition`, `execution_control` (the queue's pause switch: whoever paused the queue resumes it) | never written |
| **KEEP, the corpus (14)** | `norms_snapshot`, `norm_document`, `norm_paragraph`, `norm_chunk_build`, `norm_chunk`, `norm_embedding_profile`, `norm_embedding_build`, `norm_embedding`, `norm_retrieval_set`, `norm_custody_admission`, `norm_custody_binding`, `norm_current_snapshot`, `norm_current_snapshot_event`, `norm_repair_call` | never written |
| **MIXED (3)** | `audit_event`, `command_record`, `blob` | rows classified, see below |

**Mixed tables.** The frozen `stand-fingerprint-v1` (`copy-serve.sh`, `copy_record.py`) is the precedent for what is the corpus' inside
them.
* `audit_event`: events `norm_custody.*` stay; the run/job/attempt/provider/artifact/stage/finding/execution journal goes. An event
  type that is neither refuses, naming it.
* `command_record`: `approve_registration` receipts stay (account-side); the product commands go. A command type that is neither
  refuses, naming it. (`tests/.../test_product_purge.py` greps `src/` for `event_type=` and command constants so a new one fails in
  the gate, not on the stand.)
* `blob`: a row any KEEP table references (custody admission/binding, retrieval set; found from the live catalog, closed against
  `blob_reference_audit`'s set) stays with its object, even if a product row references the same bytes (a Blob is content-addressed
  and shared). Every other row goes with its object.

**Views** (`finding_current_verdict`, `version_classification_current`, `version_classification_revision`, `work_assignment_current`)
hold no rows and empty themselves.

## 4. Order, and what each step guards

1. **Guards before any connection** (bash, 11): known options, a mode, one mode, both names typed, env file, configured instance,
   typed database/bucket equal the configured ones, compose file, the module directory.
2. **Preflight, read-only, in the `api` image** (`REPEATABLE READ, READ ONLY`): catalog guards (relations, classification, the Blob
   reference set, no foreign key from a KEEP/MIXED table into a PRODUCT table, no `BEFORE TRUNCATE` trigger on a PRODUCT table,
   the connected role owns what it must change, no libpq `PG*` variable, the bucket is unversioned), row classes, **quiescence** (a
   run `running`/`validating`, a job or attempt `leased`/`running` refuses unless `--allow-running`; queued work is counted and
   discarded), the exact rows and object keys, and one **plan SHA-256** over the product rows' digests, the mixed rows to delete and
   the key list.
3. **Stop the worker** (it writes on its own), make a fresh `infra/deploy/dumps/<instance>-purge-<UTC stamp>/` with room checked
   first (database size + product object bytes + 256 MiB), and write **`database.dump`** (`pg_dump --format=custom`, the whole
   database through the stack's own postgres, corpus included), the **product objects' bytes** under `objects/` and **`objects.attrs`**
   (the six attributes per object, in `reset.sh`'s sidecar format), **`product-objects.tsv`** (key, size, kind, reference, sha256,
   restorable), `plan.txt`, `objects.sha256`.
4. **Verify the dump**: `pg_restore --list` reads it (the table of contents) **and** `pg_restore --file=-` expands every data block
   to a null sink (a custom dump cut short can pass `--list`; reused from the cancelled cleanup branch); `objects.attrs`, `objects/`,
   `product-objects.tsv` exist; each copied object has the size and the sha256 the object recorded; the mirror has the count and
   bytes the plan named; **the plan is recomputed and must be the same SHA-256**.
5. **One transaction.** `lock_timeout 15 s`; `LOCK` KEEP `SHARE` and PRODUCT/MIXED `ACCESS EXCLUSIVE`; the plan **re-derived under the
   locks** and compared with the one the dump was taken for; KEEP fingerprints taken (count + digest of every KEEP table whole and
   of each mixed table's keep rows); `audit_event`'s append-only trigger (one named trigger, owner right, transactional) switched
   off for the one `DELETE` and back on; `TRUNCATE` of the 29 product tables; `DELETE` of the product `command_record` and `blob`
   rows; counts per table before/after; KEEP fingerprints taken again and **a mismatch rolls the transaction back**; every PRODUCT
   table empty, every mixed table down to its keep rows, every trigger's state and `alembic_version` as before, or rollback.
6. **Only after COMMIT, objects, by exact key from the dumped list** — never a prefix. The deleter parses the list strictly (each
   key must equal the key derived from its Blob id or token), refuses if **its SHA-256 differs** from the dumped one, refuses any
   key the norm custody ledger owns, refuses any key whose Blob row still (or again) exists, refuses a versioned bucket, deletes,
   and checks the key is gone. A failure here exits 4 with the exact `--finish-objects` command; the database part is complete.
7. **Start the worker again**, always (also after a refusal or a failure), and print where the dump is.

**What it never touches:** the norm bucket keys, the session register (`<instance>-web-sessions`, `reset.sh`'s business), any
account row, `alembic_version`, a sequence (none is reset), objects no row names (counted in the dry run as "other objects").

### Which mechanism works, proved (the brief asked)

* `TRUNCATE` of the product tables needs **only table ownership**: the immutable/append-only triggers are `BEFORE UPDATE OR DELETE`
  row triggers and do not fire on `TRUNCATE`. The only `BEFORE TRUNCATE` triggers at head `0029` are
  `trg_norm_current_snapshot_no_truncate` and `trg_norm_current_snapshot_event_no_truncate`, on KEEP tables that are never
  truncated and never reached by `CASCADE` (the tool never uses it). A `BEFORE TRUNCATE` trigger on a PRODUCT table is a refusal, not
  something to disable (`no-truncate-guard-on-product`).
* `audit_event` rows cannot be deleted while `trg_audit_event_append_only` is on. `ALTER TABLE ... DISABLE TRIGGER <that one
  trigger>` works for the **owner** (the migration role), inside the transaction, and is undone by `ENABLE` in the same transaction;
  no superuser mechanism (`session_replication_role`, `DISABLE TRIGGER ALL`) is used. The connected role not owning the tables is a
  refusal (`owner-may-write`). `triggers-restored` compares every user trigger's `tgenabled` before and after.

## 5. Restore

The dump is `reset.sh`'s layout, so its restore applies: `infra/deploy/reset.sh --database <db> --bucket <bucket> --restore
infra/deploy/dumps/<instance>-purge-<stamp>` puts back the objects first, then `pg_restore --clean --if-exists` of the whole
database, then (R-52) raises `token_epoch` on every account and names any account on a default password. It replaces **every**
table with the dump's copy: the accounts and the corpus as they were at dump time as well. Proved on the lane: the dump of a
purged stand restores into a scratch database with every product row count of the pre-purge database
(`test_the_script_purges_for_real_and_the_dump_it_leaves_restores`); `reset.sh --restore` itself was not run (it needs `mc` containers
a lane does not have). Temporary staging objects a product row names are mirrored and listed (`restorable: no`) but not re-attached:
they have no recorded attributes.

## 6. What was reused from `task/prod-project-cleanup` (90f9aba7, 2026-10-09) and what was dropped

Read for ideas, not merged (it was built for head `0016` and a one-time migration; `src/**` is closed to this lane).

| Reused | Where |
| --- | --- |
| A dump is not verified by `pg_restore --list` alone: a truncated custom archive passes it and fails on expansion (measured there with a real 1,667-byte dump) | `dump-verified` runs `pg_restore --file=-` too |
| libpq's ambient `PG*` variables (`PGHOSTADDR`, `PGSERVICE`) can override the host in `DATABASE_URL` | `no-ambient-libpq` |
| A versioned bucket turns a `DELETE` into a delete marker | `bucket-unversioned` |
| Objects are deleted from a durable list of exact keys, re-derived and re-checked before the delete; a rerun finishes a partial pass | `product-objects.tsv`, `key-shape`, `row-gone`, `--finish-objects` |
| Compare the live project/Blob state to what was backed up before deleting; lock the tables; the changed set stops the run | the plan SHA-256, `plan-unchanged`, `lock-available` |
| The key rule comes from the storage adapter, not from a pattern | `canonical_object_key_for_recovery` (public) for canonical keys; the `temporary/` prefix is a literal pinned by a test against `_object_layout` |

| Dropped | Why |
| --- | --- |
| The pinned head `0016`, the pinned project FK graph, the pinned list of Blob referrers | the classification now comes from `schema_coverage.py`; the head is only reported |
| Deleting by identity regex over every `audit_event` payload | `norm_custody.*` is kept by event type, the rest of the journal goes by event type; unknown types refuse |
| "no other client sessions" | the `api` container keeps pooled sessions; quiescence is the running-work check, the worker stop and the locks |
| An `operations.*` intent/completion event written into `audit_event` | this tool writes nothing into the database but deletions; the trace is `plan.txt` in the dump directory; the object list is the TSV |
| A `ProjectCleanupObjectStore` in `src/storage/` | `src/**` is closed; the S3 calls are `boto3` in the tool |
| `restore-objects` as its own verb | the dump is `reset.sh --restore`-compatible |
| Dumping only what the project graph owns | the tool keeps the accounts and the corpus *in* the database, so it dumps the whole database |

## 7. Measured, with the method

* **Rehearsal on the lane** (PostgreSQL 16 + MinIO, `make up`; seed `scripts/recovery/synthetic_drill_seed.py` + `purge_seed.py`; 115
  product rows, 24 present product objects of 271,448 bytes, 78 keep rows, host load average about 15): `purge-product-data.sh ...
  --yes-purge-product-data` through `tests/integration/recovery/docker_shim.py` took **9.5 s** wall clock (`time`, the whole script).
* **Fingerprint cost at the corpus' scale, extrapolated, not measured on the corpus:** in a scratch database on the lane,
  `SELECT count(*), sum(first 64 bits of sha256(row text))` over 50,000 rows of 1.5 KB took 109 ms and over 5,000 rows with a
  `vector(1024)` column 167 ms (psql `\timing`). Scaled to 350,194 paragraphs and 61,573 embedding windows that is about 0.8 s and 2 s per
  pass, twice per run. The real corpus was not available on the lane; the stand's figures are UNVERIFIED.
* **Not measured:** `pg_dump` and `pg_restore --file=-` on the 2.5 GB corpus-bearing database (the dump-room guard assumes the dump is
  not larger than the database); the transaction's lock wait on a busy stand; anything in the real `api` image (see 8).

## 8. Known limits and UNVERIFIED

* **Not run on the deployed stand**, and the `api` image was not built here (it costs gigabytes this host does not have). The tests use a
  `docker` shim for `compose exec postgres` and `compose run ... api python`; the SQL, the S3 calls, `pg_dump` and `pg_restore` are real.
  **UNVERIFIED on the stand:** that `compose run -v <checkout>/scripts/recovery:/purge/scripts/recovery:ro --user root -e PYTHONPATH=/app/src:/purge`
  resolves `scripts.recovery.product_purge` inside the image (it relies on `scripts/` being a namespace package, as the tests' own imports
  do), and that the stand's database role owns the tables (the migrations run as it; the `owner-may-write` guard says so by name if not).
* **Run the dry run on the stand first.** An event type or command type the code scan did not know, a table a later migration added, or a
  `PG*` variable is a named refusal there, before anything is touched.
* Writers: the worker is stopped by the script; `web` and `api` are not. A write between the plan and the transaction makes the plan
  SHA-256 differ and the run refuses (the dump is then stale and harmless). Stopping `web` and `api` for the window removes the retry.
* A `running` job left by a crashed worker blocks the purge until its lease is resolved or `--allow-running` is given.
* Objects named by no row (a staged upload nobody references, a stray) are neither deleted nor listed beyond a count.
* The bucket must be unversioned. The tool deletes keys, it does not purge versions.
* `schema_coverage.HEAD` was `0028_classification_corrections` while the alembic head is `0029_routing_refusal_codes`: at `origin/dev`
  `ef3c348a` 26 recovery tests failed with `migration head differs`, independent of this tool. The second commit of this branch moves the
  pin to `0029_routing_refusal_codes` (migration `0029` only widens four stored-error CHECKs: measured on a migrated lane database, 55 tables,
  4 views, 72 triggers, 7 sequences, constraints `c=445 f=111 p=54 t=8 u=39`, 153 indexes, 0 unvalidated, all equal to the declaration) and makes
  `test_synthetic_drill_runner` follow the single pin instead of a literal. `product_purge` does not read `HEAD`.

## 9. Tests (all against the lane's real PostgreSQL and MinIO unless stated)

| File | What it proves |
| --- | --- |
| `tests/integration/recovery/test_product_purge.py` | the declaration partitions `schema_coverage.TABLES`; every `event_type=`/command constant in `src/` is classified; dry run changes nothing and prints exact counts; the purge empties all 29 product tables, leaves 23 KEEP tables, the keep rows of the 3 mixed tables and `alembic_version` identical by the test's own digest, deletes the product objects and keeps the norm objects and a stray byte for byte, leaves triggers and sequences as they were, and the stand still works (the administrator signs in with the changed password; a project can be created); a second run is a no-op; **26 guards x (refuses and changes nothing, deleting the guard removes the refusal)** |
| `tests/integration/recovery/test_product_purge_script.py` | the real script, through the docker shim: dry run, real run with worker stop/start, the dump restores into a scratch database, `objects.attrs` passes `reset.sh`'s regex, second run no-op, running job (exit 3, no dump, `--allow-running` overrides), unclassified table (exit 3), a post-commit deletion failure (exit 4) finished by `--finish-objects`, a list a row still names refused |
| `tests/integration/composition/test_purge_product_data_script.py` | with a scripted `docker`, no stack: every bash refusal exits 3 and calls no docker; deleting each of the 15 guard blocks removes the refusal (and, after a connection, lets the script reach `pg_dump`/`apply`); order; exit codes 2/3/4; worker restarted on every path; dry run is one read-only call; nothing-to-purge writes nothing |

### Mutation table (a guard block deleted from a copy; the real module/script refuses, the copy does not)

Python module (`# >>> guard:` markers; each row = scenario, real result, what the copy does):

| Guard | Scenario | Copy without it |
| --- | --- | --- |
| `no-ambient-libpq` | `PGHOSTADDR` set | connects and plans |
| `names-match` | wrong database typed | plans for the wrong name |
| `bucket-unversioned` | versioning enabled on the bucket | plans |
| `relations-recognised` | table in another schema | ignores it |
| `classification-total` | throwaway table `zz_throwaway` | plans, the table would survive unclassified |
| `declaration-matches-coverage` | `schema_coverage.TABLES` differs | plans |
| `blob-columns-closed` | new Blob reference column | classifies it silently |
| `keep-never-references-product` | KEEP column with a foreign key into `project` | plans (the truncate would fail later) |
| `no-truncate-guard-on-product` | `BEFORE TRUNCATE` trigger on `project` | plans |
| `owner-may-write` | role without ownership | plans (the transaction would fail later) |
| `event-types-classified`, `command-types-classified` | `zz.unclassified` event, `zz_unclassified` command | treats it as product, deletes it |
| `quiescent` | a run `running` | plans over it |
| `norm-key-not-in-product-list` | norm key set equal to the product keys | plans |
| `lock-available` | a session holds `project` | exit 4 FAILED instead of 3 |
| `plan-unchanged` | a project inserted after the dump | commits, purging a row the dump never saw |
| `object-list-matches-plan` | one key dropped from the list | commits with a list that is not the plan's |
| `keep-unchanged` | classification that also deletes `norm_custody.*` events | commits, the custody journal is gone |
| `product-emptied` | classification that deletes no product event | commits, product events remain |
| `triggers-restored` | `audit_event` trigger disabled beforehand | commits, trigger silently re-enabled |
| `mirror-bytes-match` | object bytes differ from its recorded sha256 | copies and goes on |
| `mirror-complete` | stale file in the mirror directory | accepts it |
| `object-list-intact` | list SHA-256 differs | deletes from an edited list |
| `key-shape` | list names the stray object under a product reference | **deletes the stray object** |
| `norm-owned-key` | list names a corpus object | `row-gone` still refuses; both deleted: **the corpus object is deleted** |
| `row-gone` | `delete-objects` before the purge | **deletes objects whose rows remain** |

Bash script (`# >>> guard:` markers): `known-options`, `destructive-flag`, `one-mode`, `names-required`, `env-file-present`,
`instance-configured`, `database-matches`, `bucket-matches`, `compose-file-present`, `module-present`, `finish-dir-valid` (each: exit 3,
no docker call; copy: no refusal); `preflight-ran` (copy reaches `pg_dump` on a refused or digest-less preflight), `dump-has-room`
(copy reaches `pg_dump` on a full disk), `dump-verified` (copy reaches `apply` on an empty, unreadable or truncated dump),
`plan-unchanged` (copy reaches `apply` after the plan moved).
