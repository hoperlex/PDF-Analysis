# COMPARE-MODULES-PLAN — «Сравнение стадий» and «Сравнение версий» to the original's functions and screens

Revision 0 (draft for judging), 2026-10-27, planner session `pdf-analysis-4d`. Docs only: this plan
changes no code, contract, migration or test. Base: `integration/ar-close-1026` at `9e42c18a`
(contract `1.8.0`, surface 95 paths / 107 operations / 314 schemas, migration head
`0035_comparison_records`, product `0.9.0`). Branch `plan/compare-modules`.

Evidence: `docs/program/compare/README.md` and the two inventories next to it (the original
`SU10KAZ/PDF-proverka` at `23f379fd`, and its live screens at `https://auditmanager.app` seen
read-only on 2026-10-27). In this plan «the original» means that commit and those screens.

## 0. Owner answers this plan rests on

Asked by direct poll on 2026-10-27 (≈16:05 and ≈16:20 +05). They are answers, not rulings; the
integrator of the wave records them in `OWNER_RULINGS_2026-09-17.md` and numbers them. Until then
this plan cites them as `Q-CMP-1` … `Q-CMP-5`.

| Id | Question (short) | Answer chosen |
| --- | --- | --- |
| Q-CMP-1 | Which path for «Сравнение стадий»: the live V3 pipeline (a model reads both sets and writes «Было/Стало» cards) or the documented deterministic chain with an AI layer on top | «Цепочка + ИИ-слой»: deterministic sheet links and differences, the AI only classifies and summarises into «Было/Стало» cards that point at places in the sheets; an expert confirms each card; report with grouping and Excel; screens after the original's four tabs |
| Q-CMP-2 | What a stage comparison compares | «Пары документов в проекте»: the project is the object; an expert pairs stage П documents with stage Р documents inside one project (the system suggests by designation/section), one П document may face several Р documents as one assembly («сборка»); a new «stage pair» entity, no separate «object» entity |
| Q-CMP-3 | Scope of «Сравнение версий» | «Полный паритет»: the projects table with seven steps, the sheet matrix across all versions, the deterministic per-sheet comparison in eight channels, the overlay viewer, the AI check of doubtful sheet pairs, the AI description of sheet changes, the specification comparison, the MD summary and the PDF report |
| Q-CMP-4 | When, and may sheet images go to a model | «До беты, с изображениями»: both modules are beta scope; crops of drawings may be sent to a model in the comparison AI layers (this widens the accepted risk `A-2` to drawing images; the integrator records it) |
| Q-CMP-5 | Upload for comparison | «PDF для сравнения»: the comparison modules accept plain PDFs in batches (all versions of a designation, or the documents of a stage); such a version is marked as uploaded without a portal bundle; it is compared by its PDF text layer and raster; starting a section analysis on it still requires a portal bundle; a scan without a text layer is compared as an image only |

Standing rules that also apply: `AGENTS.md` §4 (no LLM output as an expert decision, no AI change
to raw deterministic evidence, no job state only in memory, no path or file name as identity, no
silent fallback, no deep imports across contexts); `R-29` (live model spend per wave); `R-133` (a
reply from a model other than the pinned one is a typed refusal); `R-60` (expert writes are
expert-role); `R-146ba` (no human-review labels during the beta, `A-10`); subagent rule (execution
lanes on Sonnet, data gathering on Haiku).

## 1. What the user gets

### 1.1 «Сравнение версий» (menu item, group «Работа»)

Tab «Проекты и этапы» (one row per document set of the chosen project, its designation shown as
«шифр»): counters «Все / Ждут действия / Идут / Ошибки / Готовы», versions and transitions total,
«Поиск по шифру…», filters «Марка» and «Порядок», a launch-queue strip, and the table «Проект ·
следующий шаг», «Версии», «1 Загрузка», «2 Разбор версий», «3 Сопоставление листов», «4 ИИ-проверка
сомнительных пар», «5 Сравнение соседних», «6 ИИ-описание изменений», «7 Сводка и отчёт», each step
with the original's state words, counts and actions («Подготовить», «Проверить», «Запустить»,
«Пауза», «Продолжить», «Заново», «Из очереди», «PDF»), row checkboxes for steps 4–7 feeding the queue.
Button «Загрузить проект со всеми версиями» (plain PDFs or a ZIP/folder of them, `Q-CMP-5`).

