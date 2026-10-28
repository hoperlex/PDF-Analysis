# COMPARE-MODULES-PLAN — review round 1 of 3 (completeness and fidelity)

Plan reviewed: `docs/program/dispatch/COMPARE-MODULES-PLAN.md` revision 0 at `63449a71` (branch
`plan/compare-modules`, worktree `.local/worktrees/plan-compare-modules`). Read-only review, 2026-10-27.

Evidence notation:
- `orig:` = the original at `23f379fd`, downloaded under
  `/tmp/claude-0/-root-projects-PDF-Analysis/754ae11c-a0de-41ac-9ac2-1b49a23f1a22/scratchpad/orig-src/files/`
  (`orig:F/` = `frontend/`, `orig:B/` = `backend/app/services/`, `orig:R/` = `backend/app/api/routers/`,
  `orig:docs/` = `docs/`).
- `tree:` = this repository at the plan worktree.
- `plan:` = the plan file, by line number.

Checked against the original's code (projects table, matrix page, viewer, «Изменения в листе» panel, PDF
report window, batch uploader, stage queue, run phases, status/channels, md_report runner/client, the
stage tab templates in `index.html`, `project-change-ui.js`, the documented chain in
`DOCUMENT_COMPARISON_CURRENT_STATE.md`, `sheet_matching.py`, `text_ai_reviewer.py`), not only against the
inventories.

---

## BLOCKER

**R1-01 · BLOCKER · §4 wave C2, §5** — No slice owns the web screens of the C2 functions.
CMP-VC-UI-01 (C1) owns `web/src/_pages/version-comparison/**` and `web/src/widgets/version-series/**`, but the
C2 operations exist only after CMP-SEAL-C2; the C2 lanes have backend paths only (AIPAIR `comparison/ai_pairs/**`,
SPEC `comparison/specification/**`, REPORT `comparison/report/**`; AISHEET gets only «the viewer side panel»). So
nobody builds: step 4/6/7 cell actions and dialogs (estimate + consent) in «Проекты и этапы»; the
«ИИ-описание изменений» transitions block; «Полные спецификации (СО)» block; «Сводка MD и отчёт для заказчика»
block; the «Сформировать PDF-отчёт…» window; MD downloads; AI hints/flags in matrix cells; the AI queue strip.
Evidence: plan:207-222; orig:F/static/js/version-comparison.js:76-79, 159-333, 388-405; orig:F/static/js/version-comparison-projects.js:477-528, 558-605; orig:F/static/js/version-comparison-md-report.js:10-84.
Fix: add `CMP-VC-UI-02` (L) to C2, after the C2 backend lanes, owning `web/src/_pages/version-comparison/**`,
`web/src/widgets/version-series/**` and a new `web/src/widgets/comparison-report/**`, with the list above as its
result; or give each C2 lane a disjoint web path. Add it to §5 and re-estimate (§7).

**R1-02 · BLOCKER · §3 A-6, §4 CMP-SEAL-C2, §8 «Vision», `Q-CMP-4`** — The image channel the plan relies on
cannot carry comparison images. `EXEC-IMAGE-CHANNELS-01` sends exactly one PNG per request, and the PNG must be a
portal block crop (`portal_block_id`). The original sends several images per call: crops of A and B for each
candidate place in «Изменения в листе», the sheet plus candidate pages in the doubtful-pair check, all rendered
from PDF pages that have no portal block (plain PDFs, `Q-CMP-5`). The plan's only executors hotspot is `kinds.py`.
Evidence: tree:src/auditmanager/executors/image_input.py:34-53 (`len(images) != 1` → refusal; descriptor keys must be
`{blob_id, portal_block_id, sha256, size_bytes, media_type}`); tree:src/auditmanager/executors/pull.py:193-196 («one image
is allowed per runner task»); tree:docs/program/EXEC-IMAGE-CHANNELS-01.md:5; orig:B/version_comparison_ai/packet.py:163-165, 227-251;
orig:B/version_comparison_ai/sheet_match.py:1-20.
Fix: add an executors slice (e.g. `CMP-EXEC-IMAGES-01`, C0 or before C2, coordinated with the executor workstream's
owner): N images per request with a cap, an image reference not bound to a portal block (opaque crop id + blob id +
sha256 + size), on every served channel (http direct/vpn, pull command, local endpoint, MCP); the estimate counts
images and bytes. Name it in ADR-0025. The alternative (one composite A|B image per call) is a deviation that the
plan must state. Without one of the two, «с изображениями» cannot be delivered.

