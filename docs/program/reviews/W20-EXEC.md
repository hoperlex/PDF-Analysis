# W20-EXEC — the run leaves the request thread, and `running` becomes a reading

**Session:** `W20-EXEC`  **Branch:** `agent/w20-exec`  **Worktree:** `/root/w20exec`
**Row:** `D-20` — the contract declares a `running` state no client can observe.

## HEAD on arrival

```
8a88fce merge(W19-RUN): rendering a field is not rendering a fact
```

`origin/dev` was at `8a88fce` as the brief required. Nothing was stale and no stop was
needed at STEP 0.

## Base gate, measured before the first edit

Instance `gate-w20a`, PostgreSQL 55850, MinIO 59450/59451, database `audit_w20a`, bucket
`auditmanager-gate-w20a`. `make gate`, exit code read from `$?` after a redirect:

```
1785 passed, 5 skipped, 1 warning, 168 subtests passed in 220.32s   (battery)
35 passed in 29.68s                                                 (foundation)
Test Files  47 passed (47)   Tests  681 passed (681)                (frontend)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_BASE_EXIT=0
```

Identical, figure for figure, to the numbers the brief carries.

## The brief, checked against the tree

Nine of ten premises held. One is wrong in a way that matters, and correcting it is what
makes the shape of the repair what it is.

| premise | the tree |
|---|---|
| `bootstrap/adapters.py:248` — `start_run` imports `execute_run` and runs it inline | **true**, at `src/auditmanager/bootstrap/adapters.py:247-268`, inside one `self._write(...)` |
| the run is already `published` when `startRun` answers | **true**, measured over a socket below: `202` in **354 ms** carrying `"state": "published"` |
| polling makes one request and stops | **true**, and measured: the poller's distinct readings were `['published']` |
| `PA-01` criterion 4's UI clause is unreachable, not unimplemented | **true** |
| nginx `proxy_read_timeout 300s` at `infra/deploy/proxy/nginx.conf:38` | **true** — and see §7 |
| **`queued` and `running` are declared and unreachable** | **false as stated.** `runs/executor.py` has written *both* since `B5`: `advance(created→queued)` then `advance(queued→running)`. They were unreachable **to a client**, not to the code, because the whole run lived in one uncommitted transaction and no second connection could read an intermediate row |
| making them reachable is an implementation change, not a reseal | **true**, and confirmed rather than relied on: `contracts/domain/v1/state-machines.json` declares `created → queued → running → validating → {published, partial, failed}` and `RunState` declares all eight values. Nothing under `contracts/` was touched |
| `W19-RUN` built the poller and it is correctly conditioned | **true**, and stronger than the brief says — see §6 |
| `make mutation-copy` copies `src/`, `tests/`, `pyproject.toml` | **true**, and it also symlinks `contracts/`, `docs/`, `fixtures/`, `db/`, `tools/` — which means three suites in `tests/integration/composition` that read `Makefile`, `infra/` or `scripts/` cannot run in the copy at all. Noise, not mutation results; excluded by path and named here so nobody reads them as evidence |
| `pytest-randomly` is not installed | **true**; `addopts` is `--import-mode=importlib` and nothing else |

**Why the correction changes the design.** If the states were merely unwritten, the repair
would be to write them. They *were* written. The defect is a **transaction boundary**: one
`_write(...)` around creation *and* execution, so every intermediate state was written and
overwritten before anything committed. So the repair is about where the commits are, and
that is also what decides what a crash leaves behind — §5.

## 1. The shape, and the argument from the code and the profile

**A bounded pool of worker threads inside the serving process**, owned by the composition
root: `src/auditmanager/runs/carrier.py`.

`PROTOTYPE_PROFILE.md` section 7 defers, verbatim:

> - remote/distributed workers;

and section 2 says, verbatim:

> One local execution process is sufficient. Run and stage state are persisted before
> execution, but distributed-worker semantics are deferred.

Both sentences are about **distribution**. Neither says the work must happen on the thread
that answered the request — and the second says something close to the opposite: state is
persisted *before* execution, which is a claim with no content unless something other than
the accepting call can read it in between. That is the sentence `D-20` was violating.