Tab «Сравнение листов» (one document set): «Сводка переходов» (one row per adjacent transition
with progress, «Листов», «✓ ◐ ● ⚠», «Состав +N / −M», the deterministic verdict, «Открыть»), «ИИ-описание
изменений» per transition, «Полные спецификации (СО)», «Сводка MD и отчёт для заказчика», the sheet
matrix «Лист \ версия» with thumbnails, confidence flags, manual edits as drafts («Применить
сопоставления (N)», «Отменить правку»), «∅ нет в версии», unmatched cells with candidates, «Несвязанные
страницы», «только изменения», sides A/B per version column, «Порядок версий», «Сводка изменений (MD)»,
«Сформировать PDF-отчёт…».

Sheet viewer: «Наложение» / «Рядом» / A / B, «шторка», zoom and pan on tiles («Вписать»), the layer
checkboxes of the original, «рамки отличий», «Совмещать блоки», the channel strip «Проверено: … / Не
проверено: …», the difference list «Отличия: N» with ← →, «Служебные зоны и пометки», and the side panel
«Изменения в листе» (estimate, consent «Подтверждаю передачу этого листа исполнителю», result with
«Было/стало», confirmation tier «с изображения» / «не подтверждено», «Показать на чертеже», «MD листа»).
Every AI text is labelled as model output not confirmed by an engineer.

### 1.2 «Сравнение стадий» (menu item, group «Работа»)

Tab «1. Загрузка документации»: the stage pairs of the chosen project with the original's columns
«Проект / раздел», «OLD → NEW» (with «сборка из N»), «Метод и модель», «Дата», «Изменения», «Требуют
проверки», «Статус», «Открыть» / «Запустить сравнение»; «Загрузить проекты» (plain PDFs or portal
bundles per stage, `Q-CMP-5`); pair suggestion and expert confirmation (`Q-CMP-2`).

Tab «2. Сопоставление листов»: the pipeline strip of the opened pair; the sheet map with confidence
(«Высокая», «Ручная», «Проверить», «Исправлено автоматически»), many-to-many links, «Оставить»,
«Изменить», «+ Добавить лист РД», «Удалить связь», explicit «без пары»; the thumbnail strip with
drag-and-drop reassignment; the two-panel synchronised viewer with per-panel text search; history of
automatic repairs with undo.

Tab «3. Изменения проекта»: cards «ID / Изменение / Было / Стало / Источник (TEXT, TABLE, GRAPHIC) /
Статус» with «Основные изменения проекта» first, «Служебные и структурные изменения» collapsed,
«Показать исходные текстовые различия» collapsed; each card opens the П and Р places; expert
verdict per card «Принято» / «Не принято» (reason required for a rejection), «Сохранить решения».

Tab «4. Отчёт»: «Итоговый журнал изменений», «Подтверждено изменений: N», grouping «По шифру / По
разделу / По системе» that really groups the table, exports «Excel ↓», «PDF ↓», «HTML ↓» that work.

### 1.3 What is deliberately not copied

- The live V3 semantic pipeline of the original's stage comparison (`Q-CMP-1`); its «Консолидатор»,
  «Отчёт с ИИ-разбором» and «Проверка по источникам» steps exist only as V3 features.
- Code the inventories found dead or unwired in the original (the `!pcUiEnabled` blocks, the
  run-level `vc-ai-report`, G1 graphic routes without a caller, the 403 decisions stub), and the
  original's disabled exports (we build working ones).
- Server-side file paths, object folders and `current_id` per server: our project is the object
  (`Q-CMP-2`) and identity is always an opaque id.
- The original's model names (`gpt-6-luna`, `gpt-6.1-sol`, `gpt-6-astra`): our AI calls go through
  «Исполнители» routes and pins (`R-133`, `P02_LOCK.json`).

## 2. Gap: the original against this tree

