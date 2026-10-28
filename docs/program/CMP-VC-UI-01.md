# CMP-VC-UI-01 — the screens of «Сравнение версий»: projects and steps, the sheet matrix, the upload dialogs

Written 2026-10-28 by the Sonnet lane `CMP-VC-UI-01` (branch `agent/cmp-vc-ui-01`, base `9f5f4912` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-VC-UI-01.md`](tasks/CMP-VC-UI-01.md). The plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) sections 1.1, 1.3, 3.2 and 4 wave C1; the original's screens are [`compare/ORIGINAL-VERSION-COMPARISON-INVENTORY.md`](compare/ORIGINAL-VERSION-COMPARISON-INVENTORY.md), and where it was not precise enough the original's frontend and services at `23f379fd` (read as raw files into a scratch directory outside git; `P` = `frontend/static/js/version-comparison-projects.js`, `V` = `version-comparison.js`, `B` = `version-comparison-batch.js`, `S` = `backend/app/services/version_comparison/series.py`, `R` = `resolve.py`, `L` = `lineage.py` of the same directory).

## 1. Result

A menu item **«Сравнение версий»** in the group «Работа» opens `/version-comparison`: a project is chosen on the screen (the original has a global object, ours has none), then two tabs.

* **«Проекты и этапы»** — the counters, the totals, the search, the filters, the sort, «Обновить» with the time, the legend, the strip of uploads not yet in the list, and the table of document sets with the steps 1, 2, 3 and 5.
* **«Сравнение листов»** — for one document set: the header, «Сводка переходов», the matrix «Лист \ версия» with its draft of manual edits, the history and the edits that no longer apply, «Порядок версий», and the viewer of one pair (`ComparisonViewer`, mounted by the page).
* **Upload** — «Загрузить проект со всеми версиями» opens «Загрузка проекта и версий»; its button «Пакетная загрузка…» leads to «Загрузка нескольких проектов».
* **A-12** — the version-scoped screen offers none of the three `0035` controls while `ProductVersion.comparison_modules` names the versions module, and points to «Сравнение версий».
* **«Очередь»** — a read-only block «Сравнение» from `getComparisonQueueSummary`.
* **Words** — a Russian sentence for every reason of contracts 1.9.0 and 1.10.0 a comparison screen can show; twenty-two new enums in `TRANSLATED_SCHEMAS` with their markers.
* **Heading** — the version-scoped screen is now «Сравнение этой версии и её прогонов».

A module whose operation answers `503 dependency_unavailable` with one of its own dependency names is a **state** on every screen («Модуль ещё недоступен»), never a crash (proof in section 8).

## 2. Base facts, printed before any edit

`contract 1.10.0, 131 paths, 148 operations, 432 schemas`, head `0039_comparison_core` (`P-01` of the task file), base `9f5f49128723c231813430ef3d941c1723643028`. They equal the brief's, so the lane went on. The lane changed no contract, no migration, no generated client, no dependency, no lock and no global style.

## 3. What was built

| Path | What it holds |
| --- | --- |
| `web/src/entities/version-series/` | `api/` the reads and the keyed commands (overview, matrix, edits, series, sheet pairs, order, page profile, queue summary, thumbnails); `model/` the steps and their words, the overview's groups and sorts, the verdict sentences, the cells' words, the draft of manual edits and its rebase, the gestures, the click notes, the order, the upload words, the refusal sentences, the thumbnail store |
| `web/src/widgets/version-series/` | `ProjectsAndStages`, `SheetsTab`, `TransitionSummary`, `SheetMatrix`, `MatrixCellView`, `DraftPanel`/`EditHistory`, `MatrixState`, `VersionOrderDialog`, `PairViewerSlot`, `FailureState`; one module stylesheet |
| `web/src/widgets/comparison-upload/` | the transfer (`model/transfer.ts`, resumable and stoppable), the matching of files to declarations, the confirmation bodies, `UploadDialog` for both modes, `SetEditor`; one module stylesheet |
| `web/src/_pages/version-compare/`, `web/src/app/version-comparison/` | the page (project chooser, tabs, module state, composition of the viewer and the dialogs) and its route file |
| `web/src/widgets/version-comparison/` | the A-12 edit (`handedOver`) |
| `web/src/widgets/execution-queue/` | `ComparisonQueueBlock` and its slot under the list |
| `web/src/_pages/stage-comparison/` | the heading only |
| `web/src/shared/config/screen-registry.ts`, `web/src/shared/lib/routes.ts` | the row and the builder of the route (the enumerators of plan §4.0 rule 2) |
| `tests/e2e/pc01/journey/manifest.json` | the route `version-comparison`, and `getProductVersion` on the route `comparison` (A-12 reads it) |
| `web/tests/` | `unit/version-compare/` (model, upload model, thumbnail store, screens; fixtures, seeds, `shapes.ts`), the census block in `unit/styles/screens.ts`, the schemas and markers in `guards/rendered-language.guard.test.ts`, the enumerating tests below |

## 4. The screens, with the original's words and where they come from

### 4.1 «Проекты и этапы» (`widgets/version-series/ui/projects-and-stages.tsx`, words in `entities/version-series/model/steps.ts` and `overview-view.ts`)

| Element | Original | Here |
| --- | --- | --- |
| counters «Все / Ждут действия / Идут / Ошибки / Готовы», «N версий · M переходов» | `P:18-24`, `P:98-105` | tiles (`aria-pressed`); the server's `counters` when nothing is searched, the visible sets' counts when something is (`P:318`) |
| «Поиск по шифру…», «Марка», «Порядок» (four presets), column sort ▲▼ | `P:108-118`, `P:167-172`, `P:29-34` | same words; the mark is the letters after the last hyphen of the designation |
| «Обновить», «обновлено …» | `P:123-124` | the time is the overview's `generated_at`, in UTC like every stamp of this application |
| «В загрузке, ещё не в списке проектов:» | `P:126-132` | the unfinished uploads of `pending_uploads`, with state, files and sets |
| «Проект · следующий шаг» with the next-step chip; a row click opens the second tab | `P:170`, `P:93` | chip «Далее: …» from `next_step`; the title is also a button |
| «Версии» | `P:171` | `version_count` and the day of the last update |
| «1 Загрузка», «2 Разбор версий» («Повторить»), «3 Сопоставление листов» («Подготовить»), «5 Сравнение соседних» («Запустить», «Пауза», «Продолжить», «Заново») | `P:6-16`, `P:41-94` `stageView`, `P:460-530` `stageActs` | the state words of the original, the figures the contract names (`ComparisonStepCounts`), the buttons of `stepActions`; «Повторить» and «Подготовить» are `prepareComparisonMatrix` (CMP-SEAL-C1 decision 7); «Заново» asks first with the original's text and «Пересчитать» |
| legend | `P:218-225` | «✓ готово · ! есть что проверить · ⟳ идёт · ○ не запускалось · ✕ ошибка» and «Щелчок по строке — сравнение листов комплекта.» |
| «Загрузить проект со всеми версиями» | `V:72` | in the page header; disabled with the reason for a reader who is not an expert or when no project is chosen |

**Steps 4, 6 and 7 are left out** (wave C2): the table has no column for them and says so under the table (`LATER_STEPS_NOTE`); the next-step chip can still name them (`NEXT_STEP_LABELS`). The strips «Очередь запуска» and «Очередь «ИИ-описание изменений»» and the row checkboxes of the selection bar belong to steps 4–7 and are left out with them. «Сводка изменений (MD)» per row is step 6–7.

### 4.2 Upload (`widgets/comparison-upload/`)

| Element | Original | Here |
| --- | --- | --- |
| «Загрузка проекта и версий», «Выбрать папку», «Выбрать файлы», «Исходные файлы не изменяются.» | `V:435-467` | same words; PDFs only — a ZIP of a whole stage is not accepted yet (the safe reader exists, nothing calls it): the dialog says so |
| proposal, «Куда загрузить», title input, ↑↓, label per file, warnings (⚠), «Подтвердить группировку и порядок» | `V:468-500` | `SetEditor`: the designation input, «Новый проект со всеми версиями» / «Добавить версии в существующий комплект», ↑↓ and a label per file, the five warnings of the contract in sentences, the proposed stage and section with a checkbox; «Подтвердить группировку и порядок» confirms every set waiting for a word with what the reader changed |
| «в проект…» (moving a file to another group) | `V:~494` | **not offered**: the confirmation lists exactly the set's own files (`comparison_set_members`); to regroup, upload again |
| «Загрузка нескольких проектов», «Добавить папку», «Добавить папку с проектами», «Исключить», «Повторить», «Принять состав, порядок…» | `B:58-126` | same; the projects table is the picked folders; per-set «Подтвердить состав и порядок», «Исключить», «Повторить» |
| «Продолжить загрузку», «Прервать передачу», «Удалить недогруженный пакет» | `B:91-97` | «Остановить загрузку» (aborts the request in flight, keeps the staged parts), «Продолжить загрузку» (reads the batch again and sends from the next part; a reader who reloaded picks the same files again, matched by SHA-256 and size), «Удалить пакет» (`cancelComparisonUpload`) |
| «После подготовки сравнить все соседние версии» | `compare_neighbors` | `compare_after_preparation` of the create request; shown on the batch afterwards |
| «Пауза после текущего проекта», «Подтвердить порядок во всех проектах» | plan §1.1 | `pauseComparisonUpload` / `resumeComparisonUpload`; the second confirms every set waiting for a word as the reader proposed it |
| the ten status labels (`B:4-8`) | `B:4-8` | eight of them from the set states (`Загрузка`, `Разбор PDF`, `Требуется проверка`, `Ожидает обработки`, `Подготовка версий`, `Готово`, `Ошибка`, `Исключён`); «Ожидает разбора» and «Сравнение версий» have no state in contract 1.10.0 and are not drawn |

The transfer (`model/transfer.ts`) sends 16 MiB parts numbered from 1, completes each file, resumes from `parts_staged`, mints one `Idempotency-Key` per (file, part) and reuses it on every retry, sends a file that failed its integrity again from part 1 under a new key generation, retries a retryable refusal at most three times with a growing wait, ends the file (not the batch) on any other refusal and the whole batch on `comparison_upload_state`. The SHA-256 of a file is taken whole by `crypto.subtle` (no streaming hash without a package; the 250 MiB envelope bounds what is held; files are hashed one at a time).

### 4.3 «Сравнение листов» (`widgets/version-series/ui/sheets-tab.tsx` and the files beside it)

| Element | Original | Here |
| --- | --- | --- |
| header, «· версий: N» | `V:93-106` | the designation, «· версий: N» |
| «Применить сопоставления (N)», «Отменить правку» while a draft exists | `V:98-99`, `V:1349-1394` | one batch against the revision `{matrix_id, edit_no}`; «Отменить правку» takes the last line off the draft; with no draft and a saved applied edit, «Отменить последнюю правку» is `undoComparisonMatrixEdit` |
| «Порядок версий» | `V:503-523` | `VersionOrderDialog`: ↑↓ and «Сохранить порядок» (a new revision against the one seen); disabled while a draft exists |
| side selection | `V:355-360` | **«Было» / «Стало»** (see section 7, deviation 1) |
| «Сводка переходов»: progress, «Листов», «✓ ◐ ● ⚠», «Состав +N / −M», the verdict, «Открыть», «Отменить» / «Продолжить» / «Досчитать» | `V:124-158`, `S:54-62` | `TransitionSummary`; the verdict is built from the verdict codes and the counts of the summary (`verdictParts`) in the original's sentences, joined with «; », plus the note about pairs that rest on an AI link (plan §4.0 rule 6) |
| «Сохранённая сводка для прежнего порядка версий.» | `V:127` | with the stale reasons of the series |
| a non-adjacent pair | `V:1274-1278` | «Пара собрана по цепочке через промежуточные версии и не сравнивалась: сравниваются только соседние версии.» |
| matrix «Лист \ версия», «только изменения», row heads with the status badge | `V:347-370` | `SheetMatrix`; the badge opens the pair |
| flags «?», «▤ группа», «✎», «ИИ», «⧉», «скан», «◫», «⇉» | `V:380-398` | `matrix-cell.tsx`; «◫» / «⇉»: a split cell reads «⇉» when the next version's cell of the row is a split sheet too, else «◫»; an extra flag «↷» for a link across a version without the sheet (`bridge`) |
| unmatched cell «⁇ не сопоставлен», reason, «кандидаты:», «Связать», «Отметить, что этого листа в версии нет», «∅ нет в версии», «Несвязанные страницы» | `V:397-420` | reasons are `REASON_LABELS` of the original (`R:43-57`) and `L:631-646`; «Связать» is `link(row page, candidate)` with the row page taken from another version than the candidate's, «Отметить…» is `mark_absent(row page, version)` |
| drag and drop, «⤫ Отвязать в отдельную строку» | `V:373-398`, `V:1220-1330` | a thumbnail dragged onto a cell of its own column is `link`; «⤫» is `unlink` (not offered for a row with one sheet); all of them are lines of the draft |
| rebase | — | a draft carries the revision it was started on; when the matrix is read at another revision (after a `409 comparison_matrix_stale` the query is read again) the draft is rebased: the base becomes the fresh revision, an edit naming a page the fresh matrix does not hold is taken out **and listed** («Эти правки не подходят…»); nothing is lost silently |
| orphaned edits, stale reasons | — | «Правки, которые больше не применяются (N)» always in view; «История правок (N)» behind a disclosure; the banner of a stale matrix with its reasons |
| a click on a sheet with no pair | `V:1227-1248` | the original's sentences (`answerClick`) |

## 5. SERIES and OVERVIEW: what was built against, and what the integrator confirms

The lane was written against the sealed contract while both backends were stubs. `CMP-SERIES-01` merged (`c228cf2e`) while the lane ran; its report and the integrator's notes were read and the screens adapted in commit `feat(web): the facts of CMP-SERIES-01` (the branch was not merged, as told). **Settled by the SERIES report**, each pinned by a test:

1. «Листов» is `summary.sheets` (the lane first used `compared`; test «counts «Листов» by the transition's sheets»).
2. A split sheet is one pair per part with the older sheet as page A of each; `pairOfRow` finds a row's pair by its newer page first, so the second part's row has its own pair (`model.test.ts`, «gives the second part of a split sheet its own pair»).
3. «Досчитать» (`finishComparisonSeries`) is offered for a series that has ended with something left: `failed`, `cancelled`, or `completed` with a transition that is not `completed` or has a failed pair; «Продолжить» (`resume`) for `paused`; «Заново» (`start` with `restart` and the `base_order_revision_no` the sheets tab saw) for `completed`, `failed`, `cancelled` — a queued, running or paused series is `comparison_series_active` (`continueOf`, `canRestart`, `hasLeftovers`).
4. Step 5 words: queued and running are «идёт»; the others as the integrator listed them (`stepView`).
5. A pair shows `reasons` (the engine's, then the series': `SPLIT_SHEET`, `TABLE_GROUP`, `AI_MATCH`, and `UNCHECKED_CHANNEL_<CHANNEL>` as «не проверено: <канал>»), `permit` (the four states, each item), `parts` (role and coverage), `ai_dependent`, and a failed pair's «ошибка расчёта»; none of these codes is printed.
6. Sentences owed by the SERIES report (§10) are in `failure.ts`: `comparison_series_active`, `comparison_series_state`, `comparison_version_order_stale`, `comparison_matrix_stale` (now worded for both uses: moved under the reader, or not ready for the start), `comparison_versions_few`; `ComparisonPermitState` and `ComparisonPartRole` joined `TRANSLATED_SCHEMAS`.

**Still assumed (the OVERVIEW lane has not merged); the integrator confirms when it does:**

1. **The grouping of a set** (`groupOf`, `overview-view.ts`): any step `failed` → «Ошибки»; else any step `queued`/`running`/`pausing` → «Идут»; else `next_step` present → «Ждут действия»; else «Готовы». The server's `counters` are shown as they come when nothing is searched; if OVERVIEW groups differently the tiles and the filtered table disagree (`model.test.ts`, «groups a set by its steps»).
2. **`next_step`** is the step the chip proposes; a set with none and no running step reads «Готово».
3. **Step figures** (`ComparisonStepCounts`): `profile` uses `ready`, `total`, `failed`; `matrix` `rows`, `unmatched`, `manual_edits`; `series` `done`, `total`, `with_changes`; `upload` `total`. A figure that is absent prints nothing.
4. **Series ids.** The overview carries none, so a series command from the table («Пауза», «Продолжить», «Заново») reads `listComparisonSeries(limit 1)` first and acts on the newest series; «Заново» from the table sends no `base_order_revision_no` (the table does not read the order), from the sheets tab it sends the one seen.
5. **The step state of a cancelled series** is `interrupted` («прервано») and offers «Продолжить» = `finishComparisonSeries`; a `paused` one offers `resume`.

## 6. The Russian sentences (g)

`entities/version-series/model/failure.ts`: the mechanism of the application keeps reason sentences next to their entity (`presetRefusalSentence`, `pairingFailure`), keyed by the safe detail key of the code — `conflict_reason` under `conflict`, `constraint` under `validation_failed`, `dependency` under `dependency_unavailable`, `role` under `storage_integrity_error` — so the words live there and `catalog-message.ts` (which words a *code*) is untouched. Every reason registered by the two seals is covered, and a test pins the lists equal to the registered ones: eight `conflict` reasons, twenty-six `constraint`s (the limits, the part refusals, the edit refusals, the thirteen `comparison_zip_*`, `display_name`, `required_together`, `declared_page_count`), nine `dependency` names (the seven stub classes, `comparison_modules`, `comparison_versions_module`), the integrity refusal of a received file, and the `failure_reason` of a file or a set. A dependency name of the comparison is the **module state** («Модуль ещё недоступен», `moduleUnavailable`); a reason this table does not know falls back to the code's own catalogue sentence, never to the server's English. `comparisonFailure` is the one classifier the widgets use.

Schemas registered in `TRANSLATED_SCHEMAS` with markers (every member is seen by a rendered state, as the guard demands): `ComparisonSheetStatus`, `ComparisonCellConfidence`, `ComparisonCellFlag`, `ComparisonCellState`, `ComparisonMatrixState`, `ComparisonMatrixStaleReason`, `ComparisonMatrixEditKind`, `ComparisonMatrixEditStatus`, `ComparisonMatrixEditSource`, `ComparisonSeriesState`, `ComparisonSeriesStaleReason`, `ComparisonTransitionState`, `ComparisonVerdictCode`, `ComparisonStepId`, `ComparisonStepState`, `ComparisonUploadState`, `ComparisonUploadSetState`, `ComparisonUploadFileState`, `ComparisonProposalWarning`, `ComparisonVersionOrderSource`, `ComparisonModules`, `ComparisonQueueModule`. The expectation of `needs_manual_review` is restored to `['needs', 'manual', 'review']`.

## 7. Deviations, on purpose, and STOP items

1. **A/B → «было» / «стало»; «V1» → «№1».** The brief names «side selection A/B» and the original prints «A», «B» and «V1». The repository's rule `R-18` (the interface is Russian) is held by `rendered-language.guard.test.ts`, which reddens a bare Latin letter that no contract word explains; it reddened on «A», «B» and «V» in this lane's screens. The sides are therefore «Было» / «Стало» and the columns «Версия №1…», named by their place in the comparison order (not the document's ordinal). The alternative — permit the letters in the guard's `NOT_DERIVABLE` list — loosens a global guard and was not taken; the integrator may overrule.
2. **STOP (widget not mine): the markers of `ComparisonLayer` and `ComparisonChannelState` are not registered.** The brief asks for both ("as VIEWER noted"). A schema in `TRANSLATED_SCHEMAS` needs a marker that rendered screens carry for every member, and `widgets/comparison-viewer` carries none (`data-layer` on the eight layer toggles in `comparison-viewer-view.tsx`, `data-channel-state` on the channel chips in `evidence-panels.tsx`). Adding a `data-` attribute to the widget is a change beyond "a prop it lacks", so the lane stopped that item. The exact edit: `Choice` in the layer fieldset gets `data-layer={layer}` (the element that wraps the checkbox), `ChannelStrip` puts `data-channel-state={channel.state}` on the checked and unchecked lines (one per channel). Then add the two names to `TRANSLATED_SCHEMAS` and two rows to `SCHEMA_MARKERS`.
3. **Finding in the viewer widget (FIX slot).** Rendered under the language guard, the widget prints Latin letters and the engine's machine words as text: «Лист A:», «Лист B:», «(B)», «Совмещение B на A», «зона «stamp»», «поле «revision»». The shapes that mount the viewer are therefore `censusOnly` (the contrast census renders them, the language guard does not). Either the widget says «было/стало» and translates the zone and field names, or the guard permits the letters.
4. **The menu entry stays when the module is off.** ADR decision 23 says a module that is off has no menu entry. The registry (`screenDecision`) has no per-deployment column and the frame makes no API call, so hiding the row needs the frame (`_app/**`, not this lane's paths). The screen says «Модуль «Сравнение версий» выключен» and draws no command. FIX slot.
5. **The block «Сравнение» of «Очередь» mounts through a slot in the widget** (`ComparisonQueueSlot` under the list), because `_pages/queue/**` is outside the lane's paths. The slot draws the block only inside a query provider (several tests render the list bare). The clean mount is one line in `queue-page.tsx`; FIX slot.

## 8. Mutation proofs (the guard shown red, the file restored from git, the same tests green)

Tool: a script outside the repository applies one replacement to the committed file, runs the named test files, restores the file with `git checkout`, and runs them again; the tree was clean after each. `U` is `web/tests/unit/version-compare`.

| # | commitment | file mutated | guard | red | restored |
| --- | --- | --- | --- | --- | --- |
| P1a | **the draft is rebased and what does not fit is reported**: nothing counts as missing | `entities/version-series/model/draft.ts` | `U/model.test.ts` | 2 failed, 33 passed | 35 passed |
| P1b | the rebased draft takes the fresh revision as its base | `draft.ts` | `U/model.test.ts` | 1 failed | 35 passed |
| P1c | **a `409 comparison_matrix_stale` is recognised** | `model/failure.ts` | `U/model.test.ts` | 1 failed | 35 passed |
| P1d | the draft knows the matrix moved under it | `draft.ts` | `U/model.test.ts` | 1 failed | 35 passed |
| P2a | **A-12: «Подтвердить пару» / «Отозвать» are not offered while the versions module is on** | `widgets/version-comparison/ui/version-comparison.tsx` | `U/screens.test.ts` | 2 failed, 52 passed | 54 passed |
| P2b | **A-12: «Подготовить сводку» is not offered** | `version-comparison.tsx` | `U/screens.test.ts` | 1 failed, 53 passed (after the test was tightened: the first version survived this mutation) | 54 passed |
| P2c | A-12: the pointer to «Сравнение версий» is drawn | `version-comparison.tsx` | `U/screens.test.ts` | 1 failed | 54 passed |
| P3a | **a `503` of the module is the module's state, not an error** (the widget) | `widgets/version-series/ui/module-state.tsx` | `U/screens.test.ts` | 2 failed, 52 passed | 54 passed |
| P3b | the classifier knows the comparison's dependency names | `model/failure.ts` | `U/model.test.ts`, `U/screens.test.ts` | 4 failed, 85 passed | 89 passed |
| P4 | **the census block**: no rendered state of the lane's screens | `web/tests/unit/styles/screens.ts` | `tests/unit/styles/contrast.test.ts` | 1 failed, 19 passed (`names every colour-bearing rule that NO rendered screen reaches`) | 20 passed |
| P5 | the transfer sends from part 1 although the server holds parts | `widgets/comparison-upload/model/transfer.ts` | `U/upload-model.test.ts` | 1 failed | 25 passed |
| P6 | a part the stop interrupted gets a new key on the next run | `transfer.ts` | `U/upload-model.test.ts` | 1 failed (the first version of the test survived; a stop-and-continue case was added) | 26 passed |
| P7 | «⤫» is offered for a row with one sheet | `model/matrix-edits.ts` | `U/model.test.ts` | 1 failed | 35 passed |
| P8 | the queue block shows an unwired module as a plain error | `widgets/execution-queue/ui/comparison-queue-block.tsx` | `U/screens.test.ts` | 1 failed | 54 passed |
| P9 | the version-scoped screen keeps its old heading | `_pages/stage-comparison/ui/stage-comparison-page.tsx` | `U/screens.test.ts` | 1 failed | 54 passed |

Two of the fourteen first survived (P2b, P6): the guard beside each was tightened in the commit `test(web): two guards that survived their mutation`, and the mutation run again. Counts above are those of the files before the SERIES adaptation added tests.

Seven more proofs for the SERIES adaptation and the polling guard, run the same way:

| # | commitment | file mutated | guard | red | restored |
| --- | --- | --- | --- | --- | --- |
| P10 | **the matrix poll has an arm that ends it** (the first version of the guard survived; it now reads the option's own value) | `entities/version-series/api/use-matrix.ts` | `web/tests/unit/run/polling.test.ts` | 1 failed, 15 passed | 16 passed |
| P11 | the series read has no timer of its own | `use-series.ts` | `polling.test.ts` | 1 failed | 16 passed |
| P12 | the second part of a split sheet has its own pair | `model/matrix-view.ts` | `U/model.test.ts`, `U/screens.test.ts` | 4 failed, 94 passed | 98 passed |
| P13 | «Листов» counts the sheets of the transition | `widgets/version-series/ui/transition-summary.tsx` | `U/screens.test.ts` | 1 failed | 57 passed |
| P14 | «Досчитать» for a finished series with something left | `model/series-words.ts` | `U/model.test.ts`, `U/screens.test.ts` | 2 failed | 98 passed |
| P15 | «Заново» only for a series that is not live | `series-words.ts` | `U/model.test.ts`, `U/screens.test.ts` | 2 failed | 98 passed |

## 9. Enumerators and pins (plan §4.0 rule 2)

`python3 tools/plan/pin_sweep.py route` lists 29 files. The new route reddened these, and each was edited in the lane's allowed paths, with its reason:

| File | Reason |
| --- | --- |
| `web/src/shared/config/screen-registry.ts`, `web/src/shared/lib/routes.ts` | the row of `/version-comparison` (a menu item in «Работа», `any-role`) and `routes.versionComparison()` |
| `tests/e2e/pc01/journey/manifest.json` | the route `version-comparison` (and `getProductVersion` among the calls of the route `comparison`, which A-12 now makes); `tests/e2e/test_pc01_journey_conformance.py` 135 passed |
| `web/tests/unit/screens/route-screens.ts` | the seed of the new address (`screen-set.guard.test.ts` was red naming it) |
| `web/tests/guards/screen-registry.guard.test.ts` | the registry holds 30 rows, the menu of «Работа» one more |
| `web/tests/unit/shell/navigation.test.ts`, `web/tests/unit/qa_w50/r66-navigation.test.ts` | the ruled menu (`R-66`) written out by hand, one item longer |
| `web/tests/unit/screens/routes.test.ts` | `D-94`: every address a builder builds is linked from a rendered screen — the frame draws the menu item |
| `web/tests/unit/styles/screens.ts` | the census block (the contrast census was red until every rule of the lane's stylesheets was reached) |
| `web/tests/guards/rendered-language.guard.test.ts` | the branches of the mandatory states, the 24 schemas and their markers, and the restored `needs_manual_review` expectation |
| `web/tests/unit/run/polling.test.ts` | the guard "no second polling loop" read `refetchInterval` as a run poll; the four comparison reads are named as the second bounded exception, with assertions of their own (named interval ≥ 1 s, no timer, an arm that schedules nothing, never the run endpoint) |

Green without an edit: `dashboard-invalidation`, `server-credential`, `lazy-boundary` (no sixth lazy widget is needed), `screen-guard`, `home`, `frame`, `screen-decision`, `current-screen`. **The four documents under `docs/program/**` that the sweep lists (`ALPHA_ROADMAP.md`, `CONTRACT_PIN_REGISTRY.md`, `CURRENT_STATE.md`, `P02_SEAMS.md`) and `tests/support/expected_facts.json` were not edited and no pin in them is red** (`tests/contract` is green; none of them states a number of screens or routes).

## 10. Limits, risks, items for the FIX slot

1. **STOP item and the viewer findings** — section 7 items 2 and 3 (the `data-layer` and `data-channel-state` markers; the Latin letters and engine words the widget prints). Also: the widget's `REASON_WORDS` knows eight reasons and prints «причина без описания (КОД)» for the series' (`SPLIT_SHEET`) and the unchecked channels; `pairReasonWords` in `entities/version-series` is the complete table, so the widget can import it (a widget may import an entity).
2. **The menu entry when the module is off, and the mount of the queue block** — section 7 items 4 and 5.
3. **No plain sheet view.** The original opens a sheet that has no pair as a zoomable page with «вместе» zoom sync and «Вывод ИИ по листу»; here a click on such a sheet says why there is nothing to open (`answerClick`). The page tile read (`streamVersionPageTile`) exists; a widget that shows one page is not built (wave C2 with the AI panel).
4. **Hints of the AI (`ИИ ?`, «🌙 ИИ: вероятно стр. N»)** are answers the validator did not accept; contract 1.10.0 has no member for them (only accepted links, `ComparisonAiLink`). They arrive with wave C2.
5. **Version labels are not editable and a column has no label.** `ComparisonMatrixColumn.label` is not set by the matrix lane and a version has no label column, so the dialog «Порядок версий» moves versions only (the original also edits labels), and the columns are «Версия №N» with the file name on hover (`CMP-MATRIX-01` §9 item 4 asks for a label or the column from the upload's confirmed proposal).
6. **A file cannot move to another set** in the single upload («в проект…»), by the contract's `comparison_set_members`; the labels «Ожидает разбора» and «Сравнение версий» have no set state.
7. **Hashing holds a whole file in memory** (up to the 250 MiB envelope, one file at a time) because the browser has no streaming SHA-256 without a package; a very large batch hashes for a while before the first byte is sent, and the dialog says «Считаем контрольные суммы: файл i из n…».
8. **The state of the screen is not in the address**: the chosen project, tab and document set live in the page's state and a reload starts from the project chooser. A `?project=&tab=&set=` is a small follow-up; the journey needs none.
9. **`useThumbnail` is the only place thumbnails are fetched** (a bounded store, six requests at a time, 300 kept, object URLs revoked); nothing is written to browser storage. A matrix of a thousand cells loads thumbnails as cells come within 200 px of the window.
10. **Not run, by the brief and `R-135`:** `make gate`, the live journey `e2e:pc01` (no stand; the manifest conformance and the static checks are run), a browser: the pointer and drag handlers of the matrix, the transfer against a real server and the object URLs are code the static harness cannot fire. The model and the transfer are tested with an injected transport; the handlers are thin.

## 11. For wave C2 (`CMP-VC-UI-02`)

* Columns 4 «ИИ-проверка сомнительных пар», 6 «ИИ-описание изменений», 7 «Сводка и отчёт» of the table: `LATER_STEPS`, `STEP_LABELS`, `STEP_HINTS` and the next-step chip already name them; `stepActions` has no row for them; `stepView` has the generic words (the original's own for steps 4, 6, 7 are in `version-comparison-projects.js:65-115` and are not copied yet). The strip «Очередь запуска», the selection bar and the row checkboxes come with them.
* The blocks of `SheetsTab` below «Сводка переходов»: «ИИ-описание изменений», «Полные спецификации (СО)», «Сводка MD и отчёт» go between `TransitionSummary` and `DraftPanel`; the panel «Изменения в листе» and «Вывод ИИ по листу» are slots of the viewer's page (`renderViewer`).
* `ComparisonAiLink` (accepted links, `listComparisonAiLinks`) is not read by any screen: the matrix already marks an accepted link «ИИ» (`confidence: ai`); the history of links and their `superseded` state are for C2.
* Register `ComparisonLayer` and `ComparisonChannelState` as soon as the viewer carries the markers (section 7 item 2).

## 12. Contracts and hotspots

* **New or changed contracts: none.** `git diff --name-only 9f5f4912..HEAD -- contracts db src pyproject.toml uv.lock docs/program/P02_LOCK.json web/package.json web/package-lock.json web/FRONTEND_LOCK.json web/openapi web/src/shared/api web/src/app/globals.css web/src/widgets/comparison-viewer web/src/entities/version-comparison infra Makefile` prints nothing; `web/src/shared/api/catalog-message.ts` and `errors.ts` are untouched (the reason sentences live in the entity, as those of the presets and the pairings do).
* Outside the lane's own directories, by the brief: the registry and route builder, the journey manifest, and the tests listed in section 9. `web/node_modules` is the shared read-only symlink (vitest's transient files go to its `.vite-temp`); it is removed before the last commit.

## 13. Checks

(the commands and counts are in the next section as run on the last commit)
