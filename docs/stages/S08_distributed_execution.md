# S08 — Distributed execution

**Target checkpoint:** `CP-08 / v0.8.0-distributed`

## Goal

Запускать тот же Execution Engine на remote workers, сохраняя package contract, idempotency, fencing, offline recovery and validated publication.

## Preconditions

- CP-04 accepted.
- Analysis Job/Result contracts stable.
- Local engine implements same boundary.

## Contract gate

Worker enrollment/capabilities, lease/heartbeat, attempt token, package transfer, event sequence/outbox, result validation and action allowlist.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W8.1 — protocol/threat contract

Freeze protocol before network code; no arbitrary inbound command channel.

### W8.2 — parallel center/worker/transfer/security/UI

WRK/JOB/STO/SEC/WEB/QA lanes.

### W8.3 — fault/recovery

Disconnect/restart/stale/corrupt result drills are blockers.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W8-C-01 | WRK | Freeze worker protocol/security contracts | CP-04 | events/api/analysis | Run/Job/Attempt/fencing explicit. |
| W8-WRK-01 | WRK | Enrollment/heartbeat/capabilities | W8-C-01 | workers/** | Heartbeat loss ≠ kill. |
| W8-JOB-01 | JOB | Dispatcher lease/fencing/manual assignment | W8-C-01 | jobs/workers | Stale attempt rejected. |
| W8-STO-01 | STO | Scoped package download + resumable validated upload | W8-C-01 | storage transport | Publish only after verify. |
| W8-WRK-02 | WRK | Worker durable local job/event outbox + recovery | W8-C-01 | worker adapter | Sequence/idempotency. |
| W8-SEC-01 | SEC | Credentials/action allowlist/redaction | W8-C-01 | worker security | No arbitrary shell; provider secrets stay local/scoped. |
| W8-WEB-01 | WEB | Worker/job/attempt ops UI | W8-C-01 | web workers | Offline/lease/recovery visible. |
| W8-QA-01 | QA | Network/restart/stale/corrupt tests | W8-C-01 | tests/** | Fault injection mandatory. |
| W8-INT-01 | INT | Distributed checkpoint | all | evidence | Local/remote contour parity. |

## Automated exit evidence

- [ ] Disconnect does not kill running work.
- [ ] Restart replays unsent events idempotently.
- [ ] Superseded Attempt cannot publish.
- [ ] Corrupt/incomplete result remains unpublished.
- [ ] Repeated upload with same hash is idempotent.
- [ ] Unknown worker action rejected/audited.

## Manual local acceptance

Full script: `../manual-tests/CP-08_distributed.md`.

- [ ] Run audit on test remote worker.
- [ ] Disconnect network and later observe accumulated events.
- [ ] Restart worker process and verify recovery.
- [ ] Supersede attempt then try stale upload and verify rejection.
- [ ] Corrupt artifact/checksum and verify no canonical publication.

## Checkpoint exit criterion

Remote execution changes placement, not business semantics/data ownership, and survives ordinary network/process failures.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
