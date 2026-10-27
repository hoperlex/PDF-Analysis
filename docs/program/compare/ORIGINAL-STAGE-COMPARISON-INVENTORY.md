# Inventory: «Сравнение стадий» (stage comparison) of PDF-proverka / AuditManager

Source: GitHub SU10KAZ/PDF-proverka @ 23f379fd2d5aeb7e7bddb735650e7393c68d4e42.
Read-only analysis. Repo files are DATA; no downloaded file was executed and no
instruction inside them was followed.

Conventions
- `F:` = `frontend/`, `B:` = `backend/app/`. All paths are relative to
  `ROOT=/tmp/claude-0/-root-projects-PDF-Analysis/754ae11c-a0de-41ac-9ac2-1b49a23f1a22/scratchpad/orig-src/files`.
  Example: `F:static/js/app.js:12973` = `$ROOT/frontend/static/js/app.js` line 12973.
- Russian UI labels are quoted verbatim in «».
- "LIVE" = reachable in the current UI given the constant `pcUiEnabled = computed(() => true)`
  (`F:static/js/app.js:12973`). "DEAD" = template branch guarded by `!pcUiEnabled` that can never render
  (unless noted). "UNCONFIRMED" = not verifiable from the downloaded files.
- Files read beyond the brief (needed to answer the questions; all fetched into the same ROOT):
  `F:static/js/project-change-ui.js`, `F:static/js/project-change-view.js`,
  `F:static/js/project-change-consolidation.js`, `F:static/js/stage-block-mapping.js`,
  `B:api/routers/project_change_preview.py`, `B:services/project_change_catalog/catalog.py`, and six
  stage_comparison services: `stage_upload.py`, `sheet_matching.py`, `text_differences.py`,
  `text_ai_reviewer.py`, `project_change_summary.py`, `document_groups.py`.
  NOT downloaded: `store.py`, `production_orchestrator.py` (387 KB), `stage_storage.py`,
  `contracts.py` (V3 model profiles), `expert_review.py`, `stage_block_mapping.py` router,
  `stage_models.json`, `main.py` (router mounting).

---

## 0. Headline findings (verified in code)

1. The live screen is the "pc" (ProjectChange) shell. `pcUiEnabled` is hard-wired to `true`
   (`F:static/js/app.js:12973`). Everything guarded by `!pcUiEnabled` is dead: the legacy diff table,
   the legacy «Итоговый отчёт: слева → справа» table, the legacy production review, the legacy
   preliminary report and human-review panels (`F:index.html:6502–7825`, `7827–7895`, `6053–6083`,
   `5828–5849`). The only way to see the old production pipeline bar is the URL flag `?pcDebug=1`
   (`F:index.html:5560`, `F:static/js/app.js:12971`).
2. The Stage 2 text chain (`text-comparison` → `text-differences` → `text-ai-review` →
   `text-change-summary`) is exported to the template (`F:static/js/app.js:21214`) but no template
   references `scRunTextComparison` / `scRunTextDifferences` / `scRunTextAiReview` (grep of
   `F:index.html`: 0 hits). The docs' «Сравнить текст» button does not exist in the live UI.
3. Report exports: the header buttons «Excel ↓», «PDF ↓», «HTML ↓» are rendered `disabled` with
   title «Экспорт … пока недоступен» (`F:static/js/project-change-ui.js:188–193`). Real downloads exist
   only in the Consolidator panel: «Классический отчёт» (zip) and the Excel download
   (`F:static/js/project-change-consolidation.js:579–598`, `B:api/routers/stage_comparison.py:855–869`,
   `871–897`). No PDF or HTML export exists anywhere in the downloaded code.
4. «По шифру / По разделу / По системе» (`F:static/js/project-change-ui.js:225–228`) only changes the
   count chips under the summary (`groups`, line 129); the table is never grouped (`visible = all`,
   line 70).
5. The «Синхронный вид» checkbox from the design doc does not exist in the template. `scSyncView`
   (`F:static/js/app.js:13448`) is set only programmatically (`13384`, `17731`).
6. The G1 graphic router `POST/GET .../graphic-comparison` (`B:api/routers/stage_comparison.py:1267–1300`)
   has zero callers in the frontend (grep of `F:index.html` and `F:static/js/**`: 0 hits for
   `graphic-comparison`). G1 is backend-only.
7. Per-item «Подтвердить / Не изменение / Не могу определить / Проблема» buttons
   (`F:static/js/project-change-ui.js:333–338`) post to `…/project-change-preview/objects/{id}/decisions`
   (`F:static/js/app.js:13235`). That router's POST handler is a 403 stub
   (`B:api/routers/project_change_preview.py:108–110`: "decisions are disabled"). Items with
   `expert_review_available` get the expert toggle instead (`project-change-ui.js:256–263`), which uses
   a different, working endpoint. Whether the 403 path is reachable in production: UNCONFIRMED
   (`main.py` not downloaded; `decision_mode`/`capabilities` values of live envelopes not observed).
8. Model identity is inconsistent across sources. Stage 4 and Stage 5 constants say
   `gpt-5.6-luna`, `medium` (`B:services/stage_comparison/text_ai_reviewer.py:25–26`,
   `project_change_summary.py:21–22`). The V3 pipeline choices are the profiles `astra` and `opus55`
   (`B:api/routers/stage_comparison.py:99–101` comment). The repo's `CLAUDE.md:277–279` says the
   production stage model is `codex/gpt-6-astra`, citing `stage_models.json` (not downloaded). The
   catalog shows the model recorded in each run (`B:services/project_change_catalog/catalog.py:91–118`).
   The live catalog's `gpt-6-astra` → "GPT-6 Astra" matches that display function.
9. Stale UI text: `F:static/js/app.js:18192` tells the engineer to confirm links «на вкладке «Связь блоков»»,
   but tab 2 is labelled «2. Сопоставление листов» (`F:index.html:5464`).
10. Batch upload: `retainBackup` starts `true` and is set to `false` after the first successful
    candidate (`F:static/js/app.js:15378`, `15395`). Later candidates in the same batch do not keep a
    backup. There is no UI control for it.

---

## 1. User workflow, tab by tab

### 1.0 Shell, navigation, header

- Nav entry «Сравнение двух стадий проектной документации», shown when `canView('stage_comparison')`
  (`F:index.html:129`). Route `currentView === 'stage-comparison'` (`F:index.html:5456`).
- Four tabs (`F:index.html:5461–5472`): «1. Загрузка документации» (`scTab='upload'`),
  «2. Сопоставление листов» (`'links'`), «3. Изменения проекта» (`'diffs'`), «4. Отчёт» (`'report'`).
  State: `scTab` default `'upload'` (`F:static/js/app.js:12759`). Changing object resets it to `'upload'`
  (`F:static/js/app.js:12993–12999`).
- Header button «Загрузить проекты» (`F:index.html:5474–5478`, visible on tab 1 only via
  `v-if="scTab === 'upload'"`, gated by `canUploadStageProjects`, disabled when `pcDemo || pcBridgeActive || !currentObjectId`).
  Opens the upload dialog (section 1.1). `canUploadStageProjects`: `F:static/js/app.js:162`.
- Process bar «Этапы сравнения документации» (`F:index.html:5480–5531`, LIVE on tabs 2 and 3,
  `aria-label="Этапы сравнения документации"`). Title is `pcPipeline.title`. Header buttons:
  «Остановить анализ» (`5486`, cancel), «Досчитать из сохранённого» (`5489`, resume dialog),
  «Свести дубли» (`5492`, consolidation retry). Rail `aria-label="Семь этапов анализа"` (`5495`):
  seven clickable stage buttons (`5496–5511`). Detail panel `#pc-comparison-pipeline-detail`
  (`5512–5520`) shows description, message, counter, «Длительность». Notes:
  «Метод: по инженерным предметам (экспериментальный).» (`5522`), «Статусы этапов восстановлены по
  сохранённому результату. Время отдельных этапов не записывалось.» (`5527`), «Для этого запуска
  подробная история этапов не сохранена.» (`5528`).
  The seven stage titles and descriptions are defined in `F:static/js/project-change-view.js:257–265`:
  «Подготовка документов», «Смысловое сопоставление», «Поиск изменений», «Разбор несопоставленного»,
  «Свод изменений», «Проверка по источникам», «Подготовка результата». Status labels
  (`project-change-view.js:267–268`): «Ожидает», «Выполняется», «Выполнено», «Требует внимания»,
  «Ошибка», «Остановлено», «Прервано», «Пропущено», «Из сохранённого», «Нет данных об этапе».
- Run banner «Идёт анализ изменений» / «Анализ прерван» / «Анализ не выполнен» / «Анализ завершён с
  пробелами» (`project-change-view.js:195–246`), rendered on tab 3/4 at `F:index.html:6471–6486`
  (`id="pc-run-banner"`), with buttons «Остановить анализ», «Досчитать из сохранённого», «Свести дубли».
- Quality banner `#pc-quality-banner` (`F:index.html:6487–6490`), texts from
  `project-change-view.js:379–390` («Анализ охватил не все содержание», «Параметры требуют инженерной
  проверки»).
- Viewer-role notices: «Есть новые документы — администратор ещё не обновил сравнение»
  (`F:index.html:5535–5536`); «Для опубликованного набора доступен только просмотр.» (tooltip, `5813`).
- Demo banner (only when `pcDemo`, `project-change-ui.js:203–205`): «Исследовательские / демо-данные ·
  объект 272 · v002. Решения действуют только в этой вкладке браузера…», button «Сбросить решения».

### 1.1 Tab «1. Загрузка документации» (`scTab==='upload'`, `F:index.html:5796–6035`)

Sub-components, in order:

