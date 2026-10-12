# W55A-FIX-DB — the first database run of W54 + W55a, repaired

**Executor:** lane `agent/w55a-fix-db`, worktree `.local/worktrees/w55a-fix-db`.
**Base:** `9c635ee` (`origin/dev`: all W54 and W55a code). **Date:** 2026-10-13.
**Input:** the integrator's first full database run (`.local/handoff/w54db.log`, `w54db.xml`):
3259 passed, 15 failed, 2 errors.
**Stack:** private instance `gate-w55a-fixdb` (PostgreSQL 17 + pgvector 0.8.6 on `57300`, MinIO on
`60900/60901`), `make up && make migrate` to `0020_norms_search`, owner ruling R-111.
**Commits:** fixes `6a7a1e7`; this report is the next commit.

## 0. Verdicts

One **product** defect, eleven **test** defects. No migration, contract or lock file was wrong
or touched.

| # | Failure | Verdict | Root cause |
| --- | --- | --- | --- |
| 1 | `test_d124_a_second_snapshot_no_longer_shrinks_nearest` | TEST (fixture) | the far snapshot was unreachable in the HNSW graph |
| 2 | `test_the_migration_creates_the_canonical_and_rebuildable_topology` | TEST | 0020's two tables missing from the expected `norm%` set |
| 3a | `test_import_conflicts_are_refused_and_write_nothing` | TEST | other key inconsistent with the row's counts (W54-FIX-PY §4.1) |
| 3b | `test_an_import_the_database_refuses_midway_leaves_nothing_behind` | TEST | Python now subsumes `ck_norms_snapshot_raw_key` |
| 4 | `test_a_fresh_upgrade_creates_the_current_snapshot_and_the_search_columns` | TEST | catalog query also read the two GIN indexes' attributes |
| 5 | `test_the_current_snapshot_changes_only_with_its_own_history_event` | TEST | the BEFORE trigger fires before the key/CHECK; wrong event for an INSERT |
| 6 | `test_every_migration_invariant_family_matches_the_reviewed_fresh_database` | TEST (pending reseal) | 0018–0020 never sealed against a database |
| 7 | `test_d150_and_worker_claims.py` × 2 (setup errors) | TEST | fixture copied the product's `detach()` order (see 8) |
| 8 | `test_worker_service.py` × 2 | **PRODUCT** | `JobWakeup.connect` read `driver_connection` after `detach()` → `None` |
| 9 | `test_bundle_postgres.py` × 2 | TEST (+ support) | tamper broke `ck_norm_paragraph_char_length`; duplicate kwarg in `open_waiver` |
| 10 | `test_an_administrator_reads_the_history` | TEST | grantor was a random `usr_` not in `app_user` |
| 11 | `test_the_port_offers_no_way_to_name_or_delete_an_object` | TEST | `open_stream` (a read) missing from the expected member set |
| 12 | `test_reconciliation_rules_with_no_guard.py` × 2 | TEST | since W54-CUSTODY-01 `publish` refuses to adopt an impostor; precondition unreachable through the port |

## 1. Diagnoses, with the evidence

**1 — D-124 (test).** A probe on this stack (temporary test, deleted) seeded the test's two
snapshots and measured:

- the settings *are* applied: inside `nearest`'s transaction `current_setting` reads
  `strict_order` / `200` / `100000`; pgvector is `0.8.6`, whose GUC names these are;
- the iterative scan *does* run: `EXPLAIN ANALYZE` shows `Rows Removed by Filter: 150`, i.e. it
  walked every near-snapshot tuple it could reach;
- the far snapshot is **unreachable**: an *unfiltered* scan with `ef_search = 1000` returns 150
  rows, 0 of them far; even a query *equal to a far vector* returns 0 far rows.

Cause: `_far(i + 500)` gave each far vector a private dimension, so every far vector was exactly
equally far from every near vector. pgvector's neighbour heuristic (`distance <= e->distance`
discards) then pruned every far vector from every near vector's neighbour list; nothing in the
graph pointed at them. With `_far(i + 1)` — each far vector shares its one non-query dimension
with one near vector, so it is strictly nearest to that one — the same probe gave: no settings
0 rows (the defect still reproduced), `strict_order` 10 rows, unfiltered 180 rows / 30 far.
`nearest`, `SCAN_SETTINGS` and the short-scan refusal are correct and unchanged. The fixed test
passed 8 of 8 consecutive runs; its "settings reverted → `NormEmbeddingScanShort`" half still holds.

