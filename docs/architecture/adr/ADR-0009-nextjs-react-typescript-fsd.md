# ADR-0009: Next.js/React/TypeScript strict with FSD vertical slices

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act)

## Context
The legacy UI declares its own stage/model configuration and legacy artifact aliases, and UI parity with the legacy application is unknown (CP-00 review §5, `[B]` §2.2 items 24–25 and §7 gap 8).

## Decision
Use Next.js App Router; thin `app/`; domain UI organized under `_pages`, widgets, features, entities, shared. API transport is generated from OpenAPI. Server state and UI state remain separate; no global domain mega-store. PDF viewer/live progress are bounded client islands.

## Consequences
- Positive: the UI consumes the stage registry and the generated client and never redeclares stage vocabulary; no route-strangler phase exists (CP-00 review §5).

## Alternatives considered
The refactoring source's route strangler (source ADR-0017, `proposed`) — not applicable (CP-00 review §5).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
