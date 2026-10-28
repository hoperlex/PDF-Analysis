# Task CMP-VC-UI-01 — the screens of «Сравнение версий»: projects and steps, the sheet matrix, the upload dialogs

task_id: CMP-VC-UI-01
status: in progress (lane `agent/cmp-vc-ui-01`, wave C1, size L, web only; nothing pushed, merged or tagged)

## Outcome

A menu item «Сравнение версий» in the group «Работа» opens `/version-comparison`, a screen with two tabs for one chosen project.

* Tab «Проекты и этапы»: the counters «Все / Ждут действия / Идут / Ошибки / Готовы» and «N версий · M переходов», «Поиск по шифру…», the filters and the sort, «Обновить» with the time, the legend, the strip «В загрузке, ещё не в списке проектов», and the table «Проект · следующий шаг» (the next-step chip; a row click opens the second tab), «Версии», «1 Загрузка», «2 Разбор версий» («Повторить»), «3 Сопоставление листов» («Подготовить»), «5 Сравнение соседних» («Запустить», «Пауза», «Продолжить», «Заново»), from `getComparisonOverview`; the button «Загрузить проект со всеми версиями».
* The upload dialogs over the C0 operations: the single upload with its proposal («Подтвердить группировку и порядок») and the multi-project batch «Загрузка нескольких проектов» (chunked transfer that can stop and continue, «Удалить пакет», «После подготовки сравнить все соседние версии», «Пауза после текущего проекта», «Подтвердить порядок во всех проектах», «Исключить», «Повторить», the status labels).
* Tab «Сравнение листов» for one document set: «· версий: N», «Применить сопоставления (N)» and «Отменить правку» while a draft exists, «Порядок версий», the A/B side choice, the block «Сводка переходов» (progress, «Листов», «✓ ◐ ● ⚠», «Состав +N / −M», the verdict sentence built from the verdict codes, «Открыть», «Отменить» / «Продолжить» / «Досчитать»), the matrix «Лист \ версия» (thumbnails, flags, candidates, «Связать», «Отметить, что этого листа в версии нет», «⤫ Отвязать в отдельную строку», drag and drop, «Несвязанные страницы»), the draft applied in one batch against the revision and rebased on `409 comparison_matrix_stale`, undo, orphaned edits and stale reasons; opening a pair mounts `ComparisonViewer`.
* A-12: while `ProductVersion.comparison_modules` names the versions module, the version-scoped screen offers none of the three `0035` controls (approve, withdraw, generate summary) and points to «Сравнение версий».
* The read-only block «Сравнение» in «Очередь» from `getComparisonQueueSummary`.
* A Russian sentence for every reason of contracts 1.9.0 and 1.10.0 a comparison screen can show; the new enums that these screens render in `TRANSLATED_SCHEMAS` with markers.
* The heading of the version-scoped screen no longer reads like the new menu item.

A module whose operations answer `503 dependency_unavailable` is a normal state of every screen above («Модуль ещё недоступен» in the words of the existing error mechanism), never a crash.

## Depends on

