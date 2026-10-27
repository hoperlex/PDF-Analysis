# COMPARE-MODULES-PLAN — «Сравнение стадий» and «Сравнение версий» to the original's functions and screens

Revision 1, 2026-10-27, planner session `pdf-analysis-4d`, after judging round 1 (`docs/program/compare/REVIEW-R1.md`:
3 BLOCKER, 22 MAJOR, 11 MINOR; the disposition of every finding is §10). Docs only: this plan changes no code,
contract, migration or test. Base: `integration/ar-close-1026` at `9e42c18a` (contract `1.8.0`, 95 paths / 107
operations / 314 schemas, migration head `0035_comparison_records`, product `0.9.0`). Branch `plan/compare-modules`.

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
| G-06 | Sheet matrix across versions (assignment, thresholds, groups, splits, duplicates, bridges, rules v1.2, drafts, undo) | proposals for two versions (`src/auditmanager/comparison/pairing.py`), approved pairs (`approveSheetPairing`, `0035`) | CMP-MATRIX-01 |
| G-07 | Per-sheet comparison, eight channels, separation, block alignment, region classes, forcing reasons, cache | text-line diff (`src/auditmanager/comparison/raw_text.py`) | CMP-ENGINE-01 |
| G-08 | Series of transitions, parts coverage, permit phase, durable progress | none; `job` bound to `audit_run` (`src/auditmanager/jobs/repository.py:28`) | CMP-JOBS-01, CMP-SERIES-01 |
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
| G-19 | AI spend of non-run work | `model_call.run_id` NOT NULL → `audit_run` (`db/migrations/versions/20260910_0002_pc01_schema.py:820-823`), cost queries by run (`src/auditmanager/jobs/repository.py:211`, `:266-343`) | CMP-JOBS-01 |
| G-20 | Stage pairs of different documents, assemblies, workbench, upload | `mode=stage` compares two versions of ONE set | CMP-STAGE-PAIR-01 |
| G-21 | Stage sheet links (passports, suggestions, many-to-many, viewer, masks, hints) | none for different documents | CMP-STAGE-LINK-01 |
| G-22 | Text exclusion contract, differences | line diff per approved pair (`src/auditmanager/comparison/raw_evidence_seal.py`) | CMP-STAGE-TEXT-01 |
| G-23 | AI reviewer, classifier, high-level synthesis | none | CMP-STAGE-AI-01 |
| G-24 | Deterministic link repair with undo and recompute | none | CMP-STAGE-REPAIR-01 |
| G-25 | Chain run orchestration, strip, batch launch, staleness | none | CMP-STAGE-RUN-01 |
| G-26 | Cards, verdicts, journal, grouping, exports | none | CMP-STAGE-REVIEW-01 |
| G-27 | Two menu items | one screen under a version (`web/src/shared/config/screen-registry.ts:161`, «Сравнение прогонов») | CMP-VC-UI-01, CMP-STAGE-PAIR-01 |

What stays: run comparison of one version (`W43-COMPARE`), finding match proposals and decision carry-over
(`carryOverDecision`) over `compareDocumentVersions`.

## 3. Architecture (fixed by `ADR-0025` in CMP-ADR-01, before CMP-SEAL-C0)

**A-1 Context.** New comparison logic lives in `src/auditmanager/comparison/` in subpackages created by the slices
that need them. Plain-PDF admission belongs to `ingest`/`documents`; the run-start refusal to `runs`; durable work
to `jobs`/`workers`; model calls and images to `executors`. Other contexts only through their `public.py`; the
composition root adapts ports.

