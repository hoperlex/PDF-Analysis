# ADR-0016: Testing is an evidence model, not a test pyramid quota

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); input `U-05`

## Context
The CP-00 behavioral inventory lists golden-journey candidates `GJ-01`–`GJ-11` with required assertions; `W0-BHV-02` selects five journeys from the eleven (CP-00 review §5, §11 `U-05`).

## Decision
Use characterization/golden, domain, contract, integration with real PostgreSQL/S3, migration, E2E, replay/live-quality, restore/rollback and manual checkpoint evidence. No layer has an arbitrary coverage percentage as sole release proof.

## Consequences
- Positive: release proof combines several evidence layers instead of one coverage number.
- Cost: the uncovered remainder of the golden journeys must be recorded as a known coverage gap, not silently dropped; acceptance needs a machine-readable mapping of the eleven candidates to concrete assertion IDs (`U-05`; CP-00 review §5, §11). Live LLM text equality is explicitly out of scope.

## Alternatives considered
A test pyramid with coverage quotas — rejected by the title and Decision (no arbitrary coverage percentage as sole release proof).

## Verification
The evidence layers listed in Decision; the golden-journey mapping of `U-05`.

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged); `U-05` conditionally accepted.
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
