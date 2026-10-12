# W53C-EXEC-01 — hand-back report

Lane `EXEC` of `W53-CLOSE` (`docs/program/dispatch/W53-CLOSE-PLAN.md` §2 C-01…C-06), branch
`agent/w53c-exec`, base `04de50c` (`integration/w53-close`). Every finding was re-read at its
cited location before it was changed; all six reproduced at the base.

## Findings

| ID | Status | What changed |
|---|---|---|
| C-01 | fixed | `JobRepository.start_execution` re-raises every catalog refusal of the claim (pause `CONFLICT`, duplicate-executor `CONFLICT`, not-claimable Run/Job) as the new `ExecutionNotClaimed(DomainError)`, same code, message and details. `run_to_terminal` logs it and re-raises without `_record_crash`, so the Run and Job stay as the claim found them. |
| C-02 | fixed (`R-82`) | `reaudit_run` takes `analysis_profile_id`, `prompt_bundle_id`, `provider_mode` (required), resolves the source version's manifest through the same guard as `start_audit_run` and computes a new `frozen_input_digest`. `ExecutionAdapter.reaudit_run` passes `RunAdapter.current_configuration()` — the same three fields `start_run` stamps. No composition change was needed. |
| C-03 | fixed | `RunRow.reaudit_of_run_id` (selected in `_RUN_COLUMNS`); `_run_status_view` reads it from the row; the raw `text(...)` query and the now-unused `from sqlalchemy import text` import in `bootstrap/adapters.py` are gone. |
| C-04 | fixed | `ProxyAdapter` validates the 200 body shape explicitly and has a backstop catch, so every unusable answer is one `ProxyDispatchError(ANALYSIS_FAILED, dispatch_class="outcome_unknown", retry_safe=False)`. When the body has a readable usage block it carries `received: ReceivedResponse` (sha256 of the raw bytes, provider token counts, latency); the stage journals that as `response_received`, otherwise `outcome_unknown`. |
| C-05 | fixed for the journal path | `run_text_analysis` journals any failed call of a **recorded** adapter as `not_processed`/`not_sent`. See limitation 1 for the lease-reclaim path. |
| C-06 | fixed | `ABSENT_CAPABILITIES` now lists remote execution and cancellation after `validating` (cancel exists); stale heartbeat/failover/resume prose corrected in `runs/__init__.py`, `runs/executor.py`, `runs/carrier.py`, `runs/repository.py`; dead `jobs/lease.py` `LEASE_SECONDS` removed (the 60 s lease lives in SQL: migration 0017 default and `_HEARTBEAT`); `finish_execution -> None`. No test read `ABSENT_CAPABILITIES` at the base although its module said one did; `test_the_scope_note_does_not_deny_a_command_that_exists` now does. |

## 1. Changed files

```
src/auditmanager/analysis/text/proxy.py
src/auditmanager/analysis/text/stage.py
src/auditmanager/bootstrap/adapters.py        (ExecutionAdapter, RunAdapter, _run_status_view, unused import)
src/auditmanager/jobs/__init__.py
src/auditmanager/jobs/lease.py
src/auditmanager/jobs/public.py
src/auditmanager/jobs/repository.py
src/auditmanager/runs/__init__.py
src/auditmanager/runs/carrier.py
src/auditmanager/runs/commands.py
src/auditmanager/runs/executor.py
src/auditmanager/runs/repository.py
src/auditmanager/runs/scope.py
tests/integration/analysis_text/test_w53c_proxy_answer_shapes.py   (new)
tests/integration/runs/test_w53_execution.py                       (re-audit test follows R-82)
tests/integration/runs/test_w53c_exec_closure.py                   (new)
docs/program/W53C-EXEC-01.md                                       (this report)
```

## 2. Checks

All in `/root/projects/PDF-Analysis/.local/worktrees/w53c-exec`.

- `git diff --check` — exit 0.
- `ruff check` on every changed Python file. `.venv/bin/ruff` does not exist in the shared
  tooling; the integrator's downloaded `ruff 0.17.0` in the session scratchpad was used. Per
  file, the finding count is equal to the base or lower (`runs/scope.py` 1 → 0); the two new
  test files have 0. Pre-existing findings were not touched (e.g. F821 `QueuePosition` in
  `adapters.py`, F821 `outcome` in `executor.py`, F841 in `test_w53_execution.py`).
