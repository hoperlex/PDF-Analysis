# Task ANALYSIS-PRESETS-01 — named executor selections for a run, chosen at start and recorded on the run

task_id: ANALYSIS-PRESETS-01
status: completed in development candidate (written by the integrator from the lane's hand-back; the lane could not create new markdown files)

## Outcome

Under owner ruling `R-146av` an administrator can save a **preset** — a name plus an executor connection — as append-only revisions in «Настройки анализа»; an expert chooses it at run start instead of picking the executor by hand; the run records the preset revision it used and the run page shows it. A run started with a preset equals the hand-started run in every column except ids, clock and the preset. Migration `0037_analysis_presets` is the head; the contract stays `1.8.0` (four additive operations, surface 98 paths / 111 operations / 321 schemas).

## Depends on

- `R-146av`, `A-8` — recorded in `docs/program/OWNER_RULINGS_2026-09-17.md` and `PRODUCTION-READINESS-PLAN-01.md`.
- `PRODUCTION-WAVE-PW5` section 6 — the brief.
- `EXEC-PAR-START-01`, `EXEC-PAR-QUEUE-01`, `EXEC-PAR-WEB-01` — completed; the run start already takes `executor_connection_id`.
- `COMPARE-PERSISTED-SUMMARY-01`, `AR-V3-DECISIONS-01` — completed; the precedents for a contract + migration lane.

## Frozen inputs

- domain contract: unchanged (the new constraint/conflict words are not added to `contracts/domain/v1/error-codes.json`)
- API contract: `1.8.0`, additive; `95` paths / `107` operations / `314` schemas before, `98` / `111` / `321` after
- analysis/comparison/event contract: not_applicable
- migration head: `0036_cite_partition_v3` before, `0037_analysis_presets` after
- base commit: `05f4584d` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: ANALYSIS-PRESETS-01
- totality_query: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(len(d['paths']),sum(len([m for m in v if m in ('get','post','put','patch','delete')]) for v in d['paths'].values()),len(d['components']['schemas']))"` prints `98 111 321`

## Captured premise evidence

- premise: the lane printed from the code what a run start can take; the preset therefore holds only a name and an executor connection

### P-01 — the per-run fields of a start

- captured_at: 2026-10-27
- command: reading `startRun`, `reauditRun`, the group start and the run-start commands under `src/auditmanager/runs/commands.py` and `src/auditmanager/api/schemas/models.py`
- result: the only per-run fields of `startRun` are `executor_connection_id` and `provider_mode`; `provider_mode` is refused unless it equals the deployment's own; `reauditRun` takes no body; the group start takes only a version; the profile is routed from the version's classification; the cost ceiling is the process-wide `AUDITMANAGER_RUN_COST_CEILING_USD`; no threshold is an input of a start.

### P-02 — identifiers

- captured_at: 2026-10-27
- command: reading `contracts/domain/identifiers.json` and `src/auditmanager/shared/identity`
- result: a new id prefix needs those two places and the pin of 48; they are outside the lane's grant, so preset and revision ids are `evt_` ids, as `summary_id` is in `0035`.

### P-03 — the closest precedents

- captured_at: 2026-10-27
- command: reading `docs/program/COMPARE-PERSISTED-SUMMARY-01.md` and `docs/program/AR-V3-DECISIONS-01.md`
- result: the method for the migration, the head pins, the grants/erase classification and the contract reseal is the one these two lanes used.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `db/migrations/versions/20261027_0037_analysis_presets.py` and the head pins it requires
- `src/auditmanager/executors/**` (presets, commands, audit writer), `src/auditmanager/runs/**` (the record and the application at start), `src/auditmanager/bootstrap/{adapters,composition}.py`, `src/auditmanager/api/**`
- `contracts/api/v1/openapi.json`, `web/openapi/openapi.json`, the generated client, `web/FRONTEND_LOCK.json`
- `scripts/recovery/{schema_coverage,grant_classification,project_erase,product_purge}.py`, `infra/deploy/apply-grants.sh` (classification only)
- `web/src/_pages/analysis-settings/**`, `web/src/entities/**`, `web/src/features/**`, `web/src/widgets/**` for the preset UI and the start control, and their tests
- `docs/program/ANALYSIS-PRESETS-01.md`, `docs/program/tasks/ANALYSIS-PRESETS-01.md`

## Forbidden hotspots

- the section profile packages, optimisation, comparison, АР v3 run code
- root dependency/lock files
- the version literal of the contract (no version move)
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings, ADRs (the integrator edits these)

## Non-goals

- a per-run cost limit or a threshold (not selectable per run in the code)
- a preset for a re-audit or the six-check group start
- a dedicated id prefix for presets
- any live call

## Deliverables

- migration `0037_analysis_presets` with the chain trigger, the immutability triggers and the frozen guard on `audit_run.preset_revision_id`
- four keyed operations, the preset on the run start and on the run record, the preset section and the start choice in the web
- `docs/program/ANALYSIS-PRESETS-01.md` (written by the integrator from the lane's hand-back)

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit tests/contract tests/integration/db tests/integration/recovery tests/integration/runs tests/integration/api tests/integration/executors --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py`
- expected: all pass (the DB directories on a private migrated database); web `vitest run`, `tsc --noEmit`, `eslint .`, `npm --prefix web run api:verify` green

## Integration contract

The integrator can rely on: (1) `listAnalysisPresets`-style reads are open to every role, create/revise/archive are administrator-only, and choosing a preset at `startRun` needs the expert role; (2) a start carries either a preset or an executor, never both (`422`); an unknown preset is `422 unknown_preset`, an archived one `409 preset_archived`, both before the idempotency key is claimed; (3) the preset's CURRENT revision is applied at start and the run records `preset_revision_id`; (4) the database refuses an update or delete of a preset revision, a gap in revision numbers, a revision after an archive, a duplicate active name (case-insensitive), an archived connection, and more than 100 presets; (5) the migration's downgrade refuses while rows exist.

## Failure/idempotency/security cases

- the same idempotency key with a different preset, or with a hand-chosen executor after a preset start, is `idempotency_key_reuse`
- a retry of a preset start after the preset was revised replays the first run (the fingerprint carries `preset_id`)
- an audit write failure rolls the revision back (same transaction)
- two writers racing for the same name or the same gap: the advisory lock serialises them
- a run cannot claim a preset revision whose connection it did not freeze

## Rollback / feature flag

Not a flag. The migration's downgrade drops exactly what `0037` created and refuses while any preset row exists; the web section and the start choice are separate commits (`2ea15ac0`, `5804ee45`) that can be reverted without touching the server.

## Handoff

- changed files: see `docs/program/ANALYSIS-PRESETS-01.md` and `git diff --name-only 05f4584d..5804ee45`
- commands/results: see `docs/program/ANALYSIS-PRESETS-01.md`
- known limits: the current revision is applied at start (no expected revision); archiving a connection does not archive presets that name it; no per-run limit or threshold exists to hold
- integration notes: the files pinning head `0037` and the surface counts are listed in `docs/program/ANALYSIS-PRESETS-01.md`; the prose patch (98/111/321, head 0037) was applied by the integrator