| # | Function (original) | This tree at `9e42c18a` | Slice |
| --- | --- | --- | --- |
| G-01 | Upload plain PDFs, batches, all versions of a designation | only portal bundles (`portal_bundle_required`, `src/auditmanager/ingest/bundle_archive.py:200`); one version per upload (`uploadDocumentVersion`) | CMP-INGEST-01 |
| G-02 | Version order and labels («Порядок версий», stamp «Изм.N», date) | versions ordered by upload ordinal only | CMP-INGEST-01 |
| G-03 | Page profile: text words with boxes, stamp fields, sheet number and title, ink mask, scan flag | text layer of a run (`prepared.text_layer`), crops by pypdfium2 (`src/auditmanager/analysis/geometry/render.py`); no page profile | CMP-PROFILE-01 |
| G-04 | Previews, thumbnails, 512-px tiles at zoom levels, overlay tiles | none on the server; the web has a pdf.js viewer | CMP-PROFILE-01, CMP-VIEWER-01 |
| G-05 | Sheet matrix across all versions, max-weight matching with thresholds 0.55/0.35/0.20, groups, manual drafts, undo | two versions at a time, proposals only (`src/auditmanager/comparison/pairing.py`), single approved pairs (`approveSheetPairing`, migration `0035`) | CMP-MATRIX-01 |
| G-06 | Deterministic per-sheet comparison in eight channels with statuses and reasons, cached by content | text-line diff only (`raw_text.py`), no raster, no zones, no annotations | CMP-ENGINE-01 |
| G-07 | Series of adjacent transitions, pause/resume/cancel, durable progress | none; `job` is bound to `audit_run` (`src/auditmanager/jobs/repository.py:28`) | CMP-JOBS-01, CMP-SERIES-01 |
| G-08 | Overlay viewer with layers, swipe, difference list | none | CMP-VIEWER-01 |
| G-09 | AI check of doubtful sheet pairs (images of candidates) | none | CMP-VC-AIPAIR-01 |
| G-10 | AI description of sheet changes (crops + words, tiers text/image/unverified) | a recorded-only summary over approved pairs (`generateComparisonSummary`, `D-244`) | CMP-VC-AISHEET-01 |
| G-11 | Whole-specification comparison (СО) | the Form-7 extractor of optimisation (`src/auditmanager/optimisation/specification.py`), not used by comparison | CMP-VC-SPEC-01 |
| G-12 | MD summary (deterministic) and PDF report (AI analyst/verifier/composer, PDF built by a program) | none | CMP-VC-REPORT-01 |
| G-13 | Projects table «Проекты и этапы», queue strip | none | CMP-VC-UI-01 |
| G-14 | Stage pairs of different documents, assemblies | `mode=stage` compares two versions of ONE set (`compareDocumentVersions`) | CMP-STAGE-PAIR-01 |
| G-15 | Stage sheet links many-to-many, suggestions by sheet passport, repair with undo | none for different documents | CMP-STAGE-LINK-01 |
| G-16 | Text exclusion contract and deterministic differences inside links | line diff per approved pair (`raw_evidence_seal.py`) | CMP-STAGE-TEXT-01 |
| G-17 | AI reviewer and change classifier (PROJECT_CHANGE / SERVICE_STRUCTURE / REVIEW), high-level synthesis | none | CMP-STAGE-AI-01 |
| G-18 | Change cards, expert verdicts, journal, grouping, exports | none | CMP-STAGE-REVIEW-01 |
| G-19 | Two menu items and their screens | one screen under a version («Сравнение прогонов», `web/src/shared/config/screen-registry.ts:161`) | CMP-VC-UI-01, CMP-STAGE-REVIEW-01 |

What stays as it is: run comparison of one version (`W43-COMPARE`), finding match proposals and
decision carry-over (`carryOverDecision`), which keep reading `compareDocumentVersions`.

## 3. Architecture (to be fixed by `ADR-0025` in slice CMP-ADR-01)

**A-1 Context.** Everything new lives in the `comparison` context (`src/auditmanager/comparison/`),
split into subpackages created by the slices that need them: `ingest_pdf` is NOT one of them —
plain-PDF admission belongs to `ingest` and `documents` (G-01). Other contexts are called through
their `public.py` only; the composition root adapts ports.

