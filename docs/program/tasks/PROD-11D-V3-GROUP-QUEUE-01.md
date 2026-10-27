# Task PROD-11D-V3-GROUP-QUEUE-01 — accepting an AR v3 group queues its six Runs and hands them to the carrier

task_id: PROD-11D-V3-GROUP-QUEUE-01
status: completed in development candidate (see the report)

## Outcome

`RunAdapter.start_ar_v3_group` behaves, for each of the group's six Runs, like the ordinary `RunAdapter.start_run`: in the command transaction, on a start that is not a replay, each new Run goes `created -> queued` and gets its Job (one transaction with the group, so a crash after the 202 leaves claimable rows), the 202 says `queued`, and after the commit, only when the start was not a replay, the adapter hands each Run's work to the carrier through the same `self._job(run_id)` the ordinary start uses. A replayed start queues nothing and submits nothing. The six Runs run serially on the single worker (`R-146j`); no slot is changed.

Found by lane `AR-V3-BETA-ACCEPT-RECORDED-01` (fact 5): before this task the start left six `created` Runs and no Job, the `DurableCarrier` poller never saw them and the group review read `pending` for ever, so even an installed reviewed pack would not have produced a single analysis.

## Depends on

- `AR-V3-BETA-ACCEPT-RECORDED-01` — completed (the module whose fact 5 and state facts flip here, and the finding).
- `PROD-11B-V3-STAGE-ID-MIGRATION-01`, `PROD-11C-RECORDED-COST-01` — completed (the Runs can publish at all).

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched); the 202 body is the same `ArV3BetaGroup` schema, its members now read `queued` instead of `created` (both are declared run states)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged
- base commit: `23d7e8ac36338b13675ae2dd4e9525ce962ca082` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the integrator's reading and lane A3's finding are exactly as dispatched (P-01, P-02); the one open design question, whether the queueing belongs in the command or in the adapter, is decided by the evidence in P-03.

### P-01 — what the group start does today

- captured_at: 2026-10-26
- command: `git rev-parse HEAD; rg -n "def start_ar_v3_group|def start_run|\.advance\(|\.enqueue\(|_carrier\.submit|started\.replayed|No Job or provider" src/auditmanager/bootstrap/adapters.py src/auditmanager/runs/v3_group.py`
- captured_output:
  ```text
  23d7e8ac36338b13675ae2dd4e9525ce962ca082
  src/auditmanager/runs/v3_group.py:5:The caller owns the transaction. No Job or provider call is made here.
  src/auditmanager/runs/v3_group.py:202:def start_ar_v3_group(
  src/auditmanager/bootstrap/adapters.py:884:    def start_ar_v3_group(self, *, version_uid: str, idempotency_key: str) -> models.ArV3BetaGroup:
  src/auditmanager/bootstrap/adapters.py:931:    def start_run(
  src/auditmanager/bootstrap/adapters.py:989:            if not started.replayed:
  src/auditmanager/bootstrap/adapters.py:1007:                RunRepository().advance(
  src/auditmanager/bootstrap/adapters.py:1017:                JobRepository().enqueue(session, run_id=started.run_id)
  src/auditmanager/bootstrap/adapters.py:1036:        if not started.replayed:
  src/auditmanager/bootstrap/adapters.py:1041:            # worker. `started.replayed` is the command ledger's own answer to "did this
  src/auditmanager/bootstrap/adapters.py:1043:            self._carrier.submit(self._job(str(started.run_id)))
  src/auditmanager/bootstrap/adapters.py:1104:        self._carrier.submit(self._job(run_id))
  ```
  and the method before this task (`git show 23d7e8ac:src/auditmanager/bootstrap/adapters.py`, lines 884-897): `started = self._write(lambda session: start_ar_v3_group(session, ...))` followed by `return models.ArV3BetaGroup.model_validate(asdict(started.group))` and nothing else.
- interpretation: the group method has no `advance`, no `enqueue` and no `submit`; `start_run` has all three, the first two inside `if not started.replayed:` in the `work` closure and the third after `_write` returns, under the same `if not started.replayed`. The command `runs/v3_group.py` documents «No Job or provider call is made here». Present as dispatched.

### P-02 — what the serving carrier needs

- captured_at: 2026-10-26
- command: `rg -n "def submit|def _poll|next_queued_run|_active" src/auditmanager/runs/carrier.py; rg -n "j.state = 'queued' AND r.state|ORDER BY j.priority" src/auditmanager/jobs/repository.py; rg -n "created_at +timestamptz" db/migrations/versions/20261002_0014_durable_analysis_effects.py | head -1`
- captured_output:
  ```text
  154:    def submit(self, job: Callable[[], None]) -> None:
  179:    def submit(self, job: Callable[[], None]) -> None:
  212:    def submit(self, job: Callable[[], None]) -> None:
  259:        "_active",
  269:        self._active = False
  277:        self._active = True
  283:    def submit(self, job: Callable[[], None]) -> None:
  284:        if not self._active:
  291:    def _poll(self) -> None:
  304:                        run_id = JobRepository().next_queued_run(session)
  315:        if not self._active:
  90:    "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
  97:    "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1 "
  143:            created_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
  ```
