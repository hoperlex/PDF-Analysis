# COMPARE-MODULES-PLAN — «Сравнение стадий» and «Сравнение версий» to the original's functions and screens

Revision 2, 2026-10-27, planner session `pdf-analysis-4d`, after judging rounds 1 and 2 (`docs/program/compare/REVIEW-R1.md`:
3 BLOCKER, 22 MAJOR, 11 MINOR; `REVIEW-R2.md`: 4 BLOCKER, 15 MAJOR, 9 MINOR; dispositions in §10 and §11). Docs only: this plan changes no code,
contract, migration or test. Base: `integration/ar-close-1026` at `9e42c18a` (contract `1.8.0`, 95 paths / 107
operations / 314 schemas, migration head `0035_comparison_records`, product `0.9.0`). Branch `plan/compare-modules`.
The base moves while PW5 runs (at revision 2 the integration tip is `05f4584d` with `0036_cite_partition_v3`
merged, and the presets lane holds an uncommitted `0037`): every seal re-reads tip, head, contract version and
surface counts at dispatch and states them in its task file.

Evidence: `docs/program/compare/README.md` and the two inventories next to it (the original `SU10KAZ/PDF-proverka`
at `23f379fd`, and its live screens at `https://auditmanager.app` seen read-only on 2026-10-27). «The original»
means that commit and those screens. Where the original's live template and its design document
`docs/DOCUMENT_COMPARISON_CURRENT_STATE.md` («the original's chain document») differ, this plan says which one it
follows: `[live]` or `[doc]`.

## 0. Owner answers this plan rests on

Asked by direct poll on 2026-10-27 (≈16:05 and ≈16:20 +05). They are answers, not rulings; the integrator of the
wave records them in `OWNER_RULINGS_2026-09-17.md` and numbers them. Until then this plan cites them as `Q-CMP-1` …
`Q-CMP-5`.

| Id | Question (short) | Answer chosen |
| --- | --- | --- |
| Q-CMP-1 | Path for «Сравнение стадий»: the live V3 pipeline (a model reads both sets and writes «Было/Стало» cards) or the documented deterministic chain with an AI layer | «Цепочка + ИИ-слой»: deterministic sheet links and differences; the AI only classifies and summarises into «Было/Стало» cards that point at places in the sheets; an expert confirms each card; a report with grouping and Excel; screens after the original's four tabs |
| Q-CMP-2 | What a stage comparison compares | «Пары документов в проекте»: the project is the object; an expert pairs stage П documents with stage Р documents inside one project (suggested by designation/section); one П document may face several Р documents as one assembly («сборка»); a new stage-pair entity, no «object» entity |
| Q-CMP-3 | Scope of «Сравнение версий» | «Полный паритет»: projects table with seven steps, sheet matrix across all versions, deterministic per-sheet comparison in eight channels, overlay viewer, AI check of doubtful pairs, AI description of sheet changes, specification comparison, MD summary and PDF report |
| Q-CMP-4 | When; may sheet images go to a model | «До беты, с изображениями»: both modules are beta scope; crops of drawings may be sent to a model in the comparison AI layers (widens accepted risk `A-2` to drawing images; the integrator records it) |
| Q-CMP-5 | Upload for comparison | «PDF для сравнения»: plain PDFs in batches are admitted for comparison; such a version is marked as uploaded without a portal bundle and compared by its PDF text layer and raster; a section analysis on it still requires a portal bundle; a scan without text is compared as an image only |

Standing rules that also apply: `AGENTS.md` §4 (no LLM output as an expert decision, no AI change to raw
deterministic evidence, no job state only in memory, no path/file name/display number as identity, no silent
fallback, no deep imports across contexts); `R-29` (live spend per wave); `R-133` (a reply from a model other than
the pinned one is a typed refusal); `R-60` (expert writes need the expert role); `R-146ba` — it removed two
human-review labels for the beta and **kept** the label above the comparison summary: every comparison AI text in
this plan keeps the label that it is model output not confirmed by an engineer; subagent rule (execution lanes on
Sonnet, data gathering on Haiku).

## 1. What the user gets

### 1.1 «Сравнение версий» (menu item, group «Работа»)

**Tab «Проекты и этапы»** (one row per document set of the chosen project; its designation is shown as «шифр»):
counters «Все / Ждут действия / Идут / Ошибки / Готовы»; totals «N версий · M переходов»; «Поиск по шифру…»;
filters «Марка», «Порядок»; «Обновить» with «обновлено HH:MM:SS»; column sort ▲▼; the legend; the strip
«В загрузке, ещё не в списке проектов»; the launch queue strip «Очередь запуска» («готово N из M · пропущено K ·
ошибок E», «Пауза очереди», «Продолжить очередь», «Очистить», «Список», «✕»); the per-install AI queue
«Очередь «ИИ-описание изменений»». Table columns «Проект · следующий шаг» (with the next-step chip, a row click
opens «Сравнение листов», per-row «Сводка изменений (MD)»), «Версии», «1 Загрузка», «2 Разбор версий»
(«Повторить»), «3 Сопоставление листов» («Подготовить»), «4 ИИ-проверка сомнительных пар» («Проверить», «Пауза»,
«Продолжить»), «5 Сравнение соседних» («Запустить», «Пауза», «Продолжить», «Заново» with «Пересчитать» and the
cache note), «6 ИИ-описание изменений» («Запустить», «Из очереди», «Пауза», «Продолжить», «Заново» / «Описать
заново»), «7 Сводка и отчёт» («Сформировать PDF-отчёт», «Пауза», «Продолжить», «Заново» / «Сформировать заново»,
«PDF»), with the original's state words and counts per step; checkboxes per row and «выбрать все» per column for
steps 4–7, the selection bar «Запустить выбранные по очереди» / «Снять выбор»; every AI dialog shows the estimate and
the consent line. Button «Загрузить проект со всеми версиями».

**Upload** (`Q-CMP-5`). Single upload with a proposal: «Куда загрузить: Новый проект / Добавить версии в «…»»,
grouping by designation or name base, title input, ↑↓, «в проект…», a label per file, warnings, «Подтвердить
группировку и порядок». Multi-project batch «Загрузка нескольких проектов»: several folders or «Общая папка с
проектами», resumable chunked transfer with the original's limits (up to 10 000 files and 100 projects), «Остановить
загрузку», «Продолжить загрузку», «Удалить пакет», «После подготовки сравнить все соседние версии», a server queue
with «Пауза после текущего проекта», «Подтвердить порядок во всех проектах», «Подтвердить состав и порядок» per
project, «Исключить», «Повторить» and the ten status labels.

**Tab «Сравнение листов»** (one document set): header with ▶/▼, «· версий: N», «Применить сопоставления (N)» and
«Отменить правку» while a draft exists, «Сводка изменений (MD)», «Порядок версий», «Сформировать PDF-отчёт…»; side
selection A/B per version column (default: the last two versions; «Выберите две разные версии.»); blocks:
- «Сводка переходов»: one row per adjacent transition with progress, «Листов», «✓ ◐ ● ⚠», «Состав +N / −M», the
  deterministic verdict, «Открыть»; «Отменить» / «Продолжить» / «Досчитать»; «Сохранённая сводка для прежнего
  порядка версий.» after a reorder; a non-adjacent A/B pair is not compared («Пара собрана по цепочке… не
  сравнивалась»);
- «ИИ-описание изменений»: per transition progress and «Листов / Изм. / Вопр. / Ошибок / Проверить / Обращ. /
  tokens / time», fold with the «Проверить» list and added/removed single sheets, «Отменить», «Досчитать», «Убрать из
  очереди», «Повторить листы с ошибкой»;
- «Полные спецификации (СО)»: per transition method («полное сравнение» / «листовой ИИ»), spec sheets A/B,
  coverage, positions «изменено / +добавлено / −удалено / ?неясно», reason, «Открыть»;
- «Сводка MD и отчёт для заказчика»: report state, per-transition progress, usage, «Скачать PDF», «Скачать MD»,
  «Продолжить»;
- the sheet matrix «Лист \ версия» with «только изменения»; row heads with title and status badge; cells with
  thumbnails and flags «?» (medium confidence), «▤ группа», «✎» (manual), «ИИ» / «ИИ ?», «⧉» (duplicate), «скан»,
  «◫» / «⇉» (split across versions); unmatched cells «⁇ не сопоставлен» with «рядом», reason, «🌙 ИИ: вероятно стр.
  N», «кандидаты:» with «Связать», «Отметить, что этого листа в версии нет»; «∅ нет в версии»; «Несвязанные
  страницы»; drag-and-drop of thumbnails onto cells and «⤫ Отвязать в отдельную строку» as drafts; the bridge across
  a missing intermediate version; the «рядом» window with «вместе» zoom sync, «＋ − Вписать», «‹ лист / лист ›» and
  «Вывод ИИ по листу».

**Sheet viewer**: two modes «Наложение» and «Рядом» (A and B are the panes of «Рядом» and the under-layer of
«шторка», not modes); «шторка»; zoom/pan on tiles, «Вписать», Ctrl+wheel, double click; one visible layer checkbox
«места, где изменился цвет» (the other layers fixed: «Основное», «Светлые элементы», «Оформление линий» on;
«Перемещено (сдвиг — не изменение)», «В пределах допуска», «Шум» off; «Служебные зоны» on); toggles «сдвиги (не
изменение): N» and «оформление линий: N»; «рамки отличий»; «Совмещать блоки»; the channel strip «Проверено: … / Не
проверено: …»; «Отличия: N» with ← →; «Текст: N изменений» with «было → стало» and numbers highlighted; «Служебные
зоны и пометки» (with «Исчезновение предупреждения не подтверждает согласования.»); «Как сравнивалось» (transform,
dpi, tolerance, within-tolerance and noise counts, separated objects); «Только изменённые листы» and «‹ лист / лист
›»; the split-part note («Лист B — часть листа A») and the scan note; «Спецификация по позициям» for spec sheets;
the evidence banner from an AI description («Из ИИ-описания: …», «доказательство N из M», «Обзор всех / Один
фрагмент»). Side panel «Изменения в листе»: «Описать этот лист…» → estimate (sheets, images, image bytes, prompt
size, model) → «Подтверждаю передачу этого листа исполнителю» → «Передать и описать»; «Отменить задание»; the eleven
state labels («Не обработано» … «Строительных изменений не выявлено», «Описание устарело»); the changes with object,
«Было/стало», place, «Неясно», tiers «с изображения» / «не подтверждено», «Показать на чертеже»; «Требует
уточнения (N)»; «Заявлено проектировщиком в разрешении (N)»; «Скопировать», «MD листа», «Не включено в сводку»,
«Диагностика», «История (N)»; «По полной спецификации · только изменения этого листа». Every AI text carries the
unconfirmed-by-an-engineer label; a recorded (test) answer is labelled as such (our counterpart of «ТЕСТОВЫЙ ОТВЕТ
подменного исполнителя»).

**PDF report window** «Сформировать PDF-отчёт…»: source «сводка проекта» or «загрузить MD-файл»; the default kind
«Отчёт для заказчика · Изменения проектных решений» (one model call per transition over the MD summary's facts with
discipline priorities; a program check drops every point whose number, mark or direction the facts do not confirm;
one chronological table) `[live, since 2026-10-21]`; the analytic kind (analyst → verifier → composer) as the second
kind; reuse of finished parts; «Отменить», «Продолжить», «Пересобрать PDF» (no model call), «Удалить», «Исходный
MD», «Подготовить отчёт для заказчика» from an analytic report; per-transition progress tables (client and analytic
columns); report history and downloads.

### 1.2 «Сравнение стадий» (menu item, group «Работа»)

The pipeline is the chain of `Q-CMP-1`; its step strip (our own, the live strip's seven steps are V3's) is
«01 Связи листов», «02 Исключение одинакового текста», «03 Расхождения», «04 ИИ-ревизия», «05 Классификация и починка
связей», «06 Синтез», «07 Карточки», each with state and counts; run and quality banners; «Есть новые документы —
сравнение не обновлено» when a newer version arrived.

**Tab «1. Загрузка документации»** `[live]`: the catalog of stage pairs with «Проект / раздел», «OLD → NEW» («сборка
из N»), «Метод и модель» (for the chain: «Цепочка» plus the routed model of the AI layer), «Дата», «Изменения»
(PROJECT_CHANGE cards), «Требуют проверки» (REVIEW cards plus sheets without a pair), «Статус» (the chain run
state), «Открыть» / «Запустить сравнение», the row menu «⋯ → Перезапустить анализ пары»; the pair workbench: OLD/NEW
columns with drag-and-drop, counters «Сопоставлено / Требует проверки / Только OLD / Только NEW», «Сопоставить
автоматически» with auto-save, the assembly fan list with «Убрать из группы» and «Пересобрать», «Добавить проекты
справа для …», «Состав NEW относительно OLD» (неизвестна / полный / неполный), batch launch «Запустить анализ
выбранных (N)» and «Остановить очередь»; the upload dialog «Загрузить проекты» with the stage choice («Слева —
исходная редакция / Справа — новая редакция»), the candidate table («ZIP-комплект / папка проекта / PDF-проект»),
background minimise and the progress tray. Stage (П/Р) and section of a plain PDF are a stamp proposal that an
expert confirms (`Q-CMP-2`, `Q-CMP-5`).

**Tab «2. Сопоставление листов»**: `[live]` per-row page selects with «Пусто», confidence «Высокая / Ручная /
Проверить / Исправлено автоматически / Нет пары», filter «Все / Требуют проверки (N)», «Принять предложенные (N)»,
«Обработать», «Удалить текущую связь листов», «Добавить пустой лист слева/справа», «1:1», «Вписать», «Постраничный /
Непрерывный режим», «← Вернуться к той же строке», per-panel text search («Найти», ↑/↓, «Нет текста» for a scan);
`[doc]` «Оставить», «Изменить», «+ Добавить лист РД», «Удалить связь», «Синхронный вид», the five-row sheet map, the
thumbnail strip «Миниатюры» with Ctrl/Shift multi-select and drag reassignment under the two rules (sheets go to the
nearest FREE places below the target; only a CHANGED row becomes manual; a leftover sheet becomes an explicit
«без пары»); grey masks of proven-same text on both panels (one overlay for a fully matched block; after step 04 only
for accepted SAME/MOVED); the «↗» marker for text found on another sheet with «Добавить связь» / «Заменить связь»
(hints never change links by themselves); the history of automatic repairs with «Откатить».

**Tab «3. Изменения проекта»**: summary «Всего / Нужно проверить / Конфликты / Высокая важность»; sections in the
order of the chain document: high-level changes first, then «Детализация увеличена», material review, non-material
review (collapsed), «Служебные и структурные изменения» (collapsed), «Показать исходные текстовые различия»
(collapsed; columns «Лист П / Лист РД / Изменилось / Удалено / Добавлено»); cards «ID / Изменение / Было / Стало /
Источник (TEXT, TABLE, GRAPHIC) / Статус» with the evidence panel per side («Отсутствие объекта не доказано» where it
applies) and «Открыть в PDF ↗»; the «Экспертная оценка» toggle, per card «Принято» / «Не принято» (reason required for
a rejection, «Укажите причину каждого отказа.»), «Не сохранено: N», «Сохранить решения», «Решения сохранены».

**Tab «4. Отчёт»**: «Итоговый журнал изменений», «Подтверждено изменений: N», grouping «По шифру / По разделу / По
системе» that groups the table (the original only re-counts chips), exports «Excel ↓» (columns ID, Объект,
Изменение, Было, Стало, Источник, Решение эксперта — the original's legacy final report) and, subject to open item
O-2, «PDF ↓» and «HTML ↓».

### 1.3 Not copied, and deliberate deviations

Not copied (V3-only or dead in the original), listed so the cut is visible: the V3 semantic pipeline and its strip;
«Консолидатор», «Классический отчёт» zip, «Отчёт с ИИ-разбором», «Загрузить разбор» (IT-analysis xlsx); «Проверка по
источникам»; the «Смысловые блоки» mode of tab 2 («Все блоки / Блоки со связями / Блоки без связей», «Редактировать
связи»); the launch dialog modes «Быстро / Стандартно / По инженерным предметам», «Модель анализа», «Параллельные
запросы 5/10»; «Досчитать из сохранённого» with «Максимум новых участков»; «Свести дубли»; «Вид сравнения
Документ↔документ / Страница↔страница»; the catalog statuses «Заморожен · прогон V3 / запечатанный снимок»; the
dead `!pcUiEnabled` blocks; the 403 decisions stub; G1 routes without a caller; the version comparison's
backend-only Excel/HTML run reports and the unreachable run-level `vc-ai-report`; server paths and per-server
`current_id` (our project is the object, identity is an opaque id); the original's model names.

Deliberate deviations (owner may override at the end-of-plan poll):
- D-1 An automatic link repair never overrides an expert's link; it proposes, and the expert accepts (the original
  may change a manual link with HIGH proof). Reason: A-7, `AGENTS.md` §4.
- D-2 GRAPHIC evidence in stage cards is an addition beyond the original (its chain is text-only, G1 is
  backend-only): allowed only for 1↔1 links whose registration is reliable; otherwise the card says «графика не
  проверялась». TABLE evidence means text fragments of table rows, not a table extractor.
- D-3 AI runtime: a 429 is waited out and retried per `W53` (a 429 is a provably unprocessed call); quota and
  authorisation failures pause the job with a typed state; the original's model-driven context-request loop is not
  built — one request per item plus at most one technical retry.
- D-4 Grouping in tab 4 really groups (the original re-counts chips only); exports work (the original's are
  disabled).
- D-5 The comparison version order never changes the documents' ordinal that runs and finding carry-over use.

## 2. Gap: the original against this tree

| # | Function (original) | This tree at `9e42c18a` | Slice |
| --- | --- | --- | --- |
| G-01 | Plain-PDF upload, single with proposal | only portal bundles (`portal_bundle_required`, `src/auditmanager/ingest/bundle_archive.py:200`); one version per upload (`uploadDocumentVersion`) | CMP-INGEST-01 |
| G-02 | Multi-project resumable batch with a server queue | none | CMP-INGEST-02 |
| G-03 | Version order and labels («Порядок версий») | upload ordinal only | CMP-INGEST-01 |
| G-04 | Page profile (words with boxes, vector lines, stamp, sheet number/title, ink mask, scan flag) | run text layer (`prepared.text_layer`), crops (`src/auditmanager/analysis/geometry/render.py`) | CMP-PROFILE-01 |
| G-05 | Previews, thumbnails, tiles, overlay tiles | none on the server | CMP-PROFILE-01, CMP-VIEWER-01 |
| G-06 | Sheet matrix across versions (assignment, thresholds, groups, splits, duplicates, bridges, rules v1.2, drafts, undo) | proposals for two versions (`src/auditmanager/comparison/sheet_match_suggestions.py`), approved pairs (`comparison/pairing.py`, `approveSheetPairing`, `0035`) | CMP-MATRIX-01 |
| G-07 | Per-sheet comparison, eight channels, separation, block alignment, region classes, forcing reasons, cache | text-line diff (`src/auditmanager/comparison/raw_text.py`) | CMP-ENGINE-01 |
| G-08 | Series of transitions, parts coverage, permit phase, durable progress | none; `job` bound to `audit_run` (`src/auditmanager/jobs/repository.py:28`, `uq_job_run_id`) | CMP-WORK-01, CMP-SERIES-01 |
| G-09 | Overlay viewer | none | CMP-VIEWER-01 |
| G-10 | Overview read model and next-step rule of «Проекты и этапы» | none | CMP-VC-OVERVIEW-01 |
| G-11 | Launch queue (one step at a time, luna → series → ai (sheets → spec → MD) → report) and per-install AI queue | none | CMP-VC-QUEUE-01 |
| G-12 | AI check of doubtful pairs (images) | none | CMP-VC-AIPAIR-01 |
| G-13 | AI description per sheet and per series, single-sheet description, review list | recorded-only summary over approved pairs (`generateComparisonSummary`, `D-244`) | CMP-VC-AISHEET-01 |
| G-14 | Deterministic spec positions per run (`spec_positions` channel, «Спецификация по позициям») | Form-7 extractor of optimisation reads a run's text layer (`src/auditmanager/optimisation/specification.py`) — not usable for plain PDFs | CMP-VC-SPEC-01 (part A) |
| G-15 | AI whole-specification comparison «Полные спецификации (СО)» | none | CMP-VC-SPEC-01 (part B) |
| G-16 | MD summary; PDF report (client default, analytic) with its window | none | CMP-VC-REPORT-01 |
| G-17 | Screens of steps 4–7 and of the C2 blocks | none | CMP-VC-UI-02 |
| G-18 | Images to a model: several crops per call, from plain-PDF pages | one PNG per request, portal block crops only (`src/auditmanager/executors/image_input.py:34-53`, `pull.py:193-196`) | CMP-EXEC-IMAGES-01 |
| G-19 | AI spend of non-run work | `model_call.run_id` NOT NULL → `audit_run` and `ck_model_call_stage_id` (`db/migrations/versions/20260910_0002_pc01_schema.py:820-840`), `ck_provider_effect_stage_id` (`0014`), cost sums by run (`runs/repository.py` `_COST_SUMMARY`, `dashboard/repository.py` `_SPEND`, meter `analysis/text/cost.py`) | CMP-SPEND-01 |
| G-20 | Stage pairs of different documents, assemblies, workbench, upload | `mode=stage` compares two versions of ONE set | CMP-STAGE-PAIR-01 |
| G-21 | Stage sheet links (passports, suggestions, many-to-many, viewer, masks, hints) | none for different documents | CMP-STAGE-LINK-01 |
| G-22 | Text exclusion contract, differences | line diff per approved pair (`src/auditmanager/comparison/raw_text.py`, sealed by `raw_evidence_seal.py`) | CMP-STAGE-TEXT-01 |
| G-23 | AI reviewer, classifier, high-level synthesis | none | CMP-STAGE-AI-01 |
| G-24 | Deterministic link repair with undo and recompute | none | CMP-STAGE-REPAIR-01 |
| G-25 | Chain run orchestration, strip, batch launch, staleness | none | CMP-STAGE-RUN-01 |
| G-26 | Cards, verdicts, journal, grouping, exports | none | CMP-STAGE-REVIEW-01 |
| G-27 | Two menu items | one screen under a version (`web/src/shared/config/screen-registry.ts:161`, «Сравнение прогонов») | CMP-VC-UI-01, CMP-STAGE-PAIR-01 |

What stays: run comparison of one version (`W43-COMPARE`), finding match proposals and decision carry-over
(`carryOverDecision`) over `compareDocumentVersions`.

## 3. Architecture (fixed by `ADR-0025` in CMP-ADR-01, before CMP-SEAL-C0)

**A-1 Context.** New comparison logic lives in `src/auditmanager/comparison/` in subpackages created by the slices
that need them. Plain-PDF admission belongs to `ingest`/`documents`; the run-start refusal to `runs`; durable comparison work
to `comparison/work` (A-4) hosted by `workers`; model calls and images to `executors`. Other contexts only through their `public.py`; the
composition root adapts ports.

**A-2 Identities (opaque; never a path, file name or display number).** `DocumentUid` is the series (the «шифр» is
stamp metadata, confirmed, not identity). New identities (prefixes proposed, fixed in the ADR against the
identifier catalogue): `cvo_` version-order revision, `cpr_` page profile (content-keyed), `cmx_` matrix revision,
`cme_` manual matrix edit, `cak_` accepted AI link, `cser_` series, `csp_` sheet-pair result (content-keyed), `cbt_`
upload batch, `cq_` queue item, `stp_` stage pair, `sas_` assembly, `slk_` stage link revision, `crp_` link repair,
`crn_` chain run, `cai_` AI job, `ccd_` card, `cdv_` card verdict, `crt_` report. Every id has the catalogue format
`<prefix>_<ULID>` (`contracts/domain/v1/identifiers.json`) and is never parsed; a «content-keyed» row (profile,
sheet-pair result, card) has a ULID id plus a unique content-key digest column.

**A-3 Evidence layers.** Raw deterministic layers (profiles, algorithmic matrix, sheet-pair results, spec positions,
permit reconciliation, text fragments, exclusions, differences) are immutable rows or content-addressed blobs. AI
layers (pair-check answers, accepted AI links, sheet descriptions, reviewer decisions, classes, syntheses, report
text) are separate rows that reference raw ids and never rewrite them. The **effective matrix** is a read model:
algorithm, then accepted AI links (labelled «ИИ», never an expert act), then manual edits (manual wins). A UI
«final» layer is a read model over raw and AI rows. Every AI answer passes a strict validator (schema, existing ids
only, exact coverage, no invented numbers or designations); a failure keeps the deterministic layer visible and marks
the AI layer `failed`/`partial`.

**A-4 Durable work and spend (decided at revision 2, `R2-02`).** A Job of `jobs` is a Run in the schema
(`job.run_id NOT NULL`, `uq_job_run_id`), in the effect journals (`ck_provider_effect_stage_id`), in `model_call`
(`ck_model_call_stage_id`), in the frozen contract (`ExecutionQueueItem` / `ExecutionJournalEntry` require `run_id`)
and in about 180 code sites, so comparison work does **not** enter `job`. The comparison context gets its own durable
queue `src/auditmanager/comparison/work/**`: tables `comparison_work` and `comparison_work_attempt` copying the Lease
pattern (lease expiry, heartbeat, attempt count, pause, cancel, reclaim), and a spend journal
`comparison_model_call` with the columns and CHECKs of the `comparison_summary` precedent (migration `0035`:
`provider_mode`, `cost_basis`, `cost_micros`). The worker hosts it as a second loop the way `probe_runner` is hosted
(`src/auditmanager/workers/service.py`), counted against `AUDITMANAGER_WORKER_SLOTS`; `executor_task` gains an origin
`comparison_call` with a nullable `comparison_attempt_id` (and `runner_repository`'s live-attempt check an OR
branch); the one-active-run-per-connection check also counts active comparison AI work under the same advisory lock;
the `R-29` spend sum (`runs/repository.py` `_COST_SUMMARY`, `dashboard/repository.py` `_SPEND`) unions the two
journals. The «Очередь» screen and its contract stay run-only; comparison work shows its progress on its own screens.
No progress lives only in memory.

**A-5 Compute and dependencies.** Raster from `pypdfium2`, PNG via `Pillow` (both pinned, `pyproject.toml:46`, `:48`);
words with boxes and vector lines from `pdfplumber`; annotations from `pypdf`; PyMuPDF stays excluded (`OD-01`,
`pyproject.toml:30-32`). The original's engine, registration, profile, tiles and matrix use `numpy`, `cv2` and `fitz`.
The ADR decides, and the owner approves at the end-of-plan poll (open item O-1): `numpy` (BSD-3) — recommended; for
phase correlation, morphology and connected components either own `numpy` code (recommended) or `opencv-python-headless`
(Apache-2.0). The dependency is taken by CMP-SEAL-C0 (root lock slot) with licences recorded, before the profile and
engine lanes start; a dependency also moves `docs/program/P02_LOCK.json` and the `DIRECT` tuple of
`tests/contract/test_w55b_direct_pins.py`, and `uv lock` needs network. Results are cached by a key over both page
contents, parameters and `ALGO_VERSION`. Memory is the binding resource (the host: 11 GiB, about 3 GiB available;
an A1 page at 200 dpi is ≈ 31 Mpx): CMP-PROFILE-01 measures time and peak RSS per A1 page, CMP-ENGINE-01 per A1
pair, and both fix a downsample-for-registration rule, a per-job memory budget and a typed refusal above N Mpx per
page. There is **no eviction** of stored blobs in the beta (the storage boundary offers no delete; a delete from a
lane would be a dual write): previews and thumbnails are stored once per page, tiles are rendered on demand with a
bounded in-process cache, and a per-version page cap and a per-page pixel cap are enforced by refusal. The full-page
renderer is added to `src/auditmanager/analysis/geometry/render.py` and exported from `analysis/public.py`, under the
existing `PDFIUM_LOCK` (today's renderer clips crops only).

**A-6 AI calls.** Through «Исполнители» only. New work kinds (in `src/auditmanager/executors/model.py` `WORK_KINDS` /
`SERVES`, the contract schema `ExecutorWorkKind`, `web/src/entities/executor-connection/model/vocabulary.ts` and
`web/src/widgets/executor-routes/`): proposed `comparison_pair_check`, `comparison_sheet_changes`,
`comparison_spec`, `comparison_stage_review`, `comparison_report`; routed in «Назначения»; pinned model of the routed
connection (`R-133`); recorded mode for every test; the database constraint `ck_executor_route_work_kind`
(`0030_executor_connections.py:360`) is widened by SEAL-C2's migration. Images (`Q-CMP-4`): CMP-EXEC-IMAGES-01 extends the image channel
from «one portal-block PNG» to «up to N images per request» with an opaque crop reference (crop id, blob id, sha256,
size, media type) not bound to a portal block, on every served channel (HTTP direct/VPN/SSH tunnel, pull command,
local endpoint, MCP session, SSH command), counted in the estimate. The contract part (`RunnerImage` without a
required `portal_block_id`, `ClaimedExecutorTask.images.maxItems` > 1, the `executor_task` origin
`comparison_call`) is sealed by SEAL-C0; the one-image field `image_bytes` of `ModelRequest`
(`src/auditmanager/analysis/text/adapter.py:43`) is granted to CMP-EXEC-IMAGES-01 after PW5's SX lane has merged;
the runner tools (`codex_answer.py`, `claude_answer.py`, `mcp_bridge.py`) are updated by the same slice.
Compatibility: a runner already deployed on a remote host that does not support several images fails the task with
`image_input_unsupported` and never answers on a subset of the images. Every AI job shows an estimate (items, images,
image bytes, prompt size, model) and starts only after an explicit consent; live spend follows `R-29`.

**A-7 Expert acts.** Stage cards carry verdicts («Принято» / «Не принято» with a reason): append-only, keyed,
expert-role (`R-60`), audited. Manual matrix edits and stage links are expert acts with history. The version order
(«Порядок версий»): who may save it is decided in the ADR (open item O-3; the original: administrator). Version
comparison has no verdict in the original; its AI texts are labelled unconfirmed.

**A-8 Plain-PDF versions (`Q-CMP-5`).** `ingest` admits a plain PDF for comparison under a distinct manifest role
(not `source.document`), so the existing start-run check already refuses it (`runs/commands.py:385-395`,
`analysis_input_invalid`); CMP-INGEST-01 adds the reason value `comparison_only_version` and its Russian sentence
under that existing code (no 28th error code). The contract's `DocumentVersion` gains an upload-kind field so that
every existing screen can mark the version «загружено без пакета портала» and disable its run start
(CMP-VERSION-MARK-01). Upload transport: every comparison upload is chunked, 16 MiB per chunk, on the default proxy
location (body cap 32 MiB, `infra/deploy/proxy/nginx.conf:219`), so no proxy file changes; CMP-INGEST-01 measures a
10 000-chunk batch against the `limit_req` zones and STOPs if a zone refuses it. Resume and grouping identities are
opaque ids (`cbt_` batch, item id) plus the declared sha256 and size, never a path or file name; file names and
folders only feed the proposal the user confirms; a chunk has a database owner (a declared blob) before its bytes are
staged; an abandoned batch is swept by the existing temporaries sweep (`jobs/temporaries.py`); the 10 000-file and
100-project limits are typed refusals. The portal-bundle upload is unchanged. Passports and fragments of every
comparison input come from the page profile (stamp, words with boxes, vector lines); portal artefacts, when present,
are optional extra evidence. Stage (П/Р) and section of a plain PDF are a stamp proposal confirmed by an expert
through the existing classification operations. A scan gives no TEXT evidence and is compared as an image only.

**A-9 Stage pair binding.** A stage pair binds `DocumentUid`s (П side: one; Р side: one or an assembly of several);
each chain run pins exact version ids of every member; a newer version marks the run stale («Есть новые документы
…»); cards and verdicts belong to the run they were made on and carry over to a newer run only when the card's
evidence digest is equal; otherwise the old verdict is shown as stale.

**A-10 Cards.** A card is a Stage-5 aggregate of the chain document (class PROJECT_CHANGE / SERVICE_STRUCTURE /
REVIEW, category, title, its atomic evidence ids); its identity is a digest over its class and sorted evidence ids.
Verdicts are taken on PROJECT_CHANGE and REVIEW cards; SERVICE_STRUCTURE is one collapsed block without verdicts.
«Подтверждено изменений» counts accepted PROJECT_CHANGE and REVIEW cards. The Stage-5.3 high-level changes are a
read view over cards (sections of tab 3). «Шифр» and «Раздел» come from the documents deterministically; «Система» is
a classifier field from a closed list the validator enforces (the list is fixed in CMP-SEAL-C4).

**A-11 Screens and flags.** Menu entries in `web/src/shared/config/screen-registry.ts`, routes
`web/src/app/version-comparison/` and `web/src/app/stage-comparison/` (new); new FSD slices with names that do not
collide with the existing `_pages/stage-comparison` and `widgets/stage-comparison` (the version-scoped page and the
W43 run comparison): pages `web/src/_pages/version-compare/` and `web/src/_pages/stage-compare/`, entities
`web/src/entities/version-series/` and `web/src/entities/stage-pair/`, widgets named per slice in §4. The project is
chosen on the screen (no global object). Own styles only (`--am-*`, no UI library). Flags: SEAL-C0 adds
`AUDITMANAGER_COMPARISON_MODULES` (values `none`, `versions`, `versions,stages`) read by
`web/src/shared/config/server-env.ts` (the only place in `web/` that reads the environment) and by the API, passed by
`infra/deploy/compose.server.yml`; a module that is off has no menu entry and its operations answer
`dependency_unavailable`; its route still exists in the tree and in the journey manifest (the journey runs with both
modules on).

**A-12 One truth for sheet pairs of versions (decided at revision 2, `R2-12`).** In the new module the effective
matrix (A-3) is the only canonical store of «page X of version A ≙ page Y of version B». While the versions module is
on, the version-scoped screen stops offering `approveSheetPairing`, `withdrawSheetPairing` and
`generateComparisonSummary` (its existing approvals and summaries stay readable as history; `0035` rows are not
migrated); its heading «Сравнение версий» is renamed «Сравнение с другой версией: находки»; finding match proposals
and decision carry-over keep their own proposals from runs (`comparison/carryover.py`,
`comparison/finding_match_suggestions.py`), unchanged. These web edits belong to CMP-VC-UI-01.

## 4. Slices

Sizes: S ≤ 0.5 lane-day, M ≈ 1, L ≈ 1.5–2, XL ≈ 3. «Seal» = the slice of a wave that opens the wave: contract
schemas and operations (as sealed stubs), the migration of the wave, the generated client, `web/FRONTEND_LOCK.json`,
the contract-version bump, and (when granted) the dependency lock. Own paths are exact paths or `dir/**` from the
repository root; «(new)» marks a path that does not exist at the base.

### 4.0 Rules every slice follows (revision 2)

1. **Wiring (`R2-01`).** A sealed operation is a stub answering `503 dependency_unavailable` and listed in
   `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`) and
   `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_COLLECTIONS`). The
   lane that implements an operation owns, for that operation only: its adapter class(es) in
   `src/auditmanager/bootstrap/adapters.py`, its rows in `src/auditmanager/api/routers/ports.py` and its router file,
   and the removal of its rows from the two stub enumerators. Because `adapters.py` and the two enumerators are single
   files, the implementing lanes of a wave merge **in the order line of the wave**, each rebasing on the previous
   merge; a lane may develop in parallel and wait for its merge turn. `src/auditmanager/bootstrap/composition.py` and
   `src/auditmanager/workers/service.py` are edited only by the seal and by CMP-WORK-01.
