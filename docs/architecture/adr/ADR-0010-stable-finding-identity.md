# ADR-0010: Stable Finding identity is separate from run observation

- Status: accepted for bootstrap; ratify at CP-00

## Context
Legacy display identifiers such as `F-NNN` can change after rerun and cannot safely carry expert history.

## Decision
`finding_uid` identifies a durable semantic issue. Each run emits `finding_observation_id` with evidence/provenance. Display ordinals are presentation only. Identity matching policy is versioned and may create a new Finding when confidence/rules do not justify carryover.

ExpertDecision references stable Finding plus optional observation context.
