# CMP-JOB-HINT-01 — Run dispatch hint and comparison calls

Task: [`CMP-JOB-HINT-01`](tasks/CMP-JOB-HINT-01.md). Base: C2 publication candidate `8f23322df1ced8aaa253b2b495e76993104e41af`; this branch is separate and has no publication authority.

`JobRepository.next_queued_run` now treats a connection as held while a `comparison_model_call` is `prepared` or `sent` and its attempt is `created`, `leased` or `running`. It maps the call's frozen executor revision to the connection, matching the locked claim's existing predicate. The held CTE still takes active Run Jobs and submitted Runs. A terminal call, a lost attempt or a call without a connection does not hold a connection. Priority and age ordering are unchanged. The hint remains advisory; `start_execution` still makes the authoritative decision under its connection lock.

The new real-PostgreSQL test puts a higher-priority queued Run behind the occupied connection and a lower-priority Run on a free connection. It checks all five call states and verifies that ending the attempt releases the hint even if the historical call row remains. The existing connection-limit suite checks submitted Runs, active Runs and Runs without a connection.

Checks on isolated `auditmanager-cmp-job-hint-01` at migration head `0040_comparison_ai_reports`:

- `make up` and `make migrate`: pass.
- `pytest -q tests/integration/comparison/spend/test_connection_single_user.py tests/integration/jobs/test_connection_limit_claim.py`: **31 passed**.
- PostgreSQL `EXPLAIN (FORMAT JSON)` of `_NEXT_JOB`: the default plan uses the partial `ix_comparison_model_call_open` index; it remains eligible with sequential scans disabled.
- `py_compile` of the two changed Python files and `git diff --check`: pass.

No contract, migration, composition root, dependency/lockfile, global style or other `jobs/**` file changed. This task does not touch the C2 gate candidate. Merge this branch after that exact candidate has been published to `origin/dev`, then close D-260 in the integrated debt register. No `origin/main` action is authorized.