**R1-03 · BLOCKER · §2, §4 C1/C2** — No slice owns the server side of «Проекты и этапы»: the overview read model
(per-project state of the seven steps, the «следующий шаг» chip, counters and totals, «В загрузке, ещё не в списке
проектов») and the launch queue «Очередь запуска». The queue runs selected steps strictly one at a time across
projects, in the order luna → series → ai, where step 6 is three sub-steps (sheets → specifications → MD summary),
then report. It supports pause, resume, clear and removal of an item, and there is a per-install AI-description
queue («Очередь «ИИ-описание изменений»»). CMP-VC-UI-01 is web-only, CMP-SERIES-01 owns series only, and
CMP-JOBS-01 provides the generic job subject.
Evidence: orig:F/static/js/version-comparison-projects.js:4, 129-163, 355; orig:B/version_comparison_ai/stage_queue.py:1-41
(`STAGES`, `AI_CHAIN`, «строго по одному»); orig:F/static/js/version-comparison.js:76-79; orig:B/version_comparison/overview.py.
Fix: add `CMP-VC-OVERVIEW-01` (M, C1: overview read model, next-step rule, tile counts) and `CMP-VC-QUEUE-01` (M, C2:
durable stage queue as a job subject, AI chain sheets→spec→summary, per-install AI queue, «Из очереди»); add gap rows
G-20/G-21.

## MAJOR

**R1-04 · MAJOR · §3 A-5, §4 CMP-PROFILE-01 / CMP-ENGINE-01** — The dependency stance is not credible.
The original's profile, registration, engine, tiles, lineage and service import `cv2`, `numpy` and `fitz`
(PyMuPDF), and it compares at 200 dpi by default. This tree has neither numpy nor OpenCV, and PyMuPDF is excluded by
OD-01. With «default none» and the rule that only the slot-owning seal takes a dependency, the profile lane (C0) and
the engine lane (C1) would find the need after their seal has merged, and must STOP.
Evidence: orig:B/version_comparison/{engine.py:19-21, registration.py:18-19, profile.py:18-20, tiles.py:15-17,
lineage.py:27-28, service.py:22-24}; orig:B/version_comparison/settings.py:33-34; tree:pyproject.toml:30-32 (PyMuPDF
excluded, AGPL).
Fix: decide in CMP-ADR-01, before CMP-SEAL-C0: numpy (BSD-3) yes/no; OpenCV-headless (Apache-2.0) or own
numpy code for phase correlation, morphology and connected components. Take the choice in CMP-SEAL-C0 with licences
recorded and put it to the owner like open item 2. Name the PyMuPDF replacements: words with boxes and vector lines
from pdfplumber, annotations from pypdf, raster from pypdfium2. Require the profile slice to measure time and memory
per A1 page at 200 dpi.

**R1-05 · MAJOR · §4 CMP-ENGINE-01, §1.1, `Q-CMP-3` («восемь каналов»)** — The engine result lists seven channels
plus a «hook». It misses `text_coverage` («читаемость надписей») and several other parts:
- separation of overlays (stamps, warnings, QR — `separation.py`);
- block alignment («Совмещать блоки» needs `aligned_blocks` and the tile parameter `align_blocks`; `blocks.py`,
  `block_alignment.py`);
- the shift classes `text_moved`, `block_moved` and `shifted` (hidden by default as «не изменение»);
- the light-fill, within-tolerance and noise layers;
- the number highlighting and normalisation labels of «было → стало»;
- the rule that «Совпадает» needs every applicable channel `checked`, and the `FORCING_REASONS` set.
Evidence: orig:B/version_comparison/status.py:1-21; orig:B/version_comparison/engine.py:23; orig:F/static/js/version-comparison-viewer.js:8-23, 90, 157-200.
Fix: list in CMP-ENGINE-01 the eight channel names verbatim, the region classes, the layer set, the forcing reasons,
separation and block alignment. Name where the per-run post-phases live: spec positions (R1-09), parts coverage
(R1-07) and permit (R1-06).

**R1-06 · MAJOR · §2, §4 (absent)** — The per-run permit phase is missing everywhere. For version B, the original
reads the change-permit tables, reconciles declared against found changes (`declared_and_found`, `declared_no_diff`,
`diff_not_declared`, `needs_review`), and shows «Заявлено проектировщиком в разрешении (N)» in the sheet panel.
Evidence: orig:B/version_comparison/jobs.py:751-755, 930-968; orig:F/static/js/version-comparison-sheet-changes.js:79-80.
Fix: add a gap row; assign the deterministic phase to CMP-ENGINE-01 or CMP-SERIES-01 and the panel item to
CMP-VC-AISHEET-01. Otherwise list it as a non-goal, which needs the owner because `Q-CMP-3` says full parity.

