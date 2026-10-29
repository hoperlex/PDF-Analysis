# Task CMP-VC-AISHEET-01 — the AI description of sheet changes: per-sheet packets, the checked description, the per-series run, the review list, the Markdown of a sheet

## Outcome
On `integration/compare-modules` the fifteen operations of `CMP-SEAL-C2` section 3 that belong to `ComparisonAiSheetAdapter` answer instead of
`503`: `estimate`, `get`, `start`, `pause`, `resume`, `cancel`, `finish`, `dequeue` and `retry` of `ComparisonAiSheetChanges`;
`getComparisonSheetDescription`, `startComparisonSheetDescription`, `estimateComparisonSheetDescription`,
`listComparisonSheetDescriptionHistory`, `streamComparisonSheetDescriptionMd` and `listComparisonReviewSheets`. The lane is the `sheet_changes`
method of the shared AI-job core (`CMP-AI-JOBS-01`): it supplies an `AiMethod` and a work handler of kind `comparison_sheet_changes`, and it
writes `comparison_ai_sheet_item` and `comparison_sheet_description` (never `comparison_ai_job`). Per sheet pair of a series with differences
the handler builds the original's packet (tables, places, shifts, with crops and words, from the engine's raw evidence), asks the routed
model once through the spend wrapper (recorded mode in every test), checks the answer by program (a claim about a place or a number the raw
evidence does not contain is `unverified`, never a confirmed change), and stores the description content-keyed by the pair result, the prompt
version and the model, so a stored description is never sent again. The Markdown of a sheet has the same bytes for the same description.
Each safety guard is shown failing under a quoted mutation.

## Depends on
- CMP-AI-JOBS-01 (`ComparisonAiJobService`, `AiMethod`, `RecordedAnswers`, `ai_jobs_support.py`)
- CMP-SEAL-C2 (contract `1.11.0`, migration `0040_comparison_ai_reports`: `comparison_ai_sheet_item`, `comparison_sheet_description`)
- CMP-SPEND-01 (`ComparisonModelCaller`), CMP-EXEC-IMAGES-01 (`attach_images`, at most 8 images), CMP-WORK-01 (`WorkItem`, handlers)
- CMP-ENGINE-01 (the stored result and its raw evidence), CMP-SERIES-01 (sheet pairs, transitions, permit records), CMP-PROFILE-01 (words,
  vector lines, stored previews and tiles), CMP-C1-FIX-A

## Frozen inputs
- domain contract: `contracts/domain/v1/**` (prefixes `csi`, `csd` exist)
- API contract: `contracts/api/v1/openapi.json` `1.11.0`, 176 paths / 198 operations / 517 schemas (this lane changes none)
- analysis/comparison/event contract: ADR-0025 decisions 3, 4, 10, 11, 12, 14, 15, 16, 17-23 and the addenda; plan `A-6`, `A-8`, `A-12`, `R3-02`,
  `R3-08`; the original at commit `23f379fd` (`version_comparison_ai/sheet_changes/*`, cited by file and line in the report)
