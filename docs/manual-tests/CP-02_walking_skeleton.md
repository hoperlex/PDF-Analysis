# CP-02 — Walking skeleton local acceptance

## Preconditions

- CP-01 stack working.
- Synthetic PDF fixture.
- Fake engine enabled explicitly.

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

### MT02-01 — Create hierarchy

**Action**
В UI создать project/document as defined by slice.

**Expected**
Opaque IDs returned; human names are display-only.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT02-02 — Upload

**Action**
Загрузить synthetic PDF and publish version.

**Expected**
Blob verify completes; immutable version/input manifest visible.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT02-03 — Idempotent retry

**Action**
Повторить тот же upload command с тем же idempotency key/flow.

**Expected**
No duplicate version/blob/business effect.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT02-04 — Fake audit

**Action**
Start audit. Refresh browser while running.

**Expected**
Run/Job survive refresh; progress projection reconstructs from durable state.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT02-05 — Finding publication

**Action**
Wait fake ResultPackage publication and open finding.

**Expected**
Finding + run-specific observation visible with stable opaque identifiers.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT02-06 — Process restart

**Action**
During new fake run restart API/runner according to supported local procedure.

**Expected**
No duplicate published result; durable job reaches allowed state/retry.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT02-07 — Integrity failure

**Action**
Use designated test fixture/path to cause checksum mismatch.

**Expected**
Artifact/result is rejected/quarantined; not published as success.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] No URL/file name/S3 key serves as identity.
- [ ] No duplicate side effects under retry/restart.
- [ ] UI has visible loading/error/empty states.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
