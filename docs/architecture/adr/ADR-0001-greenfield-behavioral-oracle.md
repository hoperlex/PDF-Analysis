# ADR-0001: Greenfield product; legacy is a behavioral oracle

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principle P-19

## Context
A working application exists, but its filesystem/JSON state, large frontend/orchestrator and duplicated stage semantics are precisely the technical debt the new product must avoid. The new repository starts empty.

## Decision
No runtime Strangler dependency is required. Legacy is a read-only evidence source: characterization tests, anonymized fixtures, expected structural outputs and edge cases. New code may port an algorithm only after defining its contract and tests. Importing a large legacy service/router/pipeline manager as a shortcut is forbidden without a new ADR.

## Consequences
- Positive: business parity is proven deliberately rather than inherited accidentally; architecture does not become coupled to old paths/state formats.
- Cost: initial discovery costs more.

## Alternatives considered
1. The refactoring source's "hybrid Strangler" (legacy stays the production runtime) — deliberately not transferred; recorded as accepted greenfield divergence `DV-06` (CP-00 review §5, §8).

## Verification
Algorithm ports follow characterize → contract → tests → parity (CP-00 review §5).

## Revisit trigger
A proposal to import legacy runtime code needs a new ADR (see Decision).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
