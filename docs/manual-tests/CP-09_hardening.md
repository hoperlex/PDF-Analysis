# CP-09 — Production hardening

## Preconditions

- Approved test AuthZ/retention/backup policies.
- Two test principals/objects.
- Synthetic data only.

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

### MT09-01 — Cross-object AuthZ

**Action**
User A attempts read/write/run/decision/file-link on User B object.

**Expected**
All object boundaries denied server-side and audited where required.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT09-02 — Presigned expiry

**Action**
Generate short-lived test access, use before and after expiry.

**Expected**
Works only within scope/TTL; no permanent public access.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT09-03 — Redaction

**Action**
Inject designated fake secret/token/PII markers into safe test inputs/errors.

**Expected**
Markers absent from default diagnostic logs, durable audit payload fields not allowlisted and metric labels.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT09-04 — Retention dry-run

**Action**
Run deletion/retention dry-run on synthetic object.

**Expected**
Exact impacted canonical/derived artifacts listed; no deletion in dry-run.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT09-05 — Legal hold

**Action**
Apply test legal hold and request deletion.

**Expected**
Deletion blocked according to approved policy with audit evidence.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT09-06 — Backup/restore

**Action**
Create backup then restore to clean local environment.

**Expected**
Required metadata/manifests/artifacts can be reopened within target recovery procedure.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT09-07 — Provider outage/cost gate

**Action**
Simulate provider outage and cost-budget breach.

**Expected**
Explicit controlled state; no silent provider/model downgrade.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT09-08 — Readiness/load

**Action**
Run documented load smoke and dependency failure.

**Expected**
Readiness/SLO behavior matches policy; no process kill solely due readiness failure.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] Owner-approved retention matrix used; no invented TTL.
- [ ] Restore drill produces evidence.
- [ ] Critical secrets/security negative tests pass.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
