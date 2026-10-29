# CMP-SERIES-01 — the series of adjacent transitions: sheet pairs and their results, the post-phases, the verdict codes, pause / resume / cancel / finish / restart, and the compare-after-preparation flag

Written 2026-10-28 by the Sonnet lane `CMP-SERIES-01` (size M, branch `agent/cmp-series-01`, base `9f5f4912` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-SERIES-01.md`](tasks/CMP-SERIES-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (3, 4, 5, 7 and its addendum, 10, 13, 14, 16, 18, 20, 21, 23); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) sections 1.1, 3.2 and 4 wave C1; the seal it serves is [`CMP-SEAL-C1.md`](CMP-SEAL-C1.md) (section 3 shape decisions 3, 4, 7, 8 and section 9, its row); the lanes it stands on are [`CMP-MATRIX-01`](CMP-MATRIX-01.md), [`CMP-ENGINE-01`](CMP-ENGINE-01.md), [`CMP-WORK-01`](CMP-WORK-01.md), [`CMP-INGEST-01`](CMP-INGEST-01.md) and [`CMP-INGEST-02`](CMP-INGEST-02.md).

## 1. Result

The nine series operations of the seal (`startComparisonSeries`, `listComparisonSeries`, `getComparisonSeries`, `pauseComparisonSeries`, `resumeComparisonSeries`, `cancelComparisonSeries`, `finishComparisonSeries`, `listComparisonSheetPairs`, `getComparisonSheetPair`) answer instead of `503`, served by `ComparisonSeriesAdapter` over `ComparisonSeriesService`. Their stub rows are gone from the composition registers, and `comparison_series`, `comparison_transition` and `comparison_sheet_pair` left `SEALED_NOT_YET_WRITTEN`.

* **A series** is comparison work over the *adjacent* transitions of the ordered versions of one document set. It starts only when the matrix is `ready`, binds the matrix revision `{matrix_id, edit_no}`, the version order revision and the digest of those inputs, allows at most one live series per document set, and writes, in one transaction, every transition, every sheet pair of the matrix and its work: one `series_pair` item for each pair that needs the engine and one `series_drive` item. A pair of versions that are not neighbours is never written; a sheet only in one version (`added`, `removed`) or one the matrix could not place (`unmatched`) is reported at once and never compared.
* **Each pair's result** is the engine's: the handler of `series_pair` calls `compare_sheet_pair` under the item's lease fence and writes the pair `done` with its status and its content-keyed result. The result row is never touched by the series.
* **The post-phases** run when none of a transition's pairs is `queued` or `computing`: the parts coverage of the sheets that were split across versions and the permit reconciliation (`declared_and_found`, `declared_no_diff`, `diff_not_declared`, `needs_review`), ported from the original's `_parts_phase` / `parts.py` and `_permit_phase` / `permit.py`; then the counts and the verdict **codes** (`incomplete`, `content_same`, `zones_only`, `different`, `composition_changed`, `needs_review`, `calculation_failed`), with `ai_dependent` counting the pairs that rest on an accepted AI link.
* **Steering**: pause / resume / cancel act on the series and on its work items (`comparison_work.comparison_series_id`); «Досчитать» (`finish`) queues the transitions that have no complete result and the pairs that failed or were left unfinished, reusing what is done; «Заново» is a start with `restart: true` that names the series it replaced. A series that no longer matches its inputs (a reorder, a matrix edit, a version published after it, other page profiles) says so with `stale_reasons`, derived on every read from the stored input digest.
* **Durable progress**: every state is a row. The one thing that can leave a pair unfinished with no handler running (the queue gave up on its item) is repaired by the series' own polling item, which marks that pair `failed` with the item's reason: visible, and a «Досчитать» queues it again.
* **`compare_after_preparation`** is stored by the create path, read back by the upload view, no longer refused, and `BatchLifecycle.advance` queues, once per set and through `comparison.public` names only, one `series_after_preparation` item that prepares the set's matrix and then starts the series on behalf of the person who declared the batch.

## 2. Base facts, printed before any edit

`contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes`, `VERSION` `0.9.0`, head `0039_comparison_core`, base `9f5f49128723c231813430ef3d941c1723643028` (`P-01` of the task file). They equal the premise of the lane's brief, so the lane went on. The lane changed no contract, no migration, no dependency and no lock file. **The original's clone `/root/projects/PDF-proverka` does not exist on this host**: the lane read `backend/app/services/version_comparison/{series,jobs,parts,permit}.py` at the pinned commit `23f379fd` from the public repository's raw files into its session scratchpad, outside git, as data (`P-04`), and cites file and line of those copies. Nothing of it is copied into the repository.

## 3. What was built

`src/auditmanager/comparison/series/` (new, 13 files, about 2 900 lines):

| module | what it holds |
| --- | --- |
| `model.py` | the three work kinds, the command types, the states, the verdict codes, the planned pair / transition / series |
| `planning.py` | `plan_series`: the transitions and pairs from `AdjacentSheetPairs`; `assert_adjacent` (only neighbours); `link_reasons` (the forcing reasons from the stored confidence and flags); the pairs of a sheet split across versions |
| `verdict.py` | `summarize` (the eleven counts of `ComparisonTransitionSummary`) and `verdict_codes` |
| `parts.py` | `group_coverage`: the parts coverage of a split sheet from the engine's `part` and the matrix's text coverage |
| `permit.py` | the permit table read from a page profile's words and vertical lines, the sheet references, `reconcile`, `pair_permits` |
| `inputs.py` | `input_digest` and `stale_reasons` (`order_changed`, `matrix_changed`, `profiles_changed`) |
| `repository.py` | the statements of the three tables, in one lock order (work rows, series, transitions, pairs) |
| `service.py` | `ComparisonSeriesService`: the nine operations, the start's single transaction, the steering commands, the follow-up of a prepared set |
| `handlers.py` | `series_pair`, `series_drive`, `series_after_preparation` |
| `advance.py` | `SeriesAdvancer.advance`: reconcile, finalise a transition (parts, permit, counts, verdict), conclude the series; the fence is the first statement of every transaction that writes |
| `views.py`, `followup.py`, `__init__.py` | the contract-shaped dictionaries (raw evidence copied, never rebuilt); the call `BatchLifecycle` makes; the exports |

Outside the package, each hunk named by the brief and minimal: `comparison/work/{model,repository}.py` (the series id: the column on enqueue, the claim, `pause_for_series`, `resume_for_series`, `cancel_for_series`, `counts(series_id=)`, `WorkRecord`), `comparison/engine/enqueue.py` (one keyword), `comparison/public.py` (imports, three handler factories in `HANDLER_FACTORIES`, twelve names), `ingest/comparison_pdf/{repository,service,views}.py` and `ingest/comparison_batch/{repository,service,lifecycle}.py` (the flag and the `advance` hook), `bootstrap/adapters.py` (the body of `ComparisonSeriesAdapter`; in `ComparisonUploadAdapter` the refusal lines, the flag passed on, and the one line of `_comparison_upload` that reads it back), `bootstrap/composition.py` (**one line**: `comparison_series=ComparisonSeriesAdapter(sessions, blob_store=store),`), the three composition registers, `scripts/recovery/grant_classification.py` (three names out of `SEALED_NOT_YET_WRITTEN`), and the pin of the handler tuple in `tests/unit/comparison/engine/test_handler_unit.py` (by the three kinds). `api/routers/ports.py` needed no row.

## 4. The original's rules, ported, with their lines

`O` = `backend/app/services/version_comparison/` at `23f379fd`. Lines are those of the files fetched for this lane.

| rule | original | here |
| --- | --- | --- |
| a series is the adjacent pairs of the order | `O/series.py:94-95` (`zip(order, order[1:])`) | `planning.plan_series`, `assert_adjacent`; shown by M09 |
| at least two versions; the matrix must be ready; one live series | `O/series.py:78-79`, `:80-81`, `:82-84` (`ACTIVE` `:29`) | `comparison_versions_few` (validation), `comparison_matrix_stale`, `comparison_series_active` and the partial unique index of `0039` |
| a matched pair is compared; `removed` / `added` when the other cell is absent, `unmatched` when it is a hole; those three are reported at once | `O/jobs.py:461-468`, `:474-483` | `planning` (immediate statuses, `state done` on insert) |
| the forcing link reasons | `O/jobs.py:463-471` (`MATCH_LOW_CONFIDENCE`, `TABLE_GROUP`, `AI_MATCH`, `DUPLICATE_SHEET`) | `planning.link_reasons`; `CHAIN_ONLY` (`O/jobs.py:437-459`) belongs to a non-adjacent pair and never arises |
| a sheet split across versions is compared with each of its parts, the older sheet is page A of every part pair, its own «removed» row disappears | `O/jobs.py:532-562` | `planning._plan_transition` |
| the counts and the verdict of a transition | `O/series.py:38-64` | `verdict.summarize` / `verdict_codes` (codes, not sentences) |
| `different` of style only | `O/series.py:48-49` | the `style_only` count, in SQL over the result's differences |
| pause stops after the sheets in hand; cancel; resume of an interrupted, cancelled, failed or paused series | `O/series.py:232-248`, `:261-281` (`RESUMABLE` `:30`) | `pause_series`, `cancel_series`, `resume_series`, `finish_series` |
| the parts coverage | `O/jobs.py:875-926` (and `O/parts.py:27-75` for the pairing, the matrix lane's) | `parts.group_coverage`, `advance._parts_phase` |
| the permit table, the sheet references, the reconciliation | `O/permit.py:37-60`, `:63-82`, `:85-127`, `:147-158`, `:167-219`; `O/jobs.py:930-968` | `permit.py`, `advance._read_permit` |
| a restart after a crash marks a series `interrupted` | `O/series.py:200-229` | not a state here: leases and the queue's reclaim (ADR-0025 decision 4) and the series' polling item |

**Where this port differs from the original, and why.**

1. *The work is items in the durable queue, not a thread per series.* One item is one sheet pair (decision 6); the pairs of the earlier transitions have the stronger priority, so the transitions finish roughly in order, but pairs of two transitions may be in flight together on more than one slot.
2. *The verdict is stricter.* `content_same` is never said while a pair has not finished or has failed (`O/series.py:53-54` withheld it for a failed item only).
3. *A sheet split across versions is a review of the series* (reason `SPLIT_SHEET`), whatever the engine's status of the part: the engine's report names it (section 5 item 1 of `CMP-ENGINE-01`) and the answer key says it. The original keeps the engine's status and records `part_coverage` beside it. The engine's row is untouched; the pair's status is the series'.
4. *The parts coverage* uses the engine's `part` member (`area_a_pt`, `coverage_a`, `reliable`, confirmed by the integrator) and the matrix's text coverage instead of the original's 36 dpi mask: the sum of the ink shares when every part has a reliable area and the areas do not overlap, else the text coverage marked unreliable. For a typical sheet repeated per floor (`role whole`) the figure is 100 and says only that each copy is compared whole.
5. *The permit* reads the page profile (words and vertical lines), not the PDF with PyMuPDF (`OD-01`). It searches the whole page (the original: the top 35 %, which would miss the table of the synthetic corpus at 37 %) and the first ten text pages of a version (the profile has no page kind). The permit's own number is not read. The sheet that carries the table is not reported as «найдено, но не заявлено». A row that numbers a sheet in the main set where only the specification set has that number, once, means that sheet. A scan has no stamp text, so the pair's older sheet gives its number.
6. *The verdict is a list of codes*; the Russian sentences are the client's.

## 5. Decisions the lane took (the FIX slot may revise any; none edits the contract)

1. **Three work kinds, one item per pair.** `series_pair` (payload `{"sheet_pair_id"}`, dedupe key `series_pair:<pair id>`), `series_drive` (one polling item per series) and `series_after_preparation`. The pair uses `compare_sheet_pair` directly and not the engine's `pair_result` kind (its dedupe key `pair_result:<a>:<b>` ignores reasons and part, and the pair row has to be written by the series under its own fence); `enqueue_pair_result` takes `comparison_series_id` as one keyword all the same.
2. **The input digest.** `comparison_series.input_sha256` is the SHA-256 of the canonical JSON of the chain of versions, the matrix id and edit count, the bound build's profile signature and the engine's `ALGO_VERSION`. A read recomputes it from the present inputs and, when it differs, names why. A new `order` revision with the same list is not `order_changed`.
3. **«Заново»** is `restart: true`; it names the latest series of the document set (any state: a live one is refused first). Nothing is deleted; the content-keyed result cache makes the repeat cheap.
4. **«Досчитать»** needs a series that is `completed`, `failed` or `cancelled`, no item of it still winding down, and something left: a transition `queued`, `running`, `failed` or `cancelled`, or a `completed` one with a failed pair. It queues those transitions and their `failed` / `computing` pairs again (the database allows `computing` and `failed` to `queued`, never `done`) and a new drive.
5. **A failed pair does not fail its transition.** The transition is `completed` with `incomplete` and `calculation_failed` in its verdict; a transition fails only when a post-phase cannot run (the reason is `post_phase_<code>`), and then the series ends `failed` with `transition_failed`.
6. **The pair's `status` and `reasons`.** The pair's status is the engine's, except that a split sheet is `needs_review`; its `reasons` are the result's own followed by the series' (`SPLIT_SHEET`). `only_changes` hides `same` pairs only (a pair not yet computed is not known to be unchanged).
7. **The matrix not ready** is `409 conflict` `comparison_matrix_stale` (registered for the edit operations; the seal registers no reason for the start). A document set of one version is `422 validation_failed` with `constraint: comparison_versions_few` (not registered). Both are FIX items (section 9).
8. **Lock order**: work item rows (the fence, `pause_for_series`...), then the series row, then its transitions, then its pairs. A command updates the items before the series.
9. **Staleness does not block a command.** A stale series can be paused, resumed, cancelled and finished; the screens offer «Заново».
10. **The follow-up of a batch** is the upload creator's act (`createComparisonUpload` is an expert's); the series it starts names that person and uses the idempotency key `auto-<set id>`. The follow-up is an item of the batch, so the next set and the batch's completion wait for it and a cancel of the batch reaches it; if a series is live when it runs, it fails visibly with `comparison_series_active`.

## 6. The corpus against the answer keys

`test_corpus_against_the_answer_keys.py` runs the series on VS-1 with the **real** page children, the real matrix, the real runner and the real engine in its ceilinged child (24 pair items, 35 s), and judges it against `fixtures/comparison/vs1/answer_key.json`, which the fixtures lane authored next to the content.

| transition | series verdict | counts of the series (sheets / same / zones-only / different / review / added / removed) | the key's counts |
| --- | --- | --- | --- |
| V1 → V2 | `different` | 6 / 2 / 1 / 3 / 0 / 0 / 0 | same 2, zones 1, different 3 |
| V2 → V3 | `different`, `composition_changed` | 7 / 1 / 0 / 4 / 0 / 1 / 1 | same 1, different 4, added 1, removed 1 |
| V3 → V4 | `different`, `needs_review` | 6 / 2 / 0 / 3 / 1 / 0 / 0 | same 2, different 3, review 1 |
| V4 → V5 | `different`, `needs_review` | 7 / 2 / 0 / 2 / **3** / 0 / 0 | same 2, different 2, review **2** |

**Every one of the 26 pairs has the key's status.** The one count that differs is by construction: the key counts the split sheet E05 once, the series has one pair for each of its two parts, both `needs_review` with `SPLIT_SHEET`. The scan of V4 (E04) is the engine's `NO_TEXT_LAYER`; the duplicated sheet of V5 (E03) is `DUPLICATE_SHEET`; the added and removed sheets of V2 → V3 are reported at once.

**The permit of V4** (V3 → V4) matches the key's four classes: E05 `declared_and_found`, E07 `declared_no_diff` (key: `declared_not_found`), E04 `needs_review` (key: `declared_unverifiable_scan`), E03 `diff_not_declared` (key: `found_not_declared`); E01 carries the table and E02 is unchanged, so they have none. V5 has no new permit row, so its one changed, undeclared sheet (E07) is `diff_not_declared`: true to the original's rule, and the key says nothing for that transition.

**The parts coverage of the split** is the matrix's text coverage, 60.71 %, marked unreliable: the engine registered the second part (V5 page 6) onto the **left** half of the older sheet (`area_a_pt` `[78.89, 3.5, 1221.89, 1680.5]` where the first part is `[45.5, 3.5, 1188.5, 1680.5]`, and the key says the second part is the region `[1193.39, 2383.94]`), so the two areas overlap and the ink figure is refused. It is an item for the engine's lane (section 9 item 2).

## 7. Safety rules and their mutation proofs

Tool: a script outside the repository applies one replacement to the committed file, runs the named tests, restores the file with `git checkout`, and runs them again; the tree was clean after each. Every row was run on the final code of its guard.

| # | commitment | file mutated | guard | red | restored |
| --- | --- | --- | --- | --- | --- |
| M01 | one live series per document set (the check) | `service.py` | `test_start.py` | 1 failed | 1 passed |
| M02 | staleness on a reorder | `inputs.py` | `test_inputs.py`, `test_stale.py` | 5 failed, 11 passed | 16 passed |
| M03 | staleness on a matrix edit (the edit count ignored) | `inputs.py` | `test_inputs.py`, `test_stale.py` | 4 failed, 12 passed | 16 passed |
| M04 | the lease fence on the write of a finished pair | `handlers.py` | `test_fence.py` | 1 failed, 5 passed | 6 passed |
| M05 | the lease fence on marking a pair computing | `handlers.py` | `test_fence.py` | 1 failed | 1 passed |
| M06 | the lease fence on the reconcile | `advance.py` | `test_fence.py` | 3 failed, 3 passed | 6 passed |
| M07 | the lease fence on the finalisation of a transition | `advance.py` | `test_fence.py` | 2 failed, 4 passed | 6 passed |
| M08 | the lease fence on the conclusion of the series | `advance.py` | `test_fence.py` | 1 failed, 5 passed | 6 passed |
| M09 | non-adjacent pairs are refused by the plan | `planning.py` | `test_planning.py` | 1 failed, 15 passed | 16 passed |
| M10 | the verdict is incomplete while a pair is missing or failed | `verdict.py` | `test_verdict.py`, `test_run.py` | 4 failed, 11 passed | 15 passed |
| M11 | raw evidence is copied verbatim (one member dropped) | `views.py` | `test_views.py`, `test_post_phases.py` | 2 failed, 5 passed | 7 passed |
| M12 | every steering command is an expert's act | `service.py` | `test_steering.py` | 4 failed | 4 passed |
| M13 | the start is an expert's act | `service.py` | `test_start.py` | 1 failed | 1 passed |
| M14 | a keyed steering command replays its outcome | `service.py` | `test_steering.py` | 4 failed | 4 passed |
| M15 | a keyed start replays its outcome | `service.py` | `test_start.py` | 1 failed | 1 passed |
| M16 | a stale base order revision is a conflict | `service.py` | `test_start.py` | 1 failed | 1 passed |
| M17 | the series starts only on a ready matrix | `service.py` | `test_start.py` | 1 failed | 1 passed |
| M18 | a pair whose item ended is failed by the reconcile | `advance.py` | `test_run.py`, `test_fence.py` | 2 failed | 2 passed |
| M19 | a split sheet is a review of the series | `handlers.py` | `test_post_phases.py`, `test_corpus_against_the_answer_keys.py` | 2 failed | 2 passed |
| M20 | the upload flag is stored | `repository.py` | `test_upload_flag.py` | 1 failed | 1 passed |
| M21 | BatchLifecycle.advance queues the follow-up of a prepared set | `lifecycle.py` | `test_upload_flag.py` | 4 failed, 4 passed | 8 passed |
| M22 | a cancel reaches the items of the series | `service.py` | `test_steering.py`, `test_run.py` | 2 failed | 2 passed |
| M23 | a pause reaches the items of the series | `service.py` | `test_steering.py` | 1 failed | 1 passed |
| M24 | the permit reconciliation: a found declared change | `permit.py` | `test_permit.py`, `test_post_phases.py` | 4 failed, 14 passed | 18 passed |
| M25 | the parts coverage is written | `advance.py` | `test_post_phases.py` | 1 failed | 1 passed |
| M26 | the pair handler is registered through the shipped tuple | `public.py` | `test_handler_unit.py`, `test_run.py` | 2 failed | 2 passed |
| M27 | the stub register no longer lists a served operation | `test_an_absent_parent_is_not_an_empty_page.py` | `test_an_absent_parent_is_not_an_empty_page.py` | 1 failed, 11 passed | 12 passed |
| M28 | the written tables leave SEALED_NOT_YET_WRITTEN | `grant_classification.py` | `test_grant_classification.py` | 2 failed, 33 passed | 35 passed |
| M29 | an unmatched pair is never compared | `planning.py` | `test_planning.py` | 1 failed, 15 passed | 16 passed |
| M30 | the series id rides every item | `service.py` | `test_start.py` | 1 failed | 1 passed |
| M31 | the items are filed under the versions module (decision 23) | `service.py` | `test_run.py` | 2 failed | 2 passed |
| M32 | a done pair is not computed again (the handler's early end) | `handlers.py` | `test_run.py` | 1 failed | 1 passed |
| M33 | the transition of only placed-nowhere sheets passes through running | `advance.py` | `test_run.py` | 1 failed | 1 passed |
| M34 | a reason the contract cannot carry is mapped | `views.py` | `test_views.py`, `test_corpus_against_the_answer_keys.py` | 2 failed | 2 passed |

ADR-0025 decisions where they touch this lane: **4** (durable progress, one handler per kind): M18, M26, M32 and the tests of the reconcile; no state lives in memory (the handlers hold none). **7 and its addendum** (the publishing transaction is fenced; the project cannot vanish under an item, by `ON DELETE RESTRICT`): M04–M08. **10** (a batch's cancel reaches its items): `test_the_next_set_waits_for_the_follow_up_and_a_cancel_of_the_batch_reaches_it`. **13** (one truth for sheet pairs): the series reads the effective matrix and never `comparison_sheet_link`. **14** (matrix revisions): M02, M03, M17. **16** (expert acts): M12, M13. **20** (raw evidence is never rewritten): M10, M11, M19, M34. **21** (staleness compares stored digests): M02, M03. **23** (the module flag): M31. **5 and 18** (spend, images): not touched; the series has no model call and no image.

## 8. Commands and results

All from the lane worktree with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src`, the lane's `.env` loaded for the container suites; PostgreSQL on `57870`, MinIO on `61870`, head `0039` (`make up` and `make migrate` from the worktree). `df -h /` was read before every container start and every long run: 1.6 to 2.6 GiB free (the host, not the lane, moved it; the lane's PostgreSQL stayed near 100 MB and its bucket near 7 MB; the stop line is 1.5 GiB).