2. **Enumerators (`R2-03`, `R2-23`, `R2-24`).** A slice that adds a route owns its entry in
   `tests/e2e/pc01/journey/manifest.json`, `web/src/shared/lib/routes.ts`, `web/src/shared/config/screen-registry.ts`
   and the route pins listed by `python3 tools/plan/pin_sweep.py route` (`web/tests/guards/screen-set.guard.test.ts`,
   `lazy-boundary.guard.test.ts`, `server-credential.guard.test.ts`, `dashboard-invalidation.guard.test.ts`,
   `web/tests/unit/shell/navigation.test.ts`). A slice that adds a module stylesheet owns its block in
   `web/tests/unit/styles/screens.ts`. A slice that adds to the cross-context entry
   `src/auditmanager/comparison/public.py` owns its appended names. These single files are edited in the wave's merge
   order. Each task file carries the «Enumerator ownership» block of `docs/templates/TASK_TEMPLATE.md`.
3. **Per-table family (`R2-06`).** A seal that adds tables owns, from its probe: `scripts/recovery/schema_coverage.py`,
   `grant_classification.py`, `product_purge.py`, `project_erase.py`, `blob_reference_audit.py`,
   `infra/deploy/apply-grants.sh`, `src/auditmanager/access/references.py` (actor columns) and the tests that pin
   table counts and inventories (`tests/integration/db/test_application_role_grants.py`,
   `tests/integration/recovery/test_grant_classification.py`, `test_schema_shape.py`,
   `test_schema_invariant_inventory.py`, `test_migration_lifecycle.py`, `test_downgrade_chain_round_trip.py`,
   `test_product_purge.py`, `test_project_erase.py`, `test_synthetic_drill_compare.py`,
   `test_synthetic_drill_seed.py`, wherever the probe finds them). Every new table is reachable from `project` by
   foreign keys (profiles and results are per-version rows; there are no cross-project rows), so project erase keeps
   its closure.
