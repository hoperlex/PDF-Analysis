# CMP-VC-UI-02 — the C2 screens of «Сравнение версий»: AI steps 4/6/7, the queue strips, the three blocks of «Сравнение листов», the PDF report window and the side panel «Изменения в листе»

Written 2026-10-29 by the Sonnet lane `CMP-VC-UI-02` (branch `agent/cmp-vc-ui-02`, base `901914a5` on `integration/compare-modules`; nothing pushed, nothing merged, no tag). Task file: [`tasks/CMP-VC-UI-02.md`](tasks/CMP-VC-UI-02.md). The plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) §1.1, §1.3, §3.2 and §4 wave C2; the seal is [`CMP-SEAL-C2.md`](CMP-SEAL-C2.md) (§3 operations, §9 row `CMP-VC-UI-02`); the screens extended are those of [`CMP-VC-UI-01.md`](CMP-VC-UI-01.md), [`CMP-C1-FIX-B.md`](CMP-C1-FIX-B.md), [`CMP-VC-OVERVIEW-01.md`](CMP-VC-OVERVIEW-01.md) and [`CMP-VIEWER-01.md`](CMP-VIEWER-01.md). The original's frontend at `23f379fd` was read as raw files into a scratch directory outside git (`P` = `frontend/static/js/version-comparison-projects.js`, `V` = `version-comparison.js`, `SC` = `version-comparison-sheet-changes.js`, `MR` = `version-comparison-md-report.js`, `VW` = `version-comparison-viewer.js`).

The lane is **web only**, written against the sealed contract `1.11.0` while the backend lanes build: every C2 operation answers `503 dependency_unavailable` until its lane is merged, and every screen shows that as a **state** («Модуль ещё недоступен»), never as a crash (proof M6, section 7). The integrator's note on `CMP-AI-JOBS-01` (merged `0f6a008d`) was applied (section 5).

## 1. Result

* **«Проекты и этапы»** has all seven steps in the original's order. The cells of steps 4, 6 and 7 carry the original's words and notes and the buttons the server accepts; a checkbox per row and a «выбрать все» per column for steps 4–7; the selection bar «Запустить выбранные по очереди» / «Снять выбор»; the strip «Очередь запуска» and the installation's «Очередь «ИИ-описание изменений»»; the per-row «Сводка изменений (MD)».
* **Every AI start shows the estimate and the consent line** through one component (`EstimatePanel`): calls, images with their bytes, the size of the prompt, the model, the price («≈ 3,45 долл.») or «без учёта стоимости», the two ceilings and the 1,2 overrun. The start carries the **digest of the estimate that was shown**; the stale-estimate, ceiling, consent and overrun-pause refusals are in Russian.
* **«Сравнение листов»** has the blocks «ИИ-описание изменений», «Полные спецификации (СО)» and «Сводка MD и отчёт для заказчика», the AI flags and hints in the matrix cells (joined to cells by `(version_uid, page)`), and the button «Сформировать PDF-отчёт…».
* **The PDF report window** (`widgets/comparison-report`, new).
* **The viewer** has the side panel «Изменения в листе» (the eleven states, the changes with their tiers, «Показать на чертеже», «Требует уточнения (N)», «Заявлено проектировщиком в разрешении (N)», «Скопировать», «MD листа», «Не включено в сводку», «Диагностика», «История (N)») and the evidence banner («Из ИИ-описания: …», «доказательство N из M», «Обзор всех / Один фрагмент»).
* **«Очередь»**: the installation's AI queue under the block «Сравнение».
* **Every AI text carries «не подтверждено инженером»**; a recorded (test) answer is marked «тестовый ответ».
* **Words**: a Russian sentence for each of the 12 conflict, 3 validation and 5 dependency reasons the seal registered, and for `executor_route_missing`; 23 new enums in `TRANSLATED_SCHEMAS`, each with its marker.

## 2. Base facts, printed before any edit

`contract 1.11.0, 176 paths, 198 operations, 517 schemas`, head `0040_comparison_ai_reports`, `VERSION` `0.9.0`, base `901914a5520a2d90b22b0c5c3fcdae1fa3f6e438` (`P-01` of the task file). They equal the brief's. No contract, migration, generated client, dependency, lock or global style was changed (section 10).

## 3. What was built

