# DEV-PURGE-INVENTORY-01 — the product purge knows the AR v3 run group

Migration `0032_ar_v3_run_group` added `ar_v3_run_group` and `ar_v3_run_group_member`, and the group start writes a command receipt of type `start_ar_v3_beta_group`. None of the three was classified in `scripts/recovery/product_purge.py`, and `scripts/recovery/schema_coverage.py` still declared head `0031`. The purge tool therefore refused any database at head (`product_purge: REFUSED: table(s) classified as neither PRODUCT, KEEP nor MIXED: ['ar_v3_run_group', 'ar_v3_run_group_member']`, exit 3, nothing changed), and the recovery drills' schema audit refused it for the head. This was an operational defect on any stand migrated to `0032`, not only test lag. It is measured identically on the clean `origin/dev` base `354a9092`.

## What changed

- `product_purge.py`: both tables are PRODUCT; `start_ar_v3_beta_group` is a PRODUCT command type. The lane brief also asked to verify the group start's command rows: they were **not** covered (the command type was unclassified and `command-types-classified` would have refused the first stand that started a group), so this was a second, separate gap in the same cluster.
- `schema_coverage.py` (outside the brief's list, needed because 26 failing tests audit it and the tool is built on it): head, tables, the triggers `trg_ar_v3_run_group_frozen` and `trg_ar_v3_run_group_member_frozen` (`am_immutable_row`, 27) and the deferred constraint trigger `trg_ar_v3_group_complete` (5), constraint counts `{c 560, f 134, p 63, t 9, u 48}` and index count 184. Each number was read from the live catalog by the audit and equals what the migration text adds (2 primary keys, 3 unique, 7 foreign keys, 18 checks, 1 constraint trigger, 5 unique indexes).
- Inventories: `EXPECTED_TABLES` (migration lifecycle) lists the two tables. `P02_TABLES` (in `tests/integration/p02_journey/journey.py`, not in the test file the brief names; that file needed no change) lists the two tables **and the seven executor tables of `0030`/`0031`**, which the list had never counted: that failure was the same fix class but nine tables wide, not two.
- Stale pins corrected: the drill seed and compare tests asserted 60 tables (the head before `0032` already had 62; the `0032` failure had hidden it); now 64. The purge declaration test pins PRODUCT 30 to 32.
- New `tests/integration/recovery/test_product_purge_run_group.py` (5 tests).

## The "children first" premise was not the mechanism

The lane brief expected the purge order to matter. It does not: the tool issues one `TRUNCATE TABLE` naming every PRODUCT table, and the group rows are immutable, so a row `DELETE` is refused by design (`AM003 ... ar_v3_run_group_member is immutable once written; DELETE is refused`). What matters is closure: PostgreSQL refuses `TRUNCATE ar_v3_run_group` unless `ar_v3_run_group_member` is in the same statement (`0A000 cannot truncate a table referenced in a foreign key constraint`). The group's reference to the command receipt (`command_record`, MIXED) is safe because the receipt is deleted by the tool after the truncate. The new test module proves each of these on the real schema and pins the seven foreign keys of the two tables.

## Before and after (existing integration stack, real PostgreSQL and S3)

| file | before | after |
|---|---|---|
| `tests/integration/recovery/test_product_purge.py` | 47 failed | 64 passed |
| `tests/integration/recovery/test_schema_coverage.py` | 26 failed | 30 passed |
| `tests/integration/recovery/test_product_purge_script.py` | 7 failed | 7 passed |
| `tests/integration/recovery/test_synthetic_drill_seed.py` | 1 failed | 5 passed |
| `tests/integration/recovery/test_synthetic_drill_compare.py` | 1 failed | 13 passed |
| `tests/integration/db/test_migration_lifecycle.py` | 1 failed | 10 passed |
| `tests/integration/p02_journey/test_whole_journey_idempotency.py` | 1 failed | 2 passed |
| `tests/integration/recovery/test_product_purge_run_group.py` (new) | n/a | 5 passed |

Before: `84 failed, 47 passed` over the seven files. After: `136 passed, 0 failed` over those files plus the new module (one invocation, 91.6 s), and `315 passed` over the whole `tests/integration/recovery` directory (87.4 s). The DB-backed tests all ran; nothing was skipped.

## Mutation proofs (each reverted afterwards; `git status` clean between runs)

| mutation | result |
|---|---|
| group moved from PRODUCT into KEEP | new module 4 failed, 1 passed; purge refuses `a KEEP or MIXED table has a foreign key into a PRODUCT table: [('ar_v3_run_group', 'document_version'), ('ar_v3_run_group', 'project')]`; `test_the_declaration_partitions...` and `test_the_live_schema_passes_every_catalog_guard` red |
| member moved from PRODUCT into KEEP | 4 failed, 1 passed; refuses `[('ar_v3_run_group_member', 'ar_v3_run_group'), ('ar_v3_run_group_member', 'audit_run')]` |
| `start_ar_v3_beta_group` removed from `PRODUCT_COMMAND_TYPES` | new module 2 failed (`REFUSED: command_record holds command type(s) nobody classified as product or keep: ['start_ar_v3_beta_group']`) and `test_every_event_type_and_command_type_the_source_writes_is_classified` red (`assert ['start_ar_v3_beta_group'] == []`) |
| single TRUNCATE built from `PRODUCT_TABLES - {member}` (the child left out of the statement) | real run red: apply exits 4, `FeatureNotSupported ... cannot truncate a table referenced in a foreign key constraint. Table "ar_v3_run_group_member" references "ar_v3_run_group"` |
| `schema_coverage.HEAD` back to `0031` | `test_the_declared_head_is_the_alembic_head` red, 25 of 30 coverage tests red (`migration head differs`) |
| `trg_ar_v3_group_complete` not declared deferred | 18 of 30 red (`trigger deferral differs: ['trg_ar_v3_group_complete']`) |
| member's immutable trigger not declared | 18 of 30 red (`triggers differ: ... unknown=[('ar_v3_run_group_member', 'trg_ar_v3_run_group_member_frozen', 'am_immutable_row', 27)]`) |
| foreign-key count pin 134 to 127 | 18 of 30 red (`constraint counts differ`) |
| lifecycle inventory without the member table | `test_clean_install_creates_exactly_the_declared_relations` red (set differs) |
| `P02_TABLES` without the member table and `executor_task` | `tables exist that this suite's idempotency claim does not count: ['ar_v3_run_group_member', 'executor_task']` |
| drill compare pin 64 to 62 | `assert (64 == 62)` |

## Not run

No purge against a real stand, no run of `infra/deploy/purge-product-data.sh` (it keeps no table list and was not touched), no `make gate` (`R-135`). The tests used the shared integration stack through throwaway databases and buckets; nothing in `auditmanager_ar_close` was written.

## Proposed register note (not written; `DEBT_REGISTER.md` is outside this lane)

> The purge tool, the recovery schema declaration and the P02 and lifecycle table inventories lagged migrations `0030` to `0032` (84 red tests at SHA `9c35ec4e`, identical on `origin/dev` `354a9092`). Closed by `DEV-PURGE-INVENTORY-01`. Check: `pytest tests/integration/recovery tests/integration/db/test_migration_lifecycle.py tests/integration/p02_journey/test_whole_journey_idempotency.py` reports `0 failed`. Standing rule it exposes: a migration that adds a table, a command type or a trigger is not complete until `product_purge.py`, `schema_coverage.py`, `P02_TABLES` and `EXPECTED_TABLES` name it; the four tests already go red by name, but only in a DB-backed run, which `R-135` defers, so a lane that adds a migration should run those four files before it hands back.
