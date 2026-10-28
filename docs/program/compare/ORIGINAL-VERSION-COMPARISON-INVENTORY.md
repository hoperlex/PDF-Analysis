# Inventory: «Сравнение версий» (version comparison), PDF-proverka at commit 23f379fd

Scope: read-only inventory of the version-comparison module, built from the downloaded
source tree (ROOT = /tmp/claude-0/-root-projects-PDF-Analysis/754ae11c-a0de-41ac-9ac2-1b49a23f1a22/scratchpad/orig-src/files).
All code citations are repo-relative (`frontend/...`, `backend/...`, `docs/...`) under that ROOT.
Russian UI labels are quoted verbatim in «». Line numbers were taken from the downloaded files;
where a claim rests on a file I did not read, it is marked UNCONFIRMED.

Files read in full or by range: `frontend/index.html` (grep only), the 8 `version-comparison*.js` UI files,
3 CSS files (sizes only), `backend/app/api/routers/version_comparison*.py` (3 files), and these services:
`version_comparison/{jobs,engine,lineage,series,overview,store,batches,settings,status,recovery,tiles,textdiff,report,resolve,spec,stamp,profile,registration,service,paths,specification_compare,specification_run,specification_view,work_queue,worker}.py`
and `version_comparison_ai/{jobs,sheet_match,stage_queue,executor,settings,packet,prompt,whole_specifications,summary}.py`,
`version_comparison_ai/sheet_changes/{series_ai,series_summary,run,single,validate,view,report,schema,collect}.py` (docstrings and key defs),
`version_comparison_ai/md_report/{runner,stages,pdf,client,settings}.py` (docstrings and key defs).
Docs read: `docs/version_comparison_{plan,ai_plan,sheet_changes_plan,matching_upgrade_plan,md_report,worker,em2_verification}.md` (headings and status lines),
`docs/whole_specification_comparison.md` (headings, sequence section).
NOT read: `version_comparison_ai/{records,verify,view,navigation,importer,context,geometry,ids,images,report,schema,validate}.py`
(listed by name only), most `specification_*.py` in `version_comparison/` other than those named above, `permit.py`, `pdfio.py`,
`separation.py`, `blocks.py`, `block_alignment.py`, `parts.py`, `resources.py`, `md_report/client_edit.py`. Tests were not read.

---

## 1. User workflow as the user sees it

### 1.1 Entry, page frame, global strips

- Menu item: `frontend/index.html:137`, `title="Наложение листов разных версий проекта"`, shown when `canView('version_comparison')`.
  Route `/version-comparison`: `frontend/static/js/app.js:16,30`. Mount: `frontend/index.html:5452-5453` (`<version-comparison-page>`).
- Backend gate: every `/api/version-comparison` handler goes through `_guard`, which returns 404 «Раздел «Сравнение версий» выключен»
  when `settings.enabled()` is false (`backend/app/api/routers/version_comparison.py:30-33`).
- Object: the object comes from the platform header (`portalObjectId` prop); the section has no object picker of its own
  (`frontend/static/js/version-comparison.js:629`, `usePortalObject` at `:718-724`).
- Default tab: `view` = `'projects'` unless `localStorage['version-comparison:view']` says otherwise (`version-comparison.js:641`).
- Page head: title «Сравнение версий» (`version-comparison.js:68`); button «⇪ Загрузить проект со всеми версиями»
  (`:72`, `v-if="canUpload"`, disabled when no object; tooltip starts «Загрузить PDF: один проект со всеми версиями…»).
  Mounts the batch uploader `<vc-batch-upload>` (`:75`).
- AI queue strip (`:76-79`): shown when `aiQueue.current` or waiting; text «Очередь «ИИ-описание изменений»:» + `aiQueueText()` (`:949`).
- Error bar (`:80`): click clears the message.
- Empty states (`:81-84`): «Выберите объект в шапке платформы (слева вверху) — раздел покажет его проекты и версии.»;
  «Загрузка каталога…»; «В объекте ещё нет версий. Нажмите «Загрузить проект со всеми версиями» и выберите папку с PDF.»
  (viewer text when not `canOperate`: «В объекте ещё нет версий: администратор их пока не загрузил.»).
- Tabs (`:85-88`): «Проекты и этапы» + project count (`title`: «Все проекты объекта и этапы их проверки одной таблицей»);
  «Сравнение листов» + selected project title, disabled when no project selected (`title`: «Матрица листов открытого проекта…»).

### 1.2 Page «Проекты и этапы» (`frontend/static/js/version-comparison-projects.js`)

Data: one GET `/api/version-comparison/objects/{id}/overview` per refresh (`projects.js:293`, read-only, starts nothing).
Refresh timer: 5 s while anything is running or uploading, else 30 s (`projects.js:296-300`); the «Обновить» button (`:124`) calls `load()`.
Last refresh shown as «обновлено HH:MM:SS» (`:123`).

**Tiles (`:98-105`, filters from `FILTERS` at `:18-24`):**
«Все» (all in scope), «Ждут действия» (group `act`), «Идут» (`run`), «Ошибки» (`bad`), «Готовы» (`ok`), and an info tile
«N версий · M переходов» (`totals`, `:103`). Group mapping: `next.tone` `run`→Идут, `bad`→Ошибки, `ok|muted`→Готовы, else Ждут действия (`projects.js:318-319`).
Tile counts respect the search and the mark filter; tiles themselves are the state filter.

**Toolbar (`:107-124`):**
- «Поиск по шифру…» (`:108`): case-insensitive substring of `p.title` (`projects.js:310-313`).
- «Марка» select, options «все» + each mark with count (`:109`). Mark = letters at the tail of the cipher after the last `-`
  (`projects.js:29-34`, e.g. «133/23-ГК-ЭМ2» → «ЭМ»).
- «Порядок» select (`:113-118`): «по шифру», «сначала требующие действия», «по последней загрузке», «по числу версий»
  (plus a custom entry when the column sort is non-preset).
- Column sort: header buttons with ▲/▼ (`:167-172`); tooltips from `SORT_TEXT` (`projects.js:269`).

**Pending uploads strip (`:126-132`):** «В загрузке, ещё не в списке проектов:» with each batch item’s code/label, files count, error.

**Queue strip «Очередь запуска» (`:136-151`):** shown when the stage queue has items (admin only; `loadQueue` returns early for viewers, `:421-425`).
- State label `QSTATE` (`:~402`): running «идёт», paused «на паузе», failed «ошибка — процесс остановлен», done «выполнена», idle «пусто».
- Counts: «готово N», «идёт N», «на паузе N», «ждут N», «из M» (total items), «пропущено N», «ошибок N» (`:142`).
- Buttons: «⏸ Пауза» (`:143`, POST `stage-queue/pause`), «▶ Продолжить очередь» (`:144`, POST `stage-queue/resume`, shown when paused/failed),
  «Очистить» (`:146`, POST `stage-queue/clear`, title «Убрать ждущие этапы и историю; идущий этап продолжит работу»),
  «Список» / «Скрыть список» (`:147`). List items show `QITEM`: ждёт, идёт, пауза, готово, ошибка, пропуск; ✕ removes a pending item (POST `stage-queue/remove`).

**Selection bar (`:157-163`):** appears when cells are ticked: «Выбрано: N» + per-stage counts,
«▶ Запустить выбранные по очереди» (`runSelected`, `:398-419`: builds a confirm dialog with the first 8 items, then POST `stage-queue`),
«Снять выбор».

**Table (`:165-213`). Columns, left to right:**

| # | Header (verbatim) | Content |
|---|---|---|
| 1 | «Проект · следующий шаг» (`:170`) | cipher (`p.title`); next-step chip `p.next.label`; «Сводка изменений (MD)» button when `canDownload && p.stages.report.summary_md` (`:189`, `downloadMd` `:608-616` opens `…/series/{sid}/ai-sheet-changes/summary.md`) |
| 2 | «Версии» (`:171`) | version count + «· N стр.» (page count of last version); last version label, tooltip with first and last labels |
| 3 | «1 Загрузка» (`STAGES[0]` at `projects.js:6-16`; header `:172-180`) | upload status |
| 4 | «2 Разбор версий» | profile status (per-version PDF profiling) |
| 5 | «3 Сопоставление листов» | sheet matrix (lineage) status |
| 6 | «4 ИИ-проверка сомнительных пар» | model check of doubtful pairs («Луна») |
| 7 | «5 Сравнение соседних» | transition runs (V1→V2 …) |
| 8 | «6 ИИ-описание изменений» | AI description of changed sheets, then specifications and the MD summary |
| 9 | «7 Сводка и отчёт» | PDF report based on the MD summary |

Each stage header has a per-column checkbox (`:172-176`, title «Выбрать все строки, где этап «…» можно запустить или продолжить») only for stages in `SELECTABLE` = luna, series, ai, report and only for admins (`:355`, `canOperate`).
Each stage cell: optional row checkbox (`canSelect`, `:376-396`; title «Выбрать для запуска по очереди: …»), or a queue badge (`queuedAt`, `:~358-369`: «очередь: идёт», «очередь: пауза», «в очереди №N»), then the status chip (icon, text, title), a note line, progress bars for running series/AI, then action buttons (`stageActs`, see §2.4).
Row click opens the project’s «Сравнение листов» tab (`open` → `emit('open')` → `openProject`, `version-comparison.js:649-657`; the legend at `projects.js:219-225` says «Щелчок по строке — сравнение листов проекта»).
Legend (`:218-225`): «✓ готово», «! есть что проверить», «⟳ идёт», «○ не запускалось», «✕ ошибка», pause/resume explanation (admins).

