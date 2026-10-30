# CMP-VC-AISHEET-01 — the AI description of sheet changes: the packet, the checked description, the per-series run, the single sheets, the review list, the Markdown of a sheet

Written 2026-10-29 by the Sonnet lane `CMP-VC-AISHEET-01` (size L, branch `agent/cmp-vc-aisheet-01`, base `0f6a008d` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-VC-AISHEET-01.md`](tasks/CMP-VC-AISHEET-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (3, 4, 10, 11, 12, 14, 15, 16, 17-23 and the addenda); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) (`A-6`, `A-8`, `A-12`, `R3-02`, `R3-08`); the tables and the refusals are the seal's ([`CMP-SEAL-C2.md`](CMP-SEAL-C2.md) sections 3, 4, 8, 9); the core it builds on is [`CMP-AI-JOBS-01.md`](CMP-AI-JOBS-01.md) (its section 2 is the API this lane follows); the wave brief is [`dispatch/CMP-WAVE-C2.md`](dispatch/CMP-WAVE-C2.md).

## 1. Result

The fifteen operations of `ComparisonAiSheetAdapter` answer instead of `503`: `estimate`, `get`, `start`, `pause`, `resume`, `cancel`, `finish`, `dequeue` and `retry` of `ComparisonAiSheetChanges`; `getComparisonSheetDescription`, `startComparisonSheetDescription`, `estimateComparisonSheetDescription`, `listComparisonSheetDescriptionHistory`, `streamComparisonSheetDescriptionMd` and `listComparisonReviewSheets`. The lane is the `sheet_changes` method of the shared AI-job core: it supplies an `AiMethod` and a work handler of kind `comparison_sheet_changes`, writes `comparison_ai_sheet_item` and `comparison_sheet_description`, and never writes `comparison_ai_job`.

Per sheet pair of a finished transition that has differences, the handler builds the original's packet from the engine's **raw** rows (tables found by their ruling lines, places, shifts; the words around them; at most eight pictures), asks the routed model once through the spend wrapper, checks the answer by program and stores the description **content-keyed** by the pair's stored result, the prompt version and the pinned model, so a stored description is never requested again. An added or removed sheet is described on its own (what is on it). The description never rewrites the raw evidence; every value carries a tier (`from_text`, `from_image`, `unverified`), a claim the raw evidence does not contain is `unverified` and its change is `unclear`, never `confirmed`, and every stored description says in its data that no engineer has confirmed it and whether it is a recorded answer.

## 2. Base facts, printed before any edit

`P-01` of the task file: contract `1.11.0`, **176 paths / 198 operations / 517 schemas**, `VERSION` `0.9.0`, head `0040_comparison_ai_reports`, base `0f6a008d91f4fbdf1fd7a3b2561dae57392fa8da`. Equal to the brief's premise, so the lane went on. Nothing in `contracts/**` or `db/migrations/**` was changed; no column was missing.

## 3. What was built

| path | what it holds |
| --- | --- |
| `src/auditmanager/comparison/ai_sheets/schema.py` | the answer schemas (`SHEET_CHANGES_SCHEMA`, `SINGLE_SCHEMA`), the prompts, the version names and their digests, the small validator of an answer against those schemas |
| `.../tables.py`, `.../candidates.py`, `.../geometry.py` | the rows of a drawing's table from its ruling lines; the pointers of the engine's stored result and the candidates (`table`, `place`, `shift`) with the fate of every pointer |
| `.../material.py`, `.../images.py` | the seam `SheetMaterial` (words, lines and pictures of the stored page profiles; the real one cuts crops from the stored tile pyramid and never calls PDFium); the pictures (stack, frames, limits) |
| `.../packet.py` | the packet: candidates, planned or rendered pictures (at most eight), the text for the model |
| `.../check.py`, `.../description.py` | the program's check of an answer (tiers, completeness, service phrases), the stored description, the contract shapes, the review reason, the Markdown of a sheet |
| `.../describe.py` | the run of one sheet through `ComparisonModelCaller` (launches, technical retry, context request, coverage pass) and the single sheet |
| `.../repository.py`, `.../views.py` | the statements of the two tables and the reads; the eleven states, the progress of a transition, the review list |
| `.../method.py`, `.../service.py`, `.../handler.py` | the `AiMethod` (counts, work items), the fifteen operations over the core, the work handler and its `drain` item |
| `comparison/public.py` | an import block and eleven names; `sheet_changes_handler` appended to `HANDLER_FACTORIES` |
| `bootstrap/adapters.py`, `bootstrap/composition.py` | the body of `ComparisonAiSheetAdapter` (the module-flag refusal first in every method) and its one constructor expression |
| registers | `SEALED_STUB_GETS` (7), `SEALED_STUB_ADDRESSED` (7), `WIRED` (15), `SEALED_NOT_YET_WRITTEN` (`comparison_ai_sheet_item`, `comparison_sheet_description`), the `HANDLER_FACTORIES` pin of `test_handler_unit.py` (`test_composition_unit.py` enumerates no kind and needed no edit) |
| `tests/unit/comparison/ai_sheets/**` , `tests/integration/comparison/ai_sheets/**` | the tests of section 7 |

## 4. The original's rules and prompts ported, with their lines

`O` = `backend/app/services/version_comparison_ai/` at `23f379fd`, read from the raw files into a scratch directory outside git; the lines are those of those copies.

| rule | original | here |
| --- | --- | --- |
| the prompt (13 rules, data fenced by `{{BEGIN}}`/`{{END}}`) | `O/prompts/sheet_changes.md:1-48` | `schema.PROMPT_TEMPLATE`, byte for byte; `packet.render_prompt` ← `O/sheet_changes/pack.py:334-340` |
| the answer schema (all properties required; «нет значения» is an empty string) | `O/sheet_changes/schema.py:10-104` | `schema.SHEET_CHANGES_SCHEMA` |
| the single-sheet prompt and schema | `O/sheet_changes/single.py:30-66` | `schema.SINGLE_PROMPT`, `SINGLE_SCHEMA` |
| a pair is described unless the engine says `same` / `same_zones_changed`; an added or removed sheet is described alone | `O/jobs.py:119-138` (`SC_SKIP_STATUSES`, `_sc_items`) | `views.eligible`, `method.SheetChangesMethod.eligible_pairs` |
| a pointer's role: service / label move / whitespace / revision tag excluded, the rest strong; a shift is weak | `O/sheet_changes/collect.py:63-91` | `candidates._role` |
| candidates: tables by the ruling lines; places by clustering (45 pt, 650 pt); a shift outside any place; the ledger | `O/collect.py:30-50`, `:212-360`, `:365-454` | `candidates.collect`, `_tables`, `_clusters`, `_place_candidate` |
| rows of a table, header words, key of a row | `O/sheet_changes/tables.py:18-186` | `tables.py` |
| pictures: overview with frames, shared crops for neighbouring places, the table of A over B; dpi from the text height | `O/pack.py:34-41`, `:69-101`, `:120-201` | `packet._plan_images`, `_place_plan`, `_table_plan`, `_render` |
| the text of the packet (candidates, rows, words, pointers, other sheets) | `O/pack.py:204-331` | `packet.render_data`, `_marks_wanted` |
| other sheets that name the same designation, only text, at most 2 per designation | `O/context.py:170-206` | `material.find_marks_in` |
| the check: schema, packet id (typo 0.8), ids of candidates and pictures, tiers `text` / `image` / `unverified`, `text_correction`, service phrases, reasons, completeness | `O/sheet_changes/validate.py:31-241` | `check.check` |
| the state of a sheet | `O/validate.py:244-263` | `check.state_of`, `model.STATE_LABELS` |
| the limits of one sheet: 3 launches, 6 context requests, 6 extra pictures; the context request is executed by the program inside the two versions; the coverage pass | `O/sheet_changes/run.py:33-36`, `:57-142`, `:147-272` | `describe.describe_pair`, `resolve_context` |
| the single sheet: one call, no before/after | `O/sheet_changes/single.py:73-197` | `describe.describe_single`, `description.check_single` |
| the result, the disclaimer «не подтверждено инженером», the declared items | `O/sheet_changes/report.py:305-356` | `description.build_description`, `views.declared_of` |
| the Markdown of a sheet | `O/report.py:367-388` | `description.sheet_markdown` |
| why a `partial` sheet is to be checked («Проверить») | `O/sheet_changes/view.py:154-168` | `description.review_reason` |
| the per-transition progress («Листов / Изм. / Вопр. / Ошибок / Проверить / Обращ.», tokens, time) | `O/sheet_changes/series_ai.py:127-148`, `:162-219` | `views.transition_progress` |
| one job per series, a retry of the failed sheets only, «Досчитать», «Убрать из очереди» | `O/series_ai.py:88-125`, `:295-402` | the core's state edges; `method.SheetChangesMethod.work_items` (modes `LEFT`, `FAILED`) |

## 5. Where this port differs from the original, and why

1. **The evidence is this tree's, not the original's records.** The engine stores one box for a text change and for a region, on the canvas of page A (`comparison_sheet_pair_result.result`: `text_changes`, `differences`, `service_notes`, `aligned_blocks`); the original's `records.build` had a box on each side. The box on page B is the inverse of the engine's registration matrix applied to it (`geometry.a_to_b_page`). A region of the class `text` that overlaps a text change is **linked** to it (the original's `group == "linked"`, `collect.py:82-83`); the layers `within_tolerance`, `noise` and the service zones are excluded as the engine's side-products (reasons `engine_noise`, `service`). Service notes are excluded as `service`.
2. **At most eight pictures per request** (`A-12`, ADR-0025 decision 18). The original sends every picture it builds. Here the overview comes first, then the tables, then the places (the larger first); what does not fit is told to the model («Изображения: нет — изменение текстовое; при необходимости zoom») and stays a candidate it must sort. A follow-up request (the context round, the pass over unsorted candidates) carries the extra pictures and as many of the first request's as fit, the overview first. `build_request` refuses a ninth and holds the pictures to 16 MiB each and 32 MiB in all.
3. **No overlay picture and no drawn captions.** The engine's mask is a packed format of its own; the packet reads raw boxes only. Pillow's default font has no Cyrillic, and the prompt lists the pictures anyway (`I2 — таблица: сверху A, ниже B`). The overview carries a frame and the label `O3` per candidate.
3. **Pictures are cut from the stored tile pyramid**, never rendered in the API or the worker by PDFium (`material.crop_from_tiles`): the finest level whose crop fits the picture, the covering tiles pasted and cut to the box. Levels 0 and 1 are rendered on request by the profile reader in its ceilinged child.
4. **A technical retry is for an unusable answer or a proven non-delivery only.** The original also retried `UNKNOWN` and `TIMEOUT` (`run.py:36`); ADR-0025 decision 5 forbids sending again what may have been sent. The 429 waits (20 .. 600 s, `run.py:198-212`) are the queue's retry back-off (`CallFailed(retry_safe)` becomes `Failed(retry=True)` only for a sheet that has no usable answer), not a sleep inside a handler.
5. **No cache directory.** The stored description is the cache; its content key is looked up **before** any call (the handler's first step).
6. **Two additions to the check** (ADR-0025 decision 20 and the brief): the **summary** and the **place** of an item are read for numbers and designations that no evidence holds (`SUMMARY_UNSUPPORTED`, `PLACE_UNVERIFIED`), and the tier is kept for the two sides apart (`was_tier`, `now_tier`). An item is `confirmed` only when every value is `from_text` or `from_image`, the model called nothing unclear and the summary and the place hold nothing the evidence lacks.
7. **A sheet with no candidate is described by the program, with no call** (state `partial` when the engine left notes, else `no_construction_changes`; `calls` 0, `model` `program`). The original asked the model with an empty list.
8. **A single sheet** gets the original's one-call description; its answer is checked against the sheet's own text (a mark that is not on the sheet is dropped and said in the issues; a detail or a number the text lacks is `unverified`), and it is served as changes (`added` with a `now`, `removed` with a `was`) because the contract's description has no other place for it.
9. **The table finder's header words** gain the column words of an electrical load table (`гр.`, `нагрузк`, `кабел`, `автомат`, `мощност`, `длин`, `сечен`, `напряж`): the corpus sheet E03 has none of the original's words but «№», so the original's list would have read its table as a place. `test_corpus_pages.py` holds this to the real PDF.
10. **The estimate does not look for the other sheets** that name a designation (that reads every page of two versions); it adds an allowance of two lines of 900 characters to a packet that names designations. The run looks (`material.find_marks`).
11. **The job's end is a separate, unlinked `drain` item** (section 7, FIX item 2).

## 6. Decisions this lane made (each is one place to change)

1. **The content key** of a description is the SHA-256 of `{project, kind (pair or single), the content key of the stored result (or of the page profile of a single sheet), the prompt version with the start of its digest, the pinned model}` (`repository.content_key`). The job, the pair, the time and the user are not in it, so a second series over the same pages, or a pair job over a sheet a series described, finds the stored row. `UNIQUE (project_uid, content_key)` is the database's guard; `insert_description` answers the stored row when the key exists.
2. **The estimate op answers by what the series is doing.** While the latest job is paused for `overrun` or `route_changed` it is the estimate of **what is left** (the consent a resume asks for; otherwise the client could never learn that digest); with `only_failed` it is the estimate of the failed sheets for the latest job's `restart` flag (a retry's consent); otherwise it is the start's.
3. **A start with `restart` is consented to the digest of the estimate without it** (the estimate op has no `restart`): the service checks the presented digest against it (a stale one is still `comparison_estimate_stale`) and starts the restart scope under that scope's own digest. `restart` makes the job list every eligible sheet; the ones with a stored description are resolved by the handler without a call.
4. **Eligible sheets** are the pairs of a `completed` transition whose state is `done` and whose status is `different` or `needs_review` with a result, or `added`/`removed` (described alone). `same`, `same_zones_changed`, `unmatched` and unfinished pairs are not described (`engine_same` / `not_processed` are derived states).
5. **The state of a pair is derived on every read** (`views.derive_state`), never stored: a waiting or running item of a live job; else the newest stored description (`stale` when its `prompt_version` is another prompt's); else a failed or cancelled item; else `engine_same` / `not_processed`.
6. **The sheet item rows are written in `work_items`** (the method's only write; the rows are this lane's own): a cancelled job or a waiting sheet then has a row to show. The handler moves them `queued -> running -> done | failed | queued`.
7. **The progress of a transition** is derived from the current state of its eligible pairs (done, changed, questions, failed, to check) and from the latest job's items (calls, tokens, seconds), so a stored description counts as done whichever job made it.
8. **The «declared» items** are read from the pair's permit record at read time (`ComparisonAiDeclaredItem.reference` is the permit state code), not stored in the description, which is shared by every pair over the same result.
9. **A refusal that pauses the job yields the item** instead of failing it (the core's doc returns `refused.as_outcome()`): the in-hand sheet continues after the resume. An item of a paused job is offered again every 30 s and yields again until the resume.
10. **`model_identity`** of a stored description is the pinned model, `recorded` for a recorded answer, `program` for a description made with no call; `recorded` is true only when a recorded answer was used.
11. **The Markdown** is built from the stored description and the pair's header (version ordinals, pages, declared items): no time, no row identity, no dictionary order. The same description gives the same bytes; the state line is the description's own, not the derived one.

## 7. Safety proofs (mutation)

Each mutation changed one exact piece of the file named, the tests named by the driver ran **red**, the file was restored with `git checkout`, the same tests ran **green**, and the file was byte-equal to the original afterwards (driver `mutate.py` in the lane's scratch, outside git; the tree was clean after each). Counts are pytest's, over the unit and integration files that cover the commitment (the test set of M03b is `test_schema_keys_and_material.py` alone; the others name two or three files).

| # | mutation | file | red | restored |
| --- | --- | --- | --- | --- |
| M01 | the module gate: the refusal never fires | `adapters.py` | **2 failed, 2 passed** | 4 passed |
| M02a | a value absent from the raw evidence gets the tier from_text | `check.py` | **3 failed, 31 passed** | 34 passed |
| M02b | a place absent from the raw evidence is not noticed | `check.py` | **2 failed, 32 passed** | 34 passed |
| M02c | a number absent from the raw evidence in the summary is not noticed | `check.py` | **2 failed, 32 passed** | 34 passed |
| M02d | an item with an unverified value stays "confirmed" | `check.py` | **2 failed, 32 passed** | 34 passed |
| M03a | a stored description is requested again (the handler's lookup of the content key) | `handler.py` | **1 failed, 15 passed** | 16 passed |
| M03b | the content key forgets the project | `repository.py` | **1 failed, 12 passed** | 13 passed |
| M03c | the estimate does not see the stored descriptions | `method.py` | **1 failed, 20 passed** | 21 passed |
| M04 | a retry takes every sheet that lacks a description, not the failed ones | `method.py` | **1 failed, 16 passed** | 17 passed |
| M05 | the Markdown carries a clock | `description.py` | **3 failed, 45 passed** | 48 passed |
| M06 | the packet may hold twelve pictures | `packet.py` | **3 failed, 35 passed** | 38 passed |
| M07 | the model is called without the spend wrapper | `describe.py` | **12 failed, 4 passed** | 16 passed |
| M08 | a cost over the consent does not stop the job | `describe.py` | **2 failed, 27 passed** | 29 passed |
| M09 | an outcome nobody knows is not a stop | `describe.py` | **2 failed, 27 passed** | 29 passed |
| M10 | the adapter takes every actor for an expert | `adapters.py` | **1 failed, 3 passed** | 4 passed |
| M11 | the adapter ignores the caller's key | `adapters.py` | **1 failed, 3 passed** | 4 passed |
| M12 | a worker that lost its lease publishes | `handler.py` | **1 failed** | 1 passed |
| M13 | no sheet hands the job its end | `handler.py` | **7 failed, 14 passed** | 21 passed |
| M14 | a description of another prompt is not stale | `views.py` | **3 failed, 45 passed** | 48 passed |
| M15 | the tag of the current change is not left out | `candidates.py` | **3 failed, 7 passed** | 10 passed |
| M16 | a sheet with no candidate is sent to the model | `handler.py` | **7 failed, 14 passed** | 21 passed |
| M17 | a text correction needs no second representation | `check.py` | **1 failed, 17 passed** | 18 passed |
| M18 | a restart is consented to without checking the digest the user saw | `service.py` | **1 failed, 15 passed** | 16 passed |
| M19 | a candidate left in no list does not make the sheet partial | `check.py` | **2 failed, 32 passed** | 34 passed |
| M20 | the request does not hold its pictures to the limits | `describe.py` | **1 failed, 8 passed** | 9 passed |

**M04 survived once, and what it showed.** The first tests of a retry ran after a clean run in which the one failed sheet was also the one sheet without a description, so "the failed sheets" and "the sheets without a description" gave the same answer and the mutation (`return lacking`) stayed green. The test `test_a_retry_leaves_alone_the_sheets_that_were_cancelled_and_have_no_description` now cancels the job with two sheets waiting; the mutation is red (row above), and the real defect that the test found was fixed in the same commit: those two sheets kept a `queued` row in a job that was retried, and a sheet waiting in a finished job showed `queued` instead of `cancelled`.

The brief's commitments and where they are shown: **a claim absent from the raw evidence is never confirmed** (M02a-d, and `test_check.py`, `test_safety.py`); **a stored description is never re-requested** (M03a-c); **a retry touches only the failed sheets** (M04); **the Markdown is byte-stable** (M05); **at most eight pictures per request** (M06, M20); **the module gate** (M01); **the expert role and the key replay** (M10, M11); **the spend before the call** and **a cost over the consent** (M07, M08), **an unknown outcome is never sent again** (M09).

## 8. Checks (light acceptance; the stack is the lane's own: `auditmanager-cmp-vc-aisheet-01`, ports 57970 / 61970 / 61971, head `0040`)

The integrator ran these checks on the merged C2 tree after SPEC and AIPAIR. Python used
`AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, `PYTHONPATH=$PWD/src`, `-p no:cacheprovider` and a basetemp under
`/tmp/pytest-cmp-int-aisheet/`; the integration commands loaded the `cmp-int` `.env` and used its migrated `0040` stack.

| check | result |
| --- | --- |
| `tests/unit/comparison/ai_sheets tests/unit/comparison/engine` | **404 passed** in 60.27 s |
| `tests/integration/comparison/ai_sheets` | **43 passed** in 16.58 s |
| three composition registers (`test_router_answers.py`, `test_an_absent_parent_is_not_an_empty_page.py`, `test_comparison_ai_stub_operations.py`) | **158 passed, 1 skipped, 1 warning** in 27.57 s |
| `tests/integration/recovery/test_grant_classification.py` | **35 passed** in 9.61 s |
| `scripts/recovery/grant_classification.py --verify-script infra/deploy/apply-grants.sh` | exit 0 |

The first integration passes exposed test assumptions about an empty database: unscoped reads could select another
project's AI job or count another project's rows. The tests now use the job they started and scope counts to their
project or series. One adapter test also read the nonexistent `first.job` instead of `first.job_id`. These are test
corrections; the method's product behavior is unchanged. The whole comparison directory, whole composition directory,
unit battery and contract battery remain wave C2 integration checks after the other methods merge.

## 9. Limits, risks, FIX items

**FIX items for the wave's FIX slot or the integrator.** None blocks the merge of this lane; items 1 and 2 are the ones that make the feature work live.

1. **The live model route and the crops reach a runner by a seam this lane could not close.** The handler takes its call route from a `ModelRoutes` (adapter, pinned model, revision), because `bind_connection` needs the worker's private ring, the destination policy and a `KindRuntime`, and `WorkDependencies` carries none of them. `HANDLER_FACTORIES` holds `sheet_changes_handler(dependencies)`, built with no route source: **a job started on a live route ends `failed` with the reason `executor_adapter_unavailable`** (the sheet's item says so too), never silently. The composition root has to hand the handler a `ModelRoutes` (one change of `build_comparison_work`, which is the seal's and CMP-WORK-01's file; the four AI lanes share it). A **pull** connection also needs the bytes of every crop in the blob store under the descriptor's blob id when the runner claims the task (`CMP-EXEC-IMAGES-01` section 2); the handler does not store them. All tests run in recorded mode.
2. **The core cannot complete a job from the job's own last item.** `ComparisonAiJobService.complete_if_drained` counts every live item of the job, the caller's included, so the last sheet cannot complete its job. This lane enqueues one **unlinked** `drain` item per job (kind `comparison_sheet_changes`, payload `drain_job_id`, dedupe key `sheet_drain:<job>`, no `comparison_ai_job_id`), which polls while sheets are live and completes the job. An `excluding_work_id` argument would remove the workaround; the other lanes meet the same gap.
3. **The estimate operation has no `restart` and no job in its address.** A consent is to one digest that binds the scope's `restart` flag and the mode, so decisions 2 and 3 of section 6 bridge it in the service. If the owner wants `restart` and the mode named in the contract, that is a contract change (an additive query parameter).
4. **`ComparisonAiChange` has no `summary`, `fields` or `members`.** The 1-2 sentences of an item («объект/место — было → стало»), its fields and its members live in the stored description and in the Markdown of the sheet; the contract's item carries the object, the place, `was` and `now` (the fields joined) and their tiers. A single sheet's content is served as changes (`added`/`removed`; the first, `s0`, is the summary). A richer contract is an additive change.
5. **`CallRefused(pauses_job)` yields the item** where the core's doc (section 2.5) returns `refused.as_outcome()` (a failed item). A failed item would not come back with the resume. An item of a paused job that was in hand when it paused is offered again every 30 s (`PAUSED_WAIT_SECONDS`) and yields until the resume: one claim per 30 s per such item (one slot, so one).
6. **Crops are an opaque blob with no row that references them** once a live pull route stores them; `blob_reference_audit.py` will list them unreferenced (not this lane's file).
7. **`comparison_ai_sheet_item.state = 'skipped'`** is never written (a sheet that needs no model gets a description with no call and is `done`).

**Limits.**

* Nothing was run live. The recorded answers are filed under the digest of the request the handler builds through the same code (`conftest.Lab.packet_of`); a prompt edit therefore moves every digest, and the pin in `test_schema_keys_and_material.py` turns red first.
* The packet is built from the engine's stored result and the page profiles; it was tested on hand-made pages and on two sheets of the corpus VS-1 (`test_corpus_pages.py`: the load table of E03 found by its ruling lines with the changed cell in its row; the moved label of E02 not asked about). The whole pipeline (real profiles, real engine, real series) was **not** run on the corpus for this lane: the series lane's lab fixtures are a 375-line conftest of that directory and a 30 s profiling pass; the answer keys judge the candidates of two sheets, not a description.
* The estimate prices the main call of each sheet once (the original's `calls_primary`); the follow-up calls (context, coverage, retry) are not priced in advance, and the x1.2 rule of the wrapper is what pauses a job that spends more.
* The tier of a value is a substring check of the value's normalised text against the normalised text of its side (the original's rule): a one-digit value is found in almost any text. The summary and place checks of this lane are the same kind of check.
* The lock order (items first, then the job row) and the race of two workers are the core's and are not exercised here (one connection per test).
* Commit trailers carry `Claude Sonnet 5.5` (the attribution the harness gave).

## 10. Notes for the next lanes

* **`CMP-VC-REPORT-01`**: read the stored descriptions through `ComparisonAiSheetService.descriptions_of_transition(transition_id=)` (each pair of the transition in matrix order with its derived state, its newest description document, its declared items and `recorded`) and the Markdown of one sheet through `read_md`. The «Реестр» categories map from the state: `engine_same` «совпадает по движку», `no_construction_changes` / `done` / `needs_clarification` «описано ИИ», `partial` «неоднозначно», `not_processed` «не обработано». A description is **AI output, not an engineer's decision**; keep the label.
* **`CMP-VC-QUEUE-01`**: `ComparisonAiSheetService.start_series(series_id=, consent=, restart=, command=)` is the call for a series; `AiJobCommand` needs the actor's roles. The installation's AI queue is the core's `waiting()`. The unlinked `drain` item of a job is a `comparison_work` row of kind `comparison_sheet_changes` that `comparison_ai_job_id` does not name; it is not a queue entry of the AI queue. The work queue claims by creation order, so the items of the older job go first: one series at a time follows from it.
* **`CMP-VC-UI-02`**: the eleven states and their words are `STATE_LABELS` (contract enum `ComparisonAiSheetState`); `stale` is a description of another prompt version, still served; the three tiers are `from_text` (no mark), `from_image` («с изображения»), `unverified` («не подтверждено»); a change with `certainty: unclear` shows «Неясно» with its `limitation`; `recorded: true` is the label «Записанный (тестовый) ответ»; `model` is `recorded`, `program` (no call) or the pinned model; `declared[].reference` is the permit state code; the evidence of an item is `side` and `box` on the canvas of page A. The estimate op returns the **left** estimate while the latest job is paused for `overrun` / `route_changed` (the consent of the resume), the **failed** estimate with `only_failed`, else the start's; a start with `restart` carries the digest of that same estimate. A single sheet's description is `changes` of `kind` `added` / `removed` (the first is the summary).

## 11. Proof that the forbidden hotspots were not touched

`git diff --name-only 0f6a008d..HEAD` lists only: `src/auditmanager/comparison/ai_sheets/**` (new), `src/auditmanager/comparison/public.py`, `src/auditmanager/bootstrap/adapters.py` (the body of `ComparisonAiSheetAdapter`), `src/auditmanager/bootstrap/composition.py` (its one constructor expression), `scripts/recovery/grant_classification.py`, `tests/unit/comparison/ai_sheets/**`, `tests/integration/comparison/ai_sheets/**`, the three composition registers, `tests/unit/comparison/engine/test_handler_unit.py`, `docs/program/CMP-VC-AISHEET-01.md` and `docs/program/tasks/CMP-VC-AISHEET-01.md`. Nothing under `contracts/`, `db/migrations/`, `src/auditmanager/api/` (`routers/ports.py` needed no row), `comparison/{ai_jobs,work,spend,series,engine,profile}/`, `jobs/`, `executors/`, `analysis/`, `workers/`, `infra/`, `web/`, `pyproject.toml`, `uv.lock`, `tests/support/`; the other four adapters of the wave and their register lines are as they were; the one `conftest.py` is this lane's own, in `tests/integration/comparison/ai_sheets/` (`AGENTS.md` section 8 case 3 covers it in the final gate).

## 12. Instructions for the integrator

1. Merge after `CMP-VC-AIPAIR-01` (wave brief section 3). Hunks in shared files: `comparison/public.py` (an import block after the AI-job imports, one line in `HANDLER_FACTORIES`, eleven names at the end of `__all__`), `bootstrap/adapters.py` (the body of one class), `bootstrap/composition.py` (one expression), `scripts/recovery/grant_classification.py` (two names out of `SEALED_NOT_YET_WRITTEN`), the three composition registers (`MODULE_GATED_GETS` and `MODULE_GATED_ADDRESSED` are new sets: the other lanes that gate their reads by the module flag need the same two sets or an equivalent, and the integrator may merge them), `test_handler_unit.py` (one kind).
2. Tell the lanes: a wired C2 read answers `503 comparison_modules` while the versions module is off, so the two sweeps cannot see its `404`; they need the module-on client (see `test_the_wired_sheet_reads_are_404_for_an_absent_parent_once_the_module_is_on`).
3. FIX items 1 and 2 of section 9 are the ones to schedule: until the composition root gives the handler a route source, a live job fails with a named reason.
4. The stack of this lane is `auditmanager-cmp-vc-aisheet-01`; it is brought down and its two volumes removed by exact name (section 8).
