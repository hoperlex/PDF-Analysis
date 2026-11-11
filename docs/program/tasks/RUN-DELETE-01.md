# Task RUN-DELETE-01 — deleteRun: a partial, failed or cancelled run leaves the run lists (contract 1.53.0, migration `0066`)

## Outcome
An expert or an administrator can delete a `partial`, `failed` or `cancelled` run from the run lists by one keyed call, `deleteRun` (`POST /runs/{run_id}/deletion`). The run leaves every
list, selection and display aggregate of runs; it, its stage results, findings, expert decisions and Blobs stay stored, and `getRunStatus` still answers it by its identity.

Owner order, 2026-11-11 (a hotfix to `main`): «Добавь возможность удалять частичные и непрошедшие прогоны в UI — они необъективны и их нужно удалять, чтобы уменьшить шум.»

Decided semantics (the integrator, from the order):

- deletion is a **tombstone**: one immutable row in `audit_run_deletion` (the run, who, when, the command receipt); there is no restore and no physical deletion;
- deletable states: `partial`, `failed`, `cancelled`; any other state is `409 state_transition_not_allowed` (`details.machine` `audit_run`, `current_state`, `requested_state` `delete`);
  a run already deleted, like an unknown one, is `404 not_found`;
- roles: `expert` and `admin` (the roles of `cancelRun`);
- the response is `RunStatus`; no new schema and no new error code.

This lane is the BACKEND + SEAL lane. A parallel WEB lane owns the UI (`web/src/features/delete-run/**`, `web/src/_pages/**`, `web/src/widgets/**`).

## Depends on
- none (the interface commit `a64725862` of this task is the base)

