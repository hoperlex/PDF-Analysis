# ADR-0007: PostgreSQL jobs/outbox; Attempt fencing

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: adapt (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); owner decision `PD-03`; integration decision `ID-02`

## Context
The legacy evidence has at most one active job per project/version and one active attempt per job with an attempt-scoped execution token (`DW-02`), but no Run entity and no domain-level fencing token (`DW-03`, `DW-05`; CP-00 review §10 `E-03`).

## Decision
Persist Job before execution. Each concrete execution is an Attempt with lease/heartbeat and fencing token. DB state change + side-effect intent ends in transactional outbox. Retry creates/renews attempt according to policy; stale attempts cannot publish. No external message broker at bootstrap.

Qualification (CP-00, PD-03, ID-02): the fencing clause is ratifiable only as follows. The capability is named `execution_token`; it is opaque and equality-only, is refreshed on every new `Attempt` and is verified inside the publishing transaction. Fencing is a property of behavior, not a field name and not a monotonic number. Retry/resume/restart/worker failover create a new `Attempt`, never a new `AuditRun`.

## Consequences
- Positive: durable job/outbox is ratifiable as written; the Run-creation rule of `PD-03` is the recorded answer to what creates a new `AuditRun`.

## Revisit trigger
Measured throughput/latency/operational contention proves PostgreSQL scheduling inadequate.

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: adapt, qualification `PD-03` / `ID-02` (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); qualification copied into Decision; meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