4. **Contract version and surface (`R2-07`).** Each seal is one additive minor bump: SEAL-C0 `1.9.0`, SEAL-C1 `1.10.0`,
   SEAL-C2 `1.11.0`, SEAL-C3 `1.12.0`, SEAL-C4 `1.13.0` (or the next free minor at dispatch). It owns the families of
   `python3 tools/plan/pin_sweep.py contract-version` and `… reseal`, the infra surface pins
   (`infra/deploy/proxy/nginx.conf`, `infra/deploy/serve.py`, `infra/deploy/README.md`),
   `web/src/shared/api/authorization.ts` and `web/src/app/bff/v1/[...path]/route.ts`. An `infra/**` change puts the wave
   in the full-gate class of `AGENTS.md` §8; under `R-135` that gate is the one before beta.
5. **No new error code** unless no existing code fits; a new reason under an existing code is the default (`R2-08`).
6. **Identity and AI rules** of A-2, A-3, A-12 hold in every slice; downstream outputs that an AI decision shaped are
   marked (a transition whose pairs depend on an AI link is marked in the series verdict, the MD summary and the
   report; masked raw differences stay listed in «Показать исходные текстовые различия» with their AI class) (`R2-28`).

### Wave C0 — foundation (after PW5's SX and PR lanes merge)

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-ADR-01 | `docs/architecture/adr/ADR-0025-comparison-modules.md` (new) + `docs/architecture/ADR_INDEX.md` line: A-1…A-12, identities, the comparison queue, work kinds, images, dependencies (O-1), PDF writer (O-2), order rights (O-3); judged | S | the two ADR files |
| CMP-SEAL-C0 | contract `1.9.0`: plain-PDF chunked upload (single, batch), upload batches, `DocumentVersion` upload kind, version-order revisions, profile/preview/thumbnail/tile reads, runner image references (A-6), `executor_task` origin; migration (head + 1) with `comparison_work`, `comparison_work_attempt`, `comparison_model_call`, upload batches, order revisions, profiles; the flag `AUDITMANAGER_COMPARISON_MODULES`; dependency lock per O-1; rules 3–4 of §4.0 | L | seal hotspots, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `tests/contract/test_w55b_direct_pins.py`, `infra/deploy/compose.server.yml`, `web/src/shared/config/server-env.ts` |
| CMP-WORK-01 | comparison durable queue (A-4): claim, lease, heartbeat, reclaim, pause, cancel, slot accounting, the worker loop hook; mutation proofs | M | `src/auditmanager/comparison/work/**` (new), `src/auditmanager/workers/service.py` (the hook) |
| CMP-SPEND-01 | `comparison_model_call` journal, cost meter for comparison AI, the `R-29` spend union, the connection limit counting comparison AI work, the `executor_task` origin path | M | `src/auditmanager/comparison/spend/**` (new), `src/auditmanager/runs/repository.py` (`_COST_SUMMARY` only), `src/auditmanager/dashboard/repository.py` (`_SPEND` only), `src/auditmanager/jobs/repository.py` (connection check only), `src/auditmanager/executors/runner_repository.py` (live-attempt OR branch only) |
| CMP-EXEC-IMAGES-01 | N images per request with opaque crop references on every channel (A-6), compatibility refusal, estimate counts | M | `src/auditmanager/executors/image_input.py`, `src/auditmanager/executors/pull.py`, `src/auditmanager/executors/http_adapter.py`, `src/auditmanager/executors/ssh_adapter.py`, `src/auditmanager/executors/ssh_tunnel_adapter.py`, `src/auditmanager/analysis/text/adapter.py` (`ModelRequest` only, after SX), `tools/executor-runner/**` |
| CMP-FIXTURES-01 | synthetic comparison corpus with answer keys (§6), `/Annots` support in the fixture PDF writer | M | `tools/fixtures/comparison/**` (new), `tools/fixtures/ar_corpus/pdfwrite.py` (annotations only), `fixtures/comparison/**` (new) |
| CMP-INGEST-01 | plain-PDF admission (single) over chunks, stamp reading (designation, «Изм.», date, stage and section proposals), grouping proposal confirmed by the user, version-order proposal and «Порядок версий» (A-7, D-5), reason `comparison_only_version` | L | `src/auditmanager/ingest/comparison_pdf/**` (new), `src/auditmanager/documents/**`, `src/auditmanager/runs/commands.py` (the reason value only), `web/src/shared/api/catalog-message.ts` (one sentence) |
| CMP-INGEST-02 | multi-project resumable batch over chunks, server batch queue as comparison work, limits, statuses | M | `src/auditmanager/ingest/comparison_batch/**` (new) |
| CMP-PROFILE-01 | page profiles (per-version rows), stored previews and thumbnails, on-demand tiles, full-page renderer, measurements (A-5) | L | `src/auditmanager/comparison/profile/**` (new), `src/auditmanager/analysis/geometry/render.py` (full-page function only, after SX), `src/auditmanager/analysis/public.py` (one export, after SX) |
| CMP-VERSION-MARK-01 | the «загружено без пакета портала» mark and the disabled run start on the existing version screens | M | `web/src/_pages/version-detail/**`, `web/src/widgets/version-list/**`, `web/src/widgets/version-history/**`, `web/src/widgets/document-list/**`, `web/src/widgets/run-list/**`, `web/src/entities/document-version/**` |

