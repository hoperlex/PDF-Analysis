# RECOVERY-REBASE-01 — the W58 restore drill rebased onto migration head 0028

**Status:** code and one real drill done on a lane stack; nothing pushed, no ref moved. Beta criterion **B6** (backup and
restore drill, local; `BETA-MATRIX-01.md` §B6) asked for the drill to be repeated on a current head. This is that repeat, with
the gaps it exposed closed. **It does not set a PASS**: `ROADMAP-TO-BETA.md` §9 defines B6 as a measurement the owner accepts;
this document is the evidence, with its limits (section 8).
**Base:** `origin/dev` `ff58bdd1` (migration head `0028_classification_corrections`). **Tree the drill ran on:** `a6d485cc (full: a6d485ccf68bde8e48d1b54ca8f8426dd81412ce)`
(the code commits; this document is the only change after it).

## 1. What was wrong

The W58 tooling (`scripts/recovery/**`) was written at head `0023_norm_citations`, and its one real run restored one
hand-seeded Blob. Run against head `0028` it was not merely out of date, it was unusable and, worse, would have stayed
silent about everything it did not know:

| Probe at head 0028 on the unchanged tooling | Result |
|---|---|
| `audit_blob_references` on an empty migrated database | refused: `migration head differs` (pinned `0023`) |
| the same with only the head bumped | refused: `catalog differs: unknown=[('public','price_list_revision','blob_id')]` — migration `0026` added a Blob reference |
| `synthetic_drill_fixture` | wrote records at head `0023`, exactly one Blob |
| `synthetic_drill_runner` | refused any copy not at `0023` with exactly one inventory object |
| 11 new tables, 3 views, 19 guard triggers, 0 Blob-aware rules | nothing enumerated them; nothing checked a restored trigger |

The stand fingerprint (`stand-fingerprint-v1`, the frozen SQL in `infra/deploy/copy-serve.sh`) needed no change: it enumerates
`public` base tables dynamically and, at head `0028`, counts **41** tables (every table except the 14 `norm*` ones). Its
exemption of `norm%` is now written down and tested instead of implied.

## 2. Inventory at head 0028 (measured on the lane database, then pinned)

Tables 44 → **55** (+11), views 1 → **4** (+3), user triggers → **72** (+19 on the new tables), constraints 657, indexes 153,
sequences 7. Added since `0023`:

| Migration | Tables (all immutable/append-only: `am_immutable_row`) | Other objects | Blob / object reference |
|---|---|---|---|
| `0024` | `document_version_classification` | | none |
| `0025` | `work_assignment` (deferred "has an `assigned` event"), `work_assignment_event` | view `work_assignment_current` | none |
| `0026` | `price_list_revision` (deferred "has positions", `BEFORE INSERT` Blob check), `price_list_position`, `vendor_list_revision` (deferred), `vendor_list_entry` | | **`price_list_revision.blob_id`** (FK to `blob`; the trigger demands an `available` Blob with the same digest and size) |
| `0027` | `optimisation_pass` (deferred "has proposals", scope check), `optimisation_proposal` (price check), `optimisation_proposal_decision` | | none |
| `0028` | `document_version_classification_correction` (chain check) | views `version_classification_current`, `version_classification_revision` | none |

`price_list_revision.blob_id` is the **only** new Blob-reference column. Other `*_key` columns are not object references
(`optimisation_proposal.spec_row_key`, `release.sort_key`, `norms_snapshot.*_content_key`, `command_record.idempotency_key`).

## 3. What changed (all under `scripts/recovery/**` and `tests/integration/recovery/**`)

