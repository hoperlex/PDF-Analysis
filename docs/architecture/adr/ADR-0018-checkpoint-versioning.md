# ADR-0018: Checkpoint version = tag + frozen contracts + automated + manual evidence

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principles P-20, P-21

## Context
A git tag without green gates, a manual report and a contract manifest is not a checkpoint (`P-20`); each checkpoint carries a reproducible local runbook with expected results and evidence capture (`P-21`) (`docs/architecture/ARCHITECTURE_BIBLE.md`).

## Decision
A checkpoint is not merely a tag. It requires: clean integration commit, contract manifest, migration head, automated gates, completed manual local runbook, checkpoint report, known-risk list and rollback/recovery note. Annotated tag is created only after evidence acceptance.

## Consequences
- Positive: a checkpoint is an evidence bundle, not a label.

## Alternatives considered
A bare tag as the checkpoint — rejected by the Decision (`P-20`).

## Verification
The checkpoint's integration report and manual runbook (for CP-00: `docs/manual-tests/CP-00_architecture.md`); the CP-00 review itself creates no tag and no checkpoint claim (CP-00 review §5).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