So the carrier creates no `Job`, no `Attempt`, no lease, no heartbeat, no fencing token
and no outbox — the list `auditmanager/runs/__init__.py` gives as the things PC-01 has no
such thing as, and `runs/scope.py` records as unevaluated. Nothing durable is queued
outside the process; nothing can be handed to a second machine. `RUN_CONCURRENCY` is **1**,
so runs still execute strictly one at a time exactly as they did inline. What one worker
buys that zero workers did not is that a second run submitted while the first is executing
now **waits in `queued` and says so** — which is what that state has always meant and what
no client could ever see.

`InlineCarrier` is kept as a named object: it is the pre-`D-20` behaviour, and a mutation
that restores it is one constructor argument. `RunAdapter` takes the carrier as a
**required** argument with no default, so no application can be assembled that quietly
executes on the request thread.

### Where each edge is taken, and why there

| edge | taken by | why there |
|---|---|---|
| `created → queued` | `RunAdapter.start_run`, in the transaction that accepts the run | the contract's guard on this edge is "the input manifest and the AnalysisProfile, PromptBundle and NormsSnapshot references resolve to immutable versioned records"; `start_audit_run` has just resolved exactly those, three statements earlier, in this transaction. Evaluating a guard in one place and taking its edge in another is how guards rot |
| `queued → running` | `execute_run`, unchanged, as its sole owner | one owner. The first draft of this change had the carrier take it *and* `execute_run` take it again; the second compare-and-set matched no row and every run died at `state_transition_not_allowed`. The characterization capture caught it, which is what that corpus is for |
| everything after | `execute_run`, unchanged | — |

### The one new line in the executor's state sequence

```python
run_repo.advance(session, run_id=run_id, from_state="queued", to_state="running")
checkpoint()
```

`checkpoint` defaults to doing nothing. The carrier passes `session.commit`. That is the
entire seam: **fifty-two existing `execute_run(` call sites across twenty-five test modules
are untouched and keep the all-or-nothing unit of work they have always had**, and the one
caller that wants `running` to be visible says so.

`start_run` reads the response view **before** it submits. That ordering is the answer, not
an implementation detail: once the carrier has the job, the run's state is a race between
this process's worker and this process's reader, and a fast recorded run can be `running`
or already `published` by the time a view is built. Reading first makes the `202` report
what was *accepted* — `queued`, every time, for every document and every provider — instead
of reporting how quick the machine happened to be. A body that varies with scheduling is a
body no characterization record can pin and no client can reason about.

A replay submits nothing: `started.replayed` is the command ledger's own answer to "did
this request create anything", and re-submitting would hand a worker a run that is not
`queued`.

## 2. Files I own, and the reason each one is the execution seam

The brief gave me `src/auditmanager/runs/**`, `src/auditmanager/bootstrap/adapters.py`,
"whatever else you **prove** the execution seam lives in", their tests, the affected
characterization records and this review.

| file | why it is the execution seam |
|---|---|
| `src/auditmanager/runs/carrier.py` | **new.** The carrier, the job, and the crash terminal |
| `src/auditmanager/runs/executor.py` | holds `advance(queued→running)`. The commit that makes it visible has to be *at* that line, so the hook is there |
| `src/auditmanager/runs/reconciliation.py` | what a stranded run becomes. `queued` is now a state a death can strand, which it was not before |
| `src/auditmanager/runs/repository.py` | `stale_running` could only select one state; the reconciler now needs two |
| `src/auditmanager/runs/__init__.py` | the package's public surface; a carrier nothing can import is not wired |
| `src/auditmanager/bootstrap/adapters.py` | the inline call itself, and the `created → queued` edge |
| `src/auditmanager/bootstrap/composition.py` | **outside the brief's list.** The composition root is the only place that builds an `Application`, and `RunAdapter`'s carrier has no default, so this is where the process's one carrier is constructed. `Application` gains a `carrier` field for the same reason it carries `provider_config`: "this application does not execute on the request thread" is then a fact a test reads off the built object |
| `src/auditmanager/api/app.py` | **outside the brief's list, and the one that took the most proving.** Startup reconciliation must run when a process *serves*, not when an `Application` is *constructed* — suites build several per session, some while another's run is in flight, and `STARTUP_THRESHOLD` is `0 seconds`. The only thing in this repository that distinguishes "serving" from "constructed" is the ASGI lifespan, and `create_asgi_app` is where one can be attached. It also publishes `app.state.run_carrier`, which is how anything holding the served app waits for a run without sleeping |