**Dialogs (`:229-248`):** one generic confirm modal (`confirmDialog`, `:540-556`) with title, lines, optional consent checkbox
(`CONSENT` = «Подтверждаю передачу материалов исполнителю (Codex на подписке сервера)», `:558`), buttons «Отмена» and the action label.
Action labels seen in code: «Запустить», «Проверить» (luna), «Поставить в очередь» (selection), «Описать заново», «Сформировать», «Сформировать заново», «Пересчитать».
Busy text «Запуск…» (`:247`). For luna, `load()` fetches `/ai-sheet-match` and shows model/effort/parallel and blocks if disabled (`:559-571`).

### 1.3 Stage columns: meaning and visible states

Stage definitions and hints: `projects.js:6-16` (STAGES). Chip text per state: `stageView` (`projects.js:41-94`).

- **1 Загрузка** (`upload`): «загружен» when done (`:45-46`); otherwise the batch item label or «файлов N». Upload is covered in §3.
- **2 Разбор версий** (`profile`): «готов» / «идёт» / «не начат» / «ошибка»; note «ready из total» and «ошибок N» (`:48-52`). Meaning: each PDF version was read page by page (stamp, words, ink mask) — `backend/app/services/version_comparison/profile.py`.
- **3 Сопоставление листов** (`matrix`): «готово», «не сопост. N» (N = unmatched cells), «устарело», «не собрано» (`:54-63`); note «строк N · ✎ M» (rows, manual edits). Meaning: sheet matrix (rows = sheets across versions) built by `lineage.build` (§2.2).
- **4 ИИ-проверка сомнительных пар** (`luna`): «проверено», «не нужна», «не проверялось», «идёт», «пауза», «прервано»; note «вопросов N · пар N · подсказок N · против N» (`:65-71`). Meaning: model answers only for doubtful cells.
- **5 Сравнение соседних** (`series`): «готово», «идёт», «прервано», «ошибка», «не запускалось», «по старому порядку»; note «done из total · с изм. N» (`:73-89`).
- **6 ИИ-описание изменений** (`ai`): «готово», «частично» (partial), «идёт», «в очереди №N», «пауза», «прервано», «не запускалось», «ждёт сравнения», «не нужно» (no content changes) (`:91-104`); note «листов готово N из M · ошибок K · проверить R».
- **7 Сводка и отчёт** (`report`): «PDF готов», «PDF строится», «пауза», «прервано», «ошибка PDF», «есть MD» (`:105-115`).

Tones: `TONE` map (`:15-16`): done/skip→ok, attention/partial/stale/interrupted/paused→warn, running/queued/pausing→run, failed→bad, blocked/na→off.

### 1.4 Page «Сравнение листов» (project matrix) (`frontend/static/js/version-comparison.js`)

Project header (`:93-106`): ▶/▼ caret (click toggles the pair bar and transition summary, `toggleProject` `:1047-1057`), project name «Проект, с которым работаете…», «· версий: N»,
buttons: «Применить сопоставления (N)» and «Отменить правку» (admin, when a draft exists, `:98-99`), «Сводка изменений (MD)» link (`:102`) or disabled button with the title «Сводка станет доступна после описания листов или сравнения полных спецификаций» (`:103`... `:104`),
«Порядок версий» (admin; disabled while a link draft exists; `:104`), «Сформировать PDF-отчёт…» (`:106`, opens `vc-md-report`).

Pair selection (A → B): a «Выберите две разные версии.» hint (`:118`) when no valid pair; per version column two buttons (`:355-360`) that set side A («было», `vc-pick-a`) or B («стало», `vc-pick-b`) via `setSide` (`:1059-1065`). Default pair = the last two versions (`loadCatalog`, `:731-758`).

Transition summary «Сводка переходов» (`:124-158`): one row per adjacent transition A → B with
- progress «переходов готово: done из total», «Отменить» (admin, while queued/running; `cancelSeries`), «Продолжить» (`resumeSeries`);
- columns «Переход A → B», «Ход расчёта», «Листов», «✓», «◐», «●», «⚠», «Состав» (+N / −M), verdict text, «Открыть» (opens that transition as the active A/B pair, `openTransition` `:1031`).
- Verdict strings come from `series.summary()` (see §4.1).
- Note «Сохранённая сводка для прежнего порядка версий.» when the stored series does not match the current order (`seriesMatchesOrder`, `:808`).

AI block «ИИ-описание изменений» (`:159-225`): per transition row with progress («листов готово N из M», «идёт N», state text), columns «Листов», «Изм.», «Вопр.», «Ошибок», «Проверить», «Обращ.», tokens, time.
- «Проверить» button per row opens the review list (`openReview`, `:1012`, sheet viewer in review order).
- Fold ▸/▾ shows sheets: «Проверить» lines (sheets where the AI found no change but comparison left marks) and added/removed single sheets with «Открыть» (`showSingle`, `:987`).
- Buttons per block: «Отменить» (running/paused), «Досчитать» (interrupted/paused), «Убрать из очереди» (queued), «Повторить» for failed sheets (`retryAiFailed` `:922`, POST `ai-sheet-changes/retry-incomplete`, title «Описать заново только листы с ошибкой (например, после отказа провайдера 429)…»).
- Note «Описание каждого листа — в просмотрщике пары, окно «Изменения в листе».» (`:221`).

Specifications block «Полные спецификации (СО)» (`:237-275`): per transition method «полное сравнение» (whole) or «листовой ИИ» (sheet_ai, described in the sheet block), spec sheet counts A/B, coverage «покрыто», positions column «изменено / +добавлено / −удалено / ?неясно» (`:262`), reason text, «Открыть». Header shows state labels from `SPEC_STATE` (`:872-873`: «идёт», «ставится на паузу…», «пауза», «готово», «ошибка», «прервано — можно продолжить»), phases `SPEC_PHASE` (`:874`: «подготовка», «сравнение», «готово»).

MD summary and report block «Сводка MD и отчёт для заказчика» (`:277-333`): report state (`state_label`), stage, progress «группы N из M · проверки N из M» (analyst) or «переходов N из M» (client), usage (calls, tokens), time, «Скачать PDF», «Скачать MD», «Продолжить» (`resumeReport`, `:910-914`). Transition table columns for analyst reports: «Анализ», «Проверка», «Факты» (found / confirmed / contradicted / unconfirmed), «Предупреждения»; for client reports: «Отбор», «Пунктов», «Вопросов» (`UNIT_MARK` `:877-878`: ✓ done, ⟳ running, ✗ failed, · pending).

Sheet matrix (`:347-430`): header «Лист \ версия» with checkbox «только изменения» (`:349`, filters rows to changed ones when a pair run exists). Version column headers show `user_label` or file name and A/B pick buttons.
Row head: `display_title` and a status badge (`vc-badge`, colour class from `statusInfo`, label from `itemLabel`) that opens the sheet comparison (`:370`, title «Открыть сравнение этого листа в паре A → B: наложение, A, B и рядом»).
Cells (`:372-430`):
- matched thumbnail (`vc-thumb`, image from `thumbUrl` → `…/sources/{sha}/pages/{page}/thumb?w=220`, router `version_comparison.py:244`): flags «?» (medium confidence, title «Сопоставлено с невысокой уверенностью»), «▤ группа» (group of sheets from a table), «✎» (manual link), «ИИ» / «ИИ ?» (model link or doubt), «⧉» (duplicate sheet), «скан» (image-only page: text not compared), «◫» / «⇉» (sheet split across versions).
  Click (`clickCell`, `:1220-1250`) opens the viewer for the pair if a done run item exists; otherwise a plain sheet view with explanation:
  «в проекте одна версия — сравнивать не с чем»; «пара … ещё не посчитана — сравниваются только соседние версии …»; «сравнение этого листа ещё не готово»; «у листа нет пары в версии …».
  Drag-and-drop of thumbnails onto cells and the ⤫ button («Отвязать в отдельную строку») create draft manual edits.
- unmatched cell «⁇ не сопоставлен» with «рядом» (side-by-side), reason, model hint «🌙 ИИ: вероятно стр. N», candidates «кандидаты:» with per-candidate «Связать» (`attach`), and «Отметить, что этого листа в версии нет» (`markAbsent`).
- absent cell «∅ нет в версии».
- «Несвязанные страницы» row with draggable thumbnails of unassigned pages (`:412-420`).
- Manual edits are drafts until «Применить сопоставления (N)» (`applyLinks`, `:1349-1376`: POST `links/batch`, then polls matrix while `building`/`profiling`). «Отменить правку» removes the last draft edit (`undoEdit`, `:1394`: POST `links/undo` when already saved). While a draft or save is in progress the table is `inert` (`:347`).
- Legend (`:425-429`): «Выбрано правок: N. Примените сопоставления или нажмите кнопку сравнения после всех правок.»

