# ADR-0015: Diagnostic logs, durable audit and metrics are separate

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principle P-12; input `U-04`

## Context
The legacy evidence shows redaction before outbox persistence and an action log whose retention/immutability is not established (`LO-01`; CP-00 review §5).

## Decision
Diagnostic logs may be sampled/lost; durable audit is append-only and loss is incident; metrics use low-cardinality labels. Redaction is allowlist-based at channel boundary. Secrets, cookies, presigned URLs, raw user text and entity IDs do not become metric labels.

## Consequences
- Positive: the channel separation itself is ratifiable (CP-00 review §5).
- Cost: durable audit retention depends on `ADR-0014` (authority `U-04`); CP-00 did not ratify the retention and legal-hold clauses while `U-04` is open (CP-00 review §5, §11).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify for the channel separation (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
