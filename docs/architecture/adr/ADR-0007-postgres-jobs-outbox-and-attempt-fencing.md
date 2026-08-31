# ADR-0007: PostgreSQL jobs/outbox; Attempt fencing

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Persist Job before execution. Each concrete execution is an Attempt with lease/heartbeat and fencing token. DB state change + side-effect intent ends in transactional outbox. Retry creates/renews attempt according to policy; stale attempts cannot publish. No external message broker at bootstrap.

## Revisit trigger
Measured throughput/latency/operational contention proves PostgreSQL scheduling inadequate.
