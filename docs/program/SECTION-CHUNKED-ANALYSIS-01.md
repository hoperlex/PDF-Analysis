# SECTION-CHUNKED-ANALYSIS-01 — whole-page windows for a section run above the one-call budget

Lane CH of production wave PW4 (`docs/program/dispatch/PRODUCTION-WAVE-PW4.md` section 3), base `6075df88`,
branch `agent/section-chunked-analysis-01`. Task file: `docs/program/tasks/SECTION-CHUNKED-ANALYSIS-01.md`
(premise output is printed there). The **Design** section was committed first (`d4561a00`, before any code);
sections 2 to 10 were written when the code and tests were done. Where the built thing differs from the note
it is said in section 3 (it differs in two details only: the metric names for a windowed request digest and the
tests added beyond the plan).

**Result in one paragraph.** A version whose recorded character count is above the one-call budget is analysed
in whole-page windows (up to `MAX_ANALYSIS_WINDOWS` = 12): one model call per window under the run's single
cost meter, one effect-journal entry and one `model_call` row per window, a saved reply per window, and a
restart that recovers finished windows instead of paying for them again. A kill between windows resumes; a kill
inside a window fails the run exactly as a single call always did. Below the old budget (and for a version with
no recorded count) the code path is the untouched `run_text_analysis`. No contract, no migration, no AR v3 file,
no profile package. Tests: 126 new, 16 modified (before and after in section 6), 45 mutations all red.

## 1. Design

### 1.1 What is true today (read from the tree, see the task file for the output)

* `startRun` / `reauditRun` refuse a version whose recorded `text_character_count` is above
  `input_budget_characters(model, ceiling)` (152 361 for `claude-opus-5` at USD 1.00) with
  `analysis_input_budget_exceeded` (`runs/commands.py::_refuse_over_budget`). The same helper guards the AR v3
  group (`runs/v3_group.py:251`) and **stays as it is**.
* The `text_analysis` stage makes **one** call over the whole text layer (`analysis/text/stage.py::run_text_analysis`),
  under one `CostMeter` built once per run (`runs/executor.py`), with a durable effect journal
  (`_DurableCallJournal`: prepare, response_received, complete) and a retry ladder that re-invokes the stage on a
  proven-not-sent transport failure.
* The primitives for windows exist and have **no production consumer**: `chunk_preflight.partition_text_layer`
  (whole pages, document-global offsets), `window_anchor.validate_window_plan`, `window_cohort.bind_window_claim_cohort`
  (one reply per window, quotes resolved against the full layer, a claim on a page outside its window refuses the
  cohort). `saved_window_custody.py`, `source_bytes.py` and `runs/text_window_input.py` (a run-scoped re-read of the
  saved text bytes under the Attempt locks) are also unconsumed and **stay unconsumed**: the stage already holds the
  text layer read and verified by `read_artifact`, and a second locked read buys nothing the window key does not
  already bind (section 1.4).