| what | command | result |
| --- | --- | --- |
| diff hygiene | `git diff --check 9f5f4912..HEAD` | clean (exit 0) |
| the lane's unit directory | `pytest -q tests/unit/comparison/series` | **67 passed** |
| the lane's integration directory | `pytest -q tests/integration/comparison/series` | **77 passed** (about 80 s; the answer-key test with the real engine is 35 s of it) |
| the comparison integration directories, one at a time with the live work items cleared between them (below) | `pytest -q tests/integration/comparison/<dir>` | work 62, engine 23, matrix 25, profile 18, profile_queue 20, series 75 (77 at the end), spend 85, tiles 14, the top-level files 184: **506 passed, 0 failed** |
| the ingest directories | `pytest -q tests/integration/ingest/comparison_pdf tests/integration/ingest/comparison_batch` | **298 passed** |
| the whole composition directory | `pytest -q tests/integration/composition -rf` | **1956 passed, 4 skipped, 0 failed** in 34 min 10 s (ten fewer than the matrix lane's 1 966; nine of them are the cases of the one test of `test_comparison_core_stub_operations.py` that is parametrised over the stub list, 11 stubs then and 2 now) |
| grant classification | `pytest -q tests/integration/recovery/test_grant_classification.py` | 35 passed (inside M28) |
| the whole unit battery | `pytest -q tests/unit -rf` | **4808 passed, 76 skipped**, 1 warning |
| the contract battery minus the three `D-220` files | `pytest -c pyproject.toml --rootdir=. -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py -rf` | **1310 passed**, 19283 subtests passed (it holds the boundary guard `test_alr05_boundaries`, the governance test of the task file and the surface-count guard) |

**What the new tests prove, and against what.** *The answer key* (section 6). *The start* (`test_start.py`, 11): what is written (4 transitions, 26 pairs, 24 + 1 items, the matrix revision, the digest), the one-live-series rule, the matrix and order refusals, the replay and the key reuse, the role, the unknown ids, the restart. *The run* (`test_run.py`, 9): the real runner and handlers with a scripted engine that writes real result rows; every pair, the finalised transitions, the concluded series, the adjacency of every call, a failed pair and its «Досчитать», a pair whose item the queue gave up on, a cancel, a transition with nothing to compute, the module flag. *Steering* (`test_steering.py`, 21), *staleness* (`test_stale.py`, 9), *the fence* (`test_fence.py`, 6), *the post-phases and the verbatim evidence* (`test_post_phases.py`, 5), *the series id on the queue* (`test_work_series_id.py`, 5), *HTTP* (`test_http.py`, 2), *the flag and the follow-up* (`test_upload_flag.py`, 8). Unit: planning (16), verdict (14), parts (6), inputs (7), permit (17, the table read from a real profile of VS-1), views (7).

**Two defects the tests found in the lane's own code, fixed in `9fd77f23`:** the database has no `queued -> completed` edge for a transition or a series, so a transition none of whose pairs needed the engine would have refused to finish; and the engine's reason `UNCHECKED_CHANNEL:<channel>` is refused by the contract's reason pattern, so the pair of a scan would have answered `500` (the real-engine test now validates every pair and the series through the generated models).

**The shared database.** `tests/integration/comparison` shares one database with its subdirectories, and two of them assume no other live work: `work/test_worker_hosting.py` refuses to start a worker while an item of a kind it does not register is live, and the engine's queue tests claim any queued item. This lane's tests therefore end every live item of their own projects at the end of each test (an autouse fixture); the matrix lane's tests leave `matrix_build` items live, which fails the hosting tests when the whole directory runs in one pytest process (first run: 12 failed, 6 errors, of which 7 failed after this lane's items were cleared). Run one subdirectory at a time, with the live items cleared between them, as the table above did. It is not a defect of this lane; it is an item for the integrator's gate (section 9 item 11).