Nothing under `contracts/`, `web/`, `infra/`, `db/`, `scripts/` or `Makefile` was touched.
`W20-CODE`'s lane in `contracts/domain/v1/**` was not entered.

Two ownership lines in the brief were narrower than the code, which makes four this week by
the coordinator's own count: `bootstrap/composition.py` and `api/app.py`. Both are named
above with the reason rather than assumed.

## 3. The `202` body and the poller's readings, over a real socket

`uvicorn` on this lane — `infra/deploy/serve.py`, API `127.0.0.1:18620`, health
`127.0.0.1:18621`, `AUDITMANAGER_PROVIDER_MODE=recorded`, the lane's own PostgreSQL and
MinIO. Driven with `curl`. **No image was built and no alpha stack was touched.**

`startRun` answered in **22 ms**:

```json
{"run_id": "run_01M2TEQ7Z0JHGEMQQ8TF47277Z", "project_uid": "prj_01M2TEQ7JSFV0KRP5XHBPS4Y3A",
 "version_uid": "ver_01M2TEQ7YDJVBN7CTV6FCE7NTD", "state": "queued", "provider_mode": "recorded",
 "stages": [], "created_at": "2026-09-18T14:28:55.902132Z",
 "analysis_profile_id": "ap_01M25P3TH08VVTTGJRXYBZZ7RP",
 "prompt_bundle_id": "pb_01M25P3TH0PDQYVKTRQFEM0CYS", "degradation_set": [],
 "published_finding_count": 0, "diagnostic_observation_count": 0}
```

A poller issuing `GET /runs/{run_id}` back to back got, elapsed from the `202`:

```
       0 ms  queued      (the 202 body itself)
      81 ms  running
      99 ms  running
     117 ms  running
     203 ms  running
     222 ms  running
     239 ms  running
     256 ms  running
     272 ms  running
     292 ms  running
     308 ms  running
     321 ms  published
```

Distinct readings: **`queued` → `running` → `published`**. The finished run reports four
stages, three published findings and `cost_micros: 34400`.

### The same drive against the defect, so the two are comparable

The mutation copy with execution put back on the request thread, served on
`127.0.0.1:18630` from the same repository by the same `serve.py`:

```
startRun 202 in 354 ms
{"run_id": "...", "state": "published", "stages": [ ...four... ], "terminal_at": "..."}
distinct states seen: ['published']
```

**354 ms against 22 ms, and one reading against three.** The 354 ms is the whole analysis
held on the request thread with a *recorded* provider that answers from disk. With a live
provider that term is the model call.

## 4. `web/` needed nothing, and it is worth saying what "nothing" means

No file under `web/` was touched, and the frontend gate is unchanged at 681 tests in 47
files. The poller was not merely "correctly conditioned" — it was built for this exact
sequence and could not fire:

* `web/src/shared/api/polling.ts:68-86` loops until `isTerminalRunState(status.state)`;
* `web/src/shared/api/run-state.ts:18` declares `NON_TERMINAL_RUN_STATES = ['created',
  'queued', 'running', 'validating']`, with a compile-time proof that the split is a
  partition of the contract enum;
* `web/src/features/start-run/model/use-start-run.ts` already says *"The 202 body is a full
  `RunStatus`, so it seeds `queryKeys.runs.detail(run_id)`: the run screen opens on the
  run's real first state"* — and until today that first state was a terminal;
* `web/tests/unit/run/polling.test.ts:108` already scripts
  `['queued', 'running', 'validating', 'published']` against a fake transport, and
  `web/tests/unit/screens/run-progress.test.ts:149` already renders a `queued` run.

So the UI clause of `PA-01` criterion 4 was tested against a sequence the server could not
produce. That is the whole of what `unreachable, not unimplemented` meant, and it is why
this row needed no `web/` change.

## 5. What a crash leaves, and why that state

Two different faults, kept apart because they send an operator to two different places.

