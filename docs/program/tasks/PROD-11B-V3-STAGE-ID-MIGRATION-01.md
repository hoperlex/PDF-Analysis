# Task PROD-11B-V3-STAGE-ID-MIGRATION-01 — the database admits the AR v3 CITE stage id

task_id: PROD-11B-V3-STAGE-ID-MIGRATION-01
status: completed in development candidate (see the report)

## Outcome

Migration `0033_ar_v3_cite_stage_id` replaces the one database CHECK that refuses the CITE `StageResult` row of every AR v3 Run, `stage_result.ck_stage_result_stage_id` (nine stage ids since `0002`), by the same nine ids plus `ar_v3_citation_review` (`D-225`, found by `PROD-11a`, verdict UNSAFE). The downgrade restores the nine-id CHECK and refuses while a `stage_result` row carries the new id. The migration head moves from `0032_ar_v3_run_group` to `0033_ar_v3_cite_stage_id` and every pin of the old head moves with it. After the migration the probe `tests/integration/runs/test_v3_saved_text_layer_probe.py` measures the six Runs of an unmetered recorded group `published` and the specification readers `ready`; the recorded-mode cost refusal (piece 2 of `D-225`) is unchanged and stays outside this lane.

## Depends on

- `PROD-11A-V3-TEXT-LAYER-PROBE-01` — completed (the evidence), `D-225`, `D-222`.
- `AR-V3-BETA-RUN-STAGE-SEAL-01` — completed (added the tenth id to the API vocabulary and the CITE writer).

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched; the API already carries `ArV3BetaStageId`)
- analysis/comparison/event contract: not_applicable
- migration head: `0032_ar_v3_run_group` before; `0033_ar_v3_cite_stage_id` after (the integrator owns the slot for this lane; nothing else in the wave touches migrations)
- base commit: `3f36f664` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes (the stage ids `stage_result` stores: nine to ten)
- enumerator_path: `db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py`
- enumerator_owner: this lane, for the migration; the API vocabulary (`StageId`, `ArV3BetaStageId`) and `contracts/analysis/ar_v3_beta/v1/stage.json` are unchanged
- totality_query: `SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_stage_result_stage_id'` prints the nine registry ids and `ar_v3_citation_review`; `tests/integration/db/test_ar_v3_cite_stage_id_migration.py` compares it with a list written out in the test and ties the migration's restated ids to `0002`'s `STAGE_IDS`, to `StageId` / `ArV3BetaStageId` and to the stage extension contract

## Captured premise evidence

- premise: the plan and the probe report say that one CHECK refuses the CITE row and that `ck_model_call_stage_id` and others are to be widened only if the code can write the id there. Re-read at the base commit: three CHECKs enumerate the nine ids (`stage_result`, `model_call`, `finding_observation`), the v3 code can write the CITE id into exactly one of them (`stage_result`), the other writes of the CITE stage land in places that already admit it. The premise matches; nothing differs.

### P-01 — the CHECKs over stage ids at head `0032`, measured on a throw-away database migrated by the literal migration command