Order inside C0: ADR → SEAL-C0 → (WORK ∥ EXEC-IMAGES ∥ FIXTURES ∥ VERSION-MARK ∥ INGEST-01 ∥ PROFILE) → SPEND (needs
WORK) → INGEST-02 (needs WORK). Merge order for the wiring files: WORK, SPEND, EXEC-IMAGES, INGEST-01, INGEST-02,
PROFILE, VERSION-MARK, FIXTURES.

### Wave C1 — version comparison core

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-SEAL-C1 | contract `1.10.0`/migration: matrix, manual edits, accepted AI links (table only), effective-matrix read, series, sheet-pair results, pair tiles, overview | L | seal |
| CMP-MATRIX-01 | algorithmic matrix (max-weight assignment, thresholds 0.55/0.35/0.20, match rules v1.2: resolve, package, direct, permit, page number, group), table-sheet groups «▤», duplicates «⧉», splits «◫ ⇉» with parts coverage, bridges across a missing version, absent/unmatched with candidates; manual drafts (drag-and-drop, «⤫», «листа нет», «Связать») applied in a batch, undo; effective-matrix read model (A-3); staleness by signature | L | `src/auditmanager/comparison/matrix/**` (new) |
| CMP-ENGINE-01 | per-sheet comparison: registration B→A on a downsampled raster; channels verbatim `geometry`, `color`, `text`, `text_coverage`, `zones`, `annotations`, `warnings`, `spec_positions`; overlay separation (stamps, warnings, QR); block alignment (`aligned_blocks`); region classes incl. `text_moved`, `block_moved`, `shifted`; layers incl. light fill, within tolerance, noise; text changes with numbers; «Совпадает» only when every applicable channel is `checked`; `FORCING_REASONS`; statuses `same`, `same_zones_changed`, `different`, `needs_review`, `added`, `removed`, `unmatched`; cache; peak-RSS measurement per A1 pair | XL | `src/auditmanager/comparison/engine/**` (new) |
| CMP-VIEWER-01 | tiles of a pair (overlay/A/B, levels, reduction keeps the max of masks, `align_blocks`) behind an interface fixed in SEAL-C1; the viewer widget per §1.1 | L | `src/auditmanager/comparison/tiles/**` (new), `web/src/widgets/comparison-viewer/**` (new) |
| CMP-SERIES-01 | series of adjacent transitions as comparison work; post-phases parts coverage and permit reconciliation (`declared_and_found`, `declared_no_diff`, `diff_not_declared`, `needs_review`); transition summary and verdict strings; pause/resume/cancel/«Заново»/«Досчитать»; staleness after reorder; non-adjacent pairs not compared | M | `src/auditmanager/comparison/series/**` (new) |
| CMP-VC-OVERVIEW-01 | overview read model: per-set state of the seven steps, next-step chip, counters, totals, pending uploads | M | `src/auditmanager/comparison/overview/**` (new) |
| CMP-VC-UI-01 | screens «Проекты и этапы» (columns 1–3, 5) and «Сравнение листов» (transitions, matrix, «Порядок версий», upload dialogs), route, menu entry, A-12 edits of the version-scoped screen | L | `web/src/_pages/version-compare/**` (new), `web/src/app/version-comparison/**` (new), `web/src/widgets/version-series/**` (new), `web/src/widgets/comparison-upload/**` (new), `web/src/entities/version-series/**` (new), `web/src/widgets/version-comparison/**`, `web/src/_pages/stage-comparison/**` (heading only) |

