# Task DEBT-EFFECT-GUARDS-0033 — re-prove D-148 and D-142 against the tree before a migration is written

task_id: DEBT-EFFECT-GUARDS-0033
status: completed in development candidate (no migration: both debts were already closed by `0018_norm_custody`)

## Outcome

The dispatch assumed `D-148` (the effect-table state guards fire on UPDATE only) and `D-142` (an interrupted artifact intent has no settlement state) were open and asked for `0033_effect_state_guards`. Measured on a real PostgreSQL stack at `0032_ar_v3_run_group`, both were closed on 2026-10-12 by `0018_norm_custody` (`W54-SEAL-01`, commit `6f4a2dae`) and `W54-CUSTODY-01`; only `DEBT_REGISTER.md` is stale. No `0033` is written: it would recreate the same triggers byte for byte, move the migration head for no schema change, and force a head re-pin across every status document. The lane instead adds the two tests the existing suite lacks (the 0017 to 0018 boundary on one populated database, and the 0018 downgrade/re-upgrade with ordinary effect rows) and the evidence for closing both register rows.

## Depends on

- `W54-SEAL-01` — completed; `0018_norm_custody`.
- `W54-CUSTODY-01` — completed; the `prepared -> abandoned` settlement in `JobRepository`.

## Frozen inputs

- domain contract: unchanged
- API contract: unchanged (91 paths / 103 operations / 298 schemas)
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`, unchanged (this task adds no migration)
- base commit: `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the effect-table state guards are already `BEFORE INSERT OR UPDATE` and `analysis_artifact_publication` already has the `prepared -> abandoned` settlement, so the dispatched migration `0033` has nothing to change

### P-01 — the migration that closes both, and nothing after it redefines the guard

- captured_at: 2026-10-26
- command: `rg -n '_effect_triggers\("|may not be created in state|NEW.state = .abandoned' db/migrations/versions/20261012_0018_norm_custody.py`
- captured_output:
  ```text
  97:                    RAISE EXCEPTION 'state_transition_not_allowed: % may not be created in state %',
  110:               AND OLD.state = 'prepared' AND NEW.state = 'abandoned' THEN
  137:                    AND NEW.state = 'abandoned')
  197:    _effect_triggers("INSERT OR UPDATE")
  602:    _effect_triggers("UPDATE")
  ```
- interpretation: line 197 is `0018`'s upgrade (guards attached `INSERT OR UPDATE`, the function gains an INSERT arm that refuses any state but `prepared`, and the `abandoned` arm); line 602 is its downgrade restoring the 0017 form. `rg -n "am_guard_durable_effect_transition" db/migrations/versions` names only `0014`, `0017` and `0018`, so no later migration changed the function.

### P-02 — the live catalogue at the head, on a stack built by `alembic upgrade head`

- captured_at: 2026-10-26
- command: `docker exec auditmanager-debt-effects-postgres-1 psql -U auditmanager_local -d auditmanager_debt_effects -At -c "SELECT (SELECT version_num FROM alembic_version) || ' ' || tgrelid::regclass || ' ' || substr(pg_get_triggerdef(oid), 1, 118) FROM pg_trigger WHERE tgname IN ('trg_provider_call_effect_state_guard','trg_analysis_artifact_state_guard') ORDER BY tgrelid::regclass::text"`
- captured_output:
  ```text
  0032_ar_v3_run_group analysis_artifact_publication CREATE TRIGGER trg_analysis_artifact_state_guard BEFORE INSERT OR UPDATE ON public.analysis_artifact_publication FOR E
  0032_ar_v3_run_group provider_call_effect CREATE TRIGGER trg_provider_call_effect_state_guard BEFORE INSERT OR UPDATE ON public.provider_call_effect FOR EACH RO
  ```
- interpretation: both guards fire on INSERT at the head. The same database was at `0017_execution_queue` earlier in the lane and showed `BEFORE UPDATE ON` for both, so the lane's stack can tell the two states apart.

### P-03 — the register still lists both rows as open

- captured_at: 2026-10-26
- command: `rg -n '^\| \*\*D-(142|148)\*\*' docs/program/DEBT_REGISTER.md`
- captured_output:
  ```text
  59:| **D-142** | artifact publication intents have no settlement state, so reconciliation never becomes clean after an interrupted publication | W54 custody (migration) |
  65:| **D-148** | the effect tables' state triggers guard UPDATE only | the next migration on those tables |
  ```
- interpretation: the only stale artefact. The rows' own check commands (`rg ... 20261002_0014...`, `rg ... 20261009_0017...`) read the two migrations that predate the closure, which is why they could not show it.

### P-04 — the crash, rerun and clean-report cycle passes on the lane stack