- captured_at: 2026-10-26
- command: `DATABASE_URL=<throw-away database on the lane server> PYTHONPATH=src .venv/bin/python -m alembic --config db/migrations/alembic.ini upgrade head`, then `SELECT t.relname, c.conname, pg_get_constraintdef(c.oid, true) FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid WHERE c.contype = 'c' AND pg_get_constraintdef(c.oid, true) ~* 'stage'` (the database was dropped at once; `pg_database` held no `prod11b_*` database afterwards)
- captured_output:
  ```text
  alembic_version: 0032_ar_v3_run_group
  analysis_artifact_publication  ck_analysis_artifact_stage_id   CHECK (stage_id ~ '^[a-z][a-z0-9_]{2,63}$'::text)
  finding_observation            ck_finding_observation_stage_id CHECK (stage_id = ANY (ARRAY['source_preparation'::text, 'page_geometry_extraction'::text, 'document_context_build'::text, 'text_analysis'::text, 'block_analysis'::text, 'finding_merge'::text, 'finding_review'::text, 'finding_correction'::text, 'norm_verification'::text]))
  model_call                     ck_model_call_stage_id          CHECK (stage_id = ANY (ARRAY[ ... the same nine ... ]))
  provider_call_effect           ck_provider_effect_stage_id     CHECK (stage_id = 'text_analysis'::text)
  stage_result                   ck_stage_result_stage_id        CHECK (stage_id = ANY (ARRAY[ ... the same nine ... ]))
  (also matched by the pattern, not stage vocabularies: ck_stage_result_stage_version; the project_stage CHECKs of
   document_version_classification(_correction) ('P', 'R'); the error-code CHECKs of command_record, audit_run, model_call, provider_call_effect)
  columns named stage_id: analysis_artifact_publication, finding_observation, model_call, provider_call_effect, stage_result
  functions whose body names a stage id: am_verify_norm_citation_partition ('norm_verification', a read, not a vocabulary)
  ```
- interpretation: three CHECKs list the nine ids (`stage_result`, `model_call`, `finding_observation`, all created from `STAGE_IDS` of `0002`); two others are not lists (`provider_call_effect` holds `text_analysis` only, `analysis_artifact_publication` a lower-snake-case pattern that the CITE id matches). `rg -n "ck_stage_result_stage_id|ck_model_call_stage_id|ck_finding_observation_stage_id|STAGE_IDS" db/migrations` finds `0002` only (lines 102, 771, 840, 943): no later migration redefined any of the three.

### P-02 — which code writes the CITE stage id, and into which tables

- captured_at: 2026-10-26
- command: `rg -n "ar_v3_citation_review|stage_started|record_stage_result|_persist_and_bind|_publication_store" src/auditmanager/runs/v3_cite_stage.py; rg -n "INSERT INTO model_call|INSERT INTO finding_observation \(" src; rg -n "'text_analysis'" src/auditmanager/jobs/repository.py src/auditmanager/runs/v3_provider_call.py`
- captured_output:
  ```text
  v3_cite_stage.py:72   runs.record_stage_result(...)          -> stage_result (UPSERT), then an audit_event 'stage.finished' {stage_id, state}
  v3_cite_stage.py:109  run_repo.stage_started(...)            -> audit_event 'stage.started' {stage_id}
  v3_cite_stage.py:142  _publication_store(... stage_id=contract.stage_id)  -> analysis_artifact_publication.stage_id
  v3_cite_stage.py:196  _persist_and_bind(...)                 -> stage_result + the artifact binding
  jobs/repository.py:255-261  INSERT INTO model_call (... VALUES (:model_call_id, :run_id, 'text_analysis', ...)
  jobs/repository.py:158      the provider effect: ... 'text_analysis' ...
  runs/v3_provider_call.py:133  stage_id="text_analysis" (the v3 call is journalled under it)
  findings/publication.py:49, v2_publication.py:34 (stage_id 'text_analysis' at :195), citation_publication.py:113 -> finding_observation
  ```
- interpretation: the CITE stage writes `stage_result` (refused at `0032`), `audit_event` (the payload carries the id; the table has no stage vocabulary), and `analysis_artifact_publication` (pattern CHECK, admits it). `model_call` is written from one INSERT that names the literal `'text_analysis'`, and `provider_call_effect` is held to it by its CHECK; no v3 path writes `finding_observation`. So only `ck_stage_result_stage_id` must be widened; `ck_model_call_stage_id` and `ck_finding_observation_stage_id` are left at nine ids and a test holds them there.

### P-03 — the naming and structure of `0032`, `0029` and how a migration test is written

