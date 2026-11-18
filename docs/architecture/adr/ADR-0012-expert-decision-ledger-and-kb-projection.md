# ADR-0012: Expert decisions are append-only; KB is a projection

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: adapt (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); owner decision `PD-01`; `R-146o` (`docs/program/OWNER_RULINGS_2026-09-17.md` §3.46; recorded by `PRODUCTION-ADR-PACK-01`)
- Amends: — · Amended by: `ADR-0022` section 3 (the project-erase exception, `R-146o`); `ADR-0027` (case content only)

## Context
The legacy evidence contradicts this ADR: a matching decision is updated and a revoke deletes from both the global log and the active review (`EX-02`, `not observed`; CP-00 review §5, §10 `E-01`). The CP-00 `defer` basis was the undecided `PD-01`; `PD-01` was approved with modification and the disposition became `adapt`.

## Decision
Expert verdict change creates a new immutable decision event. Current verdict, reason aggregates, similar-case index and knowledge-base views are rebuildable projections. AI/reverification may create recommendations but cannot rewrite a human event.

Qualification (CP-00, PD-01): correction and revocation each create a new `decision_id`; a revocation projects the current verdict to `pending` with no automatic restore of the superseded verdict; the KB projection is rebuilt from preserved history. Legacy overwrite/delete is characterized legacy behavior and is not the target.

**Project-erase exception (addendum `R-146o`, 2026-10-26).** The rule above stays true for every path of the product: a verdict change creates a new immutable event, and no API operation, screen or job deletes or rewrites an expert decision event.
- The operator project erase (`ADR-0022` section 3, item `PROD-07` of `PRODUCTION-READINESS-PLAN-01.md`; built as `scripts/recovery/project_erase.py`) removes every row of one project, among them its `expert_decision_event` rows, its findings, its evidence quotes and its comments. It is a deliberate exception, granted by `R-146o` for that one operation. It is not an API operation and not a verdict change; it runs only as the table owner through a script that switches the append-only trigger off inside one transaction and on again before it commits. What stays is the record of the erasure (the `erasure.requested` and `erasure.completed` events and a manifest of the erased Blobs), not the decisions.
- The frozen domain contract `contracts/domain/v1/state-machines.json` says that erasing a Blob's bytes never deletes decision, finding or audit history. That sentence is the exception's counterpart and is not edited: it stays true of the Blob `erased` transition, which the project erase does not use. A clarifying edit of the frozen text is a contract-owner item (`PROD-22`).

## Consequences
- Positive: the full decision history is preserved and every current view is rebuildable from it (`P-18`).
- Cost: one deliberate exception, the operator project erase, which runs only as the table owner (Decision).

## Alternatives considered
Legacy overwrite/delete of a matching decision — characterized legacy behavior, not the target (CP-00 review §5).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: `defer` → `adapt` on `PD-01` (approved with modification) (W0-ARC-01; status text unchanged).
- 2026-10-26 — addendum `R-146o` (`PRODUCTION-ADR-PACK-01`), folded into Decision: the operator project erase is the one exception; the addendum changed no runtime behaviour.
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); qualification copied into Decision, addendum folded in; meaning unchanged.
- 2026-11-18 — status statements updated to dev fb6c2203e: the erase tool exists (`PROD-07A-PROJECT-ERASE-CORE-01`: `scripts/recovery/project_erase.py`, `infra/deploy/erase-project.sh`, `tests/integration/recovery/test_project_erase.py`); `PROD-22` (the clarifying edit of the frozen sentence) is still open.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