**An exception on the worker is not a crash.** `run_stage` catches `DomainError` and turns
it into a failed stage; anything else — a store, a driver, a bug — escapes `execute_run`.
While execution was inline that became a `500` envelope and the caller learned about it.
Off the request thread **there is no caller left to raise at**, so the run row is the only
reader. `run_to_terminal` catches it, and in a *fresh* transaction (the failed one has been
rolled back) terminates the run `failed` with `terminal_reason: analysis_failed` and
`interrupted_reason: executor_raised_before_terminal`. It then re-raises — not for the pool,
which drops the exception into a future nothing reads, but because `InlineCarrier` runs on
the request thread and a caller that asked for inline execution should still see a fault.

**A process death has no `except` clause.** That is the reconciler's case, and `OD-10`
already decided its vocabulary: the run moves to the **declared** terminal `failed`
carrying `interrupted_reason: executor_process_ended_before_terminal`. No `interrupted`
state is invented, because the `audit_run` machine declares four terminals and that is not
one of them; the interruption is a *column*, not a *contract*. `running → failed` and
`queued → failed` are both declared edges, so this is reconciliation **inside** the contract
rather than repair around it.

Three decisions inside that:

1. **The commit boundary is before the stages, not inside them.** `checkpoint()` is called
   once, immediately after `running` is written and before any stage does anything. So a
   process death leaves a reader exactly two pictures: a run in `running` with **no stage
   rows at all**, or a terminal run with all of them. A finer boundary would add a third —
   stage results belonging to a run no terminal ever accounts for — and PC-01 defers
   resume, so nothing would ever account for them. `test_a_crashed_run_leaves_no_half_
   written_stage_results` is that claim.
2. **`queued` is now strandable and `created` is not.** A run is put in `queued` by the
   accepting transaction and then handed to the carrier; a death in that window leaves a
   `queued` row that nothing will ever pick up. `created` is reached and left inside the
   accepting transaction and is never committed on its own, so a reconciler that terminated
   `created` runs would be terminating runs mid-creation — and `created → failed` is not a
   declared edge, so the topology refuses it even if `STRANDED_STATES` were wrong. Both
   halves are asserted.
3. **Reconciliation at startup only, and no second mechanism at shutdown.** A graceful
   shutdown *could* mark the in-flight run failed, but that would be a second
   implementation of a rule the reconciler already owns and would cover strictly fewer
   cases — a `SIGKILL` reaches no shutdown hook. One mechanism, at the one moment that
   happens however a process ended. `ThreadCarrier.shutdown` therefore stops accepting and
   does not wait.

`STARTUP_THRESHOLD` is `"0 seconds"`, and the assumption under it is written down in the
module rather than buried: one local execution process (profile §2) means that at the
instant this one starts, before it binds a socket, no run can legitimately be executing.
**Start a second process against the same database and this value terminates the first
one's live run.** That configuration is outside the profile; if it ever comes inside, that
constant is the single place to change, and `1 hour` — still the default of the functions
themselves — is what it changes to.

**What was already there and had nothing to do.** `runs/reconciliation.py` has existed
since `B5` with `INTERRUPTED_REASON`, `stale_running` and `reconcile`, and **nothing in
`src/` ever called it** — one test did. It could not have found anything: the pre-`D-20`
architecture never committed an intermediate state. It was correct code guarding a case the
architecture could not produce. `api/app.py`'s lifespan is the call site it never had.

## 6. The characterization records

`make` recapture (`tests/characterization/w13_baseline/capture.py`) rewrites all 36 records.
**Exactly one moved, and it is record 03.** That, more than any argument, is the measure of
how narrow this change is.

| record | moved | why |
|---|---|---|
| `03-startRun.success` | **yes** | the `202` now reports the accepted run |
| `04-startRun.replay`, `05-…normalised_property` | **no** | a replay reports the run **as it stands**, and the journey waits for the run to finish before it replays. Their bodies are the published shape they have always been, byte for byte |
| `06`, `07` (`getRunStatus`), `34` (`listRuns`), all others | **no** | — |

`03`'s body went from 1274 bytes to 446: `state` is `queued`, `stages` is `[]`, both counts
are `0`, and `terminal_at`, `terminal_reason` and the three cost properties are absent.
Every absent name is one `run_status_body` has always omitted when the producer has nothing
to report — the same rule that already governs an absent cost, which `W19-RUN` turned into
a sentence a user reads. No property was renamed, removed or re-typed; no status or header
moved; `additionalProperties: false` on `RunStatus` is satisfied because every name present
is one the sealed document declares.

**The guard was extended, not loosened.**