- captured_at: 2026-10-26
- command: `sed -n 1,20p db/migrations/versions/20261023_0032_ar_v3_run_group.py; rg -n "^revision|^down_revision|def downgrade|RuntimeError" db/migrations/versions/20261021_0029_routing_refusal_codes.py db/migrations/versions/20261023_0032_ar_v3_run_group.py; rg -n "def test_|empty_database|_alembic" tests/integration/db/test_routing_refusal_codes_migration.py | head -20`
- captured_output:
  ```text
  0032: revision = "0032_ar_v3_run_group"      down_revision = "0031_executor_pull_channel"   file 20261023_0032_ar_v3_run_group.py
  0029: revision = "0029_routing_refusal_codes" down_revision = "0028_classification_corrections"
  0029 downgrade: reads the rows that carry the added codes, raises RuntimeError("0029 downgrade refused: ...") else restores the old CHECKs (ALTER TABLE ... DROP CONSTRAINT / ADD CONSTRAINT)
  0032 downgrade: raises RuntimeError("AR v3 group history exists; restore a backup instead of downgrading") while ar_v3_run_group has a row
  tests: empty_database + foundation_command(_alembic("upgrade"|"downgrade", REV), url) subprocesses; HEAD = FACTS.migration_head; a refusal is asserted by returncode != 0 and the message in stderr
  ```
- interpretation: the new file is `20261026_0033_ar_v3_cite_stage_id.py`, `revision = "0033_ar_v3_cite_stage_id"` (24 characters), `down_revision = "0032_ar_v3_run_group"`; the downgrade follows `0029` (a SELECT EXISTS, then `RuntimeError`).

### P-04 — the files that pin the head `0032_ar_v3_run_group`

- captured_at: 2026-10-26
- command: `rg -n "0032_ar_v3_run_group" --glob '!docs/**' .; rg -n "0032" --glob '!docs/**' --glob '!web/**' --glob '!*.json' --glob '!*.lock' . | rg -v 0032_ar_v3_run_group; python tools/plan/pin_sweep.py migration`
- captured_output:
  ```text
  pins that move with the head (code and tests):
    scripts/recovery/schema_coverage.py:41            HEAD = "0032_ar_v3_run_group"
    tests/support/expected_facts.json:834              "migration_head": "0032_ar_v3_run_group"   (read by FACTS.migration_head; test_doc_prose_facts.py compares it with the graph)
    tests/integration/db/test_ar_v3_run_group.py:359   == "0032_ar_v3_run_group" after `upgrade head`
  digests that move with the head's schema or files:
    tests/integration/db/test_schema_invariant_inventory.py   constraints digest (the CHECK text changes)
    tests/integration/db/test_downgrade_chain_round_trip.py   UPGRADE_SURFACE_DIGESTS (one entry per revision since 0022)
  mentions that are history, not pins (comments, docstrings; unchanged): scripts/recovery/product_purge.py:109,150; tests/integration/recovery/test_synthetic_drill_seed.py:123, test_synthetic_drill_compare.py:48, test_product_purge.py:64, test_product_purge_run_group.py:3; tests/integration/p02_journey/journey.py:172; tests/integration/db/test_migration_lifecycle.py:67; tests/integration/runs/test_v3_saved_text_layer_probe.py:733
  not pinned: test_migration_lifecycle.py (relations; this migration adds none), the recovery table counts (no new table), contracts/domain/v1/identifiers.json (names 0031 as evidence of an identity, not the head)
  documents that name the head: see the report (the integrator updates the prose)
  ```
- interpretation: four code or data pins and two digests; the twelve counted in the plan are mostly documents. The recovery inventories and `test_migration_lifecycle.py` list tables, and `0033` adds none.

### P-05 — the probe before the migration, and what it does after

- captured_at: 2026-10-26
- command: `pytest tests/integration/runs/test_v3_saved_text_layer_probe.py` on the base commit's probe with `0033` present
- captured_output:
  ```text
  5 failed, 10 passed: test_the_migrated_schema_does_not_admit_the_cite_stage,
  test_every_provider_request_was_answered_before_the_run_failed[recorded replay, call marked unmetered],
  test_an_unmetered_call_is_refused_at_the_cite_stage_row, test_no_v3_run_is_published_on_the_migrated_schema,
  test_the_readers_find_no_published_run_of_an_unpublished_v3_group[recorded replay, call marked unmetered]
  ```