## Frozen inputs
- domain contract: 1.52.0 at the base; 1.53.0 after this seal (candidate revision 70)
- API contract: 1.52.0 (296 paths / 325 operations / 809 schemas) at the base; 1.53.0 (297 / 326 / 809) after this seal
- analysis/comparison/event contract: 1.52.0 at the base; 1.53.0 after this seal (version literals only)
- migration head: `0065_norm_crop_render` at the base; `0066_run_deletion` after this seal
- base commit: `a6472586295e9e4c4434b7b9428a86ab6b3e0003`
- base: `origin/main` `a9c2b56ad` plus the interface commit of this task (`a64725862`)
- the slot: 1.53.0 / `0066` was planned for the wave-5 tables of the «Прецеденты» programme (`CRIT-SEAL-52`); they move to **1.54.0 / `0067`** (owned by the integrator `pdf-analysis-19`, who reseals them on `dev`)

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json` (routes), `db/migrations/versions/` (migration head), `scripts/recovery/schema_coverage.py` (`TABLES`, `TRIGGERS`), `scripts/recovery/grant_classification.py` (`APPEND_ONLY`), `scripts/recovery/product_purge.py` (`PRODUCT_TABLES`, `PRODUCT_COMMAND_TYPES`), `tests/support/expected_facts.json`
- enumerator_owner: RUN-DELETE-01
- totality_query: `git grep -n "audit_run_deletion" -- scripts db infra tests/integration` and `git grep -n "deleteRun" -- contracts tests/support src/auditmanager/api`

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

(The hotfix reaches `main` through the release integrator, under `docs/program/MAIN_AUTODEPLOY_POLICY.md`; this lane never pushes, merges or tags.)

## Allowed paths
- `contracts/**`
- `db/migrations/versions/**`
- `scripts/recovery/**`
- `infra/deploy/apply-grants.sh`
- `infra/deploy/proxy/**`
- `infra/deploy/serve.py`
- `infra/deploy/README.md`
- `src/**`
- `tests/**`
- `web/openapi/**`
- `web/src/shared/api/**`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/tests/**`
- `web/FRONTEND_LOCK.json`
- `docs/program/CURRENT_STATE.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/tasks/RUN-DELETE-01.md`

## Lane resources
- foundation_instance: `rd01` (a throwaway, never shared)
- postgres_port: `55599` (container `rd01-pg`, `--tmpfs`, image `auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9`)
- s3_api_port: `55598` (container `rd01-minio`)
- s3_console_port: not used
- postgres_db: `auditmanager`
- s3_bucket: `rd01-bucket`

## Forbidden hotspots
- `VERSION`, `release-notes/**` (the integrator writes the release note)
- `web/src/**` other than `shared/api/**` and the one comment line of `web/src/app/bff/v1/[...path]/route.ts` named in Deliverables; global styles
- the composition root

## Non-goals
- no restore operation, no physical deletion of a run, its results, findings, decisions or Blobs
- no UI (the WEB lane)
- no new error code and no new schema; no `audit_event` / execution-journal event (the tombstone row is the durable record: who, when, the receipt)
- no change to a worker, the executor, the reconciliation or the accounting of cost: a run that is executing can never be deleted

## Deliverables
- migration `0066_run_deletion` (`audit_run_deletion`, insert-only, immutable) with its recovery classification (`schema_coverage`, `grant_classification`, `product_purge`), the regenerated `infra/deploy/apply-grants.sh` and the project-erase slice
- `delete_audit_run` (`src/auditmanager/runs/commands.py`), `RunRepository.record_deletion` / `is_deleted` / `list_for_version(include_deleted=)`, `ExecutionAdapter.delete_run`
- the readers that list or pick runs leave a deleted run out (the table below)
- touched beyond the brief, forced by the seal and one line or one comment each: `web/src/app/bff/v1/[...path]/route.ts` and `web/src/shared/api/authorization.ts` (the surface counts in comments, which `test_surface_counts_in_prose.py` measures), and in `web/tests/**` the `ErrorEnvelope` version literal and one entry of the keyed-write list in `web/tests/contract/seam-operations.contract.test.ts`
- `scripts/recovery/grant_classification.py` `SEALED_NOT_YET_WRITTEN` follows the code (six tables the base's code now writes; red on the base before this task)
- contract 1.53.0: version literals, surface 297/326/809, the reseal paragraph in the API README and `info.description`, catalogs at candidate revision 70, the generated client and mirror, the frontend lock
- tests, the classification guard and this record

## Reader classification

Every statement over `audit_run` in `src/auditmanager` (the sweep: a regexp over `FROM|JOIN audit_run` including statements broken over lines, 25 files), classified. **Exclude** = a list of runs, a "newest run that ..." pick or a display
aggregate of runs: the statement gains `AND NOT EXISTS (SELECT 1 FROM audit_run_deletion deleted WHERE deleted.run_id = <run>.run_id)`. **Keep** = a read of one run by identity, the workers' and executors' own reads, the reconciliation,
and the accounting of money. A run that is executing can never be tombstoned (the command refuses every state but partial, failed and cancelled), so a worker meets none.
`tests/unit/runs/test_deleted_run_readers.py` holds the table against the SQL text (and shows its checker can fail); `tests/integration/runs/test_delete_run.py` holds the behaviour on PostgreSQL.

| File | Query | Decision | Why |
| --- | --- | --- | --- |
| `runs/repository.py` | `_LIST_RUNS_FOR_VERSION` (`list_for_version`) | **exclude** | `listRuns`, and every walk of a version's runs newest first: the block index and the portal source (`bootstrap/adapters.py`), the comparison's run pick (`runs_newest_first`, which the optimisation project match reads). `include_deleted=True` is for the operator tool only |
| `runs/repository.py` | `_SELECT_RUN`, `_SELECT_BINDING_FACTS`, `_STALE_IN_STATE`, `_COST_SUMMARY` | keep | one run by identity (`getRunStatus` still answers); the queue's binding facts; the reconciliation of runs stranded in queued or running (never deletable); what a run cost |
| `runs/hotfix_operator.py` | `status` (children of a run) | keep | the operator reads what is stored: `list_for_version(include_deleted=True)` |
| `dashboard/repository.py` | `_RUNS_BY_STATE` | **exclude** | the dashboard's runs by state counts what the lists show |
| `dashboard/repository.py` | `_SPEND`, `_SPEND_IN_PROJECT` | keep | cost accounting: the money was spent |
| `dashboard/audit_state.py` | `_RESULT_RUN_RULES` (`result_run`) | **exclude** | "the newest run `listRuns` would show among the published and partial ones": a deleted partial run gives way to the published run before it, or to none |
| `dashboard/audit_state.py` | `_ACTIVE_RUN_RULE` | keep | a run in flight is never deletable |
| `schedule/service.py` | `_FACTS` (`result_run`) | **exclude** | the same rule as the audit state, for the documents «График работ» counts as checked |
| `execution/public.py` | `_QUEUE`, `_OVERVIEW`, `live_failure_count` | **exclude** | the execution queue is a list of the jobs of runs; a failed run deleted as noise must not stay a red item, nor count as a live failure; a later run that was deleted is not an answer to an earlier failure |
| `execution/public.py` | `_QUEUE_ITEM`, `_JOURNAL_ALL`, `_JOURNAL_RUN` | keep | one item by identity; the journal is the audit trail |
| `execution/eta.py` | `_HISTORY` | **exclude** | the durations the estimate is made of: a run deleted as not objective is not a sample |
| `execution/eta.py` | `_RUN_FACTS` | keep | one run's estimate by identity |
| `precedents/run_pass/reads.py` | `_TO_SCHEDULE`, `_REFRESHABLE` | **exclude** | the runs a «Прецеденты» pass is started or refreshed for: no one is shown a deleted run's labels |
| `precedents/run_pass/reads.py` | `_RUN` | keep | one run by identity |
| `exports/query.py`, `exports/xlsx/{preflight,certified_package,run_export,query,decision_import}.py` | `_RUN_HEADER`, `_EXPORT_ROWS`, `_RUN`, `_RUN_PIN`, `_FINDINGS` | keep | an export is of one run named by its identity; there is no list of runs here |
| `findings/citation_reader.py`, `norms/references/catalogue_input.py`, `runs/reference_pipeline.py`, `runs/stage_facts.py` | `_PIN`, `_OBSERVATIONS`, `_RUN_PIN`, the run row read | keep | one run by identity |
| `jobs/repository.py` (14 statements), `bootstrap/hosts_dispatch.py`, `runs/reconciliation.py` | claim, lease, lock, dispatch, effects | keep | worker, dispatcher and reconciliation internals; a run in these is executing |
| `executors/repository.py`, `executors/group_repository.py`, `executors/host_repository.py` | capacity and pending counts | keep | the executors' own bookkeeping, of active runs |
| `comparison/spend/repository.py` | active-run capacity and spend | keep | cost and capacity accounting |
| `runs/commands.py` | the three `FOR UPDATE` locks, `reaudit_of_run_id` and `started_from_run_id` busy checks | keep | a re-audit or a start from a stage may still name a deleted run as its source (it stays stored); the busy checks read states, not lists |

## Required tests
- command: `PYTHONPATH=src python -m pytest tests/unit/runs/test_delete_audit_run.py tests/unit/runs/test_deleted_run_readers.py -q`
  expected: 37 passed
- command: `python -m pytest tests/contract/api_v1 tests/contract/domain_p02 tests/contract/program tests/contract/release_notes -q`
  expected: all passed
- command (on a throwaway stand, `rd01-pg` and `rd01-minio`): `tests/integration/runs/test_delete_run.py`, `tests/integration/db/{test_run_deletion_migration,test_migration_lifecycle,test_schema_shape,test_schema_invariant_inventory,test_application_role_grants}.py`, `tests/integration/recovery/{test_grant_classification,test_product_purge,test_blob_reference_audit,test_schema_coverage,test_project_erase}.py`, `tests/integration/api/{test_authorization,test_role_register}.py`
  expected: see the handoff
- command: `npm --prefix web run api:verify`, `test:guards`, `test:contract`
  expected: green

## Integration contract
- Provider: `deleteRun` answers `200` with the `RunStatus` of the deleted run (its state unchanged). `404 not_found` for an unknown or already deleted run, `409 state_transition_not_allowed` for any other state, `403` for the viewer, `409 idempotency_key_reuse` for one key on two runs; a repeat of the same keyed call replays the first answer.
- Consumer (the WEB lane): after a delete the run is absent from `listRuns`, so the page re-reads the list; `getRunStatus` of the deleted run still answers, so a link to it does not break. The state set that offers the button is `partial`, `failed`, `cancelled`.
- The integrator rebases onto `origin/main` (moved to `5ce7b7200`, `runs/extended_review.py` and release notes only) and writes the release note (`VERSION`, `release-notes/**` are not this lane's).

## Failure/idempotency/security cases
- a refused call leaves no tombstone and no command receipt (the transaction ends with the refusal, as `cancelRun`);
- two concurrent deletes of one run take turns on the run row lock; the primary key is the last word;
- an account holding neither `expert` nor `admin` is `permission_denied` before anything is read;
- the tombstone row cannot be updated or deleted (`am_immutable_row`), and its run cannot be removed from under it (RESTRICT); a project erase removes it with its runs (`PRODUCT_TABLES`).

## Rollback / feature flag
No feature flag: the operation is new and nothing calls it until the UI does. Rolling the application back leaves `audit_run_deletion` unread and every run in every list again. The downgrade of `0066` drops the table: the only fact lost is that the deleted runs show in the lists again.

## Handoff
- changed files: see the commit list in the lane's report
- commands/results: see the lane's report
- known limits: no `audit_event` for a delete (the tombstone is the record); the execution journal of a deleted run is still readable by its run id; `test_every_identity_column_carries_a_format_check` is red on the base for three older tables (not this task)
- integration notes: the Precedents wave-5 seal moves to 1.54.0 / `0067`; the release note and `VERSION` are the integrator's
