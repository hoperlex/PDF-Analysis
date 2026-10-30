# Task CMP-VC-UI-02 — the C2 screens of «Сравнение версий»: AI steps 4/6/7, the queue strips, the blocks of «Сравнение листов», the PDF report window and the side panel «Изменения в листе»

task_id: CMP-VC-UI-02
status: done (lane `agent/cmp-vc-ui-02`, wave C2, size L, web only; nothing pushed, merged or tagged)

## Outcome

Against the sealed contract `1.11.0` (every C2 operation is a stub answering `503 dependency_unavailable` until its backend lane merges), the lane builds the screens of plan §1.1 that wave C2 adds (`docs/program/CMP-SEAL-C2.md` §3 operations and §9 row `CMP-VC-UI-02`):

1. **«Проекты и этапы»**: the cells and dialogs of steps 4 «ИИ-проверка сомнительных пар», 6 «ИИ-описание изменений» and 7 «Сводка и отчёт»; the checkboxes per row and «выбрать все» per column for steps 4–7 and the selection bar «Запустить выбранные по очереди» / «Снять выбор»; the strip «Очередь запуска» and the installation's AI queue «Очередь «ИИ-описание изменений»»; the per-row «Сводка изменений (MD)».
2. **Every AI start shows the estimate and the consent line** (one shared estimate/consent dialog: calls, images, image bytes, prompt size, model, USD estimate or «без учёта стоимости», the two ceilings, «Подтверждаю передачу … исполнителю»; the start carries the digest of the estimate that was shown; the stale-estimate, ceiling and overrun-pause refusals in Russian).
3. **«Сравнение листов»**: the blocks «ИИ-описание изменений», «Полные спецификации (СО)», «Сводка MD и отчёт для заказчика»; the AI flags and hints in matrix cells («ИИ», «ИИ ?», «🌙 ИИ: вероятно стр. N») joined from `listComparisonAiPairHints` by `(version_uid, page)`.
4. **The PDF report window** «Сформировать PDF-отчёт…» (source, kinds, reuse, cancel, continue, «Пересобрать PDF», delete, «Исходный MD», «Подготовить отчёт для заказчика», per-transition tables, history, downloads).
5. **The side panel «Изменения в листе»** of the viewer and the evidence banner («Из ИИ-описания: …», «доказательство N из M», «Обзор всех / Один фрагмент»). Every AI text carries the «не подтверждено инженером» label; a recorded (test) answer is labelled as such.
6. **Words**: a Russian sentence for every new reason of the seal (§3), the new enums in `TRANSLATED_SCHEMAS` with markers (append-only hunks).

A module whose operation answers `503 dependency_unavailable` is a **state** on every screen («Модуль ещё недоступен»), never a crash.

## Depends on

- `CMP-SEAL-C2` (contract `1.11.0`, the regenerated client) and the C1 lanes with their two FIX lanes — completed and merged (base `901914a5`, `integration/compare-modules`).
- `CMP-VC-UI-01`, `CMP-C1-FIX-B`, `CMP-VC-OVERVIEW-01`, `CMP-VIEWER-01` — the screens extended here.
- The backend lanes `CMP-AI-JOBS-01`, `CMP-VC-SPEC-01`, `CMP-VC-AIPAIR-01`, `CMP-VC-AISHEET-01`, `CMP-VC-REPORT-01`, `CMP-VC-QUEUE-01` run in parallel; this lane merges last and adapts to the integrator's notes.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas, unchanged (`contracts/**`, `web/openapi/**`, the generated client and `web/FRONTEND_LOCK.json` are not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0040_comparison_ai_reports`, unchanged
- base commit: `901914a5520a2d90b22b0c5c3fcdae1fa3f6e438`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The lane adds no route and no error code. The new widget `web/src/widgets/comparison-report/**` is mounted by the existing page `_pages/version-compare`. `COMPARISON_SHAPES` (`web/tests/unit/version-compare/shapes.ts`) is the one list that the contrast census and the language guard both render, so a new shape is in both; `TRANSLATED_SCHEMAS` and `SCHEMA_MARKERS` of `web/tests/guards/rendered-language.guard.test.ts` get appended names and rows only.

