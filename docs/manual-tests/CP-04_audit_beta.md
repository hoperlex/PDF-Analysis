# CP-04 — Core audit beta

## Preconditions

- Golden synthetic project with text + block/visual cases.
- Versioned norms snapshot/test authoritative source.
- Core stage DAG enabled.

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

### MT04-01 — Full run

**Action**
Start full audit and watch stage progress.

**Expected**
Stages follow versioned registry/DAG; progress reflects durable stage state.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT04-02 — Evidence coverage

**Action**
Inspect at least one text and one visual/block finding.

**Expected**
Each finding observation traces to declared source artifacts/page geometry.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT04-03 — Norm verification

**Action**
Open a normative finding and provenance.

**Expected**
Verification references exact NormsSnapshot/provenance, not model-memory claim.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT04-04 — Norm source unavailable

**Action**
Disable required test norm source/snapshot and run affected case.

**Expected**
Stage becomes explicit failed/partial according to policy; verified claim is not fabricated.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT04-05 — Interrupt/recover

**Action**
Terminate engine in a supported retryable stage then restart.

**Expected**
New/resumed Attempt follows policy; no duplicate finding/publication.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT04-06 — Export

**Action**
Generate report/export.

**Expected**
Artifact references exact run/version and rows map back to findings.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT04-07 — Partial/poison case

**Action**
Use designated invalid/missing artifact fixture.

**Expected**
Bounded retries then diagnosable terminal/partial state; no infinite retry.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] Full golden route completes.
- [ ] Replay/contour parity policy satisfied.
- [ ] Recovery does not mutate completed immutable artifacts.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