**A-2 Identities (all opaque, none from a path, file name or display number).**
`DocumentUid` is the series of versions (the «шифр» is metadata read from the stamp and confirmed,
not identity). New: `cvo_` comparison version order (an append-only revision of the order and labels
of one set), `cpr_` page profile (per version page, keyed by content digest), `cmx_` matrix revision,
`cml_` manual matrix edit, `cser_` series (one order revision → its transitions), `csp_` sheet pair
result (content-keyed), `stp_` stage pair, `sla_` stage-side assembly, `slk_` stage sheet-link
revision, `crp_` link repair, `cai_` AI job, `ccd_` change card, `cdv_` card verdict, `crt_` report.
Prefixes are proposals; the ADR fixes them against `docs/program/` identity catalogues and the
identifier-catalogue test.

**A-3 Evidence layers.** Raw deterministic layers (profiles, matrix, sheet-pair results, text
fragments, exclusions, differences) are immutable rows or content-addressed blobs; AI layers (pair
check answers, sheet descriptions, reviewer decisions, classes, high-level synthesis, report text)
are separate rows that reference raw ids and never rewrite them. A UI «final» layer is a read model
computed from both. Every AI answer passes a strict validator (schema, only existing ids, exact
coverage, no invented numbers or designations); a failure leaves the deterministic layer visible
and marks the AI layer `failed`/`partial`, never a fabricated success.

**A-4 Durable work.** The `job`/`attempt`/`lease` authority of `jobs` gains a typed subject: today a
Job is a Run (`job.run_id`); the C0 seal adds a subject kind for comparison work (profile build,
matrix build, series of transitions, sheet-pair batch, AI job, report build) with the same lease,
heartbeat, reclaim, pause/resume/cancel and wake-up semantics, claimed by the same worker loop and
counted against `AUDITMANAGER_WORKER_SLOTS`. This is a risk path (durable state, `W48`); the ADR
compares it with a comparison-local queue on the same Lease pattern and states why one is chosen.
No progress lives only in memory; progress is a projection of stored results.

**A-5 Compute.** Rendering and raster comparison use `pypdfium2` and `Pillow`, both already pinned
(`pyproject.toml:46`, `:48`); text words with boxes come from the PDF text layer through the
existing extractors (`pdfplumber`, `pypdf`). The engine is versioned (`ALGO_VERSION`) and results are
cached by a key over both page contents, parameters and the algorithm version, so a recomputation of
an unchanged pair is a cache hit, never a different answer. A new third-party dependency (if the
engine slice proves `numpy` is required, or for the PDF report writer) is taken only by the slice
that owns the root dependency slot in its wave, with its licence recorded; the default is none.

**A-6 AI calls.** Through «Исполнители» only: new executor work kinds (proposed
`comparison_pair_check`, `comparison_sheet_changes`, `comparison_spec`, `comparison_stage_review`,
`comparison_report`) routed in «Назначения» like `text_analysis`, with the pinned model of the routed
connection (`R-133`), recorded mode for every test, and the image channel of `EXEC-IMAGE-CHANNELS-01`
for crops (`Q-CMP-4`). Every AI job shows an estimate (sheets, images, image bytes, prompt size, model)
and starts only after an explicit consent of an expert or administrator, as in the original. Live
spend inside a wave follows `R-29`.

**A-7 Expert acts.** Stage change cards carry an expert verdict (`Принято` / `Не принято` with a
reason), append-only, keyed, expert-role (`R-60`), audited; «Подтверждено изменений» counts accepted
cards. Version comparison has no verdict in the original; its AI texts are labelled as unconfirmed.
Manual matrix edits and stage sheet links are expert acts with history; an administrator may also
reorder versions («Порядок версий» is administrator-only in the original — the ADR decides who may).

**A-8 Plain-PDF versions (`Q-CMP-5`).** `ingest` admits a plain PDF for comparison through new
operations; the stored version records its source kind; run start on such a version refuses with a
typed code (no silent fallback); the existing portal-bundle upload is unchanged.

**A-9 Screens.** Two menu entries in `web/src/shared/config/screen-registry.ts` with new routes
`web/src/app/version-comparison/` and `web/src/app/stage-comparison/` (project chosen on the screen,
since our shell has no global object); the existing version-scoped screen stays for run comparison and
finding carry-over. Own styles only (`--am-*` tokens, no UI library). Feature flag per module (a
server setting read by the screen registry) so that an unfinished module is invisible on a stand.