- `.venv/bin/python -m compileall -q src/auditmanager/runs src/auditmanager/jobs src/auditmanager/analysis/text/proxy.py src/auditmanager/analysis/text/stage.py src/auditmanager/bootstrap/adapters.py <three test files>` — exit 0.
- Container-free: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis_text/test_w53c_proxy_answer_shapes.py tests/integration/analysis_text/test_proxy_adapter.py tests/integration/analysis_text/test_proxy_truncation_reaches_partial.py tests/integration/qa_w53/test_proxy_refusal_boundary.py` — 115 passed.
- Private lane `gate-w53c-exec` (PostgreSQL 57020, S3 60620/60621; `make up`, `make migrate`
  to `0017_execution_queue`), one pytest at a time:
  - `tests/integration/runs/test_w53c_exec_closure.py` — 5 passed;
  - `tests/integration/runs` — 138 passed;
  - `tests/integration/qa_w53` — 6 passed;
  - `tests/integration/analysis_text` — 187 passed;
  - `tests/integration/api/test_query_surface.py test_authorization.py test_role_register.py test_served_document_and_health_plane.py` — 98 passed;
  - `tests/integration/composition/test_the_run_leaves_the_request_thread.py` — first run
    12 passed, 1 failed (`test_serving_lifespan_dispatches_an_ordinary_run_adapter_submission`:
    `gated.entered` fired but the run was still `queued`); the single test then passed twice
    and the whole module passed 13/13 on rerun. Reading of the cause: leftover committed
    `leased`/`running` Jobs from earlier suites in the same database are reclaimed by the
    poller's startup sweep after the test deferred only `queued` Jobs, and one of them
    entered the gated adapter first. It does not involve code this lane changed; recorded
    as a test-isolation flake, not fixed (outside allowed paths).
- Afterwards `make down`, `docker volume rm gate-w53c-exec-postgres-data gate-w53c-exec-s3-data`,
  `.env` deleted; no `gate-w53c-exec` container, volume or network remains.

How each new test was shown to fail without its fix (each mutation restored with
`git checkout -- src` and the tree verified clean):

| Mutation | Result |
|---|---|
| base `runs/carrier.py` | C-01 test fails: row `('failed', 'analysis_failed', 'executor_raised_before_terminal', 'cancelled', None, 0)` |
| `reaudit_run` creates the child from `source.*` profile/bundle/mode/digest | both C-02 tests fail |
| `_run_row` sets `reaudit_of_run_id=None` | both re-audit tests fail on the lineage |
| base `analysis/text/stage.py` | C-05 crash-resume test fails (effect `outcome_unknown`, run failed) |
| base `runs/scope.py` | C-06 test fails |
| base `proxy.py` + `stage.py` (plus a `ReceivedResponse` shim so the module imports) | 21 of 22 tests in `test_w53c_proxy_answer_shapes.py` fail; the anti-vacuity test passes |

## 3. Contracts

None. No API, domain, event, error-catalog or migration change. `ExecutionNotClaimed`
is a `DomainError` subclass carrying the original code, so the HTTP envelope is unchanged.
`reaudit_run` (an in-process command) gained three required keyword arguments; its only
production caller is `ExecutionAdapter`.

## 4. Risks and known limitations

1. **C-05 lease-reclaim path.** `JobRepository.reclaim_expired` still treats any effect that
   is not `not_processed` as ambiguous. A recorded call still `prepared` when the process
   dies is marked `outcome_unknown` and fails the run, and a recorded call already
   `completed` blocks resume. Restricting ambiguity to `provider_mode = 'live'` would
   contradict `tests/integration/qa_w53/test_queue_and_effect_journal.py::test_lease_reclaim_journals_the_effect_outcome`,
   which pins a recorded `prepared` effect becoming `outcome_unknown` and which this lane
   may not edit. Left for the integrator/owner to decide.
2. **C-04 spend visibility.** An unusable answer with usage leaves its effect in
   `response_received` (no canonical `model_call` is invented); the terminal settlement
   sweep later marks it `abandoned` with the tokens kept. The run's `model_call` cost does
   not include that spend.
3. **C-04 stricter parsing.** Usage counts must be non-negative integers (integral floats are
   accepted); string counts such as `"12"` and booleans, previously coerced, are now refused;
   non-string `content`/`finish_reason` are refused instead of failing later in parsing.
4. **C-02 idempotency.** The re-audit fingerprint is unchanged (source run id plus source
   digest): the configuration is the server's, not the request's. A same-key retry after a
   configuration change replays the run created at first acceptance.
5. **C-01 scope.** Only refusals of the claim itself leave the run queued. Pre-claim
   refusals about the run (adapter/run mode mismatch, missing version) still fail it, as
   before; leaving those queued would make the poller retry them forever.
6. The comment in `tests/integration/findings/test_terminal_rules_are_load_bearing.py:45-46`
   ("PC-01 has no cancel command") is stale for the same reason as C-06 but is outside this
   lane's paths; its assertions remain true (`validating` cannot reach `cancelled`).

## 5. Integrator instructions

- Merge `agent/w53c-exec` as is. Expected overlap: `src/auditmanager/bootstrap/adapters.py`
  with the IDENTITY lane (`AccountAdapter`). This lane removed the module-level
  `from sqlalchemy import text` import because `_run_status_view` was its only user; if the
  IDENTITY lane introduces a `text(...)` call, re-add that import during the merge.
- Re-run on the integrator lane: `tests/integration/runs`, `tests/integration/qa_w53`,
  `tests/integration/analysis_text`, and the composition/API modules listed in §2.
- Limitations 1 and 6 need a decision or another lane's edit; consider deferred-register rows.

## 6. Containment

- `git diff --name-only 04de50c..HEAD` lists exactly the files in §1; all are inside the
  task's allowed paths, and the `bootstrap/adapters.py` changes are confined to
  `ExecutionAdapter`, `RunAdapter`, `_run_status_view` and the import that only
  `_run_status_view` used.
- No change under `contracts/**`, `db/migrations/**`, root dependency/lock files, `Makefile`,
  `tests/support/**`, any `conftest.py`, `VERSION`, `release-notes/**`, `CURRENT_STATE.md`,
  `DEBT_REGISTER.md`, `bootstrap/composition.py` or existing `tests/integration/qa_w53` files.
- `git status --porcelain -uall` is empty after the final commit.
- Nothing pushed, merged, rebased or tagged; no worktree created; only PIDs and containers
  this lane started were stopped.
