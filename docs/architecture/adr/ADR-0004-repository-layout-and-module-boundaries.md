# ADR-0004: Repository layout and module boundaries

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: adapt (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); `U-03` (§11)

## Context
The CP-00 stage S00 requires "architecture lint rules are specified" as automated exit evidence, and this ADR mandates architecture lint/test; no lint-rule specification existed under `docs/architecture/**` when the disposition was recorded (CP-00 review §5, §10 `E-06`).

## Decision
Use `src/auditmanager/<bounded-context>` for backend, `web/src/{app,_app,_pages,widgets,features,entities,shared}` for frontend, top-level `contracts/`, `db/`, `infra/`, `tests/`, `fixtures/`, `docs/`. Architecture lint/test must prevent deep cross-context imports and FSD upward/cross-slice imports.

Empty folders are not architecture: sublayers appear only when a real use case needs them.

Qualification (CP-00, U-03): the layout is ratifiable as written; the lint-rule specification is an assigned CP-00 exit obligation — `W0-ARC-02` specifies the architectural lint rules before CP-00 and `W1-ARC-01` implements enforcement.

## Consequences
- The lint-rule specification (`docs/architecture/ARCHITECTURE_LINT_RULES.md`, `W0-ARC-02`) and its enforcement (`W1-ARC-01`) are assigned tasks, not part of this ADR.

## Verification
Architecture lint/test for deep cross-context imports and FSD upward/cross-slice imports (rules: `docs/architecture/ARCHITECTURE_LINT_RULES.md`).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: adapt, qualification `U-03` (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); qualification copied into Decision; meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