- captured_at: 2026-10-26
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_durable_effect_boundaries.py -k d142`
- captured_output:
  ```text
  ..                                                                       [100%]
  2 passed, 18 deselected in 1.18s
  ```
- interpretation: `test_d142_a_crashed_publication_is_settled_and_the_report_is_clean_after_a_rerun` settles the crashed Attempt's intent `abandoned`, leaves the content-addressed blob `available`, shows the rerun's own intent `bound`, and asserts the reconciliation report lists no unbound artifact for either run. `test_d142_settlement_leaves_a_live_attempts_intent_prepared` shows settlement is never inferred from age alone: the producing Attempt must be terminal. `reconcile_at_startup` runs this settlement at API start (`src/auditmanager/api/app.py:345`).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The register rows, `W53-CLOSE-INT` and the `W48` review are not rewritten. The proposed closing text is in the report for the integrator, in the form `D-146` and `D-147` already use.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `db/migrations/versions/20261026_0033_effect_state_guards.py`
- `tests/integration/db/test_durable_analysis_effects.py`
- `tests/integration/db/test_effect_state_guards_0033.py`
- `tests/integration/db/test_downgrade_chain_round_trip.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/support/expected_facts.json`
- `tests/integration/ingest/test_reconciliation.py`
- `tests/integration/ingest/test_reconciliation_custody_blobs.py`
- `src/auditmanager/ingest/reconciliation.py`
- `src/auditmanager/runs/reconciliation.py`
- `docs/program/tasks/DEBT-EFFECT-GUARDS-0033.md`
- `docs/program/DEBT-EFFECT-GUARDS-0033.md`

## Lane resources

- foundation_instance: `auditmanager-debt-effects`
- postgres_port: `58630`
- s3_api_port: `62130`
- s3_console_port: `62131`
- postgres_db: `auditmanager_debt_effects`
- s3_bucket: `auditmanager-debt-effects`

## Forbidden hotspots

`contracts/**`, every other migration, `infra/**`, `Makefile`, root dependency/lock files, `src/auditmanager/bootstrap/**`, `web/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, and everything not listed above. The migration path above stays unused: no `0033` exists, so the migration head and its three pin files (`expected_facts.json`, the downgrade-chain digest table, the schema inventory seal) are untouched.

## Non-goals

No migration, no change to the guard function, no change to `JobRepository` settlement or the reconcilers, no register or status edit (the integrator owns both), no re-entry for a `rejected` blob (`D-143`, a separate row that W54 resolved as a report and refusal), no full gate (deferred by `R-135`; the changed surface is a test file and two documents).

## Deliverables

- `tests/integration/db/test_effect_state_guards_0033.py`: two tests.
  - `test_0018_keeps_the_terminal_rows_0017_accepted_and_refuses_new_ones`: on one database, `0017` accepts a terminal row inserted directly into each table (the control), `0018` keeps those rows, both guards read `BEFORE INSERT OR UPDATE`, a direct INSERT of `outcome_unknown` and `abandoned` (effect) and `bound` and `abandoned` (publication) is refused with `AM001`, the initial state is accepted, and `prepared -> response_received`, `prepared -> abandoned`, `prepared -> bound` still work.
  - `test_0018_round_trips_with_prepared_and_bound_effect_rows`: `0018 -> 0017 -> 0018` with a `prepared` effect, a `prepared` publication and a `bound` publication keeps every row and moves the guard text `INSERT OR UPDATE -> UPDATE -> INSERT OR UPDATE`.
- This file and the report with the closing text for `D-148` and `D-142`.

## Required tests

- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/db/test_effect_state_guards_0033.py tests/integration/db/test_durable_analysis_effects.py tests/integration/db/test_norm_custody_migration.py tests/integration/db/test_schema_invariant_inventory.py tests/integration/db/test_downgrade_chain_round_trip.py tests/integration/ingest/test_reconciliation.py tests/integration/ingest/test_reconciliation_custody_blobs.py tests/integration/storage/test_repeated_publication.py`
- expected: all pass on a PostgreSQL 17 stack with `DATABASE_URL` and the `S3_*` names exported; `-k d142` of `tests/integration/runs/test_durable_effect_boundaries.py` passes 2.

## Integration contract

Nothing to merge into the schema. The integrator may rely on: the head is still `0032_ar_v3_run_group`; no pin changes; the new test file is self-contained (own seeding, only `foundation_command`, `empty_database` and `FACTS`). To close the register, apply the report's row text.

## Failure/idempotency/security cases

A guard that regressed to UPDATE-only, a function that stops refusing a non-initial INSERT, and a downgrade that leaves the INSERT guard in place each turn a named test red (three quoted mutations in the report). Settlement never hides a `bound` object (`test_a_bound_publication_is_never_abandoned` in `test_norm_custody_migration.py`) and never fires for a live Attempt.

## Rollback / feature flag

Not applicable: no schema or behaviour change. Reverting the commit removes only the new test file and the two documents.

## Handoff

- changed files: the new test file, this task file, the report
- commands/results: see the report
- known limits: the register is stale until the integrator applies the proposed rows; the stale rows' check commands should be replaced as proposed
- integration notes: no merge-order constraint; no DB lane re-run needed beyond the commands above
