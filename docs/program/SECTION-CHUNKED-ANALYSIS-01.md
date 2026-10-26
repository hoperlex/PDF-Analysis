# SECTION-CHUNKED-ANALYSIS-01 — whole-page windows for a section run above the one-call budget

Lane CH of production wave PW4 (`docs/program/dispatch/PRODUCTION-WAVE-PW4.md` section 3), base `6075df88`,
branch `agent/section-chunked-analysis-01`. Task file: `docs/program/tasks/SECTION-CHUNKED-ANALYSIS-01.md`
(premise output is printed there). This file is committed in two steps: the **Design** section first (before any
code), the rest when the code and tests are done.

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