Order inside C1: SEAL-C1 → (ENGINE ∥ MATRIX ∥ VIEWER, developed on fixtures) → SERIES → OVERVIEW → VC-UI-01. Merge
order: MATRIX, ENGINE, VIEWER, SERIES, OVERVIEW, VC-UI-01.

### Wave C2 — version comparison AI, specifications, reports, queue

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-SEAL-C2 | contract `1.11.0`/migration: AI jobs (estimate, consent, cancel, retry failed sheets), answers, descriptions, spec reports, MD/PDF reports, launch queue; work kinds (A-6) incl. widening `ck_executor_route_work_kind`; PDF writer per O-2 | L | seal, `src/auditmanager/executors/model.py` (work kinds only), `web/src/entities/executor-connection/model/vocabulary.ts`, `web/src/widgets/executor-routes/**` (work-kind labels only) |
| CMP-VC-AIPAIR-01 | doubtful-pair check with images (sheet and candidates); accepted only with high confidence and an agreeing reverse question, never for a sheet inside a multi-sheet spec or a B already linked; accepted answers become accepted-AI-link rows; manual edits win; hints «🌙», «ИИ ?»; counts «вопросов · пар · подсказок · против»; content-keyed answers never re-sent | M | `src/auditmanager/comparison/ai_pairs/**` (new) |
| CMP-VC-AISHEET-01 | per-sheet description (packets of tables, places, shifts with crops and words; tiers text/image/unverified; «Требует уточнения»; declared items), per-series run and the per-install AI queue, single-sheet description of added/removed sheets, «Проверить» list, retry of failed sheets, MD per sheet, history | L | `src/auditmanager/comparison/ai_sheets/**` (new) |
| CMP-VC-SPEC-01 | part A deterministic: ГОСТ 21.110 tables from profile words and vector lines, positions across pages, `spec_positions` input, «Спецификация по позициям»; part B AI: whole-specification extraction per version (`comparison_spec`), coverage and quote checks, order-independent comparison, methods «полное сравнение» / «листовой ИИ». The Form-7 extractor is not used | L | `src/auditmanager/comparison/specification/**` (new) |
| CMP-VC-QUEUE-01 | launch queue as comparison work: one step at a time across sets, luna → series → ai (sheets → spec → MD) → report; pause/resume/clear/remove | M | `src/auditmanager/comparison/queue/**` (new) |
| CMP-VC-REPORT-01 | deterministic MD summary (same bytes for same data, «Реестр»); PDF report: client kind (default) and analytic kind, program checks of facts, PDF written by a program (O-2), the window functions of §1.1 | L | `src/auditmanager/comparison/report/**` (new) |
| CMP-VC-UI-02 | the C2 screens of §1.1: steps 4/6/7 cells and dialogs, selection bar, queue strips, «ИИ-описание изменений», «Полные спецификации (СО)», «Сводка MD и отчёт для заказчика», the PDF report window, AI flags and hints in matrix cells, the side panel «Изменения в листе» and the evidence banner | L | `web/src/_pages/version-compare/**`, `web/src/widgets/version-series/**`, `web/src/widgets/comparison-report/**` (new), `web/src/widgets/comparison-viewer/**` (side panel), `web/src/entities/version-series/**` |