**A-2 Identities (opaque; never a path, file name or display number).** `DocumentUid` is the series (the «шифр» is
stamp metadata, confirmed, not identity). New identities (prefixes proposed, fixed in the ADR against the
identifier catalogue): `cvo_` version-order revision, `cpr_` page profile (content-keyed), `cmx_` matrix revision,
`cme_` manual matrix edit, `cak_` accepted AI link, `cser_` series, `csp_` sheet-pair result (content-keyed), `cbt_`
upload batch, `cq_` queue item, `stp_` stage pair, `sas_` assembly, `slk_` stage link revision, `crp_` link repair,
`crn_` chain run, `cai_` AI job, `ccd_` card, `cdv_` card verdict, `crt_` report.

**A-3 Evidence layers.** Raw deterministic layers (profiles, algorithmic matrix, sheet-pair results, spec positions,
permit reconciliation, text fragments, exclusions, differences) are immutable rows or content-addressed blobs. AI
layers (pair-check answers, accepted AI links, sheet descriptions, reviewer decisions, classes, syntheses, report
text) are separate rows that reference raw ids and never rewrite them. The **effective matrix** is a read model:
algorithm, then accepted AI links (labelled «ИИ», never an expert act), then manual edits (manual wins). A UI
«final» layer is a read model over raw and AI rows. Every AI answer passes a strict validator (schema, existing ids
only, exact coverage, no invented numbers or designations); a failure keeps the deterministic layer visible and marks
the AI layer `failed`/`partial`.

**A-4 Durable work and spend.** `jobs` gains a typed subject (today a Job is a Run, `job.run_id`): comparison
subjects (profile build, matrix build, series, sheet-pair batch, upload batch, queue item, AI job, report build,
chain run) with the same lease, heartbeat, reclaim, pause/resume/cancel and wake-up, claimed by the same worker loop,
counted against `AUDITMANAGER_WORKER_SLOTS`. `model_call` and the cost meter gain the same typed subject so that
comparison AI spend is recorded and summed under `R-29`; the Attempt context reaches the executor adapters for a
comparison job as it does for a Run. This is a risk path (durable state, `W48`): the ADR compares it with a
comparison-local queue on the same Lease pattern and records the choice; CMP-JOBS-01 carries mutation proofs for
lease, reclaim, cancellation and spend.

**A-5 Compute and dependencies.** Raster from `pypdfium2`, PNG via `Pillow` (both pinned, `pyproject.toml:46`, `:48`);
words with boxes and vector lines from `pdfplumber`; annotations from `pypdf`; PyMuPDF stays excluded (`OD-01`,
`pyproject.toml:30-32`). The original's engine, registration, profile, tiles and matrix use `numpy`, `cv2` and `fitz`.
The ADR decides, and the owner approves at the end-of-plan poll (open item O-1): `numpy` (BSD-3) — recommended; for
phase correlation, morphology and connected components either own `numpy` code (recommended) or `opencv-python-headless`
(Apache-2.0). The dependency is taken by CMP-SEAL-C0 (root lock slot) with licences recorded, before the profile and
engine lanes start. CMP-PROFILE-01 measures time and memory per A1 page at 200 dpi before any batch. Results are
cached by a key over both page contents, parameters and `ALGO_VERSION`.

**A-6 AI calls.** Through «Исполнители» only. New work kinds (in `src/auditmanager/executors/model.py` `WORK_KINDS` /
`SERVES`, the contract schema `ExecutorWorkKind`, `web/src/entities/executor-connection/model/vocabulary.ts` and
`web/src/widgets/executor-routes/`): proposed `comparison_pair_check`, `comparison_sheet_changes`,
`comparison_spec`, `comparison_stage_review`, `comparison_report`; routed in «Назначения»; pinned model of the routed
connection (`R-133`); recorded mode for every test. Images (`Q-CMP-4`): CMP-EXEC-IMAGES-01 extends the image channel
from «one portal-block PNG» to «up to N images per request» with an opaque crop reference (crop id, blob id, sha256,
size, media type) not bound to a portal block, on every served channel (HTTP direct/VPN/SSH tunnel, pull command,
local endpoint, MCP session, SSH command), counted in the estimate. Every AI job shows an estimate (items, images,
image bytes, prompt size, model) and starts only after an explicit consent; live spend follows `R-29`.

