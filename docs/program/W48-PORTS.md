# W48-PORTS — D-74 premise reconciliation

## Result

**DONE without a runtime rewrite.** The Stage-B plan described D-74 as open, but the exact
repair has been in the accepted tree since `8877d5de` (`feat(A3): D-74 -- a parent-existence
check no longer costs a full parent read`). Repeating it would create churn rather than change
behaviour. This task verified the complete matrix and leaves the canonical stale row for
`W48-INT-CLOSE`, its named owner.

## Verified implementation matrix

| role | run existence | finding existence |
| --- | --- | --- |
| semantic port | `RunPort.run_exists` | `FindingPort.finding_exists` |
| production adapter | `RunAdapter.run_exists` | `FindingAdapter.finding_exists` |
| API test implementation | `_Runs.run_exists` | `_Findings.finding_exists` |
| caller | `findings.py` | `decisions.py` |

The source query at Stage-B base `7ad7cfe` returned exactly eight implementation/call sites:

```text
src/auditmanager/api/routers/decisions.py:128: findings.finding_exists(...)
src/auditmanager/api/routers/findings.py:79: runs.run_exists(...)
src/auditmanager/bootstrap/adapters.py:384: def run_exists(...)
src/auditmanager/bootstrap/adapters.py:689: def finding_exists(...)
src/auditmanager/api/routers/ports.py:252: def run_exists(...)
src/auditmanager/api/routers/ports.py:320: def finding_exists(...)
tests/integration/api/conftest.py:540: def finding_exists(...)
tests/integration/api/conftest.py:749: def run_exists(...)
```

`git show --stat 8877d5de` names all seven files carrying the ports, production/test
implementations, callers and focused regressions. `git blame` attributes the semantic methods to
the same commit. There is no later replacement or duplicate path.

## Behavioural evidence

`tests/integration/api/test_existence_is_not_a_full_read.py` separately proves:

- existing and absent runs return `True`/`False`;
- the narrow run query reads neither stage results nor model-call cost, while the full-read
  control does;
- existing and absent published findings return `True`/`False`;
- the narrow finding query does not read decision history, while the full-read control does.

`tests/integration/composition/test_every_port_implementation_is_whole.py` checks the complete
port/implementation surface and prevents a missing method from becoming a runtime
`AttributeError`.

## Checks

Final focused run against the already-running isolated W48 disposable PostgreSQL lane:

```text
.venv/bin/python -m pytest \
  tests/integration/api/test_existence_is_not_a_full_read.py \
  tests/integration/composition/test_every_port_implementation_is_whole.py -q

20 passed, 1 deprecation warning in 68.77s
```

The first invocation without `DATABASE_URL` correctly failed eight DB-backed cases rather than
skipping. A second sandboxed invocation could not reach loopback. Neither is accepted as task
evidence; the final run above used the existing local disposable lane and passed all 20 cases.

`git diff --check` is clean. The task diff contains this report only.

## Contracts, risks and integration

No API/domain/error contract, migration, dependency/lock, runtime, test, composition, global
style, deployment command, host, ref or tag changed. API remains 17 paths / 20 operations / 61
schemas, error catalog 22, migration head `0013_norm_embeddings`.

Known limitation: `docs/program/DEBT_REGISTER.md` still presents D-74 as open. That file is a
forbidden hotspot here and belongs to `W48-INT-CLOSE`; the integrator must append/record closure
from commit `8877d5de` and this verification rather than changing runtime.

Integration instruction: fast-forward/cherry-pick the report commit only, then continue with
`W48-WEB`. Rollback is a revert of this documentation commit.

## Forbidden-hotspot proof

The only changed path is `docs/program/W48-PORTS.md`, exactly the task's sole allowed path.
Runtime/test code, contracts, migrations, locks, `Makefile`, composition root, global styles,
state/register/history, refs, tags and deployment state are untouched.