**Mutation proofs**: the 34 rows of section 7, each red and then green, the tree clean after each.

## 9. Limits, risks, and items for the FIX slot

1. **A reason the contract's pattern refuses.** The engine writes `UNCHECKED_CHANNEL:<channel>`; `ComparisonSheetPair.reasons` is `^[A-Z][A-Z0-9_]{2,63}$`. The view maps it to `UNCHECKED_CHANNEL_<CHANNEL>` (the channel's own state and reason stay in `channels`; the stored row is untouched). FIX: either the engine writes the contract's form or the contract's pattern admits it.
2. **The engine's second part of a split sheet** is registered onto the wrong region of the older sheet in the synthetic corpus (section 6), so the ink coverage of the split is refused and the text coverage (60.71 %) stands. Item for the engine's lane.
3. **Reasons not registered.** `comparison_matrix_stale` is registered for the edit operations; the start uses it for a matrix that is not `ready` (absent, building, stale or failed). A document set of one version answers `validation_failed` with `constraint: comparison_versions_few`. FIX: register both, or give the start its own reason.
4. **Stale words in the sealed files** (the lane may not edit them): the module docstring of `api/routers/comparison_series.py` and the descriptions of the nine operations in the OpenAPI document still say «sealed as a stub until CMP-SERIES-01».
5. **The worker process.** `workers/__main__.py` still needs the one line of `CMP-WORK-01` section 7.1 (`comparison_work=runtime.comparison_work`); without it no worker runs a series item, a profile or a build. The three kinds ship with their first use, as the matrix's did: a start puts `series_pair` items on the queue, and an unhandled kind of an enabled module refuses the worker's start.
6. **The permit port is approximate.** It reads the first ten text pages of a version (the profile has no page kind) and finds the table by its header words and vertical lines, so a form drawn with rectangles instead of lines is not found; a declared reference that names no sheet of the version, and the references it cannot parse, are kept in the reconciliation but have no pair to attach to and no place in the contract (a transition-level record is a seal item); the permit's number is not read. Unmeasured on a real set.
7. **A pause is the granularity of one pair** (the item in flight finishes); there is no «pause after the current transition».
8. **«Досчитать» right after a cancel** answers `comparison_series_state` while an item of the cancelled series is still winding down (it ends at its next checkpoint, seconds); the client asks again.
9. **Throughput and size are unmeasured.** The start writes every pair and enqueues every item in one transaction (a series of 12 versions of 500 sheets is about 5 500 pairs); the drive polls every 15 s while a series runs and every 30 s while it is paused; `advance` runs after each pair and costs a series lock and a few counts. `CMP-MEASURE-01` should time them on the real set.
10. **Not run, by the brief and `R-135`:** `make gate`, the web battery (no web change), the live journey. The task touches `bootstrap/**` (AGENTS section 8 case 3 asks one full gate on the lane that changes the composition root), deferred to the gate before the beta.
11. **For the integrator's gate:** the shared-database rule of section 8; the three composition registers are edited in the merge order MATRIX, ENGINE, VIEWER, SERIES (the hunks are line-local: the four read rows leave `SEALED_STUB_GETS` and `SEALED_STUB_ADDRESSED`, nine names join `WIRED`; `EXPECTED_ADDRESSED` stays 53, since those operations are addressed whether stubbed or served).

