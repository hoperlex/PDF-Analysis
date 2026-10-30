# CMP-AI-JOBS-01 — the shared core of consented AI jobs: estimate, keyed start with consent, state edges, spend pause, reads, recorded mode

Written 2026-10-29 by the Sonnet lane `CMP-AI-JOBS-01` (branch `agent/cmp-ai-jobs-01`, base `901914a5` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-AI-JOBS-01.md`](tasks/CMP-AI-JOBS-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (10, 11, 19, 23; `Q-CMP-7`); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) (`A-6`, `A-8`, `A-12`); the tables and the refusals are the seal's ([`CMP-SEAL-C2.md`](CMP-SEAL-C2.md) §3, §4, §8, §9); the spend wrapper is [`CMP-SPEND-01.md`](CMP-SPEND-01.md); the wave brief is [`dispatch/CMP-WAVE-C2.md`](dispatch/CMP-WAVE-C2.md).

The package writes **no operation, no migration and no contract change**. Nothing is wired: the service is built by the method lanes (and the queue lane for the installation read), which wire their adapters through it.

## 1. Base facts, printed before any edit

Contract `1.11.0`, **176 paths / 198 operations / 517 schemas**, `VERSION` `0.9.0`, head `0040_comparison_ai_reports`, base `901914a5520a2d90b22b0c5c3fcdae1fa3f6e438` (task file `P-01`). Equal to the brief's premise, so the lane went on. Nothing in `contracts/**` or `db/migrations/**` was changed; no column was missing.

### 1.1 What was built

| path | what it holds |
| --- | --- |
| `src/auditmanager/comparison/ai_jobs/model.py` | the vocabulary: methods, states, pause reasons, the registered refusals, `AiScope` (the table's scope CHECK), `AiCallGroup` / `AiCounts` (what a method supplies, with the `A-12` limits on images), `AiRoute`, `AiEstimate` and `digest_of`, `AiMethod` (the protocol), `AiWorkItemSpec`, `AiJobRecord`, `AiJobView` and the other reads |
| `.../estimate.py` | the estimate protocol: `read_route` (the routed connection of the work kind and its pinned model, through `executors.public`), `build_estimate` (pure: price, ceilings, digest) |
| `.../repository.py` | `AiJobRepository`, the only writer of `comparison_ai_job`; the one statement that writes a job's work item; the reads of a job's progress and spend through `comparison_work.comparison_ai_job_id` |
| `.../service.py` | `ComparisonAiJobService`: `estimate`, `start`, `pause`, `resume`, `cancel`, `dequeue`, `finish`, `retry`; the worker's side (`mark_running`, `complete_if_drained`, `fail`, `pause_for_spend`, `pause_system`, `consent_for_calls`); the reads (`view`, `latest`, `waiting`) |
| `.../recorded.py` | `RecordedAnswers`, the in-memory recorded adapter keyed by request digest |
| `comparison/public.py` | 27 names (an import block after the overview service and the end of `__all__`); `SEALED_NOT_YET_WRITTEN` in `scripts/recovery/grant_classification.py` loses `comparison_ai_job` |
| `tests/unit/comparison/ai_jobs/**` (82), `tests/integration/comparison/ai_jobs/**` (99) | the tests of section 4, and `ai_jobs_support.py`, the recorded-mode helpers every lane loads by path |

## 2. The API the four method lanes follow

Everything below is exported from `auditmanager.comparison.public` (the names are `Ai`-prefixed there so they cannot collide); the package is `src/auditmanager/comparison/ai_jobs/` (`model.py` vocabulary, `estimate.py` the protocol, `repository.py` the only writer of `comparison_ai_job`, `service.py` the commands, `recorded.py` recorded mode). **A lane writes no row of `comparison_ai_job` and no `comparison_work` row of its AI items: it supplies an `AiMethod` and calls `ComparisonAiJobService`.** (`test_only_the_cores_repository_writes_the_job_table_and_no_lane_does` fails the day a lane's source says `INSERT INTO comparison_ai_job`.)

### 2.1 What a method supplies

```python
class AiMethod(Protocol):
    method: str            # "pair_check" | "sheet_changes" | "spec" | "report"  (work kind = "comparison_" + method)
    prompt_version: str    # part of the estimate digest: a new prompt is a new estimate

    def counts(self, session, request: AiEstimateRequest) -> AiCounts: ...
    def work_items(self, session, job: AiJobRecord, mode: AiMode) -> Sequence[AiWorkItemSpec]: ...
```

* `AiEstimateRequest(scope: AiScope, mode: AiMode)`. `AiScope(method, project_uid, document_uid, matrix_id | series_id | transition_id | sheet_pair_id, restart=False)` has the shape of the table's CHECK: `pair_check` a build; `sheet_changes` a series **or** a sheet pair; `spec` a transition; `report` a series; `restart` only for `sheet_changes` («Описать заново»). A malformed scope raises `ValueError` before a statement.
* `AiMode.START` (a new job), `LEFT` (what an existing job still has to do: a resume after `overrun`/`route_changed`, «Досчитать») and `FAILED` (the units that failed: the retry). The method answers the counts and the items **for that mode**.
* `AiCounts(groups, units, reused=0, questions=None, pairs=None, sheets=None, transitions=None, versions=None)` -- `units` is what the job works on, `reused` the units that already have a stored answer under their content key (never sent again, never in `groups`). `groups` is a tuple of `AiCallGroup(calls, prompt_chars, output_tokens, images=0, image_bytes=0, prompt_tokens=None)`: `calls` requests of one shape, every other figure **per call**. `prompt_tokens`, when the method knows it, wins over the conversion of `prompt_chars` (2.5 characters per token, rounded up); an image is priced at 1600 tokens; `output_tokens` is the request's `max_tokens`. **A-12**: a group over `MAX_IMAGES` (8) images or `MAX_TOTAL_IMAGE_BYTES` per call cannot be a request and raises `ValueError` -- an estimate for it can never be consented to.
* `AiWorkItemSpec(unit_key, payload, priority=0, delay_seconds=0, max_attempts=3, kind=None)`. `unit_key` names the unit **within the job** (a question, a sheet pair) and must be stable: a finish or a retry queues the same unit again with the same key, which is how progress counts a unit once, by its newest item. The core adds the module (`versions`), the dedupe key (`<job id>:<unit_key>`), `ai_job_id` in the payload (the key the spend ceilings sum; a method that sets it itself is refused) and the column `comparison_work.comparison_ai_job_id`. `kind` defaults to the method's work kind; register the handler for that kind in `HANDLER_FACTORIES`.
* `work_items` is called **after** the job row exists, in the state the job will have, in the caller's transaction; it only reads and returns specs. An empty answer is `comparison_ai_nothing_to_do` and the whole command rolls back.

### 2.2 Building the service

```python
service = ComparisonAiJobService(
    session_factory, methods=[my_method],            # a lane passes its own; the composition root may pass all four
    work=ComparisonWorkRepository(),                 # optional
    comparison_modules=parsed_module_set,            # AUDITMANAGER_COMPARISON_MODULES, parsed ("none" | "versions" | "versions,stages")
    provider_mode="live" | "recorded",               # the process's (proxy counts as live)
    route_reader=read_ai_route,                      # optional: tests inject another
)
```

Every command takes an `AiJobCommand(command_type, idempotency_key, user_uid, actor_roles)`; `command_type` is the snake case of the lane's operationId (`start_comparison_ai_pair_check`, `pause_comparison_ai_sheet_changes`, ...; already in `product_purge.py`'s command types).

### 2.3 Operations to core calls

| operation (lane) | core call | notes |
| --- | --- | --- |
| `estimate...` (GET) | `service.estimate(scope, mode=AiMode.START)` -> `AiEstimate`; `.as_dict()` is the contract's `ComparisonAiEstimate` | no write, no model call; `blocked_by` is `job`/`day`; `estimate_micros` 0 for `not_metered` |
| `get...` (GET) | `service.latest(scope)` -> `AiJobView | None`, or `service.view(job_id, method=...)` | `.as_dict()` is `ComparisonAiJob` (progress, spend from the journal, estimate, queue place); a job of another method is `404` |
| `start...` | `service.start(scope=, consent=AiConsentInput(estimate_digest, confirmed), command=)` | one transaction; replays the job on the same key |
| `pause...` | `service.pause(job_id=, method=, command=)` | `queued|running` -> `paused(user)` |
| `resume...` | `service.resume(job_id=, method=, command=, consent=None)` | `paused` -> `queued`; consent required after `overrun`/`route_changed`, ignored after the others |
| `cancel...` | `service.cancel(job_id=, method=, command=)` | `queued|running|paused` -> `cancelled` |
| `finish` («Досчитать») | `service.finish(...)` | `paused|cancelled|failed|completed` -> `queued` under the held consent |
| `dequeue` («Убрать из очереди») | `service.dequeue(...)` | `queued` and never claimed -> `cancelled` |
| `retry` («Повторить листы с ошибкой») | `service.retry(job_id=, method=, command=, consent=)` | `completed|failed|cancelled` -> `queued`, a new consent for `AiMode.FAILED` |
| `getComparisonAiQueue` (QUEUE lane) | `service.waiting(limit=200)` -> `AiWaitingJobs`; `.as_dict()` is `ComparisonAiQueue` | running first, then queued in start order (with `queue_position`), then paused |

### 2.4 Transaction rules

* A **command** opens one unit of work (`session_scope`) of its own and is keyed: it claims the idempotency key first (a repeat with the same payload replays the recorded job, another payload is `idempotency_key_reuse`). The order of refusals is: module flag (`503 comparison_modules`, the first statement, before any read or write), role (`role:expert`), consent confirmed (`422 comparison_consent_required`), job found and of the method (`404`), the key, then the state/active/stale/nothing/ceiling checks. Every refusal raises inside the unit of work, so **a refused command writes nothing** -- not the job, not an item, not the key.
* The service **never calls a model** and never opens a transaction for one. The lane's adapter keeps calling `_require_versions_module()` first, as the seal asks; the service checks again, in the transaction.
* A **worker-side** function takes the caller's `Session` and never commits.
* Locks: items first, then the job row (a handler holds an item's row and then touches the job).

### 2.5 The worker's side (the handler of a method's items)

```python
with sessions() as s:                                   # 1. the item starts the job; a non-running job sends nothing
    if service.mark_running(s, job_id) != "running": return Yielded(...)   # paused/cancelled while the item waited
    consent = service.consent_for_calls(s, job_id)      # 2. the Consent the spend wrapper checks (baseline included)
route = CallRoute(adapter=adapter, model_identity=job.pinned_model, connection_revision_id=job.connection_revision_id, expected_model=gateway, pin=pin)
try:
    result = caller.call(item, route, request, estimate=CallEstimate(...), consent=consent)   # comparison.spend: the only door to a model
except CallRefused as refused:
    if refused.pauses_job: service.pause_for_spend(s, job_id, refused.reason)   # overrun / ceilings / consent no longer holds
    return refused.as_outcome()
...
if result.pause: service.pause_for_spend(s, job_id, result.pause.reason)       # the x1.2 pause: the reply is kept, the job stops
service.complete_if_drained(s, job_id)                  # running -> completed once no item is live
service.fail(s, job_id, "reason_code")                  # a reason that ends the whole job; its live items are cancelled
```

`pause_for_spend` maps the spend wrapper's reasons (`PAUSE_OF_SPEND_REASON`): `overrun` and `job_ceiling` -> `overrun`; `day_ceiling` -> `quota`; `consent_stale` and `consent_required` -> `route_changed`; every other reason (`connection_busy`, `model_not_selected`, ...) pauses nothing and answers `False`. The job's waiting items pause with it; the item in flight finishes. `pause_system(s, job_id, reason)` is the same for `auth` and `module_off`.

`consent_for_calls`: the wrapper judges the 1.2x rule on the job's **whole** spend; after a new consent (the estimate is for what was left) it is the stored estimate **plus what the job had actually spent before that consent**, so a resumed job does not overrun on its first call.

### 2.6 Reads and refusals

Reads: `service.view_in(session, job_id)` / `view(job_id)` -> `AiJobView(record, progress, spend, queue_position)`; `progress` is `total/done/failed/unknown` over the job's units, each counted once by its newest work item; `spend` is `spent_micros`, `reserved_micros`, `calls`, `unknown_calls`, tokens, summed from `comparison_model_call` through `comparison_work.comparison_ai_job_id` (never stored on the job).

| refusal | code | when |
| --- | --- | --- |
| `comparison_modules` | `503 dependency_unavailable` | the versions module is off |
| `executor_route_missing` | `503 dependency_unavailable` | no route / no revision / unpinned model for the work kind (the standby is not priced) |
| `comparison_consent_required` | `422 validation_failed` (field `consent`) | consent missing or `confirmed` false |
| `comparison_estimate_stale` | `409 conflict` | the consented digest is not the estimate now computed |
| `comparison_ai_nothing_to_do` | `409 conflict` | no call to send, or the method supplies no item |
| `comparison_ceiling_job` / `comparison_ceiling_day` | `409 conflict` | job spent + estimate > USD 10 / day committed + estimate > USD 50 (both `>`; reaching one is allowed) |
| `comparison_ai_job_active` | `409 conflict` | a live job holds the scope (look-before-insert, and the DB's unique index when two race) |
| `comparison_ai_job_state` | `409 conflict` | the command may not be taken from the job's state |
| `404` | `not_found` | no such job, or a job of another method |

### 2.7 Recorded mode for the lanes' tests

* `RecordedAnswers` (in `comparison.public`): an in-memory recorded adapter; `answers.record(request_or_digest, output_text, ...)` files an answer under `request.request_sha256`; a question with no answer raises `analysis_input_invalid` / `recording_missing` and is **never** a call; `provider_mode` is a read-only class constant (`recorded`), so the spend wrapper journals the reply `unmetered`, needs no consent and spends nothing.
* `tests/integration/comparison/ai_jobs/ai_jobs_support.py` (load it by path, as the spend suite's helpers are loaded): `new_world(connection)` (project, document set, build, series, transition, pair), `recorded_route(connection, work_kind, billing=...)` (a connection with a revision, routed in «Назначения»), `FakeMethod`, `ScriptedLiveAdapter` (the model seam of a money test, calls nothing), `insert_call`, `default_groups`/`counts_for`, `conflict_reason`.
* `tests/integration/comparison/ai_jobs/conftest.py` shows the isolation used: one connection, an outer transaction rolled back, a session factory joined with `create_savepoint` -- the service commits as in production and nothing stays in the lane database.

## 3. Decisions this lane made (each is one place to change)

1. **The estimate is the primary route's.** `read_route` takes the current revision of the **primary** connection of the work kind (`resolve_route`) and the pin it names (`pinned_models`). The standby is not priced and the probe result is not read (neither is public to this context); a job whose calls end up on the standby meets a different revision in the spend wrapper's consent check and pauses `route_changed`. No route, no revision or an unpinned model is `dependency_unavailable` / `executor_route_missing`. A recorded process needs a route too (the estimate and the consent bind a connection and a model in both modes).
2. **Money.** `estimate_micros` is the pinned rates over the summed tokens, rounded up (the wrapper prices a call the same way); `not_metered` is 0 with no ceiling. The job ceiling is USD 10 against **what the job has already spent or reserved plus the estimate** (a resume or a retry counts the spend so far); the day ceiling is USD 50 against what the installation has committed today plus the estimate; both refuse by `>` (reaching a ceiling exactly is allowed, as in `comparison.spend`). The day is read without a lock at the start (the wrapper decides every call under its lock). The order of the digest check, nothing-to-do and the ceilings is: stale, nothing, job, day.
3. **Token conversion `[own design]`.** A thousand characters are 400 tokens (2.5 characters per token, rounded up); an image is 1600 tokens; a method that knows its prompt's tokens passes `prompt_tokens` and the conversion is not used. Both constants are in `model.py`; a lane that measures better changes them in one place (the digest moves with the estimate).
4. **The digest** covers the method, the scope (the `restart` flag included), the mode, the route (connection, revision, pinned model, billing, provider mode), the prompt version, the two hard ceilings, every figure and the price. It does **not** cover `day_remaining_micros` and `blocked_by` (what the installation spent today would make every consent stale).
5. **Pause reasons.** The contract has six. The spend wrapper's `overrun` and `job_ceiling` are `overrun`; `day_ceiling` is `quota` (a resume asks for no new consent; the wrapper checks the day again before the next call); `consent_stale` and `consent_required` are `route_changed`; `connection_busy`, `model_not_selected` and the other refusals are not pauses. A test scans `comparison/spend/*.py` for every `CallRefused(..., pauses_job=True)` and `SpendPause(...)` and fails if one has no pause reason.
6. **The wrapper's consent after a new consent.** `consent_for_calls` adds what the job had actually spent before the consent to the stored estimate (the estimate of a resume is for what was left; the wrapper judges the 1.2 x rule on the whole job).
7. **`finish` and `dequeue`.** «Досчитать» is allowed from `paused`, `cancelled`, `failed` and `completed` and uses the held consent; a job paused for `overrun` or `route_changed` is refused with `comparison_ai_job_state` (it needs a resume with a new consent); a finish of a paused job also takes its paused items up. «Убрать из очереди» is allowed from `queued` while no item of the job was ever claimed (`attempt_count`); a resumed job that had started cannot be dequeued.
8. **Progress counts units once.** A finish or a retry queues a new work item for the same unit (a terminal item never comes back); the dedupe key is `<job id>:<unit key>`, and `progress` takes the newest item of each key, so the old failed one does not count again. A unit that is `cancelled` is in `total` and in neither `done` nor `failed`.
9. **One live job per scope** is looked up first (a clear `comparison_ai_job_active` before the digest is judged) and held by the database's unique index when two commands race; both paths answer the same reason. A report has no live-scope index (a series has several reports), so the report lane keeps one live job per report.
10. **A job's work item is written by the core.** `comparison_work.comparison_ai_job_id` is frozen **at creation** (a later UPDATE, NULL to a value, is refused by the table's trigger), and `ComparisonWorkRepository.enqueue` has no such argument, so `AiJobRepository.insert_item` is that method's statement with the column added (the same dedupe rule). See FIX item 1.

## 4. Safety proofs (mutation)

The tests carry the guards; each mutation below was applied to the file named, the named tests run **red**, the file restored with `git checkout`, the same tests run **green**, `git status --porcelain` empty (driver `mutate.py` in the lane's scratch). The test set was the two directories of this lane (180 tests at the time of M1 to M4, 181 after the state-edge oracle of M5). Counts are pytest's.

| # | commitment | mutation | red | restored |
| --- | --- | --- | --- | --- |
| M1 | **the module gate** refuses every command before anything is read or written | `_require_versions_module` never raises (`if False:`) | **7 failed** (the start and estimate test, six commands) | 180 passed |
| M2 | **a stale digest** is refused | the digest comparison deleted from `_require_consentable` | **5 failed** (start, new revision, resume x2, retry) | 180 passed |
| M3a | **the job ceiling** is refused | the `blocked_by == "job"` refusal deleted | **2 failed** | 180 passed |
| M3b | **the day ceiling** is refused | the `blocked_by == "day"` refusal deleted | **1 failed** | 180 passed |
| M3c | a job ceiling reached exactly is allowed | `>` becomes `>=` in the job check | **2 failed** | 180 passed |
| M3d | a day ceiling reached exactly is allowed | `>` becomes `>=` in the day check | **2 failed** | 180 passed |
| M3e | what the job has spent counts against its ceiling | the spent figure forced to 0 | **1 failed** | 180 passed |
| M4a | one live job per scope: the look-before-insert | the look deleted from `start` | **survives** (180 passed): the database index and its mapping answer the same reason; the pair below shows each half is needed | 180 passed |
| M4b | one live job per scope (look **and** index mapping) | the look deleted and `_is_live_scope_violation` made `False` | **6 failed** (the raw unique violation reaches the caller) | 180 passed |
| M4c | one live job per scope: the race | `_is_live_scope_violation` made `False` (start and finish races) | **2 failed** | 180 passed |
| M5 | **an illegal state edge** is `comparison_ai_job_state` | the `pause` states widened to all six (the trigger is then the only guard) | **8 failed** | 181 passed |
| M5b | the same for «Убрать из очереди» | the `dequeue` states widened to the live three | **3 failed** | 181 passed |
| M6a | **the overrun pause** is a pause | `overrun` removed from `PAUSE_OF_SPEND_REASON` | **5 failed** | 180 passed |
| M6b | the overrun pause pauses | `pause_for_spend` answers `False` | **9 failed** | 180 passed |
| M6c | a paused job's waiting items pause | `_pause_items` pauses nothing | **9 failed** | 180 passed |
| M6d | the 1.2 x rule is judged on the whole job after a new consent | `consent_for_calls` forgets the baseline | **1 failed** (the resumed job overruns on its first call) | 180 passed |
| M7 | **the work item's job link** | the item is written with `comparison_ai_job_id` NULL | **33 failed** (progress, spend, pause, steering) | 180 passed |
| M8 | `A-12`: a request carries at most 8 images | the image limit deleted | **1 failed** | 180 passed |
| M9a | an unconfirmed consent starts nothing | the `confirmed` check deleted from `start` | **1 failed** | 180 passed |
| M9b | a resume or retry needs a confirmed consent | the check deleted from `_renew_consent` | **3 failed** | 180 passed |
| M10 | a resume after `overrun` / `route_changed` carries a new consent | `CONSENT_PAUSES` emptied | **5 failed** | 180 passed |
| M11 | a job that has started cannot be dequeued | the `attempt_count` check deleted | **2 failed** | 180 passed |
| M12 | «Досчитать» cannot skip the consent a resume needs | the paused-for-overrun refusal deleted from `finish` | **1 failed** | 180 passed |
| M13 | a connection that is not metered has no money | `if route.metered:` made `True` | **3 failed** | 180 passed |
| M14 | a new revision of the connection moves the digest | `revision_id` out of the route's document | **4 failed** | 180 passed |
| M16 | every command is an expert's | `_require_expert` returns | **7 failed** | 180 passed |
| M19 | a recorded reply cannot say it is live | `RecordedAnswers._PROVIDER_MODE` is `LIVE` | **2 failed** | 180 passed |
| M21 | a repeat of a key replays | the replay branch of `start` deleted | **1 failed** | 180 passed |
| M22 | the same key with another consent digest is refused | the digest out of the start's fingerprint | **1 failed** | 180 passed |

M5 first survived in the form «widen `dequeue`» because the matrix of refused edges was built **from the table under test**; it was rebuilt from a literal copy of the contract's table (`ALLOWED` in `test_state_edges.py`, with a test that the two are equal), and M5 and M5b were re-run red.

## 5. Checks (light acceptance; the stack is the lane's own: `auditmanager-cmp-ai-jobs-01`, ports 57940 / 61940 / 61941, head `0040`)

`df -h /` before the stack, before each long run and at the end: 8.6 GiB at the start, 8.3 GiB at the lowest (the stop line is 1.5 GiB). All runs: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-ai-jobs-01/<run> <path>` with `set -a; . ./.env; set +a`, the basetemp removed afterwards.

| what | path | result |
| --- | --- | --- |
| diff hygiene | `git diff --check` | exit 0 |
| this lane, unit | `tests/unit/comparison/ai_jobs` | **82 passed**, 1.1 s, no container |
| this lane, integration | `tests/integration/comparison/ai_jobs` | **99 passed**, 4.1 s |
| the whole comparison integration directory, **one process** | `tests/integration/comparison` | **653 passed**, 1 warning, 406 s |
| the classification | `tests/integration/recovery/test_grant_classification.py`; `grant_classification.py --verify-script infra/deploy/apply-grants.sh` | **35 passed**; exit 0 |
| the whole unit battery, after the last code commit | `tests/unit` | **5044 passed**, 76 skipped (none of this lane's), 1 warning, 309 s |
| the contract battery, after the last code commit | `tests/contract --ignore` of `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (`D-220`) | **1310 passed**, 19283 subtests passed, 160 s (includes the documentation and task-file guards and the import-boundary test) |

Not run, by the brief and `R-135`: `make gate`, the web battery (no web change), the live journey. `AGENTS.md` §8 case 3 names any `conftest.py`: this lane adds `tests/integration/comparison/ai_jobs/conftest.py`, so the final gate covers it.

## 6. Limits, risks, FIX items

**FIX items for the wave's FIX slot or the integrator (none blocks the four lanes):**

1. **`comparison/work/**` has two gaps the core worked around.** `ComparisonWorkRepository.enqueue` cannot set `comparison_ai_job_id`, which is frozen at creation, and `ComparisonWorkRepository.counts` has no job filter. The core has its own `INSERT` of a job's item (`AiJobRepository.insert_item`, the same dedupe rule) and its own progress query (the newest item per dedupe key). A one-parameter change to `enqueue` and a job filter in `counts` would let both delegate; nothing else depends on it. The pin test `test_the_core_writes_no_journal_row_and_no_attempt_and_one_kind_of_work_item_row` documents that `repository.py` is the only file of the core with an `INSERT INTO comparison_work`.
2. **The contract has no pause reason for a ceiling.** The job ceiling mid-job is `overrun` and the day ceiling is `quota` (decision 5). If the owner wants a word of their own («дневной лимит»), that is an additive enum value of `ComparisonAiPauseReason`, a contract change.
3. **The route's usability is not checked** (the probe result and the standby are not public to this context): an unusable primary is found by the first call, as a failed call, not by the estimate.

**Limits.**

* Nothing is wired: no adapter, no composition, no `HANDLER_FACTORIES` entry, no stub register changed. The service is built by the lane (signature in section 2.2); `provider_mode` must be `live` or `recorded` (the composition root maps `proxy` to `live`, as `_provenance_mode` does).
* The lock order (items first, then the job row) is the series' rule and is documented, but it is not exercised by a concurrency test: the tests run on one connection inside a rolled-back transaction. The race of two starts is exercised through the database index (M4c).
* `getComparisonAiQueue`'s «one series at a time» order is the queue lane's runner; `waiting()` returns running first, then queued in start order with `queue_position`, then paused.
* The token constants of decision 3 are `[own design]`; the overrun pause measures the truth.
* A report job has no database-held live scope (decision 9).
* No live model call was made; the money tests use a scripted adapter that says `live` and calls nothing (the wrapper's own rules need the mode), the answer-by-digest tests use `RecordedAnswers`.
* **Commit trailer.** The integrator's message asks for `Co-Authored-By: Claude Sonnet 4.6`; the session runs on Sonnet 5.5 and the attribution line the harness gave it names that build, so the commits carry it. The integrator may rewrite the trailer on merge.

## 7. Instructions for the integrator

1. Merge **first** among the C2 wiring files (brief §3). Hunks in shared files: `comparison/public.py` (one import block after the overview service's import, 27 names at the end of `__all__`), `scripts/recovery/grant_classification.py` (one name out of `SEALED_NOT_YET_WRITTEN`). No `bootstrap/**`, no `api/**`, no contract, no migration.
2. Tell the four lanes: build `ComparisonAiJobService` with your `AiMethod`; call it for every state edge and read; never write `comparison_ai_job` (a test fails the day a source says so); keep `_require_versions_module()` the first statement of a wired adapter method; put the handler's kind in `HANDLER_FACTORIES`; test with `RecordedAnswers` and `ai_jobs_support.py`; the day a lane writes its own table it removes that table from `SEALED_NOT_YET_WRITTEN`.
3. The queue lane calls `service.waiting()` for `getComparisonAiQueue`.
4. The stack of this lane is `auditmanager-cmp-ai-jobs-01`; it was brought down with `make down` and its two volumes were removed by exact name (section 5).

## 8. Proof that the forbidden hotspots were not touched

`git diff --name-only 901914a5..HEAD` lists only: `src/auditmanager/comparison/ai_jobs/**` (new), `src/auditmanager/comparison/public.py`, `scripts/recovery/grant_classification.py`, `tests/unit/comparison/ai_jobs/**`, `tests/integration/comparison/ai_jobs/**`, `docs/program/CMP-AI-JOBS-01.md` and `docs/program/tasks/CMP-AI-JOBS-01.md`. Nothing under `contracts/`, `db/migrations/`, `src/auditmanager/jobs/`, `src/auditmanager/executors/`, `src/auditmanager/comparison/work/`, `src/auditmanager/comparison/spend/`, `src/auditmanager/bootstrap/`, `src/auditmanager/api/`, `infra/`, `web/`, `pyproject.toml`, `uv.lock` or `web/FRONTEND_LOCK.json`; no other `conftest.py` and nothing in `tests/support/`.