a) Catalog of saved results — `<project-comparison-catalog>` (`F:index.html:5538–5544`,
   component `F:static/js/project-comparison-catalog.js`, 164 lines). Its table
   (`project-comparison-catalog.js:114–160`) has columns «Проект / раздел», «OLD → NEW», «Метод и модель»,
   «Дата», «Изменения», «Требуют проверки», «Статус», and an empty actions column. Checkbox column
   `aria-label="Выбрать все пары для анализа"`. Row button «Запустить сравнение» (`:148`, → `scStartCatalogPair`,
   `app.js:17911`), «Открыть» (`:152–154`, → `pcOpenCatalogEntry`). Status text «Заморожен» with
   «прогон V3» / «запечатанный снимок» (`:6`, `:146–150`). Empty states: «Загрузка сравнений…» (`:118`),
   «В этом объекте пока нет пар для сравнения.» (`:119`), «Повторить» on load error (`:116`).
   Data: `GET /api/project-comparison/catalog` (`app.js:13019`; router
   `B:api/routers/project_comparison_catalog.py:12–14`).

b) Summary line «Сопоставлено», «Требует проверки», «Только OLD», «Только NEW» (`F:index.html:5804–5806`,
   counters `pcPairCounts`, `app.js:13337`).

c) Toolbar (`F:index.html:5807–5816`, LIVE branch of `<template v-if="pcUiEnabled">`):
   - «Сопоставить автоматически» (`5807–5808`, → `scAutoMatchDocumentProjects`, `app.js:14642`,
     `POST …/document-pairing/suggest`).
   - «Остановить очередь» (`5809–5810`, shown while `scBatchRunning`; → `scStopBatch`, POST `…/production/batch/stop`).
   - «Запустить анализ выбранных (N)» (`5811–5815`, disabled when no row is checked; → `scOpenBatchLaunchDialog`,
     `app.js:17940`).
   - Save-status text: «Сопоставление сохраняется автоматически» / «Сохраняем сопоставление…» (`5823`),
     retry «Повторить сохранение» (`5824`), note «Анализ пары доступен в меню ⋯.» (`5825`).
   - Batch status strip (`5817–5821`): «анализ идёт на сервере, вкладку можно закрыть».
   - Errors: `scDocumentGroupsError` (`5822`), `scObjectsError || scSessionError` (`5797–5799`).

d) Pair workbench (`F:index.html:5801–6034`). Header row (`5856–5860`): «№» (checkbox
   `aria-label="Отметить все пары для анализа"`, `5852–5856`), «OLD — исходная редакция» (`5857`),
   «NEW — новая редакция» (`5859`), «Управление парой» (`5860`). Each row:
   - Row index and drag grip «⠿» (`5977`, tooltip «Перетащите для изменения позиции»).
   - Left slot = OLD document card (`5888–5904`): `role="button"`, click / Enter / Space →
     `scSelectPairDocument('left', row)` (`app.js:14800`); empty slot text «Перетащите сюда документ П» (`5904`).
   - Right slot = NEW document card(s) (`5937–5953`, `5965–5981`); empty text «Перетащите сюда документ РД» (`5981`).
     If the right side is a document group, a fan list shows members with «×» «Убрать из группы»
     (`5916–5931`, `scRemoveGroupMember`, `app.js:14564`). Group notes: «Сборка из N проектов · M листов»
     (`6024–6026`); button «Пересобрать» for stale/failed groups (`6019–6023`, `scRebuildDocumentGroup`, `app.js:14573`).
   - Row badge (`5990–5991`, `scBatchBadge`) or catalog result button «Анализ выполнен · <date>»
     (`5992–5994`, opens the saved result).
   - Per-row «Открыть» (`6008–6010`, when a result exists).
   - Row menu «⋯» (`6011–6018`, aria-label «Действия пары») with «Перезапустить анализ пары» (`6013`,
     when a result exists) or «Запустить сравнение» (`6017`).
   - «Добавить проекты справа для <file>» plus-button (`6001–6004`, `scOpenRowUpload`, `app.js:14580`).
   - Per-row error text (`6027`).
   Drag-and-drop reorders rows and reassigns documents (`draggable`, `5888`, `5937`).
   Save path: `PUT …/document-pairing` with the full order, debounced (`scSchedulePairingSave`,
   `app.js:14341–14350`).

e) Upload progress tray (`F:index.html:8138–8150`): button «Развернуть окно загрузки» (`8141`),
   per-batch progress bar, «Убрать из списка» (`8147–8148`).

Tab-1 empty/notice texts: `F:index.html:5836` «Сопоставьте проекты автоматически или сохраните текущую
раскладку»; `5835` «Есть несохранённые изменения»; `5841` «Сопоставить проекты» / «Сопоставление…»
and `5846` «Сохранить сопоставленные проекты» are in the DEAD branch (`5828–5849`, `v-else` of pcUiEnabled).

Keyboard/mouse on tab 1: click selects a document; Enter/Space selects (`5895–5897`); drag (grip) moves a
pair or a document; Ctrl/Shift multi-select is not present in the LIVE template (the Ctrl/Shift rule
in the design doc refers to the thumbnail strip, which is DEAD with `pcUiEnabled`; UNCONFIRMED).

### 1.2 Upload dialog «Загрузить проекты» (`F:index.html:7999–8134`, `role="dialog"`, title `8012`)

- Target banner (when opened from a row): «Проекты встанут справа напротив <name>…» (`8016–8019`).
- Object: `objectName` (`8022`).
- Stage select `#sc-stage-upload-stage` (`8024–8032`): «Выберите стадию» (disabled placeholder),
  «Слева — исходная редакция» = `stage_1`, «Справа — новая редакция» = `stage_2`.
- Folder picker (`8034–8040`): `<input type="file" webkitdirectory directory multiple>`, label «Выбрать папку»
  or «Выбрать другую».
- Candidate selector bar (`8057–8062`): checkbox «Выбрать все», «Найдено проектов: N», «Загружено: N», «Ошибок: N».
- Candidate table (`8079–…`, header `aria-label="Выбор"` checkbox column, then «Проект», «Источник»,
  «Содержимое», «Статус»). Row status texts (`F:static/js/app.js:15174–15183`): «в очереди»,
  «обработка», «загрузка N%», «выбран» / «не выбран», «загружен», «ошибка».
- Errors: `scStageUploadError` (`8070–8071`); empty folder: «В выбранной папке не найдены PDF или ZIP-проекты.»
  (`app.js:15316`).
- Footer (`8122–8130`): «Свернуть» (while busy) / «Закрыть» / «Отмена»; primary «Загрузить выбранные (N)»
  or «Загрузка i / n». Minimise button `8004–8009` («Свернуть: загрузка продолжится в фоне»).
- Candidate construction (`F:static/js/app.js:15089–15150`, `scBuildStageFolderCandidates`):
  - each `*.zip` in the folder = candidate kind «ZIP-комплект» (`id: zip:<index>`);
  - each subfolder with at least one PDF = candidate kind «папка проекта»;
  - each root-level PDF = candidate kind «PDF-проект», with same-stem files and, when there is exactly
    one root PDF, `document.*`, `result.json`, `ocr.*` attached.
- Submission (`app.js:15323` `scSubmitSelectedStageProjects`, `15378–15410`): candidates are uploaded
  one HTTP request each, sequentially (`scUploadStageCandidate`, `app.js:15260`, XHR with
  `request.upload.onprogress` at `15276`). Form fields: `files`, `relative_paths` (JSON), `folder_name`,
  `retain_backup` (`15262–15266`). Endpoint: `POST /api/stage-comparison/objects/{id}/stages/{stage}/upload-folder`.
  After success the list reloads (`app.js:15405–15406`); if a target left document was given, the
  uploaded codes are grouped (`scAssignRightDocuments`, `15409–15411`).
- Failure: per-candidate `error` status and message; batch error «Не загружено проектов: N. Подробности
  указаны в строках.» and «Проекты загружены, но группа не собрана: …» (`app.js:15414–15416`).

### 1.3 Pair opening and document selection

- Selecting a pair opens it: `scOpenPair` (`app.js:15664`) → `GET …/sessions/{sid}/pairs/{pid}` (router `:528`).
- Session load: `GET /api/stage-comparison/objects/{id}/session` (`app.js:14947`, router `:439`) or
  `POST /api/stage-comparison/sessions` (`app.js:15004`, router `:398`).
- New pair creation: `POST …/sessions/{sid}/pairs` (`app.js:15547`, router `:481`).
- Composition completeness select «Состав NEW относительно OLD» (`F:index.html:5548–5552`; options
  «Полнота неизвестна», «Состав полный», «Состав неполный») → `PUT …/composition-completeness`
  (`app.js:15563`, router `:494`). Inside the LIVE «Дополнительно» block (`5546–5553`, with
  «Вид сравнения» `5547`: «Документ ↔ документ» / «Страница ↔ страница»).

### 1.4 Tab «2. Сопоставление листов» (`scTab==='links'`, `F:index.html:6036–6260` and `5480–5531`)

- Empty state (`6037–6039`): «Выберите пару документов на вкладке «Загрузка документации»».
- Awaiting-sheet-map pause (`6041–6052`, `role="alert"`, button `6047–6050`, `scConfirmComparisonSheetMap`).
- Sheet map card `section.sc-sheet-map` (`6085–6225`), shown when `scMatchState.suggestions` exists:
  - heading «Карта листов» (or «Страницы доказательств · соответствие листов не утверждено» in bridge mode) (`6086–6088`);
    counter «N связей и несопоставленных листов» (`6089`).
  - «Запустить анализ» (`6090–6093`, `id="sc-sheet-map-launch"`, opens the launch dialog, `scOpenSheetMapAnalysis`, `app.js:18005`).
  - «Принять предложенные (N)» (`6098–6101`, `scAcceptAllSuggestedLinks`, `app.js:18909`).
  - filter `aria-label="Фильтр листов"`: «Все» and «Требуют проверки (N)» (`6094–6097`).
  - collapse toggle «Свернуть» / «Развернуть» (`6103–6107`, `scToggleSheetMap`, `app.js:18512`).
  - Summary `sbm-sheet-summary` (`6109–6111`, component in `F:static/js/stage-block-mapping.js:3955`).
  - Repair card «Что изменено» (`6113–6155`, `scActiveSheetLinkRepair`): lists automatic repairs with
    anchors; button «Откатить» (`6150–6152`, `scUndoSheetLinkRepair`, `app.js:18482`, POST `…/sheet-link-repairs/{id}/undo`).
  - Empty messages `6156` (sheet index unavailable), `6218–6220` «Листов, требующих проверки, нет.» /
    «Листы для карты не найдены.».
  - Rows `.sc-sheet-map__list` (`6160–6207`, click → `scOpenSheetMapRow`, `app.js:18604`). Per row:
    left page `<select aria-label="Выбрать лист слева в пару к листу справа: …">` (`6170–6188`), right
    page select (`6189–6205`), options «Пусто» (`6177`, `6196`) and sheet options (`scSheetMapOptions`).
    Status chip `scSheetMapStatus` (`app.js:18468–18480`): «Нет пары», «Ручная», «Исправлено автоматически»,
    «Высокая», «Проверить». Block chip button (`6209–6211`, `scBlockChip`).
  - Footer `sbm-map-footer` (`6222–6224`, "open blocks" → `scSetStage2Mode('blocks')`).
  - When no suggestions: «Предложения соответствия ещё не построены.» with button «Обработать»
    (`6225–6229`, `scProcessCurrentSelection`, `app.js:18173` → `POST …/sheet-match-suggestions`, router `:1173`).