**A-7 Expert acts.** Stage cards carry verdicts («Принято» / «Не принято» with a reason): append-only, keyed,
expert-role (`R-60`), audited. Manual matrix edits and stage links are expert acts with history. The version order
(«Порядок версий»): who may save it is decided in the ADR (open item O-3; the original: administrator). Version
comparison has no verdict in the original; its AI texts are labelled unconfirmed.

**A-8 Plain-PDF versions (`Q-CMP-5`).** `ingest` admits a plain PDF for comparison under a distinct manifest role
(not `source.document`), so the existing start-run check refuses it; `runs/commands.py` adds a typed refusal code
naming the reason (no silent fallback). The portal-bundle upload is unchanged. Passports and fragments of every
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
a classifier field from a closed list the validator enforces (the list is fixed in CMP-SEAL-C3).

**A-11 Screens.** Menu entries in `web/src/shared/config/screen-registry.ts`, routes `web/src/app/version-comparison/`
and `web/src/app/stage-comparison/`; the project is chosen on the screen (no global object). The version-scoped
screen stays for run comparison and finding carry-over. Own styles only (`--am-*`, no UI library). A feature flag per
module (a server setting read by the screen registry) hides an unfinished module on a stand.

## 4. Slices

Sizes: S ≤ 0.5 lane-day, M ≈ 1, L ≈ 1.5–2, XL ≈ 3 (judgment from PW2b/PW4 lane pace). «Seal» = the one slice of a
wave that owns the contract, the migration head, the generated client, `web/FRONTEND_LOCK.json`, the composition root
and (when granted) the root dependency lock for that wave; the other lanes of the wave start after it merges. Each
seal first runs a disposable apply-and-run probe of its contract/migration change and grants from its output every
pin it moves (`docs/program/CONTRACT_PIN_REGISTRY.md`). Allowed paths below are the slice's own; a seal may add a
one-line grant where a file belongs to another owner.

### Wave C0 — foundation (after PW5's `ANALYSIS-PRESETS-01` merges)

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-ADR-01 | `docs/architecture/adr/ADR-0025-comparison-modules.md` + `ADR_INDEX.md` line: A-1…A-11, identities, job/spend subject choice, work kinds, images, dependencies (O-1), PDF writer (O-2), order rights (O-3); judged | S | the ADR files |
| CMP-SEAL-C0 | contract: plain-PDF single and batch upload, upload batches, version-order revisions, profile/preview/thumbnail/tile reads, job and spend subject, new error codes (run-start refusal); migration (head + 1); dependency lock change per O-1; generated client | L | seal hotspots, `pyproject.toml`/lock (per O-1) |
| CMP-JOBS-01 | typed job subject; claim/lease/reclaim/pause/cancel for comparison subjects; slot accounting; `model_call` and cost meter subject; Attempt context for executor adapters; mutation proofs | L | `src/auditmanager/jobs/**`, `src/auditmanager/workers/**` |
| CMP-EXEC-IMAGES-01 | N images per request, opaque crop references, all served channels, estimate counts, caps; coordinated with the executor workstream owner | M | `src/auditmanager/executors/**`, `tools/executor-runner/**` |
| CMP-INGEST-01 | plain-PDF admission (single), stamp reading (designation, «Изм.», date, stage, section proposal), grouping proposal confirmed by the user, version-order proposal and «Порядок версий» (A-7, D-5), run-start refusal | L | `src/auditmanager/ingest/**`, `src/auditmanager/documents/**`, `src/auditmanager/runs/commands.py` (refusal only) |
| CMP-INGEST-02 | multi-project resumable chunked batch upload, server batch queue as a job subject, limits, statuses, «После подготовки сравнить все соседние версии» | M | `src/auditmanager/ingest/batch/**` (new) |
| CMP-PROFILE-01 | page profiles, previews, thumbnails, tiles in the blob store, content-keyed; time/memory measurement per A1 page at 200 dpi; byte cap and eviction | L | `src/auditmanager/comparison/profile/**`; rendering through `src/auditmanager/analysis/public.py` (one-line export granted if missing) |

