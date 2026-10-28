# Task CMP-C1-FIX-B — the web FIX slot of wave C1: the screens aligned with the overview, the viewer in Russian, the markers and the queue mount

task_id: CMP-C1-FIX-B
status: in progress (lane `agent/cmp-c1-fix-b`, wave C1, size M, web only; nothing pushed, merged or tagged)

## Outcome

`CMP-VC-UI-01` built the screens of «Сравнение версий» before `CMP-VC-OVERVIEW-01` merged and guessed some of its semantics. This task aligns them with the merged overview (`docs/program/CMP-VC-OVERVIEW-01.md` section 6, binding) and closes the web items the reports of C1 left:

1. **Row group and counters = the server's rule** (OVERVIEW section 6.3): no `next_step` → ready; `steps[next_step].state` in (queued, running, pausing) → running; `failed` and `next_step` in (upload, profile, matrix) → failed; otherwise waiting (a failed series is waiting). The client rule of VC-UI-01 is replaced, and a test over every state combination proves the recomputed counters equal the server's `counters.*` for the same rows.
2. **Step words, tones, chip text and actions = OVERVIEW sections 6.2 and 6.4**: the state → word (tone) tables of profile, matrix and series; the chip's sentence by the step it names and its state; the actions «Подготовить»/«Повторить» → `prepareComparisonMatrix`, «Запустить»/«Заново» → `startComparisonSeries`, «Продолжить» → `resumeComparisonSeries` for a paused series only, «Досчитать» → `finishComparisonSeries` for a failed or interrupted series with something left (only a command the series service accepts); steps 4/6/7 are `not_applicable` («—», tone off); the `ComparisonStepCounts` members read are confirmed against section 6.1.
3. **The viewer's words**: `widgets/comparison-viewer` no longer prints Latin «A»/«B» or the engine's zone and field names; its mounting shapes join the rendered-language guard (they are census-only today).
4. **Reason words**: the viewer imports `pairReasonWords` of `entities/version-series` instead of its stopgap table (`SPLIT_SHEET` and `UNCHECKED_CHANNEL_<CHANNEL>` were missing).
5. **Markers**: `data-layer` on the viewer's layer toggles and `data-channel-state` on the channel chips; `ComparisonLayer` and `ComparisonChannelState` join `TRANSLATED_SCHEMAS` with markers.
6. **The queue block mount**: the read-only «Сравнение» block is mounted with one line in `web/src/_pages/queue/**` and the slot inside `widgets/execution-queue` is removed.

## Depends on