**R1-07 · MAJOR · §1.1, §4 CMP-MATRIX-01** — The matrix scope misses these functions:
- sheets split across versions («◫», «⇉», the parts-coverage phase, the viewer note «Лист B — часть листа A»);
- duplicates «⧉»;
- table-sheet groups «▤ группа» (the plan says only «groups»);
- the bridge across a missing intermediate version;
- match rules v1.2 (resolve, package, direct, permit, page number, group);
- the edits: drag-and-drop of thumbnails onto cells, «⤫ Отвязать в отдельную строку», «листа нет», «связать» from
  candidates and from the AI hint;
- the «рядом» window with «вместе» zoom sync;
- non-adjacent cells (shown side by side, «Пара собрана по цепочке… не сравнивалась»).
Evidence: orig:F/static/js/version-comparison.js:380-420, 524-566, 1275-1279; orig:B/version_comparison/jobs.py:875-928;
inventory §2.2 (lineage.py:443-470, settings.py:125,172).
Fix: add these to CMP-MATRIX-01's result and to §1.1.

**R1-08 · MAJOR · §3 A-3 vs §4 CMP-VC-AIPAIR-01, AGENTS §4** — In the original, an accepted model answer becomes a
matrix link (`ai_link`, flag «ИИ»), and that link decides which pages are compared. A-3 lists the matrix as a raw
layer that the AI never rewrites, and AGENTS §4 forbids model output as an expert decision. The plan does not say how
the two fit.
Evidence: orig:B/version_comparison_ai/sheet_match.py:10-17; orig:F/static/js/version-comparison.js:388-389, 401-405.
Fix: in A-3/A-7 and AIPAIR-01, define the effective matrix as a read model over separate rows: algorithm, then
accepted AI links, then manual edits (manual wins). An AI link is labelled «ИИ» and is never an expert act. Show the
hints «🌙 ИИ: вероятно стр. N» and «ИИ ?» (AI disagrees with the algorithm); «связать» turns a hint into a manual
edit draft. List the counts «вопросов · пар · подсказок · против».

**R1-09 · MAJOR · §4 CMP-VC-SPEC-01 vs §3 A-6** — Two different specification functions are merged into one, and
the plan contradicts itself.
- The original has (a) a deterministic per-run `spec.py`: ГОСТ 21.110 tables read by vector lines, positions compared
  across pages, the status of a spec sheet decided by positions, the `spec_positions` channel and the viewer panel
  «Спецификация по позициям».
- It also has (b) AI whole-specification extraction (`specification_run.py`, a model, one session per whole
  specification, coverage and quote checks) behind «Полные спецификации (СО)», with methods «полное сравнение» and
  «листовой ИИ».
- SPEC-01 says it reuses the Form-7 extractor, which is deterministic and reads a run's `prepared.text_layer`, so a
  plain-PDF version without a run has no input. Yet A-6 adds the AI work kind `comparison_spec`.
Evidence: orig:B/version_comparison/jobs.py:787-871; orig:B/version_comparison/spec.py:1-21; orig:B/version_comparison/specification_run.py:1-25;
orig:F/static/js/version-comparison.js:228-275; orig:F/static/js/version-comparison-viewer.js:175-187; tree:src/auditmanager/optimisation/specification.py:1-6.
Fix: state which mechanism serves (a) and which serves (b). If Form-7 replaces the AI, call it a deliberate deviation
and raise it with the owner. If the AI stays, add estimate, consent and the work kind. Name the input as the page
profile words and lines. Add the two viewer/panel elements, including «По полной спецификации · только изменения этого листа».

**R1-10 · MAJOR · §1.1, §2 G-12, §4 CMP-VC-REPORT-01** — The PDF report is described as analyst → verifier →
composer. Since 21.10.2026 the original's default kind is «client» («Отчёт для заказчика … Изменения проектных
решений»):
- one model call per transition over the MD summary's facts, with discipline priorities;
- a program check drops every point whose number, mark or direction the facts do not confirm;
- the result is one chronological table.
The analytic kind is the older path. The window's functions are also missing:
- source «загрузить MD-файл»;
- reuse of finished parts;
- «Отменить», «Продолжить», «Пересобрать PDF» (no model call), «Удалить», «Исходный MD»;
- «Подготовить отчёт для заказчика» from an analytic report;
- the per-transition progress tables (client and analytic columns).
Evidence: orig:B/version_comparison_ai/md_report/runner.py:133-143; orig:B/version_comparison_ai/md_report/client.py:1-10;
orig:F/static/js/version-comparison-md-report.js:15-18, 26-37, 64-77; orig:F/static/js/version-comparison.js:277-333.
Fix: rewrite REPORT-01 and G-12 with the client report as the default. Make the analytic kind either an owner item or
an explicit non-goal. List the window's functions.