Order: SEAL-C2 → (AIPAIR ∥ AISHEET ∥ SPEC) → QUEUE → REPORT → VC-UI-02 (merge order the same).

### Wave C3 — stage comparison, deterministic part (SEAL-C3 starts after the C2 judge's FIX lane has merged)

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-SEAL-C3 | contract `1.12.0`/migration: stage pairs, assemblies, link revisions, hints, fragments, exclusions, differences, chain runs | L | seal |
| CMP-STAGE-PAIR-01 | stage pairs (A-9), suggestion by section and designation, expert confirmation, assemblies, composition completeness, stage upload dialog (plain PDF or bundles, stage choice), tab 1 catalog and workbench, route, menu entry | L | `src/auditmanager/comparison/stage/**` (new), `web/src/_pages/stage-compare/**` (new), `web/src/app/stage-comparison/**` (new), `web/src/widgets/stage-pair-catalog/**` (new), `web/src/entities/stage-pair/**` (new) |
| CMP-STAGE-LINK-01 | sheet passports from profiles (A-8), automatic suggestions (type + корпус + этаж/кровля/уровень, then корпус 4 / этаж 4 / уровень 3 / тип 2 / Sheet 1 / порядок 1; a conflict in корпус/этаж/тип is never overridden), many-to-many links as append-only revisions, explicit «без пары», tab 2 per §1.2 with the two move rules, two-panel viewer (imports `comparison-viewer`) with per-panel search | L | `src/auditmanager/comparison/stage_links/**` (new), `web/src/widgets/stage-sheet-map/**` (new), `web/src/_pages/stage-compare/**` (the tab mount only) |
| CMP-STAGE-TEXT-01 | fragments, exclusion contract, second pass «↗», recommendation-only hints, deterministic differences with box anchors, staleness after a link change, grey masks, raw-differences table; GRAPHIC regions from CMP-ENGINE-01 for 1↔1 links only (D-2) | M | `src/auditmanager/comparison/stage_text/**` (new) |