* `PERMITTED_EXCEPTIONS` still holds **seven** entries — the count is the assertion, and it
  did not change. Record 03's value went from `("D-19", "D-21")` to
  `("D-19", "D-21", "D-20")`, because a record moved by a third debt has to name a third.
  Three records that moved together twice did **not** move together a third time, which is
  the reason `debt` is a list and the reason that map is written out case by case.
* `EXCEPTION_W20EXEC` in `journey.py` follows the form of `EXCEPTION_W18SEAL` and
  `EXCEPTION_W19API` exactly: `debt`, `ruling`, `status`, `decided_by` (`9f3436f`),
  `decided_by_subject`, `decided_on`, `permitted_change` describing the *whole* of the move
  including the D-19/D-21 fields that are absent from this one record and still present on
  the four records of a finished run, and `everything_else`.
* **No owner ruling, and the block says so in as many words.** `R-5` and `R-10` were both
  needed because a *property* appeared or was filled. Nothing appears here: `queued` is a
  value the frozen `RunState` enum has always declared and `created → queued` an edge the
  frozen `audit_run` machine has always had. No file under `contracts/` was touched.
* `test_the_five_run_status_records_no_longer_pin_one_instant_for_the_whole_run` became
  `test_the_run_status_records_…` over the **four** records that report a finished run, and
  gained `assert body["stages"]` so a record that lost its stages cannot pass it silently.
  Record 03 is not dropped from the file — it gets
  `test_the_start_run_record_pins_an_accepted_run_and_not_a_finished_one`, which makes the
  *stronger* claim: a declared non-terminal state, no stages, and none of the five
  properties only a run that has executed can have. Five assertions replaced by seven.
  Putting execution back on the request thread is now a red test rather than a longer body.

## 7. The 300-second margin

**`infra/deploy/proxy/nginx.conf` was not touched.** No timeout changed, so the brief's
condition for entering that file was not met.

**It has stopped being the deadline for a run, and that is the substantive answer.** The
file's own comment reads:

> A model run is slow. The default 60s read timeout would cut `startRun` off mid-call and
> hand the browser a 504 that no catalog code explains.

That was true and is now false. `startRun` no longer waits for the model: 22 ms against
354 ms for a recorded run on a socket, and with a live provider the difference is the whole
model call. **A 30-page document that takes ten minutes now finishes, and the screen shows
it**, because the browser is polling rather than holding a connection open. The failure the
300 s was buying margin against — a gateway error to a browser with a run still executing
behind it — cannot occur any more, at any document length.

**What 300 s now bounds** is the slowest remaining request, which is `uploadDocument`: up to
26 214 400 bytes through the proxy. Measured on this lane against the running server, three
times, at 4 KB under the cap: **0.85 s, 0.86 s, 0.87 s**, refused `422` at the validator.
That is the body-read and validation term on loopback and not a full accepted upload through
a proxy, so it is a floor rather than a worst case — but it settles the order of magnitude
as seconds.

**I did not lower it**, and the reason is a rule this programme keeps: lowering a timeout
means claiming a bound on something, and nothing in this repository measures an accepted
cap-sized upload end to end through nginx. Trading a measured margin for a guess is the
wrong direction. What is left is a **stale comment in a file I do not own**: it states a
reason that no longer exists. That is a finding for whoever owns `infra/**` (`W14-PKG`), not
a licence for me to edit it.

## 8. Mutations: what reddened, and how sleeping was avoided

**Nothing in this session proves concurrency by sleeping.** The model adapter is gated: a
`threading.Event` it *sets* when the worker reaches it, and a second one it *waits on* until
the test releases it. Between those two points the run is inside `text_analysis` by
construction — which is after `queued → running` and after the carrier's commit — so the
reading a `getRunStatus` gets there cannot be anything but `running`, on any machine, under
any load. Every wait in every suite goes through `ThreadCarrier.drain`, which blocks on the
futures of the work itself. There is no `time.sleep` anywhere in the new tests and no poll
loop that gives up after *n* tries.

`make mutation-copy MUT=/root/w20exec-mut`, baselined green first (68 passed) — a red from a
copy nobody baselined is not evidence. Each mutation was applied alone and reverted from the
pristine tree before the next.

