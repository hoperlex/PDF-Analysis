# CP-07 — Advanced comparison

## Preconditions

- CP-06 golden pair/raw evidence.
- Recorded AI comparison response + graphic pair.

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

### MT07-01 — AI synthesis

**Action**
Generate AI review from raw evidence.

**Expected**
Derived artifact references raw checksum + AnalysisProfile/model provenance.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT07-02 — Malformed AI output

**Action**
Activate invalid response fixture.

**Expected**
AI layer fails explicitly; raw diff remains available and unchanged.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT07-03 — New profile revision

**Action**
Run synthesis with changed approved profile.

**Expected**
New derived revision created; previous artifact retained.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT07-04 — Repair proposal

**Action**
Generate/inspect a link/content repair proposal.

**Expected**
Proof/rationale/source refs visible before state change.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT07-05 — Accept + undo repair

**Action**
Accept repair then undo.

**Expected**
Both actions audited; prior approved state restored.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT07-06 — Graphic overlay

**Action**
Open raw graphic/vector evidence overlay.

**Expected**
Coordinates align with golden page; raw artifact is separate from AI summary.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] AI never overwrites raw evidence.
- [ ] Repair is auditable/reversible.
- [ ] Graphic evidence traces to source/version/checksum.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