Order: SEAL-C3 → (PAIR ∥ LINK) → TEXT; merge order PAIR, LINK, TEXT. C3 lanes may run beside C2 lanes only after
SEAL-C3 has merged, which follows the C2 FIX.

### Wave C4 — stage comparison AI, repair, review; closing

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-SEAL-C4 | contract `1.13.0`/migration: AI reviewer rows, classes, syntheses, repairs, cards, verdicts, journal, exports; work kind `comparison_stage_review`; the closed «Система» list | L | seal |
| CMP-STAGE-AI-01 | reviewer (SAME / MOVED / CHANGED / REMOVED / ADDED / UNCERTAIN over existing fragment ids, ≤ 40 items per chunk, all-or-nothing per group, high confidence for SAME/MOVED; an AI SAME never removes a raw difference row), classifier (PROJECT_CHANGE / SERVICE_STRUCTURE / REVIEW, category, title, «Система»), high-level synthesis; crops of GRAPHIC evidence (D-2) | L | `src/auditmanager/comparison/stage_ai/**` (new) |
| CMP-STAGE-REPAIR-01 | deterministic purpose precheck, one repair cycle per run (unique exact title or mutual-best fuzzy ≥ 0.94, swaps and cycles), never over an expert link (D-1), repair records, «Откатить» with recompute of steps 02–07, supersession by a later manual edit | M | `src/auditmanager/comparison/stage_repair/**` (new) |
| CMP-STAGE-RUN-01 | chain run as comparison work: steps 01–07, single and batch launch, consent for the AI steps, cancel/resume, banners, staleness | M | `src/auditmanager/comparison/stage_run/**` (new) |
| CMP-STAGE-REVIEW-01 | tab 3 per §1.2 (cards A-10, verdicts, carry-over, sections), tab 4 journal with grouping and exports: Excel by a generic sheet writer exported from `exports/__init__.py`; PDF/HTML per O-2 | L | `src/auditmanager/comparison/stage_review/**` (new), `src/auditmanager/exports/**` (generic sheet writer), `web/src/widgets/stage-changes/**` (new), `web/src/_pages/stage-compare/**` (the tab mounts only) |
| CMP-JOURNEY-01 | the browser walk of both modules on the synthetic corpus: upload, matrix, viewer, recorded AI with images, verdicts, exports (the manifest entries already exist, rule 2) | M | `tests/e2e/pc01/journey/**` (walk steps only) |
| CMP-CLOSE-01 | release note, `CURRENT_STATE.md`, debt rows, flags on, whole-suite measurement, handoff for the gate | S | docs |

Order: SEAL-C4 → STAGE-AI → (REPAIR ∥ RUN) → REVIEW → JOURNEY → CLOSE; merge order the same.

Census: 35 slices — C0 10, C1 7, C2 7, C3 4, C4 7 (five seals included).

## 5. Order, hotspots, parallelism

- **Entry (`R2-05`).** C0 starts when PW5's `SECTION-CATEGORY-OCR-01` (SX: `analysis/public.py`,
  `analysis/text/adapter.py`) and `ANALYSIS-PRESETS-01` (PR: migration `0037`, `executors/public.py`,
  `executors/preset_*`) have merged. SEAL-C0 takes the then-current head + 1 (`0038` or later).
- **Seals are serial**: C0 → C1 → C2 → (C2 FIX) → C3 → C4. Each seal holds the contract and the migration head from its
  start to its merge; a wave's FIX lane that needs a migration or contract change takes the slot before the next seal.
- **Wiring files** follow §4.0 rule 1: one writer at a time, in the wave's merge order.
- **Executor files**: CMP-EXEC-IMAGES-01 owns the executor files it lists in C0; SPEND-01 the one-line changes it lists;
  SEAL-C2 the work kinds in `executors/model.py`. The executor workstream (`EXEC-*`) is told before C0 starts.
- **Shared web files**: §4.0 rule 2. `web/src/widgets/comparison-viewer/**` belongs to CMP-VIEWER-01 in C1 and to
  CMP-VC-UI-02 in C2 (side panel); CMP-STAGE-LINK-01 imports it without editing it. The page files of
  `_pages/version-compare` and `_pages/stage-compare` take later mounts one slice at a time. Global styles are not
  touched.
- **Never**: `origin/main` (`AGENTS.md` §6), root locks outside the slot, a second writer in a worktree.

## 6. Verification

Per slice (light acceptance `R-70`): the slice's unit and integration directories on a private database and object
store; contract tests minus the `D-220` files; web Vitest/tsc/eslint for touched web paths; the two static guards of
§4.0 rule 2 (journey conformance, contrast census) for any slice that adds a route or a stylesheet; a mutation proof
per guard — a refusal that must fire; a raw layer an AI layer must not change; an AI SAME that must not remove a raw
difference row; an effective matrix where manual must beat AI; a cache key that must change with `ALGO_VERSION`; a
consent that must precede a model call; a lease reclaim that must not double-spend; a verdict that must not carry
over to a changed evidence digest; a page above the pixel cap that must be refused, not rendered. Recorded model
responses only, including multi-image requests.

Fixtures (CMP-FIXTURES-01): a synthetic corpus generated in-tree on `tools/fixtures/ar_corpus/pdfwrite.py` extended
with `/Annots`: a set with 5 versions (moved text, changed numbers, added/removed sheets, changed graphics, stamp
changes, a permit table, a scan page, a split sheet, a duplicate, a spec table, a PDF annotation), and a П/Р pair with
a 3-document assembly — A4 pages at low dpi, each with an answer key the tests assert, not a re-captured output.

Per wave end: one judge, then a FIX lane (`R-124`…`R-127`); the whole `tests/integration` (D-245 is fixed on the tip;
no split needed); `next build`. Before beta: the complete gate (`D-205`, a host with disk) and CMP-JOURNEY-01.

Live AI: off by default; one measured live check per AI slice only within `R-29` and with the owner's key in the
session.

## 7. Estimate and beta

Method (`R2-18`): lane execution is not the bottleneck (measured spans: AR-V3-DECISIONS-01 2.0 h,
COMPARE-PERSISTED-SUMMARY-01 3.0 h, W59-VERSION-COMPARE-01 1.8 h, EXEC-PULL-01 1.6 h, EXEC-PAR-QUEUE-01 0.7 h; about 30
lanes merged on 2026-10-26/27); the serial chain is. Critical-path steps from §4's order lines plus judge and FIX per
wave: C0 ≈ 7, C1 ≈ 7, C2 ≈ 7, C3 ≈ 5, C4 ≈ 8 — about 34 steps at 2–3 h per lane plus about 1 h of merge and light
acceptance, i.e. 100–135 h, plus the XL engine (+6 h): **≈ 11–15 working days of ≈ 10 h (P50 ≈ 13)** after the entry.
If C0 starts on 2026-10-29: code-complete **P50 ≈ 2026-11-16, P80 ≈ 2026-11-20**; with the complete gate (≤ 1 day)
and the B1–B12 repeat including the comparison screens (≈ 1 day), **beta P50 ≈ 2026-11-18, P80 ≈ 2026-11-25**
(the forecast of 2026-10-27 without comparison was P50 05.11, P80 13.11). Not measured: the engine on real A1 sheets,
memory on the stand, the image channel on deployed runners, and the number of FIX rounds.

