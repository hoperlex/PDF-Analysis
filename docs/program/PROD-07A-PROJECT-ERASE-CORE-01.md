# PROD-07A-PROJECT-ERASE-CORE-01 — report

Task file: [`tasks/PROD-07A-PROJECT-ERASE-CORE-01.md`](tasks/PROD-07A-PROJECT-ERASE-CORE-01.md). Base `8453869731599e8f5815efb919859bd0159c9342` (`integration/ar-close-1026`), branch `agent/prod-07a-project-erase-core-01`. Plan item `PROD-07` (first half), `ADR-0022` section 3, `R-146c`, `R-146o`, `R-146aj`.

## 1. Result

`scripts/recovery/project_erase.py` is the operator tool that erases **one** project. `python -m scripts.recovery.project_erase --database D --bucket B --project prj_...` prints a plan and its SHA-256 and changes nothing. `--apply --plan-sha256 <digest> --actor <admin login> --reason <code> --owner-permission-ref "<text>" --dump-dir DIR` removes, in one transaction, every row reachable from the project by foreign key (31 tables, read from the catalog), the idempotency receipts of those rows and the Blob rows only this project references; then deletes their objects by exact key; then appends the completion event. `--resume era_...` finishes an erase that committed and did not complete. Four phases exactly as `ADR-0022` has them, journalled as `erasure.requested` and `erasure.completed` (`aggregate_type` `ErasureRequest`, `aggregate_id` `era_<ULID>`), with `manifest_sha256` in both. `product_purge.py` keeps the `erasure.` family (one prefix).

Measured on the lane stack: **212 tests pass** (81 unit, 128 integration, 3 for the two shapes the stand in miniature lacks); **44 guards, each shown failing**; sixteen source-level edits of the behaviour that is not a guard, each red.

## 2. Files

| path | change |
| --- | --- |
| `scripts/recovery/project_erase.py` | new: the tool (1,577 lines, 44 guard blocks) |
| `scripts/recovery/product_purge.py` | `erasure.` added to `KEEP_EVENT_PREFIXES` and the comment above it; nothing else (the 27 guard blocks are untouched) |
| `tests/integration/recovery/test_project_erase.py` | new: 128 tests (declaration, plan, erase of four projects, second apply, crash points, re-upload, owner/permission, purge after erase, 44 guards x 2) |
| `tests/integration/recovery/test_project_erase_shapes.py` | new: 3 tests (an executor task is work in flight and goes with the project; an AR v3 group goes with its members and receipt) |
| `tests/unit/recovery/test_project_erase_pure.py` | new: 81 tests (deletion order, canonical forms, argument guards and their mutants) |
| `docs/program/tasks/PROD-07A-PROJECT-ERASE-CORE-01.md`, this file | new |

No existing test was modified or weakened (**before and after of modified tests: none**). `schema_coverage.py` is not edited: no table, trigger or Blob column is added.

## 3. How it works

**Scope by foreign-key closure, not a hand list.** `load_closure` reads `pg_constraint`: the closure of `project` under "is referenced by" is 31 tables (all PRODUCT tables but `worker`). `derive_scope` is one recursive query: a row is in the project when **any** of its foreign keys points at a row that is. The cycles (`document`/`document_version`, `job`/`attempt`, `finding`/`finding_observation`) are deleted each in one statement (data-modifying CTEs; NO ACTION is checked at the end of the statement); the rest in an order computed from the graph (`deletion_order`, strongly connected components, deterministic). A table in neither the closure nor `{worker}`, a KEEP or MIXED table that references the closure, or a head different from `schema_coverage.HEAD` stops the tool before it touches anything.