| Path | What it holds |
| --- | --- |
| `web/src/entities/version-series/model/` | `ai-words.ts` (every state, reason, tier, decision and kind in Russian; the labels), `estimate.ts` (USD, the lines of the estimate, `consentOf`, the agreement that is void for another estimate), `ai-steps.ts` (the cells of steps 4/6/7, their buttons, the selection rules, the queue badge), `launch-queue.ts` (the strip and the AI queue), `hints.ts` (the join of hints to cells), `report-view.ts` (the rules of the report window, the figures of the specification block), `description-view.ts` (the change lines, the evidence, the copied text); `failure.ts` and `steps.ts` extended |
| `web/src/entities/version-series/api/` | `use-ai.ts` (the reads, the estimate), `use-ai-commands.ts` (every start with its consent; job controls; reports; the launch queue), `use-consent-flow.ts` (the state of one estimate dialog), `use-selection-estimates.ts`, `use-download.ts`; the keys |
| `web/src/entities/version-series/ui/` | `ai-text.tsx` (`AiText`, `AiLabel`, `RecordedMark`), `estimate-panel.tsx`, one module stylesheet |
| `web/src/widgets/version-series/ui/` | `ai-step-cell.tsx` (the row's reads and the three cells), `ai-dialogs.tsx` (`AiStartDialog`, `ReportDraftDialog`, `SelectionDialog`), `queue-strips.tsx`, `ai-blocks.tsx` (the three blocks), the hints in `matrix-cell.tsx`, the wiring in `projects-and-stages.tsx`, `sheet-matrix.tsx` and `sheets-tab.tsx`; `ai-steps.module.css` |
| `web/src/widgets/comparison-report/` (new) | the window «Сформировать PDF-отчёт…», its stylesheet |
| `web/src/widgets/comparison-viewer/ui/` | `changes-panel.tsx`, `evidence-banner.tsx`; `ComparisonViewer` gains `changes?: {mayAct}`; `SheetPane` draws the cited places (`evidence`); a block of rules in the stylesheet |
| `web/src/widgets/execution-queue/ui/` | `comparison-ai-queue-block.tsx`, mounted under the block «Сравнение» |
| `web/src/_pages/version-compare/` | composition: `changes` for the viewer, `renderReport` for the window |
| `web/tests/` | `unit/version-compare/{ai-fixtures.ts, ai-layer.test.ts}`, `shapes.ts` (about 110 new shapes: the one list that the census and the language guard both render), `seed.ts`, `screens.test.ts`, `model.test.ts`; the census block in `unit/styles/screens.ts`; `guards/rendered-language.guard.test.ts`; `unit/run/polling.test.ts` |

## 4. The screens, with the original's words and where they come from

### 4.1 «Проекты и этапы»

| Element | Original | Here |
| --- | --- | --- |
| step 4 «ИИ-проверка сомнительных пар»: «проверено» / «не проверялось» / «идёт» / «пауза» / «прервано», the note «вопросов N · пар N · подсказок N · против N»; «Проверить», «Пауза», «Продолжить» | `P:65-72`, `P:483-492` | `aiStepCell` over `getComparisonAiPairCheck`; a done cell has no button (re-check by the checkbox), as in the original (`P:372-373`) |
| step 6 «ИИ-описание изменений»: «готово», «в очереди №N», «пауза», «прервано», «не нужно», the note «листов готово N из M · ошибок K · проверить R»; «Запустить», «Из очереди», «Пауза», «Продолжить», «Заново» → «Описать заново» | `P:90-104`, `P:493-504` | over `getComparisonAiSheetChanges`; «Продолжить» of a cancelled or failed job with something left is `finishComparisonAiSheetChanges` («Досчитать»), of a paused one `resume` |
| step 7 «Сводка и отчёт»: «PDF готов», «PDF строится», «есть MD», «ошибка PDF»; «Сформировать PDF-отчёт», «Продолжить», «Заново» → «Сформировать заново», «PDF» | `P:105-114`, `P:505-525` | over `listComparisonReports`. **There is no «Пауза»**: the contract has no pause of a report; «Отменить» keeps the finished parts and «Продолжить» goes on (FIX item 1) |
| checkboxes per row, «выбрать все» per column, the selection bar | `P:172-176`, `P:355-396`, `P:157-163`, `P:398-419` | `canSelect` is the original's `OPEN` table; a cell already in the queue shows «в очереди №N» / «очередь: идёт» instead of a box |
| «Запустить выбранные по очереди» dialog | `P:398-419` | the first eight, «… и ещё N», the estimate of each AI step that has one and one consent line; a step with no estimate yet (series not computed, no summary) is queued without a consent and waits as «ждёт подтверждения» |
| strip «Очередь запуска» («готово N из M · пропущено K · ошибок E»), «Пауза очереди», «Продолжить очередь», «Очистить», «Список», «✕» | `P:136-151` | `LaunchQueueStrip` over `getComparisonLaunchQueue`; the five queue states and the six entry states in the original's words (`P:355-357`) |
| «Очередь «ИИ-описание изменений»» | `V:76-79`, `V:949-960` | `AiQueueStrip` over `getComparisonAiQueue`; a set of another project is «комплект другого проекта» |
| per-row «Сводка изменений (MD)» | `P:189`, `P:608-616` | `streamComparisonSeriesSummary` when step 6 is done or partial |
| dialogs «Проверить», «Запустить», «Описать заново», «Сформировать» | `P:540-606` | `AiStartDialog` / `ReportDraftDialog` (a report is a draft first: no model call, nothing spent, then the consent) |

### 4.2 «Сравнение листов»

| Element | Original | Here |
| --- | --- | --- |
| «ИИ-описание изменений»: progress and «Листов / Изм. / Вопр. / Ошибок / Проверить / Обращ. / Вход / Выход / Время», the fold with «Проверить» and added/removed sheets, «Отменить», «Досчитать», «Убрать из очереди», «Повторить листы с ошибкой» | `V:159-225` | `AiChangesBlock`; the retry is `retryComparisonAiSheetChanges` under a **new** consent (the estimate with `only_failed`) |
| «Полные спецификации (СО)»: «полное сравнение» / «листовой ИИ», «Листов СО», «Покрыто», «изменено / +добавлено / −удалено / ?неясно», reason, «Открыть»; `SPEC_STATE`, `SPEC_PHASE` | `V:237-275`, `V:870-874` | `SpecificationsBlock`; the changes of a transition are a fold (`listComparisonSpecificationChanges`); a button «Сравнить спецификации» starts one transition (the original starts the specifications through the stage queue) |
| «Сводка MD и отчёт для заказчика»: state, stage, progress, usage, «Скачать PDF», «Скачать MD», «Продолжить»; the tables «Отбор / Пунктов / Вопросов» and «Анализ / Проверка / Факты / Предупреждения» | `V:277-333`, `V:877-878` | `SummaryReportBlock` |
| AI flags and hints in the cells: «ИИ», «ИИ ?», «🌙 ИИ: вероятно стр. N» | `V:380-398`, `V:397-420` | `hintsFor` joins `listComparisonAiPairHints` by `(version_uid, page)`; all thirteen decisions have words; a stale hint is drawn in italics, never hidden |

### 4.3 The PDF report window (`MR:15-77`)

Source «сводка проекта» / «загрузить MD-файл» (disabled with «Сводки проекта ещё нет — сначала «ИИ-описание изменений».»), the default kind «Отчёт для заказчика · Изменения проектных решений» and the analytic one, the reuse checkbox, «Подготовить оценку» (the draft), the history with state, stage, per-transition tables, usage, «Скачать PDF», «Исходный MD», «Начать…», «Отменить», «Продолжить», «Пересобрать PDF» (no model call), «Подготовить отчёт для заказчика» (analytic reports), «Удалить». Every control is for an expert; a reader keeps the downloads.

### 4.4 The side panel and the evidence banner (`SC:1-233`, `VW:36-52`, `VW:395-411`)

«Описать этот лист…» → the estimate → «Подтверждаю передачу этого листа исполнителю» → «Передать и описать»; «Отменить задание»; the eleven state labels; the change lines «Было: «…» → Стало: «…»» with the tier of each value («по тексту листа», «с изображения», «не подтверждено»), «Неясно», «Показать на чертеже»; the rest as in the brief. «Показать на чертеже» focuses the viewer on the change's box (the viewer's existing `focus-box`) and opens the banner; «Обзор всех» shows every cited place at once, «Один фрагмент» one.

