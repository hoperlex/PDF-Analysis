# ADR-0010: Stable Finding identity is separate from run observation

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act)

## Context
Legacy display identifiers such as `F-NNN` can change after rerun and cannot safely carry expert history. Legacy evidence recorded by CP-00 includes stable `MIG` identity with idempotent append (`EX-09`) and a carryover that preserves an existing non-empty human/auto verdict (`EX-08`).

## Decision
`finding_uid` identifies a durable semantic issue. Each run emits `finding_observation_id` with evidence/provenance. Display ordinals are presentation only. Identity matching policy is versioned and may create a new Finding when confidence/rules do not justify carryover.

ExpertDecision references stable Finding plus optional observation context.

## Consequences
- Positive: expert history stays attached to the stable Finding across reruns; display ordinals are presentation only.

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