Matrix states shown (`:107-116`): «Загрузка…», «Разбор версий: готово N из M…», «Сопоставление листов между версиями…», «Не удалось подготовить версии: …», «Сравнение ещё не подготовлено администратором» (viewer, not prepared). Viewer (not `canOperate`) reads `matrix-view` and cannot edit (`:771`).

### 1.5 Sheet viewer (`version-comparison-viewer.js`, `version-comparison-zoom.js`)

Opened from a matrix cell or badge, from the transition «Открыть», the AI review list, or a single-sheet link (`openViewer` `version-comparison.js:1426`, `vc-viewer` mount `:569`).
- Header: title, «✕ Закрыть» (`viewer.js:54-56`), navigation «‹ лист» / «лист ›» (`:52-55`, `gotoSheet` `:581-584`) across done compare items of the run in order (`navigationItems`).
- Channel strip (`:62-73`): «Проверено:» (checked channels with diff counts), «Не проверено:» (unchecked channels with reason), «причины: …» (reasons, `reasonText`). Channel labels: `CHANNEL_LABELS` in `version-comparison.js:19-21`.
- Scan note (`:58-61`) for image-only pages: «изображение без текста: надписи не читаются и сравниваются только как картинка».
- View modes (`:76-79`, `modes` at `viewer.js:278`): **«Наложение»** (overlay of A and B on one sheet, tiles) and **«Рядом»** (side by side, A and B panes); repeated «Наложение» click returns to the previous mode (`setMode` `:261-267`).
- «шторка» (swipe) checkbox (`:80`): a slider under the sheet, reveals the lower layer; disabled in «Рядом».
- Zoom: percentage, «Вписать» (`:83-84`); Ctrl+wheel zoom, drag to pan, double-click fit (`version-comparison-zoom.js:3`, `viewer.js:479-505`).
- Layer checkboxes (`:85-86`, only in overlay): «места, где изменился цвет» (`LAYERS` at `viewer.js:15-23`: «Основное» on, «Светлые элементы» on, «места, где изменился цвет» on, «Оформление линий» on, «Перемещено (сдвиг — не изменение)» off, «В пределах допуска» off, «Шум» off, «Служебные зоны» on).
- «рамки отличий» (change boxes, off by default; `:88`), «Совмещать блоки» (align recognized B blocks onto A without changing the PDF, `:89-90`, `align_blocks` query).
- Tiles: `GET …/runs/{run}/sheets/{spid}/tile?mode=overlay|a|b&level&x&y&layers&text_color` (`version_comparison.py:408-449`); sheet data `GET …/runs/{run}/sheets/{spid}` (`:391`, loaded by `viewer.js:333`). Level is chosen from zoom; reductions take the maximum of difference masks so small changes survive zooming (`tiles.py:1-8`).
- Diff list «Отличия: N» with ← / → buttons (`:134-136`, keys ← → in `onKey` `:575`); items show `classLabel` (`CLASS_LABELS` `viewer.js:8-12`: «Текст», «Сдвиг надписи», «Графика: добавлено (B)», «Графика: удалено (A)», «Графика: изменено», «Изменение цвета», «Светлая заливка / штриховка», «Оформление линии: толщина, тон, наложение», «Блок перемещён», «Сдвиг: тот же элемент на другом месте»), before → after text fragments; shift classes are hidden by default with a toggle «сдвиги (не изменение): N — показать в списке» (`:142-144`); style-only toggle «оформление линий: N — показать в списке» (`:139-141`).
- «Служебные зоны и пометки» (`:~215-240`): zone/field changes, overlays (stamps, warnings, QR), annotations («удалена», «добавлена», «изменена»). Warning note «Исчезновение предупреждения не подтверждает согласования.»
- Side panel «Изменения в листе» (`version-comparison-sheet-changes.js`, mounted at `viewer.js:130-131`), see §1.6.

Sheet view in the matrix (`version-comparison.js:524-566`, `openSheets`/`sheetView`): one or two zoom panes (`vc-zoom-pane`, page tile endpoint `…/sources/{sha}/pages/{page}/tile`, router `:270`) with shared zoom/pan when the checkbox «вместе» is ticked (title «Масштаб и сдвиг одного листа повторяются на остальных (по долям листа)», `:534-536`), «＋», «−», «Вписать», nav «‹ лист» / «лист ›» over single sheets (`stepSingle`), and «Вывод ИИ по листу» panel (`:551-562`) with sheet kind, summary, objects, marks, «Неясно: …» and the note «Описание составлено ИИ по изображению и тексту листа и инженером не подтверждено.» (`:561`).

### 1.6 «Изменения в листе» (per-sheet AI panel in the viewer)

`version-comparison-sheet-changes.js` (233 lines). Reads only stored results on open (`GET …/runs/{run}/sheets/{spid}/changes`, `:124`); no model call to open.
Header: sheet title, source note «По полной спецификации · только изменения этого листа» (whole-spec source), A/B labels and pages, state label (`STATE_LABELS` `version_comparison_ai/sheet_changes/validate.py:257-262`: «Не обработано», «В очереди», «В обработке», «Готово», «Требуется уточнение», «Частично», «Строительных изменений не выявлено», «Описание устарело», «Ошибка», «Отменено», «По данным сравнения изменений нет»), «изменений: N», «Требует уточнения».
Warnings: «ТЕСТОВЫЙ ОТВЕТ подменного исполнителя …» when the executor is not `codex_exec`; «Описание устарело: …»; «Проверить:».
- Not processed (`:20-40`): «Не обработано.» + explanation «это не означает, что изменений нет»; button «Описать этот лист…» → estimate (`POST …/ai/estimate` with method `sheet_changes`, `:135`) → shows candidates, images and image bytes, prompt characters, model and effort, and «Подтверждаю передачу этого листа исполнителю» → «Передать и описать» (`POST …/ai/jobs`, `:142`) or «Отмена».
- Running/queued: «Идёт описание листа» / «Лист в очереди» + «Отменить задание» (`POST …/ai/jobs/{id}/cancel`, `:151`).
- Engine same: «По данным сравнения содержание листа не изменилось (только служебные зоны) — описание не требуется» (`:50`).
- Changes list (`:53-71`): object, «Было: …» / «стало» values, place, «Неясно:», value confirmation marks «с изображения» (value read from the drawing) and «не подтверждено» (not found in text or image), button «Показать на чертеже» (`focus`, `:158`, sets the viewer focus). Unresolved items under «Требует уточнения (N)» (`:~76`).
- Buttons: «Скопировать» (copy text), «MD листа» (`…/changes.md`), «Заявлено проектировщиком в разрешении (N)» (declared list from permit stamps) (`:75-83`).
- Diagnostics (coverage counts) are in a «Диагностике» panel (`:87`); the plan says it is kept out of the main report (`docs/version_comparison_sheet_changes_plan.md` §2.3).

### 1.7 «Сформировать PDF-отчёт…» and «Сводка изменений (MD)» (`version-comparison-md-report.js`)

Window title «Отчёт для заказчика по «Сводке изменений (MD)»» (`:15`), subtitle «Изменения проектных решений» (`:16`).
Source choice (`:26-31`): radio «текущая «Сводка изменений (MD)» серии» (disabled until the series summary exists; hint «Сводки серии ещё нет — сначала «ИИ-описание изменений».») or «загрузить MD-файл» (file input `.md`/`.txt`, `POST …/md-reports` multipart with `project_id`, `consent`, `reuse`).
Start button (`:37`, title «Передать текст сводки исполнителю ИИ и начать составление отчёта PDF…»), checkbox for consent, «reuse» option (reuse finished parts of earlier reports of the same summary, `:63`).
Executor line (`:33-35`): «Исполнитель: Codex, модель …, усилие …, одновременно до N переходов; упавший переход отправляется повторно».
Report list rows: state, stage, kind (analyst report vs client report; `r.kind === 'client'`), discipline (`client_disciplines` registry, «раздел: …»), downloads «Скачать PDF» (`:67`), «Скачать клиентский PDF» (client.pdf), source MD (`source.md`), «Остановить», «Продолжить», «Пересчитать PDF», «Удалить» (`:67-77`); «Подготовить содержание для заказчика» (client prepare) when the analyst report is ready.
Statuses and descriptions: `docs/version_comparison_md_report.md` §«Состояния» (not re-read in full).

### 1.8 Batch upload and the «Загрузить проект со всеми версиями» dialog

Dialog «Загрузка проекта и версий» (`version-comparison.js:435-502`), 2 steps:
- **Step 1** (`:436-467`): «Пакетная загрузка: каждая папка — отдельный проект со своими версиями.» button (opens batch modal), list of saved batches with «Открыть» and «файлов догружены не полностью»; «Куда загрузить» select: «Новый проект со всеми версиями» or «Добавить версии в «…»» (`:446-451`); text «Выберите папку с PDF (вложенные папки тоже читаются) или отдельные файлы и ZIP. Исходные файлы не изменяются.»; buttons «Выбрать папку» (`webkitdirectory`), «Выбрать файлы / ZIP» (`accept=".pdf,.zip"`); counter «Выбрано файлов: N · X МБ»; then the send button (`:465`).
  Sending: `POST …/uploads` → per file `POST …/uploads/{id}/files` (XHR with progress, `version-comparison.js:46-60`, message «Файл i из n: name (разбор штампов…)») → `GET …/uploads/{id}/proposal` (`:1475-1501`).