## 4. Slices

Sizes: S ≤ 0.5 lane-day, M ≈ 1, L ≈ 1.5–2, XL ≈ 3 (measured lane pace of PW2b/PW4, judgment).
«Seal» = the one slice of a wave that owns the contract, the migration head, the generated client,
`web/FRONTEND_LOCK.json` and the composition root for that wave; other lanes of the wave start after
it merges and do not touch those hotspots.

### Wave C0 — foundation (after PW5's `ANALYSIS-PRESETS-01` merges)

| Slice | Result | Size | Hotspots |
| --- | --- | --- | --- |
| CMP-ADR-01 | `docs/architecture/adr/ADR-0025-comparison-modules.md` + index line: A-1…A-9 decided, identity prefixes, job subject choice, work kinds, dependency stance; judged | S | none |
| CMP-SEAL-C0 | contract: plain-PDF batch upload, version order revisions, profile and tile reads, job subject; migration `0038` (or next free); error codes; generated client; pins swept by a disposable apply-and-run probe first | L | contract, migration, client, composition root |
| CMP-JOBS-01 | the typed job subject in `jobs` and `workers`, claim/lease/reclaim for comparison subjects, slot accounting, cancellation; mutation-proved | L | `src/auditmanager/jobs/**`, `src/auditmanager/workers/**` |
| CMP-INGEST-01 | plain PDF admission (single, batch, ZIP/folder), stamp reading (designation, «Изм.», date), grouping proposal confirmed by the user, version order proposal and «Порядок версий», run-start refusal for comparison-only versions | L | `src/auditmanager/ingest/**`, `src/auditmanager/documents/**` |
| CMP-PROFILE-01 | page profiles (words with boxes, stamp zone, sheet number/title, ink mask, scan flag), previews, thumbnails and tiles in the blob store, cached by content | L | `src/auditmanager/comparison/profile/**` (new), rendering of `src/auditmanager/analysis/geometry/` only through `src/auditmanager/analysis/public.py` (a one-line export there if missing, granted to this slice) |

### Wave C1 — version comparison core

| Slice | Result | Size | Hotspots |
| --- | --- | --- | --- |
| CMP-SEAL-C1 | contract and migration for matrix, manual edits, series, sheet-pair results, tiles of a pair | M | seal |
| CMP-MATRIX-01 | sheet identity across versions (max-weight assignment, thresholds, groups, absent/unmatched with candidates), manual drafts applied in a batch, undo, staleness by signature | L | `comparison/matrix/**` |
| CMP-ENGINE-01 | per-sheet deterministic comparison: registration B→A, words, geometry, colour and line style, service zones (stamp), PDF annotations, warnings, specification positions channel hook; statuses and reasons as the original; cache | XL | `comparison/engine/**` |
| CMP-SERIES-01 | series of adjacent transitions as durable comparison jobs, transition summary and verdict strings, pause/resume/cancel/«Заново» | M | `comparison/series/**` |
| CMP-VIEWER-01 | overlay/side-by-side/A/B tiles with layers and change boxes, the viewer widget with swipe, zoom, difference list, channel strip, service zones | L | `web/src/widgets/comparison-viewer/**` (new), tile reads in `comparison` |
| CMP-VC-UI-01 | screens «Проекты и этапы» and «Сравнение листов» with the matrix, transitions, queue strip, «Порядок версий», menu entry and flag | L | `web/src/_pages/version-comparison/**` (new), `web/src/widgets/version-series/**` (new), `web/src/app/version-comparison/**` (new), `screen-registry.ts` (one entry) |

### Wave C2 — version comparison AI, specifications, reports