**R1-11 · MAJOR · §1.1, §4 CMP-VC-AISHEET-01** — The following visible functions are missing:
- the single-sheet AI description of added and removed sheets («Вывод ИИ по листу»: тип листа, суть, «Что на
  листе», «Марки», «Неясно», disclaimer; `single.py`, `prompts/describe_sheet.md`);
- the «Проверить» review list (sheets where the AI found no change but the engine left marks) with step-through;
- «Повторить листы с ошибкой», «Досчитать», «Убрать из очереди»;
- in the panel: «Отменить задание», «Копировать текст», «Не включено в сводку», «Диагностика», «История (N)»,
  «Описание устарело», «Строительных изменений не выявлено» and the eleven state labels;
- the viewer's evidence banner («Из ИИ-описания: …», «доказательство N из M», «Обзор всех / Один фрагмент»).
Evidence: orig:F/static/js/version-comparison.js:159-225, 548-563; orig:F/static/js/version-comparison-sheet-changes.js:20-96;
orig:F/static/js/version-comparison-viewer.js:38-50.
Fix: add these to §1.1 and AISHEET-01. Name our counterpart of «ТЕСТОВЫЙ ОТВЕТ подменного исполнителя»: a
recorded-mode label.

**R1-12 · MAJOR · §1.1 viewer, §4 CMP-VIEWER-01** — The following are missing:
- «Только изменённые листы» and the «‹ лист / лист ›» navigation;
- «Как сравнивалось» (transform, dpi, tolerance, within-tolerance and noise counts, separated objects);
- the «Текст: N изменений» list;
- the toggles «сдвиги (не изменение): N» and «оформление линий: N»;
- the split-part note and the scan note;
- the tile rule (a reduction takes the maximum of the difference masks).
Two statements are wrong:
- The original has two mode buttons only, «Наложение» and «Рядом». A and B are the panes of «Рядом» and the
  under-layer of «шторка»; they are not modes.
- Only one layer checkbox is shown, «места, где изменился цвет». The other seven layers are fixed defaults.
Evidence: orig:F/static/js/version-comparison-viewer.js:36, 52-56, 76-90, 134-245, 278, 283-286, 322-323; inventory §1.5 (tiles.py:1-8).
Fix: correct the wording in §1.1 and add the list to VIEWER-01.

**R1-13 · MAJOR · §1.1, §4 CMP-INGEST-01, `Q-CMP-5`** — Batch upload is under-described. The original has two flows.
- Single upload with a proposal: «Куда загрузить: Новый проект / Добавить версии в «…»»; groups by designation or
  name base; title input; ↑↓; «в проект…»; label per file; warnings; «Подтвердить группировку и порядок».
- Multi-project batch («Загрузка нескольких проектов»):
  - drop several folders, or «Общая папка с проектами»;
  - resumable chunked transfer, up to 10 000 files and 100 projects, with «Остановить загрузку», «Продолжить
    загрузку» and «Удалить пакет»;
  - «После подготовки сравнить все соседние версии»;
  - a server queue with «Пауза после текущего проекта», «Подтвердить порядок во всех проектах», «Подтвердить состав
    и порядок» per project, «Исключить», «Повторить» and ten status labels.
- The pending strip «В загрузке, ещё не в списке проектов».
The tree takes one version per upload (plan G-01).
Evidence: orig:F/static/js/version-comparison.js:435-502; orig:F/static/js/version-comparison-batch.js:4-8, 49-126;
orig:B/version_comparison/batches.py:29-31; orig:F/static/js/version-comparison-projects.js:129-134.
Fix: list these in INGEST-01, or split it into INGEST-01 (single, proposal, order) and INGEST-02 (batch, resumable,
server queue). Make the batch queue a job subject kind, state the limits, and re-size.

**R1-14 · MAJOR · §1.2 tab 1, §4 CMP-STAGE-PAIR-01** — Tab 1 is described as the catalog plus «pair suggestion and
expert confirmation». The original's pair workbench is missing:
- OLD/NEW columns with drag-and-drop;
- counters «Сопоставлено / Требует проверки / Только OLD / Только NEW»;
- «Сопоставить автоматически» and auto-save;
- the assembly fan list with «Убрать из группы» and «Пересобрать»;
- «Добавить проекты справа для …» (an upload aimed at a row);
- the row menu «⋯ → Перезапустить анализ пары»;
- the batch launch «Запустить анализ выбранных (N)» and «Остановить очередь»;
- «Состав NEW относительно OLD» (неизвестна / полный / неполный).
The upload dialog is missing too: the stage choice («Слева — исходная редакция / Справа — новая редакция»), the
candidate table («ZIP-комплект / папка проекта / PDF-проект»), background minimise and the progress tray.
Evidence: orig:F/index.html:5547-5553, 5801-5825, 5888-6027, 7999-8150.
Fix: list these in §1.2 and STAGE-PAIR-01, put the batch launch on a durable queue, and keep composition completeness
(it decides how a missing Р sheet reads).