Order inside C0: ADR → SEAL-C0 → (JOBS ∥ EXEC-IMAGES ∥ INGEST-01 ∥ PROFILE) → INGEST-02 (needs JOBS).

### Wave C1 — version comparison core

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-SEAL-C1 | contract/migration: matrix, manual edits, effective matrix read, series, sheet-pair results, tiles of a pair, overview | M | seal |
| CMP-MATRIX-01 | algorithmic matrix (max-weight assignment, thresholds 0.55/0.35/0.20, match rules v1.2: resolve, package, direct, permit, page number, group), table-sheet groups «▤», duplicates «⧉», splits «◫ ⇉» with parts coverage, bridges across a missing version, absent/unmatched with candidates; manual drafts (drag-and-drop, «⤫», «листа нет», «Связать» from candidates and hints) applied in a batch, undo; effective-matrix read model (A-3); staleness by signature | L | `comparison/matrix/**` |
| CMP-ENGINE-01 | per-sheet comparison: registration B→A; channels verbatim `geometry`, `color`, `text`, `text_coverage`, `zones`, `annotations`, `warnings`, `spec_positions`; overlay separation (stamps, warnings, QR); block alignment (`aligned_blocks`, tile `align_blocks`); region classes incl. `text_moved`, `block_moved`, `shifted`; layers incl. light fill, within tolerance, noise; text changes with numbers; «Совпадает» only when every applicable channel is `checked`; `FORCING_REASONS`; statuses `same`, `same_zones_changed`, `different`, `needs_review`, `added`, `removed`, `unmatched`; cache | XL | `comparison/engine/**` |
| CMP-SERIES-01 | series of adjacent transitions as durable subjects; per-run post-phases: parts coverage, permit reconciliation (`declared_and_found`, `declared_no_diff`, `diff_not_declared`, `needs_review`); transition summary and verdict strings; pause/resume/cancel/«Заново»/«Досчитать»; staleness after reorder; non-adjacent pairs not compared | M | `comparison/series/**` |
| CMP-VC-OVERVIEW-01 | overview read model: per-set state of the seven steps, next-step chip, counters, totals, pending uploads | M | `comparison/overview/**` |
| CMP-VIEWER-01 | tiles (overlay/A/B, levels, reduction keeps max of masks), the viewer widget per §1.1 | L | `web/src/widgets/comparison-viewer/**` (new), tile reads in `comparison/engine/tiles*` |
| CMP-VC-UI-01 | screens «Проекты и этапы» (C1 columns 1–3, 5) and «Сравнение листов» (transitions, matrix, «Порядок версий», upload dialogs), menu entry, flag | L | `web/src/_pages/version-comparison/**` (new), `web/src/widgets/version-series/**` (new), `web/src/widgets/comparison-upload/**` (new), `web/src/app/version-comparison/**` (new), one entry in `screen-registry.ts` |

Order inside C1: SEAL-C1 → (ENGINE ∥ MATRIX ∥ VIEWER on recorded fixtures) → SERIES → OVERVIEW → VC-UI-01.

