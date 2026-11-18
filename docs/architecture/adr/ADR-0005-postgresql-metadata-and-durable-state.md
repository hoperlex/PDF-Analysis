# ADR-0005: PostgreSQL owns metadata and durable workflow state

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); owner decision `PD-03`

## Context
The legacy application keeps state in filesystem JSON/directories, SQLite and process-local handles; pipeline/job state partly lives in process-local active task handles (CP-00 review §5, `FS-06`). Those pilot choices are not transferred.

## Decision
PostgreSQL is canonical for business metadata, AuditRun/Job/Attempt state, outbox, decision events and durable audit metadata. Domain invariants use FK/UNIQUE/CHECK/NOT NULL plus domain tests. Filesystem/JSON and WebSocket state are not canonical.

Initially jobs/outbox remain PostgreSQL-backed; introducing a broker requires evidence and ADR.

## Consequences
- Positive: storage canonicality is uncontested (CP-00 review §5); the `AuditRun` state named here is supported by the approved `PD-03` separation of AuditRun, Job and Attempt (CP-00 review §5).
- Positive: durable job/attempt state is canonical; process memory is never a status source and recovery is a declared transition, not a startup side effect (CP-00 `FS-06`).

## Alternatives considered
Legacy filesystem/SQLite pilot choices — not transferred (CP-00 review §5).

## Revisit trigger
A broker needs evidence and an ADR (see Decision).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; owner decision `PD-03`; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
