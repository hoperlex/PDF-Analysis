# S02 — First walking skeleton

**Target checkpoint:** `CP-02 / v0.2.0-walking-skeleton`

## Goal

Доказать один полный vertical slice: Project → DocumentVersion → Blob/InputManifest → AuditRun/Job → fake engine → FindingObservation → UI.

## Preconditions

- CP-01 accepted.
- Domain v1 and API/event/analysis subset frozen.

## Contract gate

Project/version commands, upload/blob manifest, Run/Job/Attempt machines, minimal Finding/FindingObservation, fake ResultPackage, UI read model.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W2.1 — contract gate

Freeze OpenAPI/events/analysis package subset.

### W2.2 — parallel ownership

META/STO/JOB/FND/API/WEB/QA implement distinct owners; engine deterministic fake.

### W2.3 — integration

Wire outbox/job runner/publication/read model and prove restart/idempotency.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W2-C-01 | ARC | Freeze walking-skeleton contracts | CP-01 | contracts/** | Consumers do not edit after freeze. |
| W2-META-01 | META | Project/Document/Version + PostgreSQL | W2-C-01 | documents/ingest | Published version immutable. |
| W2-STO-01 | STO | Blob temp→verify→publish + InputManifest | W2-C-01 | storage/** | Object key hidden; checksum required. |
| W2-JOB-01 | JOB | Run/Job/Attempt + outbox + fake runner | W2-C-01 | jobs/** | Durable before side effect. |
| W2-FND-01 | FND | Finding + Observation publication | W2-C-01 | findings/** | Display ordinal not identity. |
| W2-API-01 | API | Commands/queries for slice | W2-C-01 | api/** | Stable errors/idempotency. |
| W2-WEB-01 | WEB | Project/upload/run/finding UI | W2-C-01 | web slices | Loading/error/empty states. |
| W2-QA-01 | QA | Contract/integration/E2E/restart tests | W2-C-01 | tests/** | Independent provider/consumer checks. |
| W2-INT-01 | INT | Wire slice + checkpoint | all | bootstrap/evidence | No legacy runtime. |

## Automated exit evidence

- [ ] Duplicate upload does not duplicate version/blob.
- [ ] Fake result replay does not duplicate finding/publication.
- [ ] Process restart preserves job state.
- [ ] Checksum mismatch prevents publish.
- [ ] Browser E2E route passes.

## Manual local acceptance

Full script: `../manual-tests/CP-02_walking_skeleton.md`.

- [ ] Create project and upload synthetic PDF.
- [ ] Refresh during fake run; state survives.
- [ ] Retry same upload request and verify idempotent outcome.
- [ ] Restart API/runner and verify no duplicate run/finding.
- [ ] Inspect API/URL and verify opaque IDs/no filesystem or S3 path identity.

## Checkpoint exit criterion

The architecture proves the full data/async/UI path before real AI complexity.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