### Wave C2 — version comparison AI, specifications, reports, queue

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-SEAL-C2 | contract/migration: AI jobs (estimate, consent, cancel, retry failed sheets), answers, descriptions, spec reports, MD/PDF reports, queue; work kinds (A-6); PDF writer dependency per O-2 | M | seal, `src/auditmanager/executors/model.py` (work kinds), the executor web vocabulary and routes widget (one-line grants) |
| CMP-VC-AIPAIR-01 | doubtful-pair check with images (sheet and candidates), accepted only with high confidence and an agreeing reverse question, never for a sheet inside a multi-sheet spec or a B already linked; manual edits win; hints «🌙» and «ИИ ?»; counts «вопросов · пар · подсказок · против»; content-keyed answers never re-sent | M | `comparison/ai_pairs/**` |
| CMP-VC-AISHEET-01 | per-sheet description (packets of tables, places, shifts with crops and words; tiers text/image/unverified; «Требует уточнения»; declared items from the permit phase), per-series run and AI queue, single-sheet description of added/removed sheets, «Проверить» review list, retry of failed sheets, MD per sheet, history | L | `comparison/ai_sheets/**` |
| CMP-VC-SPEC-01 | part A deterministic: ГОСТ 21.110 specification tables from profile words and vector lines, positions compared across pages, `spec_positions` channel input, «Спецификация по позициям»; part B AI: whole-specification extraction per version (`comparison_spec`), coverage and quote checks, order-independent comparison, methods «полное сравнение» / «листовой ИИ». The Form-7 extractor is not used (it needs a run text layer). | L | `comparison/specification/**` |
| CMP-VC-QUEUE-01 | launch queue as a durable subject: one step at a time across sets, order luna → series → ai (sheets → spec → MD) → report; pause/resume/clear/remove; per-install AI queue | M | `comparison/queue/**` |
| CMP-VC-REPORT-01 | deterministic MD summary (same bytes for same data, «Реестр» categories); PDF report: client kind (default) and analytic kind, program checks of facts, PDF written by a program (O-2), the window functions of §1.1 | L | `comparison/report/**` |
| CMP-VC-UI-02 | the C2 screens: step 4/6/7 cells and dialogs (estimate + consent), selection bar, queue strips, «ИИ-описание изменений», «Полные спецификации (СО)», «Сводка MD и отчёт для заказчика», the PDF report window, AI flags and hints in matrix cells, the viewer side panel «Изменения в листе» and the evidence banner | L | `web/src/_pages/version-comparison/**`, `web/src/widgets/version-series/**`, `web/src/widgets/comparison-report/**` (new), `web/src/widgets/comparison-viewer/**` (side panel) |

Order inside C2: SEAL-C2 → (AIPAIR ∥ AISHEET ∥ SPEC) → QUEUE → REPORT → VC-UI-02.

### Wave C3 — stage comparison, deterministic part

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-SEAL-C3 | contract/migration: stage pairs, assemblies, link revisions, hints, fragments, exclusions, differences, chain runs, AI rows, repairs, cards, verdicts, journal, exports; the closed «Система» list | M | seal |
| CMP-STAGE-PAIR-01 | stage pairs (A-9), suggestion by section and designation, expert confirmation, assemblies, composition completeness, stage upload dialog (plain PDF or bundles, stage choice), tab 1 catalog and workbench, menu entry and flag | L | `comparison/stage/**`, `web/src/_pages/stage-comparison/**`, `web/src/app/stage-comparison/**` (new), one entry in `screen-registry.ts` |
| CMP-STAGE-LINK-01 | sheet passports from profiles (A-8), automatic suggestions (type + корпус + этаж/кровля/уровень, then the scale корпус 4 / этаж 4 / уровень 3 / тип 2 / Sheet 1 / порядок 1; a conflict in корпус/этаж/тип is never overridden), many-to-many links as append-only revisions, explicit «без пары», tab 2 per §1.2 with the two move rules, two-panel synchronised viewer (reuses `comparison-viewer`) with per-panel search | L | `comparison/stage_links/**`, `web/src/widgets/stage-sheet-map/**` (new) |
| CMP-STAGE-TEXT-01 | fragments, exclusion contract (the barrier every later step checks), second pass «найдено на другом листе» with «↗», recommendation-only hints, deterministic differences changed/removed/added with box anchors, staleness after a link change, grey masks, the raw-differences table; GRAPHIC regions from CMP-ENGINE-01 for 1↔1 links only (D-2) | M | `comparison/stage_text/**` |

