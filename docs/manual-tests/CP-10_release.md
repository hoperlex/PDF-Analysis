# CP-10 — v1.0 release acceptance

## Preconditions

- Release candidate commit frozen.
- Clean environment.
- All prior CP reports available.
- No unresolved critical blocker.

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

### MT10-01 — Clean deploy

**Action**
Deploy/start from documented release procedure.

**Expected**
No manual patch or hidden local state needed.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT10-02 — Full audit journey

**Action**
Project → version/upload → full audit → evidence → expert verdict → export.

**Expected**
Entire primary business journey succeeds with provenance.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT10-03 — Full comparison journey

**Action**
Create pair → approve links → deterministic diff → AI/graphic layer if v1 scope.

**Expected**
Ownership/raw/derived boundaries visible and correct.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT10-04 — Recovery

**Action**
Restart services and reopen accepted run/finding/decision/comparison.

**Expected**
Durable state/history retained.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT10-05 — Distributed route

**Action**
If enabled in v1, execute CP-08 representative disconnect/recovery. If not enabled, verify feature explicitly disabled/absent.

**Expected**
Release scope matches docs/feature configuration.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT10-06 — Backup/restore/rollback

**Action**
Run release recovery/rollback drill to documented point.

**Expected**
Operator can recover/rollback with recorded exact build/migration/contract versions.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT10-07 — Known limitations

**Action**
Review release notes/runbooks against actual UI/API behavior.

**Expected**
No known critical behavior is hidden; limitations have owner/next task.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] All automated release gates green.
- [ ] Manual tester signs report with exact commit/tag candidate.
- [ ] Annotated `v1.0.0` created only after acceptance.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