- migration head: `0040_comparison_ai_reports` (this lane changes none; a missing column is a STOP to the wave's FIX slot)
- base commit: `0f6a008d91f4fbdf1fd7a3b2561dae57392fa8da`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

(The sets this lane edits are those of the wave brief's wiring rule: `SEALED_STUB_GETS` / `SEALED_STUB_QUERY`
(`test_router_answers.py`), `SEALED_STUB_ADDRESSED` / `SEALED_STUB_COLLECTIONS` / `EXPECTED_ADDRESSED`
(`test_an_absent_parent_is_not_an_empty_page.py`), `WIRED` (`test_comparison_ai_stub_operations.py`), `SEALED_NOT_YET_WRITTEN`
(`grant_classification.py`) and the `HANDLER_FACTORIES` pins; each edit removes or adds this lane's own members only.)

## Captured premise evidence
- premise: contract `1.11.0`, 176 paths / 198 operations / 517 schemas, head `0040_comparison_ai_reports`, base `0f6a008d` (wave C2 brief); the
  lane re-read them before any edit and STOPs if they differ

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; ls db/migrations/versions | tail -1; grep -n "^revision: str" db/migrations/versions/20261029_0040_comparison_ai_reports.py`
- captured_output:
  ```text
  0f6a008d91f4fbdf1fd7a3b2561dae57392fa8da
  contract 1.11.0 176 paths 198 operations 517 schemas
  0.9.0
  20261029_0040_comparison_ai_reports.py
  69:revision: str = "0040_comparison_ai_reports"
  ```
- interpretation: equal to the premise (contract `1.11.0`, 176 / 198 / 517, head `0040_comparison_ai_reports`), so the lane did not STOP

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/ai_sheets/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/ports.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/comparison/ai_sheets/**`
- `tests/integration/comparison/ai_sheets/**`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_ai_stub_operations.py`
- `tests/unit/comparison/engine/test_handler_unit.py`
- `tests/unit/comparison/work/test_composition_unit.py`
- `docs/program/CMP-VC-AISHEET-01.md`
- `docs/program/tasks/CMP-VC-AISHEET-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-vc-aisheet-01`
- postgres_port: `57970`
- s3_api_port: `61970`
- s3_console_port: `61971`
- postgres_db: `auditmanager_cmp_vc_aisheet_01`
- s3_bucket: `auditmanager-cmp-vc-aisheet-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**` (no column is missing; a missing one is a STOP to the wave's FIX slot)
- `src/auditmanager/comparison/ai_jobs/**`, `comparison/work/**`, `comparison/spend/**`, `comparison/series/**`, `comparison/engine/**`,
  `comparison/profile/**` (read through `comparison/public.py` names only)
- `src/auditmanager/jobs/**`, `src/auditmanager/executors/**`, `src/auditmanager/analysis/**`, `src/auditmanager/workers/**`
- the bodies of the other C2 adapters (`ComparisonAiPairAdapter`, `ComparisonSpecificationAdapter`, `ComparisonLaunchQueueAdapter`,
  `ComparisonReportAdapter`) and their lines in the shared registers
- root dependency / lock files, global styles, `web/**`, `infra/**`, `tests/support/**`, any other `conftest.py`

## Non-goals
- no live model call and no live adapter wiring: every test runs in recorded mode; the handler takes its model route and its crop store from
  two seams (report section 6 names what the composition root still has to supply)
- no whole-specification description (`source = whole_specification` is the SPEC lane's) and no PDF or MD summary of a series (REPORT)
- no launch queue and no installation AI queue read (`CMP-VC-QUEUE-01`)
- the AI output is never the expert's decision and never rewrites the raw comparison evidence

## Deliverables
1. `src/auditmanager/comparison/ai_sheets/`: the packet (candidates, tables, places, shifts, crops, prompt), the checked description, the
   per-sheet run, the single-sheet description, the states, the transition progress, the review list, the Markdown, the repository, the
   `AiMethod`, the service, the handler.
2. `ComparisonAiSheetAdapter` (the fifteen bodies, the module-flag refusal kept first) and its one constructor line; the register edits.
3. Unit and integration tests with a mutation proof for each guard; the report `docs/program/CMP-VC-AISHEET-01.md`.

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-aisheet-01/unit tests/unit/comparison/ai_sheets`
- expected: all pass, no container needed
- command: `... pytest -q --basetemp=/tmp/pytest-cmp-vc-aisheet-01/integ tests/integration/comparison/ai_sheets`
- expected: all pass on the lane's own stack (`make up`, `make migrate`)
- command: `... pytest -q tests/integration/comparison` (one process), the whole `tests/integration/composition`, then the whole `tests/unit` and
  `tests/contract` minus the three `D-220` files after the last code commit
- expected: all pass

## Integration contract
The adapter answers the contract's shapes; the job object, the estimate, the consent and every state edge are `CMP-AI-JOBS-01`'s. The handler's
kind is `comparison_sheet_changes` (the executor work kind) and is appended to `HANDLER_FACTORIES`. `CMP-VC-REPORT-01` reads the stored
descriptions through `comparison.public.ComparisonAiSheetService` (`read_md`, `descriptions_of_transition`); `CMP-VC-QUEUE-01` calls
the service's start for a series; `CMP-VC-UI-02` renders the eleven states and the three tiers. A lane that needs another field STOPs to the
wave's FIX slot.

## Failure/idempotency/security cases
- the module flag is the first statement of every adapter method; a keyed write replays on the same key and payload
- a stored description under the same content key is never requested again; a retry touches only the failed sheets
- a claim the raw evidence does not contain is `unverified`; images per request are at most 8; the Markdown has stable bytes
- an administrator without the expert role is refused every write; a read is any one role

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES` (default `none`) keeps all fifteen operations at `503 comparison_modules`; the handler claims nothing while
the versions module is off.

## Handoff
- changed files: (written at the end of the lane)
- commands/results: (written at the end of the lane)
- known limits: (written at the end of the lane)
- integration notes: (written at the end of the lane)
