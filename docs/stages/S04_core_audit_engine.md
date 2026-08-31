# S04 — Core audit engine

**Target checkpoint:** `CP-04 / v0.4.0-audit-beta`

## Goal

Расширить один working stage до production-like audit DAG: deterministic preparation, block/graphic context, merge/review, authoritative norms, retry/resume and export.

## Preconditions

- CP-03 accepted.
- Stage registry/package contracts stable enough for additive stages.

## Contract gate

Stage DAG v1, geometry/block artifacts, merge identity input, critic/corrector result, norm policy/snapshot, export schema, resume/retry semantics.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W4.1 — DAG/contracts

Freeze stage names/dependencies/output roles and norm failure semantics.

### W4.2 — parallel stage families

Geometry, block analysis, merge, critic, norms, export and QA as independent lanes.

### W4.3 — orchestration/recovery

Integrate durable stage state, retry/resume, partial coverage and publication gate.

### W4.4 — beta acceptance

Golden/replay/live-quality sample + interruption/recovery.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W4-C-01 | ENG | Freeze core stage registry/DAG | CP-03 | contracts/analysis | Single stage-order source. |
| W4-ENG-01 | ENG | Geometry/page/crop deterministic artifacts | W4-C-01 | analysis stage | Rebuildable/checksummed. |
| W4-ENG-02 | ENG | Block context + visual analysis | W4-C-01 | analysis stage | Declared artifacts only. |
| W4-FND-01 | FND | Merge/dedup/identity mapping | W4-C-01 | findings | No ordinal identity. |
| W4-AI-01 | AI | Critic/corrector quality stages | W4-C-01 | analysis | Derived provenance preserved. |
| W4-AI-02 | AI | Norm verification via versioned snapshot | W4-C-01 | norm adapter | Fail closed/explicit partial. |
| W4-JOB-01 | JOB | Durable stage state + bounded retry/resume | W4-C-01 | jobs/orchestration | Restart/fencing aware. |
| W4-EXP-01 | API | Export request/artifact pipeline | W4-C-01 | export/** | References exact run/version. |
| W4-WEB-01 | WEB | Progress/coverage/retry/export UI | W4-C-01 | web slices | Partial/failed visible. |
| W4-QA-01 | QA | Stage/replay/interruption/norm tests | W4-C-01 | tests/** | Missing/invalid artifact coverage. |
| W4-INT-01 | INT | Audit beta checkpoint | all | evidence | Full synthetic run. |

## Automated exit evidence

- [ ] Unknown package/stage version rejected.
- [ ] Stage harness prevents undeclared input use.
- [ ] Missing authoritative norm source cannot produce verified normative claim.
- [ ] Kill/restart does not duplicate publication.
- [ ] Export checksum ties to exact run.
- [ ] Golden contour/replay parity meets policy.

## Manual local acceptance

Full script: `../manual-tests/CP-04_audit_beta.md`.

- [ ] Run full audit on golden synthetic project.
- [ ] Inspect DAG/progress/coverage and text+visual evidence.
- [ ] Interrupt engine and restart; verify attempt/resume behavior.
- [ ] Disable norm source and verify explicit failure/partial/no fake verification.
- [ ] Generate export and trace rows to finding/run.

## Checkpoint exit criterion

Core audit is usable end-to-end with durable recovery, evidence, norm provenance and export.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