- `CMP-SEAL-C1` — completed (contract `1.10.0`, the generated client has all 148 operations).
- `CMP-SEAL-C0`, `CMP-INGEST-01`, `CMP-INGEST-02`, `CMP-INGEST-ZIP-01`, `CMP-PROFILE-01`, `CMP-VERSION-MARK-01` — completed (the upload, order, profile and thumbnail operations; the entity `document-version` and its mark).
- `CMP-MATRIX-01`, `CMP-ENGINE-01`, `CMP-VIEWER-01` — completed (the matrix reads and writes; the widget `comparison-viewer`). All are merged in the base `9f5f4912`.
- `CMP-SERIES-01` and `CMP-VC-OVERVIEW-01` — running in parallel; this lane is developed against the sealed contract and the integrator sends their notes when they merge. An operation that answers `503` is a state the screens show.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.10.0`, 131 paths / 148 operations / 432 schemas, unchanged (`contracts/**`, `web/openapi/**`, the generated client and `web/FRONTEND_LOCK.json` are not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0039_comparison_core`, unchanged
- base commit: `9f5f49128723c231813430ef3d941c1723643028`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: web/src/shared/config/screen-registry.ts
- enumerator_owner: CMP-VC-UI-01
- totality_query: `find web/src/app -name page.tsx | sort; python3 tools/plan/pin_sweep.py route`

The lane adds one route (`/version-comparison`) and owns, for it, the rows of the route enumerators of plan section 4.0 rule 2 listed under «Allowed paths». The pins `python3 tools/plan/pin_sweep.py route` lists are judged one by one in the report: a pin that the new route reddens and that lies in the allowed paths is edited and named there with its reason; a pin in `docs/program/**` or `tests/support/expected_facts.json` is not edited, and the lane stops that item and reports the exact sentence and number.

## Captured premise evidence

- premise: contract 1.10.0 with 131 paths / 148 operations / 432 schemas and head 0039_comparison_core; no screen reads the module set, the matrix, the series, the overview or the uploads; the route enumerators are the ones the pin sweep lists

### P-01 — the wave's base facts

- captured_at: 2026-10-28
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(d['info']['version'], len(d['paths']), sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"; grep -n 'revision: str = ' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  1.10.0 131 148 432
  79:revision: str = "0039_comparison_core"
  9f5f49128723c231813430ef3d941c1723643028
  ```
- interpretation: the premise of the brief holds (contract `1.10.0`, 131/148/432, head `0039_comparison_core`), so the lane went on. It says nothing about what the series and overview operations will answer once their lanes merge.

### P-02 — nothing in `web/src` reads the new surface yet

- captured_at: 2026-10-28
- command: `grep -rlE "comparison_modules|getComparisonOverview|getComparisonMatrix|getComparisonQueueSummary|listComparisonSeries" web/src --include=*.ts --include=*.tsx | grep -v shared/api/generated | wc -l`
- captured_output:
  ```text
  0
  ```
- interpretation: the module set, the overview, the matrix, the series and the queue summary have no reader in the application, so every screen of this lane is new code over the generated client; the only existing consumers of the approval controls are `widgets/version-comparison` and `entities/version-comparison`.

### P-03 — the route enumerators the sweep lists

- captured_at: 2026-10-28
- command: `python3 tools/plan/pin_sweep.py route`
- captured_output:
  ```text
  docs/program/ALPHA_ROADMAP.md	route: live claims
  docs/program/CONTRACT_PIN_REGISTRY.md	route: registry
  docs/program/CURRENT_STATE.md	route: live claims
  docs/program/P02_SEAMS.md	route: live claims
  tests/contract/domain_p02/test_openapi_document.py	route: pattern
  tests/e2e/pc01/journey/manifest.json	route: catalogue
  tests/e2e/pc01/test_acceptance.py	route: pattern
  tests/support/expected_facts.json	route: expected facts (surface.operations)
  web/src/_app/navigation.ts	route: pattern
  web/src/shared/config/index.ts	route: pattern
  web/src/shared/config/screen-registry.ts	route: catalogue; route: live claim; route: pattern
  web/src/shared/lib/routes.ts	route: catalogue
  web/src/widgets/home-tiles/model/registrations-screen.ts	route: pattern
  web/tests/guards/dashboard-invalidation.guard.test.ts	route: catalogue
  web/tests/guards/lazy-boundary.guard.test.ts	route: pattern
  web/tests/guards/screen-guard.guard.test.ts	route: pattern
  web/tests/guards/screen-registry.guard.test.ts	route: pattern
  web/tests/guards/screen-set.guard.test.ts	route: catalogue; route: pattern
  web/tests/guards/server-credential.guard.test.ts	route: catalogue
  web/tests/unit/qa_w50/guest-redirects.test.ts	route: pattern
  web/tests/unit/qa_w50/r66-navigation.test.ts	route: pattern
  web/tests/unit/qa_w50/role-gated.test.ts	route: pattern
  web/tests/unit/release-notes/current-screen.test.ts	route: pattern
  web/tests/unit/screens/home.test.ts	route: pattern
  web/tests/unit/shell/frame.test.ts	route: pattern
  web/tests/unit/shell/navigation.test.ts	route: pattern
  web/tests/unit/shell/screen-decision.test.ts	route: pattern
  web/tests/unit/styles/contrast.test.ts	route: catalogue
  web/tests/unit/styles/screens.ts	route: catalogue
  ```
- interpretation: this is the inventory of files that mention a route set. It is a superset of what the new route reddens; the report names the ones that actually go red, with their reason. The four `docs/program/**` files and `tests/support/expected_facts.json` are not editable by this lane.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/_pages/version-compare/**`
- `web/src/app/version-comparison/**`
- `web/src/widgets/version-series/**`
- `web/src/widgets/comparison-upload/**`
- `web/src/entities/version-series/**`
- `web/src/widgets/version-comparison/**`
- `web/src/_pages/stage-comparison/**`
- `web/src/widgets/execution-queue/**`
- `web/src/shared/api/catalog-message.ts`
- `web/tests/**`
- `tests/e2e/pc01/journey/manifest.json`
- `web/src/shared/lib/routes.ts`
- `web/src/shared/config/screen-registry.ts`
- `web/src/_app/navigation.ts`
- `docs/program/tasks/CMP-VC-UI-01.md`
- `docs/program/CMP-VC-UI-01.md`

`web/src/_pages/stage-comparison/**` is changed for its heading only; `web/src/widgets/execution-queue/**` for the block «Сравнение» only; `web/src/shared/api/catalog-message.ts` for the comparison reasons only (where the lane finds that the existing mechanism keeps reason words in a per-entity table instead, the words live in `web/src/entities/version-series/**` and this file is left alone). The route pins that the new route actually reddens are listed here when they are found (see the report, section on enumerators); each is a file under `web/tests/**` or one of the four files above.

## Forbidden hotspots

- `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**` (regenerated only by a seal), `web/FRONTEND_LOCK.json`, `db/migrations/**`
- `src/**` (no backend file)
- root dependency and lock files (`web/package.json`, `web/package-lock.json`); no new npm package
- `web/src/app/globals.css` and every global style; the composition root
- `web/src/widgets/comparison-viewer/**` (mounted, not changed; a missing prop is a STOP to the integrator)
- `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md`, `docs/program/P02_SEAMS.md`, `docs/program/CONTRACT_PIN_REGISTRY.md`, `tests/support/expected_facts.json` (a red pin there is reported, not edited)

## Non-goals

- steps 4, 6 and 7 of the original (wave C2): their columns are left out of the table and the screen says so
- the AI layers, the specification comparison, the MD summary and the PDF report (wave C2); the stage module (wave C3; only the heading of its existing screen changes)
- ZIP sets in the upload (the safe reader exists, nothing calls it yet)
- hiding the menu entry when the module is off: the registry has no per-deployment column and the frame makes no API call; the screen shows the module state (reported to the FIX slot)

## Deliverables

- `entities/version-series` (reads, commands, draft model, words), `widgets/version-series` (the overview table, the transitions, the matrix, the order dialog, the pair viewer host), `widgets/comparison-upload` (the transfer engine and the two dialogs), `_pages/version-compare` and the route `app/version-comparison`
- the A-12 edit of `widgets/version-comparison`, the heading of `_pages/stage-comparison`, the block «Сравнение» of `widgets/execution-queue`
- the Russian sentences for the comparison reasons; the schemas in `TRANSLATED_SCHEMAS` with markers; the census block in `web/tests/unit/styles/screens.ts`
- tests for the model, the screens and the guards, with the mutation proofs named in the brief
- the report `docs/program/CMP-VC-UI-01.md`

## Required tests

- command: `git diff --check`; `npm --prefix web run lint -- --quiet`; `npm --prefix web run typecheck`; `npm --prefix web run api:verify`
- expected: exit 0 each
- command: `cd web && AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent npx vitest run <the lane's files> tests/guards tests/unit/styles tests/unit/shell tests/unit/qa_w50 <every file the pin sweep lists that the route reddens>`
- expected: green
- command: `npm --prefix web run test -- --run` once at the end
- expected: green
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent .venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py`
- expected: green (route and prose guards live there)
- command: mutation proofs (red, restore, green) for the draft rebase on `comparison_matrix_stale`, the A-12 hiding of the three controls, a `503` module state rendered without a crash, the census block
- expected: each guard fails under its mutation

## Integration contract

- the screens read the module set from `ProductVersion.comparison_modules` and the operations of contract `1.10.0` through the generated client; they assume nothing about the series and overview data beyond the contract (the assumptions are listed in the report for the integrator to confirm)
- merge order: after `CMP-OVERVIEW`, last of wave C1 (wave brief section 3); the wiring files this lane edits are the route enumerators and `web/tests/unit/styles/screens.ts`, `web/tests/guards/rendered-language.guard.test.ts`
- `widgets/comparison-viewer` is mounted as `ComparisonViewer(pair, rasterSize?, navigation?)`

## Failure/idempotency/security cases

- every write is an expert's act with a required `Idempotency-Key` minted once per intent and reused on a retry; a viewer without the expert role sees the state and no buttons
- `409 comparison_matrix_stale` on an edit batch: the draft is rebased on the matrix read again and nothing is lost silently; `comparison_edits_limit`, `comparison_edit_invalid` are shown in words
- `503` on any operation: the module-unavailable state, not a crash and not an empty list
- a file name is a hint and never an identity; an identity is the opaque id of the contract

## Rollback / feature flag

The module flag `AUDITMANAGER_COMPARISON_MODULES` (contract field `ProductVersion.comparison_modules`) governs what the screens offer: with `versions` off the screen says the module is off, and the A-12 controls of the version-scoped screen stay as they are. Reverting the lane's commits removes the route, the menu entry and the edits.

## Handoff

Report: [`../CMP-VC-UI-01.md`](../CMP-VC-UI-01.md). Branch `agent/cmp-vc-ui-01`, base `9f5f4912`; nothing pushed, nothing merged, no tag.

**Changed files** (80, `git diff --name-only 9f5f4912..HEAD`): `web/src/entities/version-series/**` (26), `web/src/widgets/version-series/**` (11), `web/src/widgets/comparison-upload/**` (11), `web/src/_pages/version-compare/**` (5) and `web/src/app/version-comparison/page.tsx`, `web/src/widgets/version-comparison/ui/version-comparison.tsx` (A-12), `web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx` (heading), `web/src/widgets/execution-queue/**` (4), `web/src/shared/config/screen-registry.ts`, `web/src/shared/lib/routes.ts`, `tests/e2e/pc01/journey/manifest.json`, and under `web/tests/`: `unit/version-compare/**` (7), `unit/styles/screens.ts`, `guards/rendered-language.guard.test.ts`, `guards/screen-registry.guard.test.ts`, `unit/shell/navigation.test.ts`, `unit/qa_w50/r66-navigation.test.ts`, `unit/screens/{route-screens.ts,routes.test.ts}`, `unit/run/polling.test.ts`; the report and this file.

**Checks** (exit 0 each; report section 13): `git diff --check`; `lint --quiet`; `typecheck`; `api:verify` (148 operations); the whole web suite 217 files / 3495 tests; `tests/contract` without the three `D-220` files 1310 passed; journey conformance 135 passed; mutation proofs P1a-P15 each red then green (report section 8).

**Contracts:** none new, none changed. **Forbidden hotspots:** `git diff --name-only 9f5f4912..HEAD` over `contracts db src pyproject.toml uv.lock web/package*.json web/FRONTEND_LOCK.json web/openapi web/src/shared/api web/src/app/globals.css web/src/widgets/comparison-viewer web/src/entities/version-comparison infra Makefile docs/program/{CURRENT_STATE,ALPHA_ROADMAP,P02_SEAMS,CONTRACT_PIN_REGISTRY}.md tests/support` prints nothing.

**Known limits** (report section 10): the viewer widget prints Latin A/B and engine words and lacks the markers for `ComparisonLayer` and `ComparisonChannelState` (STOP: not changed, FIX slot); the menu entry stays when the module is off; the queue block is mounted through a slot inside the widget because `_pages/queue/**` is not an allowed path; no plain sheet view, no AI hints, no version label editing, no file move between sets, no ZIP; the screen's state is not in the URL; a whole file is hashed in memory.

**For the integrator:** merge after `CMP-OVERVIEW` (the plan's order); merge `CMP-SERIES-01` (`c228cf2e`) first or together, the lane's facts were taken from its report and `src/` is untouched here. The assumptions about the overview data to confirm against the merged `CMP-VC-OVERVIEW-01` are in report section 5. Remove nothing: the lane left no symlink or untracked file in the tree (`web/node_modules`, a link to the read-only `cmp-seal-c0` install, was removed before this commit). After the merge run `tests/contract` and the web suite once on the merged tree: the enumerators (registry, manifest, navigation tests, census, language guard, polling guard) are the places another lane's route or screen collides.