- **Step 2** (`:468-500`): proposal note («Номер в имени файла, «Изм.» и дата выпуска — подсказки; порядок версий задаёте вы.» from `store.py:~204`), then for each proposed project: title input, project select «новый проект» / «добавить в «…»», warnings (⚠), table «№ / Файл / Метка версии / Подсказки», buttons ↑ ↓ and «в проект…» to move a file to another group. Buttons «Отмена» and «Подтвердить…» (`:500`, `confirmUpload` `:1526-1540`: POST `…/uploads/{id}/confirm`, then reload catalog). Cancel before confirm calls DELETE `…/uploads/{id}` (`closeUpload` `:1462-1467`).

Batch modal «Загрузка нескольких проектов» (`version-comparison-batch.js:58-126`): choose a folder «Добавить папку» (one project) or «Добавить папку с проектами» (each subfolder is a project, `:68-69`); table of projects with up/down/remove (`:80-82`), per-version ordering (`:116-117`, «Версия выше» / «Версия ниже»), item commands «Исключить» (skip) and «Повторить» (retry, `:104-105`, POST `…/items/{id}/action`), «Принять состав, порядок и метки версий этого проекта» (`:120`, POST `…/items/{id}/confirm`), «Продолжить загрузку» (resume after a broken transfer), «Прервать передачу» (`:91`), «Удалить недогруженный пакет» (`:92`), pause/resume (`:97`). Status labels `labels` (`:4-8`): «Загрузка», «Ожидает разбора», «Разбор PDF», «Требуется проверка», «Ожидает обработки», «Подготовка версий», «Сравнение версий», «Готово», «Ошибка», «Исключён».
Frontend `groupFiles` keeps only `.pdf` (`version-comparison-batch.js:9-22`).

### 1.9 «Порядок версий» dialog (`version-comparison.js:503-523`)

Title «Порядок версий · {project}»; text «Порядок задаёте вы. Номер в имени файла, «Изм.» по штампам и дата выпуска — только подсказки.»; table «№ / Файл / Метка / Подсказки» with ↑ ↓ and editable label; buttons «Отмена» and save (title «Сохранить порядок и подписи. Сопоставление листов пересоберётся…»). Save: PUT `…/projects/{pid}/order`, then PATCH `…/versions/{vid}` for changed labels, then reload (`saveOrder` `:1557-1572`). Changing the order marks dependent results stale (see §2.2).

### 1.10 Messages and dialogs, quick list

Strings and where they come from are given inline above. Notable backend messages (`version_comparison*.py`, `services/version_comparison/*.py`): «принимаются только PDF и ZIP» (`store.py:194`), «слишком много файлов в архиве» (`store.py:183`), «сопоставление листов ещё не готово» (`jobs.py:431`; `series.py:81`), «выберите две разные версии» (`jobs.py:423`), «версии не принадлежат проекту» (`jobs.py:427`), «для серии нужно не меньше двух версий» (`series.py:79`), «серия по этому проекту уже идёт» (`series.py:84`), «Сначала загрузите все файлы пакета» (`batches.py:305`), «Подтвердите каждый файл проекта ровно один раз» (`batches.py:347`), «Проект ещё не готов к подтверждению» (`batches.py:345`), «Повтор доступен для проекта с ошибкой» (`batches.py:324`), «Управление пакетом со сравнением доступно только администратору.» (`version_comparison_batches.py:19`), «ИИ-описания выключены (VERSION_COMPARISON_AI_ENABLED=0)» (`version_comparison_ai/jobs.py`, `create_job`).

### 1.11 Filters and roles

- Roles: `canOperate` (admin-type operations: runs, links, order, queue, AI) and `canUpload`, `canDownload` come from `root.portalCan` (`version-comparison.js:700-701`, `version-comparison-projects.js:285`). Viewers see matrices read-only (`matrix-view`) and only download buttons.
- The batch backend restricts non-admin users from resuming batches that compare neighbours (`version_comparison_batches.py:11-22`).

---

## 2. What each step does, and what each user action calls

Notation: `P` = `/api/version-comparison/objects/{oid}`. «det.» = deterministic (no model). «LLM» = a model call through the Codex CLI (executor `codex_exec`, `version_comparison_ai/settings.py:68`).

### 2.1 Upload and catalog (no comparison)

| Action | HTTP | Handler / service | Model | Stored output |
|---|---|---|---|---|
| open section | GET `/objects` ; GET `P/catalog` | `version_comparison.py:95,114` → `store.load_catalog` | none | catalog JSON (projects, versions) |
| Загрузить… → create | POST `P/uploads` | `:133` → `store.create_upload` | none | `uploads/<id>/upload.json` |
| add file | POST `P/uploads/{u}/files` (multipart `file`, `relative_path`) | `:138` → `store.add_file` (`store.py:168-196`) | none; PDF stamp read by `store.detect` | copy in upload dir; `detected` dict per file |
| proposal | GET `P/uploads/{u}/proposal` | `:146` → `store.proposal` (`store.py:202-238`) | none | groups (not applied) |
| confirm | POST `P/uploads/{u}/confirm` | `:151` → `store.confirm` + `jobs.ensure_profiles` | none | copies to `sources/<sha>.pdf` (read-only), catalog versions, profiles queued |
| cancel upload | DELETE `P/uploads/{u}` | `:161` | none | removes upload |
| reorder | PUT `P/projects/{p}/order` | `:169` → `store.reorder` | none | version order (matrix signature changes) |
| rename / relabel / delete | PATCH `P/projects/{p}`, PATCH `P/versions/{v}`, DELETE `P/versions/{v}` | `:174,179,184` | none | catalog |
| batch | GET/POST `P/batches`, GET/DELETE `P/batches/{b}`, chunk POST `…/items/{i}/files/{f}/chunks/{n}`, POST `…/files/{f}`, POST `…/batches/{b}/start`, PATCH `…/batches/{b}` (pause), POST `…/items/{i}/action` (skip/retry), POST `…/items/{i}/confirm` | `version_comparison_batches.py:72-125` → `batches.py` | none for upload/detect/prepare; comparison runs only if `compare_neighbors` | `batches/<b>/batch.json`, one project per phase |

Batch worker: a daemon thread `vc-batches` (`services/version_comparison/recovery.py:84-89`) calls `batches.run`, which serialises with a file lock and handles one project phase at a time, active items first (`batches.py:543-560`). Item states: queued → detecting → review (user confirms) → ready → preparing → comparing → done / failed / skipped (`batches.py:337-352`, `:576-587`).

### 2.2 Profile, matrix (sheet identity across versions)

| Action | HTTP | Service | Model | Output / idempotency |
|---|---|---|---|---|
| read overview (page «Проекты») | GET `P/overview` (`:127`) | `overview.build` (`overview.py:334`) | none, read only | JSON, starts nothing |
| «Подготовить» / «Повторить» (profile) | POST `P/projects/{p}/prepare` (`:200`) ; POST `P/versions/{v}/profile/retry` (`:189`) | `jobs.matrix` (`jobs.py:212`) → `ensure_profiles` (`:125`) → `jobs._profile_job` (`:134`) → `profile.build` (`profile.py:170`) | none | `profiles/<sha>/…`, keyed by sha256; `force=False` reuses |
| matrix (rows) | GET `P/projects/{p}/matrix` (`:209`) ; `matrix-view` (`:214`) | `jobs.matrix` → `_lineage_job` → `lineage.build` (`lineage.py:397`) | none (deterministic); AI-proposed links are stored separately (`ai_link`) | `lineage/<project>.json` with `signature`, `result`, `edits`, `built_at` |
| manual link edits | POST `P/projects/{p}/links` (`:220`), `…/links/undo` (`:225`), `…/links/batch` (`:230`) | `jobs.add_link_edit(s)` (`jobs.py:298-332`) | none | `edits` in lineage file; matrix rebuilt when signature changes |

Matching (`lineage.build`, `lineage.py:397-498`): versions are walked in the user’s order; for each adjacent pair the primaries of the next version are assigned to the previous version’s pages by a maximum-weight assignment over a page score (`score`, `_score_rules`; text, word layout, title, sheet number, 36 dpi mask, kind), using `MATCH_HIGH = 0.55`, `MATCH_MEDIUM = 0.35`, `MATCH_CANDIDATE_FLOOR = 0.20` (`version_comparison/settings.py:92-94`). Cells: `matched` with confidence `high` / `medium` / `group` / `manual`; unmatched cells keep candidates; `absent` when nothing is left. Unmatched new sheets get their own rows; a bridge step reconnects a sheet missing in one intermediate version (`lineage.py:443-470`). Duplicates (same content on several pages) are marked `dups`. Match rules default `v1.2` (`settings.py:172`); `v1.2` adds resolve, package, direct, permit, page-number and group rules (`settings.py:125`).

Staleness: matrix is `stale` when `signature` (versions order + edits, `jobs._signature` `jobs.py:173`) no longer matches; overview shows «устарело» (`overview.py:102-112`).