| Slice | Result | Size | Hotspots |
| --- | --- | --- | --- |
| CMP-SEAL-C2 | contract and migration for AI jobs (estimate, consent, cancel, retry of failed sheets), descriptions, pair-check answers, specification comparison, MD and PDF reports; executor work kinds; dependency slot if the report writer needs one | M | seal, `src/auditmanager/executors/kinds.py` |
| CMP-VC-AIPAIR-01 | «ИИ-проверка сомнительных пар»: images of the sheet and candidates, accepted only with high confidence and a reverse question that agrees; manual edits win; content-keyed answers never re-sent | M | `comparison/ai_pairs/**` |
| CMP-VC-AISHEET-01 | «ИИ-описание изменений» per sheet and per series queue: packets of candidate places (tables, places, shifts) with crops and words, strict validation, tiers text/image/unverified, «Требует уточнения», MD per sheet | L | `comparison/ai_sheets/**`, the viewer side panel |
| CMP-VC-SPEC-01 | «Полные спецификации (СО)»: whole-specification extraction per version, order-independent comparison, positions channel, coverage; reuses the Form-7 extractor through `optimisation.public` | L | `comparison/specification/**` |
| CMP-VC-REPORT-01 | «Сводка изменений (MD)» (deterministic, same bytes for same data) and «Сформировать PDF-отчёт…» (AI analyst → verifier → composer, the PDF written by a program), report history and downloads | L | `comparison/report/**` |

### Wave C3 — stage comparison chain

| Slice | Result | Size | Hotspots |
| --- | --- | --- | --- |
| CMP-SEAL-C3 | contract and migration for stage pairs, assemblies, link revisions, repairs, fragments, exclusions, differences, AI reviewer/classifier rows, cards and verdicts, journal and exports | M | seal |
| CMP-STAGE-PAIR-01 | stage pairs in a project: suggestion by section and designation, expert confirmation, assemblies («сборка из N»), stage upload («Загрузить проекты»), tab 1 list and launch | L | `comparison/stage/**`, `web/src/_pages/stage-comparison/**` |
| CMP-STAGE-LINK-01 | sheet passports, automatic suggestions (type + корпус + этаж/кровля/уровень, then the weighted scale), many-to-many links as append-only revisions, explicit «без пары», thumbnail strip with drag reassignment, two-panel synchronised viewer with per-panel search, repair history with undo | L | `comparison/stage_links/**`, `web/src/widgets/stage-sheet-map/**` (new) |
| CMP-STAGE-TEXT-01 | text fragments, exclusion contract (barrier for every later step), deterministic differences changed/removed/added with box anchors; graphic regions of linked sheets from CMP-ENGINE-01 as GRAPHIC evidence | M | `comparison/stage_text/**` |

### Wave C4 — stage comparison AI, review, report; closing

| Slice | Result | Size | Hotspots |
| --- | --- | --- | --- |
| CMP-STAGE-AI-01 | AI reviewer (SAME / MOVED / CHANGED / REMOVED / ADDED / UNCERTAIN over existing fragment ids, chunks ≤ 40, all-or-nothing per group), classifier PROJECT_CHANGE / SERVICE_STRUCTURE / REVIEW with categories and titles, high-level synthesis; crops of GRAPHIC evidence allowed (`Q-CMP-4`); one bounded link-repair cycle per run | L | `comparison/stage_ai/**` |
| CMP-STAGE-REVIEW-01 | tab 3 cards with verdicts and saving, tab 4 journal with real grouping and Excel/PDF/HTML exports, menu entry and flag | L | `web/src/widgets/stage-changes/**` (new), `comparison/stage_review/**`, `screen-registry.ts` (one entry) |
| CMP-JOURNEY-01 | the browser journey for both modules on synthetic fixtures (`tools/fixtures/comparison/**`, new): upload, matrix, viewer, recorded AI, verdicts, exports | M | `tests/e2e/**` journey files named by the slice |
| CMP-CLOSE-01 | release note, CURRENT_STATE, debt rows, flags on, whole-suite measurement in halves (`D-245`), handoff for the gate | S | docs |

## 5. Order, hotspots, parallelism

- **Entry.** C0 starts when PW5's `ANALYSIS-PRESETS-01` has merged (the integrator's answer of
  2026-10-27: AR-A owns migration `0036`, PR the next; this plan takes the head after them). The
  migration numbers above are placeholders; each seal takes the then-current head + 1 and rewrites
  every pin it moves (`docs/program/CONTRACT_PIN_REGISTRY.md` and the apply-and-run probe).
- **Inside a wave**: seal first (alone), then the other lanes in parallel on disjoint paths. The
  composition root (`src/auditmanager/bootstrap/{adapters,composition}.py`) belongs to the seal; a lane
  that needs a new port wiring lists it for the seal or receives a one-line grant.