**R1-15 · MAJOR · §1.2 tab 2, §4 CMP-STAGE-LINK-01** — Part of tab 2 comes from the original's design document, not
from its template, and the plan presents it as the original's UI.
- Document only: «Оставить», «Изменить», «+ Добавить лист РД» and «Синхронный вид», and drag reassignment on the
  thumbnail strip. The template has «Удалить связь» only at block level.
- Live but omitted:
  - per-row page selects with «Пусто»;
  - «Принять предложенные (N)»;
  - the filter «Все / Требуют проверки (N)»;
  - the status «Нет пары»;
  - «Обработать»;
  - «Удалить текущую связь листов» and «Добавить пустой лист слева/справа»;
  - «1:1»;
  - «Постраничный / Непрерывный режим»;
  - «← Вернуться к той же строке».
Using the document is legitimate under `Q-CMP-1`, but the plan must say so. It must also carry the document's two
rules for thumbnail moves: lay sheets onto the nearest free places, and make only a changed row manual; a leftover
sheet goes to `unlinked_left_pages`.
Evidence: orig:docs/DOCUMENT_COMPARISON_CURRENT_STATE.md:49-62, 64-103, 123; orig:F/index.html:6085-6229, 6249-6260, 6349-6361, 6455-6460;
orig:F/static/js/stage-block-mapping.js:2639-2706.
Fix: rewrite §1.2 tab 2 with a source tag (doc or live) on each element, add the live ones, and add the two rules to
LINK-01.

**R1-16 · MAJOR · §3 A-8, §4 C3, `Q-CMP-2`, `Q-CMP-5`** — The plan does not say what the stage chain reads for a
plain PDF.
- The original's sheet passports and suggestions come from the portal's HTML index (`ocr.html`) and `document.md`.
  Stage 2 structure comes from `document.md` TEXT blocks and `blocks.json`. A plain PDF has none of these.
- The plan does not say where passports (тип, корпус, этаж, уровень, sheet number and title) and fragments come from.
- In this tree the P/R stage and the section are expert-confirmed per version. The plan does not say how a
  plain-PDF stage upload records them, yet «suggest by designation/section» needs them.
- Scans are not covered.
Evidence: orig:B/stage_comparison/sheet_matching.py:1, 38-40; orig:docs/DOCUMENT_COMPARISON_CURRENT_STATE.md:28-31, 146-158;
tree:src/auditmanager/documents/models.py:189-252; tree:src/auditmanager/comparison/version_section_pair.py:1-12, 116-126.
Fix: in A-8 and LINK-01/TEXT-01:
- passports and fragments come from the page profile (stamp, words with boxes) for every input, with bundle artefacts
  optional;
- INGEST-01 or STAGE-PAIR-01 records P/R and section for plain PDFs, as a stamp proposal that an expert confirms;
- a scan gives no TEXT evidence and is marked as compared as an image only.

**R1-17 · MAJOR · §4 CMP-STAGE-LINK-01 / CMP-STAGE-AI-01, §3 A-7** — Automatic link repair.
- In the documented chain the repair is deterministic: a purpose precheck (`PAIR_OK` / `PAIR_REVIEW_REQUIRED`), then
  one fix by a unique exact title or a mutual-best fuzzy match ≥ 0.94; swaps and cycles are allowed.
- It may change a manual link with HIGH proof.
- Undo restores the snapshot and recomputes stages 2–5; a later manual edit supersedes an old undo.
- The plan puts «repair history with undo» in C3 (LINK-01) but produces repairs in C4 (AI-01). C3 has nothing to undo
  and cannot recompute C4 stages.
- The plan does not say the repair is deterministic, nor whether an automatic repair may override an expert's link
  (A-7 calls links expert acts).
Evidence: orig:docs/DOCUMENT_COMPARISON_CURRENT_STATE.md:326-341.
Fix:
- put repair, undo and recompute in one C4 slice and say «no model»;
- add an ADR decision or open item: a repair never overrides an expert link (it proposes instead), or it does so only
  as a recorded, revertible automatic act shown as «Исправлено автоматически».

**R1-18 · MAJOR · §1.2, §4 CMP-STAGE-TEXT-01** — The visible outputs of documented Stage 2 are missing:
- grey masks of proven-same text on both panels (one overlay for a fully matched block; after Stage 4 only for
  accepted SAME/MOVED);
