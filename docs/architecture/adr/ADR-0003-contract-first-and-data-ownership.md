# ADR-0003: Contract-first boundaries and single data owner

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principle P-04

## Context
Legacy evidence recorded by CP-00: dual filesystem layouts and shadow mirroring (`[B]` §7 gap 7), against one authoritative saved link file versus disposable suggestions (`CP-02`).

## Decision
Every independently changing boundary is versioned by OpenAPI, JSON Schema, SQL migration or equivalent machine schema. One aggregate/entity has one authoritative writer. Parallel implementation starts only after shared contract freeze.

## Consequences
- Positive: agents can work concurrently against stable interfaces; integration conflicts become explicit contract changes rather than hidden drift.
- Cost: every aggregate needs a named authoritative writer before implementation (CP-00 review §5).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