**Cross-project references.** A row of the project that references a row outside it is accepted only when that row belongs to no project (the global vendor list: its table has a direct `project_uid` and it is NULL). Anything else (a run that re-audits another project's run) is refused as `scope-is-pure`: erasing would take another project's data or leave a dangling reference.

**Receipts.** `command_record` rows of the erased rows: those a row of the project references (`command_id` of a run, a group, a decision, a proposal decision) and those whose `outcome` names the identity of a row of the project (a `create_project` receipt names the project, an upload the version, a price list the revision). A receipt of a KEEP command type is refused (`receipts-are-product-commands`). Left behind, a receipt blocks the same idempotency key for the project that comes back (`idempotency_key_reuse`; a test shows it).

**Blobs.** Candidates are the Blobs the project's rows reference (the closed set of `blob_reference_audit`); a Blob any other row or any KEEP table also references is **shared** and stays with its object; the rest are **exclusive**. Exclusive Blobs go `available` to `erasure_pending` in phase 2; their `blob` rows are **deleted** in phase 4 (so a byte-identical upload declares a fresh row: tested end to end with the same idempotency key). Staged `temporary/` objects named by the project's publication rows are deleted too.

**Phase 2 in detail** (one transaction): catalog guards, advisory lock, `LOCK TABLE` (KEEP tables and `worker` in SHARE, the closure and the three mixed tables in SHARE ROW EXCLUSIVE), the plan re-derived and compared with the digest the operator was shown, `erasure.requested`, fingerprints (count and digest) of everything that must not change, the Blob move, the delete with ONE named trigger off at a time (only `am_immutable_row` and `am_append_only`), the same fingerprints again (they must be equal), the project's tables empty, the trigger state equal to what it was, the plan and the manifest written to `DIR/<era_id>/` and fsynced, commit. The two files are removed again if anything fails.

**Resume.** From the journal (`erasure.requested` of the id, no `erasure.completed`), the Blob rows in `erasure_pending` (their manifest digest must equal the one the event recorded; the manifest file, if present, must equal the regenerated bytes, if absent it is rewritten) and `plan.json` (its digest must equal the event's; it lists the staged objects). Phases 3 and 4 are idempotent: an absent key counts as done.

**Idempotency.** After a finished erase the project has no rows; `--apply` (or a dry run) finds `erasure.completed` for it and exits 0 with "nothing to do", writing nothing. An unfinished erase is named: "resume it with --resume era_...".

## 4. Premise result

The premise (task file P-01 to P-10) was re-read on the base. **The ADR and the schema do not disagree materially.** Three places where the ADR is silent, and what the lane chose, are in section 5 (D3, D5, D6).

## 5. Decided by the lane

- **D1** The dry run does not need `--owner-permission-ref`; `--apply` and `--resume` refuse without it. `R-146aj` forbids erasing without the owner's permission; the dry run erases nothing and is how the operator obtains the plan to show the owner. Making the flag required for every mode is moving one guard block above one `return`.
- **D2** `--database` and `--bucket` are required and must equal the connected names (the purge's `names-match`), and a `PG*` variable refuses the run.
- **D3** How a receipt is tied to a project (the ADR says only "the idempotency receipts of the erased rows"): foreign key from the project's rows, and an outcome that names the identity of a row of the project (section 3).
- **D4** The cross-project rule of section 3 (`scope-is-pure`) is the lane's; the ADR assumes a project is a closed tree.
- **D5** An exclusive Blob that is not `available` (a failed or abandoned upload bound by an `abandoned` publication) cannot enter `erasure_pending` under the frozen state machine. The tool **refuses** the project and names the Blobs (`blobs-available`) instead of deleting a row the machine does not let go. Open for the owner/ADR: how such Blobs are reconciled before an erase (listed in section 9).
- **D6** Staged `temporary/` objects named by publication rows are deleted too (they hold client bytes); their keys live in `plan.json`. A resume without `plan.json` warns and deletes the Blob objects from the database's own list.
- **D7** The permission reference is recorded as `owner_permission_ref` in both events (an addition to the ADR's key list, asked for by the task), one line of at most 200 characters, as given.
- **D8** `correlation_id` of both events is the erase id.
- **D9** `manifest_sha256` is also in the `requested` event, so a resume can prove the pending set is the manifest without the file. The manifest file is byte-deterministic: `sha256sum manifest.json` is the digest in both events.
- **D10** The plan and manifest files are written inside the commit transaction, before COMMIT: a committed erase always has its record on disk.
- **D11** Work in flight is `created, queued, running, validating` runs, `queued, leased, running, retry_wait` jobs, `created, leased, running` attempts and `open, claimed` executor tasks. A queued run counts (the purge discards queued work; the ADR's erase refuses it). A test derives these sets from the schema's own CHECK constraints, so a migration that adds a state turns it red.
- **D12** `head-is-declared` (the ADR's "schema head equals the declared head") is a guard; the purge has none. Every migration therefore moves `schema_coverage.HEAD` before the erase runs on the new head (it already must, for `test_schema_coverage.py`).
- **D13** KEEP tables and `worker` are fingerprinted before and after inside the transaction under a SHARE lock (the ADR's "every keep row unchanged by count and digest"); writers wait up to 15 s (`PROJECT_ERASE_LOCK_TIMEOUT`) and then the run is refused.
- **D14** Trigger switching is per table (all DELETE guards of a table off while its rows are deleted, then on); a table with any other DELETE trigger refuses the run.
- **D15** `objects_deleted` and `objects_missing` of the completion event are those of the pass that finished the erase (after a resume, objects deleted before the crash count as missing).
- **D16** The module imports the classification and helpers of `product_purge.py` and `blob_reference_audit.py` instead of copying them; the wrapper must put all four files on the path.

## 6. Mutation proofs

### 6.1 The eight mandatory proofs

| proof | tests | what the mutation shows |
| --- | --- | --- |
| apply without the plan digest | scenario `plan-digest-required`; `test_deleting_one_guard_of_a_pair_leaves_the_other_refusing`; unit `test_an_apply_is_refused_without_the_plan_digest_it_was_shown` | refused (exit 3, nothing changed); without that guard the next one (`plan-unchanged`) still refuses; with both deleted the project is erased |
| a stale plan | scenario `plan-unchanged`; `test_a_stale_plan_is_refused_and_the_dry_run_after_it_is_the_new_plan` | the project renamed after the dry run: refused; the new dry run has a new digest and applies; without the guard the erase runs on a plan nobody approved |
| resume after a crash between phases | `test_a_crash_before_the_commit_...`, `..._between_the_commit_and_the_objects_...`, `..._between_the_objects_and_the_finish_...`, `test_resume_rewrites_a_lost_manifest_...`; the resume scenarios | the crash is raised between the phases; the state after it is asserted (project gone, Blobs `erasure_pending`, objects present or gone); `--resume` completes; a second resume says "already complete"; M16 turns the middle test red |
| a second apply | `test_a_second_apply_of_the_same_plan_finds_nothing_to_do_and_changes_nothing`; `test_without_the_already_erased_path_...` | exit 0, "nothing to do", the whole database and bucket equal, no second directory, no third event; with the path removed the second apply is a refusal, not a no-op |
| a second project's rows surviving | `test_an_erase_removes_exactly_one_project_and_nothing_else` x 4 projects; `test_the_isolation_assertions_see_a_leak_...`; `test_the_verification_sees_a_journal_event_or_a_blob_...` x 3 | every other project's rows (hand-written addressing, `row_to_json` digests), every KEEP table, every non-erasure event and every other object are equal before and after; a delete that also takes an empty project, an event or a Blob fails the assertions when `keep-unchanged` is deleted, and is refused when it is not |
| the re-upload | `test_a_byte_identical_upload_after_the_erase_succeeds_and_creates_a_fresh_blob_row`; two mutation tests | the erased bundle is uploaded again **with the same idempotency key**: not replayed, the same Blob ids, fresh rows (`created_at` after the erase), objects readable; with the rows left as `erased` the upload fails; with the receipts left it fails with `idempotency_key_reuse` |
| the owner-role guard | scenario `owner-may-write`; `test_the_apply_as_a_role_that_does_not_own_the_tables_...` | a role that owns nothing is refused at the plan and at the apply (exit 3, "does not own ... the migrator", nothing changed); without the guard the plan goes on |
| the permission reference | scenario `owner-permission-ref`; `test_no_apply_and_no_resume_runs_without_a_usable_owner_permission_reference` x 5; unit tests | missing, blank, 201 characters, a newline: refused for apply and resume; without the guard the project is erased with no permission recorded; the reference is recorded as given (Cyrillic included) |

### 6.2 Every guard block, deleted one at a time from a copy of the source

`test_the_guard_refuses_and_a_refusal_before_the_commit_changes_nothing` runs the real module (the refusal, its text, exit code, and for guards before the commit: the database and bucket digests equal, no file written, no event). `test_deleting_the_guard_removes_the_refusal_and_lets_the_harm_through` runs the copy without the block (the refusal text is gone and the harm happens). A scenario names a second guard (`without` / `also`) where two stand in a row so that each is shown on its own. A marker-count test fails if a guard has no scenario.

| # | guard | made true by | the copy without the guard |
| --- | --- | --- | --- |
| 1 | `relations-recognised` | a table in a stray schema | plan proceeds |
| 2 | `classification-total` | a table `zz_throwaway` nobody classified | plan proceeds |
| 3 | `declaration-matches-coverage` | `TABLES` lacking `project` | plan proceeds on an inconsistent declaration |
| 4 | `blob-columns-closed` | a new Blob-reference column in a KEEP table | plan proceeds, the new reference unclassified |
| 5 | `closure-is-product` | a KEEP table with a foreign key into `project` | the closure takes a KEEP table in |
| 6 | `blob-refs-in-closure` | `price_list_revision` cut out of the closure (its Blob column now sits outside it) | plan proceeds, those Blobs unaccounted |
| 7 | `delete-triggers-known` | an unknown BEFORE DELETE trigger on `document` | the erase runs past a guard it does not understand |
| 8 | `owner-may-write` | a role that owns nothing | plan proceeds (apply: a raw permission error) |
| 9 | `head-is-declared` | `alembic_version` at a later head | plan proceeds on a schema nobody declared |
| 10 | `receipts-are-product-commands` | an `approve_registration` receipt whose outcome names the project's version | the account-side receipt is deleted |
| 11 | `receipts-not-shared` | a run of another project that carries the receipt of this project's run | the delete hits the foreign key: exit 4 after the plan said it was safe |
| 12 | `bucket-unversioned` | versioning enabled on the bucket | a delete would only add a marker; plan proceeds |
| 13 | `norm-owned-key` | a classification bug that lists a corpus Blob as exclusive | the corpus object would be listed for deletion |
| 14 | `project-exists` | a well-formed id that is in no database | an empty plan with a digest; an apply would journal an erase of nothing |
| 15 | `scope-is-pure` | a run of another project that re-audits this project's run | the other project's run (and its graph) is erased too |
| 16 | `quiescent` | the project with a run in `created` | plan proceeds, the run erased from under its worker |
| 17 | `no-pending-erasure` | a Blob already in `erasure_pending` | a second erase starts over an unfinished one |
| 18 | `blobs-available` | an exclusive Blob in `verifying` | plan proceeds, the next guard refuses |
| 19 | `actor-is-active-account` | `--actor` an unknown login | exit 4 (no account to journal) |
| 20 | `actor-is-admin` | `--actor` an expert | an expert erases the project |
| 21 | `erase-lock-free` | another session holds the erase's advisory lock | two erases run at once |
| 22 | `lock-available` | a writer holds `ROW EXCLUSIVE` on `document`; timeout 300 ms | the raw lock error: exit 4 instead of a refusal |
| 23 | `plan-unchanged` | the project renamed after the dry run | the erase runs on a plan nobody approved |
| 24 | `blobs-pending` | an exclusive Blob moved out of `available` after the plan was taken | commit with a Blob that never entered `erasure_pending`; phase 4 stops (exit 4) |
| 25 | `keep-unchanged` | a delete that also changes `app_user` | an account row changed and committed |
| 26 | `project-emptied` | a delete that leaves the project row behind | an "erased" project still exists |
| 27 | `triggers-restored` | `trg_document_version_immutable` already off before the run | the erase commits with a trigger state different from the one it found |
| 28 | `object-key-shape` | a plan file naming an arbitrary key as a staging object | the stray object is deleted (the digest guard also removed) |
| 29 | `objects-unreferenced` | a row bound to a Blob waiting in `erasure_pending` | the referenced Blob's object is deleted (the later guard also removed) |
| 30 | `objects-gone` | a client whose delete does nothing | "done" while every object is still there |
| 31 | `finish-matches-manifest` | an unrelated Blob moved to `erasure_pending` before phase 4 | phase 4 deletes rows of a manifest that is not the pending set (the later guard also removed: the unrelated row stays pending) |
| 32 | `pending-unreferenced` | a row bound to a manifest Blob before phase 4 | the row delete hits the foreign key: exit 4 |
| 33 | `pending-cleared` | the same unrelated pending Blob | the erase completes with a Blob still `erasure_pending` |
| 34 | `erase-id-known` | `--resume` an id with no `erasure.requested` | exit 4 (index error) instead of a refusal |
| 35 | `resume-manifest-matches` | an unrelated Blob in `erasure_pending` at resume | the unrelated Blob's object is deleted (the file guard also removed) |
| 36 | `resume-manifest-file-matches` | `manifest.json` edited on disk | the erase completes with a manifest file whose digest is not the event's |
| 37 | `resume-plan-file-matches` | `plan.json` edited | the doctored plan is trusted; the stray object is deleted (the key-shape guard also removed) |
| 38 | `no-ambient-libpq` | `PGHOSTADDR` in the environment | the run goes on against whatever libpq resolves |
| 39 | `names-match` | typed database name differs | the run goes on against the connected database |
| 40 | `project-identity-shape` | `--project` given a name | the name reaches the database; refused one step later |
| 41 | `owner-permission-ref` | apply without the reference (also blank, 201 characters, a newline, a control character) | the project is erased with no permission recorded |
| 42 | `dump-dir-required` | apply without `--dump-dir` | exit 4 before anything is written (nothing changed) |
| 43 | `plan-digest-required` | apply without `--plan-sha256` | refused one guard later (`plan-unchanged`); with both deleted the project is erased |
| 44 | `reason-closed-list` | `--reason` free text | the text is written into the append-only journal |

### 6.3 The behaviour that is not a guard

Each edit was made to `project_erase.py`, the named tests were run, the file was restored (`git status` clean).

| # | the edit | red after the edit | the tests that went red |
| --- | --- | --- | --- |
| M1 | `deletion_order` returns the groups reversed (parents before children) | 6 failed, 1 passed | unit + the cycle/order test + the four-project erase test |
| M2 | `derive_scope` ignores the foreign keys of `input_manifest_entry` (its rows are not scoped) | 3 failed, 1 passed | the erase test: the rows stay, the delete hits a foreign key |
| M3 | `derive_receipts` looks only at foreign keys (receipts named by outcome are left) | 3 failed, 3 passed | the school erase, the receipts test and the re-upload test |
| M4 | `classify_blobs` treats a shared Blob as exclusive | 3 failed, 2 passed | the erase tests and the shared-Blob test (the kindergarten's Blob) |
| M5 | the requested event also carries the project name | 4 failed | the journal assertions (keys and client texts) in all four erase tests |
| M6 | `manifest_bytes` carries a clock reading | 5 failed, 4 passed | the determinism test, the resume tests (a rewritten manifest differs), the manifest-file guard scenarios |
| M7 | `plan_document` leaves the shared Blob list out of the digest | 1 failed, 21 passed | the unit digest test for `shared` |
| M8 | `delete_scope` never switches the guard triggers back on | 3 failed, 1 passed | the erase tests (trigger state compared before and after) |
| M9 | `phase_commit` takes no table locks | 2 failed | the `lock-available` scenarios (nothing stops a writer) |
| M10 | the plan leaves the staged `temporary/` objects out of the list | 1 failed, 3 passed | the school erase test (the staged object stays in the bucket) |
| M11 | the completion event is appended with the requested type | 6 failed | the erase tests, the crash/resume test, the second-apply test |
| M12 | the requested event is never appended | 6 failed | the same tests |
| M13 | `delete_scope` never switches a guard trigger off | 3 failed, 1 passed | the erase tests (the immutable-row trigger refuses the delete) |
| M14 | the manifest file is not written | 5 failed | the erase tests and the crash test |
| M15 | `executor_task` is dropped from `NON_TERMINAL_STATES` | 3 failed | the non-terminal-states test and the executor-task test |
| M16 | an absent object key is a failure instead of "done" | 2 failed, 3 passed | the crash-between-objects-and-finish resume test, the school erase |

Test-level mutations (the tool is patched inside the test): the second-apply path removed (a refusal instead of exit 0); the receipt step returning nothing (the same-key upload fails with `idempotency_key_reuse`); phase 4 leaving the rows as `erased` (the byte-identical upload fails); `delete_scope` also deleting an empty project, a custody event, a run-journal event or an orphan Blob, with and without `keep-unchanged`; `NON_TERMINAL_STATES` without `executor_task` (an open task no longer stops the erase); the keep prefix removed from the purge (the purge refuses the erasure events as unclassified).

## 7. Tests and counts

| command (from the lane worktree, `BS` as in the dispatch) | result |
| --- | --- |
| `pytest tests/unit/recovery tests/integration/recovery/test_project_erase.py tests/integration/recovery/test_project_erase_shapes.py` | 212 passed in 106.83 s (81 + 128 + 3), one private database clone per test |
| `pytest tests/integration/recovery/test_product_purge.py ..._executor_events.py ..._run_group.py test_schema_coverage.py tests/unit/runs/test_executor_choice.py` | 123 passed in 60.15 s (the edited tool's suites, unchanged) |
| `pytest tests/integration/recovery/test_product_purge_script.py` | 7 passed in 38.58 s |
| the governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see the lane's final message (run on the committed tree) |

Free disk stayed above 1.8 GiB throughout; every database, bucket and role a test made was dropped. Found, not made by this lane and left alone: five `a1_tpl_*` template databases (created 01:43 to 13:15 UTC) and 55 `*-tpl-*-c-*` buckets (created 13:16 to 13:17 UTC) from earlier sessions, hours before this lane's `.env` was copied (17:06 UTC).

## 8. What `infra/deploy/erase-project.sh` must do (not in this lane)

The wrapper waits for the database-role work (`PROD-04`). It is `purge-product-data.sh`'s sibling and must:

1. keep the purge wrapper's skeleton: `set -Eeuo pipefail`, the environment file, typed `--database` and `--bucket` equal to the configured ones, the compose file and the four modules present (`project_erase.py`, `product_purge.py`, `schema_coverage.py`, `blob_reference_audit.py` mounted read-only at `/purge/scripts/recovery` with `PYTHONPATH=/app/src:/purge`), refuse unknown options and more than one mode, guard markers and a test per guard (`tests/integration/composition`);
2. run the module inside the `api` image with `DATABASE_URL` set explicitly to **the migrator's URL** (`AD-02`: the api's own URL is the restricted role the tool refuses) and no `PG*` variable;
3. default to the dry run (`--project prj_...` only, prints the plan and `plan-sha256`); `--apply` needs `--project`, `--actor`, `--reason` (one of `client_request`, `end_of_engagement`, `test_data`, `other`), `--owner-permission-ref` and the digest, and shows the plan again and asks the operator to retype the project id and the digest;
4. mount a **writable** `--dump-dir` (`infra/deploy/dumps/erasures/`) and tell the operator to keep `<era_id>/plan.json` and `manifest.json` with the release record (the database holds only their digests). The tool writes the directory 0700 and the files 0600 (the manifest holds a fingerprint of every erased document, which the ADR keeps out of the database on purpose): run the container as the operator's uid, or chown the directory afterwards, so the operator can read what the tool wrote;
5. **take no `pg_dump` and no object mirror before the erase**, unlike the purge: a dump would keep the erased data. Say so, and that every existing dump, mirror and copy still holds it;
6. pass the exit codes through; on 4 after the commit print the `erase-id:` line and the exact `--resume era_... --actor ... --owner-permission-ref ... --dump-dir ...` command (a `--resume` mode of its own); on 3 with "could not lock" offer the purge wrapper's stop-the-worker-and-restart trap;
7. after success print the manifest path and `manifest-sha256`, the tool's closing list of what an erase does not reach, and the two rest-state queries of `ADR-0022` (`select count(*) from blob where state = 'erasure_pending'` is 0; `select count(*) from project where project_uid = '<id>'` is 0 and an `erasure.completed` event names it);
8. have a numbered runbook section in `DEPLOYMENT_RUNBOOK.md` (the owner's permission first, then the dry run, the apply, the verification, the manual copies) and the rehearsal on a restored copy (`PROD-17`).

## 9. Limits and what remains

- **Blobs not `available`** that only this project references stop the erase (D5). Needs an owner/ADR decision: a reconciliation step, or permission to delete such rows directly.
- **The KEEP fingerprint** inside the transaction reads every row of the norm corpus twice; the run time and the SHARE lock on accounts grow with the corpus. The dry run does not pay it. Measured only on the stand in miniature.
- **Receipts without an outcome** (`in_progress`, `failed`) name nothing and stay; a cross-project reference (a re-audit of another project's run) refuses the erase and needs a manual decision.
- **A resume without `plan.json`** cannot find the staged `temporary/` objects (it warns).
- **Not covered:** a versioned bucket beyond the refusal; a project large enough to make the `= ANY(array)` statements slow; the real wrapper, the runbook text and the rehearsal; the legal-hold question (`R-146aj`: the permission is recorded, never verified).
- **Debt-register candidates** (the integrator decides): the wrapper and runbook (`PROD-07` second half, after `PROD-04`); the non-`available` Blob question; the rehearsal (`PROD-17`); `PROD-22` for the clarifying edit of the frozen sentence in `contracts/domain/v1/state-machines.json`.

## 10. Integration notes

- Merge `--no-ff`; the lane touches no `src/`, contract, migration, `infra/`, composition root, ADR or register. The `product_purge.py` chain continues: the wrapper lane is the next editor of anything under `infra/**`.
- After the merge `KEEP_EVENT_PREFIXES` is `("norm_custody.", "executor.", "access.", "erasure.")`, which is what `ADR-0022` section 4 already says; no prose count changes.
- The tests import `purge_seed`, `purge_stand` and the `grouped` fixture of the purge's tests: renaming those breaks these tests, by design (one stand, one idiom).
- Each migration must move `schema_coverage.HEAD`, or the tool refuses (`head-is-declared`); a migration that adds a table decides it in `product_purge.py` (`D-213`), which `closure-is-product` and `classification-total` enforce for the erase as well.

## 11. Forbidden paths untouched

`git diff --name-only 8453869731599e8f5815efb919859bd0159c9342..HEAD` lists exactly these seven paths: `docs/program/PROD-07A-PROJECT-ERASE-CORE-01.md`, `docs/program/tasks/PROD-07A-PROJECT-ERASE-CORE-01.md`, `scripts/recovery/product_purge.py`, `scripts/recovery/project_erase.py`, `tests/integration/recovery/test_project_erase.py`, `tests/integration/recovery/test_project_erase_shapes.py`, `tests/unit/recovery/test_project_erase_pure.py`. Nothing under `contracts/`, `db/`, `src/`, `infra/`, `web/`, the ADRs, `DEBT_REGISTER.md` or `CURRENT_STATE.md`.
