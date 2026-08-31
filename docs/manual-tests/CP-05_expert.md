# CP-05 — Expert workflow

## Preconditions

- Completed audit with several stable findings.
- Authorized and unauthorized test principals.

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

### MT05-01 — First decision

**Action**
Accept finding with reason/comment if applicable.

**Expected**
Append-only Decision event appears; current projection updates.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT05-02 — Change verdict

**Action**
Reject same finding with another reason.

**Expected**
Second event appended; first retained; projection reflects latest valid decision.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT05-03 — Discussion

**Action**
Add discussion/comment and refresh/restart.

**Expected**
Actor/timestamp/audit retained; no mutable anonymous overwrite.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT05-04 — Projection rebuild

**Action**
Invoke supported KB/current projection rebuild in local environment.

**Expected**
Semantic current verdict/KB remains same after rebuild.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT05-05 — Audit rerun

**Action**
Rerun source fixture and open matched stable finding.

**Expected**
Expert history associated by stable Finding identity, not old ordinal.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT05-06 — AI verifier

**Action**
Run Evidence Verifier/re-review recommendation.

**Expected**
Recommendation is separate and cannot change human verdict automatically.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT05-07 — Unauthorized review

**Action**
Attempt decision on object without grant.

**Expected**
Server denies; UI hiding alone is not security boundary.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] Decision history immutable.
- [ ] KB rebuildable.
- [ ] AI recommendation and human decision visibly distinct.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
