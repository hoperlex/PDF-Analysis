# S09 — Production hardening

**Target checkpoint:** `CP-09 / v0.9.0-hardening`

## Goal

Закрыть production gates: object AuthZ, approved retention/erasure, observability/redaction, backup/restore, load/performance, provider/cost budgets and runbooks.

## Preconditions

- Core capabilities accepted.
- Owners resolve identity-provider/tenant/retention/legal-hold decisions before irreversible implementation.

## Contract gate

Auth/session/object grants, classification/retention matrix, deletion/legal-hold jobs, SLO/metrics, backup RPO/RTO and cost/quality budgets.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W9.1 — owner/security decisions

Resolve ADR-0014 gaps; never invent TTL in code.

### W9.2 — parallel hardening

SEC/OPS/AI/perf/QA lanes with fault drills.

### W9.3 — restore/security acceptance

Fresh restore and cross-object negative tests before checkpoint.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W9-C-01 | SEC | Freeze AuthZ/retention/legal-hold contracts | owner decisions | ADR/contracts | TTL requires owner/legal support. |
| W9-SEC-01 | SEC | Object AuthZ + presigned controls | W9-C-01 | access/storage/api | Fail closed. |
| W9-SEC-02 | SEC | Retention/erasure/legal-hold workflow | W9-C-01 | operations/storage | Dry-run/audit. |
| W9-OPS-01 | OPS | Metrics/traces/logs/audit/redaction | W9-C-01 | operations/infra | Low-cardinality metrics. |
| W9-OPS-02 | OPS | Backup/restore/disaster runbooks | W9-C-01 | infra/runbooks | Restore drill required. |
| W9-OPS-03 | OPS | Load/query/index profiling | W9-C-01 | infra/tests | Record query profiles. |
| W9-AI-01 | AI | Quality/cost/latency budgets + outage modes | W9-C-01 | analysis/ops | Budget regression blocks promotion. |
| W9-QA-01 | QA | Security/load/restore/retention suites | W9-C-01 | tests/** | Negative paths. |
| W9-INT-01 | INT | Hardening checkpoint | all | evidence | Clean restore + security route. |

## Automated exit evidence

- [ ] Cross-object access denied for API/storage links.
- [ ] Expired presigned URL fails.
- [ ] Secret corpus absent from logs/metrics.
- [ ] Retention dry-run exact; legal hold blocks deletion.
- [ ] Backup restore reconstructs required PG/S3 state within approved RPO/RTO.
- [ ] Load/cost budgets meet target or block checkpoint.
- [ ] Provider outage has explicit controlled state.

## Manual local acceptance

Full script: `../manual-tests/CP-09_hardening.md`.

- [ ] Use two test principals and attempt cross-object routes.
- [ ] Verify short-lived file access expires.
- [ ] Run retention dry-run and legal-hold block on synthetic data.
- [ ] Restore clean environment and reopen completed run/finding.
- [ ] Simulate provider outage; no silent fallback.
- [ ] Inspect telemetry for correlation and redaction.

## Checkpoint exit criterion

Operational/security/data-lifecycle/recovery claims are demonstrated, not merely documented.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
