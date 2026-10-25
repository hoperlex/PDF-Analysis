# Task DEV-PURGE-INVENTORY-01 — the product purge and the hand-kept table inventories know migration 0032

task_id: DEV-PURGE-INVENTORY-01
status: completed in development candidate

## Outcome

`scripts/recovery/product_purge.py` no longer refuses a database at migration head `0032_ar_v3_run_group`. `ar_v3_run_group` and `ar_v3_run_group_member` are PRODUCT tables and `start_ar_v3_beta_group` is a PRODUCT command type, so the purge of a stand that has started a six-run group truncates the group, its members and the six runs, deletes the group's command receipt after the truncate and keeps every KEEP table (the snapshot and the retrieval sets the group pins) byte for byte. The recovery tooling's closed declaration of the schema (`schema_coverage.py`) names the head, the two tables, the three new triggers (one deferred) and the new constraint and index counts, and the two other hand-kept table inventories list the new tables.

## Depends on

- `STAND-PURGE-TOOL-01` — completed purge tool whose closed classification this task extends.
- `RECOVERY-REBASE-01` — completed `schema_coverage` declaration this task extends.
- `AR-V3-BETA-SIX-RUN-02` — completed group start that wrote migration `0032` and the command type.

## Frozen inputs

- base: `integration/ar-close-1026` tip `1ce8edd029ef1a20bec8f6ed0a49b55aeeb61186` (the clean `origin/dev` base `354a9092` shows the same failures).
- migration head `0032_ar_v3_run_group` (`db/migrations/versions/20261023_0032_ar_v3_run_group.py`), unchanged; contract family/API unchanged; product `0.8.1`.
- the purge tool's guard markers and exit codes (`0` done, `2` usage, `3` refused, `4` failed) are unchanged.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: scripts/recovery/product_purge.py
- enumerator_owner: DEV-PURGE-INVENTORY-01
- totality_query: `SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'r'` — `tests/integration/recovery/test_product_purge.py::test_the_live_schema_passes_every_catalog_guard` runs the tool's own form of this query and refuses any table outside PRODUCT, KEEP and MIXED; `tests/integration/recovery/test_schema_coverage.py::test_the_declared_schema_equals_the_migrated_schema` does the same for `schema_coverage.TABLES`.

## Captured premise evidence

- premise: the purge tool refuses a database at head 0032 and 84 tests across seven files and two inventories share that gap

### P-01 — the operational defect, reproduced on a real six-run group with the base tool

- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -s -p no:cacheprovider tests/integration/recovery/test_l14_probe.py`
- note: the probe (deleted afterwards) imports the `grouped` fixture of `test_product_purge_run_group.py`, which starts one group with `start_ar_v3_group` in a clone of the migrated template, and prints the exit code and stderr of `product_purge plan --dry-run`; `scripts/recovery/product_purge.py` and `schema_coverage.py` were checked out at the base commit `1ce8edd0` for the run
- captured_output:
  ```text
  PROBE 3 product_purge: REFUSED: table(s) classified as neither PRODUCT, KEEP nor MIXED: ['ar_v3_run_group', 'ar_v3_run_group_member']. A new table is a decision about its fate (purge it or keep it) that has to be written into scripts/recovery/product_purge.py. Nothing was touched.
  1 passed in 2.08s
  ```
- interpretation: not test lag. On a stand migrated to `0032` the purge, and the recovery drills built on the same declaration, refuse for this reason; exit code 3 (REFUSED, nothing changed).

### P-02 — the failing list at the base tree, per file

- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/recovery/test_product_purge.py tests/integration/recovery/test_schema_coverage.py tests/integration/recovery/test_product_purge_script.py tests/integration/recovery/test_synthetic_drill_seed.py tests/integration/recovery/test_synthetic_drill_compare.py tests/integration/db/test_migration_lifecycle.py tests/integration/p02_journey/test_whole_journey_idempotency.py`
- note: run against the existing integration stack with the lane tree equal to the base
- captured_output:
  ```text
  failures per file (grep '^FAILED' | uniq -c):
       47 tests/integration/recovery/test_product_purge.py
       26 tests/integration/recovery/test_schema_coverage.py
        7 tests/integration/recovery/test_product_purge_script.py
        1 tests/integration/recovery/test_synthetic_drill_seed.py
        1 tests/integration/recovery/test_synthetic_drill_compare.py
        1 tests/integration/db/test_migration_lifecycle.py
        1 tests/integration/p02_journey/test_whole_journey_idempotency.py
  84 failed, 47 passed in 59.56s
  ```
- interpretation: 82 failures are the lane brief's cluster. The two inventories were read separately. `test_migration_lifecycle` differs by exactly the two `0032` tables (`Extra items in the left set: 'ar_v3_run_group_member', 'ar_v3_run_group'`). `test_whole_journey_idempotency` is the same fix class but a wider gap: its list (`P02_TABLES` in `tests/integration/p02_journey/journey.py`) misses nine tables, the two `0032` tables and the seven executor tables of `0030` and `0031` (`executor_connection`, `_connection_revision`, `_probe`, `_route_event`, `_runner_token`, `_secret`, `_task`). The drill seed and compare tests also carried pins stale since `0031` (60 tables where the head before `0032` already had 62); the `0032` failure hid them until it was fixed.

### P-03 — the group start's command type was unclassified too

- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/recovery/test_product_purge.py::test_every_event_type_and_command_type_the_source_writes_is_classified`
- note: run at the base tree
- captured_output:
  ```text
  E       AssertionError: assert ['start_ar_v3_beta_group'] == []
  E         Left contains one more item: 'start_ar_v3_beta_group'
  ```
- interpretation: the lane brief asked to verify, not assume, that the group start's command rows are covered. They were not: after the tables are classified, a stand with one started group would still be refused by `command-types-classified` (`command_record holds command type(s) nobody classified`).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/product_purge.py`
- `scripts/recovery/schema_coverage.py`
- `tests/integration/recovery/**`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/p02_journey/test_whole_journey_idempotency.py`
- `tests/integration/p02_journey/journey.py`
- `docs/program/tasks/DEV-PURGE-INVENTORY-01.md`
- `docs/program/DEV-PURGE-INVENTORY-01.md`

Reasons for the three paths beyond the lane brief's list: `schema_coverage.py` holds the declaration (`HEAD`, `TABLES`, `TRIGGERS`, `DEFERRED_TRIGGERS`, constraint and index counts) that `product_purge` is built on and that 26 of the failing tests audit; `journey.py` holds `P02_TABLES`, the list `test_whole_journey_idempotency.py` checks (that test file itself needed no change); the shell entry point `infra/deploy/purge-product-data.sh` keeps no table list (it delegates to the Python classification) and was not touched.

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, `Makefile`, `infra/**`, root dependency and lock files, `src/**`, `web/**`, the composition root, global styles, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `origin/main`, tags and the deployment host.

## Non-goals

No change to the purge algorithm, its guards, its exit codes or its shell wrapper; no new migration; no change to what the group start writes; no purge or restore against a real stand; no `make gate`. The stale pins that predate `0032` are corrected here only because they sit in the same two declarations.

## Deliverables

- `PRODUCT_TABLES` gains the two tables; `PRODUCT_COMMAND_TYPES` gains `start_ar_v3_beta_group`.
- `schema_coverage.py`: head `0032_ar_v3_run_group`, the two tables, three triggers (`trg_ar_v3_run_group_frozen`, `trg_ar_v3_run_group_member_frozen`, and the deferred `trg_ar_v3_group_complete`), constraint counts `{"c": 560, "f": 134, "p": 63, "t": 9, "u": 48}`, index count `184` (each measured from the live catalog and equal to what the migration text adds: 2 primary keys, 3 unique constraints, 7 foreign keys, 18 checks, 1 constraint trigger).
- New `tests/integration/recovery/test_product_purge_run_group.py`: a real six-run group started through `start_ar_v3_group` in a throwaway database; dry run, real run, the closure of the one TRUNCATE, the pinned foreign keys.
- Corrected pins and inventories: `PRODUCT` count 30 to 32; drill seed and compare 60 to 64 tables; `EXPECTED_TABLES` and `P02_TABLES` list the new tables (and `P02_TABLES` the seven executor tables).
- Report `docs/program/DEV-PURGE-INVENTORY-01.md` with before and after counts, the mutation proofs and a proposed register note.

## Verification

- the seven files and the two inventories, command of P-02 plus `tests/integration/recovery/test_product_purge_run_group.py`: expected `0 failed`.
- `tests/integration/recovery` whole directory (my own path): expected `0 failed`.
- every new or changed guard shown red under one quoted mutation (report).
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/DEV-PURGE-INVENTORY-01.md',encoding='utf-8').read())))"` prints `[]`.
- `git diff --check` and the exact allowed-path inventory. No full gate (`R-135`).

## Integration contract

Merge before any lane or stand step that runs `product_purge`, the recovery drills or `audit_restored_schema` against a database at `0032` (the activation runbook's purge and restore steps). The change touches no shared contract, migration, fixture module or composition root. The next migration that adds a table must again extend `PRODUCT_TABLES`/`KEEP_TABLES`/`MIXED_TABLES`, `schema_coverage.TABLES` and its trigger and count declarations, `P02_TABLES` and `EXPECTED_TABLES`; each of the four lists has a test that goes red by name until it does.

## Failure/idempotency/security cases

A table, command type or event type nobody classified still stops the tool before it touches anything. A KEEP or MIXED table with a foreign key into a PRODUCT table still stops it (this is what makes a wrong classification of the group visible). A second run after the purge reports `nothing-to-purge: yes`. The purge never uses CASCADE.

## Rollback / feature flag

Forward-revert of the commits. The change only widens a refusal list into a classification; reverting it restores the refusal on a `0032` database, which is safe (nothing is written) but blocks the purge and the recovery drills there.

## Handoff

- changed files: `scripts/recovery/product_purge.py`, `scripts/recovery/schema_coverage.py`, `tests/integration/recovery/` (new group test, three corrected pins), `tests/integration/db/test_migration_lifecycle.py`, `tests/integration/p02_journey/journey.py`, task and report.
- commands/results: see the report; the seven files and two inventories go from 84 failed to 0 failed.
- known limits: no purge was run against a real stand; the shell wrapper `purge-product-data.sh` was not exercised (it keeps no table list); the DB-backed tests ran against the shared integration stack, whose `auditmanager_ar_close` database was not touched.
- integration notes: none beyond merge order; a `DEBT_REGISTER.md` note is proposed in the report.