- `CMP-VC-OVERVIEW-01` and `CMP-VC-UI-01` — completed and merged (base `0e867b12`, `integration/compare-modules`).
- `CMP-VIEWER-01`, `CMP-SERIES-01` — completed (the viewer widget; the series commands and their allowed transitions).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.10.0`, 131 paths / 148 operations / 432 schemas, unchanged (`contracts/**`, `web/openapi/**`, the generated client and `web/FRONTEND_LOCK.json` are not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0039_comparison_core`, unchanged
- base commit: `0e867b12cbbfbed1e048e2142748f6286edc6a50`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The lane adds no route, screen, error code or migration. `TRANSLATED_SCHEMAS` of `web/tests/guards/rendered-language.guard.test.ts` gains two names with their markers (item 5); the C2 seal edits the same guard file for its own schemas, so the hunks are kept minimal.

## Captured premise evidence

- premise: contract 1.10.0 with 131 paths / 148 operations / 432 schemas and head 0039_comparison_core; the viewer prints Latin side letters and engine zone and field names at 13 places; neither marker exists; the queue block is mounted by a slot inside the widget

### P-01 — the wave's base facts

- captured_at: 2026-10-29
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(d['info']['version'], len(d['paths']), sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"; grep -n 'revision: str = ' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  1.10.0 131 148 432
  79:revision: str = "0039_comparison_core"
  0e867b12cbbfbed1e048e2142748f6286edc6a50
  ```
- interpretation: the premise of the brief holds (contract `1.10.0`, 131/148/432, head `0039_comparison_core`), so the lane went on.

### P-02 — the viewer's Latin side letters and engine words, and the missing markers

- captured_at: 2026-10-29
- command: `grep -rnE "Лист [AB]|\(B\)|\(A\)|Совмещение B на A|зона «|поле «|под ней лист|листа [AB]|лист [AB]" web/src/widgets/comparison-viewer | wc -l; grep -rn "data-layer\|data-channel-state" web/src | wc -l`
- captured_output:
  ```text
  13
  0
  ```
- interpretation: thirteen lines of the viewer carry a Latin side letter or print the engine's `zone`/`field` names; no `data-layer` or `data-channel-state` marker exists anywhere in `web/src`. Both are the premise of items 3 and 5.

### P-03 — the queue block is mounted through a slot inside the widget

- captured_at: 2026-10-29
- command: `grep -rn "ComparisonQueueSlot" web/src`
- captured_output:
  ```text
  web/src/widgets/execution-queue/ui/execution-queue.tsx:9:import { ComparisonQueueSlot } from './comparison-queue-block';
  web/src/widgets/execution-queue/ui/execution-queue.tsx:37:      <ComparisonQueueSlot />
  web/src/widgets/execution-queue/ui/comparison-queue-block.tsx:118:export function ComparisonQueueSlot() {
  ```
- interpretation: the slot is drawn by the list widget itself; the clean mount is one line in the page (item 6).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/widgets/version-series/**`
- `web/src/entities/version-series/**`
- `web/src/_pages/version-compare/**`
- `web/src/widgets/comparison-viewer/**`
- `web/src/widgets/execution-queue/**`
- `web/src/_pages/queue/**`
- `web/tests/**`
- `docs/program/CMP-C1-FIX-B.md`
- `docs/program/tasks/CMP-C1-FIX-B.md`

`web/src/widgets/comparison-viewer/**` is changed for items 3-5 only; `web/src/widgets/execution-queue/**` and `web/src/_pages/queue/**` for item 6 only; `web/tests/**` for the screens' unit tests, the census (`web/tests/unit/styles/screens.ts`) and the guards they touch (`web/tests/guards/rendered-language.guard.test.ts`). Any other file: STOP and report.

## Forbidden hotspots

- `src/**` (no backend file), `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `db/migrations/**`
- root dependency and lock files (`web/package.json`, `web/package-lock.json`); no new npm package
- `web/src/app/globals.css` and every global style; the composition root; no colour literal, custom property or `:not()` in a module stylesheet
- `docs/program/CURRENT_STATE.md` and the other process documents

## Non-goals

- the menu entry that stays when the module is off (needs `_app/**`)
- steps 4, 6 and 7 (wave C2), the plain sheet view, the AI hints
- a `group` member or a chip text on the contract (OVERVIEW FIX candidates 2 and 3: a contract change)

## Deliverables

- `entities/version-series` (the group rule, the step tables, the chip sentences, the step actions), `widgets/version-series` (the chip and the cells), `widgets/comparison-viewer` (the Russian words, the markers, the imported reason table), `widgets/execution-queue` and `_pages/queue` (the mount)
- tests for each item, each shown failing under a quoted mutation (items 1, 2, 4, 5)
- the report `docs/program/CMP-C1-FIX-B.md`

## Required tests

- command: `git diff --check`; `npm --prefix web run lint -- --quiet`; `npm --prefix web run typecheck`; `npm --prefix web run api:verify`
- expected: exit 0 each
- command: `cd web && AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent npx vitest run <the lane's files> tests/guards tests/unit/styles tests/unit/shell tests/unit/version-compare tests/unit/comparison`
- expected: green
- command: `cd web && npx vitest run --maxWorkers=4` once at the end
- expected: green
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent .venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py --basetemp=$PWD/.pytest-tmp` and `tests/e2e/test_pc01_journey_conformance.py`
- expected: green
- command: mutation proofs (red, restore, green) for items 1, 2, 4 and 5
- expected: each guard fails under its mutation

## Integration contract

- merge after `CMP-VC-UI-01`; the shared hunks are in `web/tests/guards/rendered-language.guard.test.ts` (two schemas, two markers, the viewer shapes no longer census-only) and `web/tests/unit/styles/screens.ts` (only if a rule is added); the C2 seal edits the same guard file for its schemas
- `ComparisonViewer(pair, rasterSize?, navigation?)` keeps its props; the markup gains `data-layer` and `data-channel-state`

## Failure/idempotency/security cases

- a command the server would refuse (a restart of a live series, a resume of a series that is not paused, a finish with nothing left) is not offered; a refusal that still arrives is shown in words as before
- no code is printed: an unknown reason, zone or field is said in words

## Rollback / feature flag

Not applicable: no behaviour behind a flag. Reverting the lane's commits restores the guesses of `CMP-VC-UI-01`.

## Handoff

(written with the report as the last commit)