- interpretation: the served `DurableCarrier.submit` only wakes the poller; the poller discovers work with `next_queued_run`, which needs a `queued` Job of a `queued` or `running` Run, oldest first. `RUN_CONCURRENCY` is 1, so the six Runs run one after another. `created_at` is `clock_timestamp()`, so Jobs enqueued in scope order are claimed in scope order. An unstarted `DurableCarrier` (every constructed test application) runs a submitted job on its one-thread pool at once.

### P-03 — where the queue edge belongs (the design decision)

- captured_at: 2026-10-26
- command: `rg -n "\.enqueue\(|to_state=\"queued\"" src; rg -n "\"created\"" tests/integration/db/test_ar_v3_run_group.py; sed -n 976,983p src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  src/auditmanager/runs/commands.py:891:    repository.advance(session, run_id=new_id, from_state="created", to_state="queued")
  src/auditmanager/runs/commands.py:892:    (jobs or JobRepository()).enqueue(session, run_id=new_id)
  src/auditmanager/runs/executor.py:982:            session, run_id=run_id, from_state=INITIAL_STATE, to_state="queued"
  src/auditmanager/bootstrap/adapters.py:1011:                    to_state="queued",
  src/auditmanager/bootstrap/adapters.py:1017:                JobRepository().enqueue(session, run_id=started.run_id)
  src/auditmanager/jobs/repository.py:821:            job_id = self.enqueue(session, run_id=run_id)
  tests/integration/db/test_ar_v3_run_group.py:359:                                      {"run": run}).scalar_one() == "created"
  tests/integration/db/test_ar_v3_run_group.py:391:        assert all(m.state == "created" for m in first.group.members)
  ```
  (the `repository.py:821` hit is the claim's fallback for a direct caller; the executor's `created -> queued` at 982 is for an in-process caller that creates and executes in one go: `run_to_terminal` on a `created` Run still works, which is what `tests/integration/runs/test_v3_saved_text_layer_probe.py` relies on.)
- interpretation: the ordinary **start** puts the edge and the Job in the adapter (`start_run`, with the `D-20` comment); only the re-audit command queues inside the command, and the adapter then calls `submit_existing`. The dispatch says to follow the ordinary start, and two further facts agree. (1) `tests/integration/db/test_ar_v3_run_group.py:391` pins that the **command** returns `created` Runs (and advances them itself at 401), and that file is outside this task's allowed paths: moving the queueing into `runs/v3_group.py` would turn it red. (2) The command's contract is «the caller owns the transaction; no Job or provider call is made here», which keeps the domain command free of the Job table and the carrier; the adapter is the one place that holds both the carrier and the transaction boundary, and the `D-20` reasoning (the edge is taken in the transaction that accepts the Runs, which has just resolved the pack, the profile, the snapshot and the six verified sets) holds there exactly as it does for `start_run`. Decision: the queue edge, the Job and the submission go in `RunAdapter.start_ar_v3_group`; `runs/v3_group.py` is not touched.

### P-04 — the measurement the fix must change

- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/runs/test_v3_recorded_group_over_http.py` on the base tree, then the same on the tree with only the adapter change applied
- captured_output:
  ```text
  base:           55 passed, 1 warning in 7.16s
  adapter fixed:  11 failed, 44 passed, 1 warning in 7.30s
    test_the_start_creates_the_group_of_six_with_the_right_scope_labels
    test_the_group_read_after_the_start_is_the_group_the_start_answered
    test_the_http_start_leaves_the_six_runs_created_and_unqueued_for_the_serving_poller
    test_the_review_read_before_the_runs_finish_says_pending
    test_a_read_while_the_first_run_is_at_the_provider_says_one_running_and_five_pending
    test_a_second_identical_start_is_the_same_group_and_creates_no_run
    test_the_same_key_with_another_version_is_a_conflict_and_creates_nothing
    test_every_check_can_fail[a pending review that shows a review]
    test_every_check_can_fail[a pending review that is not pending]
    test_every_check_can_fail[a replay that made a seventh Run]
    test_every_check_can_fail[a replay that made a second group]
  ```
- interpretation: the module was green at the base because it measured the gap, and red on exactly the facts its docstring named once the gap is closed (7 facts and 4 mutation-check preconditions), none others: the fix changes the state right after the start and nothing else the module asserts. Those 11 are the flips of this task.

## Decisions (taken by the lane; the owner asked for no questions)

- decided by the lane: the queueing lives in `RunAdapter.start_ar_v3_group` (P-03); the domain command and its existing tests are untouched.
- decided by the lane: the 202 answers `queued` for every member. The command returns the group it read before the edge, so the adapter re-reads the group in the same transaction after the six advances (`get_ar_v3_group` on the same session) and returns that: the answer says what was accepted, and cannot race with a worker the way a read after the commit could. `start_run` reads after commit and before submit for the same purpose.
- decided by the lane: member order is scope order (`F1 F2 A1 A2 S1 S2`), the order of the group's members; Jobs are enqueued in that order (`created_at` is `clock_timestamp()`), so the single worker runs the scopes in that order.
- decided by the lane: the carrier is handed one job per member, `self._job(member.run_id)`, as the ordinary start hands one; the served carrier only wakes its poller, an unstarted one runs them serially on its one-thread pool.
- decided by the lane: in the HTTP acceptance module a `HeldCarrier` stays between the `RunAdapter` and the application's own carrier. It is not the old carry step: the module submits nothing. It exists because the application's `DurableCarrier` is deliberately unstarted (the lifespan starts it), and an unstarted one executes a submitted job at once, which would move Run 1 off `queued` while the module is reading «right after the start». The held seam records what the adapter submits and, on `release()`, forwards exactly those jobs, in order, to the application's own carrier, which `drain` then waits on. A worker process and the started poller thread are not used (the lifespan is not entered).
- decided by the lane: the new module does not start the poller thread; it asks the repository query the poller runs (`JobRepository.next_queued_run`) from a second composition on the same database, with `submitted=` carrying the Runs already taken, which is how the carrier's pool holds a Run it has taken.
- decided by the lane: the ordinary-start tests are run against a private migrated database (a script creates one, points `DATABASE_URL` at it and drops it), because they otherwise write into the shared lane database.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/bootstrap/adapters.py`
- `tests/integration/runs/test_v3_recorded_group_over_http.py`
- `tests/integration/runs/test_v3_group_start_queues_the_runs.py`
- `docs/program/tasks/PROD-11D-V3-GROUP-QUEUE-01.md`
- `docs/program/PROD-11D-V3-GROUP-QUEUE-01.md`

## Lane resources

- foundation_instance: the integrator's lane stack (`ar-close-1026`), not stopped, reset or written to by this lane
- postgres_db: one throw-away database per module run (`prod11a_probe_*`, created and dropped by the probe's fixture) and one per ordinary-start run (`prod11d_*`); none left behind
- s3_bucket: the lane bucket (content-addressed objects only)

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, root dependency/lock files, global styles
- `src/auditmanager/runs/v3_group.py` and every `src` file other than `RunAdapter.start_ar_v3_group` in `bootstrap/adapters.py` (the parallel lane `PROD-11-AR-V1-V2-REMOVAL-01` edits other parts of that file)
- `tests/integration/runs/test_v3_saved_text_layer_probe.py` and every other existing test
- documents other than the two deliverables, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals
- No change to the executor, the carrier, the Job repository, slots or priorities (`R-146j`: one worker, serial).
- No change to the domain command `runs/v3_group.py` or the contract.
- No live provider call, no activation (`D-204`, `PROD-12`), no worker process, no browser.

## Deliverables
- the adapter change, the flipped HTTP acceptance module (64 tests), the new module `test_v3_group_start_queues_the_runs.py` (8 tests), this task file and `docs/program/PROD-11D-V3-GROUP-QUEUE-01.md` (premise, mutation tables, before/after of modified tests, commands with counts, integration notes)

## Required tests
- commands: with the lane stack, `tests/integration/runs/test_v3_group_start_queues_the_runs.py`, `tests/integration/runs/test_v3_recorded_group_over_http.py` and `tests/integration/runs/test_v3_saved_text_layer_probe.py`, one pytest, in either order
- expected: `8 passed`, `64 passed`, `18 passed` (`90 passed` together); the ordinary-start suites listed in the report still green on a private database

## Integration contract

The integrator merges with `--no-ff`. The diff in `bootstrap/adapters.py` is local to `RunAdapter.start_ar_v3_group`; the parallel removal lane edits other parts of the file. A change under `src/auditmanager/bootstrap/**` is a named case of `AGENTS.md` section 8 (a complete gate once on the lane), deferred here by `R-135`; the targeted composition and runs suites are in the report. After the merge the debt row that A3 proposed («the AR v3 group start leaves its six Runs `created` with no Job») is closed by this task: its check `pytest -q tests/integration/runs/test_v3_recorded_group_over_http.py -k queues_the_six_runs` now shows the fact flipped.

## Failure/idempotency/security cases
- a replayed start (same key, same body): `202`, the same group and members as they are now, no new Run, no new Job, no carrier submission
- a refused start (empty registry, non-expert, anonymous, body naming a pack): nothing created, nothing submitted
- a process that dies after the 202: the Runs and Jobs are committed together, so a restarted process finds all six through the poller's query
- a start that fails inside the transaction (any refusal, or an illegal `created -> queued`): rolled back as a whole, nothing submitted

## Rollback / feature flag
Revert the single commit of the adapter change: the start returns to creating six `created` Runs and no Job (the gap). No flag: the group start is already gated by the installed reviewed pack, which is not installed on any stand.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report
- integration notes: see the report