## 8. Risks, stop conditions, rollback

- **Memory and disk**: A-5 measurements, caps by refusal, no eviction; a lane stops below 1.4 GiB free disk; the
  engine refuses a page above the pixel cap with a typed state.
- **Raster failures**: a failed render is `needs_review` with `RENDER_FAILED`, never «Совпадает».
- **Model cost**: estimate and consent before every AI job; abort on the first identity refusal; retries per D-3;
  spend in `comparison_model_call` counted under `R-29`.
- **Vision**: images only through the extended channel; the accepted-risk record (`A-2` widened) is written before
  SEAL-C2 merges.
- **Upload abuse**: chunks under the default body cap; plain PDFs through the existing envelope checks (size, page
  cap, encryption, structure); ZIP members under the archive rules of `ingest`; batch limits as typed refusals.
- **Stop**: a seal's probe shows a pin the plan did not grant → STOP and report; a lane needs a hotspot it does not
  own → STOP; an AI layer would have to modify a raw row → STOP; a dependency O-1/O-2 did not approve → STOP; a
  `limit_req` zone refuses the chunked batch → STOP (proxy grant needed).
- **Rollback**: `AUDITMANAGER_COMPARISON_MODULES` (A-11); a wave that cannot finish leaves its module off and the
  version-scoped screen as it was.

## 9. Open items (to the owner by one poll at the end of judging, or to the ADR)

- O-1 Dependencies: `numpy` (recommended) and own code vs `opencv-python-headless`.
- O-2 PDF writer for the version report and the stage journal: a new dependency (e.g. `reportlab`, BSD; its own
  fonts need a Cyrillic TTF with a licence that allows embedding) or an in-tree writer promoted from
  `tools/fixtures/ar_corpus` (≈ 900 lines with `ttfsubset.py`, plus a full Cyrillic font; `tools/` is not in the API
  image); HTML export needs nothing.
- O-3 Who may save «Порядок версий» and edit the matrix: expert, administrator, or both.
- O-4 (decided at revision 2 as A-12; kept here for the owner's information.)
- O-5 The deviations D-1…D-5 (§1.3).
- O-6 Executor routes for the new work kinds on the stand (an operator act after the code).

## 10. Disposition of judging round 1

| Finding | Where it is addressed |
| --- | --- |
| R1-01 | CMP-VC-UI-02 (C2), §4 order |
| R1-02 | CMP-EXEC-IMAGES-01, A-6, G-18 |
| R1-03 | CMP-VC-OVERVIEW-01, CMP-VC-QUEUE-01, G-10, G-11 |
| R1-04 | A-5, O-1, CMP-SEAL-C0 takes the lock |
| R1-05 | CMP-ENGINE-01 result |
| R1-06 | CMP-SERIES-01 (permit phase), CMP-VC-AISHEET-01 (declared items), §1.1 |
| R1-07 | CMP-MATRIX-01 result, §1.1 |
| R1-08 | A-3 effective matrix, CMP-VC-AIPAIR-01 |
| R1-09 | CMP-VC-SPEC-01 parts A and B, G-14, G-15 |
| R1-10 | §1.1 PDF report window, CMP-VC-REPORT-01, G-16 |
| R1-11 | §1.1 side panel and blocks, CMP-VC-AISHEET-01 |
| R1-12 | §1.1 viewer (corrected), CMP-VIEWER-01 |
| R1-13 | §1.1 upload, CMP-INGEST-01/02 |
| R1-14 | §1.2 tab 1, CMP-STAGE-PAIR-01 |
| R1-15 | §1.2 tab 2 with `[live]`/`[doc]` tags and the two move rules |
| R1-16 | A-8, CMP-INGEST-01 (stage/section proposal), CMP-STAGE-LINK-01 |
| R1-17 | CMP-STAGE-REPAIR-01 in C4, D-1 |
| R1-18 | §1.2 tab 2/3, CMP-STAGE-TEXT-01 |
| R1-19 | D-2, CMP-STAGE-TEXT-01 |
| R1-20 | A-9, A-10, §1.2 tab 3 |
| R1-21 | CMP-STAGE-RUN-01, §1.2 strip |
| R1-22 | §1.3 not copied |
| R1-23 | A-4, A-6, CMP-SPEND-01 (was CMP-JOBS-01 in revision 1), CMP-SEAL-C2 |
| R1-24 | per-wave order lines in §4 |
| R1-25 | A-9 |
| R1-26 | §1.1 «Проекты и этапы» |
| R1-27 | CMP-SERIES-01, §1.1 |
| R1-28 | §0 standing rules |
| R1-29 | §4 census, §7 |
| R1-30 | §1.2 tab 4, CMP-STAGE-REVIEW-01, O-2 |
| R1-31 | A-8, CMP-INGEST-01 (`runs/commands.py`) |
| R1-32 | CMP-STAGE-PAIR-01 |
| R1-33 | §1.2 tab 3 |
| R1-34 | D-3 |
| R1-35 | D-5, CMP-INGEST-01 |
| R1-36 | §1.2 tab 1 |

## 11. Disposition of judging round 2

| Finding | Where it is addressed |
| --- | --- |
| R2-01 | §4.0 rule 1 (each lane wires its operations, serial merge order per wave); CMP-SEAL-C4 added |
| R2-02 | A-4 decided: comparison-local queue and spend journal; CMP-WORK-01 and CMP-SPEND-01 replace CMP-JOBS-01 |
| R2-03 | §4.0 rule 2 (manifest, route pins, `screens.ts` owned by the slice that adds the route or stylesheet) |
| R2-04 | A-6 (contract part in SEAL-C0, `adapter.py` grant after SX, runner tools, compatibility refusal); CMP-EXEC-IMAGES-01 paths |
| R2-05 | §5 entry: SX and PR merged; base restated at dispatch (§0 note) |
| R2-06 | §4.0 rule 3; seals re-sized L; per-version rows only |
| R2-07 | §4.0 rule 4 (one minor bump per seal, families and infra pins granted) |
| R2-08 | A-8: reason `comparison_only_version` under `analysis_input_invalid`; §4.0 rule 5 |
| R2-09 | A-8: 16 MiB chunks on the default location; §8 stop on a `limit_req` refusal |
| R2-10 | A-11 new FSD names (`_pages/version-compare`, `_pages/stage-compare`, new widgets/entities); mount grants in §4 |
| R2-11 | CMP-VIEWER-01 owns `comparison/tiles/**` |
| R2-12 | A-12 decided |
| R2-13 | A-11 flag `AUDITMANAGER_COMPARISON_MODULES` in SEAL-C0 with its grants |
| R2-14 | A-5: no eviction, caps by refusal, on-demand tiles |
| R2-15 | A-8 upload-kind field; CMP-VERSION-MARK-01 |
| R2-16 | CMP-STAGE-REVIEW-01 owns a generic sheet writer in `src/auditmanager/exports/**` |
| R2-17 | A-5 measurements and caps; CMP-ENGINE-01 peak RSS; fixtures at A4 low dpi |
| R2-18 | §7 rewritten with the critical-path method and measured spans |
| R2-19 | A-8 resume and grouping identities, chunk ownership, sweep, typed limits |
| R2-20 | §2 citations corrected; A-6 names `ck_executor_route_work_kind`; A-5 full-page renderer |
| R2-21 | A-2 ULID ids plus content-key columns |
| R2-22 | §6: D-245 fixed, no split |
| R2-23 | §4 own paths rewritten as exact paths or `dir/**`; enumerator blocks per task file (§4.0 rule 2) |
| R2-24 | §4.0 rule 2 (`comparison/public.py` appends), entities granted to UI slices |
| R2-25 | CMP-FIXTURES-01 (`/Annots`); O-2 font and image notes |
| R2-26 | §5 serial seals with the FIX slot before the next seal; SEAL-C3 after the C2 FIX |
| R2-27 | SEAL-C0 grants `P02_LOCK.json` and `test_w55b_direct_pins.py`; A-5 |
| R2-28 | §4.0 rule 6; §6 mutation proof «AI SAME never removes a raw difference row» |