- interpretation: exactly the five reds the probe report predicted for a migration that admits the id (mutation M14 there: facts 1, 2 unmetered, 4, 5, 7 unmetered). The facts that flip are rewritten in this lane; the rest are kept.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths
- `db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py`
- files that pin the head: `tests/support/expected_facts.json`, `scripts/recovery/schema_coverage.py`, `tests/integration/db/test_ar_v3_run_group.py`, `tests/integration/db/test_schema_invariant_inventory.py`, `tests/integration/db/test_downgrade_chain_round_trip.py`
- `tests/integration/db/test_ar_v3_cite_stage_id_migration.py` (new)
- `tests/integration/runs/test_v3_saved_text_layer_probe.py`
- `docs/program/tasks/PROD-11B-V3-STAGE-ID-MIGRATION-01.md`
- `docs/program/PROD-11B-V3-STAGE-ID-MIGRATION-01.md`

## Lane resources

- foundation_instance: the integrator's lane stack (`ar-close-1026`), not stopped, reset or written to by this lane
- postgres_db: throw-away databases created on that server by the fixtures of `tests/integration/db` (`a1_probe_*`, `a1_clone_*`, a session template) and by the probe (`prod11a_probe_*`), each dropped by its fixture
- s3_bucket: the lane bucket, used by the probe only (content-addressed objects, as in every suite of `tests/integration/runs`)

## Forbidden hotspots
- `contracts/**`, any composition root, `infra/**`, `profile.json`, `src/**`, `web/**`
- root dependency/lock files, global styles
- documents other than the two deliverables (the integrator updates the prose that states the head), `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- No change to `ck_model_call_stage_id` and `ck_finding_observation_stage_id`: no code writes the CITE id there.
- No fix of piece 2 of `D-225` (the recorded provider binding has no verifiable cost): it belongs to the composition root.
- No activation of the group (`PROD-12`), no change to the readers, no new table (so no product-purge classification).

## Deliverables

- the migration, the pin moves, the new migration test module, the rewritten probe facts
- this task file and `docs/program/PROD-11B-V3-STAGE-ID-MIGRATION-01.md` (premise, mutation table, before/after of modified tests, commands with counts, the list of documents whose head sentence now fails the prose guard)

## Required tests

- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/db/test_ar_v3_cite_stage_id_migration.py`
- expected: `8 passed`
- whole, one pytest at a time on the lane stack: `tests/integration/db`, `tests/integration/recovery`, `tests/integration/runs/test_v3_saved_text_layer_probe.py`, `tests/integration/p02_journey` is not run (it needs the stand), `tests/contract/analysis_packages`, `tests/contract/program` and the two prose-guard modules; counts in the report

## Integration contract

The integrator merges this lane into `integration/ar-close-1026` with `--no-ff`, then fixes the documents the report lists (the head sentence), then records in `D-225` that piece 1 is closed (check: `rg -n 'ar_v3_citation_review' db/migrations` finds `0033`, and the probe shows the unmetered group `published`) and in `D-222` that the readers answer `ready`. `D-222` closes with `D-225` (the register says so); `PROD-11` itself is the integrator's to release. Piece 2 of `D-225` (recorded binding cost) is still open. The migration changes a CHECK only: the deployed database must be upgraded by the literal migration command; no data is rewritten.

## Failure/idempotency/security cases

- upgrade on a database that already holds `stage_result` rows: no row changes, the new CHECK is validated
- the CITE row is refused at `0032` and accepted at `0033`; a lookalike id is refused at `0033`
- the downgrade refuses while one row carries the new id, changes nothing, and runs once the row is gone
- the upgrade after a downgrade restores the same constraint definition
- the two other stage CHECKs stay at nine ids

## Rollback / feature flag

Rollback is the downgrade (`alembic downgrade 0032_ar_v3_run_group`), which refuses while a CITE row exists: restore a backup then. No feature flag: nothing publishes through the AR v3 group until the registry is filled (`D-204`).

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report
- integration notes: see the report