### 2.3 Sheet comparison of a transition (deterministic)

| Action | HTTP | Service | Output |
|---|---|---|---|
| «Запустить» / «Заново» (series) | POST `P/projects/{p}/series` (`:317`) | `series.create` (`series.py:67-104`) → `_job` (`:118`) | `series/<id>/series.json`: pairs list (a, b, labels, run_id, state) |
| transition run | created inside the series job via `jobs.create_run(… scope="all")` (`series.py:164-171`) | `jobs.create_run` (`jobs.py:420-512`) | `runs/<run>/run.json`: items (kind compare/only_a/only_b, status, result_status, reasons, parts), progress, `params` (dpi, tol_pt, algo) |
| per-sheet compare | (internal) `jobs._run_job` (`jobs.py:671`) → `engine.compute_sheet_pair` (`engine.py:477`) in a process pool (`_call`, `jobs.py:89`) | — | `runs/<run>/sheets/<spid>/` result (see §4.1) |
| cache | `jobs._cache_key` (`jobs.py:586-592`): sha256 over both content hashes, annotation hashes, params, reasons, `ALGO_VERSION` | — | identical results reused across runs |
| spec / parts / permit phases | `_spec_phase` (`jobs.py:818`), `_parts_phase` (`:875`), `_permit_phase` (`:951`) after the sheet loop (`:743-756`) | `spec.build`, `permit` | per-run spec extraction for the «СО» positions channel |
| progress/pause/resume/cancel | GET `P/runs/{r}`, POST `P/runs/{r}/pause|resume|cancel`, GET `P/projects/{p}/runs`; series: POST `P/series/{s}/pause|resume|cancel`, GET `P/series/{s}` (`:317-345`) | `series.pause/resume/cancel` (`series.py:232-283`) | series state polled every 2 s by the UI (`version-comparison.js:828`) |

Per-sheet algorithm (engine, `engine.py`): render both pages at `settings.dpi()` (`engine.py:94-104`), register B onto A (`registration.register`, `registration.py:122`: anchors from words and zones, else phase correlation, `:62-100`), compare words (`_compare_words`, `:142`), masks (`_glyph_line`, `_shift_explains`, `_overdraw`), colour (`COLOR_DELTA = 25`, `DARK_THRESHOLD = 200`, `LIGHT_THRESHOLD = 250`, `settings.py:46-50`), text changes (`textdiff.build/finalize`, `textdiff.py:110-124`), service zones (`service.compare`, `service.py:125`), annotations (`_compare_annotations`, `engine.py:348`), warnings, and spec positions. Each channel reports `checked` (with diff count) or `unchecked` (with reason). `status.decide` (`status.py:45-66`): any forcing reason → «Нужна проверка»; any main channel (geometry, color, text) diff → «Есть отличия»; any unchecked channel → «Нужна проверка»; only service-channel diffs → «Совпадает, изменены служебные зоны»; else «Совпадает».

Run summary (`series.summary`, `series.py:38-63`): counts of `result_status` (`compared`, `same`, `zones_only`, `different`, `style_only`, `needs_review` = needs_review + unmatched, `added`, `removed`, `failed`) and deterministic verdict strings (see §4.1).

### 2.4 Action buttons in the stage columns (projects page)

From `frontend/static/js/version-comparison-projects.js:460-530` (`stageActs`):
- **1 Загрузка**: no button.
- **2 Разбор версий**: «Повторить» if a version failed → POST `…/versions/{v}/profile/retry` for each.
- **3 Сопоставление листов**: «Подготовить» when todo/stale (POST `…/projects/{p}/prepare`, `:~471`).
- **4 ИИ-проверка сомнительных пар** (`luna`): «Проверить» → `lunaDialog` → POST `…/ai-sheet-match` with `{consent, project_ids, luna_only: true}` (`:559-571`, `:~483`). Running: «Пауза» (POST `…/ai-sheet-match/pause`). Paused/interrupted: «Продолжить» (same POST). Done cells have no button; re-check is by the row checkbox and the queue. The code comment states that there is no «Перепроверить» button (`:372-373`).
- **5 Сравнение соседних** (`series`): «Запустить» (POST `…/projects/{p}/series`), «Пауза» (POST `…/series/{s}/pause`), «Продолжить» (POST `…/series/{s}/resume`, for paused/interrupted/failed), «Заново» → confirm dialog «Сравнение соседних заново · …» with text «Все переходы будут пересчитаны по текущему порядку и составу версий.» and «Пары листов, которые не менялись, берутся из кэша» (POST `…/projects/{p}/series`, `:~498`).
- **6 ИИ-описание изменений** (`ai`): «Запустить» → `aiDialog` (estimate via GET `…/series/{s}/ai-sheet-changes/estimate`, then POST `…/stage-queue` with `items:[{project_id, stage:'ai'}]`) — AI runs go through the global queue; «Из очереди» (POST `…/ai-sheet-changes/cancel`), «Пауза» (`…/pause`), «Продолжить» (`…/resume`), «Заново» → `aiDialog(again=true)` (stage-queue with `restart: true`).
- **7 Сводка и отчёт** (`report`): «Сформировать PDF-отчёт» → `reportDialog` → POST `…/series/{s}/md-report` `{consent, reuse: true}`; «Пауза» (`…/md-reports/{r}/pause`); «Продолжить» (`…/resume`); «Заново» (new report); «PDF» download (`…/md-reports/{r}/report.pdf`).

Sheet-level (viewer side panel, §1.6): «Описать этот лист…» → POST `…/runs/{run}/ai/estimate` → «Передать и описать» → POST `…/runs/{run}/ai/jobs` with `method: "sheet_changes"`, `spids: [spid]`, `consent`.

### 2.5 AI stages: who calls which model, and what is sent

**a. ИИ-проверка сомнительных пар («Луна»)** — `version_comparison_ai/sheet_match.py`.
- Model: `gpt-6-luna`, effort `high`, parallel 30 by default (`version_comparison_ai/settings.py:260-262`, env `VC_SM_*`).
- Questions (docstring): `review` (sheet A has no pair, B-cell has candidates «⁇») and `medium` (algorithm pair of medium confidence); sheet groups of tables are not asked. Images with captions go in (`img/`), candidate pages are named in the question.
- Accepted pair only if answer confidence is `high`, candidate number and named page agree, the sheet is not inside a multi-sheet spec, B is not linked to another A, and a reverse question agrees (`sheet_match.py` docstring). Otherwise a hint (`hint_*`) in the cell.
- Storage: `objects/<oid>/sheet_match/job.json`, `answers/<content key>.json` (identical content is never re-sent), decisions in `lineage/<project>.json` key `ai` (`edits`, `notes`). Manual edits win over model links (`lineage.py:1-19`).
- Exact prompt payload beyond images and candidate numbers: UNCONFIRMED (not read).

**b. Сравнение соседних** — deterministic, no model (§2.3).

**c. ИИ-описание изменений, per sheet («Изменения в листе», method `sheet_changes`)** — `sheet_changes/series_ai.py`, `run.py`, `collect.py`, `packet.py`, `prompt.py`.
- Model: `gpt-6.1-sol`, effort `high`, parallel 1 by default (`version_comparison_ai/settings.py:180-181`, `:219-222`; env `VC_SC_*`). Executor: Codex CLI, isolated (empty temp dir, read-only sandbox, no user config, `executor.py` docstring).
- What is sent: only sheets whose engine status is not `same` / `same_zones_changed` (`version_comparison_ai/jobs.py:119` `SC_SKIP_STATUSES`; `series_ai.py` docstring). Per sheet a packet (`packet.py:444`) with candidate objects from engine pointers (`collect.py`): `table` (table rows A and B, header, preliminary row match), `place` (A and B crops, nearby words and room/opening labels), `shift` (moved graphic element). Images: crops of A and B rendered at a DPI derived from text height and the image-side cap (`packet.py:163-165`, `:227-251`; `images.py`). Text: words of the two areas as data in the prompt (`prompt.py:1-…`, template plus packet data in a fenced block). No whole PDF; context requests are executed by the program inside the two chosen versions (`run.py` docstring).
- Limits: at most `MAX_LAUNCHES` CLI launches per sheet (main, one technical retry, one context request, one unparsed-record pass; `run.py` docstring); 429 waits use `sc_retry_delays` (default 20, 60, 120, 300, 600 s; `settings.py:231`).
- Validation (`validate.py`, docstring lines 1-10): schema, packet and part IDs, candidate and image IDs; each field gets `text` (found in its own side’s text layer), `image` (read from the drawing the model cited), or `unverified`. Coverage of candidates (`not_reviewed`) and unresolved items are counted; state derived by `state_of` (`validate.py:244-254`).
- Single-sheet add/remove (`single.py`): one call per sheet «что на этом листе», no before/after.

**d. ИИ-описание, whole series** — `series_ai.py`: one `sheet_changes` job per computed transition; all sheets of all transitions share one concurrency limit (`sc_parallel`); a project waits in the global `ai_series_queue.json` (one series at a time per install; `series_ai.py` docstring). States are read from job files on every read (no duplicate state).