- the second pass «найдено на другом листе» with the «↗» marker;
- recommendation-only `sheet_link_hints`, which become links only through «Добавить связь» / «Заменить связь»;
- older layers marked stale after a map change;
- the raw-differences table «Лист П / Лист РД / Изменилось / Удалено / Добавлено».
Evidence: orig:docs/DOCUMENT_COMPARISON_CURRENT_STATE.md:158-208, 248-254, 300-306.
Fix: add these to TEXT-01, to the stage viewer (LINK-01) and to §1.2 tabs 2–3.

**R1-19 · MAJOR · §4 CMP-STAGE-TEXT-01 / CMP-STAGE-AI-01, §5 «C3 needs CMP-ENGINE-01»** — GRAPHIC evidence is a new
feature, and the plan does not bound it.
- The documented chain is text-only (Stage 5.3 `evidence_sources: ["TEXT"]`, «G1 изолирован»).
- G1 runs only on 1↔1 blocks and is backend-only.
- The version engine registers B onto A for two versions of one sheet. Stage links are many-to-many between
  different documents, often of different formats («слева A4, а справа A1»).
Evidence: orig:docs/DOCUMENT_COMPARISON_CURRENT_STATE.md:121-122, 403-406, 438-450; inventory §5.
Fix: mark GRAPHIC as an addition beyond the original. Allow it only for 1↔1 links with reliable registration;
otherwise the card says «графика не проверялась». State that TABLE evidence means text fragments of table rows
(doc:147-148), not a table extractor.

**R1-20 · MAJOR · §1.2 tabs 3–4, §3 A-2/A-7, §4 CMP-STAGE-AI-01 / CMP-STAGE-REVIEW-01** — The card and the life of a
verdict are undefined.
- Is a card a Stage-5 aggregate or a Stage-5.3 high-level change?
- Do SERVICE_STRUCTURE and REVIEW cards take verdicts and count?
- How does a verdict survive a re-run, a repair or undo, or a new version? The original binds the review to change id
  + run id + `expected_revision`, with 409 on conflict.
- Grouping «По системе / По разделу / По шифру» needs system, discipline and designation on each card, but the
  classifier emits only class, category and title.
- Not listed: the summary «Всего / Нужно проверить / Конфликты / Высокая важность»; the evidence panel per side (with
  «Отсутствие объекта не доказано»); «Открыть в PDF ↗»; the «Экспертная оценка» toggle; «Не сохранено: N»;
  «Решения сохранены».
Evidence: orig:F/static/js/project-change-ui.js:66-135, 185-300; orig:F/static/js/project-change-view.js:185.
Fix:
- define the card and its content-keyed identity;
- state the verdict carry-over rule: same evidence digest → carried, otherwise shown stale;
- define the source of «система»: classifier output from a closed list, or derived deterministically;
- list the tab 3 elements.

**R1-21 · MAJOR · §1.2, §4 C3/C4** — No slice owns the stage chain run as durable work:
- single and batch launch, and consent for the AI part;
- cancel and resume, and the run and quality banners;
- staleness («Есть новые документы — …»);
- the steps of the pipeline strip for the chain (the live strip's seven steps are V3's).
Evidence: orig:F/index.html:5480-5531, 5536, 6471-6490; plan:68, 229.
Fix: name the chain's steps, for example: 01 Связи листов, 02 Исключение одинакового текста, 03 Расхождения,
04 ИИ-ревизия, 05 Классификация и починка связей, 06 Синтез, 07 Карточки. Give the orchestrator to one slice: PAIR-01
for the deterministic part, extended by AI-01, or a new `CMP-STAGE-RUN-01`.

**R1-22 · MAJOR · §1.3 non-goals** — §1.3 names only «Консолидатор», «Отчёт с ИИ-разбором» and «Проверка по
источникам». Other live V3-only elements that a reader of the README will expect are not listed:
- the «Смысловые блоки» mode of tab 2 («Все блоки / Блоки со связями / Блоки без связей», «Редактировать связи»);
- the launch dialog: «Быстро / Стандартно / По инженерным предметам», «Модель анализа», «Параллельные запросы 5/10»;
- «Досчитать из сохранённого» with «Максимум новых участков», and «Свести дубли»;
- «Вид сравнения Документ↔документ / Страница↔страница»;
- the catalog statuses «Заморожен · прогон V3 / запечатанный снимок»;
- the «Классический отчёт» zip and the IT-analysis xlsx upload;
- the version comparison's backend-only Excel/HTML run reports.
Evidence: tree:docs/program/compare/README.md («Листы / Смысловые блоки», «Редактировать связи»); orig:F/index.html:5547-5549, 6234-6247,
7898-7995; orig:F/static/js/project-change-consolidation.js:579-598; orig:R/version_comparison.py:354-383.
Fix: list these by name in §1.3 so the owner sees the cut.

