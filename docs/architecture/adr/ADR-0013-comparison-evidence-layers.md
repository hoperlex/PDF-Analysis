# ADR-0013: Comparison separates approved state, raw evidence and AI synthesis

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: adapt (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); owner decision `PD-04`; principle P-17
- Amends: — · Amended by: `ADR-0025` (extends it to the comparison modules)

## Context
Legacy evidence recorded by CP-00: approved links are authoritative over suggestions (`CP-02`); deterministic gates and signature reuse (`CP-03`); additive AI keyed to current artifacts with race rejection before atomic write (`CP-04`); repair proof and undo (`CP-05`); graphics are explicitly not analyzed (`CP-06`, `not observed`).

## Decision
Automatic sheet matching produces rebuildable suggestions. User-approved links are owned state and survive recomputation. Deterministic text exclusions/diff and raw graphic evidence are immutable per comparison revision. AI review/synthesis is a derived artifact keyed by raw checksums. Repairs require proof, audit and undo.

Qualification (CP-00, PD-04): the text, approved-link and AI layers are ratifiable. The "raw graphic evidence" layer is approved as future greenfield scope, absent from legacy parity and from W0; its first contractual inclusion is in **W7**, together with a dedicated golden graphic pair.

## Consequences
- Positive: the text, approved-link and AI layers are ratifiable as written (CP-00 review §5).
- Cost: the raw-graphic layer waits for W7 and its golden graphic pair.

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: adapt, qualification `PD-04` (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); qualification copied into Decision; meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