| File | Change |
|---|---|
| `scripts/recovery/schema_coverage.py` (new) | The tooling's closed declaration of the schema at head: `HEAD`, 55 `TABLES`, 4 `VIEWS`, `EXEMPT_FROM_FINGERPRINT` (14 `norm*`, with the reason), `FINGERPRINTED_TABLES` (41), 72 `TRIGGERS` as `(table, trigger, function, event mask)`, 8 `DEFERRED_TRIGGERS`, 7 `SEQUENCES`, constraint and index counts. `audit_restored_schema(session)` compares a restored database with it, SELECT-only: head, relations, trigger set, enabled state, deferral, event masks, constraint counts and validation, index validity, each sequence not behind its table's rows. |
| `blob_reference_audit.py` | Head from `schema_coverage.HEAD` (one head, not two); `price_list_revision` is a declared source whose blob must be `available` with equal digest, size and media type; statement count 8 → 9. |
| `isolated_restore_drill.py` | Refuses before any restore a record whose fingerprint table set is not `FINGERPRINTED_TABLES`; runs `audit_restored_schema` on the restored snapshot before any target object write; the evidence now carries the schema audit. |
| `synthetic_drill_fixture.py` | N Blobs per copy; `prepare_copy_from_bucket` pulls **every object of the source bucket** with `mirror_source_objects` (conditional `GetObject`, listed ETags kept) instead of one local payload; record at `HEAD`; fingerprint lines must name exactly `FINGERPRINTED_TABLES`; `--payload` repeatable or `--source-env`. |
| `synthetic_drill_runner.py` | Head `HEAD`, any positive inventory count; positive evidence = at least one manifest reference and Blob, every sealed object restored, objects ≥ Blobs, bytes ≥ Blob bytes; prints the schema audit. |
| `synthetic_drill_seed.py` (new) | Builds the realistic source dataset through the product's own public surfaces, recorded provider only (section 5). |
| `synthetic_drill_compare.py` (new) | Independent cross-check (section 6) that shares no code with the tooling it checks: every table and view by row count and content digest (the fingerprint recipe, **unfiltered**), eight schema-shape digests, every bucket object by bytes actually read, and `probe_guards`. |
| tests | `conftest.py` (re-exports the DB suite's migrated-clone fixtures), `test_schema_coverage.py` (the loud guard), `test_synthetic_drill_seed.py`, `test_synthetic_drill_compare.py`; existing recovery tests updated to head `0028`. |

## 4. The loud guard, and its mutations

`tests/integration/recovery/test_schema_coverage.py` runs against a real migrated PostgreSQL (the DB suite's template clone,
one per test, dropped afterwards). It fails when **any** of these exists that the tooling neither covers nor exempts in writing:

* the alembic head is not `HEAD`; a table or view is not declared; a `norm*` table is not in the exemption list (and the test runs
  the frozen fingerprint SQL itself and requires it to count exactly `FINGERPRINTED_TABLES`);
* a trigger is missing, extra, disabled, on a narrower event set (`BEFORE DELETE` instead of `BEFORE UPDATE OR DELETE`), or its
  deferral differs; a constraint is dropped or not validated; an index is dropped; a sequence is behind its rows;
* a Blob-reference column exists that `audit_blob_references` does not name, by foreign key under any name, by `*blob_id` name
  without a foreign key, or a second one on a declared table; or a declared one disappeared.

Red first: the first version of the test (the existing `audit_blob_references` on an empty migrated database) failed on the
unchanged tooling with `BlobReferenceAuditRefused: migration head differs`, then with the head bumped by
`unknown=[('public','price_list_revision','blob_id')]` (section 1). Each guard is shown failing under a quoted mutation of the
**tooling**. Each row is one run of the focused test files with `pytest -x` (so "1 failed" is the first red test, not the only one),
on the committed tree with one line changed and restored afterwards (`git status` clean). M1–M15 ran at `9b07f370`, M16–M20 at the
next commit; M20 first **survived** and is shown twice:

```
M1 blob audit forgets price_list_revision as a source
   mutation: '("public", "price_list_revision", "blob_id"),' -> ''
   exit=1  1 failed, 2 passed in 2.95s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_blob_reference_catalog_equals_the_audits_closed_set
M2 declared head left at 0027
   mutation: 'HEAD = "0028_classification_corrections"' -> 'HEAD = "0027_optimisation_proposals"'
   exit=1  1 failed in 0.11s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_declared_head_is_the_alembic_head
M3 declaration forgets one immutable trigger
   mutation: '("work_assignment_event", "trg_work_assignment_event_immutable", "am_i' -> ''
   exit=1  1 failed, 1 passed in 3.22s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_declared_schema_equals_the_migrated_schema
M4 a norm table drops out of the exemption list
   mutation: '"norm_retrieval_set", "norms_snapshot",\n))\n\n#: Tables whose rows' -> '"norms_snapshot",\n))\n\n#: Tables whose rows'
   exit=1  1 failed, 5 passed in 2.32s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_frozen_fingerprint_counts_exactly_the_declared_tables
M5 audit stops checking that triggers are enabled
   mutation: 'if row["enabled"] != "O")' -> 'if False)'
   exit=1  1 failed, 8 passed in 3.21s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[disabled trigger]
M6 audit stops checking sequences against rows
   mutation: 'if (highest or 0) > (last or 0):' -> 'if False:'
   exit=1  1 failed, 22 passed in 4.69s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_a_sequence_behind_its_rows_is_refused
M7 coordinator stops comparing the record's table set
   mutation: 'if set(record["fingerprint"]["tables"]) != FINGERPRINTED_TABLES:' -> 'if False:'
   exit=1  1 failed, 7 passed in 0.10s
   first: FAILED tests/integration/recovery/test_isolated_restore_drill.py::test_a_record_with_another_table_set_stops_before_database_restore[table-missing]
M8 coordinator skips the restored-schema audit
   mutation: 'schema = audit_restored_schema(restored.session)' -> 'schema = RestoredSchemaAudit(0, 0, 0, 0, ())'
   exit=1  1 failed in 0.08s
   first: FAILED tests/integration/recovery/test_isolated_restore_drill.py::test_coordinator_restores_db_before_target_write_then_reads_all_target_bytes
M9 fixture accepts any fingerprint table set
   mutation: 'if set(tables) != FINGERPRINTED_TABLES:' -> 'if False:'
   exit=1  1 failed, 7 passed in 0.15s
   first: FAILED tests/integration/recovery/test_synthetic_drill_fixture.py::test_fingerprint_lines_must_name_exactly_the_declared_tables[table-missing]
M10 runner pinned back to head 0023
   mutation: 'or record["migration_head"] != HEAD or' -> 'or record["migration_head"] != "0023_norm_citation'
   exit=1  1 failed, 4 passed in 0.12s
   first: FAILED tests/integration/recovery/test_synthetic_drill_runner.py::test_nonempty_bucket_refuses_before_engine_or_restore
M11 blob audit stops checking price-list facts
   mutation: 'if _declared_fact(row, source=source) != actual:\n            raise Blo' -> 'pass\n    counts.append(("price_list_revision"'
   exit=1  1 failed, 26 passed in 0.09s
   first: FAILED tests/integration/recovery/test_blob_reference_audit.py::test_broken_references_refuse[price_list_digest-disagrees with content identity]
M12 guard probe never tries a DELETE
   mutation: '("delete", f\'DELETE FROM public."{name}" WHERE {one}\'),' -> ''
   exit=1  1 failed, 4 passed in 30.18s
   first: FAILED tests/integration/recovery/test_synthetic_drill_seed.py::test_the_guard_probe_is_refused_everywhere_and_notices_a_dead_or_narrowed_trigger
M13 guard probe counts any error as a refusal
   mutation: 'outcome = str(getattr(error.orig, "sqlstate", "") or "error")' -> 'outcome = "AM003"'
   exit=1  1 failed, 4 passed in 24.65s
   first: FAILED tests/integration/recovery/test_synthetic_drill_seed.py::test_the_guard_probe_is_refused_everywhere_and_notices_a_dead_or_narrowed_trigger
M14 compare ignores the trigger shape
   mutation: '"triggers": """' -> '"triggers_ignored": """'
   exit=1  1 failed in 2.19s
   first: FAILED tests/integration/recovery/test_synthetic_drill_compare.py::test_two_clones_of_one_migrated_schema_are_equal
M15 compare stops hashing object bytes
   mutation: 'profile[key] = [size, hashlib.sha256(data).hexdigest()]' -> 'profile[key] = [size, "0" * 64]'
   exit=1  1 failed, 11 passed in 4.71s
   first: FAILED tests/integration/recovery/test_synthetic_drill_compare.py::test_buckets_compare_by_key_size_and_the_bytes_actually_read
M16 audit stops comparing trigger deferral
   mutation: 'if row["deferred"] != (row["trigger_name"] in DEFERRED_TRIGGERS))' -> 'if False)'
   exit=1  1 failed, 7 passed in 3.46s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[deferred co-commit trigger made immediate]
M17 audit stops comparing constraint counts
   mutation: 'if totals != CONSTRAINT_COUNTS:' -> 'if False:'
   exit=1  1 failed, 10 passed in 4.02s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped check constraint]
M18 audit stops checking index count and validity
   mutation: 'if index["total"] != INDEX_COUNT or index["unusable"]:' -> 'if False:'
   exit=1  1 failed, 12 passed in 3.69s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped index]
M19 audit stops comparing views
   mutation: '_difference("views", set(VIEWS), found_views),' -> ''
   exit=1  1 failed, 14 passed in 4.18s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped view]
M20a audit accepts a non-public relation  [BEFORE the test existed: the mutant SURVIVED, exit=0, 29 passed]
   mutation: 'if any(row["schema_name"] != "public" or row["partition"] for row in r' -> 'if False:'
   exit=0  29 passed in 7.38s
   first: 
M20b same mutation after adding the case 'relation in another schema'
   mutation: 'if any(row["schema_name"] != "public" or row["partition"] for row in r' -> 'if False:'
   exit=1  1 failed, 17 passed in 3.91s
   first: FAILED tests/integration/recovery/test_schema_coverage.py::test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[relation in another schema]
```

Mutating the **schema** instead (15 cases in `_SCHEMA_MUTATIONS`, 4 in `_BLOB_REFERENCE_MUTATIONS`, one for the sequence) is in the
same test file: each clone is audited unmutated first, then mutated, and must be refused with the specific message.

## 5. The dataset (`synthetic_drill_seed.py`, recorded provider, no spending)

Provider-selecting environment names are removed before anything is imported; the run uses the checked-in recording; both
endpoints must be loopback; the seed refuses a lane that already holds a project (most of what it writes can never be deleted).
One call, from a fresh migrated lane, **6.8 s**:

```
{"accounts": 3, "decisions": 3, "findings": 3, "optimisation_decisions": 2, "optimisation_proposals": 4, "price_lists": 2, "run_id": "run_01M5EPT1SYA291WMP8JV17ATTP", "run_state": "published", "versions": 4, "work_assignments": 2}

real	0m6.778s
user	0m5.226s
sys	0m0.253s
```

= 3 accounts (admin, two experts); 4 projects (one empty); 3 documents and 4 versions (the school's document has two);
a classification of version 1 as design stage (`P`/`AR`) and its append-only **correction** to working documentation
(`R`/`AR`, revision 2), plus two more classifications; 1 finished recorded run (`published`, 4 stage results, 1 model call,
3 findings with grounded evidence) and 3 expert decisions on them; 2 work assignments with 5 events; 2 price-list revisions
(24 positions), 2 vendor-list revisions; 1 optimisation pass with 4 proposals and 2 decisions. The source bucket holds
**23 objects, 271,413 bytes**, all `available` Blobs: 2 PDFs, 4 markdown, 13 JSON including `prepared_text_layer`,
`geometry_page_crops`, `geometry_block_index`, 2 PNG **crop images**, 2 CSV price lists.
One honest limit: the optimisation pass reads the run's saved text through its own `SavedTextReader` port, and the AR
baseline has no specification page, so that port is answered with the same one-page Form-7 fixture the optimisation suite
uses, keyed to the real published run. Everything the pass wrote is real; the text it matched is a fixture.

## 6. The real drill

**Lane** (the only allocation): `FOUNDATION_INSTANCE=auditmanager-recovery-rebase`, PostgreSQL `127.0.0.1:57730`, MinIO
`61350/61351`, images `auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9` (`sha256:4c34fc74…`), `auditmanager-minio:RELEASE.2025-10-15T17-29-55Z-9e49d5e`
(`sha256:0d80ac74…`), volumes `auditmanager-recovery-rebase-{postgres,s3}-data`, PostgreSQL 17.11 client tools
`/usr/lib/postgresql/17/bin`. **Source** = the lane database `auditmanager_recovery_rebase` and bucket
`auditmanager-recovery-rebase`. **Target** = a fresh database `auditmanager_w58_target_final` and an empty bucket
`auditmanager-w58-synthetic-target-final` **on the same two containers** (the brief allocated one port pair; the runner's
own guards — distinct instance and bucket names, empty bucket, empty database, loopback, PG 17 tools — hold). That is database-
and bucket-level isolation, not a second stack (section 8).

| Step | Command (details in section 9) | Time |
|---|---|---|
| source fingerprint (frozen SQL) | `sed` the marked block out of `infra/deploy/copy-serve.sh` into `psql` | 0.13 s |
| dump | `pg_dump --format=custom --no-owner --no-privileges` → 400338 bytes; `pg_restore --list`; fingerprint again, `cmp` equal; **41** tables | 0.24 s |
| copy | `python -m scripts.recovery.synthetic_drill_fixture … --source-env` (list, conditional-read, rehash, seal 23 objects) | 1.66 s |
| offline preflight | `python -m scripts.recovery.offline_restore_preflight` | 0.07 s |
| isolated restore + audit + target write + readback | `python -m scripts.recovery.synthetic_drill_runner` (atomic `pg_restore --single-transaction --exit-on-error`, fingerprint, schema audit, Blob audit, bind, 23 puts, 23 full streams) | 2.78 s |

Runner result (`result.json`):

```
{
 "dump_sha256": "0f7250aeb8cbb242419da4efcb0e2ba518efa7a58c156f15b2d13dbfd26c6bb0",
 "record_sha256": "74a55f3c4b4780f7d07c3342959c58a55054f86757ca98b637e8aa22a53e7e03",
 "schema": {
  "guarded_tables": 29,
  "sequences": {
   "audit_event_sequence_no_seq": [
    24,
    24
   ],
   "expert_decision_event_sequence_no_seq": [
    3,
    3
   ],
   "norm_chunk_norm_chunk_pk_seq": [
    null,
    null
   ],
   "norm_document_norm_document_pk_seq": [
    null,
    null
   ],
   "norm_embedding_norm_embedding_pk_seq": [
    null,
    null
   ],
   "norm_paragraph_norm_paragraph_pk_seq": [
    null,
    null
   ],
   "release_pk_seq": [
    null,
    null
   ]
  },
  "tables": 55,
  "triggers": 72,
  "views": 4
 },
 "source_counts": {
  "analysis_artifact_publication": 10,
  "input_manifest_entry": 13,
  "norm_custody_admission": 0,
  "norm_custody_binding": 0,
  "norm_retrieval_set": 0,
  "price_list_revision": 2
 },
 "synthetic_isolated_drill": true,
 "target_blob_bytes": 271413,
 "target_blob_facts_sha256": "3c45412502c6711d81c26c170345c94a05f5953326170f4fd9bcd1a9792e419a",
 "target_blobs": 23,
 "target_object_bytes": 271413,
 "target_objects": 23
}
```

The runner's own verdict: restored fingerprint equals the record's (41 tables, count and digest each); schema audit **55 tables,
4 views, 72 triggers, 29 guarded tables**, every sequence at its table's maximum (`audit_event` 24/24, `expert_decision_event` 3/3);
Blob audit saw `input_manifest_entry` 13, `analysis_artifact_publication` 10, `price_list_revision` 2 (and custody/retrieval sets 0);
**23 target objects = 23 target Blobs, 271,413 bytes each way**, each streamed through the public storage port with digest and size
checked.

### Independent cross-check (`synthetic_drill_compare`, `--probe-target-guards`)

```
{
 "differences": [],
 "guard_probe": {
  "accepted_or_other": [],
  "empty_tables": [
   "finding_observation_norm_citation",
   "norm_current_snapshot_event",
   "norm_custody_binding",
   "norm_document",
   "norm_paragraph",
   "norm_retrieval_set",
   "norms_snapshot",
   "release",
   "release_revision"
  ],
  "refused": 40,
  "tables": 29
 },
 "informational": [
  "/constraints_exact_text: source [657, '941f54ec665c10c76a59e1012b9966b90450b085c938be1a568001db5b05583b'] != target [657, '265497f3b893b70c9f00dfb28e7b1e7079d6c68aa099a5f4548289b0429fa035']"
 ],
 "object_bytes": 271413,
 "objects": 23,
 "shape_categories": 8,
 "table_rows": 227,
 "tables": 55,
 "views": 4
}
```

Every relation, source against the restored target (rows, content digest of all rows as text; **includes the 14 `norm*` tables the
stand fingerprint exempts**; 227 rows in all):

| relation | rows source | rows target | digest (first 12) | equal |
|---|---|---|---|---|
| account_release_mark | 0 | 0 | e3b0c44298fc | yes |
| alembic_version | 1 | 1 | fd6e1e2109a8 | yes |
| analysis_artifact_publication | 10 | 10 | f3848a898658 | yes |
| app_user | 4 | 4 | 291db12fc375 | yes |
| app_user_role | 5 | 5 | 76ba063d9682 | yes |
| attempt | 1 | 1 | 1445f0f472ac | yes |
| audit_event | 24 | 24 | 7411e83c5d5e | yes |
| audit_run | 1 | 1 | c0fb7d5ccd52 | yes |
| blob | 23 | 23 | 661583168823 | yes |
| command_record | 10 | 10 | 0c84a1ab6c32 | yes |
| contract_state_transition | 51 | 51 | e3ce7184b7bb | yes |
| document | 3 | 3 | 3257bd842aea | yes |
| document_version | 4 | 4 | 2127de69788b | yes |
| document_version_classification | 3 | 3 | aee813211d37 | yes |
| document_version_classification_correction | 1 | 1 | 9754c68ac27e | yes |
| execution_control | 1 | 1 | c3bf58648966 | yes |
| expert_decision_event | 3 | 3 | cbd7cf8c3816 | yes |
| finding | 3 | 3 | 95639abcba1f | yes |
| finding_evidence | 5 | 5 | 8e082618d7ed | yes |
| finding_observation | 3 | 3 | 8d62faf96602 | yes |
| finding_observation_norm_citation | 0 | 0 | e3b0c44298fc | yes |
| input_manifest_entry | 13 | 13 | 05128367c558 | yes |
| job | 1 | 1 | bebf53f3cc7d | yes |
| lease | 1 | 1 | ab46a79740d9 | yes |
| model_call | 1 | 1 | 20ec97a9ed1e | yes |
| norm_chunk | 0 | 0 | e3b0c44298fc | yes |
| norm_chunk_build | 0 | 0 | e3b0c44298fc | yes |
| norm_current_snapshot | 0 | 0 | e3b0c44298fc | yes |
| norm_current_snapshot_event | 0 | 0 | e3b0c44298fc | yes |
| norm_custody_admission | 0 | 0 | e3b0c44298fc | yes |
| norm_custody_binding | 0 | 0 | e3b0c44298fc | yes |
| norm_document | 0 | 0 | e3b0c44298fc | yes |
| norm_embedding | 0 | 0 | e3b0c44298fc | yes |
| norm_embedding_build | 0 | 0 | e3b0c44298fc | yes |
| norm_embedding_profile | 1 | 1 | d67d95d0cf78 | yes |
| norm_paragraph | 0 | 0 | e3b0c44298fc | yes |
| norm_repair_call | 0 | 0 | e3b0c44298fc | yes |
| norm_retrieval_set | 0 | 0 | e3b0c44298fc | yes |
| norms_snapshot | 0 | 0 | e3b0c44298fc | yes |
| optimisation_pass | 1 | 1 | c0a464ee8b74 | yes |
| optimisation_proposal | 4 | 4 | 0222009fcb03 | yes |
| optimisation_proposal_decision | 2 | 2 | 314c15d6186c | yes |
| price_list_position | 24 | 24 | a5c055a8f396 | yes |
| price_list_revision | 2 | 2 | 7ec22e8f6114 | yes |
| project | 4 | 4 | abebaca9597b | yes |
| provider_call_effect | 1 | 1 | f6ceebf966c8 | yes |
| registration_request | 0 | 0 | e3b0c44298fc | yes |
| release | 0 | 0 | e3b0c44298fc | yes |
| release_revision | 0 | 0 | e3b0c44298fc | yes |
| stage_result | 4 | 4 | c9caee3c7319 | yes |
| vendor_list_entry | 3 | 3 | c4cb5528d62d | yes |
| vendor_list_revision | 2 | 2 | 75a12eaeb7d5 | yes |
| work_assignment | 2 | 2 | 65dfbc0ab859 | yes |
| work_assignment_event | 5 | 5 | 80dca97b741c | yes |
| worker | 0 | 0 | e3b0c44298fc | yes |
| finding_current_verdict (view) | 3 | 3 | b61e21dcaff0 | yes |
| version_classification_current (view) | 3 | 3 | 222f2890cd04 | yes |
| version_classification_revision (view) | 4 | 4 | 51c088b44825 | yes |
| work_assignment_current (view) | 2 | 2 | cef6343c9398 | yes |

Schema shape, source against target:

```
shapecolumns: 606 items / 606 items, equal
shape constraints: 657 items / 657 items, equal
shape extensions: 2 items / 2 items, equal
shape functions: 145 items / 145 items, equal
shape indexes: 153 items / 153 items, equal
shape sequences: 7 items / 7 items, equal
shape triggers: 72 items / 72 items, equal
shape views: 4 items / 4 items, equal
```

**Guard probe** on the restored target (always rolled back; afterwards the same comparison is still equal): for each of the
29 tables that carry an immutable/append-only guard, one real row was UPDATEd and DELETEd inside a savepoint; all
40 attempts on the 20 populated tables (including all 11 tables added by `0024`–`0028`) were refused with the guard's own
SQLSTATE (`AM002`/`AM003`). Not probeable because empty in this dataset: finding_observation_norm_citation, norm_current_snapshot_event, norm_custody_binding, norm_document, norm_paragraph, norm_retrieval_set, norms_snapshot, release, release_revision.

**One benign difference, reported not hidden.** 28 CHECK constraints print differently on the restored side
(`/constraints_exact_text`): `pg_dump` re-emits them as text and the restore's parser flattens `(a AND b) AND c` into
`a AND b AND c`; names, operands, literals, validation and count are identical. The comparison therefore normalises parentheses and
whitespace for constraints only, and lists the exact-text mismatch as informational. This looseness (it cannot see a precedence
change that only moves parentheses) is stated in the module.

## 7. Verification of the change

See section 10 for the commands and statuses.

## 8. Not claimed / risks

* **One server, two databases.** Source and target share the lane's PostgreSQL and MinIO containers. The runner's guards held,
  but a drill with a second compose project (own volumes) was not run: the brief allocated one port pair and the host is at its
  memory and disk limit. The synthetic-drill document's own operator lane remains the way to get two stacks.
* **The norms corpus is not in the dataset.** All `norm*` tables are empty (one `norm_embedding_profile` row from the migration), so
  `norm_custody_admission`, `norm_custody_binding` and `norm_retrieval_set` — the Blob-bearing norm tables — were audited live only on
  zero rows; their Blob arms are covered by the fake-session tests as before. The stand fingerprint exempts `norm*` by design;
  the independent comparison covers them but they are empty. A drill with an imported corpus (the W54 norms path) is separate work.
* **Privileges and roles are not restored** (`--no-owner --no-privileges` is the pinned restore); the lane uses one role. Re-granting
  an application role on a stand is not exercised.
* The copy is pulled from a **quiescent** source bucket by an operator who guarantees no writers ran; the tooling detects a
  changed object (conditional read, rehash) but cannot prove quiescence.
* Row and Blob parity is proved for this synthetic dataset (227 rows, 23 objects). It is not W54-scale (the W54 stand held 28,920
  objects) and not an attested stand copy; `real_data_marker` is false and the record names a synthetic source.
* The declaration pins counts that every future migration changes (`CONSTRAINT_COUNTS`, `INDEX_COUNT`, `TRIGGERS`). That is
  the point (a migration must fail the guard until its owner extends the declaration), and it is also a cost: the first line
  of every future migration's checklist.

## 9. Reproduce

Lane stack and `.env` as in the common brief (`make up check-services migrate check-db` with `FOUNDATION_PYTHON=/usr/bin/python3.12`).
Needs `MemAvailable ≥ 2.5 GiB`, load < 8, a few MiB of disk. Then, from the worktree:

```
PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_seed --env .env      # fresh lane only
#!/usr/bin/env bash
# usage: drill.sh <label> <source .env> ; runs dump -> mirror -> isolated restore -> audit -> readback
set -euo pipefail
umask 077
LABEL="$1"; SRC_ENV="$2"
REPO=<worktree>
S=<scratch>
PG17=/usr/lib/postgresql/17/bin
cd "$REPO"
get() { grep -E "^$1=" "$SRC_ENV" | head -1 | cut -d= -f2-; }
export PGPASSWORD="$(get POSTGRES_PASSWORD)"
HOST=127.0.0.1; PORT="$(get POSTGRES_PORT)"; USER_="$(get POSTGRES_USER)"; SRC_DB="$(get POSTGRES_DB)"
DRILL_ROOT="$S/drill-$LABEL"; rm -rf "$DRILL_ROOT"; mkdir -m 700 "$DRILL_ROOT"
cp "$SRC_ENV" "$DRILL_ROOT/source.env"; chmod 600 "$DRILL_ROOT/source.env"
now() { date +%s.%N; }
lap() { printf 'TIMING %-28s %6.2f s\n' "$1" "$(echo "$(now) - $2" | bc)"; }
SRC_PG=("$PG17/psql" --no-psqlrc --quiet --no-align --tuples-only --set ON_ERROR_STOP=1 -h $HOST -p $PORT -U $USER_ -d "$SRC_DB")
FPRINT() { sed -n '/^-- >>> stand-fingerprint-v1$/,/^-- <<< stand-fingerprint-v1$/p' infra/deploy/copy-serve.sh | "${SRC_PG[@]}"; }
T=$(now); FPRINT > "$DRILL_ROOT/fingerprint.lines"; lap "source fingerprint" $T
T=$(now); "$PG17/pg_dump" --format=custom --no-owner --no-privileges -h $HOST -p $PORT -U $USER_ -d "$SRC_DB" --file "$DRILL_ROOT/source.dump"; lap "pg_dump" $T
"$PG17/pg_restore" --list "$DRILL_ROOT/source.dump" > /dev/null
FPRINT > "$DRILL_ROOT/fingerprint-again.lines"; cmp "$DRILL_ROOT/fingerprint.lines" "$DRILL_ROOT/fingerprint-again.lines"
echo "dump bytes: $(stat -c %s "$DRILL_ROOT/source.dump"); fingerprint tables: $(wc -l < "$DRILL_ROOT/fingerprint.lines")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
T=$(now); PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_fixture \
  --dump "$DRILL_ROOT/source.dump" --fingerprint-lines "$DRILL_ROOT/fingerprint.lines" \
  --source-env "$DRILL_ROOT/source.env" --output-root "$DRILL_ROOT/copy" --stamp "$STAMP" \
  --instance "auditmanager-w58-synthetic-source-$LABEL" --tree-sha "$(git rev-parse HEAD)" | tee "$DRILL_ROOT/fixture.json"; lap "copy (mirror from bucket)" $T
T=$(now); PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.offline_restore_preflight "$DRILL_ROOT/copy/$STAMP" "$DRILL_ROOT/copy/objects"; lap "offline preflight" $T
# target: a fresh database and bucket on the same lane server, named for the runner's guards
TGT_DB="auditmanager_w58_target_$LABEL"; TGT_INSTANCE="auditmanager-w58-synthetic-target-$LABEL"
"$PG17/psql" --no-psqlrc -q -h $HOST -p $PORT -U $USER_ -d postgres -c "DROP DATABASE IF EXISTS $TGT_DB" -c "CREATE DATABASE $TGT_DB"
TGT_ENV="$DRILL_ROOT/target.env"
{
  echo "FOUNDATION_INSTANCE=$TGT_INSTANCE"; echo "POSTGRES_DB=$TGT_DB"; echo "POSTGRES_USER=$USER_"
  echo "POSTGRES_PASSWORD=$PGPASSWORD"; echo "POSTGRES_PORT=$PORT"
  echo "DATABASE_URL=postgresql+psycopg://$USER_:$PGPASSWORD@$HOST:$PORT/$TGT_DB"
  echo "MINIO_ROOT_USER=$(get MINIO_ROOT_USER)"; echo "MINIO_ROOT_PASSWORD=$(get MINIO_ROOT_PASSWORD)"
  echo "S3_ENDPOINT_URL=$(get S3_ENDPOINT_URL)"; echo "S3_API_PORT=$(get S3_API_PORT)"; echo "S3_CONSOLE_PORT=$(get S3_CONSOLE_PORT)"
  echo "S3_REGION=$(get S3_REGION)"; echo "S3_ACCESS_KEY_ID=$(get S3_ACCESS_KEY_ID)"; echo "S3_SECRET_ACCESS_KEY=$(get S3_SECRET_ACCESS_KEY)"
  echo "S3_BUCKET=$TGT_INSTANCE"
} > "$TGT_ENV"; chmod 600 "$TGT_ENV"
.venv/bin/python - "$TGT_ENV" <<'PY'
import sys, boto3
from botocore.client import Config
v = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
c = boto3.client("s3", endpoint_url=v["S3_ENDPOINT_URL"], region_name=v["S3_REGION"], aws_access_key_id=v["S3_ACCESS_KEY_ID"], aws_secret_access_key=v["S3_SECRET_ACCESS_KEY"], config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
c.create_bucket(Bucket=v["S3_BUCKET"]); print("target bucket created:", v["S3_BUCKET"])
PY
T=$(now); PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_runner \
  --copy-dir "$DRILL_ROOT/copy/$STAMP" --objects-root "$DRILL_ROOT/copy/objects" \
  --target-env "$TGT_ENV" --pg17-bin "$PG17" > "$DRILL_ROOT/result.json"; lap "isolated restore drill (runner)" $T
cat "$DRILL_ROOT/result.json"
echo "$STAMP" > "$DRILL_ROOT/stamp"
PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_compare \
  --source-env <drill>/source.env --target-env <drill>/target.env --probe-target-guards
```

## 10. Checks

All on the lane stack named in section 6, one pytest process at a time, `.venv/bin/python` of the shared interpreter, no `make gate`.

| Check | Command | Status |
|---|---|---|
| recovery suite, in full | `.venv/bin/python -m pytest tests/integration/recovery -q` | **239 passed**, 36.9 s, exit 0 (was 191 offline tests before this lane; the DB-backed ones need the stack) |
| contract suite, official ignores | `.venv/bin/python -m pytest tests/contract -q --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **941 passed, 19281 subtests passed**, 154 s, exit 0 (run at `9b07f370`; the only later change is one added case in `test_schema_coverage.py` and this document) |
| red step | `pytest tests/integration/recovery/test_schema_coverage.py` on the unchanged tooling | 1 failed: `BlobReferenceAuditRefused: migration head differs`; with the head bumped: `unknown=[('public','price_list_revision','blob_id')]` |
| mutations of the tooling | `scratchpad/mutate.py` (20 mutants, quoted in section 4) | 19 killed first time; M20 **survived**, the case `relation in another schema` was added, then killed |
| real drill | section 6 | `exit 0`, 23/23 objects and Blobs, 55 tables / 4 views equal, 72 triggers equal |
| `git diff --check` | `git diff --check` | exit 0 |

Hotspot proof: `git diff --name-status ff58bdd1 HEAD` touches only `scripts/recovery/**` (the recovery package: no
`src/auditmanager/recovery` exists, the tooling lives here), `tests/integration/recovery/**` and this document. No file under
`contracts/**`, `db/migrations/**`, `web/**`, dependency or lock files, `CURRENT_STATE.md`, `DEBT_REGISTER.md` was touched; no ref,
tag, `origin/*` or the stand was touched, nothing was pushed. No migration or contract change was needed: every gap was in the
tooling's declarations.

Skipped: `make gate`; every integration suite outside `tests/integration/recovery`; the web battery; a drill on a second compose
stack; a drill with an imported norms corpus (section 8).