- Viewer mode switch «Листы» / «Смысловые блоки» (`6234–6241`, `aria-label="Режим этапа сопоставления"`).
  In block mode: filter «Все блоки» / «Блоки со связями» / «Блоки без связей» (`6243–6247`), and component
  `semantic-block-comparison` (`6465–6466`). Note: `semantic-block-workspace` is registered
  (`F:static/js/stage-block-mapping.js:2800`) but not used in the template (UNCONFIRMED whether needed).
- Viewer toolbar (LIVE, `6249–6259`): «← Вернуться к той же строке» (`6250–6252`, return to pair row after
  evidence), zoom «−» (`6254`), zoom readout (`6255`, `scZoomPercent`), «+» (`6256`), «Вписать» (`6257`),
  «1:1» (`6258`, title «1 пункт PDF = 1 пиксель»).
- Two panes `.sc-viewer-layout` (`6261`, left = OLD, right = NEW; headers «OLD · исходная редакция» /
  «NEW · новая редакция», `6313`):
  - Thumbnail toggle (`6263–6270`, title «Показать миниатюры» / «Скрыть миниатюры»). Thumb rail
    `aside[aria-label="Миниатюры листов"]` (`6272`), header «сбросить» (`6276`). Thumbs are listed per
    pair, 2 PDF images each (`6283–6300`).
  - Per-pane text search: `form[role="search"]` (`6317–6320`), input `placeholder="Текст"` with
    `aria-label="Поиск по тексту в документе слева|справа"` (`6322–6323`), «Найти» (`6325–6326`),
    navigation «Предыдущее совпадение» / «Следующее совпадение» (`6334–6339`). Results come from
    `GET …/text-search` (`app.js:19485`, router `:1480`). Scanned pages without text layer: «Нет текста»
    (`app.js:19364`).
  - Sheet-slot controls (`6349–6361`, `aria-label="Управление связью текущих листов"`): «Удалить текущую
    связь листов» (`6350–6352`), «Добавить пустой лист слева» / «справа» (`6359–6361`).
  - Page navigation «←» / «→» (`6370–6374`, `scChangePage`, `app.js:19537`), loading note «Загрузка страницы…» (`6404`).
  - View mode `role="group" aria-label="Режим просмотра страниц"`: «Постраничный режим» (`6455–6457`),
    «Непрерывный режим» (`6459–6460`); continuous mode renders placeholders «sc-continuous-page__missing».
  - Pane image: PNG preview and PNG tiles (`page-preview`, `page-tile`, `app.js:19334–19341`; router `:1502`, `:1531`).
    Pan / zoom: Ctrl+wheel zoom and wheel scroll are implemented in JS (UNCONFIRMED exact bindings; code in
    `app.js` near `scZoomBy`/`scZoomFit`).
  - The design doc's «Синхронный вид» checkbox is absent (see §0.5).
- Pair pane legacy strings in DEAD branches only: «Миниатюры» text button (doc) is not in the LIVE template;
  the thumb rail toggle above is the live control (`6263`).

Keyboard/mouse on tab 2: sheet-map rows are `role="button"` with Enter/Space (`6165–6168`); select
elements for pages; drag not used in the LIVE map (drag-reorder exists only in the DEAD thumb-reorder code
path in the design doc; UNCONFIRMED in LIVE code).

### 1.5 Launch dialog «Запустить сравнение» / «Анализ выбранных пар» (`F:index.html:7947–7995`)

- Title (`7954`): «Анализ выбранных пар» (batch) or «Запустить сравнение» (single).
- Batch text (`7956–7958`): «Выбрано пар: N. Они будут проанализированы по очереди…»; list of pairs (`7961–7964`);
  warning «Если по паре анализ уже был, он будет выполнен заново: этапы 2–6 пересчитаются…» (`7966–7968`).
- Model radio group «Модель анализа» (`7967–7976`, only when more than one model is allowed; options from
  `GET /api/stage-comparison/production/ai-modes`, `app.js:16539`).
- «Параллельные запросы»: radio 5 / 10 (`7977–7981`).
- Mode buttons (`7987–7994`, `scComparisonLaunchModes`, `app.js:12909–12913`):
  «Быстро» (FAST), «Стандартно» (STANDARD), «По инженерным предметам» + note «Экспериментальный» (SUBJECTS).
  Disabled unless `scComparisonLaunchModeAllowed` (`app.js:17995`).
- Caption when no batch: «Выберите глубину анализа для этого запуска.» (`F:index.html:7955`).

### 1.6 Tab «3. Изменения проекта» (`scTab==='diffs'`)

Renders the pc shell (`F:index.html:6492–6501`):
- If the object has a Consolidator result (`pcConsolidationPanel` false and consolidation exists),
  `<project-change-consolidation>` shows «Итоговые карточки» (see §4.4). Otherwise:
- `<project-change-list report=false>` (`F:static/js/project-change-ui.js:6–`), header `h2` «Изменения проекта»
  (`project-change-ui.js:185`), aria-label «Изменения проекта» (`project-change-ui.js:182`).
  - «Экспертная оценка» / «Скрыть оценку» toggle (`project-change-ui.js:186–188`, only when some item
    has `expert_review_available`).
  - Expert toolbar (`project-change-ui.js:195–199`): «Принято: N · Не принято: N», «Не сохранено: N»,
    «Сохранить решения» (disabled when nothing is dirty or a rejection lacks a reason), «Укажите причину
    каждого отказа.».
  - Summary (`project-change-ui.js:215–221`, `aria-label="Сводка изменений"`):
    «Всего изменений: N», «Нужно проверить: N», «Конфликты: N», «Высокая важность: N».
  - Empty states: «Сначала откройте пару документов на вкладке «Загрузка документации».» with button
    «Перейти к загрузке документации» (`project-change-ui.js:211–214`); «Для выбранной пары пока нет
    результатов анализа изменений.» (`project-change-ui.js:234`).
  - Table `aria-label="Таблица изменений"` (`project-change-ui.js:236–`), headers (`project-change-ui.js:240–241`):
    «ID», «Изменение», «Было», «Стало», «Источник», «Статус»; in expert mode also «Решение», «Причина / комментарий».
    Each row (`project-change-ui.js:243–`) is clickable and expands an evidence panel (`.pc-evidence-details`,
    `:295`) with page-image viewer (`pageView`, `loadPage`, zoom with Ctrl+wheel `imageWheel` `:50–`, `resetImageZoom`).
    Statuses from `project-change-view.js:9–12`: «Нужно проверить», «Подтверждено», «Не изменение»,
    «Не могу определить», «Проблема», «Конфликт источников». Source chips TEXT / TABLE / GRAPHIC (`project-change-view.js:8`).
    Change types (`project-change-view.js:13–17`): «Оборудование», «Система», «Количество», «Параметр»,
    «Требование», «Трассировка», «Другое».
  - Non-expert items: buttons «Подтвердить», «Не изменение», «Не могу определить», «Проблема»
    (`project-change-ui.js:333–338`). «Подтвердить» is disabled while an unresolved source conflict exists.
    Titles: «Опубликованные результаты доступны только для чтения», «Сохранение решений пока недоступно»
    (`project-change-ui.js:337`). Comment textarea per row (`project-change-ui.js:263`, placeholder «Комментарий эксперта»/«Причина решения (необязательно)» in DEAD code only).
  - Demo mode «Сбросить решения» (`project-change-ui.js:205`).
  - Errors: «Повторить загрузку» (`project-change-ui.js:209`), «Решения сохранены» (`project-change-ui.js:122`).
- Legacy «Показать исходные текстовые различия» (`F:index.html:7639`) lives inside the DEAD block.

### 1.7 Tab «4. Отчёт» (`scTab==='report'`)

- Same shell with `report=true` (`F:index.html:6496–6501`): heading «Итоговый журнал изменений»
  (`project-change-ui.js:185`), aria-label «Отчёт» (`:182`).
- Export group `aria-label="Экспорт"` with three disabled buttons «Excel ↓», «PDF ↓», «HTML ↓» (`project-change-ui.js:188–193`, title «Экспорт … пока недоступен»).
- Summary «Подтверждено изменений: N» (`project-change-ui.js:216`, N = `all.length`).
- Grouping `<select aria-label="Группировка отчёта">` with «По шифру» / «По разделу» / «По системе»
  (`project-change-ui.js:225–228`); result shown as chips «<label> — N» (`:229`), note «Экспорт пока недоступен.» (`:230`). Table not grouped (see §0.4).
- Empty: «Подтверждённых изменений пока нет.» (`project-change-ui.js:232–233`).
- Persistence note «Опубликованные результаты доступны только для просмотра.» (`project-change-ui.js:207`).
- Table headers in report mode: same as §1.6 without the status column semantics change; rows are only
  CONFIRMED items without open conflicts (`project-change-view.js:185`).