## 5. The integrator's note on `CMP-AI-JOBS-01` (applied)

1. The order of refusals (module, role, consent, live job, stale estimate, nothing to do, job ceiling, day ceiling) is the order of the sentences in `failure.ts`; a refused start writes nothing, and the sentences say so.
2. The digest does not cover the day's remaining spend: `day_remaining_micros` is shown, the agreement is judged by the digest only.
3. Resume after `overrun` or `route_changed` and the retry of failed items open the estimate dialog (a new consent); «Досчитать» sends no consent.
4. **A day-ceiling stop shows as `quota`, a job-ceiling stop as `overrun`**: the labels and the advice say so («лимит исчерпан: подписки или дневной потолок установки (50 долл.)», «расход превысил оценку в 1,2 раза или потолок одного задания (10 долл.)»).
5. A recorded answer is marked by the provider mode of its route: «тестовый ответ» on a job, a report and a description (`recorded`), and the dialog warns when the connection itself records.

## 6. What waits for which backend lane

| Screen | Operations | Waits for |
| --- | --- | --- |
| step 4, hints in cells | `getComparisonAiPairCheck`, `estimate…`, `start…`, `pause…`, `resume…`, `listComparisonAiPairHints` | `CMP-VC-AIPAIR-01` |
| step 6, the block, the panel, «Сводка (MD)» | `getComparisonAiSheetChanges`, `estimate…`, `start…`, `pause`, `resume`, `cancel`, `finish`, `dequeue`, `retry`, `getComparisonSheetDescription`, `startComparisonSheetDescription`, `listComparisonSheetDescriptionHistory`, `listComparisonReviewSheets`, `streamComparisonSheetDescriptionMd`, `streamComparisonSeriesSummary` | `CMP-VC-AISHEET-01` |
| the block «Полные спецификации (СО)» | `listComparisonSpecifications`, `listComparisonSpecificationChanges`, `estimate…`, `start…`, `cancelComparisonSpecification` | `CMP-VC-SPEC-01` (part B) |
| step 7, the block, the window | the thirteen report operations | `CMP-VC-REPORT-01` |
| the strips, the selection | `getComparisonLaunchQueue`, `enqueueComparisonLaunch`, `pause…`, `resume…`, `clear…`, `removeComparisonLaunchEntry`, `getComparisonAiQueue` | `CMP-VC-QUEUE-01` |
| the estimate and the consent, the job controls | the shared `comparison_ai_job` core | `CMP-AI-JOBS-01` (merged) |