**R1-23 · MAJOR · §3 A-6, §4 CMP-SEAL-C2, §3 A-4** — Work kinds are in the wrong file, and AI spend accounting is
bound to runs.
- `executors/kinds.py` is the registry of connection kinds. Work kinds are `WORK_KINDS`/`SERVES` in
  `executors/model.py`, plus the contract schema `ExecutorWorkKind` and the web routes widget and vocabulary.
- The spend ledger is bound to runs: `model_call.run_id` is `NOT NULL REFERENCES audit_run`, and the cost queries in
  `jobs/repository.py` filter by run and by `stage_id = 'text_analysis'`. Comparison AI calls have no run, so `R-29`
  accounting breaks.
Evidence: tree:src/auditmanager/executors/kinds.py:1-13; tree:src/auditmanager/executors/model.py:68-70; tree:contracts/api/v1/openapi.json:18095;
tree:web/src/widgets/executor-routes/ui/executor-routes.tsx:51; tree:web/src/entities/executor-connection/model/vocabulary.ts:74;
tree:db/migrations/versions/20260910_0002_pc01_schema.py:820-823; tree:src/auditmanager/jobs/repository.py:211, 266-343.
Fix:
- correct the hotspot to `executors/model.py`, and grant the web vocabulary and widget edits to the seal;
- extend CMP-JOBS-01 (or SEAL-C0) to a typed subject for `model_call` and the cost meter;
- say how Attempt context reaches the executor adapters for a comparison job.

**R1-24 · MAJOR · §5 «Inside a wave … in parallel»** — Dependencies inside a wave are not stated.
- C1: SERIES needs ENGINE and MATRIX; VIEWER needs ENGINE's result and tile format; the C1 UI needs
  MATRIX/SERIES/OVERVIEW.
- C2: REPORT consumes the AISHEET answers and the SPEC reports (MD summary first, then PDF).
- C4: REVIEW needs the AI classes; JOURNEY needs everything.
Fix: give the order per wave, for example:
- C1: ENGINE ∥ MATRIX ∥ VIEWER (on recorded fixtures) → SERIES → OVERVIEW → VC-UI;
- C2: AIPAIR ∥ AISHEET ∥ SPEC → QUEUE → REPORT → UI-02;
- C4: STAGE-AI → STAGE-REVIEW → JOURNEY → CLOSE.
Or name which lanes work against fixtures and which integration tests wait.

**R1-25 · MAJOR · §3 A-2, `Q-CMP-2`** — What a stage pair binds, and when it goes stale, is undefined. Does `stp_`
pin documents or exact versions on each side, including the assembly members' versions? When a new П or Р version
arrives, what becomes stale (links, fragments, cards, verdicts), and how is it shown? The original says «Есть новые
документы — администратор ещё не обновил сравнение».
Evidence: orig:F/index.html:5536.
Fix: a stage pair binds DocumentUids; each chain run pins version ids; a newer version marks the run stale; verdicts
stay with the run they were given on and carry over only under the R1-20 rule.

## MINOR

**R1-26 · MINOR · §1.1 «Проекты и этапы»** — The action list misses:
- «Повторить» (step 2) and «Сформировать PDF-отчёт» (step 7 start);
- the dialog labels «Описать заново», «Сформировать заново», «Пересчитать»;
- per-row «Сводка изменений (MD)»; a row click opens «Сравнение листов»;
- the column «выбрать все» checkboxes, and the selection bar «Запустить выбранные по очереди» / «Снять выбор»;
- the queue controls «Пауза очереди», «Продолжить очередь», «Очистить», «Список», «✕»;
- «Обновить», «обновлено HH:MM:SS», column sort ▲▼, the legend;
- the consent line of every AI dialog.
Evidence: orig:F/static/js/version-comparison-projects.js:120-226, 468, 516, 558.
Fix: add these to §1.1.

**R1-27 · MINOR · §4 CMP-SERIES-01** — Missing: staleness after a reorder («по старому порядку», «Сохранённая сводка
для прежнего порядка версий.»); the «Досчитать» and «Продолжить» labels; the rule that a non-adjacent A/B pair is not
compared; the cache reuse note in «Заново».
Evidence: orig:F/static/js/version-comparison-projects.js:73-89, 495-503; orig:F/static/js/version-comparison.js:126-130, 1275-1279.

**R1-28 · MINOR · §0 standing rules** — «`R-146ba` (no human-review labels during the beta, `A-10`)» is imprecise.
`R-146ba` removes the profile label and the AR v3 citation label, and explicitly keeps the label above the comparison
summary. A lane could read the plan's line as «drop the labels».
Evidence: tree:docs/program/OWNER_RULINGS_2026-09-17.md:1811.
Fix: say that every comparison AI text keeps «инженером не подтверждено» under the `R-146ba` exception.