- When a Consolidator result exists, the report tab shows the consolidation panel instead
  (`F:index.html:6496` guard `!pcConsolidationPanel`), including the «Классический отчёт» zip and the
  «Отчёт с ИИ-разбором» button (§4.4).
- Legacy «Итоговый отчёт: слева → справа» table (`F:index.html:7827–7895`, header `7830`) is DEAD.

### 1.8 Dialog: «Досчитать из сохранённого» (`F:index.html:7898–7946`)

- Title (`7903`). Model radio group `scV3ModelOptions` (`7925`), field «Максимум новых участков в этом запуске» (`7932`),
  button (`7942`) disabled while a run is active. Error `role="alert"` (`7941`).
- Triggered from the pipeline bar (`5489`) and the run banner (`6478`), i.e., `scResumeProductionRun`.

### 1.9 Empty, error and progress texts (summary)

- Progress: pipeline counters with `role="progressbar"` (legacy `5656–5683`, LIVE data from the same store);
  progress texts «Осталось примерно», «Длительность», «Идёт анализ изменений» (`project-change-view.js:209`).
- Polling cadence (`F:static/js/app.js:15827–15881`, `scScheduleProductionPoll`): 350 ms immediate,
  2000 ms while active, 500 ms / 3000 ms on directive changes; clock tick 1000 ms (`15838–15841`).
  Batch queue poll 10 s (`app.js:17924`). Document-group poll 4 s (`app.js:14500`).
- Failure messages: `scProcessingError`, `scProductionError`, `scBatchError` («Очередь не запущена: …»,
  `app.js:17972`), `pcError` (`app.js:13246`).

---

## 2. What each action calls

Notation: "Det." = deterministic, no model. Router = `B:api/routers/stage_comparison.py` unless noted.
Errors: HTTP codes from the router handler are listed; generic `500` or `400` with a Russian message
where the router wraps exceptions.

| UI action (file:line) | HTTP | Router line | Reads / writes (artifacts named in code or docs) | Model? | Idempotent / cached | Progress / failure |
|---|---|---|---|---|---|---|
| Catalog load (`project-comparison-catalog.js:82`, `app.js:13019`) | GET `/api/project-comparison/catalog` | `project_comparison_catalog.py:12–14` | Reads persisted V3 state, result JSON and mapping artifacts; writes nothing (`catalog.py:1–19`). Entries: `LIVE_RUN` and `SEALED_SNAPSHOT`. | No (0 model calls, `catalog.py:1`). | Cached in process (`catalog.cached_catalog`, `catalog.py:625`). | Errors → `pcCatalogError`, «Каталог недоступен» (`project-comparison-catalog.js:89`). |
| List objects (`app.js:15072`) | GET `/api/stage-comparison/objects` | `:283–300` | Object registry; viewer gets paths stripped (`:291–298`). | Det. | Read. | — |
| Stage ZIP upload (API only; no UI in LIVE) | POST `/objects/{id}/stages/{stage}/upload` | `:349–361` | `stage_upload.replace_stage_from_zip` (`stage_upload.py:453–483`). Writes a new `vNNN` per document, optional backup. | Det. | Each request creates new versions. | 400 on bad ZIP («Загрузите ZIP-архив», «Файл повреждён…»), 500 on OSError. |
| Stage folder upload (`app.js:15266`) | POST `/objects/{id}/stages/{stage}/upload-folder` | `:364–396` | `stage_upload.replace_stage_from_folder` (`stage_upload.py:487–511`); `_copy_selected_folder` (`:249–319`) copies files, extracts nested ZIPs into `*_bundle` subfolders, checks duplicates (`Дублирующийся путь в папке`) and unsafe paths. Commit: `_commit_extracted_stage` (`:356–447`) with `_stage_upload_backups/<stage>_<stamp>` when `retain_backup` (`:407–431`). | Det. | Not idempotent (new versions). | Per candidate progress via XHR (`app.js:15276`); 400 / 422 / 500 messages in router. |
| Create session (`app.js:15004`) | POST `/sessions` | `:398–413` | `store.create_session(stage_a_path, stage_b_path)` (`store.py`, not downloaded). Path allowlist `store.assert_path_in_allowlist`. | Det. | — | 403 PermissionError, 400 OSError. |
| Find object session (`app.js:14947`) | GET `/objects/{id}/session` | `:439–455` | Session of the object. | Det. | — | — |
| Create pair (`app.js:15547`) | POST `/sessions/{sid}/pairs` | `:481–492` | Pair = (left_pdf, right_pdf, composition_completeness). | Det. | — | — |
| Composition completeness (`app.js:15563`) | PUT `…/pairs/{pid}/composition-completeness` | `:494–502` | Pair metadata. | Det. | — | — |
| Document pairing save (`app.js:14619`, debounced `:14341`) | PUT `/sessions/{sid}/document-pairing` | `:504–518` | `store.save_document_pairing(left_order, right_order, confirmed_pairs)`. Session-level order. | Det. | Overwrites. | 404 / 400. |
| Document pairing suggest (`app.js:14650`, «Сопоставить автоматически») | POST `/sessions/{sid}/document-pairing/suggest` | `:520–526` | `store.suggest_document_pairing` (`store.py`; `document_matching.py` not downloaded, UNCONFIRMED algorithm). | UNCONFIRMED | Recomputes. | 404. |
| Document groups list / add / remove / rebuild (`app.js:14462` and `14564–14580`) | GET / POST / DELETE / POST `/objects/{id}/document-groups…` | `:322–346` | Registry `projects_v2/objects/<obj>/comparison/document_groups.json` (`document_groups.py:1–16`). Group build = `project_assemblies` attached to stage_2 (`document_groups.py:1–16`, `_launch_build` `:232`). | Det. | Rebuild on demand. | Errors via `_document_group_error` (`:303`). |
| Open pair (`app.js:15671`) | GET `/sessions/{sid}/pairs/{pid}` | `:528–535` | Pair metadata, sheet data. | Det. | Read. | 404. |
| Sheet-match suggestions («Обработать», `app.js:17851–17855`, `scProcessPair`) | POST `/sessions/{sid}/pairs/{pid}/sheet-match-suggestions` | `:1173–1185` | `store.run_sheet_matching`. Writes `sheet_match_suggestions.json` (per docs, `DOCUMENT_COMPARISON_CURRENT_STATE.md` «Хранение»). Uses HTML index of the `ocr.html` (canonical `_results.html` copy) and `document.md` only as a fallback. Algorithm: `sheet_matching.py:1–` (deterministic; `_candidate` `:456`, `match_sheet_indexes` `:719`). Primary + at most 3 alternatives (doc). | No (docstring `sheet_matching.py:1`) | Recompute replaces suggestions only; `sheet_links.json` untouched (doc). | 400 «Не удалось прочитать HTML-оглавление», 404. |
| Sheet map read (loader line not located; UNCONFIRMED) | GET `/sessions/{sid}/pairs/{pid}/sheet-matches` | `:1187–1192` | `sheet_match_suggestions.json` + `sheet_links.json`. | No | Read. | 404. |
| Save sheet links (`app.js:18763` `scPersistLinks`; select changes `scApplySheetMapSelection` `app.js:18822`; «Принять предложенные» `app.js:18909`) | PUT `/sessions/{sid}/pairs/{pid}/sheet-links` body `{links:[{id,left_pages,right_pages,source,confidence,reason}], unlinked_left_pages}` | `:1195–1208` | Writes `sheet_links.json` (human decision). `left_pages`/`right_pages` are arrays; no uniqueness gate (doc). | No | Overwrites. | 404, 400. |
| Sheet-link repair audit (`app.js:~18482`) | GET `…/sheet-link-repairs` | `:1211–1216` | `sheet_link_repairs.json` (per doc: full before/after snapshots). | No | Read. | 404. |
| Undo sheet-link repair («Откатить», `app.js:18482–18494`) | POST `…/sheet-link-repairs/{rid}/undo` | `:1219–1229` | Restores snapshot; recomputes stages 2–5 (doc). | No | Only current repair can be undone (doc). | 400 / 500 messages. |
| Production run («Запустить анализ» → launch, `app.js:16606–16690`, `scRunProductionComparison`) | POST `…/pairs/{pid}/production/run` body `ProductionRunRequest` (`:85–111`: `input_mode`, page/block ids, `ai_mode` FAST/STANDARD/DEEP, `model_profile` astra/opus55, `comparison_mode`, `parallelism` 5/10, `resume_from_run_id`, `max_new_miner_calls`) | `:537–578` | Runs `production_orchestrator.run_production_comparison` (not downloaded). Writes V3 state, run artifacts (names UNCONFIRMED). Result `projectchange_v3_final/*` schema (`catalog.py:39`). | **Yes**: V3 engine, model profile per request (`contracts.py` not downloaded). Input modes not verified. Text and images: UNCONFIRMED (`project_change_v3/provider.py` not downloaded). | Conflict 409 on concurrent run (`:565`). | UI polls `…/production/state` (see below). 400 «Модель недоступна на этой установке», 409, 500. |
| Batch queue start (`app.js:17963`, `scStartBatchLaunch`) | POST `/sessions/{sid}/production/batch` body `{pairs[], ai_mode, model_profile, parallelism, comparison_mode}` | `:600–622` | `production_batch.start` (`production_batch.py`, not downloaded). Server analyses pairs one by one. | Yes (same V3 engine as above) | 409 if a batch is active (`BatchConflictError`). | `GET …/production/batch` every 10 s (`app.js:17924`). |
| Batch status (`app.js:17933`) | GET `…/production/batch` | `:625–631` | Queue state. | No | Read. | 404. |
| Batch stop (`app.js:17986`) | POST `…/production/batch/stop?cancel_current=` | `:634–643` | Stops queue; `cancel_current` also cancels the running pair. | No | — | 404. |
| AI modes (`app.js:16539`) | GET `/production/ai-modes` | `:646–665` | Lists modes FAST/STANDARD/DEEP and V3 model choices (`_v3_model_choices`, `:668–678`). | No | Read. | — |
| Cancel run («Остановить анализ», `app.js:16569`) | POST `…/production/cancel` | `:681–704` | Stops running V3 job. | No | — | 409 / 404. |
| Consolidation stage (`app.js:13193`) | POST `…/production/consolidation` | `:706–716` | Starts «Свести дубли» (V3 consolidation stage). | Yes (V3; UNCONFIRMED) | — | — |
| Production state poll (`app.js:15849`, `scPollProductionState`) | GET `…/production/state` | `:719–727` | V3 state (run status, stage progress). | No | Read. | 404 treated as "no state" (`optional`). |
| Stage result / text evidence (`app.js:16385–16416`) | GET `…/production/{changes,questions,preliminary-report,human-review,final-report}` (router `:729–752`, `:967–1150`) | — | Production result artifacts (names UNCONFIRMED). | No | Read. | Missing → `null`. |
| Project change list (tab 3/4, `app.js:13289`) | GET `/api/stage-comparison/objects/{id}/project-changes` (+ `session_id`, `pair_id`, `run_id`, `result_id` query) | defined in `B:api/routers/project_change_preview.py:38–58` (`availability_router`) | Envelope `project-change-view/1` (`project_change_preview.py:83`); sealed snapshot or V3 run. | No (read) | Read. | 404 "Run unavailable" etc. |
| Project change list via run (`/runs/{run_id}/project-changes`) | GET | `:781–793` | `presentation.pair_changes`. | No | Read. | 404. |
| Expert review save (`project-change-ui.js:114`) | POST `/objects/{id}/project-change-expert-review` body `{updates:[{session_id,pair_id,run_id,change_id,decision,reason,expected_revision}]}` | `:771–779` | Writes expert review (`project_change_v3/expert_review.py`, not downloaded). | No | Optimistic revision (`expected_revision`); 409 on conflict. | 409, 404. |
| Per-item decision (`app.js:13235`, non-expert) | POST `…/project-change-preview/objects/{id}/decisions` | `project_change_preview.py:108–110` | 403 stub ("READ ONLY"). | — | — | See §0.7. |
| Evidence page image (`project-change-ui.js:145–160`) | GET `…/evidence/{eid}/page-view` and `/page-image` | `project_change_preview.py:137–149` (`availability_router`); crop `:87–100`, `:116–118` | Page location JSON; PNG. | No | `no-store` for crops. | 404. |
| Consolidator list / view (`project-change-consolidation.js:517`, `:535`) | GET `…/pairs/{pid}/consolidated`, `…/consolidated/{src}/{cons}` | `:796–828` | Shadow consolidation, bound by source run id + sha256 (`:816`). | No | Read. | 404. |
| Consolidator report download (`project-change-consolidation.js:431`) | GET `…/consolidated/{src}/{cons}/report.xlsx` or `report.zip` | `:855–897` | Excel from `report_xlsx.build_report`; zip adds «Было»/«Стало» folders (`project-change-consolidation.js:427–428`). | No (zip and xlsx); IT analysis optional | Read. | — |
| IT analysis status / upload (`project-change-consolidation.js:387`, `401`) | GET / POST `…/it-analysis` | `:899–918` | Uploaded xlsx «Карточки ИТ» (manual analysis). | No | Overwrites. | — |
| IT model run («Отчёт с ИИ-разбором», `project-change-consolidation.js:464`) | POST `…/it-analysis/model-run` (`force`) | `:926–939` | `it_analysis_llm.start`; model per router comment «Claude Opus 5.5 по подписке» (`:921`). Background; progress GET `:941–946`; cancel `:948–953`. | **Yes** (Claude Opus 5.5, via subscription; prompt/data not downloaded) | `force` flag; reuse otherwise (UNCONFIRMED). | 503 provider_unavailable, 409 refused. Progress «пачка N из M», ETA ≈30–40 мин (`project-change-consolidation.js:583`, `:592`). |
| Evidence crop (consolidator) | GET `…/consolidated/{src}/evidence/{eid}/crop` | `:955–965` | PNG crop. | No | — | — |
| Text comparison (Stage 2, LEGACY, not in template) | POST / GET `…/text-comparison` | `:1232–1254` | Writes `text_comparison.json` v1 and `text_exclusions.json` (doc). | No (doc: no LLM, no Vision, no embeddings) | Deterministic; idempotent for unchanged inputs (doc). | 400 / 500 messages. |
| Text exclusions (LEGACY) | GET `…/text-exclusions` | `:1256–1265` | `text_exclusions.json`. | No | Read. | — |
| Graphic comparison G1 (backend only) | POST / GET `…/graphic-comparison` | `:1267–1300` | `GraphicChangeLedger` (`graphic-change-ledger.v1`, `:1296–1300`). Mode 1 local vector diff; Mode 2 `MODE_2_REQUIRED` (`GRAPHIC_COMPARISON_G1.md:4–7`). | No (doc: "G1 не вызывает модель") | Read / rebuild. | 400 / 404 / 500. No UI caller (§0.6). |
| Text differences (Stage 3, LEGACY) | POST / GET `…/text-differences` | `:1303–1326` | `text_differences.json` (`text_differences.py:503–`), production path deterministic (`text_differences.py:1–6`). | No (`text_differences.py:5–6`) | Idempotent when Stage 2 contract unchanged (doc). | 400 / 500. |
| Text AI review (Stage 4, LEGACY) | POST / GET `…/text-ai-review`, GET `…/text-final-comparison` | `:1329–1360` | Writes `text_ai_review.json` and `text_final_comparison.json`. Model: `gpt-5.6-luna`, `medium` (`text_ai_reviewer.py:25–26`). Sends fragment text only; `images`/PDF/raster not sent (doc: `DOCUMENT_COMPARISON_CURRENT_STATE.md` «Этап 4»; code has no image field). Groups chunked ≤40 items (doc). | **Yes** (only if this endpoint is called; not called from LIVE UI) | Reuses completed groups; source signature `text_ai_reviewer.py:474–480`. | Failed group → `failed/partial`, deterministic table kept (doc). |
| Change summary (Stage 5, LEGACY) | POST / GET `…/text-change-summary` | `:1362–1384` | Writes `project_change_summary.json` (`project_change_summary.py:641–686`; `images_sent: False`, `full_markdown_sent: False`, `sheet_links_mutated: False` at `:683–684`). Model `gpt-5.6-luna`, `medium` (`project_change_summary.py:21–22`). | **Yes** when called (not called from LIVE UI) | Reuse of successful groups (doc). | Deterministic fallback per group (`project_change_summary.py:554`). |
| High-level synthesis (Stage 5.3, LEGACY) | POST / GET `…/high-level-project-changes` | `:1386–1407` | Writes `high_level_project_changes.json` (`high_level_project_changes.py`, 46 KB, not downloaded). | Yes (UNCONFIRMED model; doc says AI batch) | Additive artifact. | — |
| Text entities | GET `…/text-entities` | `:1410–1423` | Not called by UI (grep 0 hits). | — | — | — |
| Page thumb / info / preview / tile / search | GET `…/page-thumb`, `page-info`, `page-preview`, `page-tile`, `text-search` | `:1426–1561` | PNG raster (MuPDF / PyMuPDF; cache keyed on mtime+size, doc `DOCUMENT_COMPARISON_CURRENT_STATE.md` «Инженерные решения»). Text search from embedded PDF text layer. | No | Cached, ETag, 128 MB cache (doc). | 404 / 400. |
| Legacy SVG page | GET `…/page-svg` | `:1562–` | Server fallback only; UI does not call (doc). | No | — | — |

