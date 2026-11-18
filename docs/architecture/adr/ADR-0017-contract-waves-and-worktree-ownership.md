# ADR-0017: Contract waves and worktree-per-task ownership

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: adapt (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principle P-22; input `U-02` (resolved)

## Context
The W0.2 wave contract executed four lanes concurrently in one checkout on disjoint allowed paths with single-owner hotspots, while this ADR names worktree-per-task as the default (CP-00 review §5, §10 `E-08`).

## Decision
Each wave: contract task → freeze → parallel provider/consumer/test/ops tasks → single integration slot → checkpoint evidence. Default isolation is one git worktree/branch per task. Shared hotspots have one owner. Dependencies reference completed task IDs, not unmerged branches.

Qualification (CP-00, U-02): "one worktree per task" is a default mechanism, not an invariant. A worktree is the default; a shared checkout is admissible only with disjoint allowed paths and one owner per hotspot.

## Consequences
- Positive: the wave/freeze/ownership model is ratifiable as written; the isolation mechanism stays a mechanism, not an invariant (CP-00 review §4, §5).

## Alternatives considered
A shared checkout as the isolation model — admissible only under the qualification above (`U-02`).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: adapt, qualification `U-02` resolved (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); qualification copied into Decision; meaning unchanged.
