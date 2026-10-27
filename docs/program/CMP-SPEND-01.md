# CMP-SPEND-01 — the comparison spend journal, its call wrapper, the USD ceilings and the one-connection check

Written 2026-10-28 by the Sonnet lane `CMP-SPEND-01` (branch `agent/cmp-spend-01`, base `34dcf9a1` on `integration/compare-modules`; nothing pushed,
nothing merged). Task file: [`tasks/CMP-SPEND-01.md`](tasks/CMP-SPEND-01.md). Decisions cited are those of
[`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (4, 5, 6, 18, 19; `Q-CMP-7`); the wave brief is
[`dispatch/CMP-WAVE-C0.md`](dispatch/CMP-WAVE-C0.md); the tables are the seal's ([`CMP-SEAL-C0.md`](CMP-SEAL-C0.md)); the queue's hook is
[`CMP-WORK-01.md`](CMP-WORK-01.md); the image refusal is [`CMP-EXEC-IMAGES-01.md`](CMP-EXEC-IMAGES-01.md).

## 1. Base facts, printed before any edit

Contract `1.9.0`, **115 paths / 130 operations / 351 schemas**, 27 error codes, `VERSION` `0.9.0`, head `0038_comparison_foundation`, base
`34dcf9a1dad7c4f9e3ac131eb990ab673502dc12` (task file `P-01`). Equal to the brief's premise, so the lane went on. Nothing in `contracts/**` or
`db/migrations/**` was changed; no column was missing (the journal, the `comparison_call` origin and `comparison_attempt_id` were sealed by `0038`).

## 2. What was built

| path | what it holds |
| --- | --- |
| `src/auditmanager/comparison/spend/repository.py` | `ComparisonSpendRepository`, the only writer of `comparison_model_call`: `prepare`, `mark_sent`, `complete`, `fail`, `mark_unknown`, `settle_attempt`, `settle_abandoned`, `attach_task`; the reads that decide a call: `job_spend`, `day_spend`, `connection_has_active_run`, `connection_has_active_call`, `open_calls_of_other_attempts`; the two advisory locks |
| `.../caller.py` | `ComparisonModelCaller.call(...)`: the whole protocol of a call (section 3) |
| `.../ceilings.py` | the money rules, pure: `check_before_call`, `check_after_call`, `job_ceiling_micros` |
| `.../model.py` | the vocabulary: states, `Consent`, `CallRoute`, `CallEstimate`, `CallResult`, `SpendPause`, `Spend`, the constants of `Q-CMP-7`, integer money |
| `.../errors.py` | the typed refusals (`CallRefused`, `CallFailed`, `OutcomeUnknown`, `CallLost`), each with `as_outcome()` for a handler |
| `.../settler.py` | `settle_lost_attempt`, the entry of `SPEND_SETTLERS` |
| `comparison/public.py` | `SPEND_SETTLERS = (settle_lost_attempt,)`; the names of this lane (`ComparisonModelCaller`, `ComparisonSpendRepository`, `Consent`, `CallRoute`, `CallEstimate`, `CallResult`, `CallRecord`, `SpendPause`, `SpendError` and its four subclasses, `SPEND_JOB_KEY`, `JOB_CEILING_USD`, `DAY_CEILING_USD`, `job_ceiling_micros`, `settle_lost_attempt`) |
| `executors/runner_repository.py` | the `comparison_call` origin path: `insert_task(..., comparison_attempt_id=)`, `TaskRecord.comparison_attempt_id`, the live comparison attempt as the alternative to the live Run attempt in `sweep`, `claim_next` and `live_claim_and_attempt` |
| `dashboard/repository.py` | `_SPEND` as the union of `model_call` and `comparison_model_call` |
| `jobs/repository.py` | **by grant**: the one query of the connection check (section 5) |
| `scripts/recovery/grant_classification.py` | `comparison_model_call` leaves `SEALED_NOT_YET_WRITTEN` (wiring rule 4) |

## 3. The call wrapper for the comparison AI lanes

```python
from auditmanager.comparison.public import (
    CallEstimate, CallRoute, ComparisonModelCaller, Consent, SpendError,
)

caller = ComparisonModelCaller(deps.session_factory)            # WorkDependencies.session_factory; one per process is enough

route = CallRoute(                                              # what serves the call
    adapter=adapter,                  # any ModelAdapter (PullAdapter, an HTTP adapter, a recorded one): its provider_mode decides recorded/live
    model_identity=pin.model_id,      # the pinned model
    connection_revision_id=revision_id,   # the executor connection revision (decision 17: always one for a live call)
    expected_model=gateway_model,     # the name the reply must report (R-133)
    check_identity=True,
    unmetered=(billing == "not_metered"),
    pin=pin,                          # ModelPin: the rates; required for a live metered call
)   # or CallRoute.from_binding(adapter, call_binding, pin) for a CallBinding

consent = Consent(estimate_digest=sha256_hex, estimate_usd=4.0, ceiling_usd=6.0,       # ceiling <= 10, else ValueError
                  connection_revision_id=revision_id, pinned_model=pin.model_id)
estimate = CallEstimate(input_tokens=prompt_tokens + image_tokens, output_tokens=request.body["max_tokens"])

try:
    result = caller.call(item, route, request, estimate=estimate, consent=consent)    # item: the claimed WorkItem
except SpendError as error:
    return error.as_outcome()         # Failed(reason) / Failed(reason, retry=True) / Yielded(15 s) for a busy connection
# result.response (ModelResponse), result.call_id, result.cost_basis, result.cost_micros,
# result.pause (SpendPause or None): the reply is valid and paid for; make NO further call in the job when set
```

What `call` does, in order (each step a transaction of its own, committed):

1. **No database** -- a live call without a consent (`consent_required`), a consent for another revision or model (`consent_stale`), a reply that
   cannot be held to a model (`model_not_selected`: nothing or a gateway stub, `R-133`). A recorded adapter needs no consent and spends nothing.
2. **Prepare** -- the attempt still holds the item (`require_current`); no earlier attempt of the item left a call open (`unsettled_call`); the
   connection has no other user (`connection_busy`: a Run, or another comparison call), decided under the Run claim's own advisory lock; the
   ceilings hold -- under an installation-wide lock -- (`job_ceiling`, `day_ceiling`, `overrun`); then the **`prepared` row is inserted and committed
   before anything is sent**.
3. **Sent** -- `prepared -> sent`, again under the attempt's authority; the adapter is called only after this commit.
4. **The adapter, once.** Nothing retries.
5. **Settle** -- `completed` with the cost (`measured` when the transport reported one, else `estimated` from the pin, `unmetered` for a
   `not_metered` route and for every recorded reply); `failed` when the transport proved nothing was processed (`not_sent`, `rate_limited`,
   `proxy_unavailable`, `definite_refusal`) or when the provider answered something unusable (with the cost it may have charged); `unknown`
   otherwise; a reply that names another model is `failed` **with its cost** and nothing is returned (`model_identity_mismatch`).

Money. Estimates are priced from the pinned rates (`CallEstimate` is a size in tokens; the caller never supplies a USD figure) and round **up**;
a measured cost rounds to the nearest micro-USD; all sums are integers. `estimate_micros` is **0** for an unmetered call, so such a call reserves
nothing against any ceiling.

## 4. Decisions this lane made (each is one place to change)

1. **How a runner's refusal of the images counts** (`executor_image_input_unsupported`, class `outcome_unknown` from `PullAdapter`). The runner tools
   refuse before any model runs in four of five tools, but the contract also lets a session refuse after it has looked at the images, so on a
   **metered** route it cannot be shown that nothing was spent: the row is `unknown` and the wrapper raises `OutcomeUnknown` (no automatic re-send).
   On a route that costs nothing there is nothing unknown: the row is `failed`, the reason is `executor_image_input_unsupported`, and the answer is a
   different route. (`caller._settle_error`; both branches are tests.)
2. **The "job" of the ceiling** is the AI job the user consented to. The schema has no job column and the AI job object is `CMP-SEAL-C2`'s, so the
   items of one job are those whose payload carries the same `ai_job_id` (`SPEND_JOB_KEY`) within one project; an item without it is a job of its
   own. A malformed value is refused loudly. **C2 must put `ai_job_id` in the payload of every item of an AI job.**
3. **The day** is the UTC day of the database clock and counts the **comparison journal only** (`Q-CMP-7` is the ceiling of comparison AI); the Run
   path keeps its per-run ceiling. Reserved money (open and `unknown` calls at their estimate) counts against both ceilings; a ceiling refuses a call
   that would **cross** it, one that reaches it exactly is allowed (the Run path's meter refuses only when already at it).
4. **The 1.2 x rule** is judged on the job's known cost (completed calls and failed calls that were charged) against the estimate of the **consent**.
   It refuses the next call before it is made, and after a call that crosses it the result carries `pause`, so the paid-for reply is not thrown away.
5. **One user per connection, in both directions.** A comparison call takes the Run claim's own advisory lock, refuses while a Run is active on the
   connection, and also while another comparison call is (the connection is taken per call, ADR decision 6). "Active" for a call is: `prepared` or
   `sent` **and** its attempt still `created`, `leased` or `running` -- a killed worker's call keeps the connection busy until the reclaim ends the
   attempt (the Run rule for an expired Lease), and a row left open by an attempt that is over blocks nothing.
6. **A consent is required for every live call**, `not_metered` included (it binds the route and the model); only the money rules do not apply to it.
   A recorded reply needs none.
7. **No catalogue error is added.** The refusals are local exceptions with a `reason` code a work item can store.

## 5. The grant in `src/auditmanager/jobs/repository.py` (conditions of the PW5 integrator)

**Function and query:** `JobRepository._hold_connection_limit` (a static method) runs the module constant `_CONNECTION_HAS_OTHER_ACTIVE_RUN` under the
connection's advisory lock `_LOCK_CONNECTION`. Only the constant changed. Before:

```python
_CONNECTION_HAS_OTHER_ACTIVE_RUN = text(
    "SELECT EXISTS (SELECT 1 FROM job other_job "
    "JOIN audit_run other ON other.run_id = other_job.run_id "
    "JOIN executor_connection_revision peer ON peer.revision_id = other.connection_revision_id "
    "WHERE peer.connection_id = :connection_id AND other.run_id <> :run_id "
    f"AND other_job.state IN {_ACTIVE_JOB_STATES})"
)
```

After (the first `EXISTS` is byte-identical):

```python
_CONNECTION_HAS_OTHER_ACTIVE_RUN = text(
    "SELECT EXISTS (SELECT 1 FROM job other_job "
    "JOIN audit_run other ON other.run_id = other_job.run_id "
    "JOIN executor_connection_revision peer ON peer.revision_id = other.connection_revision_id "
    "WHERE peer.connection_id = :connection_id AND other.run_id <> :run_id "
    f"AND other_job.state IN {_ACTIVE_JOB_STATES}) "
    "OR EXISTS (SELECT 1 FROM comparison_model_call active_call "
    "JOIN comparison_work_attempt active_attempt "
    "ON active_attempt.comparison_work_attempt_id = active_call.comparison_work_attempt_id "
    "JOIN executor_connection_revision call_peer "
    "ON call_peer.revision_id = active_call.connection_revision_id "
    "WHERE call_peer.connection_id = :connection_id "
    "AND active_call.state IN ('prepared', 'sent') "
    "AND active_attempt.state IN ('created', 'leased', 'running'))"
)
```

The edit also adds a comment above the constant. Nothing else in `src/auditmanager/jobs/**` changed (`git diff --numstat 34dcf9a1..HEAD -- src/auditmanager/jobs`
is that one file, 16 added and 1 removed lines, the comment included); no schema change. Conditions:

| condition | evidence |
| --- | --- |
| a mutation proof: the old query back goes red | **M17a**: 7 of this lane's tests go red (section 7); M17c, M17d, M17e put the *new* half out of shape and each goes red |
| a test that a plain run still serialises per connection exactly as before | `test_a_plain_run_still_serialises_per_connection_as_before` and `test_a_comparison_row_of_a_finished_attempt_changes_nothing_for_a_run` (`tests/integration/comparison/spend/test_connection_single_user.py`); both also pass under M17a, as they must |
| the `EXEC-PAR-QUEUE-01` tests stay green **unmodified** | `tests/integration/jobs/test_connection_limit_claim.py`, `tests/integration/workers/test_worker_slots.py`, `.../test_worker_composition.py`, `tests/unit/workers`: **73 passed** on the new query and **43 passed** (the three integration files) with the old query put back (M17b); `git diff 34dcf9a1..HEAD -- tests/integration/jobs tests/integration/workers tests/unit/workers` is empty |
| the dispatch hint is not part of the grant | `_NEXT_JOB` is untouched (see section 8, item 1) |

## 6. Checks (light acceptance; the stack is the lane's own: `auditmanager-cmp-spend-01`, ports 57780 / 61780 / 61781, head `0038`)

`df -h /` before the stack, before each long run and at the end: 3.1 GiB at the start, 2.4 GiB at the lowest (the brief's stop line is 1.5 GiB).

| what | command (from the worktree root, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q`) | result |
| --- | --- | --- |
| diff hygiene | `git diff --check 34dcf9a1..HEAD` | clean (exit 0) |
| this lane, unit | `tests/unit/comparison/spend` | **113 passed, 1 xfailed** (the strict pin of section 8, item 3), 1.4 s, no container |
| this lane, integration | `tests/integration/comparison/spend` | **85 passed**, 5.5 s |
| the whole comparison integration directory | `tests/integration/comparison` | **324 passed** (the queue lane's 239 plus this lane's 85) |
| `EXEC-PAR-QUEUE-01`, unmodified | `tests/integration/jobs/test_connection_limit_claim.py tests/integration/workers/test_worker_slots.py tests/integration/workers/test_worker_composition.py tests/unit/workers` | **73 passed** |
| neighbours of the changed source | `tests/integration/executors/{test_http_run_path,test_runner_channel,test_pull_run_path,test_claim_image_gating,test_runner_seam}.py tests/integration/jobs tests/integration/dashboard` | **182 passed** (`test_http_run_path.py` appends `WHERE run_id = :r` to `_SPEND`: unmodified and green) |
| the classification, the router answers, the unit neighbours | `tests/integration/comparison tests/integration/recovery/test_grant_classification.py tests/integration/recovery/test_comparison_foundation_erase.py tests/integration/composition/test_router_answers.py tests/unit/comparison tests/unit/jobs tests/unit/executors/test_pull_adapter.py` | **783 passed, 1 skipped, 1 xfailed** (before the last two tests of this lane were added) |
| contract battery | `tests/contract` with `--ignore` of `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (`D-220`) | **1307 passed**, 19283 subtests, 134 s (includes the import-boundary test) |

| task handoff tool | `python3 scripts/task_handoff.py --task docs/program/tasks/CMP-SPEND-01.md --check-json '["git","diff","--check"]'` | `CHECKS PASS` (path check against the task file's allowed list: PASS; whitespace: PASS); the evidence file is `.local/handoff/CMP-SPEND-01-evidence.md` (ignored), bound to the head it was run on |

The neighbour and contract runs were made on the source of commit `d8d48cee`; `git diff d8d48cee..HEAD -- src scripts db contracts` is empty (what came
after is tests only). Not run, by the brief: `make gate` (`R-135` defers it; note that `AGENTS.md` section 8 case 3 names a new `conftest.py`, and this lane adds
`tests/integration/comparison/spend/conftest.py`, so the final gate covers it), the web battery (no web change), the live journey.

## 7. Mutation proofs

Each row: the quoted mutation, the files run (both of this lane's directories, 197 tests at the time and 199 now, unless named), the number of failed
tests (pytest's count, a parametrised case counts each time), then the file restored by `git checkout` and `git diff --quiet` proven (the tool printed
`restored: true` for every row). Rows marked **†** survived the first run;
the test named in their last column was added and the mutation re-run red.

| # | commitment | mutation | failed |
| --- | --- | --- | --- |
| M1 | a call is prepared before it is sent | the `prepared` insert is not committed | **47**; among them `test_the_prepared_row_is_committed_and_visible_before_the_adapter_is_called` and `test_the_prepared_row_is_committed_before_the_adapter_is_called_and_the_adapter_once` |
| M2 | **a provider call without a prior `prepared` row is impossible** | the prepare inserts nothing and the send checks nothing | **59** (the same two, and `test_a_call_whose_row_is_no_longer_prepared_is_not_sent`) |
| M3 | the wrapper never retries | a failed call is called once more | **11** (`adapter.calls == 1`) |
| M4 | **reclaim never re-sends after prepared/sent** | the settler is not in `SPEND_SETTLERS` | **9** (the kill-and-reclaim tests, the composition test) |
| M5 | the item ends `spend_unknown`, not queued | the settler marks the rows but answers `False` | **6** |
| M6 | a `prepared` row is settled too | the settler's statement covers only `sent` | **3** |
| M7 | the belt (an earlier attempt's open call stops the next send) | `open_calls_of_other_attempts` answers 0 | **1** (`test_an_earlier_attempts_open_call_stops_the_next_attempt_from_sending_if_no_settler_ran`) |
| M8 | **ceilings refuse before the call** | `check_before_call` returns at once | **20** |
| M9a | a call exactly at the job ceiling is allowed | `>` becomes `>=` | **3** |
| M9b | money in flight counts against the job ceiling | `committed` becomes `actual` | **6** |
| M9c | money in flight counts against the day ceiling | `committed` becomes `actual` | **4** |
| M9d, M9e | the ceilings are USD 10 and USD 50 | 100 / 500 | **3** / **7** |
| M10a | **overrun pauses** (after the call) | the post-call check never answers | **3** |
| M10b | **overrun pauses** (the next call) | the pre-call overrun check is off | **4** |
| M10c | the factor is 1.2 | 6/5 becomes 7/5 | **8** |
| M11 | **`not_metered` is not money-limited** | a `not_metered` live route goes through the ceilings | **8** |
| M12 | the day ceiling is decided under one lock | the installation lock is not taken | **2** (`test_two_workers_cannot_both_fit_the_one_call_that_fits`) |
| M13 | the day is the UTC day | the day filter is dropped | **1** |
| M14 | **a reply from another model is refused (`R-133`)** | the identity check returns at once | **7** |
| M15 | a call and a Run's claim cannot both pass | the connection lock is not taken | **2** (`test_a_comparison_call_waits_for_a_run_claim_that_holds_the_connection_lock_and_then_sees_the_run`) |
| M16a, M16b | one user per connection | the Run / the other call is not asked | **4** / **3** |
| M17a | **the grant: the old query back** | `_CONNECTION_HAS_OTHER_ACTIVE_RUN` as before | **7**: the `prepared` and `sent` cases of `test_a_runs_claim_is_refused_exactly_while_a_comparison_call_is_open_on_its_connection`, `test_a_runs_claim_is_not_refused_by_a_call_on_another_connection_or_by_a_run_with_none`, `test_the_runs_claim_is_refused_while_the_wrapper_is_calling_and_free_after_it_returns`, `test_the_connection_stays_busy_while_the_calls_worker_may_still_be_sending...`, `test_the_claim_and_the_comparison_side_agree_on_what_is_active` and the text pin of the query |
| M17b | the same, run against the `EXEC-PAR-QUEUE-01` tests | old query back | **0** red, 43 passed: those tests do not see the grant, which is the condition |
| M17c, M17d, M17e | the new half is right | counts an ended attempt / an `unknown` call / every connection | **3** / **3** / **1** |
| M18a, M18b | the dashboard spend is the union | the comparison half dropped / an open call counted | **2** / **1** |
| M19a, M19b, M19c | the task of an ended comparison attempt is never served | the branch missing from `claim_next` / `sweep` / `live_claim_and_attempt` | **2** / **1** / **1** |
| M19d † | the attempt must be the item's current one | the `current_work_attempt_id` join dropped | 0, then **1** after `test_a_task_whose_attempt_is_running_but_is_not_the_items_current_attempt_is_not_served` |
| M20, M21 | a consent binds the route and exists | stale / absent consent accepted | **5** / **2** |
| M22 | a worker that lost its lease cannot prepare | `require_current` dropped from the prepare | **2** |
| M23 † | a worker that lost its lease cannot send | `require_current` dropped from the send | 0, then **1** after `test_a_lease_lost_between_the_two_commits_sends_nothing_even_when_no_settler_ended_the_row` |
| M24 | a late reply does not overwrite what the reclaim settled | the "no row changed" check dropped | **2** |
| M25 | what the transport proves decides the row | `_NOT_PROCESSED` emptied | **8** |
| M26 | housekeeping settles an ended attempt's open call | `settle_abandoned` dropped | **2** |
| M27 | an unusable answer's cost is recorded | the cost not computed | **3** |
| M28 | the mode comes from the adapter | a recorded reply journalled as live | **5** |
| M29 | **one door to a model** | a module of the comparison context (`pairing.py`) calls an adapter's `complete` | **1** (`test_only_the_spend_wrapper_calls_an_adapter_in_the_comparison_context`, the AST guard over `src/auditmanager/comparison`; run on `test_wiring_and_pins.py` alone); M3 also turns `test_the_wrapper_is_the_only_caller_of_an_adapter_inside_the_spend_package` red |



## 8. Findings, deviations and open items

1. **The dispatch hint does not see comparison calls.** The grant is for the check; `_NEXT_JOB` still offers a Run whose connection holds only an
   active comparison call. The claim then refuses it (`ExecutionNotClaimed`) and the worker's existing bounded retry (`CLAIM_RETRY_LIMIT`) absorbs it; a
   call is bounded by its answer deadline, and the comparison loop claims no new item while a Run is claimable, so a Run waits at most the call in
   flight. If the hint should skip such a connection too, that is a second query and a second grant.
2. **A finding in the queue's reclaim (`comparison/work/repository.py`, not this lane's file):** `reclaim_expired` ends a **cancelled** item before it asks
   the settlers, so a call that was `sent` when the worker died is left open. This lane's guards make it harmless -- an open call blocks a connection only
   while its attempt is live, it reserves its estimate against the ceilings, and `settle_abandoned` (called inside every prepare) ends it `unknown` -- and
   `test_a_cancel_that_arrives_with_a_lost_lease_is_not_settled_by_the_queue_but_by_the_next_call` pins it. The clean fix is one line in the queue
   (ask the settlers in the cancel branch too); the integrator may also call `ComparisonSpendRepository.settle_abandoned` from the worker's reclaim pass.
3. **`executors/pull.py` is not on this row, so a `PullAdapter` still writes `origin='run_call'` for every call.** The repository half is done and tested
   (`insert_task(comparison_attempt_id=)`, the three liveness statements). The integrator's hunk, in `PullAdapter._write_task`:
   ```python
   comparison_attempt_id = getattr(context, "comparison_attempt_id", None)
   task = self._repository.insert_task(
       session, connection_id=..., revision_id=...,
       origin="comparison_call" if comparison_attempt_id is not None else "run_call",
       run_id=getattr(context, "run_id", None), attempt_id=getattr(context, "attempt_id", None),
       model_call_id=getattr(context, "call_id", None), probe_id=None, expected_model=..., payload=payload,
       deadline_seconds=window, comparison_attempt_id=comparison_attempt_id,
   )
   ```
   (`tests/unit/executors/test_pull_adapter.py`'s `FakeStore.insert_task(**kwargs)` accepts the new keyword.) A comparison call's `context` also needs
   `remaining_seconds()` (`answer_window`). `tests/unit/comparison/spend/test_wiring_and_pins.py::test_a_pull_adapter_writes_the_comparison_origin_for_a_comparison_call`
   is a **strict xfail** that turns red the moment the hunk is applied; the marker is then removed and the test stays as the pin. The wrapper does not
   link the journal row to the task (`attach_task` exists and is tested; a later lane calls it once its adapter knows the task id).
4. **No handler and no composition change.** The queue's `WorkDependencies` carries no caller; a later lane builds `ComparisonModelCaller(deps.session_factory)`.
5. **`ai_job_id` is a convention until C2 writes the job** (section 4, item 2); the ADR's "job" is not yet an object.
6. **Estimates are the caller's sizes.** `CallEstimate.input_tokens` must include the images (decision 18); the wrapper prices them from the pin but cannot count
   them. The pre-call refusal is only as good as the estimate; the post-call overrun check measures the truth.
7. **Held locks.** The prepare transaction keeps the item's and the attempt's row locks (`require_current`) while it waits for the connection and the installation
   locks. Both waits are short (the Run claim and a prepare are short transactions), the heartbeat's own lock wait is bounded, and a missed beat is covered
   by the 60 s lease; it is the order the queue documents (item, then attempt).
8. **Not measured:** a real provider, a real runner, throughput; no live call was made (recorded and scripted adapters only, `R-29`). The mutation tool is a
   scratch script outside the tree; its replacements are the table of section 7.
9. **Commit trailer.** The wave brief (rule 8) names `Co-Authored-By: Claude Sonnet 4.6`; the lane followed it although the session runs on another Sonnet
   build. The integrator may rewrite the trailer on merge.

## 9. Instructions for the integrator

1. Merge in the wave's order (brief section 3). Hunks in shared files: `comparison/public.py` (an import block before the `work` imports, the settler in
   `SPEND_SETTLERS`, 19 names at the top of `__all__`), `executors/runner_repository.py`, `dashboard/repository.py`, `jobs/repository.py` (the one granted
   constant), `grant_classification.py` (one name out of the set). None touches `bootstrap/**`.
2. Apply the `pull.py` hunk of section 8, item 3, and remove the `xfail` marker.
3. Record the grant as used in the PROD-20 owner's file, with the two quoted statements of section 5.
4. Tell the lanes that call a model: the wrapper is the only way (`test_only_the_spend_wrapper_calls_an_adapter_in_the_comparison_context`);
   put `ai_job_id` in the payload of the items of one AI job; build `Consent` from the stored consent and `CallRoute` from the bound connection; return
   `error.as_outcome()` from the handler.
5. The stack of this lane is `auditmanager-cmp-spend-01`; it was brought down with `make down`.

## 10. Proof that the forbidden hotspots were not touched

`git diff --name-only 34dcf9a1..HEAD` lists only: this lane's `src/auditmanager/comparison/spend/**` and its two test directories, the four wiring and row
files (`comparison/public.py`, `executors/runner_repository.py`, `dashboard/repository.py`, `scripts/recovery/grant_classification.py`), the one granted
file `src/auditmanager/jobs/repository.py`, and the two documents. Nothing under `contracts/`, `db/migrations/`, `src/auditmanager/comparison/work/`,
`src/auditmanager/execution/`, `src/auditmanager/bootstrap/`, `src/auditmanager/api/`, `src/auditmanager/analysis/`, `src/auditmanager/executors/` other than
`runner_repository.py`, `infra/`, `web/`, `pyproject.toml`, `uv.lock` or `web/FRONTEND_LOCK.json`; within `src/auditmanager/jobs/` only the one constant.