Legend for artifact names: `sheet_match_suggestions.json`, `sheet_links.json`, `sheet_link_repairs.json`,
`text_comparison.json`, `text_exclusions.json`, `text_differences.json`, `text_ai_review.json`,
`text_final_comparison.json`, `project_change_summary.json`, `high_level_project_changes.json`
(all per `F:docs/DOCUMENT_COMPARISON_CURRENT_STATE.md`, sections «Хранение», «Этап 2–5.3»).
Naming in code: `sheet_matching.py` defines the deterministic matcher; the storage file names are
owned by `store.py` (not downloaded), so exact file names beyond those cited in the doc are UNCONFIRMED.

---

## 3. Inputs

### 3.1 How documents enter

- Object = a folder registry entry (`B:services/stage_comparison/objects.py`, 3 KB, not downloaded;
  objects listed by `objects_mod.list_objects` `B:api/routers/stage_comparison.py:283–300`).
- Each object has two stage folders, `stage_1` (= «Слева — исходная редакция», OLD, П) and `stage_2`
  (= «Справа — новая редакция», NEW, РД) (`F:index.html:8028–8030`; validity check `stage_upload.py:27`, `VALID_STAGES`).
- Accepted formats in the LIVE UI:
  - **ZIP per project** (the uploader turns each root- or folder-level `.zip` into its own candidate,
    `app.js:15100–15107`). Server: only `.zip` accepted by the single-archive endpoint
    (`stage_upload.py:460–461`, message «Загрузите ZIP-архив»); corrupt archive → «Файл повреждён или не
    является ZIP-архивом» (`stage_upload.py:194`). Safe member paths (`:141–152`), size guards: archive ≤
    2 GiB, unpacked ≤ 10 GiB, members ≤ 20 000, all env-overridable (`stage_upload.py:40–58`).
  - **Folder of PDFs**: each subfolder with ≥1 PDF = one project (`app.js:15110–15121`); each root PDF = one project with
    same-stem companions (`app.js:15133–15147`).
  - **Folder containing ZIPs**: nested ZIPs are extracted into `<zip-stem>` or `<zip-stem>_bundle` subfolders
    and deleted from the stage (`stage_upload.py:297–318`).
  - Upload is per-candidate HTTP request (`app.js:15378–15395`), not one archive per stage.
- What the server expects inside a stage: per-document PDFs with derived artifacts. The docs name
  `ocr.html` (canonical copy of `_results.html`), `document.md`, `blocks.json`; the importer
  (`stage_storage.import_extracted_tree`, not downloaded) creates the `structured/` tree
  (`stage_upload.py:372–400`). Exact required file list: UNCONFIRMED.
  Sheet index is built from `ocr.html` (doc). PDFs are read for page count and rendering (doc).