**2 — corpus topology (test).** Added `norm_current_snapshot`, `norm_current_snapshot_event`.

**3a — import conflicts (test).** `"+1r+1u." → "+1r+2u."` with `unreliable_count` 1 is now refused by
`_require_key_terms` before the database. The other key now travels with `unreliable_count = 2`
(the count it names; validation requires only `> 0` when a paragraph is unreliable), so "the same
id under another key" reaches `SnapshotImportConflict "the id names key"` and "a child id held by
another snapshot", which shares that key, reaches its own conflict.

**3b — midway refusal (test).** The raw-key contradiction is kept as a first assertion, now
expecting `SnapshotRowsInvalid (key_terms)` with nothing written. The database refusal is reached
by another constraint no Python check states: a key every check accepts (`+1r`, `repair_count = 1`)
over rows whose last paragraph's `char_length` is one longer than its text. The insert fails on
`ck_norm_paragraph_char_length` **after** the snapshot and document rows are written — more truly
"midway" than the old case, which failed on the first insert — and the table counts are unchanged.

**4 — generated columns (test).** `pg_attribute` has a row per index column too;
`ix_norm_document_designation_tokens` and `ix_norm_paragraph_text_tsv` contributed
`attgenerated = ''`. The query now joins `pg_class` with `relkind = 'r'`; the designation index's
definition is asserted separately. The indexes are correct.