Order inside C3: SEAL-C3 → (PAIR ∥ LINK) → TEXT. C3 may run beside C2 when the two seals are serialised.

### Wave C4 — stage comparison AI, repair, review; closing

| Slice | Result | Size | Own paths |
| --- | --- | --- | --- |
| CMP-STAGE-AI-01 | reviewer (SAME / MOVED / CHANGED / REMOVED / ADDED / UNCERTAIN over existing fragment ids, ≤ 40 items per chunk, all-or-nothing per group, high confidence for SAME/MOVED), classifier (PROJECT_CHANGE / SERVICE_STRUCTURE / REVIEW, category, title, «Система»), high-level synthesis; crops of GRAPHIC evidence (D-2) | L | `comparison/stage_ai/**` |
| CMP-STAGE-REPAIR-01 | deterministic purpose precheck (`PAIR_OK` / `PAIR_REVIEW_REQUIRED`), one repair cycle per run (unique exact title or mutual-best fuzzy ≥ 0.94, swaps and cycles), never over an expert link (D-1), repair records with before/after, «Откатить» with recompute of steps 02–07, supersession by a later manual edit | M | `comparison/stage_repair/**` |
| CMP-STAGE-RUN-01 | chain run orchestration as a durable subject: steps 01–07, single and batch launch, consent for the AI steps, cancel/resume, banners, staleness | M | `comparison/stage_run/**` |
| CMP-STAGE-REVIEW-01 | tab 3 per §1.2 (cards A-10, verdicts, carry-over, sections), tab 4 journal with grouping and exports (Excel through `src/auditmanager/exports/` public API; PDF/HTML per O-2) | L | `comparison/stage_review/**`, `web/src/widgets/stage-changes/**` (new) |
| CMP-JOURNEY-01 | browser journey of both modules on synthetic fixtures: upload, matrix, viewer, recorded AI with images, verdicts, exports | M | journey files under `tests/e2e/` named by the slice |
| CMP-CLOSE-01 | release note, CURRENT_STATE, debt rows, flags on, whole-suite measurement in halves (`D-245`), handoff for the gate | S | docs |

Order inside C4: STAGE-AI → STAGE-REPAIR ∥ STAGE-RUN → STAGE-REVIEW → JOURNEY → CLOSE. (C4 has no seal: SEAL-C3 sealed
its operations.)

Census: 31 slices — C0 7, C1 7, C2 7, C3 4, C4 6 (the four seals included).

## 5. Order, hotspots, parallelism

- **Entry.** C0 starts when PW5's `ANALYSIS-PRESETS-01` has merged (integrator `pdf-analysis-cc`, 2026-10-27: AR-A
  owns migration `0036`, PR the next). Each seal takes the then-current head + 1.
- **Seals are serial across waves** (C0 → C1 → C2 → C3); C3's lanes may run beside C2's lanes after SEAL-C3 merges.
- **Composition root** belongs to the seal of the wave; a lane needing a port wiring lists it for the seal.
- **Executor files**: CMP-EXEC-IMAGES-01 owns `src/auditmanager/executors/**` and `tools/executor-runner/**` in C0;
  in C2 only SEAL-C2 touches `executors/model.py`. The executor workstream (`EXEC-*`) is told before C0 starts.
- **Shared web files**: `screen-registry.ts` gets one entry from CMP-VC-UI-01 (C1) and one from CMP-STAGE-PAIR-01
  (C3). `web/src/widgets/comparison-viewer/**` belongs to CMP-VIEWER-01 in C1 and to CMP-VC-UI-02 in C2 (side panel);
  CMP-STAGE-LINK-01 imports it without editing it. Global styles are not touched.
- **Never**: `origin/main` (AGENTS §6), root locks outside the slot, a second writer in a worktree.

## 6. Verification