| # | mutation | reddened |
|---|---|---|
| M-1 | execution back on the request thread: `start_run` calls `execute_run` inline and submits nothing | `test_the_response_reproduces_the_record[03-startRun.success]`; `test_the_comparison_reddens_on_a_planted_difference`; **7 of the 8** cases in `test_the_run_leaves_the_request_thread.py`; `TestTheAcceptedRunIsNotTheFinishedRun` (both cases) |
| M-2 | the carrier stops passing `checkpoint=session.commit`, so `running` is written and never committed | `test_a_poller_reads_running_while_the_provider_is_still_being_waited_on` — **and nothing else**. 76 other tests stayed green |
| M-3 | `_record_crash` is not called, so a worker exception writes no terminal | `test_an_exception_on_the_worker_terminates_the_run_rather_than_leaving_it_running` — alone, out of 160 |
| M-4 | the lifespan reconciles nothing | `test_the_lifespan_is_where_that_reconciliation_happens` — alone, out of 91 |
| M-5 | `STRANDED_STATES` forgets `queued` | `test_a_process_death_is_resolved_by_the_next_process_start[queued]` and `test_the_run_row_a_killed_process_leaves_is_the_only_one_it_can_leave` |
| M-6 | record 03's `exception.debt` drops `D-20` | `test_exactly_the_named_records_are_marked_as_permitted_exceptions` — the guard on the guard |

The eighth case in `test_the_run_leaves_the_request_thread.py` that survived M-1 is
`test_the_run_row_a_killed_process_leaves_is_the_only_one_it_can_leave`, which reads the
declared topology and never touches the adapter. It is supposed to survive, and M-5 is where
it reddens.

Three modules in `tests/integration/composition` — `test_mutation_copy_serves_a_tests_only_
stream.py`, `test_api_token_channel.py`, `test_reset_script_refusals.py` — cannot run inside
a mutation copy at all, because they read `Makefile`, `infra/` and `scripts/`, which the copy
does not contain. Excluded by path. They are copy artefacts and are **not** mutation results.

## 9. Where the new tests live, and why not beside the executor

`tests/integration/composition/test_the_run_leaves_the_request_thread.py`, eight cases over
the shipped `RunAdapter` behind the shipped `build_router`, against real PostgreSQL and real
object storage.

It is not in `tests/integration/runs/` because that suite's autouse `_no_network` fixture
refuses every new socket once a test body starts, and this module opens two the run suite
never does: a `TestClient` socketpair for its portal, and the carrier worker thread's own
connection to the object store. `_no_network` exists so a recorded suite cannot spend, and
that property is held here by two stronger things, both stated in the module: the adapter is
constructed in the file and is a `RecordedAdapter` (or this file's gate in front of one),
and the root `conftest` has already removed every provider-selecting variable and every
credential from the process for the whole session. There is nothing in the process to spend
with. The run harness's `seed_version` is loaded by explicit path, the way
`tests/integration/exports` already loads it.

## 10. Gate

```
GATE OK: battery, foundation, frontend and whitespace all pass
```

*(figures and exit code filled in below from the run on the final commit)*

## 11. Anything false in the brief

Restated from the table at the top, because it is the part a coordinator reads:

1. **"`queued` and `running` are declared and unreachable."** They are written by
   `runs/executor.py` and have been since `B5`. What was unreachable was a client's *view*
   of them, because creation and execution shared one uncommitted transaction. The
   distinction is the whole design: this is a commit-boundary change, not a
   write-the-missing-states change.
2. **The ownership line was narrower than the code, twice.** `bootstrap/composition.py`
   builds the carrier (nothing else builds an `Application`) and `api/app.py` is the only
   place that can tell "serving" from "constructed", which is where startup reconciliation
   has to go. Both are tabulated in §2 with the proof.
3. **`make mutation-copy` symlinks more than the brief's list suggests**, and three
   composition suites therefore cannot run in a copy. Not a defect in the tool — its own
   output says so — but a session that did not read that output would report three false
   reds.

Everything else in the brief held, including the base gate figures to the test.

## 12. Cost

One `uvicorn` on ports 18620/18621 and one on 18630/18631, both on 127.0.0.1, both stopped
by PID. **No process was killed by name**, no image was built or rebuilt, and the three
alpha stacks on 31480, 31490 and 31500 were not touched. Disk at the start: 7.3 GB free.