Until a lane is merged its screen shows «Модуль ещё недоступен» / «ещё недоступно» (the sentence of the refusal is in the `title`).

## 7. Mutation proofs (the guard shown red, the file restored from git, the same tests green)

Tool: a script outside the repository applies one quoted replacement to the committed file, runs the named tests, restores the file with `git checkout`, runs them again; `git status --porcelain` was empty after each. `AI` = `web/tests/unit/version-compare/ai-layer.test.ts` (41 tests).

| # | Commitment | File mutated | Mutation | Guard | Red | Restored |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | **the consent carries the digest it showed** | `entities/version-series/model/estimate.ts` | `consentOf` sends a fixed digest | AI | 2 failed | 41 passed |
| M2 | the start sends the consent of the shown estimate | `api/use-ai-commands.ts` | `consentFor` sends another digest | AI | 1 failed | 41 passed |
| M3a | **a stale refusal asks again** | `api/use-consent-flow.ts` | `refusalAction` always «show» | AI | 1 failed | 41 passed |
| M3b | an agreement stands only for the estimate it was given to | `model/estimate.ts` | `agreementStands` ignores the digest | AI | 2 failed | 41 passed |
| M3c | the stale refusal is recognised | `model/failure.ts` | `estimateStale: false` | AI | 3 failed | 41 passed |
| M4 | **the label «не подтверждено инженером» on every AI text** | `ui/ai-text.tsx` | `AiText` without `AiLabel` | AI | 4 failed | 41 passed |
| M5a | **a recorded answer is labelled** | `ui/ai-text.tsx` | the recorded mark never drawn | AI | 1 failed | 41 passed |
| M5b | a recorded description says so in its passport | `widgets/comparison-viewer/ui/changes-panel.tsx` | the passport's line removed | AI | 1 failed | 41 passed |
| M6 | **a 503 renders without a crash, as the module's state** | `model/failure.ts` | `comparison_ai_sheets` dropped from the module's dependency names | AI + `model.test.ts` | 3 failed | 93 passed |
| M7 | the resume after an overrun asks for a new consent | `model/ai-words.ts` | `pauseNeedsConsent` always false | AI | 2 failed | 41 passed |
| M8 | a report has no pause (the cell offers «Отменить») | `model/ai-steps.ts` | «Пауза» in place of «Отменить» | AI | 1 failed | 41 passed |
| M9 | a hint is joined to its cell by `(version, page)` | `model/hints.ts` | the version is not compared | AI | 1 failed | 41 passed |
| M10 | **the census block** | `tests/unit/version-compare/shapes.ts` | the AI shapes removed from the list | `tests/unit/styles/contrast.test.ts` | 1 failed (`names every colour-bearing rule that NO rendered screen reaches`) | 20 passed |