- Versioning: each import creates a new version per document; the previous state is kept as a backup
  folder `_stage_upload_backups/` when `retain_backup` is true (`stage_upload.py:1–10`, `:407–431`,
  `:444–447` returns `backup_path`). Symlink backup folder is refused (`:408–409`).
- Entry rule: folder upload rejects duplicate relative paths (`stage_upload.py:~276–281`, message
  «Дублирующийся путь в папке») and unsafe paths (`:291–296`, «Небезопасный путь файла»).

### 3.2 Definitions in use

- **Session** = one pair of stage folders for one object: `CreateSessionRequest(stage_a_path, stage_b_path)`
  (`B:api/routers/stage_comparison.py:31–34`); `stage_a_path` = stage_1 (OLD), `stage_b_path` = stage_2 (NEW)
  (`F:static/js/app.js:13096` guard in `pcEnsureResultSession`:
  "stage_a_path !== leftPath" guard). Find-or-create: `GET /objects/{id}/session` (`:439`).
- **Pair** = one (left_pdf, right_pdf) of a session, with `composition_completeness`
  (`CreatePairRequest`, `:36–40`). Identity is `pair_id` (server id). Pair key in UI: `row.left.pdf_path` +
  `row.right.pdf_path` (`app.js:14800–14805`, `scRowCatalogEntry` `app.js:13028`).
- **Document group** = one OLD document with several NEW documents (typical: РД split by building or
  корпус). The NEW documents are merged into one assembly (`project_assemblies`) attached to stage_2 and
  compared with the OLD document as a normal 1:1 pair (`document_groups.py:1–16`). Registry:
  `projects_v2/objects/<object>/comparison/document_groups.json` (`document_groups.py:1–16`).
  Member rules: `add_members(left_document_code, member_codes)` max 32 members per request
  (`stage_comparison.py:42–45`); groups with a single member are dropped (`document_groups.py:301` `_drop_small_groups`).
- **Sheet link (sheet pair)** = `{left_pages: [int], right_pages: [int], source, confidence, reason}` inside
  `sheet_links.json`; `unlinked_left_pages` = explicit "no pair" decision (router `:62–74`, doc «Хранение»).
- **Document pair** (OLD↔NEW PDFs) is what the batch queue and the catalog key on (`ProductionBatchPair`
  `:580–586` = `left_pdf`, `right_pdf`, `label`).

### 3.3 Pairing of stage П (OLD) with stage РД (NEW): many-to-many

- Document level: the engineer orders rows (`left_order`, `right_order`, `document-pairing` `:504–518`),
  or accepts the suggestion (`document-pairing/suggest`, UNCONFIRMED algorithm, `document_matching.py` not downloaded).
  One OLD document can map to many NEW documents only through a document group (above).
- Sheet level (doc, `DOCUMENT_COMPARISON_CURRENT_STATE.md` «Карта листов»): automatic pass first looks for an
  unambiguous `тип + корпус + этаж`, `тип + корпус + кровля`, or `тип + уровень` (underground);
  then a scale `корпус 4 / этаж 4 / уровень 3 / тип 2 / Sheet 1 / порядок 1`. A conflict in корпус,
  этаж or тип cannot be overridden by a matching Sheet number or order. Many-to-many is allowed
  (`left_pages` and `right_pages` are always arrays; "uniqueness-гейтов нет").
  Code: `sheet_matching.py` (`_candidate` `:456`, `_semantic_assignments` `:375`, `_sheet_sequence_alignments` `:643`,
  `match_sheet_indexes` `:719`). Confidence labels: `high` → «Высокая»; `manual` → «Ручная»; `source=auto_repair`
  → «Исправлено автоматически»; otherwise «Проверить» (`app.js:18468–18480`).
- Text-level pairing inside an accepted link (doc, Stage 2): exact canonical match within the accepted link
  including many-to-many; repeated phrases only with compatible type and relative position.
- Repairs: `sheet_link_repair.py` / `content_sheet_link_repair.py` (not downloaded) may swap or fix links
  once per run (doc, Stage 5 precheck `PAIR_OK` / `PAIR_REVIEW_REQUIRED`); each repair stored with
  before/after snapshots in `sheet_link_repairs.json` (doc).

---

## 4. Outputs

### 4.1 Change records (V3 `ProjectChange` / envelope)

- Envelope schema `project-change-view/1` with `object_id`, `items`, `origin` (`RESEARCH` / `PRODUCTION`),
  `mode` (`BACKEND_PREVIEW` / other), `decision_mode`, `capabilities.decisions` (`project_change_preview.py:83`,
  `project-change-view.js:86–100`, `app.js:12977–12985`). Unavailable object → `availability: UNAVAILABLE`, `items: []`
  (`project_change_preview.py:86–88`).
- Item fields used by the UI (`project-change-view.js:100–172`): `id`, `display_id`, `summary_ru`, `old_state`,
  `new_state`, `status`, `importance` (`HIGH` etc.), `change_type` (`TYPES` key), `cipher`, `discipline`,
  `engineering_system`, `evidence[]` (each with `source_type` TEXT/TABLE/GRAPHIC, `side` OLD/NEW, `pair_id`,
  `page`, `document.pdf_path`, `document.version`), `conflicts[]` (`resolved`, `values[]`), `pair_ids[]`,
  `expert_review_available`, `expert_review`, `expert_review_run_id`, `source_run_id`, `projectchange_id`,
  `decision_key`, `binding_signature`, `candidate_version` (`projectchange_v3` for expert items).
- Status computation (`project-change-view.js:105–107`): expert `accepted` → `CONFIRMED`, `rejected` → `REJECTED`;
  open conflict → `CONFLICT`; otherwise decision or `REVIEW` for non-production origins.
- The V3 result JSON (`projectchange_v3_final/` schema prefix, `catalog.py:39`) carries `projectchanges`
  (list), `provenance` (`engine`, `model`, `reasoning`), `source_manifest` (`old_pdf_sha256`,
  `new_pdf_sha256`), `quality.source_verification_pending` (`catalog.py:245–327`).

Classes: the requested classes «PROJECT_CHANGE / SERVICE_STRUCTURE / REVIEW» belong to the **doc's Stage 5**
(`project_change_summary.py`, `DOCUMENT_COMPARISON_CURRENT_STATE.md` «Этап 5»), with an atomic
`evidence_id` per CHANGED / REMOVED / ADDED / UNCERTAIN item. In the LIVE V3 envelope the class is not a
field; the UI shows status and change type instead (UNCONFIRMED whether V3 maps to the same classes).
Let me state explicitly: `grep` for `SERVICE_STRUCTURE` in downloaded frontend files: 0 hits in LIVE
code; in backend only `project_change_summary.py` (downloaded). So the Stage 5 class set is documented,
the V3 class set is UNCONFIRMED.

High-level changes (Stage 5.3, `high_level_project_changes.json`, doc «Этап 5.3»): sections
`high_level_changes`, `detail_level_increased`, `material_review`, `non_material_review` (collapsed),
`service_structure_summary`; each with full provenance. UI for it is DEAD (block `6502–7825`).

### 4.2 Expert confirmation flow (LIVE)

- Toggle «Экспертная оценка» (`project-change-ui.js:186–188`) shows per row «Принято» / «Не принято»
  (`project-change-ui.js:258–262`, `aria-label` «Принято: <id>» / «Не принято: <id>», titles «Принято», «Не принято»).
  A rejection requires a reason textarea (`project-change-ui.js:263–`, placeholder «Причина решения (необязательно)» in DEAD code;
  LIVE expert textarea `.pc-expert-reason`, validation in `project-change-ui.js:83`: «Укажите причину каждого отказа.»).
- Save: «Сохранить решения» → POST `/objects/{id}/project-change-expert-review` with `updates` (`project-change-ui.js:103–125`).
  Success message «Решения сохранены» (`:122`). Error: server `detail` or «Не удалось сохранить решения. Повторите попытку.»
  Conflict 409 means revision mismatch (`expected_revision`).
- Non-expert items (no `expert_review_available`): «Подтвердить», «Не изменение», «Не могу определить», «Проблема»
  (`project-change-ui.js:333–338`), see §0.7 for the 403 stub.

### 4.3 «Подтверждено изменений: N» — what it counts

- `report(changes) = changes.filter(c => c.status === 'CONFIRMED' && no unresolved conflict)`
  (`F:static/js/project-change-view.js:185`). In the report tab `all = V.report(props.changes)`
  (`project-change-ui.js:67–68`), so N = number of items whose status is `CONFIRMED`.
- `CONFIRMED` comes from an accepted expert review (`project-change-view.js:106`) or from a local/persisted
  decision of «Подтвердить» (`applyDecision`, `project-change-view.js:173–177`, which refuses to confirm with an open conflict).
- Items with `REJECTED` or still `REVIEW` are not counted. Items with unresolved conflicts are not counted even if `CONFIRMED`.

### 4.4 Consolidator («Итоговые карточки») — report and exports (LIVE when present)

- Shown on tabs 3 and 4 when `GET …/consolidated` returns a `projectchange-consolidations/1` entry
  (`project-change-consolidation.js:517–519`; `F:index.html:6492–6495`). Title «Итоговые карточки»
  (`project-change-consolidation.js:571`), aria-label «Итоговые карточки ...» (`:569–570`), selector «Консолидация» (`:576`).
- Report group `aria-label="Отчёт Excel"` (`project-change-consolidation.js:579`):
  - «Классический отчёт» (`:580–581`, `download('zip')` → `report.zip`, title: "Excel с готовыми результатами + папки «Было» и «Стало» с PDF и MD …, без запуска модели").
  - «Отчёт с ИИ-разбором» (`:582–584`, title «Разбор по корзинам моделью Claude Opus 5.5, затем отчёт»,
    busy text «ИИ-разбор выполняется…», ≈30–40 min note `:598`) → POST `it-analysis/model-run`.
  - «Остановить» (`:585`), «Пересчитать моделью» (`:586–587`), «Загрузить разбор» (xlsx «Карточки ИТ», `:588–591`).
  - Status texts: «Модель разбирает карточки: пачка N из M …» (`:592–594`), «Разбор моделью» / «Разбор инженера»
    (`:595–596`), «пустой шаблон» link to `report.xlsx` (`:598`).
