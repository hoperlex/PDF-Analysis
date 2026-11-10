# Task CRIT-SEAL-50 — the first seal of the precedents programme: contract 1.51.0 and migration `0064`

## Outcome
One contract version and one migration carry everything in `ADR-0029` that needs them: the tables and columns, the operations with stubs that answer 501, the identities, the grants, the recovery classification and the pins. Numbers: 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first).

Owner: the slot holder, appointed by the integrator.

## Depends on
- CRIT-ADR-29

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decisions 6, 7, 8, 10 and 12; plan sections 3.1 and 3.2 (data and operations), 3.6 (switches and marker)
- versioning: additive changes are a minor version (`docs/program/VERSIONING_AND_FREEZE_POLICY.md`); `Evidence` does not change
- plan: the «Прецеденты» plan (version 5, with the R-154 correction) is the integrator's working copy `.local/evidence/lane-common-prec/plan-v5.md` and is not in git; the decisions it carries are in `ADR-0029`
- rules: the common rules of the programme (`.local/evidence/lane-common-prec-2026-11-10.md`, git-ignored): minimal checks only, tests under the host lock, no push, merge or tag
- the plan read the code at `5342b7178`, which has the same code as the base; every `path:line` the lane relies on is checked in its own worktree before use

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json` (routes), `db/migrations/versions/` (migration head), and the sets `KEEP_TABLES`, `PRODUCT_TABLES`, `KEEP_COMMAND_TYPES`, `PRODUCT_COMMAND_TYPES`, `KEEP_EVENT_PREFIXES` in `scripts/recovery/product_purge.py`
- enumerator_owner: CRIT-SEAL-50
- totality_query: `git grep -n "0064" -- db/migrations/versions` and the operation ids added to `contracts/api/v1/openapi.json`, compared with the plan's list

## Captured premise evidence
- premise: the contract-version pin sweep; the migration-head pin sweep

### P-01 — the contract-version pin sweep
- captured_at: 2026-11-10
- command: `grep -rl --exclude-dir=node_modules --exclude-dir=.git "1\.49\.0" . | grep -v "^./.local" | wc -l`
- captured_output:
  ```text
  147
  ```
- interpretation: the number of files that carry the literal `1.49.0` at the base; at the base the lane works from, the AR v3 removal wave has moved them to `1.50.0` (`R-154h`) and this seal moves `1.50.0` to `1.51.0`, except the historical records; the lane repeats the sweep with the literal it finds before it starts. The count is the plan's, captured again on `47c90e1ec`. Once the task files of `CRIT-ADR-29` are merged the same sweep lists 24 more files, all under `docs/program/tasks/` (historical records that stay as they are): 171 in all.

### P-02 — the migration-head pin sweep
- captured_at: 2026-11-10
- command: `grep -rl --exclude-dir=node_modules --exclude-dir=.git "0062_hosts_stage_models\|\"0062\"\|'0062'" . | grep -v "^./.local" | wc -l`
- captured_output:
  ```text
  36
  ```
- interpretation: the number of files that name the head `0062`; the AR v3 removal wave moves the head to `0063` first and this seal moves it to `0064`, except the historical records; the lane repeats the sweep with the literal it finds before it starts. Once the task files of `CRIT-ADR-29` are merged the same sweep lists 24 more files, all under `docs/program/tasks/`: 60 in all.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `db/migrations/versions/**`
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `contracts/analysis/v1/**`
- `contracts/events/v1/**`
- `src/auditmanager/api/schemas/**`
- `src/auditmanager/api/routers/**`
- `src/auditmanager/api/security.py`
- `src/auditmanager/shared/identity/**`
- `web/openapi/openapi.json`
- `web/src/shared/api/**`
- `web/FRONTEND_LOCK.json`
- `scripts/recovery/product_purge.py`
- `scripts/recovery/grant_classification.py`
- `scripts/recovery/schema_coverage.py`
- `scripts/recovery/memory_forget.py`
- `infra/deploy/apply-grants.sh`
- `infra/deploy/proxy/**`
- `tools/executor-runner/RUNNER_API.md`
- `tests/contract/**`
- `tests/integration/db/**`
- `tests/integration/recovery/**`
- `tests/integration/runs/test_stage_plan_db.py`
- `tests/support/expected_facts.json`
- `tests/unit/api/**`
- `tests/unit/runs/**`
- `tests/unit/executor_runner/**`
- `web/tests/unit/**`
- `web/tests/guards/**`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- in `db/migrations/versions/**` only the new `0064` file is added; no existing migration is edited
- no other lane touches `contracts/**` or `db/migrations/**` while this seal is open

## Non-goals
- no behaviour behind the stubs: the operations answer 501 until the lane that implements them lands
- no patterns, cross-document evidence, parameter facts or `parameter_mismatch`: they belong to `CRIT-SEAL-51`
- no edit of the historical records that also contain the old version and head

## Deliverables
- tables and columns of plan section 3.1: `decision_memory_comment`; `precedent_label_at_decision` and `precedent_revision` on `decision_memory_decision`; `decision_memory_embedding_intent` and `decision_memory_embedding` (no HNSW); `decision_memory_probe`; `precedent_setting_event`; `vector_control` and `vector_control_event`; `decision_memory_precedent_run` and `decision_memory_precedent_advice`; `executor_task_context_delivery` (`KEEP`, no foreign keys, no text); `finding_block_evidence`; `decision_memory_block_evidence`; `finding_observation.grounding_kind`, `extended_observation_ref`, `related_finding_uid`; the categories `drawing_discrepancy` and `cross_source`; the diagnostic reasons `block_not_in_run_geometry`, `block_crop_mismatch`, `block_quote_not_in_recognised`; `audit_run.publication_mode` with a freeze trigger recreated as `0062` did for `stage_plan`; `norm_crop_render`
- operations of plan section 3.2 as stubs: `getExecutorTaskContext` (a task token holding the claim), `getRunPrecedents`, `getFindingPrecedents`, `getVectorControl`, `setVectorPaused`, `listPrecedentSettings`, `appendPrecedentSetting`; the claim payload `context_request`; `AnswerRequest` echo `context_sha256`; `Finding.block_evidence[]`, `FindingObservation.grounding_kind` and `origin`; `RunWaitCause += vector_window`; `RunStageChip` is **not** extended
- recovery classification of every new table, command type (`append_precedent_setting`, `set_vector_paused`) and event prefix (`precedent.`, `vector.`) in `product_purge.py`, `grant_classification.py`, `schema_coverage.py`, `memory_forget.py` and `apply-grants.sh`
- the pins moved: `1.50.0` to `1.51.0` and `0063` to `0064` in every file the repeated sweeps list, except the historical records

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- migration up, down, up; a downgrade refuses while the new tables hold rows
- the forget protection refuses an insert of a comment into a forgotten case
- the freeze trigger refuses a change of `publication_mode`
- `test_every_event_type_and_command_type_the_source_writes_is_classified` passes; the new tables, commands and events are classified
- the schema and grant inventories
- `tests/contract/api_v1`

## Integration contract
The stubs answer 501 until their lane lands; the later lanes implement behind the operations without touching the contract. Lane resources for the throwaway database are assigned by the integrator before dispatch. The numbers are fixed by `R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first and this seal is 1.51.0 / `0064`. A lane that finds a different version or head on its base stops and reports it. The id `CRIT-SEAL-50` is a label kept from the plan; it no longer names the contract version.

## Failure/idempotency/security cases
- a new table, command type or event type that is not classified makes the purge and the recovery guard refuse: that is the forcing function and must stay
- the migration is not rolled back once rows exist (as `0059`…`0062`)

## Rollback / feature flag
The switches of `ADR-0029` decision 6 turn the behaviour off for new runs; the migration with rows is not rolled back.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