## 10. Notes for the next lanes

* **`CMP-VC-OVERVIEW-01`** (step 5 «Сравнение соседних»): read the latest series of the document set (`ComparisonSeriesService.list_series`, newest first, or the three tables) — no series is «не запускалось»; `queued` / `running` is «идёт» with `transitions_done` of `transitions_total`; `paused` «пауза»; `completed` «готово» with, per transition, the verdict and `summary`; `failed` «ошибка» (`failure_reason`); `cancelled` «прервано»; `stale_reasons` non-empty is «по старому порядку» (and `order_changed` is the original's «Сохранённая сводка для прежнего порядка версий.»). The work counts of a series are `ComparisonWorkRepository.counts(series_id=...)`; the follow-up of a batch is an item of kind `series_after_preparation` attached to the upload. Step 3 «Сопоставление листов» stays the matrix's.
* **`CMP-VC-UI-01`** (the block «Сводка переходов»): a row per `transitions[]`: «Переход A → B» from `source_version_uid` / `target_version_uid` (the labels come from the versions), «Ход расчёта» `items_done` of `items_total` and `state`, «Листов» `summary.sheets`, «✓ ◐ ● ⚠» = `same`, `zones_only`, `different` (of which `style_only`), `needs_review`, «Состав +N / −M» = `added` / `removed`, `ai_dependent` the mark of pairs that rest on an accepted AI link, the verdict **codes** in the order given (the sentences are the client's), «Открыть» = `transition_id` for `listComparisonSheetPairs` (`status`, `only_changes` = «только изменения», cursor by `pair_no`). Buttons: «Отменить» `cancel`, «Продолжить» `resume` (paused) or «Досчитать» `finish` (a finished series with something left), «Заново» `start` with `restart: true` and the `base_order_revision_no` the screen saw. A pair shows `page_a` / `page_b` (the profile ids are what the viewer reads), `status`, `confidence`, `flags`, `reasons` (the engine's, then the series'), `permit`, `parts`, `ai_dependent`, `failure_reason`; `getComparisonSheetPair` adds the raw evidence. The Russian sentences are owed for `comparison_series_active`, `comparison_series_state`, `comparison_version_order_stale`, `comparison_matrix_stale` (also on the start), `SPLIT_SHEET`, the permit states, the verdict codes; `TRANSLATED_SCHEMAS` needs `ComparisonSeriesState`, `ComparisonTransitionState`, `ComparisonVerdictCode`, `ComparisonSeriesStaleReason`, `ComparisonSheetStatus`, `ComparisonSheetPairState`, `ComparisonPermitState`, `ComparisonPartRole`. The upload dialog sends `compare_after_preparation`.
* **`CMP-MEASURE-01`**: `test_corpus_against_the_answer_keys.py` is the series on a known set; on the real set time the start (rows and items written), `advance` after a pair, the drive's poll, and the permit read (at most ten page archives for each of two versions per transition).
* **Wave C2**: an accepted AI link flows into the pair as `ai_dependent` and the transition's `summary.ai_dependent`; the series needs no change.

## 11. Contracts, hotspots, resources

* **New or changed contracts: none.** `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock` and `docs/program/P02_LOCK.json` are untouched (`git diff --name-only 9f5f4912..HEAD -- contracts db pyproject.toml uv.lock docs/program/P02_LOCK.json web infra Makefile` prints nothing); nor are `src/auditmanager/{jobs,workers,storage,documents}`, `comparison/{profile,matrix,tiles}` and the engine apart from `enqueue.py`.
* **Instructions for the integrator.** Merge after MATRIX, ENGINE and VIEWER (brief section 3): `adapters.py` has the series adapter in place of its stub class and three lines in `ComparisonUploadAdapter`; `HANDLER_FACTORIES` gains three lines under `matrix_build_handler`. Apply `CMP-WORK-01` section 7.1 before a worker runs anything. The batch lifecycle now needs `comparison.public.enqueue_series_after_preparation`.
* **Resources.** Containers `auditmanager-cmp-series-01-{postgres,s3,s3-init}` on ports 57870 / 61870 / 61871, brought up with `make up FOUNDATION_PYTHON=/usr/bin/python3.12` and migrated with `make migrate` from the lane worktree; at the end `make down` ran and the volumes `auditmanager-cmp-series-01-postgres-data` and `auditmanager-cmp-series-01-s3-data` were removed by those exact names; the lane's git-ignored `.env` was deleted. No process was killed by a pattern; the one process the lane stopped (its own first mutation script, which parsed its results wrongly) was stopped by its PID, and the file it had mutated at that moment was restored with `git checkout`.