**R1-29 · MINOR · §7** — «22 slices»: the tables list 24 (C0 5, C1 6, C2 5, C3 4, C4 4). Re-count and re-estimate
after the slices from R1-01, R1-02, R1-03, R1-13 and R1-21.

**R1-30 · MINOR · §9 item 2, §1.2 tab 4** — Gaps in the export spec:
- Open item 2 names a PDF writer only for the version report; tab 4's «PDF ↓» needs one too.
- Excel should reuse the in-tree writer (`src/auditmanager/exports/xlsx/writer.py` through the exports public API).
- The Excel columns are undefined. The original's legacy final report has: ID, Объект, Изменение, Было, Стало,
  Источник, Решение эксперта.
- PDF and HTML go beyond `Q-CMP-1` («группировка и Excel») and depend on open item 2.
Evidence: tree:src/auditmanager/exports/xlsx/package.py:16-17; orig:F/index.html:7849-7858.

**R1-31 · MINOR · §4 CMP-INGEST-01, §3 A-8** — The refusal to start a run on a comparison-only version belongs in
`src/auditmanager/runs/commands.py`, where start-run checks the manifest's `source.document` (:386-391), not in
ingest/documents. A plain PDF stored under that role would pass.
Fix: grant `runs/commands.py` to the slice, or give plain PDFs a distinct manifest role; the error code goes to
SEAL-C0.

**R1-32 · MINOR · §3 A-9, §4** — The route `web/src/app/stage-comparison/**` belongs to no slice. Assign it to
CMP-STAGE-PAIR-01.

**R1-33 · MINOR · §1.2 tab 3** — Stage 5.3 sections are missing: high-level changes first, then
`detail_level_increased`, material review, non-material review (collapsed) and the service-structure summary. Only
Stage 5's three blocks are listed.
Evidence: orig:docs/DOCUMENT_COMPARISON_CURRENT_STATE.md:398-410.

**R1-34 · MINOR · §8, §4 AISHEET / AIPAIR** — Deliberate deviations from the original's AI runtime are not stated:
- the original waits out a transient 429 (20/60/120/300/600 s) and pauses on quota or auth (`paused_quota`,
  `paused_auth`); the plan says «no automatic retry beyond provably unprocessed calls»;
- the original runs a model-driven context-request loop (main call, technical retry, context request, unparsed pass);
  the plan implies one request per call.
Evidence: inventory §2.5c; orig:B/version_comparison_ai/sheet_match.py:41-45.
Fix: state both as deviations.

**R1-35 · MINOR · §1.1 «Порядок версий», §3 A-2, §4 CMP-INGEST-01** — Where the order lives is ambiguous. INGEST-01,
in documents, proposes it; A-2 makes `cvo_` comparison-owned.
Fix: say that the comparison order does not change the documents' ordinal that runs and carry-over use, and that
saving it marks the matrix and series stale.
Evidence: orig:F/static/js/version-comparison.js:519.

**R1-36 · MINOR · §1.2 tab 1** — The chain's meaning of the catalog columns «Метод и модель», «Изменения», «Требуют
проверки» and «Статус» is undefined; the live values are V3's.
Fix: for example: method «Цепочка», plus the routed model of the AI layer; Изменения = PROJECT_CHANGE cards;
Требуют проверки = REVIEW cards plus pairs without links; Статус = the chain run state.

---

### Faithfulness to the owner's answers (question 2), summary
- `Q-CMP-1` (chain + AI layer): honoured in structure. The plan departs from it in three places:
  - the automatic link repair may override expert links (R1-17);
  - GRAPHIC evidence is an addition the plan does not mark (R1-19);
  - tab 2 mixes the doc and live sources without saying so (R1-15).
- `Q-CMP-2` (pairs in a project, assemblies, no object entity): honoured. Version binding and staleness are open
  (R1-25), and so is plain-PDF stage/section capture (R1-16).
- `Q-CMP-3` («Полный паритет»): partly dropped without saying so:
  - `text_coverage`, permit, split sheets and duplicates (R1-05, R1-06, R1-07);
  - the client PDF report (R1-10) and the single-sheet AI description (R1-11);
  - the overview and launch queue (R1-03), and all C2 screens (R1-01).
- `Q-CMP-4` («с изображениями»): not deliverable on the current one-image, portal-block-only channel (R1-02).
- `Q-CMP-5` (plain PDFs in batches): resumable multi-project batch (R1-13), stage-side inputs (R1-16) and the run-start
  refusal path (R1-31).

ROUND 1 VERDICT: 3 BLOCKER, 22 MAJOR, 11 MINOR