**e. Полные спецификации (СО)** — `version_comparison_ai/whole_specifications.py` (started from the stage queue, `stage_queue.py:337`) and `version_comparison/specification_run.py`.
- Model: `specification_run.MODEL = "gpt-6-luna"`, `EFFORT = "high"` (`specification_run.py:22-23`); parallel `WS_DEFAULT_PARALLEL = 4` (`version_comparison_ai/settings.py:305`).
- Unit: the whole specification of one version in one Codex session (`docs/whole_specification_comparison.md` §«Последовательность», step 2); the program checks block coverage, quotes and field values; an unconfirmed value or a lost row makes that side incomplete (same section, step 3). Source text comes from the stored page words and vector grid of the profile (docs: «не извлекает текст PDF и не читает растр» for the preparation tool). Full pipeline details: UNCONFIRMED beyond the docs.
- Comparison is order-independent (`specification_compare.compare`, `specification_compare.py:316`).
- Used when a transition has a specification («полное сравнение»); otherwise «листовой ИИ» (UI `version-comparison.js:~247`).

**f. Сводка изменений (MD)** — `sheet_changes/series_summary.py` (docstring: «Без вызова модели»). Deterministic MD from the stored answers of the series, per transition and per sheet with pages of both versions. It is the input of the PDF stage.

**g. PDF-отчёт («Аналитический отчёт», `md_report/runner.py`, 1240 lines)** — Codex, model `gpt-6.1-sol`, effort `high` (`md_report/settings.py:16-17`). Pipeline (runner docstring): MD intake → parse (`parse.py`) → analyst per part of a transition (`stages.py`, «Анализ») → verifier («Проверка») → composer → report_v2 → PDF by reportlab (`md_report/pdf.py:1-14`, no model writes the PDF). Program checks: IDs, block coverage, row ranges, verdicts per claim, transition order; labels, dates and sources are filled by the program (`stages.py` docstring). A client variant («Отчёт для заказчика», `kind: client`) uses `client.py`/`client_edit.py` with discipline prompts from `prompts/client_disciplines/_registry.json` (`md_report/client.py`, UNCONFIRMED beyond names). Client parallelism label: «одновременно до N переходов» with default 10 (`version-comparison-md-report.js`, UI text).

**h. Legacy «records» method** — `version_comparison_ai/jobs.py:234,238` (`METHODS = ("records", "sheet_changes")`, default `records`). The only UI caller of the default method is the run-level panel `vc-ai-report` (`version-comparison-ai.js:348`), which is not reachable (see §5). Executor/model for `records`: UNCONFIRMED (generic default `gpt-6-astra`, effort `medium`: `version_comparison_ai/settings.py:72,75`).

### 2.6 Retry, failure, progress summary

- Profile failure: «Повторить» (`projects.js:468`). Matrix failure: the matrix panel shows «Не удалось подготовить версии» (`version-comparison.js:113`).
- Series failure: `failed` pairs keep `error`; resume skips done pairs (`series.py:139-165`); UI «Продолжить».
- Run items: failed sheets counted in `summary.failed` (`series.py:38-63`).
- AI: failed sheets «Повторить» (`retry-incomplete`) re-describe only failed sheets (`version-comparison.js:171-172`); 429 waits and quota pauses (`paused_quota`, `paused_auth`) are documented in `jobs.py` docstring and in `overview.py:~228`.
- Batch: `failed` items are retried with «Повторить» (`batches.py:315-336`).
- Progress: series 2 s poll (`version-comparison.js:828`), matrix 1.5 s (`:785`), run 2 s (`pickRun`, `:802`), AI series 3 s / 5 s queued (`:~865`), overview 5 s when busy else 30 s (`projects.js:296-300`), queue state within overview.

---

## 3. Inputs

### 3.1 Accepted files

- Browser: `<input type=file webkitdirectory>` (folder, recursive) and `<input type=file accept=".pdf,.zip">` (`version-comparison.js:441-446`). Non-PDF files in a folder are ignored by the batch grouper (`version-comparison-batch.js:16`).
- Server, single upload path: `store.add_file` accepts a PDF, or a ZIP whose PDF members are extracted (max 500 members, `store.py:28`, `:177-190`); other names raise «принимаются только PDF и ZIP» (`store.py:192-194`). Upload files are copied, originals are never changed (`store.py:169`, `_copy_source` read-only chmod 0444 in `batches.py:412-426`).
- Server, batch path: PDF only (`batches.py:131`); limits MAX_PROJECTS 100, MAX_FILES 10 000, chunk 8 MB (`batches.py:29-31`; `version_comparison_batches.py:49-52`).
- Size of one PDF: UNCONFIRMED (no explicit cap found in the read files).

### 3.2 How versions of one cipher are recognised

1. **Per file (`store.detect`, `store.py:106-134`):** for every page the lower-right corner (205 × 70 mm, rotated) is read; `stamp.parse` (`stamp.py:87`) extracts the document designation (the «шифр» in the title block) and «Изм.» numbers (`izm_max`); `stamp.release_blocks` (`stamp.py:157`) extracts release dates. Result: `page_count`, `designation` (most common), `izm_max`, sorted `release_dates`.
   `document_designation` (`store.py:90-103`): designations on sheets; a sub-document («ИТП.ТМ») is merged into its parent only if the parent occurs on at least 20 % of sheets (`_PARENT_SHARE = 0.2`, `store.py:87`).
2. **Per file name (`store._name_hint`, `store.py:75-87`):** `file_number` from `(N)` at the end of the stem (`_FILE_NUMBER = \((\d{1,3})\)\s*$`, `store.py:71`); `izm_in_name` from «изм N» (`_IZM_IN_NAME`, `store.py:72`); `name_base` = stem without number and «изм/v/ред» suffix.
3. **Grouping (`store.proposal`, `store.py:202-214`):** files are grouped by `designation`, else by `name_base`. An existing project is matched by code (`existing_project_id`, `store.py:219`). Batch path: project code = first designation found, project title = folder name until a code is known (`batches.py:378-383`, `:385-411`); files with differing designations raise the warning «В папке обнаружены разные шифры…».
4. **Order:** the single-upload proposal sorts by (`izm_max`, last release date, `file_number`, file name) (`store.py:213-222`); a warning appears when that order disagrees with the numbers in the file names, or two files share the same «Изм.» (`store.py:223-230`). The batch path sorts only by `file_number` (`batches.py:373-376`, `:~391`). In both cases the user has the final word (text «порядок версий задаёте вы», `store.py:~204`; order dialog `version-comparison.js:503`).
5. **Labels:** suggested «V{file_number+1 or 1} Изм.{izm_max} {last release date}» (`store._suggest_label`, `store.py:241-250`), editable by the user. Batch default label via `_suggest_labels` (`batches.py:40-48`).
6. **Versions** are identified by sha256 of the PDF (`store._register_file`, `sources/<sha>.pdf`); `version_id` is a stable id from batch and item ids (`batches.py:101-104`, `:428-433`).

### 3.3 Definitions used by the code

- **Версия** (version): one PDF in the catalog of a project, with `user_label`, `sha256`, `page_count`, `detected`.
- **Проект** (project): an ordered list of versions with a title and `code` (cipher), `project_id` (`store.py:47-58`, `:58-64`).
- **Порядок версий / переход** (order / transition): the user order; a transition is an adjacent pair (V1→V2, V2→V3 …). Non-adjacent pairs are compared only through direct page links (`jobs.create_run`, `:428-431`); otherwise the UI describes them as a chain hint.
- **Профиль** (profile): per-PDF page facts: stamp, words, masks, scan flag (`profile.py:1-…`, `profile.build` `:170`).
- **Матрица / строка** (matrix / row): one sheet identity across all versions; a row holds the matched page of each version (`lineage.py:1-19`).
- **Серия** («Сравнить все соседние», series): the ordered list of transition runs of one project (`series.create`, `series.py:67-104`). A series is stored with `pairs[i] = {a, b, run_id, state}`.
- **Прогон** (run): one transition, `scope` `all` (series) or `manual` (selected sheet pairs) (`jobs.create_run`).
- **Пара листов** (sheet pair): one matched (A page, B page) in a run; item `kind` = `compare` (both sides), `only_a` (removed or unmatched), `only_b` (added or unmatched) (`jobs.py:~436-505`).
- **Задание ИИ** (AI job): per run and method (`jobs.create_job`, `version_comparison_ai/jobs.py:237`), stored under `runs/<run>/ai/<job>/`.

---

## 4. Outputs

### 4.1 Per-sheet comparison record

Written by `engine.compute_sheet_pair` (`engine.py:477-1027`), schema `version_comparison.sheet_result/v1`, algo `ALGO_VERSION = "vc1.13"` (`version_comparison/settings.py:11`). Fields (from the code): `sheet_pair_id`, `row_id`, `a`/`b` (`version_id`, `sha`, `page`, `sheet_no`, `title`, `scan`), `params` (`dpi`, `tol_pt`, thresholds), `match` (link confidence etc.), `status`, `reasons`, `channels` (dict of 8 channels), `identical_content`, `regions` and layers, `canvas`, `transform` (B→A matrix), `aligned_blocks`, `service` (zone field changes), `overlays` (stamps, warnings, QR), `annotations`, `zones`, `text_changes`.

