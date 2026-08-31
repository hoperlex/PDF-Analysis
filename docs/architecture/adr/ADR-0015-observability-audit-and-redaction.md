# ADR-0015: Diagnostic logs, durable audit and metrics are separate

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Diagnostic logs may be sampled/lost; durable audit is append-only and loss is incident; metrics use low-cardinality labels. Redaction is allowlist-based at channel boundary. Secrets, cookies, presigned URLs, raw user text and entity IDs do not become metric labels.