Per slice (light acceptance `R-70`): the slice's unit and integration directories on a private database and object
store; contract tests minus the `D-220` files; web Vitest/tsc/eslint for touched web paths; a mutation proof per guard
(a refusal that must fire, a raw layer an AI layer must not change, an effective matrix where manual must beat AI, a
cache key that must change with `ALGO_VERSION`, a consent that must precede a model call, a lease reclaim that must
not double-spend, a verdict that must not carry over to a changed evidence digest); recorded model responses only,
including multi-image requests.

Fixtures: a synthetic comparison corpus generated in-tree (`tools/fixtures/comparison/**`, new, built on
`tools/fixtures/ar_corpus` PDF writer): a set with 5 versions (moved text, changed numbers, added/removed sheets,
changed graphics, stamp changes, a permit table, a scan page, a split sheet, a duplicate, a spec table), and a П/Р pair
with a 3-document assembly — each with an answer key the tests assert, not a re-captured output.

Per wave end: one judge, then a FIX lane (`R-124`…`R-127`); whole `tests/integration` in two halves under one hour
each (`D-245`); `next build`. Before beta: the complete gate (`D-205`, a host with disk) and CMP-JOURNEY-01.

Live AI: off by default; one measured live check per AI slice only within `R-29` and with the owner's key in the
session.

## 7. Estimate and beta

Measured basis: PW4 (seven lanes incl. a contract and a migration) went from order to integration branch in ≈ 13 h on
2026-10-27; PW2b in ≈ 1 day. This plan: 31 slices in five waves, with internal ordering (§4) that serialises about
half of each wave. Judgment: **≈ 2 working days per wave**, **9–11 working days** of execution after PW5. If C0 starts
on 2026-10-29: code-complete P50 ≈ 2026-11-11, P80 ≈ 2026-11-18. The beta forecast of 2026-10-27 (P50 05.11, P80
13.11) moves to **P50 ≈ 2026-11-18, P80 ≈ 2026-11-27**. Not measured: the engine (XL), the job/spend subject (risk
path), the image channel change, the host disk (renders of 12 versions × 100 sheets), and how many FIX rounds the
judges trigger.

## 8. Risks, stop conditions, rollback

- **Disk/memory**: previews and tiles are cached blobs with a byte cap and eviction measured by CMP-PROFILE-01 before
  any batch over 50 pages; a lane stops below 1.4 GiB free.
- **Raster cost**: the engine runs in the worker under the slot count; a failed render is `needs_review` with
  `RENDER_FAILED`, never «Совпадает».
- **Model cost**: estimate and consent before every AI job; a job aborts on the first identity refusal; retries per
  D-3.
- **Vision**: images only through the extended channel; the accepted-risk record (`A-2` widened) is written before
  CMP-SEAL-C2 merges.
- **Upload abuse**: plain PDFs go through the existing envelope checks (size, page cap, encryption, structure) and
  batch limits; ZIP members obey the archive rules of `ingest`.
- **Stop**: a seal's probe shows a pin the plan did not grant → STOP and report; a lane needs a hotspot it does not own
  → STOP; an AI layer would have to modify a raw row → STOP; a dependency is needed that O-1/O-2 did not approve → STOP.
- **Rollback**: each module is behind its flag; a wave that cannot finish leaves its flag off and the existing
  version-scoped comparison untouched.

## 9. Open items (to the owner by one poll at the end of judging, or to the ADR)

- O-1 Dependencies: `numpy` (recommended) and own code vs `opencv-python-headless`.
- O-2 PDF writer for the version report and the stage journal (no pinned library writes PDF today): a new dependency
  (e.g. `reportlab`, BSD) or an in-tree writer promoted from `tools/fixtures/ar_corpus`; HTML export is free.
- O-3 Who may save «Порядок версий» and edit the matrix: expert, administrator, or both.
- O-4 Whether the approved sheet pairs of `0035` migrate into matrix edits or stay as history.
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
| R1-23 | A-4, A-6, CMP-JOBS-01, CMP-SEAL-C2 |
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