## Captured premise evidence

- premise: contract 1.11.0 with 176 paths / 198 operations / 517 schemas and head 0040_comparison_ai_reports; no screen of `web/src` reads or sends any of the fifty C2 operations; steps 4, 6 and 7 have no column in the table

### P-01 — the wave's base facts

- captured_at: 2026-10-29
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(d['info']['version'], len(d['paths']), sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"; grep -n 'revision: str = ' db/migrations/versions/20261029_0040_comparison_ai_reports.py; git rev-parse HEAD`
- captured_output:
  ```text
  1.11.0 176 198 517
  69:revision: str = "0040_comparison_ai_reports"
  901914a5520a2d90b22b0c5c3fcdae1fa3f6e438
  ```
- interpretation: the premise of the brief holds (contract `1.11.0`, 176/198/517, head `0040_comparison_ai_reports`), so the lane went on.

### P-02 — no screen uses a C2 operation yet

- captured_at: 2026-10-29
- command: `grep -rn "getComparisonAiQueue\|listComparisonAiPairHints\|createComparisonReport" web/src --include=*.ts --include=*.tsx -l | grep -v generated | wc -l; grep -rnE "LATER_STEPS|ai_pairs|ai_changes" web/src --include=*.ts --include=*.tsx -l | grep -v generated`
- captured_output:
  ```text
  0
  web/src/widgets/version-series/ui/projects-and-stages.tsx
  web/src/entities/version-series/index.ts
  web/src/entities/version-series/model/overview-view.ts
  web/src/entities/version-series/model/steps.ts
  ```
- interpretation: no screen calls a C2 operation; the table names steps 4, 6 and 7 only as «появятся позже» (`LATER_STEPS`) and in the next-step chip.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/_pages/version-compare/**`
- `web/src/widgets/version-series/**`
- `web/src/widgets/comparison-report/**` (new)
- `web/src/widgets/comparison-viewer/**` (the side panel and the evidence banner only)
- `web/src/entities/version-series/**`
- `web/src/widgets/execution-queue/**` (the AI queue block only)
- the reason-sentence file(s) (comparison reasons only): `web/src/entities/version-series/model/failure.ts`
- `web/tests/**` (the lane's screens, the census blocks in `web/tests/unit/styles/screens.ts`, the guards they touch: `web/tests/guards/rendered-language.guard.test.ts` markers)
- `docs/program/CMP-VC-UI-02.md`
- `docs/program/tasks/CMP-VC-UI-02.md`

Any other file: STOP and report.

## Forbidden hotspots

- `src/**` (no backend file), `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `db/migrations/**`
- root dependency and lock files (`web/package.json`, `web/package-lock.json`); no new npm package
- `web/src/app/globals.css` and every global style; the composition root; no colour literal, custom property or `:not()` in a module stylesheet
- `docs/program/CURRENT_STATE.md` and the other process documents

## Non-goals

- any backend, contract, migration or generated-client change; a missing field is a STOP to the FIX slot
- the menu entry that stays when the module is off (needs `_app/**`); the plain sheet view
- «Сравнение стадий» (waves C3–C4)

## Deliverables

- `entities/version-series` (the reads and commands of the C2 surface, the Russian words, the estimate/consent model, the shared estimate panel and the AI label), `widgets/version-series` (steps 4/6/7, selection, queue strips, the three blocks, the hints in cells), `widgets/comparison-report` (the report window), `widgets/comparison-viewer` (the side panel and the evidence banner), `widgets/execution-queue` (the AI queue block), `_pages/version-compare` (composition)
- tests for each commitment, each shown failing under a quoted mutation (consent digest, stale estimate re-asks, the «не подтверждено инженером» label, the recorded-answer label, `503` without a crash, the census block)
- the report `docs/program/CMP-VC-UI-02.md`

## Required tests

- command: `git diff --check`; `npm --prefix web run lint -- --quiet`; `npm --prefix web run typecheck`; `npm --prefix web run api:verify`
- expected: exit 0 each
- command: `cd web && AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent npx vitest run <the lane's files> tests/guards tests/unit/styles tests/unit/shell tests/unit/version-compare tests/unit/comparison`
- expected: green
- command: `cd web && npx vitest run --maxWorkers=4` once at the end
- expected: green
- command: `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py --basetemp=/tmp/pytest-cmp-vc-ui-02/<run>` and `tests/e2e/test_pc01_journey_conformance.py`
- expected: green
- command: mutation proofs (red, restore, green)
- expected: each guard fails under its mutation

## Integration contract

- merge last among the wave's lanes; the shared hunks are in `web/tests/guards/rendered-language.guard.test.ts` (names appended to `TRANSLATED_SCHEMAS`, rows to `SCHEMA_MARKERS`) and `web/tests/unit/version-compare/shapes.ts`
- `ComparisonViewer(pair, rasterSize?, navigation?)` keeps its props and gains optional ones for the side panel
- the screens adapt to the backend notes the integrator sends as the lanes merge

## Failure/idempotency/security cases

- every write carries an `Idempotency-Key` minted when the reader expresses the intent and reused on every retry; a start carries the digest of the estimate the reader saw, never one computed elsewhere; a stale digest (`409 comparison_estimate_stale`) re-reads the estimate and asks again
- a reader who is not an expert sees the state and no control that sends anything; a module that is off or not wired is a state
- AI output is never an expert's decision and never replaces raw evidence: every AI text is labelled «не подтверждено инженером»; a recorded answer says so

## Rollback / feature flag

Not applicable: no behaviour behind a flag (the module flag `ProductVersion.comparison_modules` already gates the screens). Reverting the lane's commits restores the C1 screens.

## Handoff

Report: [`../CMP-VC-UI-02.md`](../CMP-VC-UI-02.md). Branch `agent/cmp-vc-ui-02`, base `901914a5`; nothing pushed, nothing merged, no tag.

**Changed files** (`git diff --name-only 901914a5..HEAD`): under `web/src/` the entity `version-series` (model, api, ui), the widgets `version-series`, `comparison-report` (new), `comparison-viewer` (side panel and evidence banner), `execution-queue` (the AI queue block) and the page `_pages/version-compare`; under `web/tests/` the fixtures, shapes, seeds and tests of `unit/version-compare`, the census block of `unit/styles/screens.ts`, `guards/rendered-language.guard.test.ts` and `unit/run/polling.test.ts`; this file and the report.

**Checks** (report section 11): `git diff --check`, `lint --quiet`, `typecheck`, `api:verify` exit 0; the whole web suite 219 files / 3651 tests in two invocations (a single run stops on the worker's RPC timeout after the three heaviest files); `tests/contract` without the three `D-220` files plus the journey conformance 1445 passed (`--basetemp` outside the repository); mutation proofs M1–M10 each red then green (report section 7).

**Contracts:** none new, none changed. **Forbidden hotspots:** `git diff --name-only 901914a5..HEAD -- contracts db src pyproject.toml uv.lock docs/program/P02_LOCK.json web/package.json web/package-lock.json web/FRONTEND_LOCK.json web/openapi web/src/shared web/src/app web/src/_app infra Makefile docs/program/CURRENT_STATE.md` prints nothing.

**Known limits** (report section 8): a report has no pause in the contract («Отменить» instead); the overview serves steps 4/6/7 as `not_applicable`, so the cells read the AI layer per row; two guard hunks beyond appended names (`MD` in `NOT_DERIVABLE`, the polling allowlist); the census is about 30 % slower and the whole suite is run in two invocations.

**For the integrator:** merge last among the wave's lanes. The shared files are `web/tests/guards/rendered-language.guard.test.ts` (23 names appended to `TRANSLATED_SCHEMAS`, 23 rows appended to `SCHEMA_MARKERS`, one `NOT_DERIVABLE` entry, the cap 20 to 21), `web/tests/unit/run/polling.test.ts` (one path) and `web/tests/unit/version-compare/shapes.ts`. The screens adapt to the backend lanes' notes through `web/src/entities/version-series/api/use-ai*.ts` and the confirmations in report section 9. No symlink or untracked file is left (`web/node_modules`, a link to the read-only `cmp-seal-c0` install, is removed before the last commit).
