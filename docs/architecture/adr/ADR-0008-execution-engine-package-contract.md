# ADR-0008: Execution engine is a package-contract boundary

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: adapt (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); owner decisions `PD-02`, `PD-05`; integration decision `ID-03`

## Context
The legacy evidence has 31 stage-declaration sites (29 mapped) that conflict in membership and order, and the single versioned stage registry is only partly supported (CP-00 review §5, §10 `E-02`).

## Decision
Engine consumes versioned `JobPackage` and produces validated `StageResult`/`ResultPackage`. It does not directly update canonical aggregates, switch current version or make expert/publication decisions. Local and remote engines implement the same contract.

A single versioned stage registry owns stage names, dependencies, contract versions and terminal semantics.

Qualification (CP-00, PD-02, PD-05): the "single versioned stage registry" clause was not consumable for a registry freeze until the name-level legacy alias map required by `PD-02` existed. That precondition is met by `contracts/analysis/v1/legacy-stage-name-map.json` (commit `cf7740474`; 62 names), which `docs/program/reviews/W0-QA-01.md` section 7.3 records as meeting it. The map gives every legacy stage name its surface, `source_declaration_id`, immutable evidence and either a canonical target stage or an explicit exclusion, with `findings_merge` → `finding_merge` mandatory; site-level mapping alone does not satisfy it. `ID-03` adds independent confirmation of the nine registry stages and of every alias-bearing declaration site. `PD-05`: the four legacy names `optimization`, `optimization_critic`, `optimization_corrector` and `optimization_review` take the explicit-exclusion branch as a separate project-optimization sub-pipeline; no registry stage changes and no second registry is created.

## Consequences
- Positive: the package boundary is ratifiable as written (CP-00 review §5).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: adapt, qualification `PD-02` / `PD-05` / `ID-03` (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); qualification copied into Decision; meaning unchanged.
- 2026-11-18 — status statements updated to dev fb6c2203e: the `PD-02` alias map exists, met by `contracts/analysis/v1/legacy-stage-name-map.json` (commit `cf7740474`; `docs/program/reviews/W0-QA-01.md` section 7.3); the qualification no longer says the map is missing.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