Channels (`status.py:11`; labels `version-comparison.js:19-21`): `geometry` («графика»), `color` («цвет и оформление линий»), `text` («текст»), `text_coverage` («читаемость надписей»), `zones` («служебные зоны»), `annotations` («PDF-пометки»), `warnings` («предупреждения»), `spec_positions` («позиции СО»). Each is `checked` (with `diffs`) or `unchecked` (with `reason`, e.g. «нет текстового слоя: надписи сравнены только графически») or `not_applicable`.

Sheet statuses (`status.py:17-27`, UI `version-comparison.js:9-16`):
- `same` «Совпадает»;
- `same_zones_changed` «Совпадает, изменены служебные зоны»;
- `different` «Есть отличия»;
- `needs_review` «Нужна проверка» (forced by reasons such as `MATCH_LOW_CONFIDENCE`, `MATCH_AMBIGUOUS`, `ALIGNMENT_UNRELIABLE`, `DUPLICATE_SHEET`, `RENDER_FAILED`, `NO_TEXT_LAYER`, `STAMP_NOT_RECOGNIZED`, `SPEC_NOT_PARSED`, …);
- `added` «Лист добавлен», `removed` «Лист удалён», `unmatched` «Не сопоставлен» (run items with `only_a` / `only_b`, `jobs.py:~449-505`).
Text items: `textdiff.classify` (`textdiff.py:110`) yields change kinds and `numbers` (`textdiff.py:124`) yields before/after numeric pairs; the viewer shows them as «было → стало» (`viewer.js:~ 205-215`).

### 4.2 Transition summary (series)

`series.summary` (`series.py:38-63`) produces: `compared`, `same`, `zones_only`, `different`, `style_only`, `needs_review`, `added`, `removed`, `failed`, and `verdict` strings: «переход досчитан не полностью», «основное содержание совпадает» (+ «, изменены только служебные зоны»), «есть отличия на N л.» (+ «из них только оформление линий — K»), «изменён состав (+A / −R л.)», «нужна проверка: N», «ошибка расчёта: N».

### 4.3 AI description of changes (per sheet)

Stored per job as `sheet_changes.json` (`sheet_changes/report.py:~50-70`): `state`, `state_label`, `executor` runtime, `packet_id`, `changes` (list), `unresolved` (questions), `excluded` (pointers ruled out by the program), `declared` (permit stamps «Заявлено проектировщиком в разрешении»), `coverage` (`candidates`, `in_changes`, `not_reviewed`), `transform`, `canvas`, `diagnostics` (issues, pointer ledger counts, excluded_by_program, candidates), `disclaimer`, `created_at`.
Each change item carries: object name, place, kind, before/after (or value_a/value_b, unit, quantity), certainty, candidate and image ids, source side and bbox, confirmation tier (`text` / `image` / `unverified`, `validate.py:6-9`), limitation («Неясно»). The schema is the JSON subset in `sheet_changes/schema.py` (all properties required, «нет значения» = empty string).
The sheet description is labelled as AI output not confirmed by an engineer (`version-comparison.js:561`).

Series-level: `ai_sheet_changes.json` lists the jobs per transition (`series_ai.py` docstring); the MD summary (`series_summary.py`, deterministic, same bytes for same data) lists per transition A/B label (cipher, Изм., date, file), per sheet number/title/pages, the main change text, the count of open questions per sheet, and a «Реестр» of categories (`series_summary.py:170-174`: «совпадает по движку», «только служебное», «описано ИИ», «СО целиком», «неоднозначно», «не обработано»). Endpoint `…/ai-sheet-changes/summary.md` (`version_comparison_ai.py:298`).

### 4.4 Specification comparison (СО)

- Per version: parsed positions (9 fields: position, name, mark, code, supplier, unit, quantity, mass, note; section, parent) with block IDs and quotes (`docs/whole_specification_comparison.md` §«Последовательность», step 2).
- Per transition (`specification_compare.compare`, `specification_compare.py:316`): changes (quantity / mark / name / other fields as «было → стало»), added and removed positions with sources, unresolved groups for disputed matches. MD/JSON reports `report.json`, `report.md` (doc step 6). Only substantive changes go into the MD; unchanged positions and technical stats stay in JSON.
- In the UI: counts «изменено / +добавлено / −удалено / ?неясно» per transition (`version-comparison.js:~ 262`), method and coverage; states (`SPEC_STATE`).
- Engine-side spec channel `spec_positions` (`status.py:11`; `engine.py:997-1000`): «лист совпадает по графике и тексту» or «не спецификация».

### 4.5 Reports

- MD summary: `…/ai-sheet-changes/summary.md` (deterministic, §4.3).
- Analytical PDF: `…/md-reports/{id}/report.pdf` (reportlab, A4, `md_report/pdf.py`); also `report.json` (report_v2), `source.md` (exact input copy), `facts.json` (`version_comparison_ai.py:484-512`). Client PDF `client.pdf` after `client-prepare` (`version_comparison_ai.py:463-482`).
- Excel and HTML-archive run reports: `version_comparison/report.py` (`build_xlsx` `:133`, `build_series_xlsx` `:364`, `build_html_zip` `:449`) exposed at `GET …/runs/{r}/reports/{name}`, `GET …/series/{s}/report.xlsx`, `POST …/runs/{r}/reports` (`version_comparison.py:354-383`). **Not wired in the UI** (no caller in `frontend/static/js`; see §5).
- Per-run spec, permit, and sheet PNG endpoints also exist (`version_comparison.py:385-410`); the UI uses `sheets/{spid}` and `tile`, not `preview.png`.

### 4.6 Expert confirmation

No approval, sign-off or «принято инженером» status exists in the read code (grep for `approv`, `accepted_by`, `reviewed_by`, `confirmed_by` found none in the version-comparison modules or UI). What exists:
- manual sheet links («✎», «Применить сопоставления»), stored as edits and applied in the matrix (§1.4, §2.2);
- model links accepted only under strict rules; otherwise hints (§2.5a);
- «Проверить» review list for sheets where the AI found no change but comparison left marks (§1.3, stage 6);
- «Требует уточнения» questions per sheet (§1.6);
- per-value confirmation tiers («с изображения», «не подтверждено») (§1.6);
- the notice that AI sheet descriptions are not confirmed by an engineer (`version-comparison.js:561`);
- the MD/PDF client report is prepared by a model step after an explicit consent checkbox (`version-comparison-md-report.js`, `client-prepare` endpoint).

---

## 5. Visible in the current UI versus present only in backend or plans

Method: a feature counts as **wired** when a Vue template or a `api(...)`/`VC.api(...)` call in `frontend/static/js` reaches it (grep of template bodies and call sites). Components are mounted from `version-comparison.js` templates (`:524`, `:569`, `:522`, `:525`), `vc-projects-overview` from `:~99`, and `vc-batch-upload` from `:75`. `app.js:21299` registers the component set.

| Feature | Status | How known |
|---|---|---|
| Projects table, tiles, filters, queue strip, selection | wired | `version-comparison-projects.js:98-248`; `app.js:21299` |
| Stage buttons «Подготовить», «Запустить», «Пауза», «Продолжить», «Заново», «Повторить» | wired | `projects.js:460-530` |
| Stage queue (`stage-queue` endpoints) | wired | `projects.js:415-437`, `version-comparison.js:941` |
| Sheet matrix, pair A/B, «только изменения», drag and drop, attach/detach/absent, «Применить сопоставления» | wired | `version-comparison.js:347-430`, `:1349-1408` |
| Sheet viewer: overlay/side-by-side, swipe, layers, zoom, change list, «Совмещать блоки» | wired | `version-comparison-viewer.js:76-160` |
| Zoom panes for single and paired sheets | wired | `version-comparison.js:524-566`; `version-comparison-zoom.js` |
| «Изменения в листе» per-sheet AI description (estimate, consent, job, cancel, focus, MD) | wired | `version-comparison-sheet-changes.js:43-160`, `viewer.js:130-131` |
| Series AI («ИИ-описание изменений», per transition, review list, retry, pause, resume, queue) | wired | `version-comparison.js:159-225`, `:855-945` |
| Whole specifications block («Полные спецификации (СО)») | wired (display and pipeline via queue) | `version-comparison.js:237-275`, `:896`; `stage_queue.py:337` |
| MD summary download (project header and stage 6/7) | wired | `version-comparison.js:102`, `projects.js:189`, `version-comparison-projects.js:608` |
| PDF analytical report and client PDF (window «Отчёт PDF») | wired | `version-comparison-md-report.js`; `version-comparison.js:106,277-333` |
| Batch folder upload (multi-project) | wired | `version-comparison-batch.js`; `version-comparison.js:75,441-467` |
| Single upload with proposal and label editing | wired | `version-comparison.js:435-502`, `:1475-1541` |
| Order dialog (PUT order, PATCH labels) | wired | `version-comparison.js:503-523`, `:1557-1572` |
| Run-level AI panel `vc-ai-report` (`ai/jobs` with `records` method, evidence focus) | **present, not reachable**: `showAiReport` (`version-comparison.js:1442`) and `aiRun` (`:1437`) are defined and returned in the setup object but never called from any template or function; `aiPanel.open` stays false. Its component `version-comparison-ai.js` is registered (`:298`) and its `vc-ai-item` child is used only inside that component. |
| Legacy `records` AI method | backend present; UI path only through the unreachable panel above | `version_comparison_ai/jobs.py:234`; `frontend/static/js/version-comparison-ai.js:348` |
| Excel/HTML run reports and series Excel | **backend only** (no UI caller in `frontend/static/js`) | `version_comparison.py:354-383`; grep of `report.xlsx`, `/reports` in frontend |
| `preview.png` per sheet | backend only (no caller) | `version_comparison.py:400` |
| `ai/latest`, `ai/jobs/{id}/view`, `view.md`, `report.md`, `check-crop`, `packet` endpoints | `view`/`focus`/`ref-focus` used only by the unreachable panel (`version-comparison-ai.js:322-395`); the others are not called from the UI | grep of `frontend/static/js` |
| `POST /md-reports` (file upload of MD) | wired (file mode of the report window) | `version-comparison-md-report.js:130` |
| `client-prepare` (client content) | wired (client report button) | `version-comparison-md-report.js:70` |
| Expert approval step | absent in code | §4.6 |
| `docs/whole_specification_comparison.md` prototype tooling (`scripts/compare_whole_specifications.py`, `scripts/whole_specification_stand_preview.py`) | tooling and stand preview; not part of the UI | file names in tree; doc status line «выпуск на production не выполнен» |
| Plans (`docs/version_comparison_*plan*.md`) | mostly historical: their status lines say «только план» (AI plan 15.10, sheet changes 16.10, matching plan 17.10), but the corresponding code exists and is wired. Treat plans as design history, not as the status of the code. |