**5 — current-snapshot guard (test).** `am_guard_norm_current_snapshot` is `BEFORE INSERT`, so it
runs before the primary key and the CHECK. For an INSERT it takes `expected_from := NULL` (the
migration docstring: "NULL for the first designation"). The test's "one row only" case named an
event `from = first` — a change history — so the guard refused it (`AM003`) and the key was never
consulted; its `singleton = false` case had the same flaw and would have answered `AM003`, not
`23514`. The contract (SEAL-01: "every insert or update names a fresh event whose `from` is the
previous current snapshot"; one row; no unset) holds either way. The test now asserts all three:
a second INSERT with a change history → `AM003` (guard); with a history the guard accepts for an
INSERT (`from` NULL) → `23505` (singleton key); `singleton = false` → `23514` (CHECK). Migration
unchanged.

**6 — inventory (test, reseal).** See §3.

**7, 8 — worker LISTEN (product).** SQLAlchemy 2.0.52 `_ConnectionFairy.driver_connection` is
`None` once `_connection_record` is `None`, which `detach()` sets. `JobWakeup.connect` read it after
`detach()`, so every `LISTEN` attempt raised `AttributeError`, was logged as "could not be
established", and the worker ran on its poll alone: the D-150 wake-up never worked against a real
database (the captured log in `w54db.log` shows exactly that warning). The fix reads the driver
connection before detaching (`src/auditmanager/workers/service.py`, 1 line moved plus a comment).
The jobs `listener` fixture had the same order and got the same fix. Before/after on this stack:
2 failed + 2 errors → 4 passed; `tests/integration/workers` + the jobs module: 47 passed.

**9 — bundle (test + support).** The tamper `UPDATE … SET text = text || ' (tampered)'` broke
`ck_norm_paragraph_char_length` (0012: `char_length = char_length(text)`); it now sets
`char_length` to match, so the row digest, not a CHECK, is what must catch it (it does).
`open_waiver` passed `migration_head=` and `**overrides` that also carried `migration_head` →
`TypeError`; overrides now replace the stand's own values.

**10 — roles window (test).** `set_roles(actor_uid=str(UserUid.new()))` wrote `granted_by` for a
user that does not exist (`fk_app_user_role_granted_by`). The grantor is now a real suite account
(`provisioned_record("norms-roles-grantor")`), never the subject (self-demotion is refused).

**11 — storage port (test).** `open_stream(blob_id, *, expected_sha256, expected_size, …)` reads
by opaque `BlobId`; it names no key and deletes nothing. Added to the expected set.

**12 — ingest impostor (test).** The brief attributed this to W55A-CONTENT's read path; the
failure is earlier. The `DomainError` is raised inside `upload_single_pdf` at step 5: since
`W54-CUSTODY-01` (`20c8f91`) `S3BlobStore.publish` checks an existing canonical object's recorded
SHA-256 and size and refuses a disagreement (`ChecksumMismatchError` / `SizeMismatchError`)
instead of adopting it. The tests planted the impostor first and relied on that adoption. The new
behaviour is correct (available bytes are immutable; covered offline by
`test_publish_reuse_checks_offline.py`). The tests now upload honestly, verify, assert that the
port refuses to plant the impostor (`ChecksumMismatchError` / `SizeMismatchError` on the real
adapter), then replace the object out of band through `raw_s3` — the route
`test_the_read_path_answers_the_manifest.py` and `test_reconciliation_reads_the_bytes.py` already
use — and keep every original reconciliation and read-path assertion.

## 2. Changed files (`git diff --name-only 9c635ee..HEAD`)

```
src/auditmanager/workers/service.py
tests/integration/db/test_norm_embeddings_migration.py
tests/integration/db/test_norms_corpus_migration.py
tests/integration/db/test_norms_search_migration.py
tests/integration/db/test_schema_invariant_inventory.py
tests/integration/ingest/test_reconciliation_rules_with_no_guard.py
tests/integration/jobs/test_d150_and_worker_claims.py
tests/integration/norms/bundle/conftest.py
tests/integration/norms/bundle/test_bundle_postgres.py
tests/integration/norms/search/test_norms_roles_window.py
tests/integration/storage/test_publication.py
docs/program/W55A-FIX-DB.md   (this report, the next commit)
```

## 3. Inventory review (item 6)

Method: two fresh databases on this stack, one `alembic upgrade 0017_execution_queue`, one
`upgrade head`; every family's rows dumped with the test's own queries and normalisation and
diffed (scratch script, not committed). The 0017 inventory equalled the previous
`EXPECTED_INVENTORY` exactly; the head inventory equalled the failing run's printed one exactly.

| Family | 0017 → head | Rows added / removed | Explained by |
| --- | --- | --- | --- |
| columns | 357 → 419 | +62 / −0 | 0018: publication `abandoned_at`, admission 17, binding 9, repair call 16, `norm_paragraph.text_reliability`, `norms_snapshot.unreliable_count`; 0019: worker 6, `lease.worker_id`; 0020: event 5, current 3, generated `designation_tokens`, `text_tsv` |
| relations | 44 → 50 | +6 / −0 | 0018 three tables; 0019 `worker`; 0020 two tables |
| constraints | 385 → 449 | +66 / −2 | 0018: admission 14, binding 9, repair call 16, paragraph reliability, unreliable count, `ck_analysis_artifact_abandoned_shape`, redefined `ck_analysis_artifact_state` (+`abandoned`) and `ck_norms_snapshot_raw_key` (+`unreliable_count`); 0019: worker 5, lease format CHECK + FK; 0020: event 8, current 7 |
| indexes | 97 → 121 | +24 / −0 | 0018 13, 0019 3, 0020 8 (two PKs, `uq_norm_current_snapshot_event`, two event indexes, designation GIN, partial `text_tsv` GIN, partial clause index) |
| triggers | 35 → 42 | +10 / −3 | 0018: both effect-table state guards redefined `BEFORE INSERT OR UPDATE` (D-148), four custody/repair-call triggers; 0019: `trg_lease_frozen_guard` redefined to freeze `worker_id`, `trg_worker_frozen_guard`; 0020: guard + event immutability |
| functions | 10 → 15 | +6 / −1 | `am_guard_durable_effect_transition` gains its INSERT arm; three custody/repair-call guards; `am_guard_norm_current_snapshot`, `norm_designation_tokens` |
| views, extensions, sequences, policies, state topology | unchanged | 0 | digests byte-identical |

No row outside 0018/0019/0020 changed. Resealed values (and this review, condensed) are in the
test's comment block.

## 4. Checks run

All on this lane's private stack, on the tree committed as `6a7a1e7` (the targeted runs ran on
the identical uncommitted tree just before the commit), with the lane `.env` exported and
`.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`:

| Run | Result |
| --- | --- |
| the 17 failing IDs, before any change (reproduction) | 15 failed, 2 errors |
| the 17 failing IDs, after | **17 passed** |
| every module that had a failure (10 modules) | **111 passed** (61 s) |
| `test_d124_…` alone, 8 consecutive runs | 8 × passed |
| full set `tests/integration/{db,api,auth,access,runs,jobs,execution,workers,norms,storage,ingest,releases,qa_w53,analysis_text,composition}` on a **freshly migrated** stack (volumes removed, `make up && make migrate`) | **1 failed, 3275 passed, 3 skipped** in 26 min 48 s; the one failure is order-dependent and not this lane's, §4.1 |
| `tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **619 passed**, 50 subtests (30 s) |
| `git diff --check` | clean |

Against the integrator's run (3259 passed / 15 failed / 2 errors over the same set) all 17 IDs now
pass; 3275 + 1 = 3276 = 3259 + 17, so no test was lost or added.

### 4.1 One order-dependent failure, not caused by this lane

`tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py::test_a_final_transaction_longer_than_the_lease_is_not_reclaimed`
failed in the full run (it passed in the integrator's). Measured:

- alone, 3 runs: 3 passed; `tests/integration/runs tests/integration/jobs` on a **freshly migrated**
  stack: **175 passed** (it and `test_w53_jobs_repair.py` included);
- `tests/integration/{db,api,auth,access,runs,jobs}` on a freshly migrated stack, with
  `-o verbosity_assertions=2`: 2 failed, 1397 passed. d141's sweeps were
  `['recovered=1', 'recovered=0', 'recovered=0', 'recovered=1', …]` while its own run published, and
  `runs/test_w53_jobs_repair.py::test_periodic_and_forced_reclaim_two_runs_never_invert_locks`
  saw `periodic: ('committed', 5)` instead of `1`;
- the database afterwards: the extra recoveries were runs created by
  `tests/integration/runs/test_durable_effect_boundaries.py` (idempotency keys `w48-recorded-…`),
  left `running` with the default 60 s lease, and lost exactly when those two tests swept, about
  65 s later.

So two reclaim-counting tests count other tests' deliberately abandoned leases whenever one expires
inside their few-second window: a timing-dependent isolation defect between W48's crash cases and
the W53/W54 reclaim assertions. Nothing this lane changed is on that path (`JobWakeup` is used only
by `WorkerService`, which only `tests/integration/workers` starts, after `jobs`). The files are
outside this grant and were not edited. Suggested owner fix: have both assertions count only their
own run's recoveries, or have `test_durable_effect_boundaries.py` release the leases it abandons.

## 5. Contracts, risks, integrator

- **Contracts:** none new or changed. No migration, `contracts/**`, lock file, `DEBT_REGISTER`,
  `OWNER_RULINGS`, `PORT_REGISTRY`, ref or tag touched.
- **Product change:** `JobWakeup.connect` only; behaviour-changing (workers now actually LISTEN, as
  D-150 specified). No flag: the previous behaviour was a silent fallback, not a mode.
- **Risks:** the D-124 fixture still depends on HNSW graph construction (random levels); with 30 far
  vectors each strictly attached to a near one, reaching 10 is robust (8/8 here, and 30/30 far rows
  reachable in every probe), but it is a graph property, not an algebraic one. Item 12's impostor
  is now written out of band, which is the only way that fault can exist after W54-CUSTODY-01.
- **Integrator:** merge `agent/w55a-fix-db`; re-measure in your own window as usual. Expect the
  §4.1 pair to pass or fail depending on timing until their isolation is fixed; a second pass over
  an already-used database also reddens other `runs` tests the same way (measured: 2 failed on a
  repeat of `runs`+`jobs`), so measure on a freshly migrated stack.

## 6. Containment

`git diff --name-only 9c635ee..HEAD` is the list in §2: one product module (the defect in §1.8),
ten test/support modules named in the brief, and this report. `git status --porcelain -uall` is
empty at the report commit. The stack was stopped (`make down`), only `gate-w55a-fixdb-postgres-data`
and `gate-w55a-fixdb-s3-data` were removed, and `.env` was deleted. No process was killed.
