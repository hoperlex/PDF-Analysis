# CP-00 — Architecture acceptance

## Preconditions

- An unpacked bootstrap package.
- Read-only access to the canonical legacy commit named in `docs/SOURCE_TRACEABILITY.md` and to the original ADRs and Bible.
- An assigned architecture/domain owner and independent reviewer.

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

### MT00-01 — Documentation navigation

**Action**
Open README → Product synopsis → Bible → ADR index → Roadmap → S00. Check that no link in this chain points to a missing required document.

**Expected**
All plan-of-record documents are available; the bootstrap package is self-contained.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-02 — Greenfield boundary

**Action**
Trace the main user journey and confirm that no required runtime step starts or imports the legacy application.

**Expected**
The legacy application is mentioned only as an oracle or fixture source.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-03 — Identity walk

**Action**
Take a legacy scenario with a finding that reappears on rerun. Trace it on paper or a whiteboard through `Finding`/`FindingObservation`/`ExpertDecision`.

**Expected**
`F-NNN` is never needed as a foreign key; an expert decision survives a rerun only through the stable identity policy.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-04 — Run/job/attempt walk

**Action**
Model a provider timeout → retry → stale worker result.

**Expected**
Run, Job, and Attempt stay distinct; a stale Attempt cannot publish a result.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-05 — Comparison ownership

**Action**
Model an automatic suggestion → user-approved sheet link → recompute → AI review.

**Expected**
Recomputation does not overwrite an approved link; AI does not change raw deterministic evidence.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-06 — Unresolved decisions

**Action**
Review the proposed ADRs and owner decisions.

**Expected**
Retention, tenant, IdP, and other unconfirmed values remain explicitly unresolved rather than invented.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] There is no hidden Strangler runtime dependency.
- [ ] Every key bounded context has a data owner.
- [ ] A reviewer can understand the shared contract freeze and process without an oral explanation.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