- **Between waves**: C1 needs C0; C2 needs C1; C3 needs C0 and CMP-ENGINE-01 (for GRAPHIC evidence) and
  can run beside C2 if the seals are serialised (C2 seal, then C3 seal); C4 needs C3.
- **Shared files**: `web/src/shared/config/screen-registry.ts` gets one entry from CMP-VC-UI-01 and one
  from CMP-STAGE-REVIEW-01 (different waves). Global styles are not touched; module CSS only.
- **Never**: `origin/main` (AGENTS §6), root locks outside the slot, a second writer in a worktree.

## 6. Verification

Per slice (light acceptance `R-70`): the slice's unit and integration directories on a private
database and object store, contract tests minus the `D-220` files, web Vitest/tsc/eslint for touched
web paths, a mutation proof per guard (a refusal that must fire, a raw layer an AI layer must not
change, a cache key that must change with the algorithm version, a consent that must precede a
model call), and recorded model responses only. Fixtures: a synthetic comparison corpus generated
in-tree (`tools/fixtures/comparison/**`, built on the existing `tools/fixtures/ar_corpus` PDF writer):
versions with known moved text, changed numbers, added and removed sheets, changed graphics, stamp
changes, a scan page, a split sheet, and a П/Р pair with an assembly — each with an answer key the
tests assert, not a re-captured output (`characterization-can-freeze-a-defect`).

Per wave end: one judge, then a FIX lane (`R-124`…`R-127`); whole `tests/integration` in two halves
under one hour each (`D-245`); `next build`. Before beta: the complete gate (`D-205`, needs a host
with disk) and the journey CMP-JOURNEY-01.

Live AI: off by default; a measured live check per AI slice only within `R-29` and with the owner's
key in the session, never in a lane by default.

## 7. Estimate and beta

Measured basis: PW4 (seven lanes including a contract and a migration) went from the order to the
integration branch in about 13 hours on 2026-10-27; PW2b in about one day. This plan has 22 slices in
five waves, two of them XL/L-heavy (C1, C2). Judgment: about **1.5 working days per wave**, so
**7–9 working days** of execution after PW5, i.e. code-complete P50 ≈ 2026-11-11, P80 ≈ 2026-11-17
if C0 starts on 2026-10-29. The beta forecast of 2026-10-27 (P50 05.11, P80 13.11) moves by the same
amount: **beta P50 ≈ 2026-11-17, P80 ≈ 2026-11-25**. The terms that are not measured: the engine
(XL, the original's `engine.py` alone is about 1,000 lines plus registration and tiles), the job
subject change (risk path), and the host disk (renders and tiles of 12 versions × 100 sheets).

## 8. Risks, stop conditions, rollback

- **Disk and memory**: previews and tiles are cached blobs; the profile slice measures bytes per page
  and sets a cap and an eviction rule before any batch over 50 pages; a lane stops when free disk is
  below 1.4 GiB.
- **Raster cost**: the engine runs in the worker under the slot count; one sheet pair at a time per
  slot; a page that fails to render is `needs_review` with `RENDER_FAILED`, never «Совпадает».
- **Model cost**: estimate and consent before every AI job; a job aborts on the first identity
  refusal; no automatic retry beyond provably unprocessed calls (`W53` rule).
- **Vision**: images only through executors whose image channel is verified; the accepted-risk
  record is written before CMP-SEAL-C2 merges.
- **Stop**: a seal's probe shows a pin or an enumerated set the plan did not grant → STOP and report;
  a lane needs a hotspot it does not own → STOP; an AI layer would have to modify a raw row → STOP.
- **Rollback**: each module is behind its flag; a wave that cannot finish leaves its flag off and the
  existing version-scoped comparison untouched.

## 9. Open items

1. Who may reorder versions and edit the matrix (the original: administrator for order, operator for
   links) — decided in ADR-0025 against our roles (`expert`, `admin`).
2. The PDF writer for the report (no pinned library writes PDF today) — ADR-0025 names the choice; a
   new dependency is the owner's to approve.
3. Whether the old approved sheet pairs of `0035` migrate into matrix edits or stay as history — ADR.
4. The executor routes for the new work kinds on the stand (an operator act after the code).
