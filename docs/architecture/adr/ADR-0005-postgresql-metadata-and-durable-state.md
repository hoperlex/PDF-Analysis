# ADR-0005: PostgreSQL owns metadata and durable workflow state

- Status: accepted for bootstrap; ratify at CP-00

## Decision
PostgreSQL is canonical for business metadata, AuditRun/Job/Attempt state, outbox, decision events and durable audit metadata. Domain invariants use FK/UNIQUE/CHECK/NOT NULL plus domain tests. Filesystem/JSON and WebSocket state are not canonical.

Initially jobs/outbox remain PostgreSQL-backed; introducing a broker requires evidence and ADR.
