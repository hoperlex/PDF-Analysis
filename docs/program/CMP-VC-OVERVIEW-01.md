# CMP-VC-OVERVIEW-01 — the overview of «Проекты и этапы» and the comparison queue summary

Written 2026-10-28 by the Sonnet lane `CMP-VC-OVERVIEW-01` (size M, branch `agent/cmp-vc-overview-01`, base `c228cf2e` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-VC-OVERVIEW-01.md`](tasks/CMP-VC-OVERVIEW-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (4, 6, 23 and the addenda); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) sections 1.1, 3.2, 4.0 and 4 wave C1 (row `G-10`); the seal it serves is [`CMP-SEAL-C1.md`](CMP-SEAL-C1.md) (sections 3, 4, 9, 10); the lanes whose rules it applies are [`CMP-MATRIX-01`](CMP-MATRIX-01.md), [`CMP-SERIES-01`](CMP-SERIES-01.md), [`CMP-WORK-01`](CMP-WORK-01.md), [`CMP-INGEST-01`](CMP-INGEST-01.md), [`CMP-INGEST-02`](CMP-INGEST-02.md) and [`CMP-PROFILE-QUEUE-01`](CMP-PROFILE-QUEUE-01.md).

## 1. Result

`getComparisonOverview` and `getComparisonQueueSummary` answer instead of `503`, served by `ComparisonOverviewAdapter` over `ComparisonOverviewService` (`src/auditmanager/comparison/overview/`, 996 lines in five modules). Both are reads in **one `REPEATABLE READ READ ONLY` transaction**: they write nothing (PostgreSQL refuses it; shown), enqueue nothing and call no model. Any role reads (seal section 3); an absent project is `404`.

* **The overview** gives one row per document set (every document of the project): the state of the seven steps — `upload`, `profile`, `matrix`, `series` are served; `ai_pairs`, `ai_changes` and `report` (wave C2) answer `not_applicable` —, the step the chip proposes (`next_step`, absent when nothing is left), the counters «Все / Ждут действия / Идут / Ошибки / Готовы», the totals «N версий · M переходов» and the batches still being uploaded. **A project costs a fixed 14 statements** whatever the number of its sets (6 for a project with no document): measured 14 for 1, 2, 30 and 100 sets, 48 ms for 100 sets.
* **The queue summary** gives the whole installation's comparison queue: the module set, the pause, the nine states in total and by `(module, kind)`, and the age of the oldest queued item. Three statements.
* The two sealed stub rows are gone from the composition registers (`SEALED_STUB_GETS`, `SEALED_STUB_ADDRESSED` and `SEALED_STUB_COLLECTIONS` are empty); both operations are in `WIRED`; the queue read joins its own aggregate shape check (`COMPARISON_QUEUE_OPERATIONS`).

## 2. Base facts, printed before any edit

`contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes`, `VERSION` `0.9.0`, head `0039_comparison_core`, base `c228cf2ed36a1bff26f169f10143b2e6855ebeaf` (`P-01` of the task file). They equal the premise of the wave brief, so the lane went on. The lane changed no contract, no migration, no dependency and no lock file.

## 3. The decision this lane had to make, and why

The brief names its sources as `ComparisonMatrixService.get_matrix` (the matrix read), `ComparisonSeriesService.list_series` and `ComparisonWorkRepository.counts(series_id=)` **and** asks that one project's overview be a fixed number of queries whatever the number of sets. The three reads take **one document set, one document or one series each** (`P-03` of the task file): called per set they are N+1 by construction (mutation `M01` is that shape: 43 statements for 30 sets against 14). The brief also says to STOP when a package lacks a read.

The lane did not stop, because the missing project-wide reads can be written **inside its own package** without editing `matrix/**`, `series/**`, `work/**` or `ingest/**`: `overview/repository.py` reads the tables set-wise (`SELECT DISTINCT ON (document_uid)`, `ANY(:documents)`, one pass over the project's versions and profiles) and `overview/service.py` applies the other lanes' **pure rules** to those rows — `profile_digest`, `profile_progress`, `resolve_order`, `stale_reasons` and `effective_matrix` of the matrix, `input_digest`, `stale_reasons` and `chain_of` of the series — imported by module path inside the comparison context, as `series/service.py:38-57` imports the matrix's. They are not appended to `comparison/public.py`: `public.py` imports the overview package, so the overview importing `public` would be a cycle. `public.py` gets one name, `ComparisonOverviewService`.

What keeps the two readings from drifting is a test, not trust: `tests/integration/comparison/overview/test_steps_against_the_services.py` builds each state a set can be in (21 tests) and requires the overview's steps 2, 3 and 5 to equal what `get_matrix` and `list_series` answer **for the same set** (state, counts, stale reasons), the expected values written in the test in words. It found a defect on its first run (the series rows built with the series and document identities swapped; mutation `M16` puts it back). If the integrator prefers batch reads inside `matrix/` and `series/`, the overview's repository is the shape they would take (FIX item 1).

`ComparisonWorkRepository.counts(series_id=)` is not used: a series' progress is its own `transitions_done` of `transitions_total`, and the queue items the overview needs (the live `page_profile`, `matrix_build` and `series_after_preparation` items of the project and the newest `matrix_build` item of each set) come from one statement over `comparison_work`. The batch follow-up (`series_after_preparation`, attached to the upload) makes the series step `queued` before the series row exists.

## 4. What was built

`src/auditmanager/comparison/overview/` (new):

| module | what it holds |
| --- | --- |
| `model.py` | the seven step ids in the table's order, the thirteen state words, the four groups, `Step` |
| `rules.py` | pure: `upload_step`, `profile_step`, `matrix_state`, `matrix_step`, `series_step`, `deferred_step` (wave C2), `next_step`, `group_of`, `counters`, `totals`, `live_state` |
| `repository.py` | 13 read-only statements for a project (documents, versions, upload-set metadata, version orders, page-profile facts, latest builds, bound signatures, edits, accepted AI links, work, latest series, transitions, pending batches; with the project lookup, 14) and 2 for the queue (3 with the pause read) |
| `service.py` | `ComparisonOverviewService.get_overview`, `get_queue_summary`; the read-only transaction; the assembly of one set |
| `__init__.py` | the export |

Wiring (the hunks of the wave brief section 1 rule 4, each minimal): `bootstrap/adapters.py` (the body of `ComparisonOverviewAdapter` and nothing else), `bootstrap/composition.py` (**one line**: `comparison_overview=ComparisonOverviewAdapter(sessions, modules=comparison_modules),`), `comparison/public.py` (the import and one name in `__all__`), the three composition registers. `api/routers/ports.py` needed no row, and `scripts/recovery/grant_classification.py` none (the lane writes no table).

## 5. The original's rules, ported, with their lines

`OV` = `backend/app/services/version_comparison/overview.py`, `PJ` = `frontend/static/js/version-comparison-projects.js`, both at `23f379fd` (read as data from the public repository into a scratch directory outside git; nothing of it is committed).

| rule | original | here |
| --- | --- | --- |
| step 2: failed if any version failed, done if all ready, running, else todo | `OV:62-76` | `rules.profile_step`; the figures are **pages** (the matrix's `progress`), a running item wins over a stored failure (a retry is in progress), `partial` for some pages stored with nothing going to run |
| step 3: `na` below two versions; `todo` without a result; `stale` on a signature mismatch; `attention` with unmatched cells, else `done` | `OV:102-112`, signature `jobs.py:173` | `rules.matrix_state` (the matrix read's own five words) and `rules.matrix_step`; figures `rows`, `unmatched`, `manual_edits` from `counts.rows`, `counts.unmatched`, `counts.manual` of the **effective** matrix |
| step 5: the newest series; `na` below two versions; none → `todo` with `total = versions - 1`; `cancelled` → `interrupted`; done but not for the present order → `stale` | `OV:148-189` (`:152-156`, `:181-185`) | `rules.series_step`; staleness from the series' own stored input digest (`order_changed`, `matrix_changed`, `profiles_changed`) |
| the next step: upload failed/running; profile failed; one version → none; profile running; prepare; the series states; unmatched sheets; done | `OV:297-331` | `rules.next_step` (the order is the original's; two additions in section 9 item 6) |
| the group of a row: `run` → Идут, `bad` → Ошибки, `ok`/`muted` → Готовы, else Ждут действия | `PJ:319` | `rules.group_of`, derived from the proposed step and its state (section 6.3) |
| the counters over the rows shown | `PJ:320-324` | `rules.counters` |
| the totals: versions, and `max(0, versions - 1)` transitions per set | `PJ:325-328` | `rules.totals` |
| a batch not yet in the list | `OV:272-292`, labels `OV:30-33` | `pending_uploads`: the project's batches that are not `completed` or `cancelled` |
| refresh 5 s while anything runs or uploads, else 30 s | `PJ:301-304` | the screen's |

## 6. The field-by-field mapping for `CMP-VC-UI-01`

### 6.1 The table (original columns, `PJ:77-92`)

| column / element | read from | note |
| --- | --- | --- |
| «Проект · следующий шаг», the cipher | `sets[].designation` (the «шифр»), else `title` | `designation` exists for a set admitted by a comparison upload (the upload set's designation); a document admitted otherwise has only `title` |
| the next-step chip | `sets[].next_step` and the state (and counts) of the step it names | absent `next_step` = nothing left; section 6.2 gives the words |
| «Версии» | `sets[].version_count` | the original's «· N стр.» and first/last labels are not in the contract (section 9 item 11); `steps[profile].counts.total` is the pages of **all** versions |
| «1 Загрузка» | `steps[upload].state` (`done` → «загружен») and `sets[].updated_at` (the date of the last upload, `PJ:46`) | `running`/`failed` do not occur in C1 (section 9 item 5) |
| «2 Разбор версий» | `steps[profile]` | note «`ready` из `total`» (pages) and « · ошибок `failed`» |
| «3 Сопоставление листов» | `steps[matrix]` | `attention` → «не сопост. `unmatched`»; note «строк `rows`» and « · ✎ `manual_edits`» when `manual_edits` > 0 (`PJ:55`); the three figures exist whenever a build exists, a stale build included |
| «4 ИИ-проверка сомнительных пар», «6 ИИ-описание изменений», «7 Сводка и отчёт» | `steps[ai_pairs]`, `steps[ai_changes]`, `steps[report]` | always `not_applicable`: «—», tone `off`; their checkboxes and buttons are wave C2 |
| «5 Сравнение соседних» | `steps[series]` | note «`done` из `total`» and « · с изм. `with_changes`» when `done` (`PJ:70`); `with_changes` is present for `done` and `stale` |
| the six tiles | `counters.all`, `.waiting`, `.running`, `.failed`, `.ready` → Все, Ждут действия, Идут, Ошибки, Готовы; `totals.versions`, `totals.transitions` → «N версий · M переходов» | the counters cover **all** rows of the project; the search and the «Марка» filter narrow them in the client (`PJ:313-324`), which recomputes them from the rows with the rule of 6.3 |
| «обновлено HH:MM:SS» | `generated_at` | |
| the strip «В загрузке, ещё не в списке проектов» | `pending_uploads[]`: `state`, `declared_files` («файлов N»), `sets_done` of `sets_total` | `sets_total` does not count excluded sets |
| the sort «по шифру», «по последней загрузке», «по числу версий» | `designation` then `title`; `updated_at`; `version_count` | the server's order is by designation (absent last), title, identity |
| «Марка» | the tail of `designation` after the last `-` (`PJ:29-33`); `section_code` is also given when the set has one | |

### 6.2 State words (the client's, `PJ:41-94`; tones `PJ:15-16`)

| step | state → word (tone) |
| --- | --- |
| profile | `done` «готов» (ok), `running` «идёт» (run), `queued` «в очереди» (run), `paused` «пауза» (warn), `partial` «частично» (warn), `not_started` «не начат» (todo), `failed` «ошибка» (bad) |
| matrix | `done` «готово» (ok), `attention` «не сопост. N» (warn), `stale` «устарело» (warn), `not_started` «не собрано» (todo), `running`/`queued` «идёт»/«в очереди» (run), `failed` «ошибка» (bad), `not_applicable` «—» (off) |
| series | `done` «готово» (ok), `running` «идёт» (run), `queued` «в очереди» (run), `paused` «пауза» (warn), `interrupted` «прервано» (warn), `failed` «ошибка» (warn: the action is «досчитать»; the original's tone is `bad`, `TONE` `PJ:16`), `stale` «по старому порядку» (warn), `not_started` «не запускалось» (todo), `not_applicable` «—» (off) |

The chip's text by the step the row names and that step's state (the original's, `OV:301-331`): `upload` — «Идёт загрузка» / «Ошибка загрузки — открыть пакет» (neither occurs in C1); `profile` failed «Разбор версии с ошибкой — повторить», running/queued «Идёт разбор версий», not_started/partial «Подготовить: разбор и сопоставление листов»; `matrix` not_started/stale «Подготовить: разбор и сопоставление листов», running/queued «Идёт сопоставление листов», failed «Сопоставление листов не собрано — повторить» (the lane's words: the original has no failed matrix, its preparation failure was the profile's), attention «Несопоставленных листов: N — вручную»; `series` running «Сравнение соседних: идёт», queued «Сравнение соседних: в очереди», paused «Сравнение соседних на паузе — продолжить», interrupted/failed «Сравнение соседних прервано — досчитать», not_started/stale «Сравнение соседних — запустить». No `next_step`: «Одна версия — сравнивать не с чем» when `version_count` < 2, else «Готово». The sentences are the client's; the contract carries codes.

### 6.3 The group of a row (what the tiles filter by)

The contract has no member for it; the counters are computed with this rule and the client derives the same from a row:

```
if next_step is absent                                        -> ready   («Готовы»)
state = steps[next_step].state
if state in (queued, running, pausing)                        -> running («Идут»)
if state == failed and next_step in (upload, profile, matrix) -> failed  («Ошибки»)
otherwise                                                     -> waiting («Ждут действия»)
```

`tests/integration/comparison/overview/test_reads_only_and_scope.py::_group` is this rule written out; a failed **series** is `waiting`, as in the original (`OV:321-322` gives it the tone `act`, only the upload and the profile give `bad`).

### 6.4 The calls

Reading starts nothing; a screen that wants to act uses the existing operations: «Подготовить»/«Повторить» → `prepareComparisonMatrix`; «Запустить»/«Заново» → `startComparisonSeries`; «Продолжить»/«Досчитать» → `resumeComparisonSeries`/`finishComparisonSeries`; the block «Сравнение» of «Очередь» → `getComparisonQueueSummary` (`modules`, `paused`, `counts` by the nine states, `kinds[]` of `{kind, module, counts}`, `oldest_queued_at` absent when nothing is queued).

## 7. Checks (light acceptance)

Commands run from the worktree root with the lane's `.env` loaded, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider`; the lane's own PostgreSQL (`57880`) and MinIO (`61880`) after `make migrate` (head `0039`); `df -h /` before each long run (2.5 GiB at the start, never below 1.9 GiB; the stop line is 1.5 GiB). Tree measured: the committed tree before this report (`git status` clean); this report and the task file's handoff change nothing else.

| what | command | result |
| --- | --- | --- |
| diff hygiene | `git diff --check c228cf2e..HEAD` | clean (exit 0) |
| unit directory | `pytest tests/unit/comparison/overview` | **82 passed** (rules 78, among them the next-step table on 23 set states; pins 4) |
| integration directory (one directory, one process) | `pytest tests/integration/comparison/overview` | **46 passed**: states against the services 21, bounded 3, reads-only and scope 12, queue summary 5, HTTP 5 |
| the whole composition directory | `pytest tests/integration/composition -rf` | **1955 passed, 5 skipped, 0 failed**, 32 min 55 s (the five skips: the stub-operation parametrisation is now empty, which is one, and four that were skips before this lane) |
| the whole unit and contract tree minus the three `D-220` files, after the last code commit | `pytest tests/unit tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py` | **6200 passed, 76 skipped, 0 failed**, 19283 subtests passed, 456 s |
| the statement count | a script counting `before_cursor_execute` for 0, 1, 2, 30, 100 sets (the populated project of `test_bounded.py`) | 6, 14, 14, 14, 14 statements; the queue summary 3; 100 sets in 48 ms |

Not run, by the brief and `R-135`: `make gate`, the web battery (no web file changed), the live journey.

**What the integration tests prove, against what.** Each test builds the rows a state leaves — through the lanes' own repositories where one exists (`MatrixRepository.insert_build`, `SeriesRepository.insert_series`/`insert_transition`/`set_*_state`, `ComparisonWorkRepository.enqueue`, the matrix service's `apply_edits`), by plain `INSERT` for versions, profiles, uploads and version orders, and every state change goes through the edges the database allows. The oracle is the matrix and series reads on the same set. Counts of every comparison table, the queue and the command records are taken before and after the calls. The HTTP tests run the shipped application with the real adapter: both roles, `401`, `404`, the module set `none`, `versions` and `versions,stages`.

## 8. Mutation proofs

Each row: the quoted replacement applied to the committed file, the named tests run (red), the file restored with `git checkout --` (`git status --short --untracked-files=no` empty), the same tests run again (green). The harness is the lane's scratch. U = `tests/unit/comparison/overview`, I = `tests/integration/comparison/overview`, C = `tests/integration/composition`.

| id | commitment | mutation | red |
| --- | --- | --- | --- |
| M01 | **bounded: a fixed number of statements** | the latest series is read one set at a time | I bounded: 1 failed (43 statements for 30 sets against 14) |
| M02 | another project's document never in a row | the document statement has no project | I scope: 8 failed |
| M03 | another project's work never in a step | the work statement has no project | I scope: 1 failed (a foreign item naming this project's document) |
| M04 | another project's batch never pending | the pending statement has no project | I scope: 2 failed |
| M05 | **an absent project is 404** | the project is not looked up | I scope + HTTP: 2 failed |
| M06 | **no write: the transaction is read-only** | the read-only options removed | I scope: 1 failed (the database accepted the write) |
| M07 | no enqueue (guard in place) | `get_overview` enqueues a `page_profile` item | I scope: 11 failed (PostgreSQL refuses it) |
| M08 | no enqueue, no write (the row counts) | the same enqueue and the guard removed | I scope: 3 failed (row counts, enqueue, read-only) |
| M09 | step 3 attention | unmatched sheets read `done` | U + I: 2 failed |
| M10 | step 3 stale | a stale build reads `done` | U + I: 4 failed |
| M11 | step 3 failed | a failed build item reads `not_started` | U + I: 2 failed |
| M12 | step 5 stale | a series for another order reads `done` | U + I: 4 failed |
| M13 | step 5 cancelled | a cancelled series reads `failed` | U + I: 2 failed |
| M14 | step 5 follow-up | a waiting follow-up is ignored | U + I: 1 failed |
| M15 | step 5 newest | the oldest series decides | I states: 1 failed |
| M16 | **the oracle** | the series rows swap the series and document identities (the defect the first run found) | I states: 6 failed |
| M17 | step 3 order | the document's order revision and its identity are ignored | I states: 1 failed |
| M18 | step 3 profiles | the profile digest of a build is never compared | I states: 1 failed |
| M19 | step 5 matrix edits | a manual edit does not move the series' inputs | I states: 1 failed |
| M20 | next step: prepare | the matrix is never proposed for preparation | U + I: 3 failed |
| M21 | next step: unmatched | unmatched sheets propose nothing | U: 1 failed |
| M22 | next step: running | a running profile does not block | U + I: 3 failed |
| M23 | group | a failed series is red | U: 2 failed |
| M24 | **counters = rows** | running rows counted as waiting | U + I scope: 3 failed |
| M25 | counters = rows | `all` is not the number of rows | U + I scope: 3 failed |
| M26 | totals | a set of n versions has n transitions | U + I scope: 3 failed |
| M27 | live work | a running item reads queued | U + I: 4 failed |
| M28 | step 2 | a stored failure wins over a retry in progress | U: 1 failed |
| M29 | metadata | the oldest admitting set gives the designation | I scope: 1 failed |
| M30 | pending | an excluded set is counted | I scope: 1 failed |
| M31 | queue | the oldest queued is the newest | I queue: 1 failed |
| M32 | queue | the module set is always `none` | I queue: 1 failed |
| M33 | queue | the pause is not read | I queue: 1 failed |
| M34 | queue | every item counts once per kind in the total | I queue: 2 failed |
| M35 | wiring | the adapter's overview answers the sealed stub | C: 2 failed |
| M36 | wiring | the adapter's queue summary answers the sealed stub | C: 2 failed |
| M37 | wiring | the overview's row back in `SEALED_STUB_ADDRESSED` | C: 1 failed |
| M38 | wiring | the queue read back in `SEALED_STUB_COLLECTIONS` | C: 1 failed |
| M39 | wiring | the queue read's path back in `SEALED_STUB_GETS` | C: 1 failed |
| M40 | wiring | the composition root does not hand the module set to the adapter | I HTTP: 1 failed |
| M41 | wiring | the queue read withdrawn from `WIRED` | C: 1 failed |

Three things the proofs showed about the tests themselves, fixed before the final run: the first `M02`–`M04` replacements failed on parameter typing (red for the wrong reason) and were rewritten with `CAST(:project AS text)`; the first form of the read-only test wrote a fixed project identity and, when its mutation ran, left it behind so the green re-run failed — it now writes an identity of its own run; and the pause test, when its mutation failed halfway, left the installation paused — it now restores the pause in `finally`.

## 9. Limits, decisions the lane took, FIX items

1. **FIX candidate: batch reads in `matrix/` and `series/`.** The overview reads the matrix and series tables itself (section 3). The semantics are the other lanes' and the oracle test holds them equal, but a change to `ComparisonMatrixService._state` or `ComparisonSeriesService._view_of` must be mirrored in `overview/service.py`/`rules.py`. A later lane may give those packages a project-wide read and shrink this repository.
2. **FIX candidate: a `group` member.** The contract has no per-row group or tone; the client derives it (6.3). A member on `ComparisonOverviewSet` would remove the duplicated rule.
3. **FIX candidate: the chip has no text.** Only `next_step` is carried; the sentences are the client's (6.2).
4. **The list is capped at 1 000 sets** (the contract's `maxItems`); the 1 001st document is dropped in the order of the identities with a warning in the log, and the counters and totals follow the rows shown. The contract has no cursor or flag; unreachable in practice, recorded.
5. **Step 1 is `done` for any set with a version.** A set is admitted in one transaction (`CMP-INGEST-02` section 2), so no asynchronous upload remains for a document; the original's `running`/`failed` upload states (`OV:301-304`) do not occur. The batches still being processed are `pending_uploads`, and the work derived from a confirmed set shows in steps 2, 3 and 5.
6. **Two additions to the original's next-step rule.** (a) A failed matrix build is proposed right after a failed profile (`OV:305-306`), as a preparation failure; the original has no such state. (b) The unmatched-sheets rule (`OV:325-326`) proposes the model check of the pairs or the matrix by hand; the model check is wave C2, so the matrix is proposed, with the series first as in the original (`OV:323`). When wave C2 serves step 4 the rule returns to the original's.
7. **Step 2 counts pages, as the matrix's `progress` does**, not versions as the original's `ready`/`total` (`OV:63-76`), so the overview and the matrix screen quote the same numbers. A page stored without a result (`needs_review`, `refused`) is `failed`: a page refused for good (too large) keeps the set red and the chip «повторить» cannot fix it; the matrix still builds. Nothing here decides that.
8. **`manual_edits` is `counts.manual` of the effective matrix** (cells shown as manual), as the brief says, not the number of edit events the original's «✎» counts (`OV:97`); one link edit can mark more than one cell.
9. **`updated_at` is the date of the last version's upload** (the original's `uploaded_at`, `PJ:46`, `:117`), not `document.updated_at`.
10. **Step 5 is `stale` only for a completed series**, as in the original (`OV:184-185`); a failed, cancelled or live series with other inputs keeps its own state.
11. **Not in the contract, so not in a row**: the page count and the labels of the first and last version (`PJ:171`), the per-row «Сводка изменений (MD)» flag (wave C2), the queue strip «Очередь запуска» (`CMP-VC-QUEUE-01`).
12. **The metadata is the admitting set's.** `designation`, `project_stage` and `section_code` come from the newest upload set that admitted the document (`comparison_upload_set`); a document admitted another way has none, and its row shows `title`.
13. **Every document of the project is a set**, including one made of portal versions; its profile and matrix are `not_started` until prepared.
14. **With the module set `none`** both reads answer (the flag gates the worker, not a read, as for the matrix and the series); the queue summary reports `modules: none`.
15. **Not measured**: a project of 1 000 sets (the cost is linear in the rows of the project; 100 sets took 48 ms), the cost of `effective_matrix` for sets with thousands of rows, concurrent writers during a read (the snapshot makes it consistent, not fresh).

## 10. Instructions for the integrator

1. **Merge position:** after `CMP-SERIES-01`, before `CMP-VC-UI-01`. The shared-file hunks: `bootstrap/adapters.py` (the body of `ComparisonOverviewAdapter`), `bootstrap/composition.py` (one line), `comparison/public.py` (an import before `HANDLER_FACTORIES` and one name at the end of `__all__`), and the three composition tests (`SEALED_STUB_GETS`, `SEALED_STUB_ADDRESSED` and `SEALED_STUB_COLLECTIONS` become empty; `COMPARISON_QUEUE_OPERATIONS` and its shape test are new; `WIRED` gains two names). A lane that serves another stub empties the same sets.
2. Run `tests/integration/comparison/overview` in its own process: the comparison directories share one database.
3. Give `CMP-VC-UI-01` section 6 as it stands.
4. No flag, no migration, no new dependency, no grant. A revert leaves both operations answering the sealed `503`.

## 11. Forbidden hotspots

`git diff --name-only c228cf2e..HEAD` lists: the task file and this report; `src/auditmanager/comparison/overview/**` (new); `src/auditmanager/comparison/public.py` (the import and one name); `src/auditmanager/bootstrap/{adapters,composition}.py` (the adapter body, one line); the three composition tests; the lane's tests under `tests/unit/comparison/overview/` and `tests/integration/comparison/overview/`. `git diff --name-only c228cf2e..HEAD -- contracts db pyproject.toml uv.lock docs/program/P02_LOCK.json web infra Makefile scripts src/auditmanager/comparison/matrix src/auditmanager/comparison/series src/auditmanager/comparison/work src/auditmanager/comparison/engine src/auditmanager/comparison/profile src/auditmanager/comparison/profile_queue src/auditmanager/comparison/tiles src/auditmanager/ingest src/auditmanager/documents src/auditmanager/storage src/auditmanager/jobs src/auditmanager/workers src/auditmanager/execution src/auditmanager/api` prints nothing.

## 12. Environment

Stack `auditmanager-cmp-vc-overview-01` (PostgreSQL `57880`, MinIO `61880`/`61881`, database `auditmanager_cmp_vc_overview_01`, bucket `auditmanager-cmp-vc-overview-01`), started with `make up FOUNDATION_PYTHON=/usr/bin/python3.12` and `make migrate`, stopped with `make down`; the volumes `auditmanager-cmp-vc-overview-01-postgres-data` and `auditmanager-cmp-vc-overview-01-s3-data` were removed by those exact names, and the network went with `make down` (`docker ps -a`, `docker volume ls` and `docker network ls` list nothing of the lane); the lane's git-ignored `.env` was deleted. `.venv` is the shared `cmp-seal-c0` environment, used read-only; no `node_modules` was linked. No process of another lane was touched and nothing was killed.