- Download link: `download('xlsx')` → `report.xlsx` (`project-change-consolidation.js:420–432`), file name
  `<code>_ИТ_четыре_корзины.xlsx` or `…_шаблон.xlsx` (`stage_comparison.py:866–867`).
- Consolidator table: columns include «Источник», «Страница по PDF», «Было (ПД)», «Стало (РД)» (`:658`, `:698`);
  cards with «Исходные карточки расходятся» for member disagreement (`:681`).

### 4.5 Final report contents and export formats

- LIVE report (tab 4) = the list in §1.7: ID, Изменение, Было, Стало, Источник, Статус, plus expert columns when
  enabled, and grouping chips. No export format is active in the LIVE list (disabled buttons).
- Active exports, LIVE: Excel (`report.xlsx`), zip (`report.zip`: Excel + «Было»/«Стало» folders with PDF and MD)
  — only for an existing Consolidator result (`stage_comparison.py:855–897`, `project-change-consolidation.js:580–598`).
- Other export surfaces in code: none found for PDF or HTML in the downloaded files. The Markdown report
  `version-comparison-md-report.js` belongs to another module (version comparison), not stage comparison.
- Legacy final report (DEAD): columns «ID», «Объект», «Изменение», «Было», «Стало», «Источник», «Решение эксперта»
  (`F:index.html:7849–7858`, empty state «Подтверждённых изменений пока нет» `7888`).
- Preliminary report (V3 / production) endpoint `…/production/preliminary-report` (router `:1087–1098`); UI DEAD (`F:index.html:6550–6716`).

---

## 5. Graphic comparison (G1) — Mode 1 / Mode 2

Docs: `F:docs/GRAPHIC_COMPARISON_G1.md` (249 lines). Code: `B:services/stage_comparison/graphic_comparison/`
(package, not downloaded) and router `B:api/routers/stage_comparison.py:1267–1300`.

- Input (doc `:9–30`): only block ids `left_block_ids`, `right_block_ids`; resolved from `02_work/blocks.json`
  of the pair's documents; inline bbox / polygon / page / URL rejected; unknown or repeated id stops the request.
  Only `1 ↔ 1` executes; other cardinality → `MODE_2_REQUIRED`.
- Mode 1 (doc `:113–149`): registration with translation, uniform scale and small rigid rotation (no affine,
  no non-uniform scale); local vector diff in the right frame with a physical grid; ledger
  `GraphicChangeLedger` (doc `:150–183`, schema files `graphic_change_ledger*.schema.json` in the package).
  Quality figures in the doc: pair-level TP=9, FP=0, FN=0, TN=31; minimal extraction precision 0.9808
  over 40 admitted pairs (doc `:216–222`). Measurement method is in the doc; not re-verified.
- Mode 2 (structural, `direct_page_mode2.schema.json` present): NOT implemented; `MODE_2_REQUIRED` is
  stored, parser not called (`GRAPHIC_COMPARISON_G1.md:4–7`, `:242`: "Mode 2 не реализован и не симулируется").