Notes on the plans, by status line (`docs/`): `version_comparison_plan.md:3` «план принят за основу (14.10)»; `version_comparison_ai_plan.md:3` «только план»; `version_comparison_sheet_changes_plan.md:3` «только план»; `version_comparison_matching_upgrade_plan.md:3` «план и протокол эксперимента»; `version_comparison_md_report.md` describes the implemented report with run dates 18.10.2026; `version_comparison_worker.md` describes the optional worker service `VERSION_COMPARISON_EXECUTOR=worker` (`:12-20`) and its installation on a local server 8095.

---

## 6. Size census (approximate)

Lines counted with `wc -l` on downloaded files; bytes from `tree.json` for files not downloaded. Totals are per directory.

### 6.1 UI (frontend)

| File | Lines | Role |
|---|---|---|
| `frontend/static/js/version-comparison.js` | 1604 | page: template `:65-570` (≈505 lines), setup and logic `:571-1604` (≈1030) |
| `frontend/static/js/version-comparison-projects.js` | 629 | «Проекты и этапы»: template `:96-242`, logic `:243-629` |
| `frontend/static/js/version-comparison-viewer.js` | 693 | sheet viewer: template `:26-240`, logic `:241-693` |
| `frontend/static/js/version-comparison-ai.js` | 410 | run-level AI panel (unreachable) and item component |
| `frontend/static/js/version-comparison-sheet-changes.js` | 233 | «Изменения в листе» panel (template `:7-96`) |
| `frontend/static/js/version-comparison-batch.js` | 352 | batch uploader (template `:49-126`) |
| `frontend/static/js/version-comparison-md-report.js` | 199 | PDF report window (template `:10-84`) |
| `frontend/static/js/version-comparison-zoom.js` | 161 | zoom pane (template `:9-19`) |
| `frontend/static/css/version-comparison.css` | 381 | page and matrix styles |
| `frontend/static/css/version-comparison-ai.css` | 154 | AI and sheet panel styles |
| `frontend/static/css/version-comparison-batch.css` | 21 | batch styles |
| **UI total** | **4237** | (JS 3910, CSS 556) |

Per step (UI): projects table and stage actions ≈ 630 (projects.js); matrix and transitions ≈ 1100 (version-comparison.js `:65-570` plus logic for matrix, links, series); viewer and tiles ≈ 690 + 161 (zoom); «Изменения в листе» ≈ 233; series AI block ≈ 410 (ai.js, unreachable panel part) plus parts in version-comparison.js; PDF report ≈ 199; batch and upload ≈ 352 + upload parts of version-comparison.js (`:435-502`, `:1458-1541`).

### 6.2 HTTP layer (backend routers)

| File | Lines | Endpoints |
|---|---|---|
| `backend/app/api/routers/version_comparison.py` | 453 | catalog, upload, profile, matrix, links, thumbs, runs, series, reports, sheet data and tiles (≈ 55 routes) |
| `backend/app/api/routers/version_comparison_ai.py` | 550 | AI jobs, sheet changes, series AI, whole specs, luna, MD reports, stage queue (≈ 60 routes) |
| `backend/app/api/routers/version_comparison_batches.py` | 126 | folder batches (≈ 12 routes) |
| **Router total** | **1129** | |

### 6.3 Services (backend)

Lines for downloaded files; bytes for not downloaded.

| Area | Downloaded lines | Not read (bytes) | Notes |
|---|---|---|---|
| `version_comparison/` core | 10 054 | 255 029 B in 17 files | jobs 1222, engine 1027, lineage 699, specification_run 688, specification_compare 724, resolve 573, spec 571, report 544, batches 603, overview 385, store 348, series 301, worker 296, tiles 289, textdiff 227, settings 205, stamp 204, profile 249, registration 157, service 183 |
| `version_comparison_ai/` (incl. md_report and sheet_changes subsets) | 10 218 (+ md_report 3 194 and sheet_changes 2 624 are included in this total) | 378 310 B in 70 files | jobs 885, stage_queue 532, sheet_match 644, packet 575, executor 334, whole_specifications 340, summary 303, prompt 264, settings 385 |
| `version_comparison_ai/md_report/` | 3 194 | 114 534 B in 7 files | runner 1240, stages 870, pdf 681, client 234, settings 169 |
| `version_comparison_ai/sheet_changes/` | 2 624 | 33 043 B in 3 files | series_ai 549, series_summary 399, run 287, validate 269, view 244, collect 471, single 197, report 104, schema 104 |

Per step (backend, approximate, downloaded files only):
- Upload and catalog: `store.py` 348 + `batches.py` 603 + `stamp.py` 204 + `profile.py` 249 ≈ 1400.
- Matrix (sheet identity): `lineage.py` 699 + `resolve.py` 573 + `registration.py` 157 + `jobs.py` (matrix part) ≈ 1500.
- Transition comparison: `engine.py` 1027 + `textdiff.py` 227 + `tiles.py` 289 + `status.py` 66 + `series.py` 301 + `service.py` 183 ≈ 2100 (plus jobs run loop).
- Luna: `sheet_match.py` 644 + `version_comparison_ai/settings.py` 385.
- Sheet AI («Изменения в листе»): `sheet_changes/*` 2624 + `packet.py` 575 + `prompt.py` 264 + `executor.py` 334.
- Series AI and queue: `series_ai.py` (in above) + `stage_queue.py` 532 + `jobs.py` (AI) 885.
- Specifications: `specification_run.py` 688 + `specification_compare.py` 724 + `spec.py` 571 + `whole_specifications.py` 340 + `specification_view.py` 143.
- MD summary: `series_summary.py` 399 + `summary.py` 303.
- PDF report: `md_report/*` 3194 (+ not-read `client_edit.py`).
- Run reports (Excel/HTML): `report.py` 544 (not wired).

### 6.4 Totals (approximate)

- UI: ≈ 4 240 lines (JS + CSS), of which the main page is 1 604.
- Backend HTTP: ≈ 1 130 lines.
- Backend services: ≈ 10 054 + 10 218 downloaded lines, plus ≈ 0.7 MB of not-read Python (estimate from bytes, ≈ 25 000–30 000 lines).
- Tests and fixtures: not counted (tests exist under `backend/tests/test_version_comparison_*.py`, `frontend/tests/version_comparison*.js`).

---

## 7. Unconfirmed items

- Exact payload sent to the Luna sheet-match model and its prompt file (not read).
- Exact payload and prompt for the legacy `records` AI method; its executor wiring (`version_comparison_ai/records.py`, `verify.py` not read).
- Upload size limit per PDF: no explicit limit found in read files.
- Whole specification pipeline internals beyond the docs and `specification_run.py` headers (`specification_prepare`, `specification_structure`, `specification_reconcile` not read).
- MD report stage prompts (`prompts/md_report_*.md` exist; not read) and the client discipline mapping (`client_edit.py` not read).
- Recovery of crashed series or runs beyond `recovery.py:31-63` (read) and `series.py` docstring.
- Which exact UI stage button text is shown for the sheet panel «Отмена» vs «Отменить задание» in every state (read from template; no runtime check).
- The `aiQueue` global (`ai_series_queue.json`) fields used by the strip (`version-comparison.js:938-947`, read; backend `series_ai.py` docstring).
- Whether any screen besides the unreachable `vc-ai-report` opens `version-comparison-ai.js` flows: grep found none (see §5), but a dynamic path is not excluded by grep alone.
- Runtime behaviour (live screens) was not checked; all statements are from source. Facts quoted by the task from the live system (counters, columns, values such as «V17 Изм.15 06.10.2026») were not re-verified.
