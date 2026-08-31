# CP-01 — Repository foundation local smoke

## Preconditions

- Clean checkout candidate.
- Docker-compatible local runtime or chosen equivalent.
- No pre-existing project DB/bucket required.

## Start record

Before testing record:

```text
candidate_commit:
contract_manifest:
migration_head:
backend_runtime:
frontend_runtime:
local_infra_versions:
tester:
started_at:
```

## Test cases

### MT01-01 — Clean bootstrap

**Action**
В новом worktree запустить documented bootstrap.

**Expected**
Dependencies/locks resolve reproducibly; no manual copying of secrets/files.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT01-02 — Local services

**Action**
Запустить local PostgreSQL + S3-compatible storage + API + web.

**Expected**
All expected services start; S3 bucket is non-public.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT01-03 — Liveness/readiness split

**Action**
Проверить liveness/readiness. Затем остановить PostgreSQL и повторить.

**Expected**
Liveness stays OK while process responsive; readiness fails safely without infrastructure details.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT01-04 — Frontend shell

**Action**
Открыть web UI and one API-backed page/state.

**Expected**
Shell loads; typed/safe error state shown when dependency unavailable.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT01-05 — Restart

**Action**
Вернуть DB, stop/start whole local stack.

**Expected**
Readiness recovers; no manual file/database edits needed.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT01-06 — Fresh test commands

**Action**
Запустить lint/type/contract/integration command set.

**Expected**
Commands match README and complete from clean checkout.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] Second agent can reproduce environment.
- [ ] No secret committed/generated into source tree.
- [ ] OpenAPI client can be regenerated without diff on same contract.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