- Model use: none in G1 (doc `DOCUMENT_COMPARISON_CURRENT_STATE.md` «Границы clean-slate»: "G1 не вызывает
  модель и раздел не создаёт findings").
- GET default when not run: `{schema_version: "graphic-change-ledger.v1", status: "not_started", pair_id}` (router `:1300–1302`).

LIVE state:
- No UI call to `/graphic-comparison` (grep of `F:index.html` and `F:static/js/**` = 0 hits).
- GRAPHIC is a *source type* on V3 evidence (`project-change-view.js:8`, `project-change-consolidation.js:72`,
  `:153`, marker classes `pcc-mark--graphic` at `:282`) produced by the V3 pipeline, not by G1.
- Graphic reason codes in `F:static/js/stage-comparison-review.js:16–48` (e.g. `NO_GRAPHIC_COMPARISON`,
  `GRAPHIC_ROUTE_UNAVAILABLE`, `LOW_MATCHED_GRAPHIC_COVERAGE`) are used by the legacy review helper and
  are not rendered by LIVE tabs (UNCONFIRMED: helper used only from DEAD branches; `SC_PRODUCTION_REVIEW`
  is also used for LIVE polling, so partial use is certain).
- Doc's «Mode 2» appears in the UI only as an unused label; no LIVE control.

---

## 6. Wired vs. backend-only vs. older docs

How to read the status: "LIVE" = referenced from `F:index.html` (or from a LIVE JS path that the template calls);
"DEAD-branch" = template exists but guarded by `!pcUiEnabled`; "backend-only" = router endpoint with no
frontend caller in the downloaded files; "docs-only" = mentioned in docs and not found in code.

| Feature | Status | Evidence |
|---|---|---|
| Four tabs, Загрузка проектов dialog | LIVE | `F:index.html:5461–5478`, `7999–8134` |
| Document pairing auto/manual, drag-reorder | LIVE | `F:index.html:5801–6034`; `app.js:14341`, `14642`, `14800` |
| Document groups (build, add, remove, rebuild) | LIVE | `F:index.html:5916–6026`; `app.js:14462–14580` |
| Catalog of saved results (LIVE_RUN / SEALED_SNAPSHOT) | LIVE | `F:index.html:5538–5544`; `F:static/js/project-comparison-catalog.js` |
| Sheet map (suggestions, selects, filter, accept all) | LIVE | `F:index.html:6085–6225` |
| Sheet-link repair audit + undo | LIVE | `F:index.html:6113–6155`; `app.js:18482–18494` |
| Viewer (paged + continuous, zoom, search, slot controls, thumbs) | LIVE | `F:index.html:6261–6470`, `6272–6300` |
| Viewer sync checkbox «Синхронный вид» | docs-only (state exists) | `app.js:13448`, no template control |
| Viewer block mode (`semantic-block-comparison`) | LIVE (blocks API UNCONFIRMED) | `F:index.html:6234–6247`, `6465–6466`; `F:static/js/stage-block-mapping.js:3421` |
| `semantic-block-workspace` component | registered, unused in template | `F:static/js/stage-block-mapping.js:2800`, `index.html` 0 hits |
| 7-stage pipeline bar (V3) | LIVE | `F:index.html:5480–5531`; `F:static/js/project-change-view.js:257–265` |
| Old 7-stage production bar (`sc-production-pipeline`) | DEAD unless `?pcDebug=1` | `F:index.html:5560–5795` |
| Run / quality banners | LIVE | `F:index.html:6471–6490` |
| Batch queue (select rows, run, stop, status) | LIVE | `F:index.html:5811–5821`; `app.js:17940–17995`, `17924` |
| Launch dialog with FAST / STANDARD / SUBJECTS and model / parallelism | LIVE | `F:index.html:7947–7995`; `app.js:12909–12913` |
| Resume dialog «Досчитать из сохранённого» | LIVE | `F:index.html:7898–7946` |
| Change list «Изменения проекта» + expert review | LIVE | `F:index.html:6496–6501`; `project-change-ui.js:6–`, `83–125` |
| Per-item «Подтвердить…» buttons via `/decisions` | LIVE UI, backend 403 stub | `project-change-ui.js:333–338`; `project_change_preview.py:108–110` |
| Report «Итоговый журнал изменений» | LIVE | `project-change-ui.js:185` |
| Report export Excel/PDF/HTML (header buttons) | LIVE but disabled | `project-change-ui.js:188–193` |
| Report grouping chips | LIVE (not a table grouping) | `project-change-ui.js:225–230` |
| Consolidator «Итоговые карточки», zip, xlsx, AI IT-analysis | LIVE when a consolidation exists | `project-change-consolidation.js:569–598`; `stage_comparison.py:796–953` |
| Stage 2 «Сравнить текст» + Stage 3 differences + Stage 4 AI review + Stage 5 summary | DEAD / orphaned (`scRunTextComparison` exported, not referenced) | `app.js:18197–18320`, `21214`; no template caller |
| Legacy diff table «Расхождения», legacy final report, legacy human review, preliminary report, questions | DEAD (`!pcUiEnabled`) | `F:index.html:6502–7895` |
| Legacy TEXT results block «Legacy-результаты TEXT» | DEAD | `F:index.html:7376–7381` (inside `6502–7825`) |
| High-level changes 5.3 UI | DEAD | `F:index.html:7400–7620` (inside `6502–7825`) |
| G1 graphic comparison | backend-only | `B:api/routers/stage_comparison.py:1267–1300`; no UI callers |
| G1 Mode 2 (structural) | docs-only (`MODE_2_REQUIRED` status) | `docs/GRAPHIC_COMPARISON_G1.md:4–7`, `242` |
| Stage 4 / Stage 5 AI (gpt-5.6-luna) | backend-only (endpoints) | `text_ai_reviewer.py:25`, `project_change_summary.py:21`; routes `:1329–1384` |
| Production V3 engine (astra / opus55 profiles) | LIVE (run, batch, cancel, resume) | `F:index.html:5489`, `7925–7994`; `stage_comparison.py:537–716` |
| Subjects comparison mode «По инженерным предметам» | LIVE, labelled experimental | `F:index.html:5522`, `7993`; `app.js:12911` |
| Human-review orchestrator (`human_review_orchestrator.py` 66 KB), human contour, prelink, function lineage, AI analyst v2/v3/v31 | backend/docs; UI referenced only in DEAD code or `stage-block-mapping.js` (`prelink`) | `F:index.html` 0 hits for `human_contour`, `function_lineage`, `ai_v31`; `prelink` used in `stage-block-mapping.js` and `app.js` |
| Old docs: `stage_comparison_ai_analyst_v2.md`, `..._v3_20260901.md`, `..._v31_question_closure_20260901.md`, `stage_comparison_function_lineage_shadow.md`, `stage_comparison_human_contour_v1.md`, `stage_comparison_human_presentation_v1.md`, `stage_comparison_recognition_coverage.md`, `stage_comparison_standard_coverage.md`, `stage_comparison_entity_matcher_v3.md`, `stage_comparison_sheet_matcher_v4.md` | older design docs; no LIVE caller found in downloaded frontend | grep of `F:index.html` and `F:static/js` for their keywords |
| `stage_comparison_load_table_linking.md` (351 lines) | UNCONFIRMED relevance | not read |

Doc vs. UI drift to note:
- Doc «Вкладка «Связь блоков» сохраняет прежнее имя» (`DOCUMENT_COMPARISON_CURRENT_STATE.md`, «Интерфейс») — the LIVE tab is «2. Сопоставление листов» (`F:index.html:5464`), but a stale string still says «Связь блоков» (`app.js:18192`).
- Doc buttons «Оставить», «Изменить», «+ Добавить лист РД», «Удалить связь» (`DOCUMENT_COMPARISON_CURRENT_STATE.md`, «Интерфейс») do not exist in the LIVE sheet map (grep of `F:index.html`: 0 hits; the strings occur only in `F:static/js/stage-block-mapping.js:2639–2706` for block-level links).
- Doc button «Миниатюры» (`DOCUMENT_COMPARISON_CURRENT_STATE.md`, «Панель миниатюр листов») is an icon-toggle in LIVE (`F:index.html:6263–6270`); DEAD code has the text version.
- Doc «Сравнить текст» (Stage 2 trigger) — no LIVE button (see §0.2).

---

## 7. Size census (approximate lines; counted from downloaded files)

UI template (`F:index.html`):
- Whole `stage-comparison` block `5456–8150`: 2 695 lines.
  - LIVE regions: `5456–6501` (1 046 lines, incl. the pc pipeline bar `5480–5531`, the old pipeline bar `5560–5795`
    which is DEAD unless `?pcDebug=1`, and the tab 1 and 2 markup) minus the DEAD sub-blocks below.
  - Old pipeline bar `5560–5795`: 236 lines, DEAD unless `?pcDebug=1`.
  - DEAD legacy diff/report/review block `6502–7825`: 1 324 lines.
  - DEAD legacy final report `7827–7895`: 69 lines.
  - Dialogs (LIVE): resume `7898–7946` (49), launch `7947–7995` (49), upload dialog `7999–8134` (136), tray `8138–8150` (13).
  - Pair workbench tab 1 `5796–6035` (240); viewer tab 2 `6036–6501` (466, includes sheet map `6085–6225`).
  - Live legacy-named but mounted by LIVE shell: `project-change-list` / `project-change-consolidation` tags `6492–6501` (10).

Frontend JS:
- `F:static/js/app.js` 21 300 lines total. Stage-comparison state and logic: `12759–21300` (8 542 lines, interleaved
  with unrelated features; includes `pc*` shell `12959–13360`, upload `15089–15420`, pairing `14300–14660`,
  production run/poll `15740–16690`, batch and launch `17840–18200`, text legacy `18197–18330`, sheet map `18400–18930`,
  viewer `19000–19560`, page URLs `19320–19345`).
- `F:static/js/stage-comparison-review.js` 3 695 lines: review/production helper module (`SC_PRODUCTION_REVIEW`, `app.js:12875`);
  LIVE only for polling directives (`app.js:15809–15872`) and reason-code labels; most of it serves DEAD UI.
- `F:static/js/stage-comparison-differences.js` 129 lines: legacy diff row builder (`app.js:14069–14200`, DEAD).
- `F:static/js/stage-comparison-batch.js` 89 lines: batch item labels and summary (LIVE, `app.js:12919`).
- `F:static/js/project-change-view.js` 407 lines: envelope adapter, statuses, pipeline stages (LIVE).
- `F:static/js/project-change-ui.js` 378 lines: change list and report (LIVE, `app.js:21295`).
- `F:static/js/project-change-consolidation.js` 724 lines: Consolidator (LIVE when results exist, `app.js:21296`).
- `F:static/js/project-comparison-catalog.js` 164 lines: catalog table (LIVE, `app.js:21297`).
- `F:static/js/stage-block-mapping.js` 4 033 lines: sheet/block store, sbm components (LIVE: `sbm-*`, `semantic-block-comparison`; `app.js:21298`).

Backend:
- `B:api/routers/stage_comparison.py` 1 592 lines (router: upload, sessions, pairs, production, sheet, text, graphic, page render, consolidator, expert review).
- `B:api/routers/project_change_preview.py` 164 lines (envelope, decisions stub, evidence crops, viewer endpoints).
- `B:api/routers/project_comparison_catalog.py` 25 lines.
- `B:services/project_change_catalog/catalog.py` 640 lines (LIVE_RUN / SEALED_SNAPSHOT discovery, read-only).
- `B:services/stage_comparison/stage_upload.py` 523 lines (ZIP / folder import).
- `B:services/stage_comparison/document_groups.py` 402 lines.
- `B:services/stage_comparison/sheet_matching.py` 853 lines (deterministic).
- `B:services/stage_comparison/text_differences.py` 654 lines (deterministic, Stage 3).
- `B:services/stage_comparison/text_ai_reviewer.py` 929 lines (Stage 4 contract, model call elsewhere).
- `B:services/stage_comparison/project_change_summary.py` 716 lines (Stage 5 contract, model call elsewhere).
- Not downloaded, size from tree: `store.py` 119 KB, `production_orchestrator.py` 387 KB, `project_change_v3/engine.py` 128 KB,
  `project_change_v3/contracts.py` 17 KB, `high_level_project_changes.py` 47 KB, `text_comparison.py` 71 KB,
  `review_queue.py` 100 KB, `human_review_orchestrator.py` 66 KB, `stage_block_mapping/` package.

Per step (LIVE only, rough):
- Upload / object and session selection: UI ~400 lines (`app.js` upload and session, 14300–15420 + dialog 136); backend
  ~250 lines (`stage_comparison.py` 283–413 + `stage_upload.py` 523).
- Pairing and document groups: UI ~250 lines (template 5801–6034 + `app.js` 14300–14660); backend ~500 lines (`document_groups.py` 402 + router 322–526).
- Sheet map and viewer: UI ~800 lines (template 6036–6470 + `app.js` 18400–19560 + `stage-block-mapping.js` 4033, of which sheet map parts ~1 000); backend ~1 000 lines (`sheet_matching.py` 853 + router 1173–1260, 1426–1561).
- Production V3 run, batch, state: UI ~700 lines (template 5480–5531, 7898–7995; `app.js` 15740–18200); backend ~1 500 lines visible here (router 537–727) plus the V3 engine (not downloaded, ≈ 130 KB + 387 KB orchestrator).
- Changes, expert review, report: UI ~900 lines (`project-change-ui.js` 378, `project-change-view.js` 407, template 6492–6501, `app.js` 12959–13360 ≈ 400); backend ~300 (`project_change_preview.py` 164 + router 771–793).
- Consolidator and exports: UI ~724 lines (`project-change-consolidation.js`); backend ~200 (router 796–953 + `report_xlsx`, `it_analysis_llm` not downloaded).
- Legacy text stages 2–5 (DEAD in LIVE UI but reachable via API): UI ~1 400 lines (DEAD template 6502–7825 + `app.js` 18197–18330 + `stage-comparison-differences.js` 129); backend ~2 300 lines (`text_differences.py` 654, `text_ai_reviewer.py` 929, `project_change_summary.py` 716, router 1232–1410; `text_comparison.py` 71 KB and `text_fact_producer.py` 63 KB not downloaded).
- Graphic G1: backend ~ 250 lines visible (router 1267–1302) plus `graphic_comparison/` package (not downloaded, ~ 200 KB); UI 0.

Method notes for the census: line counts for the downloaded files are exact (`wc -l`); template ranges are
from `awk` over the downloaded `index.html`; `app.js` sub-ranges are estimates from grep anchors
(e.g. `scRunProductionComparison` at `app.js:16606`); the per-step totals are rounded and mix UI and backend.

---

## 8. UNCONFIRMED list (not verifiable from the downloaded files)

- Whether `project_change_preview` router is mounted in `main.py` (affects §0.7 decisions 403).
- V3 engine: which model each profile calls, whether images are sent, and the exact run artifact names
  (`production_orchestrator.py`, `project_change_v3/provider.py`, `contracts.py` not downloaded).
  `CLAUDE.md:277–279` claims production uses `codex/gpt-6-astra`; the live catalog shows `gpt-6-astra`
  (per the brief); the code constants `gpt-5.6-luna` apply to Stage 4/5 only.
- Document-pairing suggestion algorithm and whether it calls a model (`document_matching.py` not downloaded).
- Sheet-link repair algorithm (`sheet_link_repair.py`, `content_sheet_link_repair.py` not downloaded).
- Block-mapping endpoints used by `F:static/js/stage-block-mapping.js:236–276` (`/api/stage-comparison/sessions/.../block-mapping/...`):
  not in `B:api/routers/stage_comparison.py`; the router `B:api/routers/stage_block_mapping.py` exists in the tree but was not downloaded.
- Expert review persistence (`project_change_v3/expert_review.py`, not downloaded) and the exact revision rules.
- Whether any LIVE V3 result yields `expert_review_available: false` with a live `/decisions` POST (so the 403 stub would be hit).
- Exact Ctrl/Shift and drag rules in tab 1 for the LIVE pair board (the design doc describes them for thumbnails).
- Exact keyboard bindings for the viewer (Ctrl+wheel, double-click zoom) beyond the code in `app.js` near `scZoomBy`.
- `stage_comparison_load_table_linking.md`, `..._sheet_identity.md`, `..._parameter_diff.md`, `..._document_consistency.md`
  were not read; relevance to LIVE UI is unconfirmed.

---

## 9. Verification commands used (reproducible, read-only)

- `grep -n` over `F:index.html`, `F:static/js/*.js`, `B:api/routers/*.py` for labels and endpoints.
- `awk 'NR>=A && NR<=B'` for template ranges; `wc -l` for census.
- `curl -sS --fail` only for the 12 extra files listed at the top; nothing executed.