* The budget is a **cost** figure, not a context figure (`budget.py`, `D-162`). A window of the full per-call budget
  costs about the whole ceiling at the pinned model's rates, so windows do **not** make a larger volume cheaper:
  they bound the size of one call (the proxy's 200 s per call, the 900 s attempt watchdog), make a killed run
  resumable, and let the owner raise the ceiling (or pick a cheaper or unmetered connection) and then be served. The
  ceiling stays what it is, **one per run**, and is enforced on measured spend (section 1.5).

### 1.2 Where windows are planned, and when a run is windowed

* **Engagement predicate = the old refusal predicate.** The executor passes the version's recorded
  `text_character_count` and the per-call budget (`input_budget_characters(config.model_id, config.run_cost_ceiling_usd)`)
  to the stage. A version with no recorded count, or a count **not above** the per-call budget, is analysed exactly
  as today: `run_text_analysis`, untouched (zero diff in `stage.py`), one call, the same request bytes, the same
  recordings. Only a count above the per-call budget engages `run_text_analysis_windows` (new, `analysis/text/windowed.py`).
* **Plan.** `partition_text_layer(layer, max_chunk_characters=per-call budget)` on the layer the stage already loaded:
  greedy whole-page windows, each retaining document-global offsets. A plan of one window delegates to
  `run_text_analysis` (identical). A plan of more than `MAX_ANALYSIS_WINDOWS` windows, or a page larger than a
  window, fails the stage **before any call** with `analysis_input_invalid` (`reason` `window_plan_over_limit` /
  `window_page_exceeds_limit`; the message carries both figures). `analysis_input_budget_exceeded` cannot be stored on
  a run (the stored vocabulary is the catalogue without it, contract note on the code), so the stage uses the
  stored code and the start-time check keeps the pre-run code.
* **The limit N (`MAX_ANALYSIS_WINDOWS` = 12) is a named constant with its arithmetic**: the upload envelope is 500
  pages; the one real set is 3 123 characters a page, so 500 pages is about 1.56 M characters, 10.2 windows of 152 361;
  12 covers it with slack, and 12 windows is 3 attempts of 4 windows of the proxy's 200 s ceiling inside one 900 s
  watchdog (`R-146y` keeps the watchdog at 900 s). `MAX_ANALYSIS_WINDOWS = 1` restores today's behaviour exactly
  (rollback, section 1.9).
* **Start-time check.** `start_audit_run` and `reaudit_run` refuse a count above `per-call budget x N` with
  `analysis_input_budget_exceeded`, details exactly `character_count` and `budget_characters`, the latter now the
  N-window capacity (same keys, same integers, so the contract's schema is untouched; its prose still describes the
  one-call budget and is the integrator's to fold into the next contract reseal). `_refuse_over_budget` stays for the AR v3 path.

### 1.3 One call per window, one ceiling, one journal

* Each window is one `ModelRequest` built by `build_request(..., user_content=...)`: the same body as today except the
  user message, which is a window preamble (Russian, model-facing: "fragment k of n, pages a-b of m, page numbers are
  the document's, you have no other pages, a disagreement with a page you cannot see is not a finding") plus the
  existing page banners with the **true page numbers**. The system prompt (the section's own, unchanged) is not edited:
  `profiles/**` is forbidden, and the preamble lives in `windowed.py`, not in the bundle, so no bundle hash moves.
* **Same `CostMeter` for every window and every attempt.** The meter is the run's (`execute_run` builds it from
  the persisted `model_call` sum, so a resumed attempt starts from the earlier windows' spend). Before each fresh call
  `check_before_call()` (spent >= ceiling stops at the boundary, no call), after it `charge()` (the call that crosses
  the ceiling is recorded and the run stops). Both stops fail the stage `cost_budget_exceeded`, name the window and the
  windows already done in the message, publish **nothing**.
* **Each window is its own effect.** The existing `_DurableCallJournal` is used unchanged: one `provider_call_effect`
  (prepared, response_received, completed) and one `model_call` row per window. `cost_micros`, the run's call count
  and `finding_observation.model_call_id` are already per row.

### 1.4 The journal key of a window, and what a restart reads

* **Key** = sha256 of the canonical JSON of: format version; the sha256 of the layer's `document_text`; the layer's
  `version_uid` and `normalization_id`; the window's `index`, `first_page`, `last_page`, `char_start`, `char_end`;
  the window count; the profile's `content_sha256` (it binds the prompt bundle); the model id; the window request's
  `request_sha256`. A changed text, a changed range, a changed profile or prompt, a changed model all change it, so a
  changed input never replays an old reply.
* **Custody of the reply.** After `response_received` and **before** `complete`, a window reply is written as a
  private blob (`runs/window_reply_custody.py`, role `analysis_text_window_reply`, the shape of the AR v3 reply blob,
  which is read and not touched): the parsed adapter answer, the call binding (run, model call, request and response
  sha256, key, window). `complete()` writes the `model_call` row with the key, the window range and the blob
  reference in its `parameters` (a free-form jsonb; no migration, no contract). A single-window run writes none of it.
* **Recovery.** At the start of a windowed stage, for each window the custody is asked for its key:
  `JobRepository.completed_window_calls` reads `model_call` joined to its `provider_call_effect` (state `completed`,
  `final_model_call_id` = the call, request/response sha256 equal, same Job, same provider mode) and returns the rows
  that carry a key; the custody verifies the blob (sha256, size, envelope, binding to that call) and returns the
  saved reply. A recovered window makes **no call, charges nothing** (its spend is already in the meter's opening
  balance or, inside one process, already charged) and takes the same parse and grounding path as a fresh one.
* **How a kill resumes.** Today `reclaim_expired` treats **any** live effect of the lost Attempt that is not
  `not_processed` as ambiguous and fails the run (`provider_outcome_unknown`). A `completed` effect whose `model_call`
  carries a window reply blob is settled with durable evidence, so it is excluded from that test (one SQL
  predicate, `jobs/repository.py`). A window still `prepared` or `response_received` at the kill stays ambiguous and
  fails the run exactly as a single call does: the provider may have been sent, or paid for, and its reply is lost.
  So a kill **between** windows resumes (a new Attempt re-runs the deterministic stages, plans the same windows,
  recovers the finished ones, calls the rest); a kill **inside** a window does not. Nothing yields at a window
  boundary when the 900 s watchdog fires: a window in flight then is the second case. That is a limit, not hidden.
* **Within one process** the retry ladder (proven-not-sent transport failure) re-invokes the stage; the second
  invocation recovers the windows the first finished through the same custody, so the ladder is unchanged.

### 1.5 How the cohort binds, merges, and what a bad window does

* A window's reply is parsed by the existing `parse_response`. **A reply that is not a JSON document with an
  `observations` list, and was not cut short, is an invalid window**: the stage fails `analysis_failed` naming the
  window (`window k of n, pages a-b`) and publishes nothing. (Today's single call reads the same reply as "no
  findings"; a window must not, or a run could look complete with a window unread.) A cut-short reply keeps the
  single-call meaning per window: complete elements are salvaged; no usable observation fails the stage naming the
  window; otherwise the run is `partial` with `pages_analysed` = every page of the complete windows plus the pages up
  to the truncated window's frontier.
* Quotes are bound by `bind_window_claim_cohort` over the **complete** tuple of replies (fresh or recovered), against
  the full layer, so anchors keep document-global offsets; `block_id` is attached afterwards exactly as `_ground`
  does. A claim on a page outside its own window is dropped before the cohort (an `UnresolvedAnchor`, counted in
  `evidence_outside_window`), the way a quote on the wrong page is dropped today, never published and never fatal.
* Observations are merged in window order, then reply order; `observation_ordinal` is positional as before; each
  keeps its own window's `model_call_id`. `build_text_observations` and the evidence gate run once over the merged set,
  unchanged. A failed or stopped run publishes **no** observation of the windows that did finish.

### 1.6 What the run says about independence

`stage_result.metrics` (scalars only, the contract schema) carries `windows_total`, `windows_analysed`,
`windows_recovered`, `windows_independent` (`true`), `window_characters_ceiling`, `windows_limit` and a plain Russian
`windows_note`: "Страницы разбиты на окна; каждое окно проверено отдельно, поэтому расхождение между страницами
разных окон не выявляется." The model is told the same in every window's preamble. The frozen `RunStatus` exposes no
stage metrics, so surfacing the sentence to a reviewer is a contract and screen change outside this lane (reported).

### 1.7 What the design does not touch

No contract (`contracts/**`, the error catalogue, the OpenAPI), no migration (the new facts live in free-form
`model_call.parameters` and a private blob with an open role), no AR v3 file (`v3_*`, `ar_v3`, `_refuse_over_budget`
and the v3 group), no profile package, no `bootstrap/**` file: the budget reaches `start_audit_run` through the
existing keyword from `settings.py` (environment source) and `providers.py::_freeze` (database source) as the
per-call figure, so `providers.py` needs no edit. `analysis/public.py` (the context façade, ALR-05) gets additive
exports because `runs` may import `analysis` only through it.

### 1.8 Proof plan

Container-free: the plan (N, N+1, page too large, offsets), the request (single window byte-identical to
`build_request`, true page numbers), the key (each input moves it), the stage over scripted adapters (three windows all
bind; recovered windows are not called; the shared ceiling stops at a boundary; an invalid window is named; a cut-short
window yields `partial`). On the lane stack: `execute_run` over a three-window version in recorded and in live mode, a
kill after window 1 and a restart that makes calls 2 and 3 only (counted at the adapter and in `model_call`), the
in-flight kill that still fails `provider_outcome_unknown`, the start-time limit, and a under-budget version that makes
one call and publishes the same artifact as before. Every guard is shown red under a quoted mutation.

### 1.9 Rollback

`MAX_ANALYSIS_WINDOWS = 1` in `analysis/text/budget.py`: the start-time limit equals the per-call budget and no
count above it is admitted, so no run is windowed. No data to undo: windowed runs leave ordinary `model_call` rows
and unbound reply blobs.

## 2. Files

| File | Change |
| --- | --- |
| `src/auditmanager/analysis/text/windows.py` (new, 327 lines) | `text_window_policy` (when a run is windowed), `plan_text_windows`, `render_window` / `build_window_request`, `window_key`, `WindowIdentity`, `RecoveredWindow`, the `WindowCustody` protocol, the `text_window_*` parameter names |
| `src/auditmanager/analysis/text/windowed.py` (new, 577 lines) | `run_text_analysis_windows`: the loop, the shared meter, the journal, the cohort binding, the merge, the failure naming |
| `src/auditmanager/analysis/text/budget.py` | `MAX_ANALYSIS_WINDOWS` (12, with its arithmetic) and `windowed_budget_characters` |
| `src/auditmanager/analysis/text/adapter.py` | `build_request(..., user_content=None)`: `None` is every existing caller and the body is byte for byte what it was |
| `src/auditmanager/analysis/text/__init__.py`, `src/auditmanager/analysis/public.py` | additive exports (the context façade, ALR-05; the one file outside the brief's list, see the task file) |
| `src/auditmanager/jobs/repository.py`, `jobs/public.py` | `JobRepository.completed_window_calls` and `CompletedWindowCall`; the reclaim predicate narrowed (section 1.4) |
| `src/auditmanager/runs/window_reply_custody.py` (new, 259 lines) | `WindowReplyCustody`: write the reply blob after the answer is journaled and before the call is completed; read it back only if it agrees with the call |
| `src/auditmanager/runs/executor.py` | the stage chooses the windowed path when the version's count is above the per-call budget; builds the custody; the retry ladder and the one meter are unchanged |
| `src/auditmanager/runs/commands.py` | `_refuse_over_window_budget` for `start_audit_run` and `reaudit_run`; `_refuse_over_budget` (AR v3) untouched |
| `tests/unit/analysis/test_text_windows.py` (31) | policy, plan, request, key, parameter-name pin |
| `tests/integration/analysis_text/test_text_windowed_stage.py` (26) | the stage over scripted adapters, an in-memory journal and custody |
| `tests/integration/runs/test_text_windows_executor.py` (7) | `execute_run` on PostgreSQL and MinIO: three windows, ceiling, kill between and inside, unreadable reply, under-budget |
| `tests/integration/runs/test_window_reply_custody.py` (25) | every way a saved reply can disagree with its call |
| `tests/integration/runs/test_completed_window_calls.py` (37) | the finished-window reader, every arm of the call/effect agreement, the reclaim rule |
| `tests/integration/runs/test_input_budget.py`, `test_input_budget_over_http.py` | the 14 tests that pinned the one-call threshold now pin the N-window limit; 12 new cases (section 6) |

## 3. Cases of the brief and the tests that hold them

| Case of `PRODUCTION-WAVE-PW4.md` section 3 | Tests |
| --- | --- |
| A three-window text yields findings from all three, offsets bind | `test_a_three_window_text_yields_findings_from_all_three_with_global_offsets_that_bind` (stage; the slice of the whole sequence equals each quote); `test_a_three_window_run_publishes_findings_from_every_window_each_tied_to_its_own_call` (executor; published findings, evidence rows, one `model_call` per window) |
| A kill after window 1 and a restart pays for windows 2-3 only (model calls counted) | `test_a_kill_between_windows_resumes_and_the_restart_pays_for_the_remaining_windows_only`: the first adapter saw `[[1,2]]`, the second `[[3,4,5],[6,7,8]]`, three `model_call` rows, window 1's call kept, two Attempts, published; the stage-level pair `test_a_second_call_recovers_finished_windows...` and `test_the_recovered_run_publishes_what_an_uninterrupted_run_publishes` |
| The ceiling counts all windows and stops at a boundary with a named reason | stage: `..._the_call_that_crosses_it_is_recorded_and_named` (window 2 of 3), `test_a_run_at_the_ceiling_stops_at_the_window_boundary_before_it_calls` (before window 3 of 3); executor: `test_the_ceiling_counts_every_window_and_the_run_stops_at_a_boundary_publishing_nothing` (terminal reason `cost_budget_exceeded`, message names window 3, two `model_call` rows, no finding) |
| N+1 windows refused with both figures | start: `test_a_start_above_the_budget_is_refused_with_both_figures` (`LIMIT + 1`, details exactly `character_count` and `budget_characters`) and the over-HTTP twin; plan: `test_a_plan_above_the_limit_is_refused_before_any_call_with_both_figures` (3 windows, limit 2, zero calls) and `test_a_plan_of_exactly_the_limit_is_accepted...` |
| One window's invalid reply fails the run naming the window | `test_a_reply_that_is_not_an_observation_list_fails_the_run_naming_the_window` (window 2 of 3, pages 4-6, window 3 never called), `test_a_json_document_without_an_observation_list_is_invalid`, `test_a_cut_short_window_with_no_usable_finding_fails_the_run_naming_the_window`; and the counter-case `test_an_empty_observation_list_is_a_real_answer_not_an_invalid_one` |
| Under the old budget: exactly one call, the same artifact as before | stage: `test_a_text_that_fits_one_window_is_the_single_call_and_publishes_the_same_artifact` (artifact and metrics equal to `run_text_analysis`, no window metric, no custody write); executor: `test_a_version_within_the_one_call_budget_makes_one_call_and_publishes_what_it_always_did` (counts `None` and exactly the budget: one call, the request key is a committed recording, same findings and evidence); `fixtures/recorded` untouched and `tests/integration/sections` green |

Differences from the design note: (1) a windowed stage carries `windows_request_sha256` (the digest of the ordered window request checksums) and **no** `request_sha256`, so nothing can read a window's checksum as the recording key of the whole text; (2) the tests added beyond the plan are the custody refusals, the reader's call/effect arms, the reclaim arms and the per-window model identity (`R-133`), because each of those is a guard that must be shown to fail.

## 4. Neighbouring suites (run, not edited)

On a migrated private database (section 7): `tests/integration/composition/test_the_served_application_always_passes_a_budget.py` and `test_settings_defaults.py` (the per-call figure still reaches the commands unchanged, which is why `bootstrap/**` needs no edit), `tests/integration/executors/test_explicit_executor.py`, `tests/integration/db/test_durable_analysis_effects.py`, `tests/integration/jobs`, `tests/contract/api_v1/test_w55b_portal_bundle_seal.py` and `tests/unit/runs`: 207 passed together. The unit directories `tests/unit/{jobs,workers,runs,analysis}`: 320 passed. The AR v3 tests inside the 860-test `tests/integration/runs` run are green.

## 5. Mutation table

Method: each row is a one-edit change to the committed source, applied by a scratch harness (not committed), then the named test files are run, then `git checkout -- <file>` restores it; the tree was verified clean after every row (`git status --short` empty). "Red" is the number of failing tests. Test files per row: the key, plan, request and stage rows run `tests/unit/analysis/test_text_windows.py` and `tests/integration/analysis_text/test_text_windowed_stage.py`; the executor, custody, reader and reclaim rows add `test_text_windows_executor.py`, `test_window_reply_custody.py`, `test_completed_window_calls.py` or `test_input_budget.py` as the row concerns. 45 of 45 mutations are red; the green runs are section 7.

| # | Guard mutated | File | Edit (before → after) | Red | First red test |
| --- | --- | --- | --- | ---: | --- |
| M01 | key ignores the text-layer digest | `analysis/text/windows.py` | `"text_layer_sha256": plan.text_sha256,` → `(removed)` | 2 | `the_key_moves_with_the_window_the_text_the_profile_the_model_and_the_r` |
| M02 | key ignores the profile | `analysis/text/windows.py` | `"profile_sha256": profile_sha256,` → `(removed)` | 1 | `the_key_moves_with_the_window_the_text_the_profile_the_model_and_the_r` |
| M03 | key ignores the model | `analysis/text/windows.py` | `"model_id": model_id,` → `(removed)` | 1 | `the_key_moves_with_the_window_the_text_the_profile_the_model_and_the_r` |
| M04 | key ignores the request checksum | `analysis/text/windows.py` | `"request_sha256": request_sha256,` → `(removed)` | 1 | `the_key_moves_with_the_window_the_text_the_profile_the_model_and_the_r` |
| M05 | key ignores the window index | `analysis/text/windows.py` | `"window_index": window.index,` → `(removed)` | 1 | `the_key_moves_with_each_part_of_the_window_s_range_alone[index-1]` |
| M06 | key ignores the window count | `analysis/text/windows.py` | `"window_count": len(plan.windows),` → `(removed)` | 1 | `the_key_moves_with_the_number_of_windows` |
| M07 | key ignores the first page | `analysis/text/windows.py` | `"first_page": window.first_page,` → `(removed)` | 1 | `the_key_moves_with_each_part_of_the_window_s_range_alone[first_page-1]` |
| M08 | key ignores the last page | `analysis/text/windows.py` | `"last_page": window.last_page,` → `(removed)` | 1 | `the_key_moves_with_each_part_of_the_window_s_range_alone[last_page-1]` |
| M09 | key ignores char_start | `analysis/text/windows.py` | `"char_start": window.char_start,` → `(removed)` | 1 | `the_key_moves_with_each_part_of_the_window_s_range_alone[char_start-1]` |
| M10 | key ignores char_end | `analysis/text/windows.py` | `"char_end": window.char_end,` → `(removed)` | 1 | `the_key_moves_with_each_part_of_the_window_s_range_alone[char_end-1]` |
| M11 | each window gets a fresh cost meter | `analysis/text/windowed.py` | `try: cost_meter.check_before_call()` → `cost_meter = CostMeter(ceiling_usd=cost_meter.ceiling_usd) try: cost_meter.check_before_…` | 6 | `the_ceiling_counts_all_windows_and_the_call_that_crosses_it_is_recorde` |
| M12 | no ceiling check before a window's call | `analysis/text/windowed.py` | `cost_meter.check_before_call()` → `pass` | 2 | `a_run_at_the_ceiling_stops_at_the_window_boundary_before_it_calls` |
| M13 | a finished window is never recovered | `analysis/text/windowed.py` | `recovered = None if custody is None else custody.recover(identity.key)` → `recovered = None` | 5 | `a_second_call_recovers_finished_windows_and_calls_only_the_rest` |
| M14 | reclaim counts a finished window as ambiguous again | `jobs/repository.py` | `AND NOT (e.state = 'completed' AND EXISTS (` → `AND NOT (e.state = 'never' AND EXISTS (` | 3 | `a_kill_between_windows_resumes_and_the_restart_pays_for_the_remaining_` |
| M15 | reclaim excuses every completed effect, not only a window's | `jobs/repository.py` | `(regex) "AND NOT \(e\.state = \'completed\' AND` → `"AND NOT (e.state = 'completed'))"` | 1 | `a_lost_attempt_with_a_finished_single_call_is_still_ambiguous` |
| M16 | plan limit off by one | `analysis/text/windows.py` | `if len(windows) > policy.max_windows:` → `if len(windows) >= policy.max_windows:` | 2 | `a_plan_of_exactly_the_limit_is_accepted_and_one_more_is_refused_with_b` |
| M17 | an invalid window reply is read as no findings | `analysis/text/windowed.py` | `if parsed.salvaged and not response.truncated:` → `if False:` | 2 | `a_reply_that_is_not_an_observation_list_fails_the_run_naming_the_windo` |
| M18 | anchors lose the document-global offsets | `analysis/text/windowed.py` | `anchor = next(anchors)` → `anchor = next(anchors) if isinstance(anchor, ResolvedAnchor): anchor = dataclasses.repla…` | 12 | `a_three_window_text_yields_findings_from_all_three_with_global_offsets` |
| M19 | a claim outside its window reaches the cohort | `analysis/text/windowed.py` | `if reply.window.first_page <= item.page_number <= reply.window.last_page )` → `if True )` | 1 | `a_claim_on_a_page_outside_its_window_is_dropped_and_counted_never_publ` |
| M20 | a one-window plan is not the single call | `analysis/text/windowed.py` | `if len(plan.windows) == 1:` → `if False:` | 1 | `a_text_that_fits_one_window_is_the_single_call_and_publishes_the_same_` |
| M21 | start-time limit is the one-call budget | `runs/commands.py` | `limit = windowed_budget_characters(input_budget_characters, MAX_ANALYSIS_WINDOWS)` → `limit = input_budget_characters` | 15 | `a_start_above_the_budget_is_refused_with_both_figures` |
| M22 | the executor never windows | `runs/executor.py` | `if window_policy is None: outcome = run_text_analysis(` → `if True: outcome = run_text_analysis(` | 5 | `a_three_window_run_publishes_findings_from_every_window_each_tied_to_i` |
| M23 | the executor hands no custody to the stage | `runs/executor.py` | `(regex) window_custody=None if version\.text_cha` → `window_custody=None,` | 4 | `a_three_window_run_publishes_findings_from_every_window_each_tied_to_i` |
| M24 | a window's call is completed without its reply reference | `analysis/text/windowed.py` | `parameters = {**request.parameters, **identity.as_parameters(), **dict(extra)}` → `parameters = {**request.parameters, **identity.as_parameters()}` | 5 | `a_three_window_run_publishes_findings_from_every_window_each_tied_to_i` |
| M25 | banners renumber the pages inside a window | `analysis/text/windows.py` | `PAGE_BANNER.format(page_number=page.page_number)` → `PAGE_BANNER.format(page_number=page.page_number - window.first_page + 1)` | 11 | `a_window_request_shows_the_fragment_with_the_documents_own_page_number` |
| M26 | the AR v3 refusal is widened with the section runs' | `runs/commands.py` | `if character_count > input_budget_characters: raise DomainError( ErrorCode.ANALYSIS_INPU…` → `if character_count > input_budget_characters * MAX_ANALYSIS_WINDOWS: raise DomainError( …` | 1 | `the_ar_v3_group_keeps_the_one_call_refusal` |
| M27 | custody does not verify the blob digest | `runs/window_reply_custody.py` | `or hashlib.sha256(data).hexdigest() != call.reply_blob_sha256` → `or False` | 1 | `a_blob_the_row_names_with_another_digest_is_refused` |
| M28 | custody does not bind the envelope to the call | `runs/window_reply_custody.py` | `if document[field] != value or type(document[field]) is not type(value):` → `if False:` | 7 | `an_envelope_that_names_another_call_or_window_is_refused[window_key-00` |
| M29 | custody does not check the response digest | `runs/window_reply_custody.py` | `if response.response_sha256 != call.response_sha256:` → `if False:` | 2 | `a_reply_whose_text_no_longer_matches_the_recorded_response_digest_is_r` |
| M30 | custody does not check the stop reason against the status | `runs/window_reply_custody.py` | `if response.truncated != (call.status == "truncated"):` → `if False:` | 1 | `a_reply_cut_short_in_the_blob_but_complete_on_the_row_is_refused` |
| M31 | custody ignores the provider mode of the saved call | `runs/window_reply_custody.py` | `if call.provider_mode != self._mode.value or call.provider != self._provider:` → `if False:` | 1 | `a_call_of_another_mode_or_provider_is_refused_not_recovered` |
| M32 | custody writes no readback check | `runs/window_reply_custody.py` | `and self._store.read(parse_blob_id(str(published.blob_id)), verify=True) == data` → `and True` | 1 | `a_readback_that_differs_from_what_was_written_is_an_integrity_failure` |
| M33 | the reader skips the duplicate-key check | `jobs/repository.py` | `if call.key in calls:` → `if False:` | 1 | `two_finished_calls_under_one_key_are_refused_not_picked_between` |
| M34 | the reader skips the call/effect agreement | `jobs/repository.py` | `if not ( isinstance(params, Mapping) and row["job_id"] == authority.job_id` → `if False and not ( isinstance(params, Mapping) and row["job_id"] == authority.job_id` | 21 | `a_window_call_whose_mode_is_not_the_runs_is_refused` |
| M35 | a cut-short window with no finding is accepted | `analysis/text/windowed.py` | `if reply.response.truncated and not window_observations:` → `if False:` | 1 | `a_cut_short_window_with_no_usable_finding_fails_the_run_naming_the_win` |
| M36 | a live run in windows needs no custody | `analysis/text/windowed.py` | `if mode is ProviderMode.LIVE and (call_journal is None or custody is None):` → `if mode is ProviderMode.LIVE and call_journal is None:` | 1 | `a_live_run_in_windows_needs_a_durable_journal_and_durable_custody` |
| M37 | a cut-short window claims all of its pages | `analysis/text/windowed.py` | `analysed.extend(_pages_analysed(window_layer, window_observations, truncated=True))` → `analysed.extend(page.page_number for page in pages)` | 1 | `a_cut_short_window_with_findings_makes_the_run_partial_with_the_pages_` |
| M38 | the live model identity is not held per window | `analysis/text/windowed.py` | `refusal = _identity_refusal(response, call, mode)` → `refusal = None` | 1 | `the_model_identity_is_held_on_every_live_window` |
| M39 | the overrun call is not journaled | `analysis/text/windowed.py` | `if call_journal is not None: call_journal.complete(overrun_call)` → `(removed)` | 1 | `the_ceiling_counts_all_windows_and_the_call_that_crosses_it_is_recorde` |
| M40 | the reply is preserved after the call is completed (never) | `analysis/text/windowed.py` | `extra = custody.preserve(` → `extra = (lambda **_: {})(` | 9 | `every_fresh_window_is_one_journal_entry_with_its_identity_and_reply_re` |
| M41 | plan accepts a page larger than a window | `analysis/text/windows.py` | `if exc.reason == "page_exceeds_limit":` → `if False:` | 1 | `a_page_larger_than_a_window_is_refused_and_named_not_split` |
| M42 | the windowed policy engages at the budget, not above it | `analysis/text/windows.py` | `if text_character_count <= call_budget or max_windows == 1:` → `if text_character_count < call_budget or max_windows == 1:` | 1 | `a_count_up_to_and_including_the_call_budget_is_the_single_call` |
| M43 | the rollback constant does not roll back | `analysis/text/windows.py` | `if text_character_count <= call_budget or max_windows == 1:` → `if text_character_count <= call_budget:` | 1 | `one_window_as_the_limit_is_the_rollback_and_never_windows` |
| M44 | reclaim treats a window still in flight (prepared) as safe | `jobs/repository.py` | `"WHERE e.attempt_id = :attempt_id AND e.state <> 'not_processed' "` → `"WHERE e.attempt_id = :attempt_id AND e.state NOT IN ('not_processed', 'prepared') "` | 2 | `a_kill_inside_a_window_is_still_the_ambiguous_effect_it_always_was` |
| M45 | reclaim treats an answer received but not completed as safe | `jobs/repository.py` | `"WHERE e.attempt_id = :attempt_id AND e.state <> 'not_processed' "` → `"WHERE e.attempt_id = :attempt_id AND e.state NOT IN ('not_processed', 'response_receive…` | 2 | `a_version_within_the_one_call_budget_makes_one_call_and_publishes_what` |

One mutation experiment found a defect of **the lane's own test**, not of the code: the first run of M45 also failed `test_a_version_within_the_one_call_budget_...`, because it compared published evidence in database order, which differs between two runs; the test now sorts (`ce801106`) and was repeated six times green.

## 6. Before and after of every modified test

`test_input_budget.py` and `test_input_budget_over_http.py` pinned the **one-call** threshold of the start-time refusal (`budget + 1` refused). With `MAX_ANALYSIS_WINDOWS` calls of `budget` the same assertions hold at `LIMIT = budget x MAX_ANALYSIS_WINDOWS`; nothing was loosened: every refusal still asserts the code, both integers, that nothing is created and the idempotency behaviour, and every acceptance still asserts the run. 14 of them failed on the first run (the other two modified tests were changed for strength and were green either way).

| Test | Before | After |
| --- | --- | --- |
| `test_a_start_above_the_budget_is_refused_with_both_figures` | count `BUDGET + 1`, details `{BUDGET+1, BUDGET}` | count `LIMIT + 1`, details `{LIMIT+1, LIMIT}`, integers |
| `test_a_refused_start_creates_nothing_at_all` | refusal of `BUDGET + 1`, all tables counted | refusal of `LIMIT + 1`, same counting |
| `test_the_same_key_after_the_budget_is_raised_is_a_fresh_start_not_a_replayed_refusal` | refused at `BUDGET`, started at `BUDGET + 1` | count `LIMIT + 1` refused at `BUDGET`, started at `BUDGET + 1` (limit `LIMIT + 12`) |
| `test_a_known_key_over_a_different_payload_is_still_a_key_reuse_not_a_budget_answer` (green either way) | large version `BUDGET + 1` | `LIMIT + 1`, so it is still over the limit and the key reuse still wins |
| `test_the_refusal_is_a_422_envelope_carrying_exactly_the_two_integers` | `BUDGET + 7`, details `{BUDGET+7, BUDGET}` | `LIMIT + 7`, `{LIMIT+7, LIMIT}` |
| `test_a_reaudit_above_the_budget_is_refused_with_both_figures` | `BUDGET + 1` | `LIMIT + 1` |
| `test_a_refused_reaudit_creates_nothing_at_all` | `BUDGET + 1` | `LIMIT + 1` |
| `test_a_reaudit_faces_todays_budget_not_the_one_its_source_was_accepted_under` | source accepted at 40 000, budget lowered to 20 000 refuses 30 000, raised to 30 000 admits | accepted at 40 000 (limit 480 000), lowered to a call budget of 2 000 (limit 24 000) refuses 30 000 with `budget_characters` 24 000, raised to `ceil(30 000 / 12)` admits it; same property: a re-audit sees today's budget |
| `test_the_same_reaudit_key_after_the_budget_is_raised_is_a_fresh_start` | `BUDGET + 1` | `LIMIT + 1` |
| `test_the_role_is_checked_before_the_budget_so_a_refusal_tells_a_stranger_nothing` (green either way) | `BUDGET + 1` | `LIMIT + 1`, so a refusal is really available to leak |
| `test_the_shipped_run_adapter_refuses_a_start_above_its_budget` | over `BUDGET + 1` refused, at `BUDGET` accepted | over `LIMIT + 1` refused, at `LIMIT` accepted |
| `test_the_shipped_execution_adapter_refuses_a_reaudit_above_its_budget` | same | same change |
| over HTTP: `TestStartRun::test_a_version_above_the_budget_is_a_422_and_leaves_nothing`, `::test_the_same_key_after_the_operator_raises_the_ceiling_is_a_fresh_start`, `TestReauditRun::test_a_source_whose_version_is_above_the_budget_is_a_422_and_leaves_nothing`, `::test_the_same_key_after_the_operator_raises_the_ceiling_is_a_fresh_re_audit` | `world.over` = `BUDGET + 1`, envelope `{BUDGET+1, BUDGET}` | `world.over` = `LIMIT + 1`, envelope `{LIMIT+1, LIMIT}`; `world.at` = `LIMIT`; the raised client still takes `BUDGET + 1` |

New in these two files (all green, each with a mutation in section 5): `test_the_limit_is_that_many_calls_of_the_budget`, `test_a_start_above_one_call_and_within_the_windows_is_accepted` (4 counts), `test_a_reaudit_above_one_call_and_within_the_windows_is_accepted` (3 counts), `test_one_window_as_the_limit_restores_the_one_call_refusal` (the rollback), `test_the_ar_v3_group_keeps_the_one_call_refusal`, and over HTTP `test_a_version_above_one_call_and_within_the_windows_is_accepted` and `test_a_source_above_one_call_and_within_the_windows_is_accepted`.

## 7. Commands and counts

Prefix for every command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider` with `BS` the bootstrap site-packages and `.venv` a symlink; the database-bound runs were repeated with `DATABASE_URL` pointing at a private database `lane_ch_private_01` created, migrated to `0033_ar_v3_cite_stage_id` with the literal alembic command and dropped by the lane (the shared lane database held residue, section 9). Free disk stayed at 1.8-1.9 GiB throughout.

| Command (targets) | Result |
| --- | --- |
| `tests/unit/analysis tests/integration/analysis_text` | 599 passed (baseline on `6075df88`: 542, so +57 = 31 + 26 new) |
| `tests/unit/analysis tests/integration/analysis_text tests/integration/sections tests/contract/analysis_packages tests/contract/architecture` | 833 passed |
| `tests/integration/runs` (private database) | 860 passed (baseline: exit 0 at `6075df88`; 779 by difference: 7 + 25 + 37 + 12 new) |
| `tests/integration/runs` (shared lane database, same tree) | 859 passed, 1 failed: `test_durable_effect_boundaries.py::test_provider_effect_settlement_is_bounded_and_resumable`, which asserts the **global** set of unresolved provider effects of the database; at that moment it held three that were not the test's own: two committed by the lane's mutation experiment M44 (settled by the lane afterwards) and one created at 21:13 UTC, before the lane's first edit (not attributable to the lane; already settled when inspected). The file was not re-run on the shared database, see section 9 |
| the neighbouring suites of section 4 | 207 passed; `tests/unit/{jobs,workers,runs,analysis}` 320 passed |
| `tests/integration/qa_w55b/test_p3_input_budget.py` (outside the lane) | 3 passed, 2 failed, predicted and explained in section 9 |
| mutations (section 5) | 45 of 45 red, tree clean after each |
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`; `git diff --check` | 105 passed; `git diff --check` exit 0 |
| governance one-liner on the task file | `[]` |

## 8. Limits

1. **Windows do not make a large volume cheaper.** The budget is a cost figure (`D-162`): a full window at the primary model costs about USD 0.45 of measured-density input plus output, against the USD 1.00 default ceiling, so a default-configured run of the primary model finishes about two full windows (roughly 90 pages at the real set's density) and then stops at a window boundary with the ceiling named. More needs a higher ceiling, a cheaper model (572 361 characters per window at the cheaper tier) or an unmetered connection (the meter charges it nothing). There is no pre-flight estimate of the plan's cost (a deliberate non-goal: the pessimistic arithmetic of `budget.py` would refuse the two-window runs this is for); a ceiling too low for the volume is therefore found by paying for the first windows, which are recorded and named. Owner choice, tied to `AD-18` / `PROD-20`.
2. **The 900-second watchdog.** A kill between windows resumes; a window in flight when the watchdog fires (or the process dies) is an ambiguous effect: the run fails `provider_outcome_unknown` and the finished windows are paid for and lost. Nothing yields at a window boundary before the watchdog. With the deterministic stages taking 300-400 s on a large drawing set (`D-171`) a 12-window run of the primary model will meet this. The follow-up is precise: stop starting windows when `AttemptContext.remaining_seconds()` is below the per-call ceiling (200 s) and return the Attempt to the queue through a new `jobs` transition (running to lost, Lease released, Job back to queued) so the next Attempt recovers the finished windows; it needs a `jobs/**` state-machine change and its own tests, so it is not in this lane.
3. **Independence is stored, not shown.** The statement that windows were analysed independently is in `stage_result.metrics` (`windows_note`) and in every window's prompt; the frozen `RunStatus` exposes no stage metrics, so a reviewer does not see it on a screen. Showing it is a contract and screen change.
4. **A finding that needs two windows is not found.** By design and said so. A claim on a page outside its window is dropped and counted (`evidence_outside_window`), never fatal.
5. **A failed or stopped run publishes nothing**, even when most windows finished. Their replies stay as private blobs and their cost stays on the `model_call` rows; a re-audit starts a new Run and pays again.
6. **Recovery is per Job.** Windows are recovered within one Run (three Attempts at most); a re-audit or a new start recovers nothing.
7. **The start-time check and the plan use two counts.** The check compares pypdfium2's count with the limit; the plan packs pdfplumber's pages, so a text that passed the check can still need more than twelve windows (page packing) or contain a page larger than a window; both fail the stage before any call (`window_plan_over_limit`, `window_page_exceeds_limit`) with the stored code `analysis_input_invalid`, because `analysis_input_budget_exceeded` is never stored.
8. **The window preamble and the recovered-window path are unreviewed**: the preamble is model-facing Russian text outside the section packages (`A-7`: nobody reviewed it), and no live model or paid call was made (`R-29`): the scripted adapters prove the mechanics, not the quality of a windowed analysis.
9. **The reply blobs are never bound.** Like the AR v3 reply blob they are `verifying`, with an `analysis_artifact_publication` intent that reconciliation settles `abandoned` after the Attempt ends; the bytes are kept. A retention rule for them belongs with `PROD-19` (accepted risk `A-6`).

## 9. Integration notes

1. **Merge.** Disjoint from the OP lane (contract, `optimisation/**`), WC (web) and G1/G2 (section packages). The only shared file with another lane's likely scope is `src/auditmanager/analysis/public.py` (additive lines at the import block and `__all__`).
2. **One out-of-lane test goes red and needs a decision.** `tests/integration/qa_w55b/test_p3_input_budget.py` (needs the served child; run here on the private database): `test_at_a_low_ceiling_a_start_and_a_reaudit_over_the_budget_are_refused_with_both_figures` and `test_a_document_exactly_at_the_budget_starts_and_one_character_less_refuses` expect a 40-page bundle (about 100-150 thousand characters) to be refused when its count is just above the one-call budget. Now such a version is accepted and windowed; the refusal needs a count above `budget x 12` (at the lowest ceiling the application starts with, 93 690 x 12 = 1.12 million characters), which the probe's `text_rich_bundle(40)` is not. The probe must either build a bundle of that size or assert acceptance for the windowed range and keep the refusal on a stored count; I did not touch it (outside `allowed_paths`).
3. **Contract prose.** The text of `analysis_input_budget_exceeded` in `contracts/domain/v1/error-codes.json` (summary and note) and in `contracts/api/v1/openapi.json` / `web/openapi/openapi.json` still says the text is "larger than the analysis input budget" and that the budget is derived from the model and the ceiling. After this lane `budget_characters` is that figure times `MAX_ANALYSIS_WINDOWS`. Keys, types and status are unchanged, so no schema or client changes; the sentence should be corrected at the next contract reseal (the OP lane owns the seal this wave). Suggested text: "larger than the most a run takes: the analysis input budget of one model call (derived from the configured model and the per-run cost ceiling) times the number of windows a run may use; `budget_characters` is that product". The web sentence (`input-budget.ts`: "допустимо не более: N") stays true.
4. **Debt rows to record** (the lane does not edit the register): the watchdog with a window in flight (limit 2); no pre-flight cost estimate (limit 1); independence not shown to the reviewer (limit 3); the contract prose; the QA probe. `D-162` is related (the budget models cost, not the context window).
5. **The shared lane database held residue, and one leftover is not the lane's to settle.** The first full `tests/integration/runs` run on the shared database failed one test that asserts the global set of unresolved provider effects (section 7). Two of the three extra effects were committed there by the lane's own mutation experiment M44 (the lane failed those two runs and abandoned their effects through the repository's own transitions); the third pre-dates the lane's first edit and was already settled when inspected. The aborted test then left its own victim: `mc_01M5X2GXCYP0012S7A516NPPYR` on `run_01M5X2GX2142EMC2HQZKV877EV` (Attempt `running`, a lease that expires, `text_character_count` NULL). I did not touch it (the environment refused the cleanup and it is not the lane's run). Until a reclaim sweep or a settlement pass handles it, the next run of that one test on the shared database fails on its global assertion; any pass that reclaims expired leases and settles terminal effects clears it, and it does not exist on a reset database. Tests of this lane that commit (the kill cases) leave no `prepared` or `response_received` effect when they pass; the full runs directory passes on a private database (860).
6. **Rollback** is one constant (section 1.9), held by two tests.
7. **Not done on purpose:** nothing under `fixtures/recorded` (the window cases use scripted adapters and need no recording), nothing in `bootstrap/**` (the brief allows `providers.py`; it needs no edit).

## 10. Forbidden paths are untouched

`git diff --name-only 6075df88..HEAD` (the complete list, taken after the last commit):

```text
docs/program/SECTION-CHUNKED-ANALYSIS-01.md
docs/program/tasks/SECTION-CHUNKED-ANALYSIS-01.md
src/auditmanager/analysis/public.py
src/auditmanager/analysis/text/__init__.py
src/auditmanager/analysis/text/adapter.py
src/auditmanager/analysis/text/budget.py
src/auditmanager/analysis/text/windowed.py
src/auditmanager/analysis/text/windows.py
src/auditmanager/jobs/public.py
src/auditmanager/jobs/repository.py
src/auditmanager/runs/commands.py
src/auditmanager/runs/executor.py
src/auditmanager/runs/window_reply_custody.py
tests/integration/analysis_text/test_text_windowed_stage.py
tests/integration/runs/test_completed_window_calls.py
tests/integration/runs/test_input_budget.py
tests/integration/runs/test_input_budget_over_http.py
tests/integration/runs/test_text_windows_executor.py
tests/integration/runs/test_window_reply_custody.py
tests/unit/analysis/test_text_windows.py
```

None of `contracts/**`, `web/**`, `db/migrations/**`, `infra/**`, `src/auditmanager/analysis/text/profiles/**`, `src/auditmanager/optimisation/**`, `fixtures/recorded/sections/**`, `bootstrap/**`, `runs/v3_*`, `analysis/profiles/ar_v3/**`, the register, `CURRENT_STATE.md`, rulings or ADRs appears. The one file outside the brief's list is `src/auditmanager/analysis/public.py` (additive exports; section 2).