Three first survived their mutation (M5b, M9 and M5a, whose text had moved): the guard beside each was tightened (the passport as a line of its own; the three hints of one row, each on its own cell) and the three mutations run again. The table is the final run.

## 8. Limits, decisions and FIX items

1. **FIX: a report has no pause.** The plan and the original have «Пауза» on step 7; the contract has `cancelComparisonReport` and `continueComparisonReport`. The cell offers «Отменить» (the finished parts stay) and «Продолжить». A `pauseComparisonReport` is a contract change.
2. **FIX candidate: the overview serves steps 4, 6 and 7 as `not_applicable`** (`overview/rules.py`). The cells are therefore derived on the client from up to four reads per row (the pair check, the newest series, the description's progress, the reports), enabled only where the step before is done. An overview that serves the three steps with figures, like the other four, would remove the N+1 reads and make the counters and the next-step chip true for them. The cell uses the overview's own word where no read has arrived.
3. **Two guard files changed beyond appended hunks.** `rendered-language.guard.test.ts`: `MD` joins `NOT_DERIVABLE` (the original's «Сводка изменений (MD)», «Скачать MD», «Исходный MD», «MD листа») and the cap goes from 20 to 21; the alternative is a Cyrillic «МД», which the lane judged worse. `tests/unit/run/polling.test.ts` names `use-ai.ts` as a bounded poll like the other comparison reads. The integrator may overrule either.
4. **`needs_consent`**: the contract has no operation that gives an existing launch entry its consent. The strip's «Подтвердить…» opens the step's own dialog and starts the step from there; what the queue then does with the entry is `CMP-VC-QUEUE-01`'s.
5. **`SheetPane` of the viewer draws the cited places** (a new optional prop); the brief limits the viewer to the side panel and the banner, and the banner has nothing to point at otherwise.
6. **A hint has no job**, so «тестовый ответ» cannot be put on one hint; it is on the job, the report and the description.
7. **«Выбрать все»** of steps 4, 6 and 7 is made from the rows' own reports (a row knows its AI state): it appears as the reads arrive. A project of many hundred sets reads four things for each, which item 2 would remove.
8. The queue strip names only the sets of the chosen project.
9. **The two heaviest guards got slower, and one run of the whole web suite cannot finish.** The contrast census alone took 158 s on the base (its longest test 40.7 s) and 207 s here (longest 53.4 s), measured back to back on the same host. The lane cut its own share three times (page shapes that are not about the table read three sets, not thirteen; the per-member shapes are rendered together; the shapes the markers, the branches and the census do not need were dropped) and it is still +30 %. A single `npx vitest run` of the whole suite then stops after the three heaviest files (`contrast.test.ts`, `rendered-language.guard.test.ts`, `lazy-boundary.guard.test.ts`, 486 s together) with `Unhandled Error: [vitest-worker]: Timeout calling "onTaskUpdate"` — the failure class `CMP-SEAL-C2` §6 met on a loaded host and `CMP-VC-UI-01` §13 avoided at 425 s; it happened in four of five runs of this tree and in none of the files' assertions. The suite was therefore run as two invocations that together hold every file (section 11). The cause is the single fork of `vitest.config.ts` (`singleFork: true`) with one synchronous test close to the 60 s timeout of the worker's RPC; the cure is a faster census or a split of `contrast.test.ts`, which are not this lane's files.
10. Not run, by the brief and `R-135`: `make gate`, the live journey `e2e:pc01`, a browser. The pointer, file-input, clipboard and download handlers are code the static harness cannot fire; their commands are tested at the model level.

## 9. What the integrator confirms about backend data

1. `ComparisonAiPairHint.page` is a **matched sheet of the older version in the row of the cell** whose `version_uid` it carries (the join of seal §3 decision 4); a hint whose `page` is in no row is not drawn.
2. `ComparisonAiChange.box` is in points on the canvas of page A for both `side` values; `side` only says where the value was read.
3. The estimate `GET` of `pair_check` and `sheet_changes` after a pause for `overrun` or `route_changed` answers **for what is left** (the dialog shows it as the new estimate).
4. `ComparisonReport.estimate` is present on a draft; for a paused report that needs a new consent the dialog reads the report again and needs `estimate` there. If the lane puts it elsewhere, one function changes (`readEstimate` in `use-ai.ts`).
5. `ComparisonLaunchEntry.series_id` is set for an entry of `ai_changes` and `report` (the strip's «Подтвердить…» needs it).
6. `uploadComparisonReportSource` takes the raw file as `text/markdown`; the generated client sends a `Blob` body. `streamComparisonReportPdf` answers a binary body the client turns into a `Blob`.
7. The step counts of steps 4, 6 and 7, if the overview ever sends them, are read nowhere yet.

## 10. Contracts and hotspots

* **New or changed contracts: none.** `git diff --name-only 901914a5..HEAD -- contracts db src pyproject.toml uv.lock docs/program/P02_LOCK.json web/package.json web/package-lock.json web/FRONTEND_LOCK.json web/openapi web/src/shared web/src/app web/src/_app infra Makefile docs/program/CURRENT_STATE.md` prints nothing.
* Outside the lane's own directories, by the task file: `web/tests/guards/rendered-language.guard.test.ts`, `web/tests/unit/run/polling.test.ts`, `web/tests/unit/styles/screens.ts`, `web/tests/unit/version-compare/*`.
* The page's composition (`_pages/version-compare`) adds two props to the sheets tab; no route, registry, manifest or menu entry changed. `web/node_modules` was the shared read-only symlink and was removed before the last commit.

## 11. Checks

Run on the committed tree whose code is the last commit before the two documents (`git status --short` showed only `docs/program/CMP-VC-UI-02.md` while the web suite ran), `web/node_modules` the read-only link to `cmp-seal-c0`, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, the host at load average 5–6 (other lanes), `--basetemp` outside the repository. The runs of the suite were started detached and read from their log files.

| Command | Exit | Result |
| --- | --- | --- |
| `git diff --check 901914a5..HEAD` | 0 | prints nothing |
| `npm --prefix web run lint -- --quiet` | 0 | no findings |
| `npm --prefix web run typecheck` | 0 | no findings |
| `npm --prefix web run api:verify` | 0 | `OK - 198 operations, contract sha256 44c565cf…191162`, no drift |
| `cd web && npx vitest run --maxWorkers=2 --exclude tests/unit/styles/contrast.test.ts --exclude tests/guards/rendered-language.guard.test.ts --exclude tests/guards/lazy-boundary.guard.test.ts` | 0 | **216 files, 3581 tests passed** (48 s); it holds `tests/unit/version-compare` (183 tests with the lane's 41), `tests/unit/run/polling.test.ts`, `tests/unit/shell`, `tests/unit/comparison` and every other file |
| `cd web && npx vitest run tests/unit/styles/contrast.test.ts tests/guards/rendered-language.guard.test.ts tests/guards/lazy-boundary.guard.test.ts` | 0 | **3 files, 70 tests passed** (486 s: the census, the language guard with the 23 new schemas and their markers, the boundary guard) |
| together | | **219 files, 3651 tests, 0 failed** (`CMP-C1-FIX-B`: 217 files, 3512 tests) |
| earlier runs of the lane's directories (`tests/guards tests/unit/styles tests/unit/shell tests/unit/comparison tests/unit/run/polling.test.ts`, 43 files) | 1 | 4 reds found and fixed in `a0dce718` (English prose in two errors and a template, a denial of sign-in in a pause sentence, three unreached rules, an empty container); the rerun of the four files was green |
| `.venv/bin/python -m pytest -q tests/contract` without the three `D-220` files, plus `tests/e2e/test_pc01_journey_conformance.py` | 0 | **1445 passed**, 19283 subtests passed (165 s): the 1310 of `tests/contract` and the 135 of the journey conformance, as at the base of `CMP-C1-FIX-B`. The first run of this battery was red once: a comment of `report-view.ts` read «§3 operation descriptions» and `test_surface_counts_in_prose.py` took the `3 operation` for a claim of three operations; the comment was reworded (`fix(web): a comment that read as a claim…`) and the battery run again on the final code |
| mutation proofs M1–M10 (section 7) | | each guard red under its mutation, green once the file is restored from git |

Not run, as the brief and `R-135` say: `make gate`, the live journey on a stand, a browser (section 8 item 10). The tree is clean after every proof.
