# CP-03 — First real audit alpha

## Preconditions

- Synthetic/anonymized real input bundle.
- Recorded provider-response cassette for deterministic replay.
- Optional live provider configured separately from mandatory replay.

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

### MT03-01 — Ingest normalization

**Action**
Upload direct/ZIP form defined in test fixture.

**Expected**
Both normalize to expected InputManifest semantics; transport path not identity.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT03-02 — Replay audit

**Action**
Run first real stage using recorded response.

**Expected**
Finding observation produced with page/evidence and stage provenance.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT03-03 — Provenance inspection

**Action**
Open run technical details/read model.

**Expected**
Input checksum, AnalysisProfile, PromptBundle, stage version, ModelCallRecord and result checksum are discoverable to authorized operator.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT03-04 — Rerun identity

**Action**
Repeat using same replay fixture.

**Expected**
`finding_uid` carryover follows matcher policy; observation/run IDs are new as appropriate.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT03-05 — Provider timeout

**Action**
Activate test adapter fault/timeout.

**Expected**
Explicit retryable/failed state; no silent fallback or fake successful finding.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT03-06 — Evidence UI

**Action**
Open PDF/evidence context from finding.

**Expected**
Correct page/location rendered; internal storage key not exposed.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] Recorded replay gives deterministic downstream result.
- [ ] Live response equality is not required for pass.
- [ ] Provider failure cannot erase prior successful run/history.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
