# S10 — Release acceptance

**Target checkpoint:** `CP-10 / v1.0.0`

## Goal

Собрать единый v1.0 evidence bundle, подтвердить clean deployment/recovery and golden journeys, зафиксировать known limitations and ownership.

## Preconditions

- CP-09 accepted.
- All v1 blockers closed or explicitly removed from scope with owner approval.

## Contract gate

No new feature contract by default; release only. Semantic change reopens relevant stage/wave.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W10.1 — release freeze

Freeze dependencies/contracts/migrations; feature work stops.

### W10.2 — independent acceptance

QA/manual tester uses clean environment; experts evaluate labelled live-quality sample.

### W10.3 — release/rollback drill

Deploy candidate, smoke, restore/rollback proof, tag.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W10-INT-00 | INT | Release freeze + build/contract manifest | CP-09 | release evidence | No opportunistic dependency updates. |
| W10-QA-01 | QA | Full automated suite + flaky triage | W10-INT-00 | test evidence | No permanent flaky allowlist. |
| W10-QA-02 | QA | Independent golden E2E acceptance | W10-INT-00 | manual/E2E | Fresh environment. |
| W10-AI-01 | AI | Live quality/cost/latency sample review | W10-INT-00 | quality report | No text-equality requirement. |
| W10-OPS-01 | OPS | Clean deploy/backup/restore/rollback | W10-INT-00 | ops evidence | Exact versions recorded. |
| W10-SEC-01 | SEC | Release security/secret/permission review | W10-INT-00 | security report | No critical blocker. |
| W10-DOC-01 | ARC | Final developer/operator docs | W10-INT-00 | docs/runbooks | Docs match reality. |
| W10-INT-01 | INT | Approve/tag v1.0.0 | all | release report/tag | Only after evidence. |

## Automated exit evidence

- [ ] All mandatory gates green from clean checkout.
- [ ] Fresh install + supported migration path pass.
- [ ] Golden/replay suites pass.
- [ ] No unresolved critical security/data-loss blocker.
- [ ] Build/contract/dependency manifest reproducible.

## Manual local acceptance

Full script: `../manual-tests/CP-10_release.md`.

- [ ] Execute complete audit journey through expert verdict/export.
- [ ] Execute comparison journey with approved link and raw/AI layers.
- [ ] If distributed is v1 scope, execute recovery route; otherwise verify feature explicitly disabled/absent.
- [ ] Restore/restart and reopen accepted run/decision artifacts.
- [ ] Perform release rollback/recovery drill and sign report.

## Checkpoint exit criterion

`v1.0.0` is an evidence-backed reproducible release, not merely completion of backlog.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
