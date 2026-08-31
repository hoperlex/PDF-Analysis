# CP-08 — Distributed execution

## Preconditions

- Center/control plane and one test worker.
- Worker has scoped credentials and same engine package version.
- Fault injection for network/process/checksum.

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

### MT08-01 — Enroll/capabilities

**Action**
Enroll/approve worker and inspect capabilities.

**Expected**
No provider secret copied to control plane; worker identity/capabilities durable.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT08-02 — Remote run

**Action**
Assign golden audit to worker.

**Expected**
Job gets concrete Attempt/lease; result semantics match local contour.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT08-03 — Network loss

**Action**
Disconnect worker network while stage runs; wait; restore.

**Expected**
Heartbeat loss does not kill running work; queued events catch up idempotently.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT08-04 — Worker restart

**Action**
Restart worker process mid/after work according to test case.

**Expected**
Local durable job/outbox recovers; no duplicate effects.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT08-05 — Stale attempt

**Action**
Supersede/expire attempt through test harness and submit stale result.

**Expected**
Fencing rejects stale publication.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT08-06 — Corrupt result

**Action**
Modify test package/checksum before upload/validation.

**Expected**
Result remains unpublished/quarantine with diagnosable error.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT08-07 — Unknown action

**Action**
Send unsupported worker action through test harness.

**Expected**
Worker rejects/audits; no arbitrary shell execution.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] Remote placement does not change data owner.
- [ ] Offline/restart/replay safe.
- [ ] Validated publish is atomic from business perspective.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
